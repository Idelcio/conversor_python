"""
Gerador de SQL para importação de instrumentos no banco de dados
Gera comandos INSERT para as tabelas instrumentos e grandezas
"""

import json
from datetime import datetime
from typing import List, Dict, Any


class GeradorSQL:
    """Gera comandos SQL INSERT a partir dos dados extraídos dos PDFs"""

    def __init__(self, user_id: int = 1):
        """
        Args:
            user_id: ID do usuário/empresa dona dos instrumentos
        """
        self.user_id = user_id

    def escapar_string(self, valor: Any) -> str:
        """Escapa string para SQL"""
        if valor is None or valor == 'n/i':
            return 'NULL'

        if isinstance(valor, (int, float)):
            return str(valor)

        if isinstance(valor, bool):
            return '1' if valor else '0'

        if isinstance(valor, list):
            # Converte array para JSON
            return f"'{json.dumps(valor, ensure_ascii=False)}'"

        # String - escapa aspas simples
        valor_str = str(valor).replace("'", "''")
        return f"'{valor_str}'"

    def gerar_insert_instrumento(self, instrumento: Dict[str, Any], instrumento_id: int = None) -> str:
        """Gera comando INSERT para um instrumento"""

        # Campos do instrumento
        campos = {
            'identificacao': instrumento.get('identificacao', 'n/i'),
            'nome': instrumento.get('nome', 'n/i'),
            'fabricante': instrumento.get('fabricante', 'n/i'),
            'modelo': instrumento.get('modelo', 'n/i'),
            'numero_serie': instrumento.get('numero_serie', 'n/i'),
            'descricao': instrumento.get('descricao', 'n/i'),
            'periodicidade': instrumento.get('periodicidade', 12),
            'departamento': instrumento.get('departamento', 'n/i'),
            'responsavel': instrumento.get('responsavel', 'n/i'),
            'status': instrumento.get('status', 'Sem Calibração'),
            'tipo_familia': instrumento.get('tipo_familia', 'n/i'),
            'serie_desenv': instrumento.get('serie_desenv'),
            'criticidade': instrumento.get('criticidade'),
            'motivo_calibracao': instrumento.get('motivo_calibracao'),
            'quantidade': instrumento.get('quantidade', 1),
            'user_id': self.user_id,
            'responsavel_cadastro_id': self.user_id,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        # Monta o INSERT
        colunas = ', '.join(campos.keys())
        valores = ', '.join([self.escapar_string(v) for v in campos.values()])

        sql = f"INSERT INTO instrumentos ({colunas})\nVALUES ({valores});\n"

        # Adiciona comentário com informações extras
        comentario = f"-- Instrumento: {instrumento.get('identificacao')} - {instrumento.get('nome')}\n"

        return comentario + sql

    def gerar_insert_grandeza(self, grandeza: Dict[str, Any], instrumento_id_var: str = "LAST_INSERT_ID()") -> str:
        """Gera comando INSERT para uma grandeza"""

        # Campos da grandeza
        campos = {
            'instrumento_id': f"@instrumento_id_{instrumento_id_var}",  # Será substituído
            'servicos': grandeza.get('servicos', []),
            'tolerancia_processo': grandeza.get('tolerancia_processo', 'n/i'),
            'tolerancia_simetrica': grandeza.get('tolerancia_simetrica', True),
            'unidade': grandeza.get('unidade', 'n/i'),
            'resolucao': grandeza.get('resolucao', 'n/i'),
            'criterio_aceitacao': grandeza.get('criterio_aceitacao'),
            'regra_decisao_id': grandeza.get('regra_decisao_id', 1),
            'faixa_nominal': grandeza.get('faixa_nominal'),
            'classe_norma': grandeza.get('classe_norma'),
            'classificacao': grandeza.get('classificacao'),
            'faixa_uso': grandeza.get('faixa_uso'),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        # Monta o INSERT (sem escapar o instrumento_id ainda)
        colunas_list = []
        valores_list = []

        for col, val in campos.items():
            colunas_list.append(col)
            if col == 'instrumento_id':
                valores_list.append(val)  # Não escapa (é variável)
            else:
                valores_list.append(self.escapar_string(val))

        colunas = ', '.join(colunas_list)
        valores = ', '.join(valores_list)

        return f"INSERT INTO grandezas ({colunas})\nVALUES ({valores});\n"

    def gerar_sql_instrumento_completo(self, instrumento: Dict[str, Any], index: int) -> str:
        """Gera SQL completo para um instrumento (incluindo grandezas)"""

        sql_parts = []

        # Comentário de separação
        sql_parts.append(f"\n-- {'='*70}")
        sql_parts.append(f"-- Instrumento #{index + 1}: {instrumento.get('identificacao')}")
        sql_parts.append(f"-- ={'='*70}\n")

        # INSERT do instrumento
        sql_parts.append(self.gerar_insert_instrumento(instrumento, index))

        # Captura o ID do instrumento inserido
        sql_parts.append(f"SET @instrumento_id_{index} = LAST_INSERT_ID();\n")

        # INSERT das grandezas
        grandezas = instrumento.get('grandezas', [])
        if grandezas:
            sql_parts.append(f"\n-- Grandezas do instrumento {instrumento.get('identificacao')}\n")

            for i, grandeza in enumerate(grandezas):
                grandeza_sql = self.gerar_insert_grandeza(grandeza, index)
                # Substitui a variável pelo ID correto
                grandeza_sql = grandeza_sql.replace(f"@instrumento_id_{index}", f"@instrumento_id_{index}")
                sql_parts.append(grandeza_sql)

        return '\n'.join(sql_parts)

    def gerar_sql_completo(self, instrumentos: List[Dict[str, Any]]) -> str:
        """Gera arquivo SQL completo com todos os instrumentos"""

        sql_parts = []

        # Cabeçalho
        sql_parts.append("-- " + "="*70)
        sql_parts.append("-- SQL de Importação de Instrumentos - Sistema Gocal")
        sql_parts.append(f"-- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sql_parts.append(f"-- Total de instrumentos: {len(instrumentos)}")
        sql_parts.append("-- " + "="*70)
        sql_parts.append("\n")

        # Configurações
        sql_parts.append("SET FOREIGN_KEY_CHECKS=0;")
        sql_parts.append("SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';")
        sql_parts.append("SET AUTOCOMMIT = 0;")
        sql_parts.append("START TRANSACTION;\n")

        # Processa cada instrumento
        for i, instrumento in enumerate(instrumentos):
            sql_parts.append(self.gerar_sql_instrumento_completo(instrumento, i))

        # Finalização
        sql_parts.append("\n-- Finalização")
        sql_parts.append("COMMIT;")
        sql_parts.append("SET FOREIGN_KEY_CHECKS=1;\n")

        # Resumo
        total_grandezas = sum(len(inst.get('grandezas', [])) for inst in instrumentos)
        sql_parts.append(f"\n-- Resumo:")
        sql_parts.append(f"-- [OK] {len(instrumentos)} instrumentos inseridos")
        sql_parts.append(f"-- [OK] {total_grandezas} grandezas inseridas\n")

        return '\n'.join(sql_parts)

    def salvar_sql(self, instrumentos: List[Dict[str, Any]], arquivo_saida: str = "instrumentos.sql"):
        """Gera e salva o arquivo SQL"""

        sql_content = self.gerar_sql_completo(instrumentos)

        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write(sql_content)

        print(f"\n[OK] SQL gerado: {arquivo_saida}")

        return arquivo_saida


def main():
    """Função principal para teste - lê JSON e gera SQL"""
    import sys

    if len(sys.argv) < 2:
        print("Uso: python gerador_sql.py <arquivo.json>")
        return

    arquivo_json = sys.argv[1]

    try:
        with open(arquivo_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        instrumentos = data.get('instrumentos', [])

        if not instrumentos:
            print("Nenhum instrumento encontrado no JSON")
            return

        gerador = GeradorSQL()
        arquivo_sql = gerador.salvar_sql(instrumentos)

        print(f"Total de instrumentos: {len(instrumentos)}")
        print(f"Arquivo SQL: {arquivo_sql}")

    except FileNotFoundError:
        print(f"Arquivo não encontrado: {arquivo_json}")
    except json.JSONDecodeError:
        print(f"Erro ao ler JSON: {arquivo_json}")
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    main()
