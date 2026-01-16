"""
Gerenciador de sessões de chat para manter contexto das conversas
"""

from datetime import datetime, timedelta
import uuid

class GerenciadorSessoes:
    """Gerencia sessões de chat com histórico de mensagens"""
    
    def __init__(self):
        self.sessoes = {}
        self.tempo_expiracao = timedelta(hours=2)  # Sessões expiram após 2 horas
    
    def criar_sessao(self):
        """Cria uma nova sessão e retorna o ID"""
        session_id = str(uuid.uuid4())
        self.sessoes[session_id] = {
            'historico': [],
            'contexto': {},  # Informações extraídas (nome, preferências, etc)
            'criado_em': datetime.now(),
            'ultimo_acesso': datetime.now()
        }
        return session_id
    
    def obter_sessao(self, session_id):
        """Obtém uma sessão existente ou cria uma nova"""
        if session_id and session_id in self.sessoes:
            sessao = self.sessoes[session_id]
            
            # Verifica se expirou
            if datetime.now() - sessao['ultimo_acesso'] > self.tempo_expiracao:
                del self.sessoes[session_id]
                return self.criar_sessao(), self.sessoes[self.criar_sessao()]
            
            sessao['ultimo_acesso'] = datetime.now()
            return session_id, sessao
        else:
            novo_id = self.criar_sessao()
            return novo_id, self.sessoes[novo_id]
    
    def adicionar_mensagem(self, session_id, role, content):
        """Adiciona uma mensagem ao histórico"""
        if session_id in self.sessoes:
            self.sessoes[session_id]['historico'].append({
                'role': role,
                'content': content,
                'timestamp': datetime.now()
            })
            
            # Limita histórico a últimas 20 mensagens
            if len(self.sessoes[session_id]['historico']) > 20:
                self.sessoes[session_id]['historico'] = self.sessoes[session_id]['historico'][-20:]
    
    def atualizar_contexto(self, session_id, chave, valor):
        """Atualiza informações de contexto (ex: nome do usuário)"""
        if session_id in self.sessoes:
            self.sessoes[session_id]['contexto'][chave] = valor
    
    def obter_contexto(self, session_id):
        """Obtém o contexto completo da sessão"""
        if session_id in self.sessoes:
            return self.sessoes[session_id]['contexto']
        return {}
    
    def obter_historico(self, session_id, limite=10):
        """Obtém o histórico de mensagens"""
        if session_id in self.sessoes:
            historico = self.sessoes[session_id]['historico']
            return historico[-limite:] if len(historico) > limite else historico
        return []
    
    def limpar_sessoes_expiradas(self):
        """Remove sessões expiradas"""
        agora = datetime.now()
        sessoes_expiradas = [
            sid for sid, sessao in self.sessoes.items()
            if agora - sessao['ultimo_acesso'] > self.tempo_expiracao
        ]
        for sid in sessoes_expiradas:
            del self.sessoes[sid]
        
        return len(sessoes_expiradas)


# Instância global
gerenciador_sessoes = GerenciadorSessoes()
