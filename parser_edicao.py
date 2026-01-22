"""
Parser para interpretar comandos de edição de instrumentos
Exemplos:
- "muda o numero de serie do arquivo x34 de 456 para 123"
- "altera a tag do certificado ABC para XYZ"
- "corrige o fabricante do instrumento x para Mitutoyo"
"""

import re

# Mapeamento de termos comuns para nomes de campos no banco
MAPA_CAMPOS = {
    'tag': 'identificacao',
    'identificacao': 'identificacao',
    'identificação': 'identificacao',
    'codigo': 'identificacao',
    'código': 'identificacao',
    
    'nome': 'nome',
    'denominacao': 'nome',
    'denominação': 'nome',
    'instrumento': 'nome',
    
    'fabricante': 'fabricante',
    'marca': 'fabricante',
    
    'modelo': 'modelo',
    'model': 'modelo',
    
    'numero de serie': 'numero_serie',
    'número de série': 'numero_serie',
    'numero serie': 'numero_serie',
    'número série': 'numero_serie',
    'serie': 'numero_serie',
    'série': 'numero_serie',
    'serial': 'numero_serie',
    'ns': 'numero_serie',
    
    'descricao': 'descricao',
    'descrição': 'descricao',
    
    'periodicidade': 'periodicidade',
    
    'departamento': 'departamento',
    'endereco': 'departamento',
    'endereço': 'departamento',
    'local': 'departamento',
    
    'responsavel': 'responsavel',
    'responsável': 'responsavel',
    'cliente': 'responsavel',
    
    'status': 'status',
    
    'tipo': 'tipo_familia',
    'familia': 'tipo_familia',
    'família': 'tipo_familia',
    'tipo familia': 'tipo_familia',
    'tipo família': 'tipo_familia',
    
    'data de calibracao': 'data_calibracao',
    'data de calibração': 'data_calibracao',
    'data calibracao': 'data_calibracao',
    'data calibração': 'data_calibracao',
    'data': 'data_calibracao',
    
    'data de emissao': 'data_emissao',
    'data de emissão': 'data_emissao',
    'data emissao': 'data_emissao',
    'data emissão': 'data_emissao',
}


def normalizar_campo(campo_texto):
    """Converte texto do usuário para nome do campo no banco"""
    campo_lower = campo_texto.lower().strip()
    return MAPA_CAMPOS.get(campo_lower, campo_lower)


