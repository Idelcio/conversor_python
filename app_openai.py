"""
METRON - Extrator OpenAI Vision + Banco de Dados
Funcionalidades:
- Extracao de PDFs com GPT-4o Vision (OCR inteligente)
- Chat livre com OpenAI
- Insercao no MySQL
- Visualizacao do banco
"""

from flask import Flask, render_template, request, jsonify, session, Response, send_file
from flask_cors import CORS
import os
import re
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
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_DATABASE', 'laboratorios'),
    'user': os.getenv('DB_USERNAME', 'root'),
    'password': os.getenv('DB_PASSWORD', '')
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

# Mapa de correcao de status (sem acento -> com acento)
STATUS_MAP = {
    'sem calibracao': 'Sem Calibração',
    'sem calibração': 'Sem Calibração',
    'pendente aprovacao': 'Pendente Aprovação',
    'pendente aprovação': 'Pendente Aprovação',
    'em calibracao': 'Em Calibração',
    'em calibração': 'Em Calibração',
    'em manutencao': 'Em Manutenção',
    'em manutenção': 'Em Manutenção',
    'inativo': 'Inativo',
}

def normalizar_status(status_raw):
    """Normaliza o status para o formato correto com acentos"""
    if not status_raw:
        return 'Sem Calibração'
    chave = status_raw.strip().lower()
    return STATUS_MAP.get(chave, status_raw)


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
        'funcionario_id': request.args.get('funcionario_id'),
        'token': request.args.get('token'),
        'empresa_id': request.args.get('empresa_id')
    }
    
    # Se vier user_id, salva na sessao para uso futuro
    if integration_data['user_id']:
        session['gocal_user_id'] = integration_data['user_id']
    if integration_data['funcionario_id']:
        session['gocal_funcionario_id'] = integration_data['funcionario_id']

    return render_template('gocal_chat.html', integration=integration_data)


@app.route('/visualizar')
def visualizar():
    """Pagina de visualizacao de instrumentos"""
    return render_template('visualizar.html')


@app.route('/lote')
def processamento_lote():
    """Pagina de processamento em lote de PDFs"""
    user_id = request.args.get('user_id') or session.get('gocal_user_id', '')
    funcionario_id = request.args.get('funcionario_id') or session.get('gocal_funcionario_id', '')
    user_name = ''
    if user_id:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM users WHERE id = %s LIMIT 1", (user_id,))
            row = cursor.fetchone()
            if row:
                user_name = row[0]
            cursor.close()
            conn.close()
        except Exception:
            pass
    return render_template('processamento_lote.html', user_id=user_id, funcionario_id=funcionario_id, user_name=user_name)


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

    # 2. Se é mensagem de texto, usa chat
    if message:
        print(f"[MSG] {message}")

        dados = extracted_cache.get(session_id, [])
        msg_lower = message.lower()

        # ── Comando: mostrar dados estruturados (cards) ──────────────────
        if dados and any(k in msg_lower for k in ['extrair tudo', 'mostrar tudo', 'mostrar dados', 'exibir dados']):
            return jsonify({'success': True, 'message': 'Dados extraidos:', 'instrumentos': dados})

        # ── Comando: mostrar tabelas de grandezas ─────────────────────────
        if dados and any(k in msg_lower for k in ['tabela', 'grandeza', 'resultado', 'mostrar tabela', 'ver tabela', 'listar tabela']):
            linhas = []
            for i, inst in enumerate(dados):
                nome = inst.get('nome') or inst.get('instrumento') or f'Instrumento {i+1}'
                tag  = inst.get('identificacao') or 'S/N'
                grandezas = inst.get('grandezas') or []
                linhas.append(f"### {i+1}. {nome} — `{tag}`\n")
                if grandezas:
                    linhas.append("| Faixa | Unidade | Resolução | Tolerância | Critério | Incerteza |")
                    linhas.append("|---|---|---|---|---|---|")
                    for g in grandezas:
                        def _v(k): return str(g.get(k) or '—')
                        linhas.append(f"| {_v('faixa_nominal')} | {_v('unidade')} | {_v('resolucao')} | {_v('tolerancia_processo')} | {_v('criterio_aceitacao')} | {_v('incerteza')} |")
                else:
                    linhas.append("_Sem grandezas registradas._")
                linhas.append("")

            tabela_md = "\n".join(linhas) if linhas else "Nenhum dado extraído ainda."
            return jsonify({'success': True, 'message': tabela_md})

        # ── Chat livre com OpenAI ─────────────────────────────────────────
        try:
            contexto = ""
            if dados:
                # Resumo compacto em vez de JSON bruto
                resumo = []
                for i, inst in enumerate(dados):
                    nome = inst.get('nome') or 'Instrumento'
                    tag  = inst.get('identificacao') or 'S/N'
                    cert = inst.get('numero_certificado') or '—'
                    lab  = inst.get('laboratorio_responsavel') or inst.get('laboratorio') or '—'
                    data = inst.get('data_calibracao') or '—'
                    n_g  = len(inst.get('grandezas') or [])
                    resumo.append(f"  {i+1}. {nome} (Tag: {tag}) | Cert: {cert} | Lab: {lab} | Data: {data} | Grandezas: {n_g}")
                contexto = "\n\nDADOS EXTRAÍDOS DO PDF:\n" + "\n".join(resumo)

            prompt = f"""Voce e o Metron, assistente de metrologia da Gocal.

PERGUNTA DO USUARIO: "{message}"
{contexto}

REGRAS DE RESPOSTA:
1. NUNCA mostre JSON bruto ou código.
2. Se pedir tabela/grandezas, diga ao usuário para usar o comando "mostrar tabelas".
3. Use Markdown para formatar (negrito, listas, tabelas Markdown quando necessario).
4. Responda em português, de forma direta e técnica.
5. Se não souber, diga que não encontrou a informação no documento."""

            if hasattr(extractor, 'ask'):
                resposta = extractor.ask(prompt)
            else:
                from openai import OpenAI as _OAI
                client = _OAI(api_key=os.getenv('OPENAI_API_KEY'))
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt}
                    ]
                )
                resposta = completion.choices[0].message.content

            return jsonify({'success': True, 'message': resposta})

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                return jsonify({'success': True, 'message': '⏳ **Sistema sobrecarregado.** Aguarde 15 segundos e tente novamente.'})
            print(f"[ERRO] Chat: {e}")
            return jsonify({'success': True, 'message': f'Ocorreu um erro: {error_msg}'})

    return jsonify({'success': False, 'message': 'Envie uma mensagem ou um PDF.'})


