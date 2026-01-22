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
    
    def salvar_instrumentos(self, session_id, instrumentos):
        """Salva instrumentos extraídos na sessão (antes de ir pro banco)"""
        if session_id in self.sessoes:
            self.sessoes[session_id]['instrumentos_pendentes'] = instrumentos
            self.sessoes[session_id]['ultimo_acesso'] = datetime.now()
    
    def obter_instrumentos(self, session_id):
        """Obtém instrumentos pendentes da sessão"""
        if session_id in self.sessoes:
            return self.sessoes[session_id].get('instrumentos_pendentes', [])
        return []
    
    def editar_campo_instrumento(self, session_id, identificador, campo, novo_valor):
        """
        Edita um campo de um instrumento específico
        
        Args:
            session_id: ID da sessão
            identificador: Pode ser a tag/identificação ou nome do arquivo PDF
            campo: Nome do campo a editar (ex: 'numero_serie', 'fabricante')
            novo_valor: Novo valor para o campo
        
        Returns:
            dict com sucesso, mensagem e instrumento editado
        """
        if session_id not in self.sessoes:
            return {'sucesso': False, 'mensagem': 'Sessão não encontrada'}
        
        instrumentos = self.sessoes[session_id].get('instrumentos_pendentes', [])
        
        if not instrumentos:
            return {'sucesso': False, 'mensagem': 'Nenhum instrumento pendente para editar. Faça upload dos PDFs primeiro.'}
        
        # Se identificador é None, usa o primeiro/único instrumento
        instrumento_encontrado = None
        indice = -1
        
        if identificador is None:
            if len(instrumentos) == 1:
                instrumento_encontrado = instrumentos[0]
                indice = 0
            else:
                return {
                    'sucesso': False,
                    'mensagem': f'Há {len(instrumentos)} instrumentos na sessão. Especifique qual deseja editar usando a tag ou nome do arquivo.'
                }
        else:
            # Procura o instrumento pelo identificador (tag ou arquivo)
            pass
        
            for i, inst in enumerate(instrumentos):
                # Verifica se é a identificação/tag
                if inst.get('identificacao', '').lower() == identificador.lower():
                    instrumento_encontrado = inst
                    indice = i
                    break
                # Verifica se é o nome do arquivo (sem extensão)
                arquivo_origem = inst.get('arquivo_origem', '')
                if arquivo_origem:
                    nome_arquivo = arquivo_origem.replace('.pdf', '').lower()
                    if identificador.lower() in nome_arquivo or nome_arquivo in identificador.lower():
                        instrumento_encontrado = inst
                        indice = i
                        break
        
        if instrumento_encontrado is None:
            msg = f'Instrumento "{identificador}" não encontrado. Verifique a tag ou nome do arquivo.' if identificador else 'Instrumento não encontrado.'
            return {
                'sucesso': False, 
                'mensagem': msg
            }
        
        # Guarda valor antigo
        valor_antigo = instrumento_encontrado.get(campo, 'n/i')
        
        # Atualiza o campo DIRETAMENTE no objeto da lista
        instrumentos[indice][campo] = novo_valor
        
        # DEBUG: Verifica se a edição foi aplicada
        print(f"🔧 [DEBUG] Editando campo '{campo}': '{valor_antigo}' → '{novo_valor}'")
        print(f"🔧 [DEBUG] Valor após edição: {instrumentos[indice].get(campo)}")
        
        # Salva de volta (garantia)
        self.sessoes[session_id]['instrumentos_pendentes'] = instrumentos
        self.sessoes[session_id]['ultimo_acesso'] = datetime.now()
        
        # DEBUG: Confirma que foi salvo
        instrumentos_salvos = self.sessoes[session_id]['instrumentos_pendentes']
        print(f"🔧 [DEBUG] Valor salvo na sessão: {instrumentos_salvos[indice].get(campo)}")
        
        return {
            'sucesso': True,
            'mensagem': f'Campo "{campo}" atualizado com sucesso!',
            'instrumento': instrumentos[indice],  # Retorna o objeto atualizado
            'valor_antigo': valor_antigo,
            'valor_novo': novo_valor,
            'campo': campo
        }
    
    def limpar_instrumentos(self, session_id):
        """Limpa instrumentos pendentes após inserção no banco"""
        if session_id in self.sessoes:
            self.sessoes[session_id]['instrumentos_pendentes'] = []


# Instância global
gerenciador_sessoes = GerenciadorSessoes()
