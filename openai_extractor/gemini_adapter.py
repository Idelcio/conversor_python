"""
Gemini Adapter for Metron
Permite usar o Google Gemini (1.5 Flash) como backend de extracao e chat.
"""
import os
import json
import fitz  # PyMuPDF
import google.generativeai as genai
from .prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT, JSON_SCHEMA_PROMPT, CONVERSATIONAL_PROMPT
from .security import SecurityValidator

class GeminiAdapter:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
             raise ValueError("GOOGLE_API_KEY not found. Configure no .env!")
        
        genai.configure(api_key=self.api_key)
        # Configura o modelo com o System Prompt
        try:
            self.model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                system_instruction=SYSTEM_PROMPT
            )
        except Exception as e:
            print(f"[AVISO] '{e}'. Tentando 'gemini-pro'...")
            self.model = genai.GenerativeModel(
                model_name='gemini-pro',
                system_instruction=SYSTEM_PROMPT
            )
        self.validator = SecurityValidator()
        print("[OK] Gemini Adapter (Google) inicializado!")

    def pdf_to_parts(self, pdf_path, max_pages=3):
        """Converte PDF para partes de imagem aceitas pelo Gemini"""
        parts = []
        try:
            doc = fitz.open(pdf_path)
            num_pages = min(len(doc), max_pages)
            print(f"[GEMINI] Convertendo {num_pages} paginas do PDF...")
            for i in range(num_pages):
                page = doc[i]
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                
                parts.append({
                    "mime_type": "image/png",
                    "data": img_bytes
                })
            doc.close()
        except Exception as e:
            print(f"[ERRO] Falha na conversao do PDF: {e}")
        return parts

    def extract_from_pdf(self, pdf_path, filename="", user_prompt=""):
        """Extracao via Gemini Vision"""
        # Validacao Basica
        is_valid, error = self.validator.validate_pdf(filename or pdf_path)
        if not is_valid: return {"error": error}

        parts = self.pdf_to_parts(pdf_path)
        if not parts: return {"error": "Falha ao ler imagens do PDF"}

        # Logica de Prompt
        is_json_mode = False
        prompt_text = EXTRACTION_PROMPT

        # Se usuario pediu especificamente JSON ou Dados
        keywords = ['json', 'banco', 'estruturar', 'extrair', 'tabela']
        if user_prompt and any(k in user_prompt.lower() for k in keywords):
             prompt_text = JSON_SCHEMA_PROMPT
             is_json_mode = True
             prompt_text += f"\n\nCONTEXTO DO USUARIO: {user_prompt}"
        elif user_prompt:
             # Modo Conversacional
             prompt_text = CONVERSATIONAL_PROMPT.replace("{user_prompt}", user_prompt)

        # Configuracao de Geracao
        config = genai.GenerationConfig(temperature=0.2)
        if is_json_mode:
            config.response_mime_type = "application/json"

        print(f"[GEMINI] Enviando para AI (JSON Mode={is_json_mode})...")
        
        try:
            # Chama API
            response = self.model.generate_content([prompt_text] + parts, generation_config=config)
            text_resp = response.text
            
            # Processa Resposta
            if is_json_mode:
                try:
                    data = json.loads(text_resp)
                except:
                    data = {"identificacao": "Erro Parse JSON", "descricao": text_resp}
            else:
                 # Se for texto livre/chat sobre PDF
                 data = {
                     "identificacao": "Resumo Gemini",
                     "nome": "Analise Conversacional",
                     "descricao": text_resp,
                     "is_text_response": True,
                     "outros_dados": "Resposta gerada em modo chat"
                 }
                 # Tentar parsear se magicamente vier json
                 try:
                     clean = text_resp.replace('```json', '').replace('```', '')
                     if '{' in clean:
                         data = json.loads(clean)
                 except:
                     pass

            data['arquivo_origem'] = filename
            print("[OK] Gemini processou com sucesso.")
            return data

        except Exception as e:
            print(f"[GEMINI-ERR] {e}")
            return {"error": str(e)}

    def ask(self, prompt):
        """Chat simples de texto"""
        clean_prompt = self.validator.sanitize_message(prompt)
        try:
             # O system prompt ja esta configurado no model
             response = self.model.generate_content(clean_prompt)
             return response.text
        except Exception as e:
             return f"Erro Gemini Chat: {str(e)}"
