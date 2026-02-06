"""
OpenAI Extractor
Extrai dados de certificados usando GPT-4 Vision
"""

import os
import json
import base64
from typing import Dict, List, Optional
from openai import OpenAI
import fitz  # PyMuPDF

from .prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT, SECURITY_MESSAGES, JSON_SCHEMA_PROMPT, CONVERSATIONAL_PROMPT
from .security import SecurityValidator


class OpenAIExtractor:
    """Extrator de certificados usando OpenAI GPT-4 Vision"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o extrator
        
        Args:
            api_key: Chave da API (ou usa variável de ambiente)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("API Key nao configurada!")
        
        self.client = OpenAI(api_key=self.api_key)
        self.validator = SecurityValidator()
        print("[OK] Gocal IA Extractor inicializado!")
    
    def pdf_to_images(self, pdf_path: str, max_pages: int = 3) -> List[str]:
        images = []
        
        try:
            doc = fitz.open(pdf_path)
            num_pages = min(len(doc), max_pages)
            
            print(f"[PDF] Convertendo {num_pages} pagina(s) do PDF em imagens...")
            
            for page_num in range(num_pages):
                page = doc[page_num]
                
                # Renderiza em alta resolução (300 DPI)
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                
                # Converte para base64
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                images.append(img_base64)
                
                print(f"  [OK] Pagina {page_num + 1} convertida")
            
            doc.close()
            return images
            
        except Exception as e:
            print(f"[ERRO] Erro ao converter PDF: {e}")
            return []
    
    def extract_from_pdf(self, pdf_path: str, filename: str = "", user_prompt: str = "") -> Dict:
        """
        Extrai dados do certificado usando OpenAI Vision
        
        Args:
            pdf_path: Caminho do PDF
            filename: Nome do arquivo original
            user_prompt: Pergunta ou instrução especifica do usuário
            
        Returns:
            Dicionário com dados extraídos
        """
        # Valida PDF
        is_valid, error = self.validator.validate_pdf(filename or pdf_path)
        if not is_valid:
            return {"error": error}
        
        # Converte PDF para imagens
        images = self.pdf_to_images(pdf_path)
        if not images:
            return {"error": "Nao foi possivel processar o PDF"}
        
        print(f"[IA] Enviando para Gocal IA...")
        
        # Monta prompt - Lógica Hibrida (Conversa vs JSON vs Resumo vs Checklist)
        # Palavras-chave RESTRITIVAS para evitar ativar JSON enquanto conversa sobre tabelas
        keywords_json = ['json', 'banco de dados', 'sql', 'estruturar para banco', 'xml', 'planilha excel']
        keywords_checklist = ['checklist', 'preencher check', 'verificar check', 'conferir check']

        is_extraction_request = user_prompt and any(k in user_prompt.lower() for k in keywords_json)
        is_checklist_request = user_prompt and any(k in user_prompt.lower() for k in keywords_checklist)

        if is_checklist_request:
            # Modo Checklist: Analisa PDF e retorna JSON com true/false por item
            final_text_prompt = """Analise as imagens deste certificado de calibracao e verifique CADA item do checklist abaixo.
Para cada item, retorne true se o certificado ATENDE ao criterio, ou false se NAO atende ou a informacao nao esta presente.

RETORNE APENAS o JSON abaixo (sem markdown, sem texto extra):
{
    "checklist_data": {
        "1": true ou false,
        "2": true ou false,
        "3": true ou false,
        "4": true ou false,
        "5": true ou false,
        "6": true ou false,
        "7": true ou false,
        "8": true ou false,
        "9": true ou false,
        "10": true ou false,
        "11": true ou false,
        "12": true ou false
    },
    "message": "Resumo da analise explicando o que foi encontrado e o que faltou"
}

CRITERIOS DE CADA ITEM:
1. Identificacao do Laboratorio: O laboratorio e acreditado (RBC/INMETRO ou equivalente)?
2. Identificacao do Instrumento: O certificado contem tipo, marca, modelo, numero de serie, faixa de medicao e resolucao?
3. Local e Cliente: Ha identificacao do cliente e local da calibracao (in loco ou em laboratorio)?
4. Numero e Data do Certificado: O certificado tem numero unico e data de emissao?
5. Etiqueta/Selo: Menciona selo de calibracao ou validade?
6. Datas: A data de emissao e no maximo 7 dias apos a data de calibracao?
7. Frequencia: A periodicidade/frequencia de calibracao esta definida?
8. Condicoes Ambientais: Temperatura e umidade estao informadas?
9. Procedimento: O metodo/procedimento de calibracao esta citado?
10. Padroes: A rastreabilidade dos padroes esta citada?
11. Assinatura: Tem assinatura do responsavel tecnico?
12. Integridade: O instrumento esta em boas condicoes de uso?

