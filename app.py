"""
Servidor Flask para interface web do Extrator de Certificados
"""

from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import os
import tempfile
from pathlib import Path
from extrator_pdf import ExtratorCertificado
from gerador_sql import GeradorSQL
import mysql.connector
import json

# Importa assistente Groq e gerenciador de sessões
from assistente_groq import inicializar_assistente
from sessoes import gerenciador_sessoes
from parser_edicao import extrair_comando_edicao
from formatar_nova import formatar_confirmacao_edicao_nova as formatar_confirmacao_edicao
from gerar_preview_novo import gerar_preview

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.secret_key = os.urandom(24)  # Para usar sessões Flask

# Inicializa assistente Groq (busca API key do .env ou variável de ambiente)
assistente_groq = inicializar_assistente()

ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    """Verifica se o arquivo é um PDF"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Página principal - Chat"""
    return render_template('index_chat_modern.html')


@app.route('/upload')
def upload_page():
    """Página de upload antiga"""
    return render_template('index.html')


@app.route('/processar', methods=['POST'])
def processar_pdfs():
    """Processa os PDFs enviados e retorna JSON"""
    print("\n=== REQUISIÇÃO RECEBIDA ===")
    try:
        # Verifica se há arquivos
        print(f"Files no request: {list(request.files.keys())}")
        if 'pdfs' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400

        files = request.files.getlist('pdfs')

        if not files or files[0].filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

        print(f"Total de arquivos recebidos: {len(files)}")

        # Salva arquivos temporariamente
        temp_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                temp_paths.append(filepath)
                print(f"  Arquivo salvo: {filename}")

        if not temp_paths:
            return jsonify({'error': 'Nenhum arquivo PDF válido encontrado'}), 400

        print(f"Processando {len(temp_paths)} PDFs...")

        # Processa os PDFs
        extrator = ExtratorCertificado()
        instrumentos = extrator.processar_multiplos_pdfs(temp_paths)

        print(f"Processamento concluído: {len(instrumentos)} instrumentos encontrados")

        # Calcula total de grandezas
        total_grandezas = sum(len(inst.get('grandezas', [])) for inst in instrumentos)

        # Limpa arquivos temporários
        for path in temp_paths:
            try:
                os.remove(path)
            except:
                pass

        # Retorna resultado
        from datetime import datetime
        resultado = {
            'data_extracao': datetime.now().isoformat(),
            'total_instrumentos': len(instrumentos),
            'total_grandezas': total_grandezas,
            'instrumentos': instrumentos
        }

        return jsonify(resultado)

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"\n[ERRO] ERRO NO PROCESSAMENTO:")
        print(f"Mensagem: {error_msg}")
        print(f"Traceback completo:")
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


