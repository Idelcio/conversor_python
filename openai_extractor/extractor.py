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

from .prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT, SECURITY_MESSAGES
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
        """
        Converte páginas do PDF em imagens base64
        
        Args:
            pdf_path: Caminho do PDF
            max_pages: Número máximo de páginas para processar
            
        Returns:
            Lista de imagens em base64
        """
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
    
    def extract_from_pdf(self, pdf_path: str, filename: str = "") -> Dict:
        """
        Extrai dados do certificado usando OpenAI Vision
        
        Args:
            pdf_path: Caminho do PDF
            filename: Nome do arquivo original
            
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
                            "text": EXTRACTION_PROMPT
                        }
                    ]
                }
            ]
            
            # Adiciona imagens
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
                print(f"[ERRO] JSON invalido. Resposta bruta:")
                print(content[:500])
                return {"error": f"Resposta da IA nao esta em formato JSON valido: {str(e)}"}

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
        
        # Se chegou aqui e não tem PDF, pede upload
        if not has_pdf:
            return SECURITY_MESSAGES['no_pdf']
        
        # Caso contrário, processa normalmente
        return "PDF recebido! Processando extração..."
    
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
