"""
Script para processar PDFs e inserir direto no banco MySQL
"""

import mysql.connector
from pathlib import Path
import json
from datetime import datetime
from extrator_pdf import ExtratorCertificado

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
        print("[OK] Conectado ao banco MySQL")
        return conn
    except Exception as e:
        print(f"[ERRO] Falha ao conectar: {e}")
        return None


def verificar_instrumento_existente(cursor, instrumento):
    """Verifica se instrumento já existe no banco"""
    
    # Busca por número de série (prioridade) ou identificação
    numero_serie = instrumento.get('numero_serie')
    identificacao = instrumento.get('identificacao')
    
    if numero_serie and numero_serie != 'n/i':
        cursor.execute(
            "SELECT id FROM instrumentos WHERE numero_serie = %s",
            (numero_serie,)
        )
    elif identificacao and identificacao != 'n/i':
        cursor.execute(
            "SELECT id FROM instrumentos WHERE identificacao = %s",
            (identificacao,)
        )
    else:
        return None
    
    resultado = cursor.fetchone()
    return resultado[0] if resultado else None


def atualizar_instrumento(cursor, instrumento_id, instrumento):
    """Atualiza um instrumento existente"""
    
    sql = """
    UPDATE instrumentos SET
        identificacao = %s,
        nome = %s,
        fabricante = %s,
        modelo = %s,
        numero_serie = %s,
        descricao = %s,
        periodicidade = %s,
        departamento = %s,
        responsavel = %s,
        status = %s,
        tipo_familia = %s,
        serie_desenv = %s,
        criticidade = %s,
        motivo_calibracao = %s,
        quantidade = %s,
        updated_at = %s
    WHERE id = %s
    """
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Converte 'n/i' para None
    def converter_ni(valor):
        return None if valor == 'n/i' else valor
    
    valores = (
        converter_ni(instrumento.get('identificacao')),
        converter_ni(instrumento.get('nome')),
        converter_ni(instrumento.get('fabricante')),
        converter_ni(instrumento.get('modelo')),
        converter_ni(instrumento.get('numero_serie')),
        converter_ni(instrumento.get('descricao')),
        instrumento.get('periodicidade', 12),
        converter_ni(instrumento.get('departamento')),
        converter_ni(instrumento.get('responsavel')),
        instrumento.get('status', 'Sem Calibração'),
        converter_ni(instrumento.get('tipo_familia')),
        converter_ni(instrumento.get('serie_desenv')),
        converter_ni(instrumento.get('criticidade')),
        converter_ni(instrumento.get('motivo_calibracao')),
        instrumento.get('quantidade', 1),
        now,
        instrumento_id
    )
    
    cursor.execute(sql, valores)
    return instrumento_id


def inserir_instrumento(cursor, instrumento, user_id=1):
    """Insere um instrumento no banco"""

    sql = """
    INSERT INTO instrumentos
    (identificacao, nome, fabricante, modelo, numero_serie, descricao,
     periodicidade, departamento, responsavel, status, tipo_familia,
     serie_desenv, criticidade, motivo_calibracao, quantidade,
     user_id, responsavel_cadastro_id, created_at, updated_at)
    VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Converte 'n/i' para None
    def converter_ni(valor):
        return None if valor == 'n/i' else valor

    valores = (
        converter_ni(instrumento.get('identificacao')),
        converter_ni(instrumento.get('nome')),
        converter_ni(instrumento.get('fabricante')),
        converter_ni(instrumento.get('modelo')),
        converter_ni(instrumento.get('numero_serie')),
        converter_ni(instrumento.get('descricao')),
        instrumento.get('periodicidade', 12),
        converter_ni(instrumento.get('departamento')),
        converter_ni(instrumento.get('responsavel')),
        instrumento.get('status', 'Sem Calibração'),
        converter_ni(instrumento.get('tipo_familia')),
        converter_ni(instrumento.get('serie_desenv')),
        converter_ni(instrumento.get('criticidade')),
        converter_ni(instrumento.get('motivo_calibracao')),
        instrumento.get('quantidade', 1),
        user_id,
        user_id,
        now,
        now
    )

    cursor.execute(sql, valores)
    return cursor.lastrowid


def deletar_grandezas_antigas(cursor, instrumento_id):
    """Deleta grandezas antigas de um instrumento"""
    cursor.execute("DELETE FROM grandezas WHERE instrumento_id = %s", (instrumento_id,))


def inserir_grandeza(cursor, grandeza, instrumento_id):
    """Insere uma grandeza no banco"""

    sql = """
    INSERT INTO grandezas
    (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica,
     unidade, resolucao, criterio_aceitacao, regra_decisao_id,
     faixa_nominal, classe_norma, classificacao, faixa_uso,
     created_at, updated_at)
    VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Converte array de serviços para JSON
    servicos_json = json.dumps(grandeza.get('servicos', []), ensure_ascii=False)

    valores = (
        instrumento_id,
        servicos_json,
        grandeza.get('tolerancia_processo'),
        1 if grandeza.get('tolerancia_simetrica') else 0,
        grandeza.get('unidade'),
        grandeza.get('resolucao'),
        grandeza.get('criterio_aceitacao'),
        grandeza.get('regra_decisao_id', 1),
        grandeza.get('faixa_nominal'),
        grandeza.get('classe_norma'),
        grandeza.get('classificacao'),
        grandeza.get('faixa_uso'),
        now,
        now
    )

    cursor.execute(sql, valores)
    return cursor.lastrowid