@app.route('/gerar-sql', methods=['POST'])
def gerar_sql():
    """Gera arquivo SQL a partir do JSON de instrumentos"""
    try:
        data = request.get_json()

        if not data or 'instrumentos' not in data:
            return jsonify({'error': 'Dados inválidos'}), 400

        # Obtém user_id (padrão: 1)
        user_id = data.get('user_id', 1)
        
        # Valida user_id
        try:
            user_id = int(user_id)
            if user_id <= 0:
                return jsonify({'error': 'User ID deve ser maior que 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'User ID inválido'}), 400

        # Gera SQL com user_id customizado
        gerador = GeradorSQL(user_id=user_id)
        sql_content = gerador.gerar_sql_completo(data['instrumentos'])

        # Salva em arquivo temporário
        temp_sql = os.path.join(app.config['UPLOAD_FOLDER'], f'instrumentos_user_{user_id}.sql')
        with open(temp_sql, 'w', encoding='utf-8') as f:
            f.write(sql_content)

        # Retorna arquivo
        return send_file(
            temp_sql,
            as_attachment=True,
            download_name=f'gocal_user_{user_id}.sql',
            mimetype='application/sql'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'ok'})


@app.route('/visualizar')
def visualizar():
    """Página de visualização dos instrumentos"""
    return render_template('visualizar.html')


@app.route('/api/instrumentos', methods=['GET'])
def listar_instrumentos():
    """API para listar instrumentos do banco"""
    try:
        conn = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            database='instrumentos',
            user='root',
            password=''
        )

        cursor = conn.cursor(dictionary=True)

        # Busca instrumentos
        cursor.execute("""
            SELECT id, identificacao, nome, fabricante, modelo, numero_serie,
                   descricao, periodicidade, departamento, responsavel, status,
                   tipo_familia, data_calibracao, data_emissao, created_at
            FROM instrumentos
            ORDER BY created_at DESC
        """)

        instrumentos = cursor.fetchall()

        # Para cada instrumento, busca suas grandezas
        for inst in instrumentos:
            cursor.execute("""
                SELECT id, servicos, tolerancia_processo, unidade, resolucao,
                       criterio_aceitacao, faixa_nominal
                FROM grandezas
                WHERE instrumento_id = %s
            """, (inst['id'],))

            grandezas = cursor.fetchall()

            # Converte servicos de JSON para array
            for g in grandezas:
                if g['servicos']:
                    try:
                        g['servicos'] = json.loads(g['servicos'])
                    except:
                        g['servicos'] = []

            inst['grandezas'] = grandezas

        cursor.close()
        conn.close()

        return jsonify({
            'total': len(instrumentos),
            'instrumentos': instrumentos
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/instrumentos/<int:id>', methods=['DELETE'])
def deletar_instrumento(id):
    """API para deletar um instrumento e suas grandezas"""
    try:
        conn = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            database='instrumentos',
            user='root',
            password=''
        )

        cursor = conn.cursor()

        # Primeiro deleta as grandezas associadas
        cursor.execute("DELETE FROM grandezas WHERE instrumento_id = %s", (id,))

        # Depois deleta o instrumento
        cursor.execute("DELETE FROM instrumentos WHERE id = %s", (id,))

        conn.commit()

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Instrumento não encontrado'}), 404

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Instrumento deletado com sucesso'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def responder_cumprimento(comando):
    """Verifica se é um cumprimento e responde de forma natural"""
    from datetime import datetime

    comando_lower = comando.lower().strip()

    # Cumprimentos simples
    cumprimentos_simples = ['oi', 'olá', 'ola', 'hey', 'ei', 'hello', 'hi']
    if comando_lower in cumprimentos_simples:
        return True, "Olá! 👋 Como posso te ajudar hoje? Faça upload dos PDFs e me diga o que você precisa extrair."

    # Verifica horário para saudações com tempo
    hora_atual = datetime.now().hour

    if hora_atual < 12:
        saudacao = "Bom dia"
        emoji = "🌅"
    elif hora_atual < 18:
        saudacao = "Boa tarde"
        emoji = "☀️"
    else:
        saudacao = "Boa noite"
        emoji = "🌙"

    # Bom dia / Boa tarde / Boa noite
    if any(palavra in comando_lower for palavra in ['bom dia', 'boa tarde', 'boa noite']):
        return True, f"{saudacao}! {emoji} Pronto para extrair informações dos seus certificados. O que você precisa?"

    # Agradecimentos
    if any(palavra in comando_lower for palavra in ['obrigado', 'obrigada', 'valeu', 'thanks', 'thank you']):
        return True, "De nada! 😊 Estou aqui para ajudar. Precisa de mais alguma coisa?"

    # Tchau
    if any(palavra in comando_lower for palavra in ['tchau', 'até logo', 'até mais', 'bye', 'adeus']):
        return True, "Até logo! 👋 Volte sempre que precisar extrair informações de certificados."

    # Perguntas sobre campos do banco
    if any(palavra in comando_lower for palavra in ['quais informações', 'quais dados', 'o que vai pro banco', 'campos do banco', 'informações do banco', 'dados do banco']):
        resposta = """<div style="line-height: 1.6;">
<h3>📊 Informações que vão para o banco de dados:</h3>

<h4>Dados do Instrumento:</h4>
<ul>
<li>Identificação</li>
<li>Nome</li>
<li>Fabricante</li>
<li>Modelo</li>
<li>Número de Série</li>
<li>Descrição</li>
<li>Periodicidade (meses)</li>
<li>Departamento</li>
<li>Responsável</li>
<li>Status</li>
<li>Tipo/Família</li>
<li>Série de Desenvolvimento</li>
<li>Criticidade</li>
<li>Motivo da Calibração</li>
<li>Quantidade</li>
<li>Data de Calibração</li>
<li>Data de Emissão</li>
</ul>

<h4>Dados das Grandezas:</h4>
<ul>
<li>Serviços (pontos de medição)</li>
<li>Tolerância do Processo</li>
<li>Tolerância Simétrica</li>
<li>Unidade</li>
<li>Resolução</li>
<li>Critério de Aceitação</li>
<li>Regra de Decisão</li>
<li>Faixa Nominal</li>
<li>Classe/Norma</li>
<li>Classificação</li>
<li>Faixa de Uso</li>
</ul>

<h4>Dados de Controle:</h4>
<ul>
<li>ID do Usuário</li>
<li>ID do Responsável pelo Cadastro</li>
<li>Data de Criação</li>
<li>Data de Atualização</li>
</ul>
</div>"""
        return True, resposta

    return False, None




@app.route('/chat-extrair', methods=['POST'])
def chat_extrair():
    """Processa PDFs com comando personalizado do chat"""
    try:
        # Pega arquivos e comando
        files = request.files.getlist('pdfs')
        comando = request.form.get('comando', 'extrair tudo').lower()
        
        print(f"\n🔍 [DEBUG] Comando recebido: '{comando}'")
        print(f"🔍 [DEBUG] Número de arquivos: {len(files)}")
        
        # Conta PDFs válidos
        num_pdfs = len([f for f in files if f and f.filename != ''])
        print(f"🔍 [DEBUG] PDFs válidos: {num_pdfs}")

        # Gerencia sessão do usuário
        if 'session_id' not in session:
            session['session_id'] = gerenciador_sessoes.criar_sessao()
        
        session_id, sessao_dados = gerenciador_sessoes.obter_sessao(session['session_id'])
        session['session_id'] = session_id  # Atualiza se foi recriada
        
        contexto_usuario = sessao_dados['contexto']
        historico = gerenciador_sessoes.obter_historico(session_id, limite=5)
        
        # Adiciona informação sobre PDFs ao contexto
        if num_pdfs > 0:
            contexto_usuario['num_pdfs'] = num_pdfs
            contexto_usuario['nomes_pdfs'] = [f.filename for f in files if f and f.filename != '']

        # Normaliza comando para verificações
        comando_lower = comando.lower().strip()

        # FALLBACK: Parser regex de edição (só se Groq não estiver disponível)
        info_edicao = extrair_comando_edicao(comando)
        if info_edicao['tipo'] == 'EDICAO' and not (assistente_groq and assistente_groq.esta_disponivel()):
            print(f"🔧 [DEBUG] Comando de edição detectado: {info_edicao}")
            
            # Tenta editar o campo
            resultado = gerenciador_sessoes.editar_campo_instrumento(
                session_id,
                info_edicao['identificador'],
                info_edicao['campo'],
                info_edicao['valor_novo']
            )
            
            # Formata resposta
            mensagem_html = formatar_confirmacao_edicao(resultado)
            
            # Salva no histórico
            gerenciador_sessoes.adicionar_mensagem(session_id, 'user', comando)
            gerenciador_sessoes.adicionar_mensagem(session_id, 'assistant', mensagem_html)
            
            return jsonify({
                'success': resultado['sucesso'],
                'is_greeting': True,  # Para não processar como extração
                'message': mensagem_html,
                'powered_by': 'Metron Editor'
            })
        
        # PRIORIDADE 1.5: Verifica se é comando para mostrar dados da sessão
        if any(palavra in comando_lower for palavra in ['mostra os dados', 'mostar os dados', 'mostra dados', 'mostar dados', 'ver dados', 'listar dados', 'mostrar instrumentos', 'exibir dados', 'mostrar os dados']):
            print(f"📊 [DEBUG] Comando 'mostrar dados' detectado!")
            instrumentos_sessao = gerenciador_sessoes.obter_instrumentos(session_id)
            print(f"📊 [DEBUG] Instrumentos na sessão: {len(instrumentos_sessao) if instrumentos_sessao else 0}")
            if instrumentos_sessao:
                print(f"📊 [DEBUG] Identificação: {instrumentos_sessao[0].get('identificacao', 'N/A')}")
                print(f"📊 [DEBUG] Modelo: {instrumentos_sessao[0].get('modelo', 'N/A')}")
            
            
            if instrumentos_sessao:
                # Retorna os dados da sessão como MENSAGEM formatada (não confia no frontend)
                preview_html = gerar_preview(instrumentos_sessao)
                return jsonify({
                    'success': True,
                    'is_greeting': True,  # Força exibição como mensagem
                    'message': preview_html,
                    'powered_by': 'Dados da Sessão (com edições)'
                })
            else:
                # Se não tem instrumentos na sessão mas tem PDFs, processa automaticamente
                if files and files[0].filename != '':
                    print(f"📊 [DEBUG] Não há instrumentos na sessão, mas há {num_pdfs} PDF(s). Processando automaticamente...")
                    # Continua o fluxo normal de processamento (não retorna aqui)
                else:
                    return jsonify({
                        'success': False,
                        'is_greeting': True,
                        'message': '⚠️ Nenhum instrumento na sessão. Faça upload dos PDFs primeiro.'
                    }), 400

        # PRIORIDADE 2: Tenta usar Groq se disponível
        print(f"🔍 [DEBUG] Assistente Groq disponível: {assistente_groq and assistente_groq.esta_disponivel()}")
        if assistente_groq and assistente_groq.esta_disponivel():
            # Processa comando com LLaMA (com contexto e histórico)
            resultado_groq = assistente_groq.processar_comando(
                comando, 
                contexto_usuario=contexto_usuario,
                historico=historico
            )
            
            print(f"🔍 [DEBUG] Resultado Groq: tipo={resultado_groq.get('tipo')}, resposta={resultado_groq.get('resposta')[:100]}...")
            
            # Salva mensagem do usuário no histórico
            gerenciador_sessoes.adicionar_mensagem(session_id, 'user', comando)
            
            # Se o LLaMA extraiu o nome do usuário, salva no contexto
            if resultado_groq.get('nome_usuario'):
                gerenciador_sessoes.atualizar_contexto(session_id, 'nome', resultado_groq['nome_usuario'])
                print(f"✅ Nome do usuário salvo: {resultado_groq['nome_usuario']}")
            
            # Salva resposta do assistente no histórico
            gerenciador_sessoes.adicionar_mensagem(session_id, 'assistant', resultado_groq['resposta'])
            
            # NOVO: Se o Groq identificou como EDICAO, processa a edição
            if resultado_groq['tipo'] == 'EDICAO':
                # Verifica se há instrumentos na sessão ANTES de tentar editar
                instrumentos_sessao = gerenciador_sessoes.obter_instrumentos(session_id)
                if not instrumentos_sessao:
                    return jsonify({
                        'success': False,
                        'is_greeting': True,
                        'message': '⚠️ Nenhum instrumento na sessão. Faça upload dos PDFs primeiro.',
                        'powered_by': 'Metron Editor'
                    }), 400
                
                # Verifica se é edição múltipla (arrays) ou única
                campos_editar = resultado_groq.get('campos_editar')
                valores_novos = resultado_groq.get('valores_novos')
                
                if campos_editar and valores_novos and len(campos_editar) > 0:
                    # EDIÇÃO MÚLTIPLA
                    print(f"🔧 [DEBUG] Groq identificou EDIÇÃO MÚLTIPLA: campos={campos_editar}, valores={valores_novos}")
                    
                    resultados = []
                    todas_sucesso = True
                    
                    for campo, valor in zip(campos_editar, valores_novos):
                        resultado = gerenciador_sessoes.editar_campo_instrumento(
                            session_id,
                            resultado_groq.get('identificador'),
                            campo,
                            valor
                        )
                        resultados.append(resultado)
                        if not resultado['sucesso']:
                            todas_sucesso = False
                    
                    # Formata mensagem consolidada
                    if todas_sucesso:
                        edicoes_texto = []
                        for r in resultados:
                            edicoes_texto.append(f"✅ **{r['campo']}**: `{r['valor_antigo']}` → `{r['valor_novo']}`")
                        
                        mensagem_html = f"""
                        <div style="padding: 10px; background: #e8f5e9; border-left: 4px solid #4caf50; border-radius: 4px;">
                            <h4 style="margin: 0 0 10px 0; color: #2e7d32;">✅ Campos editados com sucesso!</h4>
                            {'<br>'.join(edicoes_texto)}
                        </div>
                        """
                    else:
                        mensagem_html = f"""
                        <div style="padding: 10px; background: #ffebee; border-left: 4px solid #f44336; border-radius: 4px;">
                            <h4 style="margin: 0 0 10px 0; color: #c62828;">⚠️ Algumas edições falharam</h4>
                            {resultados[0].get('mensagem', 'Erro desconhecido')}
                        </div>
                        """
                    
                    return jsonify({
                        'success': todas_sucesso,
                        'is_greeting': True,
                        'message': mensagem_html,
                        'powered_by': 'Groq LLaMA 3.3 + Metron Editor'
                    })
                else:
                    # EDIÇÃO ÚNICA
                    print(f"🔧 [DEBUG] Groq identificou EDICAO ÚNICA: campo={resultado_groq.get('campo')}, valor={resultado_groq.get('valor_novo')}")
                    
                    resultado = gerenciador_sessoes.editar_campo_instrumento(
                        session_id,
                        resultado_groq.get('identificador'),  # Pode ser None
                        resultado_groq.get('campo'),
                        resultado_groq.get('valor_novo')
                    )
                    
                    # Formata resposta
                    mensagem_html = formatar_confirmacao_edicao(resultado)
                    
                    return jsonify({
                        'success': resultado['sucesso'],
                        'is_greeting': True,
                        'message': mensagem_html,
                        'powered_by': 'Groq LLaMA 3.3 + Metron Editor'
                    })
            
            # Se for cumprimento, pergunta ou exclusão, responde direto (não precisa de PDFs)
            if resultado_groq['tipo'] in ['CUMPRIMENTO', 'PERGUNTA_INFO', 'EXCLUSAO']:
                print(f"✅ [DEBUG] Retornando resposta do Groq (tipo: {resultado_groq['tipo']})")
                return jsonify({
                    'success': True,
                    'is_greeting': True,
                    'message': resultado_groq['resposta'],
                    'powered_by': 'Groq LLaMA 3.3'
                })
            
            # Se for EXTRACAO ou FILTRO, verifica se há arquivos
            if resultado_groq['tipo'] in ['EXTRACAO', 'FILTRO']:
                if not files or files[0].filename == '':
                    print(f"⚠️ [DEBUG] Tipo {resultado_groq['tipo']} mas sem arquivos")
                    return jsonify({
                        'success': False, 
                        'message': resultado_groq['resposta']  # LLaMA já pediu para fazer upload
                    }), 400
        else:
            print("⚠️ [DEBUG] Groq não disponível, usando sistema de regras")
        
        # Fallback: Verifica se é um cumprimento (sistema de regras)
        is_cumprimento, resposta = responder_cumprimento(comando)
        if is_cumprimento:
            return jsonify({
                'success': True,
                'is_greeting': True,
                'message': resposta
            })

        # IMPORTANTE: Se não tem arquivos MAS é comando de visualização, mostra dados da sessão
        comandos_visualizacao = ['mostrar tudo', 'extrair tudo', 'ver tudo', 'listar tudo', 'mostra tudo', 'exibir tudo']
        if (not files or files[0].filename == '') and any(cmd in comando_lower for cmd in comandos_visualizacao):
            instrumentos_sessao = gerenciador_sessoes.obter_instrumentos(session_id)
            if instrumentos_sessao:
                print(f"📊 [DEBUG] Mostrando dados da sessão (sem reprocessar PDF)")
                preview_html = gerar_preview(instrumentos_sessao)
                return jsonify({
                    'success': True,
                    'is_greeting': True,
                    'message': preview_html,
                    'powered_by': 'Dados da Sessão (com edições)'
                })
            else:
                return jsonify({'success': False, 'message': 'Por favor, faça upload de PDFs para extrair dados.'}), 400
        
        # Se chegou aqui e não tem arquivos, pede upload
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': 'Por favor, faça upload de PDFs para extrair dados.'}), 400

        # Salva arquivos temporariamente
        temp_paths = []
        uploaded_filenames = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                temp_paths.append(filepath)
                uploaded_filenames.append(filename)

        # IMPORTANTE: Verifica se são arquivos NOVOS ou os mesmos da sessão
        instrumentos_existentes = gerenciador_sessoes.obter_instrumentos(session_id)
        comandos_visualizacao = ['mostrar tudo', 'extrair tudo', 'ver tudo', 'listar tudo', 'mostra tudo', 
                                'exibir tudo', 'mostrar os dados', 'mostra os dados']
        
        # Verifica se os arquivos são os mesmos da sessão
        arquivos_sao_os_mesmos = False
        if instrumentos_existentes:
            arquivos_sessao = [inst.get('arquivo_origem', '').split('/')[-1].split('\\')[-1] 
                             for inst in instrumentos_existentes]
            arquivos_sao_os_mesmos = set(uploaded_filenames) == set(arquivos_sessao)
        
        # Só reutiliza dados da sessão se:
        # 1. Já existem instrumentos
        # 2. É comando de visualização
        # 3. Os arquivos são OS MESMOS (não é novo upload)
        if instrumentos_existentes and any(cmd in comando_lower for cmd in comandos_visualizacao) and arquivos_sao_os_mesmos:
            print(f"📊 [DEBUG] Mesmos arquivos da sessão - mostrando dados editados ao invés de reprocessar")
            # Limpa arquivos temporários
            for path in temp_paths:
                try:
                    os.remove(path)
                except:
                    pass
            
            # Mostra os dados da sessão (com edições)
            preview_html = gerar_preview(instrumentos_existentes)
            return jsonify({
                'success': True,
                'is_greeting': True,
                'message': preview_html,
                'powered_by': 'Dados da Sessão (com edições)'
            })

        # Se chegou aqui, são NOVOS arquivos ou comando diferente - processa normalmente
        print(f"📊 [DEBUG] Novos arquivos detectados - processando PDFs")
        extrator = ExtratorCertificado()
        instrumentos = extrator.processar_multiplos_pdfs(temp_paths)

        # Limpa arquivos temporários
        for path in temp_paths:
            try:
                os.remove(path)
            except:
                pass

        # Filtra campos baseado no comando
        # Se Groq identificou campos específicos, usa eles
        if assistente_groq and assistente_groq.esta_disponivel():
            resultado_groq = assistente_groq.processar_comando(comando)
            if resultado_groq.get('campos'):
                campos_extrair = resultado_groq['campos']
            else:
                campos_extrair = parse_comando(comando)
        else:
            campos_extrair = parse_comando(comando)
        
        if campos_extrair and campos_extrair != 'tudo':
            instrumentos = filtrar_campos(instrumentos, campos_extrair)

        # NOVO: Salva instrumentos na sessão (antes de ir pro banco)
        gerenciador_sessoes.salvar_instrumentos(session_id, instrumentos)
        print(f"💾 [DEBUG] {len(instrumentos)} instrumento(s) salvos na sessão {session_id}")

        # Gera preview
        preview = gerar_preview(instrumentos)

        # Se era um comando de "mostrar dados", retorna formatação completa HTML
        if any(palavra in comando_lower for palavra in ['mostra os dados', 'mostar os dados', 'mostra dados', 'mostar dados', 'ver dados', 'listar dados', 'mostrar instrumentos', 'exibir dados', 'mostrar os dados', 'mostrar tudo', 'extrair tudo', 'ver tudo', 'listar tudo']):
             preview_html = preview.replace('\n', '<br>')
             resposta_final = {
                'success': True,
                'is_greeting': True, # Força exibição como mensagem de texto
                'message': f'<div style="font-family: monospace; white-space: pre-wrap;">{preview_html}</div>',
                'powered_by': 'Metron Auto-Process'
            }
        else:
            # Resposta padrão para extração normal
            resposta_final = {
                'success': True,
                'message': f'✅ Extraídos {len(instrumentos)} instrumento(s) com sucesso!\n\n💡 Você pode editar qualquer campo antes de inserir no banco. Exemplo:\n"muda o numero de serie do arquivo x34 para 123"',
                'instrumentos': instrumentos,
                'preview': preview
            }
        
        # Adiciona badge se usou Groq
        if assistente_groq and assistente_groq.esta_disponivel():
            if 'powered_by' not in resposta_final:
                resposta_final['powered_by'] = 'Groq LLaMA 3.2'
        
        return jsonify(resposta_final)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/inserir-banco', methods=['POST'])
def inserir_banco():
    """Insere instrumentos extraídos diretamente no banco"""
    try:
        data = request.get_json()
        user_id = int(data.get('user_id', 1))
        
        # Obtém session_id
        if 'session_id' not in session:
            return jsonify({
                'success': False, 
                'message': 'Sessão não encontrada. Faça upload dos PDFs novamente.'
            }), 400
        
        session_id = session['session_id']
        
        # Tenta obter instrumentos da sessão primeiro (podem ter sido editados)
        instrumentos = gerenciador_sessoes.obter_instrumentos(session_id)
        
        # Se não tem na sessão, tenta pegar do request (fallback para compatibilidade)
        if not instrumentos:
            instrumentos = data.get('instrumentos', [])
        
        print(f"📥 [DEBUG] Inserindo {len(instrumentos)} instrumento(s) no banco (user_id={user_id})")

        if not instrumentos:
            return jsonify({'success': False, 'message': 'Nenhum instrumento para inserir'}), 400

        # Conecta ao banco
        conn = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            database='instrumentos',
            user='root',
            password=''
        )

        cursor = conn.cursor()

        total_inseridos = 0
        total_ignorados = 0
        total_grandezas = 0
        duplicatas = []

        for inst in instrumentos:
            identificacao = inst.get('identificacao')
            
            # Verifica se já existe instrumento com mesma identificação para este user_id
            cursor.execute("""
                SELECT id FROM instrumentos 
                WHERE identificacao = %s AND user_id = %s
                LIMIT 1
            """, (identificacao, user_id))
            
            existe = cursor.fetchone()
            
            if existe:
                # Instrumento já existe, pula para o próximo
                total_ignorados += 1
                duplicatas.append(identificacao or 'sem identificação')
                continue
            
            # Insere instrumento
            sql_inst = """
                INSERT INTO instrumentos (
                    identificacao, nome, fabricante, modelo, numero_serie, descricao,
                    periodicidade, departamento, responsavel, status, tipo_familia,
                    serie_desenv, criticidade, motivo_calibracao, quantidade,
                    user_id, responsavel_cadastro_id, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """

            valores_inst = (
                identificacao,
                inst.get('nome'),
                inst.get('fabricante'),
                inst.get('modelo'),
                inst.get('numero_serie'),
                inst.get('descricao'),
                inst.get('periodicidade', 12),
                inst.get('departamento'),
                inst.get('responsavel'),
                inst.get('status', 'Sem Calibração'),
                inst.get('tipo_familia'),
                inst.get('serie_desenv'),
                inst.get('criticidade'),
                inst.get('motivo_calibracao', 'Calibração Periódica'),
                inst.get('quantidade', 1),
                user_id,
                user_id
            )

            cursor.execute(sql_inst, valores_inst)
            instrumento_id = cursor.lastrowid
            total_inseridos += 1

            # Insere grandezas
            for grandeza in inst.get('grandezas', []):
                sql_grandeza = """
                    INSERT INTO grandezas (
                        instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica,
                        unidade, resolucao, criterio_aceitacao, regra_decisao_id,
                        faixa_nominal, classe_norma, classificacao, faixa_uso,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """

                valores_grandeza = (
                    instrumento_id,
                    json.dumps(grandeza.get('servicos', [])),
                    grandeza.get('tolerancia_processo'),
                    grandeza.get('tolerancia_simetrica', True),
                    grandeza.get('unidade'),
                    grandeza.get('resolucao'),
                    grandeza.get('criterio_aceitacao'),
                    grandeza.get('regra_decisao_id', 1),
                    grandeza.get('faixa_nominal'),
                    grandeza.get('classe_norma'),
                    grandeza.get('classificacao'),
                    grandeza.get('faixa_uso')
                )

                cursor.execute(sql_grandeza, valores_grandeza)
                total_grandezas += 1

        conn.commit()
        cursor.close()
        conn.close()

        # Monta mensagem de resposta
        mensagem = f'✅ Inseridos {total_inseridos} instrumento(s) e {total_grandezas} grandeza(s) no banco!'
        
        if total_ignorados > 0:
            mensagem += f'\n⚠️ {total_ignorados} instrumento(s) ignorado(s) (já existente(s) no banco)'
            if duplicatas:
                mensagem += f'\n📋 Duplicatas: {", ".join(duplicatas[:5])}'
                if len(duplicatas) > 5:
                    mensagem += f' e mais {len(duplicatas) - 5}...'
        
        # Limpa instrumentos da sessão após inserção bem-sucedida
        gerenciador_sessoes.limpar_instrumentos(session_id)
        print(f"🧹 [DEBUG] Instrumentos limpos da sessão {session_id}")

        return jsonify({
            'success': True,
            'message': mensagem,
            'inseridos': total_inseridos,
            'ignorados': total_ignorados,
            'duplicatas': duplicatas
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/instrumentos-pendentes', methods=['GET'])
def instrumentos_pendentes():
    """Retorna instrumentos pendentes na sessão (que ainda não foram inseridos no banco)"""
    try:
        # Obtém session_id
        if 'session_id' not in session:
            return jsonify({
                'success': True,
                'instrumentos': [],
                'total': 0,
                'message': 'Nenhuma sessão ativa'
            })
        
        session_id = session['session_id']
        instrumentos = gerenciador_sessoes.obter_instrumentos(session_id)
        
        return jsonify({
            'success': True,
            'instrumentos': instrumentos,
            'total': len(instrumentos)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



def parse_comando(comando):
    """Identifica quais campos extrair baseado no comando"""
    comando = comando.lower()

    # Lista de comandos de extração total
    if any(palavra in comando for palavra in ['tudo', 'todos', 'completo', 'todos os campos']):
        return 'tudo'

    # Mapeia palavras-chave para campos
    mapa_campos = {
        'identificacao': ['identificacao', 'identificação', 'tag', 'codigo', 'código', 'id'],
        'nome': ['nome', 'denominacao', 'denominação', 'instrumento'],
        'fabricante': ['fabricante', 'marca'],
        'modelo': ['modelo', 'model'],
        'numero_serie': ['numero serie', 'número série', 'serie', 'série', 'serial'],
        'descricao': ['descricao', 'descrição'],
        'responsavel': ['responsavel', 'responsável', 'cliente'],
        'departamento': ['departamento', 'endereco', 'endereço', 'local'],
        'data_calibracao': ['data', 'calibracao', 'calibração']
    }

    campos_encontrados = []
    for campo, palavras_chave in mapa_campos.items():
        if any(palavra in comando for palavra in palavras_chave):
            campos_encontrados.append(campo)

    return campos_encontrados if campos_encontrados else 'tudo'


def filtrar_campos(instrumentos, campos):
    """Filtra apenas os campos solicitados"""
    if campos == 'tudo':
        return instrumentos

    instrumentos_filtrados = []
    for inst in instrumentos:
        inst_filtrado = {campo: inst.get(campo, 'n/i') for campo in campos}
        # Sempre inclui grandezas e arquivo_origem (para mostrar nome do PDF)
        inst_filtrado['grandezas'] = inst.get('grandezas', [])
        inst_filtrado['arquivo_origem'] = inst.get('arquivo_origem', 'n/i')
        instrumentos_filtrados.append(inst_filtrado)

    return instrumentos_filtrados


def gerar_preview(instrumentos):
    """Gera um preview COMPLETO dos dados extraídos"""
    if not instrumentos:
        return "Nenhum instrumento encontrado"

    preview_lines = []
    for idx, inst in enumerate(instrumentos, 1):  # Mostra TODOS os instrumentos
        preview_lines.append(f"\n{'='*60}")
        preview_lines.append(f"📄 INSTRUMENTO {idx}: {inst.get('arquivo_origem', 'n/i')}")
        preview_lines.append(f"{'='*60}")
        
        # DADOS PRINCIPAIS
        preview_lines.append(f"\n🔖 IDENTIFICAÇÃO E DADOS BÁSICOS:")
        preview_lines.append(f"  • Identificação/Tag: {inst.get('identificacao', 'n/i')}")
        preview_lines.append(f"  • Nome: {inst.get('nome', 'n/i')}")
        preview_lines.append(f"  • Descrição: {inst.get('descricao', 'n/i')}")
        preview_lines.append(f"  • Tipo/Família: {inst.get('tipo_familia', 'n/i')}")
        
        # FABRICANTE E MODELO
        preview_lines.append(f"\n🏭 FABRICANTE E MODELO:")
        preview_lines.append(f"  • Fabricante: {inst.get('fabricante', 'n/i')}")
        preview_lines.append(f"  • Modelo: {inst.get('modelo', 'n/i')}")
        preview_lines.append(f"  • Número de Série: {inst.get('numero_serie', 'n/i')}")
        
        # RESPONSÁVEL E LOCALIZAÇÃO
        preview_lines.append(f"\n👤 RESPONSÁVEL E LOCALIZAÇÃO:")
        preview_lines.append(f"  • Responsável/Cliente: {inst.get('responsavel', 'n/i')}")
        preview_lines.append(f"  • Departamento/Local: {inst.get('departamento', 'n/i')}")
        
        # DATAS E PERIODICIDADE
        preview_lines.append(f"\n📅 DATAS E PERIODICIDADE:")
        preview_lines.append(f"  • Data de Calibração: {inst.get('data_calibracao', 'n/i')}")
        preview_lines.append(f"  • Data de Emissão: {inst.get('data_emissao', 'n/i')}")
        preview_lines.append(f"  • Periodicidade: {inst.get('periodicidade', 'n/i')} meses")
        
        # STATUS E CONTROLE
        preview_lines.append(f"\n⚙️ STATUS E CONTROLE:")
        preview_lines.append(f"  • Status: {inst.get('status', 'n/i')}")
        preview_lines.append(f"  • Quantidade: {inst.get('quantidade', 'n/i')}")
        preview_lines.append(f"  • Motivo Calibração: {inst.get('motivo_calibracao', 'n/i')}")
        preview_lines.append(f"  • Criticidade: {inst.get('criticidade', 'n/i')}")
        preview_lines.append(f"  • Série Desenv.: {inst.get('serie_desenv', 'n/i')}")
        
        # GRANDEZAS
        grandezas = inst.get('grandezas', [])
        if grandezas:
            preview_lines.append(f"\n📊 GRANDEZAS ({len(grandezas)}):")
            for g_idx, grandeza in enumerate(grandezas, 1):
                preview_lines.append(f"\n  Grandeza {g_idx}:")
                preview_lines.append(f"    • Unidade: {grandeza.get('unidade', 'n/i')}")
                preview_lines.append(f"    • Faixa Nominal: {grandeza.get('faixa_nominal', 'n/i')}")
                preview_lines.append(f"    • Faixa de Uso: {grandeza.get('faixa_uso', 'n/i')}")
                preview_lines.append(f"    • Tolerância Processo: {grandeza.get('tolerancia_processo', 'n/i')}")
                preview_lines.append(f"    • Tolerância Simétrica: {grandeza.get('tolerancia_simetrica', 'n/i')}")
                preview_lines.append(f"    • Resolução: {grandeza.get('resolucao', 'n/i')}")
                preview_lines.append(f"    • Critério Aceitação: {grandeza.get('criterio_aceitacao', 'n/i')}")
                preview_lines.append(f"    • Classe/Norma: {grandeza.get('classe_norma', 'n/i')}")
                preview_lines.append(f"    • Classificação: {grandeza.get('classificacao', 'n/i')}")
                preview_lines.append(f"    • Regra Decisão ID: {grandeza.get('regra_decisao_id', 'n/i')}")
                
                servicos = grandeza.get('servicos', [])
                if servicos:
                    preview_lines.append(f"    • Serviços/Pontos ({len(servicos)}): {', '.join(map(str, servicos[:3]))}{' ...' if len(servicos) > 3 else ''}")

    return "\n".join(preview_lines)


if __name__ == '__main__':
    print("\n" + "="*60)
    print(">> Servidor do Extrator de Certificados iniciado!")
    print("="*60)
    print("\n>> Acesse: http://localhost:5000")
    print("\n>> Pressione Ctrl+C para parar o servidor\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