@app.route('/chat-mensagem', methods=['POST'])
def chat_mensagem():
    """Rota exclusiva para chat de texto (sem upload)"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    data = request.get_json()
    message = data.get('message', '')
    req_user_id = data.get('user_id') or session.get('gocal_user_id') or ''
    req_funcionario_id = data.get('funcionario_id') or session.get('gocal_funcionario_id') or ''
    lat = data.get('lat')
    lon = data.get('lon')

    print(f"[CHAT-MSG] Session: {session_id[:8]}... Msg: {message} | user_id={req_user_id} | geo={lat},{lon}")

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

    msg_lower = message.lower()

    # ── Tabelas de grandezas direto do cache ─────────────────────────────
    tabela_kws = ['tabela', 'tabelas', 'grandeza', 'grandezas',
                  'resultado', 'resultados', 'mostrar tabela', 'ver tabela']
    if dados and any(k in msg_lower for k in tabela_kws):
        linhas = []
        for i, inst in enumerate(dados):
            nome = inst.get('nome') or inst.get('instrumento') or f'Instrumento {i+1}'
            tag  = inst.get('identificacao') or 'S/N'
            grandezas = inst.get('grandezas') or []
            linhas.append(f"### {i+1}. {nome} — `{tag}`\n")
            if grandezas:
                linhas.append("| Faixa | Unidade | Resolução | Tolerância | Critério | Incerteza |")
                linhas.append("|---|---|---|---|---|---|")
                for g in grandezas:
                    def _v(k, _g=g): return str(_g.get(k) or '—')
                    linhas.append(f"| {_v('faixa_nominal')} | {_v('unidade')} | {_v('resolucao')} | {_v('tolerancia_processo')} | {_v('criterio_aceitacao')} | {_v('incerteza')} |")
            else:
                linhas.append("_Sem grandezas registradas._")
            linhas.append("")
        return jsonify({
            'success': True,
            'message': "\n".join(linhas) or "Nenhum dado extraído ainda.",
            'token_usage': extractor.token_usage if extractor else {}
        })

    # ── Gráfico de erros de indicação ────────────────────────────────────
    grafico_kws = [
        'grafico', 'gráfico', 'chart', 'plot', 'plotar',
        'erro de indicacao', 'erro de indicação',
        'erros de indicacao', 'erros de indicação',
        'indicacao', 'indicação', 'desvio', 'mostrar erro',
    ]
    if any(k in msg_lower for k in grafico_kws):
        if not dados:
            return jsonify({'success': True,
                'message': 'Para gerar o gráfico, carregue o **PDF do certificado** primeiro. 📄'})
        # Monta contexto compacto com grandezas para o prompt do gráfico
        ctx_grafico = ""
        for inst in dados:
            nome = inst.get('nome', 'Instrumento')
            ctx_grafico += f"\nInstrumento: {nome}\n"
            for g in (inst.get('grandezas') or []):
                ctx_grafico += f"  faixa={g.get('faixa_nominal')} resultado={g.get('resultado')} tolerancia={g.get('tolerancia_processo')} unidade={g.get('unidade')}\n"
        prompt_g = f"""Voce e o Metron. O usuario quer um GRAFICO dos dados de calibracao.

DADOS DISPONIVEIS:
{ctx_grafico}

TAREFA: Extraia os pontos de calibracao (valor nominal e erro de indicacao) e retorne SOMENTE este JSON:
{{"message": "Aqui está o gráfico!", "mostrar_grafico": {{"titulo": "Erro de Indicação", "x_label": "Valor Nominal", "y_label": "Erro", "pontos": [{{"x": 0.0, "y": 0.000, "ie": 0.007}}]}}}}

REGRAS:
- "pontos": todos os pares da tabela (x=nominal, y=erro_de_indicacao)
- "ie": tolerância máxima (±IE); use 0 se não encontrar
- Substitua "Valor Nominal" e "Erro" pelas unidades reais do instrumento
- Retorne APENAS o JSON. Nenhum texto extra."""
        try:
            if hasattr(extractor, 'ask'):
                resp_g = extractor.ask(prompt_g)
            else:
                from openai import OpenAI as _OAI
                client = _OAI(api_key=os.getenv('OPENAI_API_KEY'))
                comp = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt_g}]
                )
                resp_g = comp.choices[0].message.content
            clean = re.sub(r'```json|```', '', resp_g).strip()
            jm = re.search(r'\{.*\}', clean, re.DOTALL)
            if jm:
                gj = json.loads(jm.group(0))
                if 'mostrar_grafico' in gj:
                    return jsonify({'success': True,
                        'message': gj.get('message', 'Gráfico gerado!'),
                        'grafico': gj['mostrar_grafico'],
                        'token_usage': extractor.token_usage if extractor else {}})
        except Exception as eg:
            print(f"[GRAFICO] Erro: {eg}")
        return jsonify({'success': True,
            'message': 'Não consegui gerar o gráfico. Verifique se o certificado tem tabela de resultados.'})

    try:
        contexto = ""

        # Carrega instrumentos do banco para o contexto do chat
        if req_user_id:
            try:
                conn_ctx = mysql.connector.connect(**DB_CONFIG)
                cur_ctx = conn_ctx.cursor(dictionary=True)
                cur_ctx.execute("""
                    SELECT i.identificacao AS tag, i.nome, i.status, i.descricao,
                           c.data_calibracao, c.data_proxima_calibracao,
                           c.laboratorio_responsavel, c.numero_calibracao
                    FROM instrumentos i
                    LEFT JOIN calibracoes c ON c.id = (
                        SELECT id FROM calibracoes WHERE instrumento_id = i.id
                        ORDER BY data_calibracao DESC LIMIT 1
                    )
                    WHERE i.user_id = %s
                    ORDER BY i.identificacao
                    LIMIT 200
                """, (req_user_id,))
                instrumentos_db = cur_ctx.fetchall()
                cur_ctx.close()
                conn_ctx.close()

                if instrumentos_db:
                    for row in instrumentos_db:
                        for k in ['data_calibracao', 'data_proxima_calibracao']:
                            if row.get(k):
                                row[k] = str(row[k])
                    db_json = json.dumps(instrumentos_db, ensure_ascii=False, indent=2)
                    contexto += f"\n\nINSTRUMENTOS NO BANCO DE DADOS (total: {len(instrumentos_db)}):\n{db_json}"
            except Exception as e_ctx:
                print(f"[CHAT-MSG] Erro ao carregar contexto do banco: {e_ctx}")

        if dados:
            # Limita o contexto para nao estourar tokens se for muito grande
            json_str = json.dumps(dados, ensure_ascii=False, indent=2)
            if len(json_str) > 10000:
                json_str = json_str[:10000] + "... (troncado)"
            contexto += f"\n\nDADOS DO DOCUMENTO (PDF atual em sessão):\n{json_str}"

        # Rotas mapeadas da aplicacao
        APP_ROUTES = {
            "Dashboard": "/monitoramento",
            "Monitoramento": "/monitoramento",
            "Instrumentos": "/instrumentos",
            "Listar Instrumentos": "/instrumentos",
            "Novo Instrumento": "/instrumentos/create",
            "Laboratorios": "/laboratorios",
            "Listar Laboratorios": "/laboratorios",
            "Perfil": "/profile",
            "Assinatura": "/profile/signature",
            "Favoritos": "/favoritos",
        }

        # Detecta se o usuario quer um grafico
        grafico_keywords = [
            'grafico', 'gráfico', 'chart', 'plot', 'plotar',
            'mostrar grafico', 'gerar grafico',
            'erro de indicacao', 'erro de indicação',
            'erros de indicacao', 'erros de indicação',
            'indicacao', 'indicação', 'desvio', 'mostrar erro',
        ]
        tabela_keywords = [
            'tabela', 'tabelas', 'grandeza', 'grandezas',
            'resultado', 'resultados', 'mostrar tabela',
            'ver tabela', 'listar tabela', 'dados de calibracao',
        ]
        is_grafico_request = any(kw in message.lower() for kw in grafico_keywords)
        is_tabela_request  = any(kw in message.lower() for kw in tabela_keywords)

        # ── Tabelas de grandezas direto do cache ──────────────────────────
        if is_tabela_request and dados:
            linhas = []
            for i, inst in enumerate(dados):
                nome = inst.get('nome') or inst.get('instrumento') or f'Instrumento {i+1}'
                tag  = inst.get('identificacao') or 'S/N'
                grandezas = inst.get('grandezas') or []
                linhas.append(f"### {i+1}. {nome} — `{tag}`\n")
                if grandezas:
                    linhas.append("| Faixa | Unidade | Resolução | Tolerância | Critério | Incerteza |")
                    linhas.append("|---|---|---|---|---|---|")
                    for g in grandezas:
                        def _v(k, _g=g): return str(_g.get(k) or '—')
                        linhas.append(f"| {_v('faixa_nominal')} | {_v('unidade')} | {_v('resolucao')} | {_v('tolerancia_processo')} | {_v('criterio_aceitacao')} | {_v('incerteza')} |")
                else:
                    linhas.append("_Sem grandezas registradas._")
                linhas.append("")
            return jsonify({
                'success': True,
                'message': "\n".join(linhas) or "Nenhum dado extraído ainda.",
                'token_usage': extractor.token_usage if extractor else {}
            })

        # Se quer gráfico mas não tem dados do PDF na sessão, responde sem chamar a IA
        if is_grafico_request and not dados:
            return jsonify({
                'success': True,
                'message': 'Para gerar o gráfico, carregue o **PDF do certificado de calibração** primeiro. Os dados de medição precisam estar disponíveis na sessão. 📄',
                'token_usage': extractor.token_usage if extractor else {}
            })

        if is_grafico_request:
            prompt = f"""Voce e o Metron. O usuario quer um GRAFICO dos dados de calibracao.
{contexto}

