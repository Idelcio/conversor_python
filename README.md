# Extrator de Certificados de Calibração - Gocal

Sistema para extrair informações de certificados de calibração em PDF e gerar dados estruturados (JSON e SQL) para importação no sistema Gocal.

## 📋 Funcionalidades

- ✅ Upload de múltiplos PDFs via interface web
- ✅ Extração automática de dados dos certificados
- ✅ Busca inteligente por palavras-chave
- ✅ Mesclagem automática de PDFs do mesmo instrumento
- ✅ Geração de JSON estruturado
- ✅ Geração de SQL INSERT pronto para importação
- ✅ Interface web moderna e intuitiva

## 🚀 Como Usar

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Iniciar o Servidor

```bash
python app.py
```

### 3. Acessar a Interface Web

Abra seu navegador em: **http://localhost:5000**

### 4. Fazer Upload dos PDFs

1. Clique ou arraste os PDFs para a área de upload
2. Clique em "Processar Certificados"
3. Aguarde o processamento
4. Baixe o JSON ou SQL gerado

## 📁 Estrutura de Arquivos

```
leitor_conversor/
├── app.py                  # Servidor Flask
├── extrator_pdf.py         # Lógica de extração de PDFs
├── gerador_sql.py          # Gerador de SQL INSERT
├── requirements.txt        # Dependências Python
├── README.md              # Este arquivo
└── templates/
    └── index.html         # Interface web
```

## 🔍 Campos Extraídos

### Instrumento:
- Identificação/Tag
- Nome/Descrição
- Fabricante
- Modelo
- Número de Série
- Departamento/Localização
- Responsável
- Data de Calibração
- Data de Emissão

### Grandezas:
- Serviços (procedimentos)
- Unidade de medida
- Resolução
- Faixa nominal
- Tolerância do processo
- Critério de aceitação

**Campos não encontrados são preenchidos com "n/i"**

## 📊 Formato de Saída

### JSON
```json
{
  "total_instrumentos": 2,
  "instrumentos": [
    {
      "identificacao": "ALT-001",
      "nome": "Medidor de Altura",
      "fabricante": "DIGIMESS",
      "grandezas": [...]
    }
  ]
}
```

### SQL
```sql
INSERT INTO instrumentos (identificacao, nome, fabricante, ...)
VALUES ('ALT-001', 'Medidor de Altura', 'DIGIMESS', ...);

INSERT INTO grandezas (instrumento_id, servicos, unidade, ...)
VALUES (LAST_INSERT_ID(), '["Calibração"]', 'mm', ...);
```

## 🛠️ Uso em Linha de Comando

### Processar PDFs sem interface web:

```bash
python extrator_pdf.py
```
(Processa todos os PDFs na pasta atual e gera `instrumentos.json`)

### Gerar SQL a partir de JSON:

```bash
python gerador_sql.py instrumentos.json
```
(Gera `instrumentos.sql`)

## ⚙️ Configurações

### Alterar User ID padrão:

No arquivo `gerador_sql.py`, altere:

```python
gerador = GeradorSQL(user_id=1)  # Altere para o ID correto
```

### Ajustar regra de decisão padrão:

No arquivo `extrator_pdf.py`, em `extrair_grandezas()`:

```python
'regra_decisao_id': 1,  # Altere conforme necessário
```

## 🔄 Mesclagem de Instrumentos

O sistema identifica instrumentos duplicados usando:
1. **Número de série** (prioridade)
2. **Identificação** (se número de série não existir)

Se múltiplos PDFs do mesmo instrumento forem enviados, as informações são mescladas automaticamente.

## 📝 Observações

- PDFs de formatos muito diferentes podem ter extração parcial
- Revise sempre o JSON gerado antes de importar o SQL
- O sistema busca palavras-chave comuns em certificados brasileiros
- Certificados de laboratórios acreditados têm melhor taxa de extração

## 🐛 Problemas Comuns

### "Nenhum texto extraído"
- O PDF pode ser uma imagem escaneada
- Tente usar OCR ou reescrever o PDF

### "Campo não encontrado"
- O formato do certificado pode ser muito diferente
- Verifique o JSON e preencha manualmente se necessário

### "Erro ao processar"
- Verifique se o arquivo é um PDF válido
- Tente reenviar o arquivo

## 📞 Suporte

Para dúvidas ou problemas, revise os logs no console do servidor.

---

**Desenvolvido para o Sistema Gocal** 🚀
