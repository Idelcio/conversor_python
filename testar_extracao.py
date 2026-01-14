"""
Script para testar a extração de um PDF específico
"""

from extrator_pdf import ExtratorCertificado
import json
from pathlib import Path

# Testa extração do PDF (pega o primeiro PDF da pasta)
extrator = ExtratorCertificado()
pdfs = list(Path('pdfs').glob('*.pdf'))
if not pdfs:
    print("[ERRO] Nenhum PDF encontrado na pasta pdfs/")
    exit(1)

pdf_path = str(pdfs[0])

print("="*60)
print("TESTANDO EXTRACAO DO PDF")
print("="*60)
print(f"\nArquivo: {pdf_path}")

# Extrai texto
texto = extrator.extrair_texto_pdf(pdf_path)
print(f"\n[INFO] Texto extraido ({len(texto)} caracteres)")
print("\n" + "="*60)
print("PRIMEIROS 2000 CARACTERES DO TEXTO:")
print("="*60)
print(texto[:2000])

# Extrai instrumento
instrumento = extrator.extrair_instrumento(texto, pdf_path)
print("\n" + "="*60)
print("DADOS EXTRAIDOS:")
print("="*60)
print(json.dumps(instrumento, indent=2, ensure_ascii=False))