IMPORTANTE: Retorne APENAS o JSON. Marque false quando a informacao NAO estiver presente no documento."""
            print("[IA] Modo CHECKLIST ativado!")

        elif is_extraction_request:
            # Modo 1: Extração JSON (Explícito)
            final_text_prompt = JSON_SCHEMA_PROMPT
            print("[IA] Modo Extracao JSON ativado!")
            if user_prompt:
                 final_text_prompt += f"\n\nCONTEXTO DO USUARIO: {user_prompt}"
        
        elif user_prompt and user_prompt.strip():
            # Modo 2: Conversa Livre com Contexto Visual
            # Usa o .format() ou f-string manual se o prompt tiver chaves {} extras cuidado
            # O CONVERSATIONAL_PROMPT tem {user_prompt}, entao .format funciona bem se nao tiver outros {}
            final_text_prompt = CONVERSATIONAL_PROMPT.replace("{user_prompt}", user_prompt)
            print("[IA] Modo Conversacional ativado!")
            
        else:
            # Modo 3: Resumo Padrão (Sem input do usuário)
            final_text_prompt = EXTRACTION_PROMPT
            print("[IA] Modo Resumo Padrão ativado!")

        try:
            # Prepara mensagens
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": final_text_prompt
                        }
                    ]
                }
            ]
            
            # Adiciona imagens (usa a lista já convertida acima)
            for img_base64 in images:
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}",
                        "detail": "high"  # Alta qualidade para melhor OCR
                    }
                })
            
            # Chama API - usando gpt-4o (suporta visao e JSON)
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=4000,
                temperature=0.1  # Baixa temperatura para respostas mais precisas
            )
            
            # Extrai resposta
            content = response.choices[0].message.content
            print(f"[IA] Resposta recebida ({len(content)} caracteres)")

            # Remove markdown code blocks se existirem
            if content.startswith('```'):
                # Remove ```json ou ``` do inicio
                lines = content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                # Remove ``` do final
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines)

            content = content.strip()

            try:
                dados = json.loads(content)
            except json.JSONDecodeError as e:
                # Fallback para resposta texto-livre (Modo ChatGPT)
                print(f"[IA] Resposta nao-JSON (texto livre). Adaptando...")
                dados = {
                    "identificacao": "Análise IA",
                    "nome": "Resposta Textual",
                    "descricao": content, # Conteudo completo
                    "outros_dados": "Texto extraído em formato livre",
                    "is_text_response": True
                }

            # Adiciona arquivo de origem
            dados['arquivo_origem'] = filename or os.path.basename(pdf_path)

            print(f"[OK] Extracao concluida!")
            print(f"   - Identificacao: {dados.get('identificacao', 'n/i')}")
            print(f"   - Nome: {dados.get('nome', 'n/i')}")
            print(f"   - Fabricante: {dados.get('fabricante', 'n/i')}")

            return dados

        except json.JSONDecodeError as e:
            print(f"[ERRO] Erro ao decodificar JSON: {e}")
            return {"error": "Resposta da IA nao esta em formato JSON valido"}
        
        except Exception as e:
            print(f"[ERRO] Erro na API OpenAI: {e}")
            return {"error": f"Erro ao processar: {str(e)}"}
    
    def chat(self, message: str, has_pdf: bool = False) -> str:
        """
        Processa mensagem do chat com validação de segurança
        
        Args:
            message: Mensagem do usuário
            has_pdf: Se há PDF anexado
            
        Returns:
            Resposta da IA ou mensagem de erro
        """
        # Sanitiza mensagem
        clean_message = self.validator.sanitize_message(message)
        
        # Valida requisição
        is_valid, error_msg = self.validator.is_valid_request(clean_message, has_pdf)
        
        if not is_valid:
            print(f"[BLOQUEADO] Requisicao bloqueada: {clean_message[:50]}...")
            return error_msg
        
        # Se chegou aqui e não tem PDF, responde como Chat (GPT-4o)
        if not has_pdf:
            try:
                # Chama API para chat normal
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": clean_message}
                    ],
                    max_tokens=2000,
                    temperature=0.7 
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[ERRO] Erro na API (Chat): {e}")
                return f"Desculpe, tive um problema ao processar sua mensagem: {str(e)}"
        
        # Se tem PDF, o fluxo segue via /chat-extrair (upload-async), entao aqui so confirma
        return "PDF carregado. Aguarde o processamento..."
    
    def extract_batch(self, pdf_paths: List[str]) -> List[Dict]:
        """
        Extrai dados de múltiplos PDFs
        
        Args:
            pdf_paths: Lista de caminhos dos PDFs
            
        Returns:
            Lista de dicionários com dados extraídos
        """
        resultados = []
        
        print(f"[BATCH] Processando {len(pdf_paths)} PDF(s)...")
        
        for i, pdf_path in enumerate(pdf_paths, 1):
            print(f"\n[{i}/{len(pdf_paths)}] Processando: {os.path.basename(pdf_path)}")
            
            dados = self.extract_from_pdf(pdf_path, os.path.basename(pdf_path))
            resultados.append(dados)
        
        print(f"\n[OK] Processamento em lote concluido!")
        return resultados