TAREFA UNICA: Extraia os pontos de calibracao (valor nominal e erro de indicacao) do contexto acima e retorne SOMENTE este JSON, sem nenhum texto antes ou depois:

{{"message": "Aqui está o gráfico!", "mostrar_grafico": {{"titulo": "Erro de Indicação", "x_label": "Valor Nominal (mm)", "y_label": "Erro (mm)", "pontos": [{{"x": 0.0, "y": 0.000, "ie": 0.007}}, {{"x": 75.31, "y": 0.005, "ie": 0.007}}]}}}}

REGRAS:
- "pontos": lista com todos os pares (x=nominal, y=erro_de_indicacao) da tabela de resultados
- "ie": valor do ±IE ou tolerância máxima (use 0 se nao encontrar)
- "x_label" e "y_label": use a unidade correta do instrumento
- Retorne SOMENTE o JSON. Zero texto adicional.
"""
        else:
            prompt = f"""Voce e o Metron, assistente do sistema Gocal/Labster de gestao de instrumentos de medicao.

IMPORTANTE: Voce SOMENTE pode falar sobre dados do usuario autenticado (user_id={req_user_id or 'NAO IDENTIFICADO'}).
Nunca revele nem use dados de outros usuarios. Se nao houver user_id, recuse consultas ao banco.
{contexto}

ROTAS DA APLICACAO (Use se o usuario pedir para ir):
{json.dumps(APP_ROUTES, indent=2)}

USUARIO: "{message}"

INSTRUCOES:
0. BLOQUEIO DE NAVEGACAO: Se o usuario pedir para ir, abrir, acessar ou navegar para a pagina de calibracoes OU movimentos, NAO execute a navegacao. Responda APENAS em texto, de forma sutil e amigavel, algo como: "Essa navegação ainda não está disponível pelo chat, mas você pode acessar pelo menu do sistema normalmente. 😊" — sem JSON, sem navigate_to.

1. Se o usuario pedir para NAVEGAR para alguma tela (ex: "ir para instrumentos"), retorne APENAS este JSON:
   {{"message": "Indo para instrumentos...", "navigate_to": "/instrumentos"}}

2. Se o usuario fizer QUALQUER pergunta sobre instrumentos cadastrados — seja para listar, ver, contar, filtrar por tipo, status, vencimento, etc. (ex: "quantos micrometros temos?", "mostre os paquimetros", "quais estao em revisao", "instrumentos vencidos", "ver calibracoes a vencer") — retorne APENAS este JSON puro, sem nenhum texto antes ou depois:
   {{"message": "Buscando instrumentos...", "listar_instrumentos": {{"termo": "micrometro", "status": "", "filtro_vencidos": false, "filtro_a_vencer": false}}}}
   - Use "termo" para filtrar por tipo/nome (ex: "micrometro", "paquimetro", "termometro"). Deixe vazio para todos.
   - Use "status" EXATAMENTE um destes valores (com acento correto): "Aprovado", "Reprovado", "Inativo", "Em Calibração", "Em Manutenção", "Em Revisão", "Sem Calibração", "Pendente Aprovação". Deixe vazio para todos os status.
   - Use "filtro_vencidos": true para instrumentos com calibracao vencida
   - Use "filtro_a_vencer": true para instrumentos que vencem nos proximos 30 dias
   - CRITICO: retorne SOMENTE o JSON, sem explicacao, sem introducao, sem texto adicional

4. Se o usuario fizer QUALQUER pergunta sobre LABORATORIOS DE CALIBRACAO (encontrar labs, responsavel, contato, RBC, acreditacao, etc):
   Retorne APENAS este JSON:
   {{"message": "Buscando...", "buscar_laboratorios": {{"termo": "<termo>", "tipo": "<tipo>"}}}}

   "tipo" deve ser:
   - "instrumento" → quer labs para calibrar um instrumento (ex: "paquimetro", "multimetro")
   - "nome_lab"    → menciona nome de um lab (ex: "A E R Balancas")
   - "rbc"         → menciona numero de acreditacao (ex: "850", "75")
   - "livre"       → qualquer outra coisa sobre labs

   "termo" deve ser:
   - instrumento: nome corrigido do instrumento
   - nome_lab: nome do lab EXATAMENTE como o usuario escreveu (corrija so ortografia basica)
   - rbc: APENAS O NUMERO (ex: "850") sem letras
   - livre: frase do usuario corrigida

   EXEMPLOS:
   - "onde calibro multimetro?" → {{"termo": "multimetro", "tipo": "instrumento"}}
   - "A E R Balancas quem e o responsavel?" → {{"termo": "A E R Balancas", "tipo": "nome_lab"}}
   - "responsavel pelo lab acreditacao 850" → {{"termo": "850", "tipo": "rbc"}}
   CRITICO: retorne SOMENTE o JSON

3. Para qualquer outra pergunta (sobre o sistema, como usar, etc.), responda em texto normal.
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

            # Contabiliza tokens no extractor
            if completion.usage and extractor:
                extractor.token_usage['prompt_tokens'] += completion.usage.prompt_tokens
                extractor.token_usage['completion_tokens'] += completion.usage.completion_tokens
                extractor.token_usage['total_tokens'] += completion.usage.total_tokens

            resposta = completion.choices[0].message.content
        
        # Remove tags HTML que a IA eventualmente gera (<br>, <br/>, etc)
        resposta = re.sub(r'<br\s*/?>', '\n', resposta, flags=re.IGNORECASE)

        # Tenta parsear se a IA mandou um JSON (Navegacao ou Checklist)
        try:
            # Limpa backticks se a IA colocou ```json ... ```
            clean_resp = resposta.replace('```json', '').replace('```', '').strip()

            # Extrai JSON mesmo se vier com texto antes (ex: "Aqui está: {...}")
            json_match = re.search(r'\{.*\}', clean_resp, re.DOTALL)
            if json_match:
                clean_resp = json_match.group(0)

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

                # Caso 3: Gráfico de Calibração
                if 'mostrar_grafico' in resp_json:
                    return jsonify({
                        'success': True,
                        'message': resp_json.get('message', 'Gerando gráfico...'),
                        'grafico': resp_json['mostrar_grafico'],
                        'token_usage': extractor.token_usage if extractor else {}
                    })

                # Caso 4: Listar/Filtrar Instrumentos
                if 'listar_instrumentos' in resp_json:
                    filtros = resp_json['listar_instrumentos']
                    uid = req_user_id or session.get('gocal_user_id') or ''
                    texto_resultado = _buscar_instrumentos_texto(uid, filtros)
                    return jsonify({
                        'success': True,
                        'message': texto_resultado,
                        'token_usage': extractor.token_usage if extractor else {}
                    })

                # Caso 5: Buscar Laboratórios
                if 'buscar_laboratorios' in resp_json:
                    filtros_lab = resp_json['buscar_laboratorios']
                    termo_lab = filtros_lab.get('termo', '')
                    tipo_lab  = filtros_lab.get('tipo', 'livre')
                    print(f"[CHAT-LAB] termo='{termo_lab}' tipo='{tipo_lab}'")
                    # Busca e formata em texto (Passando lat/lon se disponivel)
                    texto_labs = _buscar_laboratorios_texto(termo_lab, lat=lat, lon=lon, tipo=tipo_lab)
                    return jsonify({
                        'success': True,
                        'message': texto_labs,
                        'buscar_laboratorios': {'termo': termo_lab}, # Mantém para cards se o JS quiser
                        'token_usage': extractor.token_usage if extractor else {}
                    })
        except:
            pass # Nao e JSON, segue normal

        token_data = extractor.token_usage if extractor else {}
        return jsonify({'success': True, 'message': resposta, 'token_usage': token_data})

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
             return jsonify({'success': True, 'message': '⏳ **Muitas requisições.** Estamos operando no limite da IA. Aguarde alguns segundos e tente de novo.'})

        print(f"[ERRO] Chat Msg: {e}")
        return jsonify({'success': False, 'message': f'Erro técnico: {error_msg}'})




