"""
Debug para testar extração de cliente
"""

import re
from extrator_pdf import ExtratorCertificado

extrator = ExtratorCertificado()
texto = extrator.extrair_texto_pdf("pdfs/visualizar-pdf (9).pdf")

# Testa os padrões de cliente
padroes_cliente = [
    r'Cliente\s+:\s+([^\n]+)',  # "Cliente :" com espaços (mais específico)
    r'Contratante:\s*([^\n]+)',
    r'Solicitante:\s*([^\n]+)',
    r'Cliente\s*:\s*([^\n\r]+?)(?:\s*(?:Endere[çc]o|Endere.o))',
    r'Cliente\s*:\s*(.+?)(?:\n)',
]

print("TESTANDO PADRÕES DE CLIENTE:")
print("="*60)

for i, padrao in enumerate(padroes_cliente, 1):
    match = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
    if match:
        print(f"\nPadrão {i}: MATCH!")
        print(f"Regex: {padrao}")
        print(f"Capturado: '{match.group(1)}'")
        break
    else:
        print(f"\nPadrão {i}: Sem match")
        print(f"Regex: {padrao}")

# Mostra trecho relevante do texto
print("\n" + "="*60)
print("TRECHO DO TEXTO COM 'Cliente':")
print("="*60)
match_contexto = re.search(r'.{0,100}Cliente.{0,200}', texto, re.DOTALL)
if match_contexto:
    print(match_contexto.group(0))
