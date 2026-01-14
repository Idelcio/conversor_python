"""
Servidor Flask para interface web do Extrator de Certificados
"""

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import tempfile
from pathlib import Path
from extrator_pdf import ExtratorCertificado
from gerador_sql import GeradorSQL
import mysql.connector
import json

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    """Verifica se o arquivo é um PDF"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Página principal - Chat"""
    return render_template('index_chat.html')


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

        # Verifica se é um cumprimento
        is_cumprimento, resposta = responder_cumprimento(comando)
        if is_cumprimento:
            return jsonify({
                'success': True,
                'is_greeting': True,
                'message': resposta
            })

        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400

        # Salva arquivos temporariamente
        temp_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                temp_paths.append(filepath)

        # Processa PDFs
        extrator = ExtratorCertificado()
        instrumentos = extrator.processar_multiplos_pdfs(temp_paths)

        # Limpa arquivos temporários
        for path in temp_paths:
            try:
                os.remove(path)
            except:
                pass

        # Filtra campos baseado no comando
        campos_extrair = parse_comando(comando)
        if campos_extrair and campos_extrair != 'tudo':
            instrumentos = filtrar_campos(instrumentos, campos_extrair)

        # Gera preview
        preview = gerar_preview(instrumentos)

        return jsonify({
            'success': True,
            'message': f'✅ Extraídos {len(instrumentos)} instrumento(s) com sucesso!',
            'instrumentos': instrumentos,
            'preview': preview
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/inserir-banco', methods=['POST'])
def inserir_banco():
    """Insere instrumentos extraídos diretamente no banco"""
    try:
        data = request.get_json()
        instrumentos = data.get('instrumentos', [])
        user_id = int(data.get('user_id', 1))

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
        total_grandezas = 0

        for inst in instrumentos:
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
                inst.get('identificacao'),
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

        return jsonify({
            'success': True,
            'message': f'Inseridos {total_inseridos} instrumento(s) e {total_grandezas} grandeza(s) no banco!'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
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
    """Gera um preview dos dados extraídos"""
    if not instrumentos:
        return "Nenhum instrumento encontrado"

    preview_lines = []
    for idx, inst in enumerate(instrumentos[:3], 1):  # Mostra apenas os 3 primeiros
        preview_lines.append(f"Instrumento {idx}:")
        preview_lines.append(f"  • Identificação: {inst.get('identificacao', 'n/i')}")
        preview_lines.append(f"  • Nome: {inst.get('nome', 'n/i')}")
        preview_lines.append(f"  • Fabricante: {inst.get('fabricante', 'n/i')}")
        preview_lines.append(f"  • Modelo: {inst.get('modelo', 'n/i')}")
        preview_lines.append("")

    if len(instrumentos) > 3:
        preview_lines.append(f"... e mais {len(instrumentos) - 3} instrumento(s)")

    return "\n".join(preview_lines)


if __name__ == '__main__':
    print("\n" + "="*60)
    print(">> Servidor do Extrator de Certificados iniciado!")
    print("="*60)
    print("\n>> Acesse: http://localhost:5000")
    print("\n>> Pressione Ctrl+C para parar o servidor\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