def extrair_comando_edicao(comando):
    """
    Extrai informações de um comando de edição
    
    Returns:
        dict com: {
            'tipo': 'EDICAO' ou None,
            'identificador': str (tag ou arquivo),
            'campo': str (nome do campo),
            'valor_novo': str,
            'valor_antigo': str ou None
        }
    """
    comando_lower = comando.lower().strip()
    
    # Padrões de comando de edição
    # Padrão 1: "muda/altera/corrige [campo] do [arquivo/certificado/instrumento] [id] de [antigo] para [novo]"
    # Padrão 2: "muda/altera/corrige [campo] do [arquivo/certificado/instrumento] [id] para [novo]"
    
    # Verbos de ação
    verbos = ['mud[ae]', 'alter[ae]', 'corrig[ae]', 'atualiz[ae]', 'troc[ae]']
    verbo_pattern = '|'.join(verbos)
    
    # Identificadores de instrumento
    id_tipos = ['arquivo', 'certificado', 'instrumento', 'pdf', 'tag', 'item']
    id_pattern = '|'.join(id_tipos)
    
    # PADRÃO ESPECIAL PARA DATAS: "muda a data de calibração de YYYY-MM-DD para YYYY-MM-DD"
    # Tenta primeiro com padrão de data específico
    pattern_data = rf'(?:{verbo_pattern})\s+(?:o\s+|a\s+)?(data\s+(?:de\s+)?(?:calibra[çc][ãa]o|emiss[ãa]o)?)\s+de\s+(\d{{4}}-\d{{2}}-\d{{2}})\s+para\s+(\d{{4}}-\d{{2}}-\d{{2}})'
    match_data = re.search(pattern_data, comando_lower)
    
    if match_data:
        campo_texto = match_data.group(1).strip()
        valor_antigo = match_data.group(2).strip()
        valor_novo = match_data.group(3).strip()
        
        campo = normalizar_campo(campo_texto)
        
        return {
            'tipo': 'EDICAO',
            'identificador': None,  # Datas geralmente são únicas, usa primeiro instrumento
            'campo': campo,
            'valor_novo': valor_novo,
            'valor_antigo': valor_antigo
        }
    
    # PADRÃO SIMPLIFICADO PARA DATAS: "muda a data de calibração para YYYY-MM-DD"
    pattern_data_simples = rf'(?:{verbo_pattern})\s+(?:o\s+|a\s+)?(data\s+(?:de\s+)?(?:calibra[çc][ãa]o|emiss[ãa]o)?)\s+para\s+(\d{{4}}-\d{{2}}-\d{{2}})'
    match_data_simples = re.search(pattern_data_simples, comando_lower)
    
    if match_data_simples:
        campo_texto = match_data_simples.group(1).strip()
        valor_novo = match_data_simples.group(2).strip()
        
        campo = normalizar_campo(campo_texto)
        
        return {
            'tipo': 'EDICAO',
            'identificador': None,
            'campo': campo,
            'valor_novo': valor_novo,
            'valor_antigo': None
        }
    
    # Padrão completo com "de X para Y"
    pattern1 = rf'(?:{verbo_pattern})\s+(?:o\s+|a\s+)?(.+?)\s+do\s+(?:{id_pattern})\s+(.+?)\s+de\s+(.+?)\s+para\s+(.+?)(?:\s|$)'
    match1 = re.search(pattern1, comando_lower)
    
    if match1:
        campo_texto = match1.group(1).strip()
        identificador = match1.group(2).strip()
        valor_antigo = match1.group(3).strip()
        valor_novo = match1.group(4).strip()
        
        campo = normalizar_campo(campo_texto)
        
        return {
            'tipo': 'EDICAO',
            'identificador': identificador,
            'campo': campo,
            'valor_novo': valor_novo,
            'valor_antigo': valor_antigo
        }
    
    # Padrão simplificado sem "de X"
    pattern2 = rf'(?:{verbo_pattern})\s+(?:o\s+|a\s+)?(.+?)\s+do\s+(?:{id_pattern})\s+(.+?)\s+para\s+(.+?)(?:\s|$)'
    match2 = re.search(pattern2, comando_lower)
    
    if match2:
        campo_texto = match2.group(1).strip()
        identificador = match2.group(2).strip()
        valor_novo = match2.group(3).strip()
        
        campo = normalizar_campo(campo_texto)
        
        return {
            'tipo': 'EDICAO',
            'identificador': identificador,
            'campo': campo,
            'valor_novo': valor_novo,
            'valor_antigo': None
        }
    
    # Padrão 3: Sem especificar "do arquivo/certificado" - "muda [campo] de [antigo] para [novo]"
    # Útil quando há apenas 1 instrumento na sessão
    pattern3 = rf'(?:{verbo_pattern})\s+(?:o\s+|a\s+)?(.+?)\s+de\s+(.+?)\s+para\s+(.+?)(?:\s|$)'
    match3 = re.search(pattern3, comando_lower)
    
    if match3:
        campo_texto = match3.group(1).strip()
        valor_antigo = match3.group(2).strip()
        valor_novo = match3.group(3).strip()
        
        campo = normalizar_campo(campo_texto)
        
        return {
            'tipo': 'EDICAO',
            'identificador': None,  # Vai usar o primeiro/único instrumento
            'campo': campo,
            'valor_novo': valor_novo,
            'valor_antigo': valor_antigo
        }
    
    # Padrão 4: Super simplificado - "muda [campo] para [novo]"
    # Útil quando há apenas 1 instrumento e não quer especificar valor antigo
    pattern4 = rf'(?:{verbo_pattern})\s+(?:o\s+|a\s+)?(.+?)\s+para\s+(.+?)(?:\s|$)'
    match4 = re.search(pattern4, comando_lower)
    
    if match4:
        campo_texto = match4.group(1).strip()
        valor_novo = match4.group(2).strip()
        
        campo = normalizar_campo(campo_texto)
        
        return {
            'tipo': 'EDICAO',
            'identificador': None,  # Vai usar o primeiro/único instrumento
            'campo': campo,
            'valor_novo': valor_novo,
            'valor_antigo': None
        }
    
    # Não é um comando de edição
    return {'tipo': None}


def formatar_confirmacao_edicao(resultado_edicao):
    """
    Formata uma mensagem HTML de confirmação da edição
    
    Args:
        resultado_edicao: dict retornado por editar_campo_instrumento
    
    Returns:
        str com HTML formatado
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
    
    html = f"""<div style="background: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; border-radius: 8px; margin: 10px 0;">
    <h4 style="margin: 0 0 10px 0; color: #2e7d32;">✅ Alteração Realizada</h4>
    
    <div style="background: white; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
        <strong>📄 Instrumento:</strong> {inst.get('identificacao', 'n/i')} - {inst.get('nome', 'n/i')}<br>
        <strong>📁 Arquivo:</strong> {inst.get('arquivo_origem', 'n/i')}
    </div>
    
    <div style="background: white; padding: 12px; border-radius: 6px;">
        <strong>🔧 Campo alterado:</strong> {nome_campo_exibicao}<br>
        <div style="margin-top: 8px;">
            <span style="color: #d32f2f; text-decoration: line-through;">{valor_antigo}</span>
            <span style="margin: 0 8px;">→</span>
            <span style="color: #2e7d32; font-weight: bold;">{valor_novo}</span>
        </div>
    </div>
    
    <p style="margin: 12px 0 0 0; font-size: 0.9em; color: #555;">
        ℹ️ A alteração foi salva temporariamente. Use o comando <strong>"inserir no banco"</strong> ou clique no botão para confirmar.
    </p>
</div>"""
    
    return html


# Testes
if __name__ == "__main__":
    # Testa parser
    comandos_teste = [
        "muda o numero de serie do arquivo x34 de 456 para 123",
        "altera a tag do certificado ABC para XYZ",
        "corrige o fabricante do instrumento metron para Mitutoyo",
        "mude o modelo do pdf teste123 para ABC-500",
        "atualiza o status do item x para Calibrado"
    ]
    
    for cmd in comandos_teste:
        print(f"\nComando: {cmd}")
        resultado = extrair_comando_edicao(cmd)
        print(f"Resultado: {resultado}")
