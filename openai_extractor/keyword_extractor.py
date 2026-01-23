# Keyword based extractor for calibration certificates
"""
Extrai campos de certificados PDF usando busca por palavras‑chave.
Não depende de modelo de visão; usa apenas texto extraído via PyMuPDF.
"""

import re
import fitz  # PyMuPDF

# Mapeamento completo de palavras‑chave -> nome do campo JSON
KEYWORDS = {
    # Campos obrigatórios
    "identificacao": [
        "identificacao", "identificação", "tag", "código", "codigo",
        "n°", "nº", "numero certificado", "número certificado",
        "certificado n", "certificado nº"
    ],
    "nome": [
        "nome", "instrumento", "equipamento", "descrição do instrumento",
        "descricao do instrumento", "tipo de instrumento"
    ],
    "fabricante": [
        "fabricante", "marca", "manufacturer"
    ],
    "modelo": [
        "modelo", "model"
    ],
    "numero_serie": [
        "numero de serie", "número de série", "n/s", "ns", "s/n", "sn",
        "serial number", "serie"
    ],
    "descricao": [
        "descricao", "descrição", "caracteristicas", "características",
        "especificacoes", "especificações"
    ],
    "periodicidade": [
        "periodicidade", "periodo", "período", "intervalo de calibracao",
        "intervalo de calibração", "validade", "prazo"
    ],
    "departamento": [
        "departamento", "setor", "local", "localizacao", "localização",
        "endereco", "endereço", "sala", "predio", "prédio"
    ],
    "responsavel": [
        "responsavel", "responsável", "cliente", "solicitante",
        "empresa", "proprietario", "proprietário"
    ],
    
    # Campos opcionais
    "tipo_familia": [
        "tipo", "familia", "família", "categoria", "classe de instrumento",
        "tipo de equipamento"
    ],
    "serie_desenv": [
        "serie desenvolvimento", "série desenvolvimento", "serie desenv",
        "lote", "batch"
    ],
    "criticidade": [
        "criticidade", "nivel critico", "nível crítico", "importancia",
        "importância", "prioridade"
    ],
    "motivo_calibracao": [
        "motivo", "motivo da calibracao", "motivo da calibração",
        "razao", "razão", "finalidade"
    ],
    "status": [
        "status", "situacao", "situação", "condicao", "condição",
        "estado"
    ],
    
    # Datas
    "data_calibracao": [
        "data de calibracao", "data de calibração", "data calibracao",
        "data da calibracao", "calibrado em", "executado em"
    ],
    "data_emissao": [
        "data de emissao", "data de emissão", "emitido em",
        "data emissao", "data do certificado"
    ],
    "data_recebimento": [
        "data de recebimento", "recebido em", "entrada em",
        "data entrada"
    ],
    
    # Informações adicionais
    "local_calibracao": [
        "local de calibracao", "local de calibração", "calibrado em",
        "laboratorio", "laboratório"
    ],
    "software": [
        "software", "programa", "sistema"
    ],
    "condicao": [
        "condicao", "condição", "estado do equipamento",
        "observacoes", "observações"
    ],
    "laboratorio": [
        "laboratorio", "laboratório", "lab", "empresa calibradora"
    ],
    
    # Grandezas (campos dentro de grandezas[])
    "unidade": [
        "unidade", "unid", "unit", "medida"
    ],
    "tolerancia_processo": [
        "tolerancia", "tolerância", "tolerancia do processo",
        "erro maximo", "erro máximo", "incerteza"
    ],
    "tolerancia_simetrica": [
        "simetrica", "simétrica", "bilateral"
    ],
    "resolucao": [
        "resolucao", "resolução", "menor divisao", "menor divisão",
        "precisao", "precisão"
    ],
    "criterio_aceitacao": [
        "criterio", "critério", "criterio de aceitacao",
        "critério de aceitação", "limite de aceitacao"
    ],
    "faixa_nominal": [
        "faixa nominal", "faixa", "range", "alcance",
        "capacidade", "escala"
    ],
    "classe_norma": [
        "classe", "norma", "classe de exatidao", "classe de exatidão"
    ],
    "classificacao": [
        "classificacao", "classificação", "tipo de medicao",
        "tipo de medição"
    ],
    "faixa_uso": [
        "faixa de uso", "faixa utilizada", "faixa de trabalho"
    ],
    "servicos": [
        "servico", "serviço", "servicos", "serviços",
        "tipo de servico", "calibracao realizada"
    ],
    "regra_decisao_id": [
        "regra de decisao", "regra de decisão", "criterio de decisao"
    ]
}

