"""
Debug específico para visualizar-pdf (9).pdf
"""

from extrator_pdf import ExtratorCertificado

extrator = ExtratorCertificado()
texto = extrator.extrair_texto_pdf("pdfs/visualizar-pdf (9).pdf")

print("="*60)
print("ANALISANDO visualizar-pdf (9).pdf")
print("="*60)

# Mostra mais do texto para ver se tem data
print("\nPRIMEIROS 2000 CARACTERES:")
print(texto[:2000])

# Busca padrões alternativos de data
import re

print("\n" + "="*60)
print("BUSCANDO PADROES DE DATA:")
print("="*60)

padroes_data = [
    (r'\d{2}/\d{2}/\d{4}', 'DD/MM/YYYY'),
    (r'\d{4}-\d{2}-\d{2}', 'YYYY-MM-DD'),
    (r'[Dd]ata[:\s]+([^\n]+)', 'Data: ...'),
    (r'[Cc]alibra[çc][ãa]o[:\s]+([^\n]+)', 'Calibracao: ...'),
    (r'[Ee]miss[ãa]o[:\s]+([^\n]+)', 'Emissao: ...'),
]

for padrao, descricao in padroes_data:
    matches = re.findall(padrao, texto, re.IGNORECASE)
    if matches:
        print(f"\n[{descricao}] Encontrado(s) {len(matches)} match(es):")
        for m in matches[:3]:
            print(f"  - {m}")
