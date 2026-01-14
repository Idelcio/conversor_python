"""
Script para gerar SQL com user_id customizado
Permite escolher o user_id para importação no Gocal
"""

import mysql.connector
import json
from datetime import datetime
from gerador_sql import GeradorSQL
from pathlib import Path

# Configurações do banco
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'instrumentos',
    'user': 'root',
    'password': ''
}


def conectar_banco():
    """Conecta ao banco MySQL"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"[ERRO] Falha ao conectar: {e}")
        return None


def buscar_instrumentos_do_banco():
    """Busca todos os instrumentos do banco local"""
    
    conn = conectar_banco()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    
    # Busca instrumentos
    cursor.execute("""
        SELECT id, identificacao, nome, fabricante, modelo, numero_serie,
               descricao, periodicidade, departamento, responsavel, status,
               tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade
        FROM instrumentos
        ORDER BY created_at DESC
    """)
    
    instrumentos = cursor.fetchall()
    
    # Para cada instrumento, busca suas grandezas
    for inst in instrumentos:
        cursor.execute("""
            SELECT servicos, tolerancia_processo, tolerancia_simetrica,
                   unidade, resolucao, criterio_aceitacao, regra_decisao_id,
                   faixa_nominal, classe_norma, classificacao, faixa_uso
            FROM grandezas
            WHERE instrumento_id = %s
        """, (inst['id'],))
        
        grandezas = cursor.fetchall()
        
        # Converte servicos de JSON para array
        for g in grandezas:
            if g['servicos']:
                try:
                    g['servicos'] = json.loads(g['servicos'])
                except:
                    g['servicos'] = []
        
        inst['grandezas'] = grandezas
    
    cursor.close()
    conn.close()
    
    return instrumentos


def gerar_sql_customizado():
    """Gera SQL com user_id customizado"""
    
    print("\n" + "="*70)
    print("GERADOR DE SQL CUSTOMIZADO PARA GOCAL")
    print("="*70)
    
    # Busca instrumentos do banco
    print("\n[INFO] Buscando instrumentos do banco local...")
    instrumentos = buscar_instrumentos_do_banco()
    
    if not instrumentos:
        print("[ERRO] Nenhum instrumento encontrado no banco")
        print("       Execute 'python inserir_banco.py' primeiro")
        return
    
    print(f"[OK] {len(instrumentos)} instrumentos encontrados")
    
    # Mostra preview dos instrumentos
    print("\n" + "-"*70)
    print("INSTRUMENTOS ENCONTRADOS:")
    print("-"*70)
    for i, inst in enumerate(instrumentos[:5], 1):
        print(f"{i}. {inst['identificacao']} - {inst['nome']}")
    
    if len(instrumentos) > 5:
        print(f"... e mais {len(instrumentos) - 5} instrumentos")
    
    # Solicita user_id
    print("\n" + "="*70)
    print("CONFIGURAÇÃO DO USER_ID")
    print("="*70)
    print("\nEste será o ID do usuário/empresa no Gocal.")
    print("Exemplo: Se você criou o usuário 'Idelcio' com ID 53 no Gocal,")
    print("         digite 53 para que todos os instrumentos sejam dele.")
    
    while True:
        try:
            user_id_input = input("\nDigite o USER_ID desejado (padrão: 1): ").strip()
            
            if not user_id_input:
                user_id = 1
                break
            
            user_id = int(user_id_input)
            
            if user_id <= 0:
                print("[ERRO] User ID deve ser maior que 0")
                continue
            
            break
        except ValueError:
            print("[ERRO] Digite um número válido")
    
    # Solicita nome do arquivo
    print("\n" + "="*70)
    print("NOME DO ARQUIVO SQL")
    print("="*70)
    
    arquivo_padrao = f"gocal_user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    arquivo_input = input(f"\nNome do arquivo (padrão: {arquivo_padrao}): ").strip()
    
    arquivo_saida = arquivo_input if arquivo_input else arquivo_padrao
    
    if not arquivo_saida.endswith('.sql'):
        arquivo_saida += '.sql'
    
    # Gera SQL
    print("\n" + "="*70)
    print("GERANDO SQL...")
    print("="*70)
    
    gerador = GeradorSQL(user_id=user_id)
    
    try:
        gerador.salvar_sql(instrumentos, arquivo_saida)
        
        # Estatísticas
        total_grandezas = sum(len(inst.get('grandezas', [])) for inst in instrumentos)
        
        print("\n" + "="*70)
        print("SQL GERADO COM SUCESSO!")
        print("="*70)
        print(f"\nArquivo: {arquivo_saida}")
        print(f"\nResumo:")
        print(f"  - User ID: {user_id}")
        print(f"  - Instrumentos: {len(instrumentos)}")
        print(f"  - Grandezas: {total_grandezas}")
        print(f"\nPróximos passos:")
        print(f"  1. Copie o arquivo '{arquivo_saida}' para o servidor Gocal")
        print(f"  2. Importe no MySQL do Gocal:")
        print(f"     mysql -u root -p gocal < {arquivo_saida}")
        print(f"  3. Todos os instrumentos serão do usuário ID {user_id}")
        
    except Exception as e:
        print(f"\n[ERRO] Falha ao gerar SQL: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    gerar_sql_customizado()