def processar_e_inserir():
    """Processa PDFs da pasta e insere no banco"""

    print("="*60)
    print("PROCESSAMENTO E INSERCAO NO BANCO")
    print("="*60)

    # Busca PDFs na pasta
    pasta_pdfs = Path('pdfs')
    if not pasta_pdfs.exists():
        print("[ERRO] Pasta 'pdfs' nao encontrada")
        return

    pdfs = list(pasta_pdfs.glob('*.pdf'))

    if not pdfs:
        print("[AVISO] Nenhum PDF encontrado na pasta 'pdfs'")
        print("        Coloque os certificados na pasta 'pdfs' e execute novamente")
        return

    print(f"\n[INFO] Encontrados {len(pdfs)} PDFs na pasta 'pdfs'")

    # Processa PDFs
    print("\n" + "="*60)
    print("EXTRAINDO DADOS DOS PDFS...")
    print("="*60)

    extrator = ExtratorCertificado()
    instrumentos = extrator.processar_multiplos_pdfs([str(pdf) for pdf in pdfs])

    if not instrumentos:
        print("[ERRO] Nenhum instrumento extraido")
        return

    print(f"\n[OK] {len(instrumentos)} instrumentos extraidos")

    # Conecta ao banco
    print("\n" + "="*60)
    print("CONECTANDO AO BANCO DE DADOS...")
    print("="*60)

    conn = conectar_banco()
    if not conn:
        return

    cursor = conn.cursor()

    # Insere instrumentos
    print("\n" + "="*60)
    print("INSERINDO NO BANCO...")
    print("="*60)

    total_grandezas = 0
    instrumentos_novos = 0
    instrumentos_atualizados = 0

    try:
        for i, instrumento in enumerate(instrumentos, 1):
            identificacao = instrumento.get('identificacao', 'N/I')
            print(f"\n[{i}/{len(instrumentos)}] Processando: {identificacao}")

            # Verifica se instrumento já existe
            instrumento_id_existente = verificar_instrumento_existente(cursor, instrumento)

            if instrumento_id_existente:
                # Atualiza instrumento existente
                print(f"  [INFO] Instrumento já existe (ID: {instrumento_id_existente})")
                print(f"  [INFO] Atualizando dados...")
                
                instrumento_id = atualizar_instrumento(cursor, instrumento_id_existente, instrumento)
                
                # Deleta grandezas antigas
                deletar_grandezas_antigas(cursor, instrumento_id)
                print(f"  [INFO] Grandezas antigas removidas")
                
                instrumentos_atualizados += 1
            else:
                # Insere novo instrumento
                print(f"  [INFO] Novo instrumento detectado")
                instrumento_id = inserir_instrumento(cursor, instrumento)
                print(f"  [OK] Instrumento inserido (ID: {instrumento_id})")
                instrumentos_novos += 1

            # Insere grandezas (novas ou atualizadas)
            grandezas = instrumento.get('grandezas', [])
            for j, grandeza in enumerate(grandezas, 1):
                grandeza_id = inserir_grandeza(cursor, grandeza, instrumento_id)
                print(f"  [OK] Grandeza {j} inserida (ID: {grandeza_id})")
                total_grandezas += 1

        # Commit
        conn.commit()

        print("\n" + "="*60)
        print("CONCLUIDO COM SUCESSO!")
        print("="*60)
        print(f"\nResumo:")
        print(f"  - {instrumentos_novos} instrumentos NOVOS inseridos")
        print(f"  - {instrumentos_atualizados} instrumentos ATUALIZADOS")
        print(f"  - {total_grandezas} grandezas processadas")
        print(f"\nAcesse o visualizador: http://localhost:5000/visualizar")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERRO] Falha ao processar: {e}")
        import traceback
        traceback.print_exc()

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    processar_e_inserir()
