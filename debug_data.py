"""
Debug para testar extração de datas dos PDFs
"""

from extrator_pdf import ExtratorCertificado
from pathlib import Path
import re

extrator = ExtratorCertificado()

# Pega todos os PDFs
pdfs = list(Path('pdfs').glob('*.pdf'))

print("="*60)
print("TESTANDO EXTRAÇÃO DE DATAS")
print("="*60)

for pdf_path in pdfs:
    print(f"\n[PDF] Arquivo: {pdf_path.name}")
    print("-"*60)

    texto = extrator.extrair_texto_pdf(str(pdf_path))

    if not texto:
        print("  [ERRO] Texto vazio!")
        continue

    # Busca por datas no formato DD/MM/YYYY
    datas_encontradas = re.findall(r'\d{2}/\d{2}/\d{4}', texto)

    if datas_encontradas:
        print(f"  [OK] Datas encontradas no texto: {len(datas_encontradas)}")
        for i, data in enumerate(datas_encontradas[:5], 1):
            # Pega contexto ao redor da data
            pos = texto.find(data)
            contexto_antes = texto[max(0, pos-30):pos].strip()
            contexto_depois = texto[pos+10:pos+40].strip()
            print(f"     {i}. ...{contexto_antes} {data} {contexto_depois}...")
    else:
        print("  [ERRO] Nenhuma data encontrada no texto")
        print(f"  Primeiros 500 caracteres:")
        print(f"  {texto[:500]}")

    # Testa extração com o extrator
    instrumento = extrator.extrair_instrumento(texto, str(pdf_path))
    print(f"\n  [INFO] Resultado da extracao:")
    print(f"     Data Calibracao: {instrumento.get('data_calibracao', 'n/i')}")
    print(f"     Data Emissao: {instrumento.get('data_emissao', 'n/i')}")
    print()
