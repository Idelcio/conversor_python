"""
Script para processar PDFs diretamente sem interface web
Uso: python processar_pdfs.py
"""

from extrator_pdf import ExtratorCertificado
from gerador_sql import GeradorSQL
from pathlib import Path
import json

def main():
    print("="*60)
    print("EXTRATOR DE CERTIFICADOS - MODO OFFLINE")
    print("="*60)

    # Busca todos os PDFs na pasta atual
    # Busca todos os PDFs na pasta atual e na pasta pdfs
    pdfs_root = list(Path('.').glob('*.pdf'))
    pdfs_dir = list(Path('pdfs').glob('*.pdf')) if Path('pdfs').exists() else []
    
    pdfs = pdfs_root + pdfs_dir

    if not pdfs:
        print("\n[ERRO] Nenhum PDF encontrado na pasta atual")
        return

    print(f"\n[INFO] Encontrados {len(pdfs)} PDFs para processar:")
    for pdf in pdfs:
        print(f"  - {pdf.name}")

    # Processa os PDFs
    print("\n" + "="*60)
    print("PROCESSANDO PDFS...")
    print("="*60)

    extrator = ExtratorCertificado()
    instrumentos = extrator.processar_multiplos_pdfs([str(pdf) for pdf in pdfs])

    if not instrumentos:
        print("\n[ERRO] Nenhum instrumento foi extraido dos PDFs")
        return

    # Estatísticas
    total_grandezas = sum(len(inst.get('grandezas', [])) for inst in instrumentos)

    print("\n" + "="*60)
    print("ESTATISTICAS:")
    print("="*60)
    print(f"  Total de PDFs processados: {len(pdfs)}")
    print(f"  Total de instrumentos: {len(instrumentos)}")
    print(f"  Total de grandezas: {total_grandezas}")

    # Mostra resumo dos instrumentos
    print("\n" + "="*60)
    print("INSTRUMENTOS EXTRAIDOS:")
    print("="*60)

    for i, inst in enumerate(instrumentos, 1):
        print(f"\n{i}. {inst['identificacao']} - {inst['nome']}")
        print(f"   Fabricante: {inst['fabricante']}")
        print(f"   Modelo: {inst['modelo']}")
        print(f"   Nº Série: {inst['numero_serie']}")
        print(f"   Grandezas: {len(inst.get('grandezas', []))}")

    # Gera JSON
    print("\n" + "="*60)
    print("GERANDO ARQUIVOS DE SAIDA...")
    print("="*60)

    arquivo_json = extrator.gerar_json(instrumentos, "instrumentos_extraidos.json")

    # Gera SQL
    gerador = GeradorSQL(user_id=1)  # Ajuste o user_id conforme necessário
    arquivo_sql = gerador.salvar_sql(instrumentos, "instrumentos_extraidos.sql")

    print("\n" + "="*60)
    print("CONCLUIDO!")
    print("="*60)
    print(f"\nArquivos gerados:")
    print(f"  - JSON: {arquivo_json}")
    print(f"  - SQL: {arquivo_sql}")
    print("\nVoce pode:")
    print("  1. Revisar o JSON para verificar os dados extraidos")
    print("  2. Importar o SQL direto no banco de dados")
    print("  3. Editar manualmente campos que ficaram como 'n/i'")
    print("\n")

if __name__ == "__main__":
    main()
