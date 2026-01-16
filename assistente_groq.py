"""
Módulo de integração com Groq API para processamento de linguagem natural
"""

import os
from pathlib import Path
from groq import Groq

# Carrega variáveis do arquivo .env
def carregar_env():
    """Carrega variáveis de ambiente do arquivo .env"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Carrega .env ao importar o módulo
carregar_env()

class AssistenteGroq:
    """Assistente de conversação usando Groq API com LLaMA"""
    
    def __init__(self, api_key=None):
        """
        Inicializa o cliente Groq
        
        Args:
            api_key: Chave da API Groq (se None, busca de variável de ambiente)
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        
        if not self.api_key or self.api_key == 'sua_chave_aqui':
            print("⚠️  AVISO: Groq API key não configurada. Chat inteligente desabilitado.")
            self.client = None
        else:
            try:
                self.client = Groq(api_key=self.api_key)
                print("[OK] Groq API inicializada com sucesso!")
            except Exception as e:
                print(f"[ERRO] Erro ao inicializar Groq: {e}")
                self.client = None
    
    def esta_disponivel(self):
        """Verifica se o assistente está disponível"""
        return self.client is not None
    
    def processar_comando(self, comando, contexto="", historico=None, contexto_usuario=None):
        """
        Processa um comando do usuário usando LLaMA
        
        Args:
            comando: Comando/pergunta do usuário
            contexto: Contexto adicional (opcional)
            historico: Lista de mensagens anteriores (opcional)
            contexto_usuario: Dict com informações do usuário (nome, etc)
            
        Returns:
            dict com 'tipo', 'resposta', 'campos' e 'contexto_atualizado'
        """
        if not self.esta_disponivel():
            return {
                'tipo': 'erro',
                'resposta': 'Assistente inteligente não disponível. Configure GROQ_API_KEY.'
            }
        
        try:
            # Monta informações de contexto do usuário
            info_contexto = ""
            if contexto_usuario:
                if contexto_usuario.get('nome'):
                    info_contexto += f"\nNome do usuário: {contexto_usuario['nome']}"
                if contexto_usuario.get('num_pdfs'):
                    info_contexto += f"\nPDFs carregados: {contexto_usuario['num_pdfs']}"
                    if contexto_usuario.get('nomes_pdfs'):
                        info_contexto += f"\nNomes dos arquivos: {', '.join(contexto_usuario['nomes_pdfs'])}"
            
            # Prompt do sistema para guiar o LLaMA
            system_prompt = f"""Você é o Metron, um assistente especializado em extração de dados de certificados de calibração de instrumentos, mas também pode ajudar com perguntas gerais.
{info_contexto}

Seu trabalho é entender comandos do usuário de forma natural e classificá-los em:

1. **CUMPRIMENTO** - Saudações, agradecimentos, despedidas
   Exemplos: "oi", "bom dia", "obrigado", "tchau"
   Resposta: Seja amigável e acolhedor. Se souber o nome do usuário, use-o!

2. **PERGUNTA_INFO** - Perguntas sobre o sistema, funcionalidades, campos do banco, OU perguntas gerais/cálculos
   Exemplos: 
   - "quais informações vão pro banco?"
   - "o que você faz?"
   - "quanto é 10 + 10?"
   - "qual a capital do Brasil?"
   Resposta: Responda de forma clara e objetiva. Para cálculos, faça o cálculo e responda.

3. **EXTRACAO** - Comandos para extrair dados dos PDFs (REQUER PDFs)
   Exemplos: "extrair tudo", "quero só fabricante e modelo", "me mostra as tags"
   Resposta: Se não houver PDFs, peça gentilmente para fazer upload
   Campos disponíveis: identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, data_calibracao, data_emissao

4. **FILTRO** - Comandos para filtrar/buscar dados específicos (REQUER PDFs)
   Exemplos: "mostra só os da Fluke", "instrumentos calibrados em 2024"
   Resposta: Se não houver PDFs, peça gentilmente para fazer upload

5. **EXCLUSAO** - Perguntas sobre excluir/deletar dados do banco
   Exemplos: "pode excluir?", "como deletar?", "apagar do banco"
   Resposta: "🚫 Desculpe, não tenho permissão para excluir dados do banco. Apenas posso extrair informações de PDFs e inserir novos instrumentos. Para exclusões, entre em contato com o administrador do sistema."

**IMPORTANTE:**
- Seja conversacional, amigável e prestativo
- Use emojis quando apropriado
- Responda perguntas gerais e cálculos simples diretamente
- Para comandos de EXTRACAO, se o usuário pedir campos específicos, identifique-os e retorne no array "campos"
- Se for "extrair tudo" ou similar, não inclua o array "campos" (ou deixe vazio)
- Se o usuário mencionar o nome dele, extraia e retorne em "nome_usuario"
- Se perguntar sobre EXCLUSÃO, deixe claro que você NÃO tem essa permissão

Responda SEMPRE em JSON válido no formato:
{{
    "tipo": "CUMPRIMENTO|PERGUNTA_INFO|EXTRACAO|FILTRO|EXCLUSAO",
    "resposta": "sua resposta amigável e contextual aqui",
    "campos": ["campo1", "campo2"],  // apenas para EXTRACAO com campos específicos
    "nome_usuario": "nome"  // apenas se o usuário mencionar o nome dele
}}"""

            # Adiciona contexto se fornecido
            mensagem_usuario = comando
            if contexto:
                mensagem_usuario = f"Contexto: {contexto}\n\nUsuário: {comando}"
            
            # Chama API Groq
            print(f"🤖 Processando com LLaMA: '{comando}'")
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Modelo LLaMA 3.3 ativo
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": mensagem_usuario}
                ],
                temperature=0.3,  # Baixa temperatura para respostas mais consistentes
                max_tokens=500
            )
            
            # Extrai resposta
            resposta_texto = response.choices[0].message.content.strip()
            print(f"📥 Resposta do LLaMA: {resposta_texto[:200]}...")
            
            # Tenta parsear JSON
            import json
            import re
            
            try:
                # Remove markdown code blocks se existirem
                if '```json' in resposta_texto:
                    resposta_texto = re.search(r'```json\s*(.*?)\s*```', resposta_texto, re.DOTALL).group(1)
                elif '```' in resposta_texto:
                    resposta_texto = re.search(r'```\s*(.*?)\s*```', resposta_texto, re.DOTALL).group(1)
                
                # Tenta encontrar o JSON no texto (ignora emojis e texto antes/depois)
                json_match = re.search(r'\{.*\}', resposta_texto, re.DOTALL)
                if json_match:
                    resposta_texto = json_match.group(0)
                
                resultado = json.loads(resposta_texto)
                print(f"[OK] JSON parseado: tipo={resultado.get('tipo')}, campos={resultado.get('campos', [])}")
            except Exception as e:
                print(f"[AVISO] Erro ao parsear JSON: {e}")
                print(f"   Texto recebido: {resposta_texto[:300]}")
                # Se não for JSON válido, retorna como resposta genérica
                resultado = {
                    'tipo': 'RESPOSTA',
                    'resposta': resposta_texto
                }
            
            return resultado
            
        except Exception as e:
            print(f"[ERRO] Erro ao processar com Groq: {e}")
            return {
                'tipo': 'erro',
                'resposta': f'Erro ao processar comando: {str(e)}'
            }
    
    def gerar_resposta_contextual(self, pergunta, dados_contexto=None):
        """
        Gera uma resposta contextual baseada em dados
        
        Args:
            pergunta: Pergunta do usuário
            dados_contexto: Dados relevantes para contexto (dict ou str)
            
        Returns:
            str: Resposta gerada
        """
        if not self.esta_disponivel():
            return "Assistente inteligente não disponível."
        
        try:
            contexto = ""
            if dados_contexto:
                if isinstance(dados_contexto, dict):
                    contexto = f"\n\nDados disponíveis: {json.dumps(dados_contexto, ensure_ascii=False)}"
                else:
                    contexto = f"\n\nContexto: {dados_contexto}"
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Você é um assistente prestativo que ajuda com certificados de calibração. Seja conciso e direto."},
                    {"role": "user", "content": pergunta + contexto}
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Erro ao gerar resposta: {str(e)}"


# Instância global (será inicializada no app.py)
assistente = None

def inicializar_assistente(api_key=None):
    """Inicializa o assistente global"""
    global assistente
    assistente = AssistenteGroq(api_key)
    return assistente
