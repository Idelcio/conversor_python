"""
METRON - Extrator OpenAI Vision + Banco de Dados
Funcionalidades:
- Extracao de PDFs com GPT-4o Vision (OCR inteligente)
- Chat livre com OpenAI
- Insercao no MySQL
- Visualizacao do banco
"""

from flask import Flask, render_template, request, jsonify, session, Response
from flask_cors import CORS
import os
import tempfile
from werkzeug.utils import secure_filename
import concurrent.futures
import threading
import uuid
import json
import mysql.connector
from datetime import datetime

# Carrega variaveis de ambiente do .env
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from openai import OpenAI

# Importa extrator OpenAI Vision
from openai_extractor.extractor import OpenAIExtractor
try:
    from openai_extractor.gemini_adapter import GeminiAdapter
except ImportError:
    GeminiAdapter = None
from openai_extractor.security import SecurityValidator
from openai_extractor.prompts import SYSTEM_PROMPT

# ============================================================
# CONFIGURACAO FLASK
# ============================================================
app = Flask(__name__)
CORS(app)
app.secret_key = 'gocal-secret-key-2026'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# ============================================================
# CONFIGURACAO MYSQL
# ============================================================
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'laboratorios',
    'user': 'root',
    'password': ''
}

# ============================================================
# INICIALIZACAO
# ============================================================
try:
    if os.getenv('GOOGLE_API_KEY') and GeminiAdapter:
        print("[INIT] 🚀 Iniciando com MODO GEMINI (Google)...")
        extractor = GeminiAdapter()
    else:
        print("[INIT] Iniciando com OpenAI...")
        extractor = OpenAIExtractor()
except Exception as e:
    print(f"[ERRO] Falha ao inicializar Extrator: {e}")
    extractor = None

validator = SecurityValidator()
extracted_cache = {}  # Cache: {session_id: [dados_extraidos]}
processing_tasks = {} # Cache de tarefas assincronas {task_id: status}


