"""
Testa se o padrão captura "Código do indicador: CVZ 001"
"""

import re

texto_teste = """
Código do indicador: CVZ 001
Fabricante: Teste
"""

# Padrões que o extrator usa
padroes = [
    r'Autenticação:\s*([^\n]+)',
    r'Código:\s*([^\n]+)',
    r'Tag:\s*([^\n]+)',
    r'ID:\s*([^\n]+)'
]

print("TESTANDO PADRÕES DE CÓDIGO:")
print("="*60)
print(f"Texto de teste:\n{texto_teste}")
print("="*60)

for i, padrao in enumerate(padroes, 1):
    match = re.search(padrao, texto_teste, re.IGNORECASE | re.MULTILINE)
    if match:
        print(f"\nPadrão {i}: MATCH!")
        print(f"Regex: {padrao}")
        print(f"Capturado: '{match.group(1)}'")
        break
    else:
        print(f"\nPadrão {i}: Sem match")
        print(f"Regex: {padrao}")

# Teste com "Código do indicador:"
print("\n" + "="*60)
print("TESTANDO PADRÃO ESPECÍFICO:")
print("="*60)

padrao_codigo_indicador = r'Código\s+do\s+indicador:\s*([^\n]+)'
match = re.search(padrao_codigo_indicador, texto_teste, re.IGNORECASE)
if match:
    print(f"MATCH com 'Código do indicador:'")
    print(f"Capturado: '{match.group(1)}'")
else:
    print("SEM MATCH")
