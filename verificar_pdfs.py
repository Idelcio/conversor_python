"""
Script para verificar PDFs duplicados
Verifica se existem 2 PDFs para cada instrumento
"""

from pathlib import Path
from extrator_pdf import ExtratorCertificado
from collections import defaultdict


def verificar_pdfs_duplicados():
    """Verifica se há PDFs duplicados para cada instrumento"""
    
    print("\n" + "="*70)
    print("VERIFICAÇÃO DE PDFS DUPLICADOS")
    print("="*70)
    
    # Busca PDFs na pasta
    pasta_pdfs = Path('pdfs')
    if not pasta_pdfs.exists():
        print("[ERRO] Pasta 'pdfs' não encontrada")
        return
    
    pdfs = list(pasta_pdfs.glob('*.pdf'))
    
    if not pdfs:
        print("[AVISO] Nenhum PDF encontrado na pasta 'pdfs'")
        return
    
    print(f"\n[INFO] Encontrados {len(pdfs)} PDFs na pasta 'pdfs'")
    print("\nProcessando PDFs para identificar instrumentos...\n")
    
    # Extrai informações básicas de cada PDF
    extrator = ExtratorCertificado()
    instrumentos_por_id = defaultdict(list)
    
    for pdf_path in pdfs:
        try:
            # Extrai só o texto para pegar a identificação
            texto = extrator.extrair_texto_pdf(str(pdf_path))
            if not texto:
                continue
            
            # Extrai o instrumento
            instrumento = extrator.extrair_instrumento(texto, str(pdf_path))
            
            # Agrupa por identificação
            identificacao = instrumento['identificacao']
            instrumentos_por_id[identificacao].append({
                'arquivo': pdf_path.name,
                'numero_serie': instrumento['numero_serie'],
                'nome': instrumento['nome']
            })
            
        except Exception as e:
            print(f"[ERRO] Falha ao processar {pdf_path.name}: {e}")
    
    # Análise dos resultados
    print("\n" + "="*70)
    print("RESULTADOS DA VERIFICAÇÃO")
    print("="*70)
    
    total_instrumentos = len(instrumentos_por_id)
    com_duplicata = 0
    sem_duplicata = 0
    mais_de_duas = 0
    
    # Instrumentos COM 2 PDFs (OK)
    print("\n✅ INSTRUMENTOS COM 2 PDFs (OK):")
    print("-"*70)
    for identificacao, pdfs_list in sorted(instrumentos_por_id.items()):
        if len(pdfs_list) == 2:
            com_duplicata += 1
            print(f"\n{identificacao} - {pdfs_list[0]['nome']}")
            for i, pdf_info in enumerate(pdfs_list, 1):
                print(f"  {i}. {pdf_info['arquivo']}")
    
    if com_duplicata == 0:
        print("  (Nenhum)")
    
    # Instrumentos com APENAS 1 PDF (ATENÇÃO)
    print("\n\n⚠️  INSTRUMENTOS COM APENAS 1 PDF (ATENÇÃO):")
    print("-"*70)
    for identificacao, pdfs_list in sorted(instrumentos_por_id.items()):
        if len(pdfs_list) == 1:
            sem_duplicata += 1
            print(f"\n{identificacao} - {pdfs_list[0]['nome']}")
            print(f"  1. {pdfs_list[0]['arquivo']}")
            print(f"  ⚠️  Falta 1 PDF para este instrumento!")
    
    if sem_duplicata == 0:
        print("  (Nenhum)")
    
    # Instrumentos com MAIS DE 2 PDFs (VERIFICAR)
    print("\n\n🔍 INSTRUMENTOS COM MAIS DE 2 PDFs (VERIFICAR):")
    print("-"*70)
    for identificacao, pdfs_list in sorted(instrumentos_por_id.items()):
        if len(pdfs_list) > 2:
            mais_de_duas += 1
            print(f"\n{identificacao} - {pdfs_list[0]['nome']}")
            for i, pdf_info in enumerate(pdfs_list, 1):
                print(f"  {i}. {pdf_info['arquivo']}")
            print(f"  🔍 Este instrumento tem {len(pdfs_list)} PDFs (esperado: 2)")
    
    if mais_de_duas == 0:
        print("  (Nenhum)")
    
    # Resumo final
    print("\n\n" + "="*70)
    print("RESUMO")
    print("="*70)
    print(f"\nTotal de PDFs processados: {len(pdfs)}")
    print(f"Total de instrumentos únicos: {total_instrumentos}")
    print(f"\n✅ Instrumentos com 2 PDFs: {com_duplicata}")
    print(f"⚠️  Instrumentos com 1 PDF: {sem_duplicata}")
    print(f"🔍 Instrumentos com mais de 2 PDFs: {mais_de_duas}")
    
    # Cálculo de cobertura
    if total_instrumentos > 0:
        percentual_ok = (com_duplicata / total_instrumentos) * 100
        print(f"\n📊 Cobertura: {percentual_ok:.1f}% dos instrumentos têm 2 PDFs")
    
    # Recomendações
    print("\n" + "="*70)
    print("RECOMENDAÇÕES")
    print("="*70)
    
    if sem_duplicata > 0:
        print(f"\n⚠️  Há {sem_duplicata} instrumento(s) com apenas 1 PDF.")
        print("   Recomendação: Adicione o PDF faltante para cada instrumento.")
    
    if mais_de_duas > 0:
        print(f"\n🔍 Há {mais_de_duas} instrumento(s) com mais de 2 PDFs.")
        print("   Recomendação: Verifique se há PDFs duplicados ou incorretos.")
    
    if com_duplicata == total_instrumentos:
        print("\n✅ Perfeito! Todos os instrumentos têm exatamente 2 PDFs.")
        print("   Você pode prosseguir com o processamento.")
    
    print("\n")


if __name__ == "__main__":
    verificar_pdfs_duplicados()