def clean_text(text: str) -> str:
    """Normaliza texto para busca case‑insensitive"""
    return text.lower().replace("\n", " ").replace("\r", " ")

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrai todo o texto de um PDF usando PyMuPDF"""
    doc = fitz.open(pdf_path)
    full_text = []
    for page in doc:
        full_text.append(page.get_text())
    doc.close()
    return " ".join(full_text)

def extract_date(text: str, patterns: list) -> str:
    """
    Procura por datas no formato DD/MM/YYYY ou DD-MM-YYYY
    e retorna no formato YYYY-MM-DD
    """
    for pat in patterns:
        # Busca o padrão seguido de uma data
        regex = re.compile(
            rf"{re.escape(pat)}\s*[:\-]?\s*(\d{{1,2}}[\/\-]\d{{1,2}}[\/\-]\d{{2,4}})",
            re.IGNORECASE
        )
        m = regex.search(text)
        if m:
            date_str = m.group(1)
            # Converte DD/MM/YYYY para YYYY-MM-DD
            parts = re.split(r'[\/\-]', date_str)
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 2:
                    year = '20' + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return None

def extract_number(text: str, patterns: list) -> int:
    """Procura por números após os padrões"""
    for pat in patterns:
        regex = re.compile(rf"{re.escape(pat)}\s*[:\-]?\s*(\d+)", re.IGNORECASE)
        m = regex.search(text)
        if m:
            return int(m.group(1))
    return None

def find_value(text: str, patterns: list) -> str:
    """
    Procura o primeiro padrão que aparecer no texto e retorna o valor após ele.
    Exemplo: "Modelo: Sigma 2018" -> "Sigma 2018"
    """
    for pat in patterns:
        # regex que captura tudo após o padrão até a próxima quebra ou ponto final
        regex = re.compile(
            rf"{re.escape(pat)}\s*[:\-]?\s*(.+?)(?:\n|\r|\.|;|$)",
            re.IGNORECASE
        )
        m = regex.search(text)
        if m:
            value = m.group(1).strip()
            # Remove caracteres extras
            value = value.replace('\n', ' ').replace('\r', ' ')
            # Limita tamanho
            if len(value) > 500:
                value = value[:500]
            return value
    return None

def extract_by_keywords(pdf_path: str) -> dict:
    """
    Extrai os campos definidos em KEYWORDS a partir do texto do PDF.
    Retorna um dicionário JSON com os valores encontrados ou "n/i" quando não encontrado.
    ORDEM: Segue exatamente a ordem do formulário Laravel (esquerda → direita, cima → baixo)
    """
    raw_text = extract_text_from_pdf(pdf_path)
    text = clean_text(raw_text)
    
    # Dicionário ordenado conforme formulário
    result = {}
    
    # LINHA 1: Identificação | Nome
    result['identificacao'] = find_value(text, KEYWORDS['identificacao']) or "n/i"
    result['nome'] = find_value(text, KEYWORDS['nome']) or "n/i"
    
    # LINHA 2: Tipo/Família | Fabricante
    result['tipo_familia'] = find_value(text, KEYWORDS['tipo_familia']) or "n/i"
    result['fabricante'] = find_value(text, KEYWORDS['fabricante']) or "n/i"
    
    # LINHA 3: Modelo | Nº de Série
    result['modelo'] = find_value(text, KEYWORDS['modelo']) or "n/i"
    result['numero_serie'] = find_value(text, KEYWORDS['numero_serie']) or "n/i"
    
    # LINHA 4: Descrição (campo grande)
    result['descricao'] = find_value(text, KEYWORDS['descricao']) or "n/i"
    
    # LINHA 5: Periodicidade | Localização
    periodicidade = extract_number(text, KEYWORDS['periodicidade'])
    result['periodicidade'] = periodicidade if periodicidade else 12
    result['departamento'] = find_value(text, KEYWORDS['departamento']) or "n/i"
    
    # LINHA 6: Responsável | Motivo de Calibração
    result['responsavel'] = find_value(text, KEYWORDS['responsavel']) or "n/i"
    result['motivo_calibracao'] = find_value(text, KEYWORDS['motivo_calibracao']) or "n/i"
    
    # LINHA 7: Criticidade | Série/Desenv
    result['criticidade'] = find_value(text, KEYWORDS['criticidade']) or "n/i"
    result['serie_desenv'] = find_value(text, KEYWORDS['serie_desenv']) or "n/i"
    
    # Campos adicionais (não visíveis no form mas necessários)
    result['status'] = find_value(text, KEYWORDS['status']) or "Sem Calibração"
    
    # Datas
    result['data_calibracao'] = extract_date(text, KEYWORDS['data_calibracao'])
    result['data_emissao'] = extract_date(text, KEYWORDS['data_emissao'])
    result['data_recebimento'] = extract_date(text, KEYWORDS['data_recebimento'])
    
    # Informações extras
    result['local_calibracao'] = find_value(text, KEYWORDS['local_calibracao'])
    result['software'] = find_value(text, KEYWORDS['software'])
    result['condicao'] = find_value(text, KEYWORDS['condicao'])
    result['laboratorio'] = find_value(text, KEYWORDS['laboratorio'])
    result['arquivo_origem'] = pdf_path.split('\\')[-1].split('/')[-1]
    
    # GRANDEZAS - SEMPRE POR ÚLTIMO
    grandezas = []
    grandeza = {
        # Ordem dentro de grandezas (conforme form):
        'servicos': [],
        'tolerancia_processo': find_value(text, KEYWORDS['tolerancia_processo']) or "n/i",
        'unidade': find_value(text, KEYWORDS['unidade']) or "n/i",
        'resolucao': find_value(text, KEYWORDS['resolucao']) or "n/i",
        'criterio_aceitacao': find_value(text, KEYWORDS['criterio_aceitacao']),
        'regra_decisao_id': 1,
        'faixa_nominal': find_value(text, KEYWORDS['faixa_nominal']),
        'classe_norma': find_value(text, KEYWORDS['classe_norma']),
        'classificacao': find_value(text, KEYWORDS['classificacao']),
        'faixa_uso': find_value(text, KEYWORDS['faixa_uso']),
        'tolerancia_simetrica': True
    }
    
    # Serviços
    servico = find_value(text, KEYWORDS['servicos'])
    if servico:
        grandeza['servicos'] = [servico]
    
    grandezas.append(grandeza)
    result['grandezas'] = grandezas
    
    return result
