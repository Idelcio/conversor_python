"""
System Prompts e Schemas para OpenAI
Configuração de segurança e instruções de extração
"""

# System Prompt - Define o comportamento da IA
SYSTEM_PROMPT = """Voce e um assistente inteligente especializado em analise de documentos.

Voce tem a capacidade de:
1. Ler e interpretar qualquer documento PDF (certificados, relatorios, formularios, etc)
2. Extrair TODAS as informacoes relevantes que encontrar
3. Organizar os dados de forma estruturada em JSON
4. Identificar padroes, tabelas, campos e valores

REGRAS:
1. Analise o documento completamente
2. Extraia TODOS os dados que encontrar, sem limitacoes
3. Organize em JSON de forma logica
4. Use "n/i" apenas se um campo esperado nao existir
5. Seja preciso - nao invente dados
6. Datas no formato YYYY-MM-DD quando possivel
7. Numeros como valores numericos

Retorne APENAS JSON valido, sem texto adicional.
"""

# Schema JSON esperado (ORDEM: Formulário Laravel)
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        # LINHA 1
        "identificacao": {"type": "string", "description": "Tag ou código do instrumento"},
        "nome": {"type": "string", "description": "Nome do equipamento"},
        
        # LINHA 2
        "tipo_familia": {"type": "string", "description": "Tipo ou família do instrumento"},
        "fabricante": {"type": "string", "description": "Fabricante"},
        
        # LINHA 3
        "modelo": {"type": "string", "description": "Modelo"},
        "numero_serie": {"type": "string", "description": "Número de série"},
        
        # LINHA 4
        "descricao": {"type": "string", "description": "Descrição completa"},
        
        # LINHA 5
        "periodicidade": {"type": "integer", "description": "Periodicidade em meses (default 12)"},
        "departamento": {"type": "string", "description": "Localização ou departamento"},
        
        # LINHA 6
        "responsavel": {"type": "string", "description": "Responsável ou cliente"},
        "motivo_calibracao": {"type": "string", "description": "Motivo da calibração"},
        
        # LINHA 7
        "criticidade": {"type": ["string", "null"], "description": "Criticidade (Alta, Média, Baixa)"},
        "serie_desenv": {"type": ["string", "null"], "description": "Série/Desenho"},
        
        # Ocultos/Extras
        "status": {"type": "string", "default": "Sem Calibração"},
        # quantidade removido
        
        # Datas
        "data_calibracao": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
        "data_emissao": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
        "data_recebimento": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
        
        # Extras
        "local_calibracao": {"type": ["string", "null"]},
        "software": {"type": ["string", "null"]},
        "condicao": {"type": ["string", "null"]},
        "laboratorio": {"type": ["string", "null"]},
        "arquivo_origem": {"type": "string"},
        
        # Grandezas (ÚLTIMO)
        "grandezas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "servicos": {"type": "array", "items": {"type": "string"}},
                    "tolerancia_processo": {"type": ["number", "string"]},
                    "tolerancia_simetrica": {"type": "boolean", "default": True},
                    "unidade": {"type": "string"},
                    "resolucao": {"type": "string"},
                    "criterio_aceitacao": {"type": ["string", "null"]},
                    "regra_decisao_id": {"type": "integer", "default": 1},
                    "faixa_nominal": {"type": "string"},
                    "classe_norma": {"type": ["string", "null"]},
                    "classificacao": {"type": ["string", "null"]},
                    "faixa_uso": {"type": ["string", "null"]}
                },
                "required": ["unidade", "tolerancia_processo"]
            }
        }
    },
    "required": ["identificacao", "nome", "fabricante", "modelo", "numero_serie", "grandezas"]
}

# Prompt de extração detalhado
EXTRACTION_PROMPT = """Analise este documento/imagem e extraia TODAS as informacoes que voce conseguir identificar.

INSTRUCOES:
1. Leia TODO o conteudo do documento
2. Identifique e extraia TODOS os campos, dados, valores, tabelas
3. Organize as informacoes em um JSON estruturado de forma logica
4. Use nomes de campos descritivos em portugues (sem acentos)
5. Datas no formato YYYY-MM-DD
6. Numeros como valores numericos
7. Textos como strings
8. Se houver tabelas, extraia como arrays de objetos
9. NAO invente dados - extraia apenas o que esta visivel
10. Use "n/i" (nao informado) se um campo comum estiver ausente

Estrutura sugerida (adapte conforme o documento):
{
  "tipo_documento": "tipo identificado",
  "titulo": "titulo do documento",
  "dados_principais": { ... campos principais ... },
  "dados_adicionais": { ... outros campos ... },
  "tabelas": [ ... dados tabulares ... ],
  "observacoes": "notas ou informacoes extras"
}

Retorne APENAS o JSON, sem texto adicional.
"""

# Mensagens de segurança
SECURITY_MESSAGES = {
    "off_topic": "[INFO] Desculpe, so posso ajudar com extracao de dados de certificados de calibracao. Por favor, faca upload de um PDF de certificado.",
    "no_pdf": "[INFO] Por favor, faca upload de um certificado de calibracao em PDF para que eu possa extrair as informacoes.",
    "invalid_request": "[AVISO] Requisicao invalida. Envie apenas certificados de calibracao em PDF.",
    "blocked": "[BLOQUEADO] Esta pergunta nao esta relacionada a extracao de certificados. Posso apenas processar certificados de calibracao."
}