def _buscar_instrumentos_texto(user_id, filtros):
    """Consulta o banco e retorna resposta formatada em texto para o chat.
    SEGURANÇA: sempre filtra por user_id — nunca retorna dados de outro usuário."""
    if not user_id:
        return "Não foi possível identificar o usuário. Faça login novamente."
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        termo = (filtros.get('termo') or '').strip()
        status = (filtros.get('status') or '').strip()
        filtro_vencidos = bool(filtros.get('filtro_vencidos'))
        filtro_a_vencer = bool(filtros.get('filtro_a_vencer'))

        sql = """
            SELECT i.identificacao, i.nome, i.status,
                   c.data_proxima_calibracao
            FROM instrumentos i
            LEFT JOIN calibracoes c ON c.id = (
                SELECT id FROM calibracoes WHERE instrumento_id = i.id ORDER BY data_calibracao DESC LIMIT 1
            )
            WHERE i.user_id = %s
        """
        params = [user_id]

        if termo:
            sql += " AND (i.identificacao LIKE %s OR i.nome LIKE %s OR i.descricao LIKE %s)"
            params += [f'%{termo}%', f'%{termo}%', f'%{termo}%']

        if status:
            sql += " AND i.status = %s"
            params.append(status)

        if filtro_vencidos:
            sql += " AND c.data_proxima_calibracao <= CURDATE()"

        if filtro_a_vencer:
            sql += " AND c.data_proxima_calibracao BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)"

        sql += " ORDER BY i.identificacao LIMIT 50"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return "Nenhum instrumento encontrado com esses filtros."

        linhas = [f"Encontrei **{len(rows)}** instrumento(s):\n"]
        for r in rows:
            prox = str(r['data_proxima_calibracao']) if r.get('data_proxima_calibracao') else 'sem data'
            linhas.append(f"• **{r['identificacao']}** — {r['nome']} | {r['status']} | Próx. calib.: {prox}")

        return "\n".join(linhas)
    except Exception as e:
        print(f"[ERRO] _buscar_instrumentos_texto: {e}")
        return "Erro ao buscar instrumentos no banco de dados."




def _buscar_laboratorios_texto(termo, lat=None, lon=None, tipo='livre'):
    """Consulta o banco e retorna resposta formatada em texto para o chat.
    tipo: 'instrumento', 'nome_lab', 'rbc', 'livre'
    """
    print(f"[LAB-TEXTO] termo='{termo}' tipo='{tipo}' lat={lat} lon={lon}")
    try:
        labs_detalhe = []
        labs_lista   = []

        if tipo in ('rbc', 'nome_lab'):
            # Busca direta na tabela laboratorio
            labs_detalhe = _consultar_detalhes_laboratorio(termo, lat=lat, lon=lon)

        elif tipo == 'instrumento':
            # Busca por escopo de calibração
            labs_lista = _buscar_laboratorios_para_instrumento(termo, lat=lat, lon=lon, limit=5)

        else:  # livre
            # Tenta instrumento primeiro, depois nome de lab
            labs_lista = _buscar_laboratorios_para_instrumento(termo, lat=lat, lon=lon, limit=5)
            if not labs_lista:
                labs_detalhe = _consultar_detalhes_laboratorio(termo, lat=lat, lon=lon)

        # FORMATAÇÃO: detalhes de lab específico
        if labs_detalhe:
            linhas = []
            for l in labs_detalhe:
                dist = f" ({l['distancia_km']}km)" if l.get('distancia_km') is not None else ""
                linhas.append(f"Aqui estão os dados do laboratório **{l['nome_laboratorio']}** [RBC {l.get('acreditacao_num', '')}]:\n")
                linhas.append(f"• **Responsável:** {l.get('gerente_tecnico') or 'Não informado'}")
                linhas.append(f"• **Localização:** {l.get('endereco', '')} — {l.get('cidade', '')}/{l.get('uf', '')}{dist}")
                linhas.append(f"• **E-mail:** {l.get('email', 'não informado')}")
                linhas.append(f"• **Telefone:** {l.get('telefone', 'não informado')}")
                if l.get('situacao'): linhas.append(f"• **Situação:** {l['situacao']}")
                linhas.append("")
            return "\n".join(linhas).strip()

        # FORMATAÇÃO: lista de labs por instrumento
        if labs_lista:
            linhas = [f"Encontrei **{len(labs_lista)}** laboratório(s) para **{termo}**:\n"]
            for l in labs_lista:
                dist = f" ({l['distancia_km']}km)" if l.get('distancia_km') is not None else ""
                acred = f" [RBC {l['acreditacao_num']}]" if l.get('acreditacao_num') else ""
                linhas.append(f"• **{l['nome_laboratorio']}**{dist}{acred} - {l['cidade']}/{l['uf']}")
            return "\n".join(linhas)

        return f"Não encontrei laboratórios para **{termo}** no banco. Tente outro termo."

    except Exception as e:
        print(f"[ERRO] _buscar_laboratorios_texto: {e}")
        return "Erro ao buscar laboratórios no banco."

