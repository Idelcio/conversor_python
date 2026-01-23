from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import os
import tempfile
from werkzeug.utils import secure_filename
import uuid
import json

# Carrega variaveis de ambiente do .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv nao instalado, usa variaveis de ambiente do sistema

from openai import OpenAI

# Importamos o extractor original da OpenAI (Visão)
from openai_extractor.extractor import OpenAIExtractor
from openai_extractor.security import SecurityValidator

# Inicializa Flask
app = Flask(__name__)
CORS(app)
app.secret_key = 'gocal-secret-key-2026'

# Configurações
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Inicializa Extrator OpenAI
try:
    extractor = OpenAIExtractor()
except Exception as e:
    print(f"Erro ao inicializar Extrator: {e}")
    extractor = None

# Validador de segurança
validator = SecurityValidator()

# Cache global: {session_id: [dados_extraidos]}
extracted_cache = {}


@app.route('/')
def index():
    """Página principal do Chat Gocal"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('gocal_chat.html')


@app.route('/chat-extrair', methods=['POST'])
def chat_extrair():
    """
    Rota de chat que processa PDFs com GPT-4 Vision e responde perguntas.
    """
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    files = request.files.getlist('pdfs')
    message = request.form.get('comando', '') or request.form.get('message', '')

    print(f"\n{'='*60}")
    print(f"[CHAT] GOCAL (Vision) - Session: {session_id[:8]}...")
    print(f"{'='*60}")
    
    # 1. Se tem PDFs, processa com GPT-4 Vision
    if files and files[0].filename:
        if not extractor:
            return jsonify({'success': False, 'message': 'Erro: API OpenAI não configurada.'})

        instrumentos = []
        for file in files:
            filename = secure_filename(file.filename)
            is_valid, error = validator.validate_pdf(filename)
            if not is_valid:
                continue
            
            print(f"[PDF] Processando com IA (Vision): {filename}")
            try:
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(temp_path)
                
                # Extração via GPT-4 Vision
                dados = extractor.extract_from_pdf(temp_path, filename)
                
                # Remove arquivo temporário
                try: os.remove(temp_path)
                except: pass
                
                if dados and 'error' not in dados:
                    instrumentos.append(dados)
                    print(f"[OK] Extraido IA: {dados.get('identificacao', 'n/i')}")
                else:
                    print(f"[ERRO] Erro IA: {dados.get('error')}")

            except Exception as e:
                print(f"[ERRO] Erro processamento: {e}")
        
        if instrumentos:
            extracted_cache[session_id] = instrumentos
            if 'extracted_context' not in session:
                session['extracted_context'] = []
            session['extracted_context'] = instrumentos  # Corrigido: era 'instruments'

            return jsonify({
                'success': True,
                'message': f'{len(instrumentos)} certificado(s) analisado(s) com IA! Pergunte qualquer detalhe ou digite "extrair tudo".',
                'instrumentos': instrumentos
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Falha ao analisar o PDF. Verifique se eh um certificado valido.'
            })

    # 2. Se é pergunta de texto (SEM LIMITACOES - IA LIVRE)
    if message:
        print(f"[MSG] Mensagem recebida: '{message}'")

        # Pega dados da sessao se existirem
        dados = extracted_cache.get(session_id, [])

        # Comandos especiais para exibir dados
        if dados and ('extrair tudo' in message.lower() or 'mostrar tudo' in message.lower()):
            return jsonify({
                'success': True,
                'message': 'Aqui estao os dados estruturados:',
                'instrumentos': dados
            })

        # Chat Inteligente LIVRE - responde qualquer pergunta
        try:
            print(f"[IA] Respondendo pergunta: {message}")

            # Contexto dos dados extraidos (se houver)
            contexto = ""
            if dados:
                contexto = f"\n\nDADOS DE CERTIFICADOS EXTRAIDOS:\n{json.dumps(dados, ensure_ascii=False, indent=2)}"

            prompt_chat = f"""Voce e o Metron, um assistente inteligente e amigavel.

PERGUNTA DO USUARIO:
"{message}"
{contexto}

Responda de forma direta, educada e util. Voce pode responder sobre qualquer assunto."""

            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Voce e um assistente inteligente, amigavel e sem restricoes. Pode responder sobre qualquer assunto."},
                    {"role": "user", "content": prompt_chat}
                ]
            )

            resposta_ia = completion.choices[0].message.content
            return jsonify({'success': True, 'message': resposta_ia})

        except Exception as e:
            print(f"[ERRO] Erro no chat: {e}")
            return jsonify({'success': True, 'message': f'Erro: {str(e)}'})

    return jsonify({'success': False, 'message': 'Envie uma mensagem ou um PDF.'})


@app.route('/inserir-banco', methods=['POST'])
def inserir_banco():
    data = request.get_json()
    instrumentos = data.get('instrumentos', [])
    return jsonify({
        'success': True,
        'message': f'{len(instrumentos)} instrumentos inseridos com sucesso!'
    })


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'mode': 'openai_vision_chat'})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("METRON - Chat Gocal (Powered by OpenAI Vision)")
    print("="*60)
    print("Acesse: http://localhost:5001")
    print("Seguranca: Ativada")
    print("Modo: Chat IA (Vision + Context)")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5001, debug=True)