# ============================================================
# ROTAS - PAGINAS
# ============================================================
@app.route('/')
def index():
    """Pagina principal do Chat"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Captura parametros de integracao (vindo do ERP/Gocal)
    # Ex: /?user_id=55&token=xyz
    integration_data = {
        'user_id': request.args.get('user_id'),
        'token': request.args.get('token'),
        'empresa_id': request.args.get('empresa_id')
    }
    
    # Se vier user_id, salva na sessao para uso futuro
    if integration_data['user_id']:
        session['gocal_user_id'] = integration_data['user_id']

    return render_template('gocal_chat.html', integration=integration_data)


@app.route('/visualizar')
def visualizar():
    """Pagina de visualizacao de instrumentos"""
    return render_template('visualizar.html')


# ============================================================
# ROTAS - OPENAI (Extracao e Chat)
# ============================================================
@app.route('/chat-extrair', methods=['POST'])
def chat_extrair():
    """Processa PDFs com GPT-4o Vision e responde perguntas"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    session_id = session['session_id']
    files = request.files.getlist('pdfs')
    message = request.form.get('comando', '') or request.form.get('message', '')

    print(f"\n{'='*60}")
    print(f"[CHAT] OpenAI Vision - Session: {session_id[:8]}...")
    print(f"{'='*60}")

    # 1. Se tem PDFs, processa com GPT-4o Vision
    if files and files[0].filename:
        if not extractor:
            return jsonify({'success': False, 'message': 'Erro: API OpenAI nao configurada.'})

        instrumentos = []
        temp_files = []

        # 1. Salva todos os arquivos temporariamente
        for file in files:
            filename = secure_filename(file.filename)
            is_valid, error = validator.validate_pdf(filename)
            if not is_valid:
                continue
            
            # Gera nome unico para evitar colisao em paralelo
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(temp_path)
            temp_files.append((temp_path, filename))

        # 2. Funcao de processamento individual
        def process_single_pdf(args):
            path, original_name = args
            print(f"[PDF-THREAD] Iniciando: {original_name}")
            try:
                res = extractor.extract_from_pdf(path, original_name)
                # Remove arquivo logo apos processar
                try:
                    os.remove(path)
                except:
                    pass
                return res
            except Exception as e:
                print(f"[ERRO-THREAD] {original_name}: {e}")
                return {'error': str(e)}

        # 3. Executa em paralelo (max 5 threads para evitar Rate Limit excessivo)
        print(f"[PARALELO] Iniciando extracao de {len(temp_files)} arquivos...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_single_pdf, temp_files))

        # 4. Coleta resultados validos
        for dados in results:
            if dados and 'error' not in dados:
                instrumentos.append(dados)
                print(f"[OK] Extraido: {dados.get('identificacao', 'n/i')}")
            else:
                print(f"[ERRO] Falha na extracao: {dados.get('error') if dados else 'Desconhecido'}")


        if instrumentos:
            extracted_cache[session_id] = instrumentos
            
            # Gera resumo em texto para o chat
            resumo_msg = f"✅ **{len(instrumentos)} documento(s) analisado(s)!**\n\n"
            for i, inst in enumerate(instrumentos):
                ident = inst.get('identificacao') or inst.get('numero_certificado') or 'S/N'
                nome = inst.get('nome') or inst.get('instrumento') or 'Instrumento'
                resumo_msg += f"{i+1}. **{ident}** - {nome}\n"
            
            # Adiciona aviso de erro se houve falhas
            falhas = len(files) - len(instrumentos)
            if falhas > 0:
                resumo_msg += f"\n⚠️ {falhas} arquivo(s) não foram processados (erro ou segurança)."

            return jsonify({
                'success': True,
                'message': resumo_msg,
                'instrumentos': instrumentos
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Falha ao analisar o PDF. Verifique se e um documento valido.'
            })

    # 2. Se e mensagem de texto, usa chat OpenAI
    if message:
        print(f"[MSG] {message}")

        dados = extracted_cache.get(session_id, [])

        # Comando especial para mostrar dados
        if dados and ('extrair tudo' in message.lower() or 'mostrar tudo' in message.lower()):
            return jsonify({
                'success': True,
                'message': 'Dados extraidos:',
                'instrumentos': dados
            })

        # Chat livre com OpenAI
        try:
            contexto = ""
            if dados:
                contexto = f"\n\nDADOS EXTRAIDOS:\n{json.dumps(dados, ensure_ascii=False, indent=2)}"

            prompt = f"""Voce e o Metron, um assistente inteligente.

PERGUNTA: "{message}"
{contexto}

Responda de forma direta e util."""

            # Lógica Hibrida (Gemini ou OpenAI)
            if hasattr(extractor, 'ask'):
                resposta = extractor.ask(prompt)
            else:
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ]
                )

                resposta = completion.choices[0].message.content
            return jsonify({'success': True, 'message': resposta})

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                return jsonify({'success': True, 'message': '⏳ **Sistema sobrecarregado.** Atingimos o limite de velocidade da IA. Por favor, aguarde 15 segundos e tente novamente.'})
            
            print(f"[ERRO] Chat: {e}")
            return jsonify({'success': True, 'message': f'Ocorreu um erro ao processar: {error_msg}'})

    return jsonify({'success': False, 'message': 'Envie uma mensagem ou um PDF.'})


