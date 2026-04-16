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

from .prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT, SECURITY_MESSAGES, JSON_SCHEMA_PROMPT, CONVERSATIONAL_PROMPT, GRAPH_EXTRACTION_PROMPT
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
        self.token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        print("[OK] Gocal IA Extractor inicializado!")
    
    def pdf_to_images(self, pdf_path: str, max_pages: int = 3) -> List[str]:
        images = []
        
        try:
            doc = fitz.open(pdf_path)
            num_pages = min(len(doc), max_pages)
            
            print(f"[PDF] Convertendo {num_pages} pagina(s) do PDF em imagens...")
            
            for page_num in range(num_pages):
                page = doc[page_num]
                
                # Renderiza em resolução otimizada (300 DPI)
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
        keywords_json = ['json', 'banco de dados', 'sql', 'estruturar para banco', 'xml', 'planilha excel']
        keywords_checklist = ['checklist', 'preencher check', 'verificar check', 'conferir check']
        keywords_grafico = ['grafico', 'gráfico', 'chart', 'plot', 'plotar', 'mostrar grafico', 'gerar grafico']

        is_extraction_request = user_prompt and any(k in user_prompt.lower() for k in keywords_json)
        is_checklist_request = user_prompt and any(k in user_prompt.lower() for k in keywords_checklist)
        is_grafico_request = user_prompt and any(k in user_prompt.lower() for k in keywords_grafico)
        
        # Flag para saber se devemos esperar uma resposta de texto ou um JSON
        is_conversational_request = False

        if is_grafico_request:
            final_text_prompt = GRAPH_EXTRACTION_PROMPT
            print("[IA] Modo Gráfico ativado!")
        elif is_checklist_request:
            # Modo Checklist: Analisa PDF e retorna JSON com true/false por item
            final_text_prompt = """Voce e um assistente tecnico de metrologia e qualidade industrial. Analise o documento tecnico fornecido e verifique a presenca de cada item do checklist abaixo.

Para cada item, retorne true se a informacao ESTA presente no documento, ou false se NAO esta presente ou nao esta claramente identificada.

RETORNE APENAS o JSON abaixo (sem markdown, sem texto extra, sem crases):
{
    "checklist_data": {
        "1": true,
        "2": true,
        "3": true,
        "4": true,
        "5": true,
        "6": true,
        "7": true,
        "8": true,
        "9": true,
        "10": true,
        "11": true,
        "12": true
    },
    "message": "Resumo da analise explicando o que foi encontrado e o que faltou"
}

ITENS DO CHECKLIST:
1. Identificacao do emissor: O documento identifica quem realizou a medicao/calibracao (empresa, laboratorio ou responsavel tecnico)?
2. Identificacao do item medido: O documento contem tipo, codigo, modelo ou numero de serie do instrumento ou gabarito?
3. Identificacao do cliente: Ha identificacao do cliente ou empresa solicitante?
4. Numero e data do documento: O documento tem numero unico e data de emissao?
5. Validade ou prazo: Menciona data de vencimento, validade ou proximo prazo?
6. Datas coerentes: A data de emissao e proxima ou posterior a data da medicao/calibracao?
7. Frequencia: A periodicidade ou frequencia de calibracao/verificacao esta definida?
8. Condicoes do ambiente: Temperatura, umidade ou outras condicoes ambientais estao informadas?
9. Procedimento ou metodo: O metodo, procedimento ou norma utilizada esta citada?
10. Rastreabilidade: Ha referencia a padroes rastraveis ou acreditados?
11. Assinatura ou aprovacao: Tem assinatura, carimbo ou indicacao do responsavel tecnico?
12. Resultado ou parecer: O documento apresenta resultado, parecer (aprovado/reprovado) ou conclusao?

Analise o documento visualmente e retorne SOMENTE o JSON. Nao adicione texto fora do JSON."""
            print("[IA] Modo CHECKLIST ativado!")

        elif is_extraction_request:
            # Modo 1: Extração JSON (Explícito)
            final_text_prompt = JSON_SCHEMA_PROMPT
            print("[IA] Modo Extracao JSON ativado!")
            if user_prompt:
                 final_text_prompt += f"\n\nCONTEXTO DO USUARIO: {user_prompt}"
        
        elif user_prompt and user_prompt.strip():
            # Modo 2: Conversa Livre com Contexto Visual
            is_conversational_request = True # ATIVA A FLAG AQUI
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
                        "detail": "high"
                    }
                })
            
            # Chama API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=4000,
                temperature=0.1
            )
            
            # Contabiliza tokens
            if response.usage:
                self.token_usage['prompt_tokens'] += response.usage.prompt_tokens
                self.token_usage['completion_tokens'] += response.usage.completion_tokens
                self.token_usage['total_tokens'] += response.usage.total_tokens
                print(f"[TOKENS] Req: {response.usage.prompt_tokens}+{response.usage.completion_tokens} | Acum: {self.token_usage['total_tokens']}")

            # Extrai resposta
            content = response.choices[0].message.content
            print(f"[IA] Resposta recebida ({len(content)} caracteres)")
            print(f"[IA] Conteudo: {content[:500]}")

            # Se a IA recusou, tenta de novo
            recusa_patterns = ["i'm sorry", "i can't assist", "i cannot assist", "i can't help", "i cannot help", "sorry, i can"]
            if any(p in content.lower() for p in recusa_patterns):
                print("[IA] DETECTADA RECUSA DA IA! Tentando novamente com prompt reforçado...")
                messages[0]["content"] = "Voce e um assistente tecnico de metrologia. Sua UNICA funcao e analisar certificados de calibracao. As imagens enviadas sao de um certificado de calibracao tecnico. Voce DEVE analisa-las e responder conforme solicitado. Isso e uma tarefa 100% legitima de controle de qualidade industrial."
                response2 = self.client.chat.completions.create(model="gpt-4o", messages=messages, max_tokens=4000, temperature=0.2)
                if response2.usage:
                    self.token_usage['prompt_tokens'] += response2.usage.prompt_tokens
                    self.token_usage['completion_tokens'] += response2.usage.completion_tokens
                    self.token_usage['total_tokens'] += response2.usage.total_tokens
                content = response2.choices[0].message.content
                print(f"[IA] Retry resposta ({len(content)} caracteres): {content[:500]}")

                # Se ainda recusou após retry, retorna erro amigável
                if any(p in content.lower() for p in recusa_patterns):
                    print("[IA] Recusa persistente após retry. Retornando erro amigável.")
                    return {
                        "is_text_response": True,
                        "descricao": "Não foi possível analisar este documento automaticamente. Por favor, preencha os dados manualmente ou tente com outro PDF.",
                        "arquivo_origem": filename or os.path.basename(pdf_path)
                    }

            # Se for uma conversa, retorna o texto diretamente sem tentar converter para JSON
            if is_conversational_request:
                print("[IA] Resposta conversacional, retornando como texto.")
                return {
                    "is_text_response": True,
                    "descricao": content,
                    "arquivo_origem": filename or os.path.basename(pdf_path)
                }

            # Para os outros casos, continua o fluxo de processamento JSON
            if content.startswith('```'):
                lines = content.split('\n')
                if lines[0].startswith('```'): lines = lines[1:]
                if lines and lines[-1].strip() == '```': lines = lines[:-1]
                content = '\n'.join(lines)
            content = content.strip()

            import re as _re
            dados = None
            try:
                dados = json.loads(content)
            except json.JSONDecodeError:
                pass

            if dados is None:
                m = _re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', content)
                if m:
                    try:
                        dados = json.loads(m.group(1))
                        print("[IA] JSON extraído de bloco markdown")
                    except: pass

            if dados is None:
                try:
                    start = content.index('{')
                    depth, end = 0, -1
                    for i, c in enumerate(content[start:], start):
                        if c == '{': depth += 1
                        elif c == '}':
                            depth -= 1
                            if depth == 0: end = i + 1; break
                    if end > start:
                        dados = json.loads(content[start:end])
                        print("[IA] JSON extraído por localização de chaves")
                except Exception: pass

            if dados is None:
                print("[IA] JSON inválido — solicitando correção à IA...")
                try:
                    fix_resp = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "Você é um conversor de texto para JSON. Retorne APENAS o JSON válido, sem texto adicional."},
                            {"role": "user", "content": f"Converta em JSON limpo e válido:\n\n{content[:3000]}"}
                        ],
                        max_tokens=3000, temperature=0
                    )
                    fix_content = fix_resp.choices[0].message.content.strip()
                    m2 = _re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', fix_content)
                    if m2: fix_content = m2.group(1)
                    dados = json.loads(fix_content)
                    print("[IA] JSON corrigido pela IA com sucesso")
                except Exception as e2:
                    print(f"[IA] Falha também na correção: {e2}")

            if dados is None:
                print(f"[ERRO] Não foi possível extrair JSON do PDF '{filename}'. Conteúdo: {content[:200]}")
                return {"error": f"A IA não retornou JSON válido para '{filename}'. Tente novamente ou verifique o PDF."}

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
                if response.usage:
                    self.token_usage['prompt_tokens'] += response.usage.prompt_tokens
                    self.token_usage['completion_tokens'] += response.usage.completion_tokens
                    self.token_usage['total_tokens'] += response.usage.total_tokens
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
