"""
Script de teste para debug da extração do PDF Gmetro
"""

import pdfplumber
import re

caminho_pdf = r"pdfs\GMB032_23.pdf"

print("=" * 60)
print("TESTE DE EXTRAÇÃO - CERTIFICADO GMETRO")
print("=" * 60)

# Extrai texto
with pdfplumber.open(caminho_pdf) as pdf:
    texto = ""
    for pagina in pdf.pages:
        texto += pagina.extract_text() + "\n"

print("\n[1] TEXTO COMPLETO (primeiras 2000 caracteres):")
print("-" * 60)
print(texto[:2000])
print("-" * 60)

# Testa padrões de número do certificado
print("\n[2] TESTANDO PADRÕES DE NÚMERO DO CERTIFICADO:")
print("-" * 60)

padroes_cert = [
    r'N[°º]\s+do\s+Certificado\s+([A-Z0-9/]+)',
    r'Certificado\s+([A-Z0-9/]+)',
    r'GMB\d+/\d+',
    r'([A-Z]{3}\d+/\d+)'
]

for padrao in padroes_cert:
    match = re.search(padrao, texto, re.IGNORECASE)
    if match:
        print(f"✓ Padrão '{padrao}' encontrou: {match.group(0)}")
        if match.groups():
            print(f"  Grupo capturado: {match.group(1)}")
    else:
        print(f"✗ Padrão '{padrao}' não encontrou nada")

# Testa padrões de datas
print("\n[3] TESTANDO PADRÕES DE DATAS:")
print("-" * 60)

padroes_datas = [
    (r'Data\s+Recebimento\s+(\d{2}/\d{2}/\d{4})', 'Data Recebimento'),
    (r'Data\s+da\s+Calibra[çc][ãa]o\s+(\d{2}/\d{2}/\d{4})', 'Data Calibração'),
    (r'Data\s+da\s+Emiss[ãa]o\s+(\d{2}/\d{2}/\d{4})', 'Data Emissão')
]

for padrao, nome in padroes_datas:
    match = re.search(padrao, texto, re.IGNORECASE)
    if match:
        print(f"✓ {nome}: {match.group(1)}")
    else:
        print(f"✗ {nome}: não encontrado")

# Procura por todas as datas no formato DD/MM/YYYY
print("\n[4] TODAS AS DATAS ENCONTRADAS (DD/MM/YYYY):")
print("-" * 60)
todas_datas = re.findall(r'\d{2}/\d{2}/\d{4}', texto)
for data in todas_datas:
    print(f"  - {data}")

print("\n" + "=" * 60)