@app.route('/chat-mensagem', methods=['POST'])
def chat_mensagem():
    """Rota exclusiva para chat de texto (sem upload)"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    data = request.get_json()
    message = data.get('message', '')
    
    print(f"[CHAT-MSG] Session: {session_id[:8]}... Msg: {message}")
    
    dados = extracted_cache.get(session_id, [])

    # Se usuario pedir explicitamente para ver os dados completos
    if dados and ('mostrar tudo' in message.lower() or 'ver dados' in message.lower()):
        return jsonify({
            'success': True,
            'message': 'Aqui estão os dados extraídos:',
            'instrumentos': dados
        })
        
    # Comando para limpar sessao
    if 'limpar' in message.lower() or 'nova sessao' in message.lower() or 'novo arquivo' in message.lower():
        if session_id in extracted_cache:
            del extracted_cache[session_id]
        return jsonify({'success': True, 'message': 'Sessão limpa! Pode enviar um novo arquivo.'})

    # Chat normal com GPT-4o
    try:
        contexto = ""
        if dados:
            # Limita o contexto para nao estourar tokens se for muito grande
            json_str = json.dumps(dados, ensure_ascii=False, indent=2)
            if len(json_str) > 20000:
                json_str = json_str[:20000] + "... (troncado)"
            contexto = f"\n\nDADOS DO DOCUMENTO (Contexto):\n{json_str}"

        # Rotas mapeadas da aplicacao
        APP_ROUTES = {
            "Dashboard": "/monitoramento",
            "Monitoramento": "/monitoramento",
            "Instrumentos": "/instrumentos",
            "Listar Instrumentos": "/instrumentos",
            "Novo Instrumento": "/instrumentos/create",
            "Laboratorios": "/laboratorios",
            "Listar Laboratorios": "/laboratorios",
            "Calibracoes": "/calibracoes",
            "Listar Calibracoes": "/calibracoes",
            "Nova Calibracao": "/calibracoes/create", 
            "Perfil": "/profile",
            "Assinatura": "/profile/signature",
            "Favoritos": "/favoritos",
        }

        prompt = f"""Voce e o Metron (Assistente Labster).
        
DADOS ANEXADOS:
{contexto}

ROTAS DA APLICACAO (Use se o usuario pedir para ir):
{json.dumps(APP_ROUTES, indent=2)}

USUARIO: "{message}"

INSTRUCOES:
1. Responda a pergunta do usuario com base nos dados.
2. Se o usuario pedir para NAVEGAR para alguma tela (ex: "ir para instrumentos"), sua resposta DEVE SER um JSON puro no formato: 
   {{"message": "Indo para instrumentos...", "navigate_to": "/instrumentos"}}