def _consultar_detalhes_laboratorio(termo, lat=None, lon=None):
    """Consulta dados diretos da tabela laboratorio pelo nome ou RBC.
    Estratégia: tenta por RBC, depois LIKE completo, depois palavras individuais."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor(dictionary=True)

        lat_v  = float(lat)  if lat  else 0
        lon_v  = float(lon)  if lon  else 0

        base_select = """
            SELECT id, nome_laboratorio, razao_social, acreditacao_num, uf, cidade,
                   email, telefone, fax, gerente_tecnico, endereco, bairro, cep,
                   situacao, latitude, longitude, grupo_servico,
                   ROUND((6371 * ACOS(GREATEST(-1, LEAST(1,
                       COS(RADIANS(%s)) * COS(RADIANS(IFNULL(latitude,0))) *
                       COS(RADIANS(IFNULL(longitude,0)) - RADIANS(%s)) +
                       SIN(RADIANS(%s)) * SIN(RADIANS(IFNULL(latitude,0)))
                   )))), 0) AS distancia_km
            FROM laboratorio
        """
        params_geo = (lat_v, lon_v, lat_v)

        # 1. Por número RBC (ex: "RBC 850" ou "850")
        rbc_match = re.search(r'\b(\d+)\b', termo)
        if rbc_match:
            rbc_num = rbc_match.group(1)
            print(f"[LAB-DETALHE] Tentando por RBC={rbc_num}")
            cur.execute(base_select + " WHERE acreditacao_num = %s LIMIT 1",
                        params_geo + (rbc_num,))
            res = cur.fetchall()
            print(f"[LAB-DETALHE] Resultado RBC: {len(res)} linha(s)")
            if res:
                cur.close(); conn.close()
                return res

        # 2. LIKE completo no nome ou razao social
        print(f"[LAB-DETALHE] Tentando LIKE '{termo}'")
        cur.execute(base_select + " WHERE nome_laboratorio LIKE %s OR razao_social LIKE %s LIMIT 1",
                    params_geo + (f'%{termo}%', f'%{termo}%'))
        res = cur.fetchall()
        print(f"[LAB-DETALHE] Resultado LIKE: {len(res)} linha(s)")
        if res:
            cur.close(); conn.close()
            return res

        # 3. Cada palavra com >= 3 chars como condição OR
        palavras = [p for p in re.split(r'\s+', termo) if len(p) >= 3]
        print(f"[LAB-DETALHE] Tentando por palavras: {palavras}")
        if palavras:
            conditions = " OR ".join(["nome_laboratorio LIKE %s OR razao_social LIKE %s"] * len(palavras))
            word_params = []
            for p in palavras:
                word_params += [f'%{p}%', f'%{p}%']
            cur.execute(base_select + f" WHERE {conditions} LIMIT 3",
                        params_geo + tuple(word_params))
            res = cur.fetchall()
            print(f"[LAB-DETALHE] Resultado palavras: {len(res)} linha(s)")
            if res:
                cur.close(); conn.close()
                return res

        cur.close(); conn.close()
        print(f"[LAB-DETALHE] Nenhum resultado para '{termo}'")
        return []
    except Exception as e:
        print(f"[ERRO] _consultar_detalhes_laboratorio: {e}")
        return []


# ============================================================
# BUSCA DE LABORATÓRIOS POR INSTRUMENTO
# ============================================================
_INSTRUMENTO_ALIASES = {
    'multimetro': ['tensao', 'corrente', 'resistencia', 'eletric'],
    'multímetro': ['tensao', 'corrente', 'resistencia', 'eletric'],
    'voltimetro': ['tensao'],
    'voltímetro': ['tensao'],
    'amperimetro': ['corrente'],
    'amperímetro': ['corrente'],
    'ohmimetro': ['resistencia'],
    'ohmímetro': ['resistencia'],
    'termometro': ['temperatura', 'termometria'],
    'termômetro': ['temperatura', 'termometria'],
    'termopar': ['termopar', 'temperatura'],
    'paquimetro': ['comprimento', 'paquimetro', 'dimensional'],
    'paquímetro': ['comprimento', 'paquimetro', 'dimensional'],
    'micrometro': ['comprimento', 'micrometro', 'dimensional'],
    'micrômetro': ['comprimento', 'micrometro', 'dimensional'],
    'balanca': ['massa', 'balanca'],
    'balança': ['massa', 'balanca'],
    'manometro': ['pressao', 'manometro'],
    'manômetro': ['pressao', 'manometro'],
    'torquimetro': ['torque', 'torquimetro'],
    'torquímetro': ['torque', 'torquimetro'],
    'cronometro': ['tempo', 'intervalo'],
    'cronômetro': ['tempo', 'intervalo'],
    'higrometro': ['umidade', 'higro'],
    'higrômetro': ['umidade', 'higro'],
    'durometro': ['dureza'],
    'durômetro': ['dureza'],
    'rugosimetro': ['rugosidade'],
    'rugosímetro': ['rugosidade'],
    'osciloscópio': ['tensao', 'frequencia', 'eletric'],
    'osciloscópio': ['tensao', 'frequencia'],
    'calibrador': ['calibrador'],
    'trena': ['comprimento', 'dimensional'],
    'pino': ['comprimento', 'dimensional'],
    'nivel': ['angulo', 'nivel'],
    'nível': ['angulo', 'nivel'],
    'pipeta': ['volume'],
    'bureta': ['volume'],
    'proveta': ['volume'],
}

def _extrair_termo_instrumento(message):
    """Extrai o nome do instrumento de uma pergunta sobre laboratórios."""
    msg = message.lower().strip()
    # Remove frases comuns que não são o instrumento
    stop_phrases = [
        'qual laboratório calibra', 'qual laboratorio calibra',
        'qual lab calibra', 'laboratório que calibra', 'laboratorio que calibra',
        'onde posso calibrar', 'onde calibrar', 'onde vou calibrar',
        'laboratório para calibrar', 'laboratorio para calibrar',
        'quero calibrar', 'preciso calibrar', 'tem laboratório para',
        'tem laboratorio para', 'qual laboratório faz', 'qual lab faz',
        'buscar laboratório', 'buscar laboratorio', 'encontrar laboratório',
        'laboratorio para', 'laboratório para', 'laboratório de calibração de',
        'laboratorio de calibracao de', 'laboratorio calibra', 'laboratório calibra',
        'calibração de', 'calibracao de', 'calibra', 'meu', 'minha', 'o ', 'a ',
        'um ', 'uma ', '?', '!'
    ]
    for phrase in stop_phrases:
        msg = msg.replace(phrase, ' ')
    msg = re.sub(r'\s+', ' ', msg).strip().strip('.,?!')
    return msg if len(msg) > 1 else message.strip()


def _buscar_laboratorios_para_instrumento(termo, lat=None, lon=None, limit=8):
    """Busca laboratórios acreditados para calibrar um instrumento.
    Se lat/lon fornecidos, ordena por distância (Haversine). Caso contrário, por nome."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor(dictionary=True)
        like_term = f'%{termo}%'

        if lat and lon:
            query = """
                SELECT DISTINCT
                    l.id, l.nome_laboratorio, l.uf, l.cidade, l.situacao,
                    l.telefone, l.email, l.acreditacao_num,
                    e.descricao_servico, e.grupo, e.cmc,
                    ROUND((6371 * ACOS(GREATEST(-1, LEAST(1,
                        COS(RADIANS(%s)) * COS(RADIANS(l.latitude)) *
                        COS(RADIANS(l.longitude) - RADIANS(%s)) +
                        SIN(RADIANS(%s)) * SIN(RADIANS(l.latitude))
                    )))), 0) AS distancia_km
                FROM escopo_calibracao e
                JOIN laboratorio l ON l.id = e.laboratorio_id
                WHERE (e.descricao_servico LIKE %s OR e.grupo LIKE %s)
                  AND l.situacao = 'Ativo'
                  AND l.latitude IS NOT NULL AND l.longitude IS NOT NULL
                ORDER BY distancia_km ASC
                LIMIT %s
            """
            cur.execute(query, (lat, lon, lat, like_term, like_term, limit))
        else:
            query = """
                SELECT DISTINCT
                    l.id, l.nome_laboratorio, l.uf, l.cidade, l.situacao,
                    l.telefone, l.email, l.acreditacao_num,
                    e.descricao_servico, e.grupo, e.cmc
                FROM escopo_calibracao e
                JOIN laboratorio l ON l.id = e.laboratorio_id
                WHERE (e.descricao_servico LIKE %s OR e.grupo LIKE %s)
                  AND l.situacao = 'Ativo'
                ORDER BY l.nome_laboratorio ASC
                LIMIT %s
            """
            cur.execute(query, (like_term, like_term, limit))

        results = cur.fetchall()
        for r in results:
            if r.get('distancia_km') is not None:
                r['distancia_km'] = int(r['distancia_km'])
        cur.close()
        conn.close()
        return results
    except Exception as e:
        print(f"[LAB-SEARCH] Erro: {e}")
        return []


