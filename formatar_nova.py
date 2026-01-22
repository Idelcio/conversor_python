def formatar_confirmacao_edicao_nova(resultado_edicao):
    """
    Formata uma mensagem HTML de confirmação da edição - VERSÃO MODERNA
    """
    if not resultado_edicao.get('sucesso'):
        return f"❌ {resultado_edicao.get('mensagem', 'Erro desconhecido')}"
    
    inst = resultado_edicao['instrumento']
    campo = resultado_edicao['campo']
    valor_antigo = resultado_edicao['valor_antigo']
    valor_novo = resultado_edicao['valor_novo']
    
    # Traduz nome do campo para exibição
    nomes_campos = {
        'identificacao': 'Identificação/Tag',
        'nome': 'Nome',
        'fabricante': 'Fabricante',
        'modelo': 'Modelo',
        'numero_serie': 'Número de Série',
        'descricao': 'Descrição',
        'periodicidade': 'Periodicidade',
        'departamento': 'Departamento',
        'responsavel': 'Responsável',
        'status': 'Status',
        'tipo_familia': 'Tipo/Família',
        'data_calibracao': 'Data de Calibração',
        'data_emissao': 'Data de Emissão'
    }
    
    nome_campo_exibicao = nomes_campos.get(campo, campo)
    
    html = f"""<div style="background: white; border-radius: 12px; padding: 20px; margin: 15px 0; color: #333; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 2px solid #4CAF50;">
    <div style="display: flex; align-items: center; margin-bottom: 15px;">
        <span style="font-size: 32px; margin-right: 12px;">✅</span>
        <h3 style="margin: 0; font-size: 20px; font-weight: 600; color: #2e7d32;">Pronto! Campo alterado com sucesso</h3>
    </div>
    
    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #2196F3;">
        <div style="font-size: 14px; color: #666; margin-bottom: 8px;">📄 Instrumento</div>
        <div style="font-size: 16px; font-weight: 500; color: #000;">{inst.get('identificacao', 'n/i')} - {inst.get('nome', 'n/i')}</div>
    </div>
    
    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; border-left: 4px solid #FF9800;">
        <div style="font-size: 14px; color: #666; margin-bottom: 8px;">🔧 {nome_campo_exibicao}</div>
        <div style="display: flex; align-items: center; gap: 12px; font-size: 18px;">
            <span style="text-decoration: line-through; color: #999;">{valor_antigo}</span>
            <span style="font-size: 24px; color: #666;">→</span>
            <span style="font-weight: 700; background: #4CAF50; color: white; padding: 6px 12px; border-radius: 6px;">{valor_novo}</span>
        </div>
    </div>
</div>"""
    
    return html
