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
from openai_extractor.security import SecurityValidator

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
    'database': 'instrumentos',
    'user': 'root',
    'password': ''
}

# ============================================================
# INICIALIZACAO
# ============================================================
try:
    extractor = OpenAIExtractor()
except Exception as e:
    print(f"[ERRO] Falha ao inicializar Extrator: {e}")
    extractor = None

validator = SecurityValidator()
extracted_cache = {}  # Cache: {session_id: [dados_extraidos]}


# ============================================================
# ROTAS - PAGINAS
# ============================================================
@app.route('/')
def index():
    """Pagina principal do Chat"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('gocal_chat.html')


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
        for file in files:
            filename = secure_filename(file.filename)
            is_valid, error = validator.validate_pdf(filename)
            if not is_valid:
                continue

            print(f"[PDF] Processando: {filename}")
            try:
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(temp_path)

                # Extracao via GPT-4o Vision
                dados = extractor.extract_from_pdf(temp_path, filename)

                # Remove arquivo temporario
                try:
                    os.remove(temp_path)
                except:
                    pass

                if dados and 'error' not in dados:
                    instrumentos.append(dados)
                    print(f"[OK] Extraido: {dados.get('identificacao', dados.get('titulo', 'n/i'))}")
                else:
                    print(f"[ERRO] {dados.get('error')}")

            except Exception as e:
                print(f"[ERRO] {e}")

        if instrumentos:
            extracted_cache[session_id] = instrumentos
            return jsonify({
                'success': True,
                'message': f'{len(instrumentos)} documento(s) analisado(s) com IA!',
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

            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Voce e o assistente Metron. Responda perguntas sobre os documentos analisados. Se o usuario pedir um dado especifico (ex: 'qual o modelo?'), responda APENAS com a informacao em texto. NAO gere JSON a menos que explicitamente pedido."},
                    {"role": "user", "content": prompt}
                ]
            )

            resposta = completion.choices[0].message.content
            return jsonify({'success': True, 'message': resposta})

        except Exception as e:
            print(f"[ERRO] Chat: {e}")
            return jsonify({'success': True, 'message': f'Erro: {str(e)}'})

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

    # Chat normal com GPT-4o
    try:
        contexto = ""
        if dados:
            # Limita o contexto para nao estourar tokens se for muito grande
            json_str = json.dumps(dados, ensure_ascii=False, indent=2)
            if len(json_str) > 20000:
                json_str = json_str[:20000] + "... (troncado)"
            contexto = f"\n\nDADOS DO DOCUMENTO (Contexto):\n{json_str}"

        prompt = f"""Voce e o Metron (Assistente Labster).
        
DADOS ANEXADOS:
{contexto}

USUARIO: "{message}"

INSTRUCOES:
1. Responda a pergunta do usuario com base nos dados.
2. Seja direto e objetivo.
3. Se o usuario pedir apenas um campo (ex: 'modelo'), responda APENAS O VALOR em texto.
4. NAO gere blocos de JSON na resposta.
"""

        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Voce e um assistente util. Responda em texto simples."},
                {"role": "user", "content": prompt}
            ]
        )

        resposta = completion.choices[0].message.content
        return jsonify({'success': True, 'message': resposta})

    except Exception as e:
        print(f"[ERRO] Chat Msg: {e}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})


# ============================================================
# ROTAS - BANCO DE DADOS (MySQL)
# ============================================================
@app.route('/inserir-banco', methods=['POST'])
def inserir_banco():
    """Insere instrumentos extraidos no MySQL"""
    try:
        data = request.get_json()
        user_id = int(data.get('user_id', 1))

        if 'session_id' not in session:
            return jsonify({'success': False, 'message': 'Sessao nao encontrada.'}), 400

        session_id = session['session_id']
        # Prioriza os dados enviados pelo frontend (que podem ter sido editados)
        instrumentos = data.get('instrumentos', []) or extracted_cache.get(session_id, [])

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
            nome = buscar_valor('nome', inst) or buscar_valor('instrumento', inst) or buscar_valor('titulo', inst)
            fabricante = buscar_valor('fabricante', inst)
            modelo = buscar_valor('modelo', inst)
            numero_serie = buscar_valor('numero_serie', inst) or buscar_valor('serie', inst)
            descricao = buscar_valor('descricao', inst) or json.dumps(inst, ensure_ascii=False)[:500]
            periodicidade = buscar_valor('periodicidade', inst, 12)
            departamento = buscar_valor('departamento', inst) or buscar_valor('cliente', inst) or buscar_valor('localizacao', inst)
            responsavel = buscar_valor('responsavel', inst) or buscar_valor('solicitante', inst)
            status = buscar_valor('status', inst, 'Sem Calibracao')
            tipo_familia = buscar_valor('tipo_familia', inst) or buscar_valor('tipo_documento', inst)
            serie_desenv = buscar_valor('serie_desenv', inst) or buscar_valor('desenho', inst)
            criticidade = buscar_valor('criticidade', inst)
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
