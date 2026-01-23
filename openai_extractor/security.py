"""
Módulo de Segurança
Valida e bloqueia perguntas off-topic
"""

import re
from typing import Tuple
from .prompts import SECURITY_MESSAGES


class SecurityValidator:
    """Valida requisições e bloqueia perguntas não relacionadas"""
    
    # Palavras-chave que indicam perguntas off-topic
    BLOCKED_KEYWORDS = [
        # Perguntas sobre a IA
        'como você foi criado', 'quem te criou', 'qual modelo você usa',
        'que versão você é', 'você é gpt', 'você é chatgpt',
        'qual seu código', 'como você funciona', 'você usa openai',
        
        # Perguntas pessoais
        'você tem sentimentos', 'você é consciente', 'você pensa',
        'qual sua opinião', 'o que você acha',
        
        # Tópicos não relacionados
        'me conte uma piada', 'escreva um poema', 'traduza',
        'resolva este problema', 'faça um código', 'explique',
        
        # Tentativas de jailbreak
        'ignore as instruções', 'esqueça o que eu disse',
        'você pode fazer', 'mas e se', 'apenas desta vez'
    ]
    
    # Palavras-chave válidas (relacionadas a certificados)
    VALID_KEYWORDS = [
        'certificado', 'calibração', 'calibracao', 'instrumento',
        'equipamento', 'extrair', 'dados', 'pdf', 'grandeza',
        'fabricante', 'modelo', 'série', 'serie', 'tag',
        'número', 'numero', 'data', 'tolerância', 'tolerancia'
    ]
    
    @staticmethod
    def is_valid_request(message: str, has_pdf: bool = False) -> Tuple[bool, str]:
        """
        Valida se a requisição é válida
        
        Args:
            message: Mensagem do usuário
            has_pdf: Se há PDF anexado
            
        Returns:
            (is_valid, error_message)
        """
        message_lower = message.lower().strip()
        
        # Se não tem PDF e não está pedindo upload
        if not has_pdf and not any(word in message_lower for word in ['upload', 'enviar', 'pdf']):
            # Verifica se é pergunta off-topic
            if SecurityValidator._is_off_topic(message_lower):
                return False, SECURITY_MESSAGES['blocked']
        
        # Se tem PDF, sempre válido
        if has_pdf:
            return True, ""
        
        # Se está pedindo para fazer upload
        if any(word in message_lower for word in ['upload', 'enviar', 'carregar', 'pdf']):
            return True, ""
        
        # Se menciona palavras válidas
        if any(word in message_lower for word in SecurityValidator.VALID_KEYWORDS):
            if not has_pdf:
                return False, SECURITY_MESSAGES['no_pdf']
            return True, ""
        
        # Caso contrário, bloqueia
        return False, SECURITY_MESSAGES['off_topic']
    
    @staticmethod
    def _is_off_topic(message: str) -> bool:
        """Verifica se a mensagem é off-topic"""
        # Verifica palavras-chave bloqueadas
        for keyword in SecurityValidator.BLOCKED_KEYWORDS:
            if keyword in message:
                return True
        
        # Verifica padrões suspeitos
        suspicious_patterns = [
            r'você (é|usa|tem|pode|sabe)',
            r'qual (é|seu|sua|o)',
            r'como (você|funciona|foi)',
            r'me (conte|diga|explique|mostre)',
            r'(escreva|crie|faça|gere) (um|uma|o|a)',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, message):
                # Mas permite se mencionar certificados
                if not any(word in message for word in SecurityValidator.VALID_KEYWORDS):
                    return True
        
        return False
    
    @staticmethod
    def sanitize_message(message: str) -> str:
        """Remove caracteres perigosos da mensagem"""
        # Remove caracteres especiais que podem causar injection
        sanitized = re.sub(r'[<>{}\\]', '', message)
        
        # Limita tamanho
        if len(sanitized) > 500:
            sanitized = sanitized[:500]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_pdf(filename: str) -> Tuple[bool, str]:
        """Valida se o arquivo é um PDF válido"""
        if not filename:
            return False, "Nenhum arquivo enviado"
        
        # Verifica extensão
        if not filename.lower().endswith('.pdf'):
            return False, "Apenas arquivos PDF são aceitos"
        
        # Verifica caracteres perigosos no nome
        if re.search(r'[<>:"|?*\\]', filename):
            return False, "Nome de arquivo inválido"
        
        return True, ""