@app.route('/buscar-laboratorios', methods=['POST'])
def buscar_laboratorios():
    """Busca laboratórios aptos a calibrar um instrumento específico.
    Aceita lat/lon para ordenação por distância."""
    data = request.get_json()
    message  = data.get('message', '')
    termo_ia = data.get('termo_ia')
    lat = data.get('lat')
    lon = data.get('lon')

    if not message and not termo_ia:
        return jsonify({'success': False, 'message': 'Parâmetro não informado.'})

    # Prioriza o termo extraído pela IA (que já corrigiu typos)
    termo = termo_ia if termo_ia else _extrair_termo_instrumento(message)
    print(f"[LAB-SEARCH] Termo extraído: '{termo}' | lat={lat} lon={lon}")

    labs = _buscar_laboratorios_para_instrumento(termo, lat=lat, lon=lon, limit=8)

    if not labs:
        return jsonify({
            'success': True,
            'message': f'Não encontrei laboratórios acreditados para **{termo}** no banco. Tente um termo diferente (ex: "paquímetro", "termômetro", "balança").',
            'laboratorios': []
        })

    return jsonify({
        'success': True,
        'message': f'Encontrei {len(labs)} laboratório(s) para **{termo}**:',
        'laboratorios': labs,
        'termo': termo,
        'por_distancia': lat is not None
    })


