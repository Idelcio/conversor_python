"""
Extrator de Informações de Certificados de Calibração
Extrai dados de PDFs e gera JSON estruturado para importação no sistema Gocal
"""

import pdfplumber
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Tenta importar PyMuPDF como fallback
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


class ExtratorCertificado:
    """Extrai informações de certificados de calibração em PDF"""

    def __init__(self):
        self.instrumentos = {}

    def extrair_texto_pdf(self, caminho_pdf: str) -> str:
        """Extrai todo o texto do PDF usando pdfplumber e PyMuPDF como fallback"""
        texto_pdfplumber = self._extrair_com_pdfplumber(caminho_pdf)

        # Verifica se o texto parece corrompido (muitos caracteres duplicados de data)
        if self._texto_parece_corrompido(texto_pdfplumber) and HAS_PYMUPDF:
            texto_pymupdf = self._extrair_com_pymupdf(caminho_pdf)
            # Combina os dois textos para ter mais dados
            return texto_pdfplumber + "\n" + texto_pymupdf

        return texto_pdfplumber

    def _extrair_com_pdfplumber(self, caminho_pdf: str) -> str:
        """Extrai texto usando pdfplumber"""
        texto_completo = []
        try:
            with pdfplumber.open(caminho_pdf) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if texto:
                        texto_completo.append(texto)
        except Exception as e:
            print(f"[ERRO] pdfplumber falhou em {caminho_pdf}: {e}")
        return "\n".join(texto_completo)

    def _extrair_com_pymupdf(self, caminho_pdf: str) -> str:
        """Extrai texto usando PyMuPDF (fallback)"""
        texto_completo = []
        try:
            doc = fitz.open(caminho_pdf)
            for page in doc:
                texto = page.get_text()
                if texto:
                    texto_completo.append(texto)
            doc.close()
        except Exception as e:
            print(f"[ERRO] PyMuPDF falhou em {caminho_pdf}: {e}")
        return "\n".join(texto_completo)

    def _texto_parece_corrompido(self, texto: str) -> bool:
        """Verifica se o texto extraido parece corrompido (datas com muitos digitos)"""
        # Procura padroes de data corrompida (ex: 033310///000676//22/0202025255)
        padrao_corrompido = r'\d{3,}///\d{3,}//\d{2}/\d{6,}'
        return bool(re.search(padrao_corrompido, texto))

    def _buscar_data_agressivo(self, texto: str, contexto: str) -> Optional[str]:
        """Busca data de forma agressiva quando padroes normais falham"""
        from collections import Counter

        # Encontra todas as datas no formato DD/MM/YYYY com suas posições
        datas_encontradas = [(m.group(1), m.start()) for m in re.finditer(r'(\d{2}/\d{2}/\d{4})', texto)]
        if not datas_encontradas:
            return None

        # Filtra apenas datas válidas
        datas_validas = [d for d, p in datas_encontradas if self._validar_data(d)]
        if not datas_validas:
            return None

        # Conta frequência - geralmente a data de calibração aparece mais vezes
        contador = Counter(datas_validas)
        data_mais_comum, freq = contador.most_common(1)[0]

        # Se a data mais comum aparece pelo menos 2 vezes, usa ela
        if freq >= 2:
            dia, mes, ano = data_mais_comum.split('/')
            return f"{ano}-{mes}-{dia}"

        # Caso contrário, tenta encontrar por posição relativa ao contexto
        match_contexto = re.search(rf'data\s+d[ae]\s+{contexto}', texto, re.IGNORECASE)
        if match_contexto:
            pos_contexto = match_contexto.end()
            for data_str, pos in datas_encontradas:
                if pos > pos_contexto and self._validar_data(data_str):
                    dia, mes, ano = data_str.split('/')
                    return f"{ano}-{mes}-{dia}"

        # Último fallback: retorna a data mais comum mesmo se aparecer só 1 vez
        dia, mes, ano = data_mais_comum.split('/')
        return f"{ano}-{mes}-{dia}"

    def _validar_data(self, data_str: str) -> bool:
        """Valida se uma string de data é válida"""
        try:
            dia, mes, ano = data_str.split('/')
            dia, mes, ano = int(dia), int(mes), int(ano)
            # Dias por mês (simplificado)
            dias_mes = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if 1 <= mes <= 12 and 1 <= dia <= dias_mes[mes - 1]:
                return True
        except:
            pass
        return False

    def buscar_campo(self, texto: str, padroes: List[str], default: str = "n/i") -> str:
        """Busca um campo no texto usando múltiplos padrões regex"""
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                valor = match.group(1).strip()
                # Remove hífens múltiplos que indicam campo vazio
                if valor and valor not in ['---', '--', '-', '']:
                    return valor
        return default

    def buscar_data(self, texto: str, padroes: List[str]) -> Optional[str]:
        """Busca uma data no texto e retorna no formato YYYY-MM-DD"""
        meses_abrev = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
            'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
        }

        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                data_str = match.group(1).strip()
                # Tenta converter para formato padrão
                try:
                    # Formato: DD/MM/YYYY, DD/MM/YY
                    if '/' in data_str:
                        partes = data_str.split('/')
                        if len(partes) == 3:
                            dia, mes, ano = partes
                            if len(ano) == 2:
                                ano = '20' + ano
                            return f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"

                    # Formato: DD-MMM-YY (19-jan-24)
                    elif '-' in data_str:
                        partes = data_str.split('-')
                        if len(partes) == 3:
                            dia, mes_nome, ano = partes
                            mes_nome = mes_nome.lower()[:3]  # Primeiras 3 letras
                            if mes_nome in meses_abrev:
                                mes = meses_abrev[mes_nome]
                                if len(ano) == 2:
                                    ano = '20' + ano
                                return f"{ano}-{mes}-{dia.zfill(2)}"
                except:
                    pass
                return data_str
        return None

    def buscar_numero(self, texto: str, padroes: List[str]) -> Optional[float]:
        """Busca um número no texto"""
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                try:
                    numero_str = match.group(1).strip().replace(',', '.')
                    return float(numero_str)
                except:
                    pass
        return None

    def extrair_faixa_resolucao(self, texto: str) -> Dict[str, str]:
        """Extrai faixa de medição e resolução"""
        info = {
            'faixa_nominal': 'n/i',
            'resolucao': 'n/i',
            'unidade': 'n/i'
        }

        # Primeiro tenta extrair unidade do formato "Resolução (mm):" ou similar
        match_unidade = re.search(r'[Rr]esolu[çc][ãa]o\s*\(([^)]+)\)', texto)
        if match_unidade:
            info['unidade'] = match_unidade.group(1)

        # Padrões para faixa e resolução
        # Ex: "Faixa de 0 a 300 °C - Resolução de 0,01 °C"
        # Ex: "de 0 a 300 mm, com resolução de 0,01 mm"
        padrao_faixa = r'(?:Faixa de|de)\s+(\d+(?:,\d+)?)\s+a\s+(\d+(?:,\d+)?)\s*([°ºCcmMpPaA]+)'
        match_faixa = re.search(padrao_faixa, texto, re.IGNORECASE)

        if match_faixa:
            min_val = match_faixa.group(1).replace(',', '.')
            max_val = match_faixa.group(2).replace(',', '.')
            unidade = match_faixa.group(3)
            info['faixa_nominal'] = f"{min_val} a {max_val} {unidade}"
            info['unidade'] = unidade

        # Padrão para resolução
        padroes_resolucao = [
            r'[Rr]esolução\s+de\s+(\d+(?:[,\.]\d+)?)\s*([°ºCcmMpPaA]+)?',
            r'[Rr]esolu[çc][ãa]o\s*\(([^)]+)\)\s*:\s*(\d+(?:[,\.]\d+)?)',  # Resolução (mm): 0,0001
            r'[Rr]esolu[çc][ãa]o:\s*(\d+(?:[,\.]\d+)?)\s*([°ºCcmMpPaA]+)?'
        ]

        for padrao in padroes_resolucao:
            match_resolucao = re.search(padrao, texto)
            if match_resolucao:
                if len(match_resolucao.groups()) >= 2 and match_resolucao.group(2):
                    # Formato: Resolução (unidade): valor
                    if '(' in padrao:
                        unidade_res = match_resolucao.group(1)
                        resolucao = match_resolucao.group(2).replace(',', '.')
                    else:
                        resolucao = match_resolucao.group(1).replace(',', '.')
                        unidade_res = match_resolucao.group(2) if match_resolucao.group(2) else info['unidade']
                    info['resolucao'] = f"{resolucao} {unidade_res}"
                    break
                else:
                    resolucao = match_resolucao.group(1).replace(',', '.')
                    info['resolucao'] = f"{resolucao} {info['unidade']}"
                    break

        return info

    def extrair_grandezas(self, texto: str) -> List[Dict[str, Any]]:
        """Extrai informações de grandezas calibradas"""
        grandezas = []

        # Extrai faixa e resolução
        info_medicao = self.extrair_faixa_resolucao(texto)

        # Busca procedimento/serviço
        procedimento = self.buscar_campo(texto, [
            r'Procedimento:\s*([^\n]+)',
            r'Procedimento\s+([A-Z0-9]+\s*-[^\n]+)'
        ])

        # Busca método
        metodo = self.buscar_campo(texto, [
            r'Método:\s*([^\n]+)',
            r'Método\s+([^\n]+)'
        ])

        # Busca incerteza (tolerância do processo)
        incerteza = self.buscar_campo(texto, [
            r'IE[:\s]+([±\d,\.]+)',
            r'Incerteza[:\s]+([±\d,\.]+)',
            r'±IE[:\s]+([±\d,\.]+)'
        ], default="0,20")

        # Cria a grandeza
        grandeza = {
            'servicos': [procedimento] if procedimento != 'n/i' else [],
            'tolerancia_processo': incerteza,
            'tolerancia_simetrica': True,
            'unidade': info_medicao['unidade'],
            'resolucao': info_medicao['resolucao'],
            'criterio_aceitacao': metodo if metodo != 'n/i' else None,
            'regra_decisao_id': 1,  # Padrão - ajustar conforme necessário
            'faixa_nominal': info_medicao['faixa_nominal'],
            'classe_norma': None,
            'classificacao': None,
            'faixa_uso': None
        }

        grandezas.append(grandeza)

        return grandezas

    def extrair_instrumento(self, texto: str, nome_arquivo: str) -> Dict[str, Any]:
        """Extrai todas as informações do instrumento do certificado"""

        # Primeiro extrai o nome do item calibrado
        nome = self.buscar_campo(texto, [
            r'Descrição:\s*([^\n]+?)(?:\s+Fabricante|$)',
            r'Instrumento:\s*([^\n]+)',
            r'Denominação:\s*([^\n]+)',  # "Denominação: Transmissor de vazão"
            # Novos padrões
            r'ITEM CALIBRADO:\s*([^\n]+)',
            r'IDENTIFICAÇÃO DO ITEM CALIBRADO:\s*([^\n]+)'
        ])

        # Busca TAG/ID/Código específicos
        identificacao = self.buscar_campo(texto, [
            r'Autenticação:\s*([^\n]+)',
            r'Código\s+do\s+indicador:\s*([A-Z0-9\s\-]+?)(?:\s{2,}|Tipo|$)',  # "CVZ 001" (para antes de espaços duplos ou "Tipo")
            r'Código:\s*([^\n]+)',
            r'Tag:\s*([^\n]+)',
            r'ID:\s*([^\n]+)'
        ])

        # Se não encontrou TAG específica, usa o nome do item calibrado
        if identificacao == 'n/i' and nome != 'n/i':
            identificacao = nome

        # Se não encontrou nada, usa o nome do arquivo
        if identificacao == 'n/i':
            identificacao = Path(nome_arquivo).stem
            identificacao = identificacao.split()[0] if identificacao.split() else identificacao

        fabricante = self.buscar_campo(texto, [
            r'Fabricante:\s*([^\n]+)',
            r'Manufacturer:\s*([^\n]+)',
            # Novo padrão com espaços extras
            r'Fabricante\s*:\s*([^\n\r]+?)(?:\s+N[°º]|$)'
        ])

        modelo = self.buscar_campo(texto, [
            r'Modelo:\s*([^\n]+)',
            r'Model:\s*([^\n]+)',
            # Novo padrão com espaços extras
            r'Modelo\s*:\s*([^\n\r]+?)(?:\s+Fabricante|$)'
        ])

        numero_serie = self.buscar_campo(texto, [
            r'N[°º]\s*(?:de\s+)?Série:\s*([^\n]+)',
            r'Serial:\s*([^\n]+)',
            r'S/N:\s*([^\n]+)',
            # Novos padrões com variações de espaço
            r'N[°º]\s+S[eé]rie\s*:\s*([^\s\n\r]+)',
            r'Nº\s+Série\s*:\s*([^\s\n\r]+)'
        ])

        # Cliente e endereço
        cliente = self.buscar_campo(texto, [
            # Padrões específicos que evitam "Identificação do Cliente"
            r'Cliente\s+:\s+([^\n]+)',  # "Cliente :" com espaços (mais específico)
            r'Contratante:\s*([^\n]+)',
            r'Solicitante:\s*([^\n]+)',
            # Padrões genéricos (último recurso) - podem capturar "Identificação do Cliente"
            r'Cliente\s*:\s*([^\n\r]+?)(?:\s*(?:Endere[çc]o|Endere.o))',
            r'Cliente\s*:\s*(.+?)(?:\n)',
        ])

        endereco = self.buscar_campo(texto, [
            r'Endereço:\s*([^\n]+)',
            r'Endereco:\s*([^\n]+)',
            r'Local:\s*([^\n]+)',
            # Novo padrão com espaços extras
            r'Endereço\s*:\s*([^\n\r]+?)(?:\s+Cidade|$)',
            r'Endereco\s*:\s*([^\n\r]+?)(?:\s+Cidade|$)'
        ])

        # Datas
        data_calibracao = self.buscar_data(texto, [
            r'Data\s+(?:da\s+)?Calibração:\s*(\d{2}/\d{2}/\d{4})',
            r'Data\s+de\s+Calibração:\s*(\d{2}/\d{2}/\d{4})',
            r'Data\s+da\s+calibração:\s*(\d{2}/\d{2}/\d{4})',
            r'Data\s+da\s+calibra[çc][ãa]o\s*:\s*(\d{2}/\d{2}/\d{4})',
            r'Calibração:\s*(\d{2}/\d{2}/\d{4})',
            # Padrão mais flexível (qualquer variação de "calibração")
            r'Data\s+d[ae]\s+calibra\S*o\s*:\s*(\d{2}/\d{2}/\d{4})',
            # Formato DD-MMM-YY (19-jan-24)
            r'Data\s+da\s+calibra[çc][ãa]o\s*:\s*(\d{1,2}-[a-z]{3}-\d{2})',
            r'calibra[çc][ãa]o\s*:\s*(\d{1,2}-[a-z]{3}-\d{2})'
        ])

        # Se não encontrou, tenta busca mais agressiva (PyMuPDF separa labels de valores)
        if not data_calibracao:
            data_calibracao = self._buscar_data_agressivo(texto, 'calibra')

        data_emissao = self.buscar_data(texto, [
            r'Data\s+(?:da\s+)?Emissão:\s*(\d{2}/\d{2}/\d{4})',
            r'Data\s+de\s+Emissão:\s*(\d{2}/\d{2}/\d{4})',
            r'Data\s+de\s+Emissão\s+do\s+Certificado:\s*(\d{2}/\d{2}/\d{4})',
            r'Emissão:\s*(\d{2}/\d{2}/\d{4})',
            # Formato DD-MMM-YY (22-jan-24)
            r'Data\s+da\s+emiss[ãa]o\s*:\s*(\d{1,2}-[a-z]{3}-\d{2})',
            r'emiss[ãa]o\s*:\s*(\d{1,2}-[a-z]{3}-\d{2})'
        ])

        # Se não encontrou, tenta busca mais agressiva
        if not data_emissao:
            data_emissao = self._buscar_data_agressivo(texto, 'emiss')

        # Extrai grandezas
        grandezas = self.extrair_grandezas(texto)

        # Monta o instrumento
        instrumento = {
            'identificacao': identificacao,
            'nome': nome,
            'fabricante': fabricante,
            'modelo': modelo,
            'numero_serie': numero_serie,
            'descricao': nome,  # Usa o nome como descrição
            'periodicidade': 12,  # Padrão 12 meses
            'departamento': endereco,
            'responsavel': cliente,
            'tipo_familia': nome,  # Inferido do nome
            'serie_desenv': None,
            'criticidade': None,
            'motivo_calibracao': 'Calibração Periódica',
            'status': 'Sem Calibração',
            'quantidade': 1,
            'data_calibracao': data_calibracao,
            'data_emissao': data_emissao,
            'grandezas': grandezas,
            'arquivo_origem': nome_arquivo
        }

        return instrumento

    def processar_pdf(self, caminho_pdf: str) -> Dict[str, Any]:
        """Processa um PDF e retorna o instrumento extraído"""
        print(f"\nProcessando: {caminho_pdf}")

        texto = self.extrair_texto_pdf(caminho_pdf)

        if not texto:
            print(f"  [ERRO] Nao foi possivel extrair texto do PDF")
            return None

        instrumento = self.extrair_instrumento(texto, caminho_pdf)

        print(f"  [OK] Instrumento: {instrumento['identificacao']}")
        print(f"    - Nome: {instrumento['nome']}")
        print(f"    - Fabricante: {instrumento['fabricante']}")
        print(f"    - Nº Série: {instrumento['numero_serie']}")

        return instrumento

    def mesclar_instrumentos(self, inst1: Dict, inst2: Dict) -> Dict:
        """Mescla informações de dois instrumentos (mesmo instrumento, PDFs diferentes)"""
        merged = inst1.copy()

        # Para cada campo, se estiver vazio no primeiro, pega do segundo
        for campo, valor in inst2.items():
            if campo == 'grandezas':
                # Mescla grandezas (adiciona as que não existem)
                merged['grandezas'].extend(valor)
            elif campo == 'arquivo_origem':
                # Mantém lista de arquivos de origem
                if isinstance(merged.get('arquivo_origem'), list):
                    merged['arquivo_origem'].append(valor)
                else:
                    merged['arquivo_origem'] = [merged['arquivo_origem'], valor]
            elif merged.get(campo) in ['n/i', None, '']:
                merged[campo] = valor

        return merged

    def processar_multiplos_pdfs(self, caminhos_pdfs: List[str]) -> List[Dict[str, Any]]:
        """Processa múltiplos PDFs e mescla instrumentos duplicados"""
        instrumentos_dict = {}

        for caminho in caminhos_pdfs:
            instrumento = self.processar_pdf(caminho)

            if not instrumento:
                continue

            # Chave única: numero_serie (se existir) ou identificacao
            chave = instrumento['numero_serie']
            if chave == 'n/i':
                chave = instrumento['identificacao']

            # Se já existe, mescla
            if chave in instrumentos_dict and chave != 'n/i':
                print(f"  [INFO] Mesclando com instrumento existente (chave: {chave})")
                instrumentos_dict[chave] = self.mesclar_instrumentos(
                    instrumentos_dict[chave],
                    instrumento
                )
            else:
                instrumentos_dict[chave] = instrumento

        return list(instrumentos_dict.values())

    def gerar_json(self, instrumentos: List[Dict], arquivo_saida: str = "instrumentos.json"):
        """Gera arquivo JSON com os instrumentos extraídos"""
        dados = {
            'data_extracao': datetime.now().isoformat(),
            'total_instrumentos': len(instrumentos),
            'instrumentos': instrumentos
        }

        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] JSON gerado: {arquivo_saida}")
        print(f"  Total de instrumentos: {len(instrumentos)}")

        return arquivo_saida


def main():
    """Função principal para teste"""
    extrator = ExtratorCertificado()

    # Processa todos os PDFs na pasta atual
    pdfs = list(Path('.').glob('*.pdf'))

    if not pdfs:
        print("Nenhum PDF encontrado na pasta atual")
        return

    print(f"Encontrados {len(pdfs)} PDFs para processar")

    instrumentos = extrator.processar_multiplos_pdfs([str(pdf) for pdf in pdfs])

    # Gera JSON
    extrator.gerar_json(instrumentos)


if __name__ == "__main__":
    main()
