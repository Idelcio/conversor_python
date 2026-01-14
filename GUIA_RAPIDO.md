# Guia Rápido - Extrator de Certificados Gocal

## Instalação

```bash
# Instalar dependências
pip install -r requirements.txt
```

## Como Usar

### 1. Preparar PDFs

Coloque todos os certificados de calibração na pasta `pdfs/`:

```
leitor_conversor/
├── pdfs/
│   ├── certificado1.pdf
│   ├── certificado2.pdf
│   └── certificado3.pdf
```

### 2. Processar e Inserir no Banco

Execute o script que extrai dados dos PDFs e insere direto no MySQL:

```bash
python inserir_banco.py
```

O script vai:
- Ler todos os PDFs da pasta `pdfs/`
- Extrair informações dos certificados
- Conectar ao banco MySQL
- Inserir instrumentos e grandezas
- Mostrar relatório de sucesso

### 3. Visualizar no Navegador

```bash
# Inicie o servidor (se não estiver rodando)
python app.py

# Acesse no navegador:
# http://localhost:5000/visualizar
```

## Fluxo Completo

```
PDFs na pasta → inserir_banco.py → MySQL → Visualizador Web
```

## Estrutura do Banco

O script espera as tabelas:
- `instrumentos` - Dados principais dos instrumentos
- `grandezas` - Grandezas calibradas de cada instrumento

## Configuração do Banco

Edite em `inserir_banco.py` se suas credenciais forem diferentes:

```python
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'instrumentos',
    'user': 'root',
    'password': ''  # Altere se necessário
}
```

## Comandos Úteis

```bash
# Processar PDFs sem inserir no banco (só gerar JSON/SQL)
python processar_pdfs.py

# Iniciar servidor web
python app.py

# Testar upload individual
python teste_upload.py
```

## Acesso Rápido

- **Upload de PDFs:** http://localhost:5000
- **Visualizador:** http://localhost:5000/visualizar
- **API Instrumentos:** http://localhost:5000/api/instrumentos

## Solução de Problemas

### Erro ao conectar no MySQL
- Verifique se o MySQL está rodando
- Confirme as credenciais em `inserir_banco.py`
- Verifique se o banco `instrumentos` existe

### Nenhum PDF encontrado
- Certifique-se que os PDFs estão na pasta `pdfs/`
- Verifique se os arquivos têm extensão `.pdf`

### Campos com "n/i"
- Normal para informações que não estão no PDF
- Você pode editar o JSON gerado antes de inserir
- Ou ajustar manualmente no banco depois