@app.route('/buscar-instrumentos', methods=['GET'])
def buscar_instrumentos():
    """Busca instrumentos com filtros para o chat"""
    user_id = request.args.get('user_id') or session.get('gocal_user_id')
    if not user_id:
        return jsonify({'success': False, 'items': [], 'message': 'Usuário não identificado.'})

    termo = request.args.get('termo', '').strip()
    status = request.args.get('status', '').strip()
    filtro_vencidos = request.args.get('filtro_vencidos', '0') == '1'
    filtro_a_vencer = request.args.get('filtro_a_vencer', '0') == '1'

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT i.id, i.identificacao, i.nome, i.status,
                   c.data_calibracao, c.data_proxima_calibracao, c.status_calibracao,
                   c.laboratorio_responsavel
            FROM instrumentos i
            LEFT JOIN calibracoes c ON c.id = (
                SELECT id FROM calibracoes WHERE instrumento_id = i.id ORDER BY data_calibracao DESC LIMIT 1
            )
            WHERE i.user_id = %s
        """
        params = [user_id]

        if termo:
            sql += " AND (i.identificacao LIKE %s OR i.nome LIKE %s OR i.descricao LIKE %s)"
            params += [f'%{termo}%', f'%{termo}%', f'%{termo}%']

        if status:
            sql += " AND i.status = %s"
            params.append(status)

        if filtro_vencidos:
            sql += " AND c.data_proxima_calibracao <= CURDATE()"

        if filtro_a_vencer:
            sql += " AND c.data_proxima_calibracao BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)"

        sql += " ORDER BY i.identificacao LIMIT 50"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Formata datas
        for r in rows:
            for k in ['data_calibracao', 'data_proxima_calibracao']:
                if r.get(k):
                    r[k] = str(r[k])

        return jsonify({'success': True, 'items': rows, 'total': len(rows)})

    except Exception as e:
        print(f"[ERRO] buscar-instrumentos: {e}")
        return jsonify({'success': False, 'items': [], 'message': str(e)})


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
                         # Le o PDF como base64 ANTES de processar (para salvar no banco depois)
                         import base64
                         pdf_base64 = None
                         try:
                             with open(p, 'rb') as f:
                                 pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
                         except:
                             pass
                         
                         # Extrai dados com IA
                         res = extractor.extract_from_pdf(p, n, user_prompt=user_cmd)
                         try: os.remove(p)
                         except: pass
                         
                         if res and 'error' not in res:
                             # Anexa o PDF base64 e nome original ao resultado
                             if pdf_base64:
                                 res['_pdf_base64'] = pdf_base64
                                 res['_pdf_filename'] = n
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
    raw_data = processing_tasks.get(task_id, {'status': 'not_found'})
    
    # Cria uma copia rasa para nao alterar o original em cache (que tem o PDF)
    data = raw_data.copy()
    
    # Se tiver resultados, remove o base64 para nao travar o front
    if 'results' in data and data['results']:
        clean_results = []
        for res in data['results']:
            # Copia o dict do resultado para remover a chave sem afetar o original
            res_clean = res.copy()
            if '_pdf_base64' in res_clean:
                del res_clean['_pdf_base64']
            clean_results.append(res_clean)
        data['results'] = clean_results

    if extractor:
        data['token_usage'] = extractor.token_usage
    return jsonify(data)



# ============================================================
# ROTAS - BANCO DE DADOS (MySQL)
# ============================================================
# Normalização de Status para o padrão do Gocal
def normalizar_status(valor):
    if not valor:
        return 'Em Revisão'
    
def normalizar_data(data_str):
    """Converte DD/MM/YYYY ou similar para YYYY-MM-DD"""
    if not data_str or not isinstance(data_str, str) or data_str.lower() in ['n/i', 'n/a', '---', '']:
        return None
    
    import re
    # Tenta DD/MM/YYYY
    match = re.search(r'(\d{2})[/-](\d{2})[/-](\d{4})', data_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    
    # Tenta YYYY-MM-DD
    match = re.search(r'(\d{4})[/-](\d{2})[/-](\d{2})', data_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
        
    return data_str # Retorna original se nao bater

@app.route('/inserir-banco', methods=['POST'])
def inserir_banco():
    """Insere instrumentos extraidos no MySQL"""
    try:
        data = request.get_json()
        raw_uid = data.get('user_id')
        user_id = int(raw_uid) if raw_uid else int(session.get('gocal_user_id') or 1)
        raw_fid = data.get('funcionario_id')
        funcionario_id = int(raw_fid) if raw_fid else (int(session.get('gocal_funcionario_id')) if session.get('gocal_funcionario_id') else None)

        if 'session_id' not in session:
            pass

        session_id = session.get('session_id')
        
        # Prioriza os dados enviados pelo frontend
        instrumentos = data.get('instrumentos', [])
        
        # Fallback para cache apenas se tiver sessao valida
        if not instrumentos and session_id:
             instrumentos = extracted_cache.get(session_id, [])

        if not instrumentos:
            return jsonify({'success': False, 'message': 'Nenhum instrumento para inserir.'}), 400

        # Se veio task_id (lote), mescla o _pdf_base64 do cache do servidor
        task_id = data.get('task_id')
        if task_id and task_id in processing_tasks:
            cached_results = processing_tasks[task_id].get('results', [])
            for i, inst in enumerate(instrumentos):
                if isinstance(inst, dict) and i < len(cached_results):
                    cached = cached_results[i]
                    if isinstance(cached, dict):
                        if '_pdf_base64' in cached and '_pdf_base64' not in inst:
                            inst['_pdf_base64'] = cached['_pdf_base64']
                        if '_pdf_filename' in cached and '_pdf_filename' not in inst:
                            inst['_pdf_filename'] = cached['_pdf_filename']
            print(f"[DB] PDFs base64 mesclados do cache da task {task_id}")

        print(f"[DB] Inserindo {len(instrumentos)} instrumento(s) (user_id={user_id})")

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        total_inseridos = 0
        total_ignorados = 0
        total_grandezas = 0
        total_calibracoes_adicionadas = 0
        instrumentos_inseridos = []  # Para retornar IDs e dados de calibracao

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
                            buscar_valor('autenticacao', inst) or \
                            buscar_valor('tag', inst) or \
                            buscar_valor('codigo', inst) or \
                            buscar_valor('patrimonio', inst) or \
                            buscar_valor('numero_certificado', inst) or 'n/i'

            # Verifica se instrumento já existe
            cursor.execute(
                "SELECT id FROM instrumentos WHERE identificacao = %s AND user_id = %s LIMIT 1",
                (identificacao, user_id)
            )
            existente = cursor.fetchone()
            if existente:
                instrumento_id_existente = existente[0]
                # Extrai dados da calibração do PDF
                data_calib_dup = buscar_valor('data_calibracao', inst)
                # PRIORIDADE TOTAL para numero_certificado
                numero_cert_dup = buscar_valor('numero_certificado', inst) or \
                                  buscar_valor('numero_calibracao', inst) or \
                                  identificacao
                
                print(f"[DEBUG] Extraido para calibração: cert={numero_cert_dup}, tag={identificacao}")

                laboratorio_dup = buscar_valor('laboratorio', inst) or buscar_valor('laboratorio_responsavel', inst) or 'N/I'
                validade_dup = buscar_valor('validade', inst) or buscar_valor('data_proxima_calibracao', inst)
                motivo_dup = buscar_valor('motivo_calibracao', inst, 'Calibração Periódica') or 'Calibração Periódica'
                status_dup = normalizar_status(buscar_valor('status', inst)) or 'Em Revisão'

                # Verifica se já existe calibração com mesmo número de certificado E mesma data
                print(f"[DEBUG] Instrumento existente id={instrumento_id_existente}, numero_cert='{numero_cert_dup}', data_calib='{data_calib_dup}'")
                cursor.execute(
                    "SELECT id FROM calibracoes WHERE instrumento_id = %s AND numero_calibracao = %s AND data_calibracao = %s LIMIT 1",
                    (instrumento_id_existente, numero_cert_dup, data_calib_dup)
                )
                dup_calib = cursor.fetchone()
                print(f"[DEBUG] Calibracao duplicada encontrada: {dup_calib}")
                if dup_calib:
                    total_ignorados += 1
                    continue

                # Instrumento existe mas calibração é nova — insere só a calibração
                try:
                    sql_cal_dup = """
                        INSERT INTO calibracoes (
                            user_id, responsavel_cadastro_id, instrumento_id,
                            numero_calibracao, sufixo,
                            laboratorio_responsavel, motivo_calibracao,
                            data_calibracao, data_proxima_calibracao,
                            status_calibracao, status_instrumento,
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """
                    cursor.execute(sql_cal_dup, (
                        user_id, user_id, instrumento_id_existente,
                        numero_cert_dup, '',
                        laboratorio_dup, motivo_dup,
                        normalizar_data(data_calib_dup), normalizar_data(validade_dup),
                        'Em Revisão', status_dup
                    ))
                    calibracao_id_dup = cursor.lastrowid
                    print(f"[DB] Calibracao #{calibracao_id_dup} adicionada ao instrumento existente #{instrumento_id_existente}")

                    # Salva PDF se existir
                    pdf_base64_dup = inst.get('_pdf_base64')
                    pdf_filename_dup = inst.get('_pdf_filename', 'certificado.pdf')
                    if calibracao_id_dup and pdf_base64_dup:
                        try:
                            import hashlib, time
                            hash_name = hashlib.md5(f"{time.time()}_{pdf_filename_dup}".encode()).hexdigest()
                            cursor.execute("""
                                INSERT INTO certificados (
                                    calibracao_id, arquivo_pdf, nome_original,
                                    pdf_content, pdf_in_database,
                                    created_at, updated_at
                                ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                            """, (calibracao_id_dup, f"certificados/{hash_name}.pdf", pdf_filename_dup, pdf_base64_dup, 1))
                        except Exception as e_pdf_dup:
                            print(f"[AVISO] Erro ao salvar PDF para calibracao #{calibracao_id_dup}: {e_pdf_dup}")

                    instrumentos_inseridos.append({
                        'instrumento_id': instrumento_id_existente,
                        'calibracao_id': calibracao_id_dup,
                        'numero_calibracao': numero_cert_dup,
                        'data_calibracao': data_calib_dup,
                        'laboratorio_responsavel': laboratorio_dup,
                        'motivo_calibracao': motivo_dup
                    })
                    total_calibracoes_adicionadas += 1
                except Exception as e_cal_dup:
                    print(f"[AVISO] Erro ao adicionar calibracao a instrumento existente: {e_cal_dup}")
                    total_ignorados += 1
                continue
            
            # Mapeia campos principais procurando recursivamente ou usando defaults
            # Campos que nao podem ser NULL recebem 'N/I' (Nao Informado)
            nome = buscar_valor('nome', inst) or buscar_valor('instrumento', inst) or buscar_valor('titulo', inst) or 'N/I'
            fabricante = buscar_valor('fabricante', inst) or 'N/I'
            modelo = buscar_valor('modelo', inst) or 'N/I'
            numero_serie = buscar_valor('numero_serie', inst) or buscar_valor('serie', inst) or 'N/I'
            descricao = buscar_valor('descricao', inst) or json.dumps(inst, ensure_ascii=False)[:500]
            periodicidade = buscar_valor('periodicidade', inst, 12)
            departamento = ""
            responsavel = str(user_id)
            # Default Status Instrumento: "Em Revisão"
            status = normalizar_status(buscar_valor('status', inst)) or 'Em Revisão'
            tipo_familia = buscar_valor('tipo_familia', inst) or buscar_valor('tipo_documento', inst) or 'N/I'
            serie_desenv = buscar_valor('serie_desenv', inst) or buscar_valor('desenho', inst) or 'N/I'
            criticidade = buscar_valor('criticidade', inst) or 'N/I'
            motivo_calibracao = buscar_valor('motivo_calibracao', inst, 'Calibração Periódica') or 'Calibração Periódica'
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
            
            # --- LOG AUDITORIA (Instrumento) ---
            try:
                sql_audit = """
                    INSERT INTO logs_auditoria (
                        user_id, funcionario_id, acao, modelo, modelo_id, depois, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                # Serializa dados para JSON (depois)
                dados_inst = {
                    'identificacao': identificacao, 'nome': nome, 'status': status,
                    'user_id': user_id, 'id': instrumento_id
                }
                cursor.execute(sql_audit, (
                    user_id, funcionario_id, 'criado', 'Instrumento', instrumento_id, json.dumps(dados_inst, default=str)
                ))
            except Exception as e_audit:
                print(f"[AVISO] Erro ao criar log auditoria instrumento: {e_audit}")

            # Cria calibracao automaticamente
            data_calib = normalizar_data(buscar_valor('data_calibracao', inst))
            data_emissao = normalizar_data(buscar_valor('data_emissao', inst))
            
            # PRIORIDADE TOTAL para numero_certificado na calibração
            numero_cert = buscar_valor('numero_certificado', inst) or \
                          buscar_valor('numero_calibracao', inst) or \
                          identificacao
            
            print(f"[DEBUG] Nova calibração: cert={numero_cert}, inst={identificacao}")
            laboratorio = buscar_valor('laboratorio', inst) or buscar_valor('laboratorio_responsavel', inst) or 'N/I'
            validade = normalizar_data(buscar_valor('validade', inst) or buscar_valor('data_proxima_calibracao', inst))

            try:
                sql_cal = """
                    INSERT INTO calibracoes (
                        user_id, responsavel_cadastro_id, instrumento_id,
                        numero_calibracao, sufixo,
                        laboratorio_responsavel, motivo_calibracao,
                        data_calibracao, data_proxima_calibracao,
                        status_calibracao, status_instrumento,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                valores_cal = (
                    user_id, user_id, instrumento_id,
                    numero_cert, '',
                    laboratorio, motivo_calibracao,
                    data_calib, validade,
                    'Em Revisão', status
                )
                cursor.execute(sql_cal, valores_cal)
                calibracao_id = cursor.lastrowid
                print(f"[DB] Calibracao #{calibracao_id} criada para instrumento #{instrumento_id}")
                
                 # --- LOG AUDITORIA (Calibracao) ---
                try:
                    dados_cal = {
                        'instrumento_id': instrumento_id, 'numero_calibracao': numero_cert,
                        'status_calibracao': 'Em Revisão', 'user_id': user_id, 'id': calibracao_id
                    }
                    cursor.execute(sql_audit, (
                        user_id, funcionario_id, 'criado', 'Calibracao', calibracao_id, json.dumps(dados_cal, default=str)
                    ))
                except Exception as e_audit:
                    print(f"[AVISO] Erro ao criar log auditoria calibracao: {e_audit}")

                # Salva o PDF fisico na tabela certificados (igual ao Gocal Laravel)
                pdf_base64 = inst.get('_pdf_base64')
                pdf_filename = inst.get('_pdf_filename', 'certificado.pdf')
                if calibracao_id and pdf_base64:
                    try:
                        import hashlib, time
                        hash_name = hashlib.md5(f"{time.time()}_{pdf_filename}".encode()).hexdigest()
                        arquivo_path = f"certificados/{hash_name}.pdf"
                        
                        sql_cert = """
                            INSERT INTO certificados (
                                calibracao_id, arquivo_pdf, nome_original,
                                pdf_content, pdf_in_database,
                                created_at, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                        """
                        cursor.execute(sql_cert, (
                            calibracao_id, arquivo_path, pdf_filename,
                            pdf_base64, 1
                        ))
                        print(f"[DB] Certificado PDF salvo para calibracao #{calibracao_id} ({pdf_filename})")
                    except Exception as e_pdf:
                        print(f"[AVISO] Erro ao salvar PDF para calibracao #{calibracao_id}: {e_pdf}")
                        
            except Exception as e_cal:
                calibracao_id = None
                print(f"[AVISO] Erro ao criar calibracao para instrumento #{instrumento_id}: {e_cal}")

            instrumentos_inseridos.append({
                'instrumento_id': instrumento_id,
                'calibracao_id': calibracao_id,
                'numero_calibracao': numero_cert,
                'data_calibracao': data_calib,
                'laboratorio_responsavel': laboratorio,
                'motivo_calibracao': motivo_calibracao
            })

            # ── GRANDEZAS: desativado temporariamente (segunda ordem) ──────────
            # lista_grandezas = buscar_valor('grandezas', inst) or buscar_valor('tabelas', inst) or []
            # if not isinstance(lista_grandezas, list):
            #     lista_grandezas = []
            # for grandeza in lista_grandezas:
            #     def get_g(key, default=None):
            #         val = grandeza.get(key)
            #         if val is None and isinstance(grandeza, dict):
            #             for k, v in grandeza.items():
            #                 if isinstance(v, dict) and key in v:
            #                     return v[key]
            #         return val or default
            #     sql_g = """
            #         INSERT INTO grandezas (
            #             instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica,
            #             unidade, resolucao, criterio_aceitacao, regra_decisao_id,
            #             faixa_nominal, classe_norma, classificacao, faixa_uso,
            #             created_at, updated_at
            #         ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            #     """
            #     tolerancia  = get_g('tolerancia_processo') or get_g('tolerancia') or get_g('erro_maximo')
            #     unidade     = get_g('unidade')
            #     resolucao   = get_g('resolucao')
            #     faixa_nominal = get_g('faixa_nominal') or get_g('faixa') or get_g('valor_nominal')
            #     valores_g = (
            #         instrumento_id,
            #         json.dumps(get_g('servicos', []) if isinstance(get_g('servicos'), list) else []),
            #         tolerancia, get_g('tolerancia_simetrica', True), unidade, resolucao,
            #         get_g('criterio_aceitacao'), get_g('regra_decisao_id', 1),
            #         faixa_nominal, get_g('classe_norma'), get_g('classificacao'), get_g('faixa_uso')
            #     )
            #     cursor.execute(sql_g, valores_g)
            #     total_grandezas += 1
            # ────────────────────────────────────────────────────────────────────

        conn.commit()
        cursor.close()
        conn.close()

        # Limpa cache
        if session_id in extracted_cache:
            del extracted_cache[session_id]

        msg = f'Inseridos {total_inseridos} instrumento(s)!'
        if total_calibracoes_adicionadas > 0:
            msg += f' ({total_calibracoes_adicionadas} calibração(ões) adicionada(s) a instrumento(s) existente(s))'
        if total_ignorados > 0:
            msg += f' ({total_ignorados} duplicata(s) ignorada(s))'

        return jsonify({
            'success': True,
            'message': msg,
            'inseridos': total_inseridos,
            'ignorados': total_ignorados,
            'calibracoes_adicionadas': total_calibracoes_adicionadas,
            'grandezas': total_grandezas,
            'instrumentos_inseridos': instrumentos_inseridos
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
            val_status = escape(inst.get('status', 'Sem Calibração'))
            val_tipo = escape(inst.get('tipo_familia') or inst.get('tipo_documento'))
            val_serie = escape(inst.get('serie_desenv'))
            val_crit = escape(inst.get('criticidade'))
            val_motivo = escape(inst.get('motivo_calibracao', 'Calibração Periódica'))
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

@app.route('/certificado-pdf/<int:calibracao_id>')
def servir_certificado_pdf(calibracao_id):
    """Serve o PDF do certificado direto do banco de dados pelo ID da calibracao"""
    import base64
    import io
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Busca na tabela certificados (que tem o PDF in database)
        cursor.execute(
            'SELECT pdf_content, pdf_in_database, nome_original, arquivo_pdf FROM certificados WHERE calibracao_id = %s ORDER BY id DESC LIMIT 1',
            (calibracao_id,)
        )
        cert = cursor.fetchone()
        cursor.close()
        conn.close()

        if not cert:
            return jsonify({'error': 'Certificado nao encontrado'}), 404

        # Se o PDF esta no banco (base64)
        if cert['pdf_in_database'] and cert['pdf_content']:
            pdf_bytes = base64.b64decode(cert['pdf_content'])
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                download_name=cert['nome_original'] or 'certificado.pdf'
            )

        # Se tem caminho de arquivo (storage do Laravel)
        if cert['arquivo_pdf']:
            # Tenta no storage do Laravel
            laravel_storage = os.path.join(os.getenv('LARAVEL_STORAGE', 'C:/xampp/htdocs/gocal/storage/app/public'), cert['arquivo_pdf'])
            if os.path.exists(laravel_storage):
                return send_file(laravel_storage, mimetype='application/pdf')

        return jsonify({'error': 'PDF nao disponivel'}), 404

    except Exception as e:
        print(f"[ERRO] Servir PDF: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/token-usage')
def token_usage():
    """Retorna o uso acumulado de tokens da sessao"""
    if extractor:
        return jsonify(extractor.token_usage)
    return jsonify({'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0})

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
