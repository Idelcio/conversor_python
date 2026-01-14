"""
Script para criar as tabelas no banco MySQL
"""

import mysql.connector

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': ''
}

def criar_tabelas():
    print("="*60)
    print("CRIANDO TABELAS NO BANCO DE DADOS")
    print("="*60)

    try:
        # Conecta ao MySQL (sem especificar database)
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Cria o banco se não existir
        print("\n[INFO] Criando banco 'instrumentos' se nao existir...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS instrumentos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE instrumentos")
        print("[OK] Banco selecionado")

        # Cria tabela instrumentos
        print("\n[INFO] Criando tabela 'instrumentos'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS instrumentos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                identificacao VARCHAR(255),
                nome VARCHAR(255),
                fabricante VARCHAR(255),
                modelo VARCHAR(255),
                numero_serie VARCHAR(255),
                descricao TEXT,
                periodicidade INT DEFAULT 12,
                departamento VARCHAR(255),
                responsavel VARCHAR(255),
                status VARCHAR(50) DEFAULT 'Sem Calibracao',
                tipo_familia VARCHAR(255),
                serie_desenv VARCHAR(255),
                criticidade VARCHAR(100),
                motivo_calibracao VARCHAR(255),
                quantidade INT DEFAULT 1,
                user_id INT NOT NULL DEFAULT 1,
                responsavel_cadastro_id INT NOT NULL DEFAULT 1,
                data_calibracao DATE,
                data_emissao DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("[OK] Tabela 'instrumentos' criada")

        # Cria tabela grandezas
        print("\n[INFO] Criando tabela 'grandezas'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grandezas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                instrumento_id INT NOT NULL,
                servicos JSON,
                tolerancia_processo VARCHAR(255),
                tolerancia_simetrica BOOLEAN DEFAULT TRUE,
                unidade VARCHAR(50),
                resolucao VARCHAR(100),
                criterio_aceitacao TEXT,
                regra_decisao_id INT DEFAULT 1,
                faixa_nominal VARCHAR(255),
                classe_norma VARCHAR(100),
                classificacao VARCHAR(100),
                faixa_uso VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (instrumento_id) REFERENCES instrumentos(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("[OK] Tabela 'grandezas' criada")

        conn.commit()

        print("\n" + "="*60)
        print("TABELAS CRIADAS COM SUCESSO!")
        print("="*60)
        print("\nProximo passo:")
        print("  python inserir_banco.py")

    except Exception as e:
        print(f"\n[ERRO] Falha ao criar tabelas: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    criar_tabelas()