3. Se for uma pergunta normal, responda apenas texto.
4. NAO use JSON se nao for navegacao.
"""

        if hasattr(extractor, 'ask'):
             resposta = extractor.ask(prompt)
        else:
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )

            resposta = completion.choices[0].message.content
        
        # Tenta parsear se a IA mandou um JSON (Navegacao ou Checklist)
        try:
            # Limpa backticks se a IA colocou ```json ... ```
            clean_resp = resposta.replace('```json', '').replace('```', '').strip()
            
            # Tenta carregar como JSON
            if clean_resp.startswith('{'):
                resp_json = json.loads(clean_resp)
                
                # Caso 1: Navegação
                if 'navigate_to' in resp_json:
                    return jsonify({
                        'success': True, 
                        'message': resp_json.get('message', 'Redirecionando...'),
                        'redirect_url': resp_json['navigate_to']
                    })
                
                # Caso 2: Checklist Automático
                if 'checklist_data' in resp_json:
                     return jsonify({
                        'success': True,
                        'message': resp_json.get('message', 'Checklist verificado!'),
                        'auto_checklist': resp_json['checklist_data']
                    })
        except:
            pass # Nao e JSON, segue normal

        return jsonify({'success': True, 'message': resposta})

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
             return jsonify({'success': True, 'message': '⏳ **Muitas requisições.** Estamos operando no limite da IA. Aguarde alguns segundos e tente de novo.'})

        print(f"[ERRO] Chat Msg: {e}")
        return jsonify({'success': False, 'message': f'Erro técnico: {error_msg}'})


@app.route('/limpar-cache', methods=['POST'])
def limpar_cache():
    """Limpa o cache de dados extraidos da sessao atual"""
    if 'session_id' not in session:
        return jsonify({'success': False, 'message': 'Nenhuma sessao ativa.'})
    
    session_id = session['session_id']
    
    if session_id in extracted_cache:
        del extracted_cache[session_id]
        print(f"[CACHE] Sessao {session_id[:8]}... limpa.")
    
    return jsonify({'success': True, 'message': 'Cache limpo com sucesso.'})


@app.route('/upload-async', methods=['POST'])
def upload_async():
    """Recebe arquivos e inicia processamento em background, retornando task_id"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    
    files = request.files.getlist('pdfs')
    pdf_url = request.form.get('pdf_url') # Novo parametro
    comando = request.form.get('comando')

    has_files = (files and files[0].filename) or pdf_url
    if not has_files:
        return jsonify({'success': False, 'message': 'Sem arquivos ou URL'})
        
    task_id = str(uuid.uuid4())
    temp_files_info = [] # (path, name)
    
    # Inicializa status da task
    processing_tasks[task_id] = {
        'status': 'starting',
        'total': 1 if pdf_url else len(files),
        'completed': 0,
        'files': {}, # {filename: status}
        'results': []
    }
    
    try:
        # 1. Se veio URL, faz download
        if pdf_url:
            import requests
            try:
                # Nome do arquivo da URL ou padrao
                fname = pdf_url.split('/')[-1] or "documento_web.pdf"
                if not fname.lower().endswith('.pdf'): fname += '.pdf'
                
                unique = f"{uuid.uuid4().hex}_{fname}"
                path = os.path.join(app.config['UPLOAD_FOLDER'], unique)
                
                # Download
                response = requests.get(pdf_url, stream=True, verify=False) # verify=False para local/dev
                if response.status_code == 200:
                    with open(path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    
                    temp_files_info.append((path, fname))
                    processing_tasks[task_id]['files'][fname] = 'pending'
                else:
                    return jsonify({'success': False, 'message': f'Erro ao acessar URL: {response.status_code}'})
            except Exception as e:
                return jsonify({'success': False, 'message': f'Falha no download: {e}'})

        # 2. Se veio Arquivos (Upload normal)
        if files and files[0].filename:
            for file in files:
                fname = secure_filename(file.filename)
                unique = f"{uuid.uuid4().hex}_{fname}"
                path = os.path.join(app.config['UPLOAD_FOLDER'], unique)
                file.save(path)
                temp_files_info.append((path, fname))
                processing_tasks[task_id]['files'][fname] = 'pending'
            
            # Recalcula total real
            processing_tasks[task_id]['total'] = len(temp_files_info)
            
        # Funcao Worker (Background)
        def run_job(tid, files_info, sid, user_cmd):
            try:
                 processing_tasks[tid]['status'] = 'running'
                 instrumentos = []
                 
                 def process_one(args):
                     p, n = args
                     processing_tasks[tid]['files'][n] = 'processing'
                     try:
                         # Extrai
                         res = extractor.extract_from_pdf(p, n, user_prompt=user_cmd)
                         try: os.remove(p)
                         except: pass
                         
                         if res and 'error' not in res:
                             processing_tasks[tid]['files'][n] = 'done'
                             return res
                         else:
                             processing_tasks[tid]['files'][n] = 'error'
                             return None
                     except:
                         processing_tasks[tid]['files'][n] = 'error'
                         return None
                 
                 # Paralelismo
                 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                     # Usa as_completed para atualizar contador realtime? 
                     # Ou map simples. Map é mais facil de coletar ordem, mas as_completed é melhor pra progresso.
                     future_to_file = {executor.submit(process_one, f): f[1] for f in files_info}
                     
                     for future in concurrent.futures.as_completed(future_to_file):
                         res = future.result()
                         processing_tasks[tid]['completed'] += 1
                         if res:
                             instrumentos.append(res)
                
                 # Salva no Cache da Sessao
                 if sid not in extracted_cache: extracted_cache[sid] = []
                 extracted_cache[sid].extend(instrumentos)
                 
                 processing_tasks[tid]['results'] = instrumentos
                 processing_tasks[tid]['status'] = 'completed'
                 print(f"[TASK] {tid} concluida. {len(instrumentos)} itens.")
                 
            except Exception as e:
                 print(f"[TASK-ERR] {e}")
                 processing_tasks[tid]['status'] = 'error'

        # Lança thread solta
        threading.Thread(target=run_job, args=(task_id, temp_files_info, session_id, comando)).start()
        
        return jsonify({'success': True, 'task_id': task_id})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/upload-status/<task_id>')
def check_status(task_id):
    """Retorna o status do processamento assincrono"""
    return jsonify(processing_tasks.get(task_id, {'status': 'not_found'}))



# ============================================================
# ROTAS - BANCO DE DADOS (MySQL)
# ============================================================
# Normalização de Status para o padrão do Gocal
def normalizar_status(valor):
    if not valor:
        return 'Sem Calibracao'
    
    v = valor.lower().strip()
    
    # Mapa de correlações
    if 'pendente' in v or 'aprovacao' in v:
        return 'Pendente Aprovação'
    if 'inativo' in v:
        return 'Inativo'
    if 'manutencao' in v:
        return 'Em Manutenção'
    if 'sem' in v or 'calibracao' in v: # Default se contiver calibração
        return 'Sem Calibração'
    if 'em calibracao' in v:
        return 'Em Calibração'
        
    # Default
    return 'Sem Calibração'

@app.route('/inserir-banco', methods=['POST'])
def inserir_banco():
    """Insere instrumentos extraidos no MySQL"""
    try:
        data = request.get_json()
        user_id = int(data.get('user_id', 1))

        if 'session_id' not in session:
            # Em modo widget/iframe, a sessao pode se perder. 
            # Aceitamos a insercao se vier com dados validos mesmo sem sessao.
            pass

        # session_id = session['session_id'] # Nao obrigatorio
        session_id = session.get('session_id') # Usa .get para evitar erro se nao existir
        
        # Prioriza os dados enviados pelo frontend
        instrumentos = data.get('instrumentos', [])
        
        # Fallback para cache apenas se tiver sessao valida
        if not instrumentos and session_id:
             instrumentos = extracted_cache.get(session_id, [])

        if not instrumentos:
            return jsonify({'success': False, 'message': 'Nenhum instrumento para inserir.'}), 400

        print(f"[DB] Inserindo {len(instrumentos)} instrumento(s) (user_id={user_id})")

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        total_inseridos = 0
        total_ignorados = 0
        total_grandezas = 0

        for inst in instrumentos:
            if isinstance(inst, str):
                try:
                    inst = json.loads(inst)
                except:
                    print(f"[AVISO] Item ignorado nao e JSON valido: {inst}")
                    continue
            
            if not isinstance(inst, dict):
                continue

            # Funcao auxiliar para buscar valor em qualquer nivel do JSON
            def buscar_valor(chave, dados_json, default=None):
                if isinstance(dados_json, dict):
                    if chave in dados_json:
                        return dados_json[chave]
                    for v in dados_json.values():
                        res = buscar_valor(chave, v, default=None)
                        if res is not None:
                            return res
                return default

            # Tenta encontrar campos chaves em qualquer lugar
            identificacao = buscar_valor('identificacao', inst) or \
                            buscar_valor('numero_certificado', inst) or \
                            buscar_valor('tag', inst) or \
                            buscar_valor('codigo', inst) or 'n/i'

            # Verifica duplicata
            cursor.execute(
                "SELECT id FROM instrumentos WHERE identificacao = %s AND user_id = %s LIMIT 1",
                (identificacao, user_id)
            )
            if cursor.fetchone():
                total_ignorados += 1
                continue
            
            # Mapeia campos principais procurando recursivamente ou usando defaults
            nome = buscar_valor('nome', inst) or buscar_valor('instrumento', inst) or buscar_valor('titulo', inst) or 'n/i'
            fabricante = buscar_valor('fabricante', inst) or 'n/i'
            modelo = buscar_valor('modelo', inst) or 'n/i'
            numero_serie = buscar_valor('numero_serie', inst) or buscar_valor('serie', inst) or 'n/i'
            descricao = buscar_valor('descricao', inst) or json.dumps(inst, ensure_ascii=False)[:500]
            periodicidade = buscar_valor('periodicidade', inst, 12)
            departamento = buscar_valor('departamento', inst) or buscar_valor('cliente', inst) or buscar_valor('localizacao', inst) or 'n/i'
            responsavel = buscar_valor('responsavel', inst) or buscar_valor('solicitante', inst) or 'n/i'
            
            # Normaliza Status
            status_bruto = buscar_valor('status', inst, 'Sem Calibracao')
            status = normalizar_status(status_bruto)
            
            tipo_familia = buscar_valor('tipo_familia', inst) or buscar_valor('tipo_documento', inst) or 'n/i'
            serie_desenv = buscar_valor('serie_desenv', inst) or buscar_valor('desenho', inst) or 'n/i'
            criticidade = buscar_valor('criticidade', inst) or 'B' # Default B = Baixa/Normal
            motivo_calibracao = buscar_valor('motivo_calibracao', inst, 'Calibracao Periodica')
            # quantidade = buscar_valor('quantidade', inst, 1)

            sql = """
                INSERT INTO instrumentos (
                    identificacao, nome, fabricante, modelo, numero_serie, descricao,
                    periodicidade, departamento, responsavel, status, tipo_familia,
                    serie_desenv, criticidade, motivo_calibracao, quantidade,
                    user_id, responsavel_cadastro_id, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """

            valores = (
                identificacao, nome, fabricante, modelo, numero_serie, descricao,
                periodicidade, departamento, responsavel, status, tipo_familia,
                serie_desenv, criticidade, motivo_calibracao, 1,
                user_id, user_id
            )

            cursor.execute(sql, valores)
            instrumento_id = cursor.lastrowid
            total_inseridos += 1

            # Busca grandezas (Simplificado como solicitado)
            # Tenta pegar direto da chave 'grandezas' ou 'tabelas'
            lista_grandezas = buscar_valor('grandezas', inst) or buscar_valor('tabelas', inst) or []
            
            if not isinstance(lista_grandezas, list):
                lista_grandezas = []

            for grandeza in lista_grandezas:
                # Mapeia campos da grandeza 
                def get_g(key, default=None):
                    # Tenta direto, depois tenta recursivo se for dict
                    val = grandeza.get(key)
                    if val is None and isinstance(grandeza, dict):
                         # Pequeno helper local para buscar em profundidade rasa
                         for k, v in grandeza.items():
                             if isinstance(v, dict) and key in v:
                                 return v[key]
                    return val or default

                sql_g = """
                    INSERT INTO grandezas (
                        instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica,
                        unidade, resolucao, criterio_aceitacao, regra_decisao_id,
                        faixa_nominal, classe_norma, classificacao, faixa_uso,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                
                tolerancia = get_g('tolerancia_processo') or get_g('tolerancia') or get_g('erro_maximo')
                unidade = get_g('unidade')
                resolucao = get_g('resolucao')
                faixa_nominal = get_g('faixa_nominal') or get_g('faixa') or get_g('valor_nominal')

                
                valores_g = (
                    instrumento_id,
                    json.dumps(get_g('servicos', []) if isinstance(get_g('servicos'), list) else []),
                    tolerancia,
                    get_g('tolerancia_simetrica', True),
                    unidade,
                    resolucao,
                    get_g('criterio_aceitacao'),
                    get_g('regra_decisao_id', 1),
                    faixa_nominal,
                    get_g('classe_norma'),
                    get_g('classificacao'),
                    get_g('faixa_uso')
                )
                cursor.execute(sql_g, valores_g)
                total_grandezas += 1

        conn.commit()
        cursor.close()
        conn.close()

        # Limpa cache
        if session_id in extracted_cache:
            del extracted_cache[session_id]

        msg = f'Inseridos {total_inseridos} instrumento(s)!'
        if total_ignorados > 0:
            msg += f' ({total_ignorados} duplicata(s) ignorada(s))'

        return jsonify({
            'success': True,
            'message': msg,
            'inseridos': total_inseridos,
            'ignorados': total_ignorados,
            'grandezas': total_grandezas
        })

    except mysql.connector.Error as e:
        print(f"[ERRO] MySQL: {e}")
        return jsonify({'success': False, 'message': f'Erro MySQL: {str(e)}'}), 500

    except Exception as e:
        print(f"[ERRO] {e}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


@app.route('/listar-instrumentos', methods=['GET'])
@app.route('/api/instrumentos', methods=['GET'])
def listar_instrumentos():
    """Lista instrumentos do banco de dados"""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        limite = request.args.get('limite', 100, type=int)

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, identificacao, nome, fabricante, modelo, numero_serie,
                   status, created_at, departamento, responsavel, periodicidade
            FROM instrumentos
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limite))

        instrumentos = cursor.fetchall()
        
        # Busca a ultima calibracao para cada instrumento
        # (Logica simplificada: assume data de hoje se status for aprovado, ou busca de outra tabela se existisse)
        # Neste caso, vamos adicionar campos que o frontend espera
        for inst in instrumentos:
            if inst.get('created_at'):
                inst['data_calibracao'] = inst['created_at'].strftime('%d/%m/%Y')
                inst['created_at'] = inst['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            # Busca grandezas basicas para mostrar na lista
            cursor.execute("SELECT unidade, resolucao, tolerancia_processo FROM grandezas WHERE instrumento_id = %s LIMIT 1", (inst['id'],))
            grandeza = cursor.fetchone()
            if grandeza:
                inst['grandezas'] = [grandeza]

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'total': len(instrumentos),
            'instrumentos': instrumentos
        })

    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': f'Erro MySQL: {str(e)}'}), 500


@app.route('/api/instrumentos/<int:instrumento_id>', methods=['DELETE'])
def deletar_instrumento(instrumento_id):
    """Deleta um instrumento"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Deleta grandezas primeiro (FK)
        cursor.execute("DELETE FROM grandezas WHERE instrumento_id = %s", (instrumento_id,))
        
        # Deleta instrumento
        cursor.execute("DELETE FROM instrumentos WHERE id = %s", (instrumento_id,))
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Instrumento deletado com sucesso'})

    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': f'Erro MySQL: {str(e)}'}), 500


@app.route('/buscar-instrumento/<int:instrumento_id>', methods=['GET'])
def buscar_instrumento(instrumento_id):
    """Busca detalhes de um instrumento especifico com grandezas"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Busca instrumento
        cursor.execute("SELECT * FROM instrumentos WHERE id = %s", (instrumento_id,))
        instrumento = cursor.fetchone()

        if not instrumento:
            return jsonify({'success': False, 'message': 'Instrumento nao encontrado'}), 404

        # Converte datetime
        for key in ['created_at', 'updated_at']:
            if instrumento.get(key):
                instrumento[key] = instrumento[key].strftime('%Y-%m-%d %H:%M:%S')

        # Busca grandezas
        cursor.execute("SELECT * FROM grandezas WHERE instrumento_id = %s", (instrumento_id,))
        grandezas = cursor.fetchall()

        for g in grandezas:
            for key in ['created_at', 'updated_at']:
                if g.get(key):
                    g[key] = g[key].strftime('%Y-%m-%d %H:%M:%S')
            if g.get('servicos'):
                try:
                    g['servicos'] = json.loads(g['servicos'])
                except:
                    pass

        instrumento['grandezas'] = grandezas

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'instrumento': instrumento})

    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': f'Erro MySQL: {str(e)}'}), 500


@app.route('/gerar-sql', methods=['POST'])
def gerar_sql():
    """Gera arquivo SQL com os dados inseridos"""
    try:
        data = request.get_json()
        instrumentos = data.get('instrumentos', [])
        
        if not instrumentos:
            return jsonify({'success': False, 'message': 'Nenhum instrumento para gerar SQL.'}), 400

        sql_lines = []
        sql_lines.append("-- Gerado pelo Metron")
        sql_lines.append(f"-- Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sql_lines.append("USE instrumentos;")
        sql_lines.append("")

        user_id = data.get('user_id', 1)

        def escape(val):
            if val is None: return 'NULL'
            if isinstance(val, (int, float)): return str(val)
            if isinstance(val, bool): return 'TRUE' if val else 'FALSE'
            return "'" + str(val).replace("'", "''").replace("\\", "\\\\") + "'"

        for inst in instrumentos:
            identificacao = inst.get('identificacao') or inst.get('dados_principais', {}).get('numero_certificado', 'n/i')
            
            # Dados Principais
            dados_principais = inst.get('dados_principais', {})
            
            # Mapeamento de campos
            val_ident = escape(identificacao)
            val_nome = escape(inst.get('nome') or dados_principais.get('instrumento') or inst.get('titulo'))
            val_fab = escape(inst.get('fabricante') or dados_principais.get('fabricante'))
            val_mod = escape(inst.get('modelo') or dados_principais.get('modelo'))
            val_ns = escape(inst.get('numero_serie') or dados_principais.get('numero_serie'))
            val_desc = escape(inst.get('descricao') or json.dumps(inst, ensure_ascii=False)[:500])
            val_period = escape(inst.get('periodicidade', 12))
            val_dep = escape(inst.get('departamento') or dados_principais.get('cliente'))
            val_resp = escape(inst.get('responsavel') or dados_principais.get('solicitante'))
            val_status = escape(inst.get('status', 'Sem Calibracao'))
            val_tipo = escape(inst.get('tipo_familia') or inst.get('tipo_documento'))
            val_serie = escape(inst.get('serie_desenv'))
            val_crit = escape(inst.get('criticidade'))
            val_motivo = escape(inst.get('motivo_calibracao', 'Calibracao Periodica'))
            val_qtd = escape(inst.get('quantidade', 1))
            val_uid = escape(user_id)

            sql_lines.append(f"""
INSERT INTO instrumentos (
    identificacao, nome, fabricante, modelo, numero_serie, descricao,
    periodicidade, departamento, responsavel, status, tipo_familia,
    serie_desenv, criticidade, motivo_calibracao, quantidade,
    user_id, responsavel_cadastro_id, created_at, updated_at
) VALUES (
    {val_ident}, {val_nome}, {val_fab}, {val_mod}, {val_ns}, {val_desc},
    {val_period}, {val_dep}, {val_resp}, {val_status}, {val_tipo},
    {val_serie}, {val_crit}, {val_motivo}, {val_qtd},
    {val_uid}, {val_uid}, NOW(), NOW()
);""")
            
            # Variavel para ID
            sql_lines.append("SET @inst_id = LAST_INSERT_ID();")

            # Grandezas
            grandezas = inst.get('grandezas', []) or inst.get('tabelas', [])
            if grandezas:
                for grandeza in grandezas:
                     val_servs = escape(json.dumps(grandeza.get('servicos', []) if isinstance(grandeza.get('servicos'), list) else []))
                     val_tol = escape(grandeza.get('tolerancia_processo'))
                     val_sim = 'TRUE' if grandeza.get('tolerancia_simetrica', True) else 'FALSE'
                     val_uni = escape(grandeza.get('unidade'))
                     val_res = escape(grandeza.get('resolucao'))
                     val_crit_g = escape(grandeza.get('criterio_aceitacao'))
                     val_regra = escape(grandeza.get('regra_decisao_id', 1))
                     val_faixa = escape(grandeza.get('faixa_nominal'))
                     val_classe = escape(grandeza.get('classe_norma'))
                     val_classif = escape(grandeza.get('classificacao'))
                     val_fuso = escape(grandeza.get('faixa_uso'))

                     sql_lines.append(f"""INSERT INTO grandezas (
    instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica,
    unidade, resolucao, criterio_aceitacao, regra_decisao_id,
    faixa_nominal, classe_norma, classificacao, faixa_uso,
    created_at, updated_at
) VALUES (
    @inst_id, {val_servs}, {val_tol}, {val_sim},
    {val_uni}, {val_res}, {val_crit_g}, {val_regra},
    {val_faixa}, {val_classe}, {val_classif}, {val_fuso},
    NOW(), NOW()
);""")
            sql_lines.append("")

        # Retorna o arquivo
        return Response(
            "\n".join(sql_lines),
            mimetype="application/sql",
            headers={"Content-disposition": "attachment; filename=instrumentos.sql"}
        )

    except Exception as e:
        print(f"[ERRO] SQL Gen: {e}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


# ============================================================
# ROTAS - UTILIDADES
# ============================================================
@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'mode': 'openai_vision',
        'extractor': 'ok' if extractor else 'error'
    })


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("METRON - OpenAI Vision + MySQL")
    print("="*60)
    print("Acesse: http://localhost:5001")
    print("")
    print("Rotas disponiveis:")
    print("  GET  /                     - Chat interface")
    print("  POST /chat-extrair         - Extrai PDF com OpenAI Vision")
    print("  POST /inserir-banco        - Insere no MySQL")
    print("  POST /gerar-sql            - Gera SQL para download")
    print("  GET  /visualizar            - Interface Web de Visualizacao")
    print("  GET  /listar-instrumentos  - Lista instrumentos")
    print("  GET  /buscar-instrumento/N - Detalhes do instrumento N")
    print("  GET  /health               - Health check")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5001, debug=True)
