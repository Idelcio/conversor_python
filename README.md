# 🤖 Metron - Chat Extrator de Certificados

Assistente inteligente com LLaMA 3.3 para extração de dados de certificados de calibração.

## ✨ Funcionalidades

- 🤖 **Chat Inteligente** com LLaMA 3.3 (Groq API)
- 📄 **Extração de PDFs** de certificados de calibração
- 💾 **Inserção automática** no banco MySQL
- 📊 **Visualização** de dados extraídos
- 🌙 **Modo escuro/claro**
- 💬 **Conversação contextual** (lembra seu nome e histórico)

## 🚀 Quick Start (Desenvolvimento)

1. **Clone o repositório**
```bash
git clone <seu-repo>
cd leitor_conversor
```

2. **Configure o ambiente**
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite e adicione sua GROQ_API_KEY
nano .env
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Inicie o servidor**
```bash
python app.py
```

5. **Acesse o chat**
```
http://localhost:5000
```

## 🌐 Deploy em Produção

### Opção 1: Gunicorn (Recomendado)

```bash
# Instale as dependências
pip install -r requirements.txt

# Configure o .env
cp .env.example .env
nano .env

# Inicie com Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 300 app:app
```

### Opção 2: Script Automático

**Linux/Mac:**
```bash
chmod +x start_production.sh
./start_production.sh
```

**Windows:**
```cmd
start_production.bat
```

## 📋 Requisitos

- Python 3.8+
- MySQL 5.7+
- Groq API Key (gratuita em https://console.groq.com)

## 🔑 Variáveis de Ambiente (.env)

```bash
# Groq API
GROQ_API_KEY=sua_chave_aqui

# MySQL
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=instrumentos
DB_USER=root
DB_PASSWORD=sua_senha
```

## 📖 Guia Completo de Deploy

Veja o arquivo [DEPLOY.md](DEPLOY.md) para instruções detalhadas de deploy em produção.

## 🧪 Testando o LLaMA

```bash
python test_groq.py
```

## 💡 Exemplos de Uso

### Chat Inteligente
- "oi" → Cumprimento
- "quanto é 10 + 10?" → Cálculo
- "qual a capital do Brasil?" → Pergunta geral

### Extração de PDFs
1. Faça upload dos PDFs na lateral esquerda
2. Digite comandos como:
   - "extrair tudo"
   - "mostrar apenas as tags"
   - "extrair fabricante e modelo"

## 🛠️ Tecnologias

- **Backend**: Flask 3.0
- **IA**: Groq API (LLaMA 3.3 70B)
- **PDF**: pdfplumber
- **Banco**: MySQL
- **Frontend**: HTML/CSS/JavaScript (Vanilla)

## 📝 Estrutura do Projeto

```
leitor_conversor/
├── app.py                    # Servidor Flask principal
├── assistente_groq.py        # Integração com Groq API
├── sessoes.py                # Gerenciamento de sessões
├── extrator_pdf.py           # Extração de dados dos PDFs
├── gerador_sql.py            # Geração de SQL
├── inserir_banco.py          # Inserção no MySQL
├── templates/
│   └── index_chat_modern.html # Interface do chat
├── .env                      # Variáveis de ambiente (não commitar!)
├── .env.example              # Template de variáveis
├── requirements.txt          # Dependências Python
├── DEPLOY.md                 # Guia de deploy
└── README.md                 # Este arquivo
```

## 🔒 Segurança

⚠️ **IMPORTANTE**: 
- Nunca commite o arquivo `.env` no Git
- Mantenha sua `GROQ_API_KEY` segura
- Use HTTPS em produção
- Configure firewall adequadamente

## 📊 Monitoramento

### Logs do servidor
```bash
# Desenvolvimento
python app.py

# Produção (Gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - app:app
```

## ❓ Problemas Comuns

### LLaMA não responde
- ✅ Verifique se `GROQ_API_KEY` está configurada
- ✅ Teste: `python test_groq.py`
- ✅ Verifique os logs do servidor

### Erro de conexão MySQL
- ✅ Verifique se MySQL está rodando
- ✅ Confirme credenciais no `.env`
- ✅ Teste: `mysql -u root -p`

## 📄 Licença

Desenvolvido por Gocal

---

**Powered by Groq LLaMA 3.3** 🚀
