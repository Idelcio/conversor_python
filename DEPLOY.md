# 🚀 Guia de Deploy - Chat Metron com LLaMA

## ✅ Checklist Pré-Deploy

### 1. **Variáveis de Ambiente (.env)**
O arquivo `.env` **NÃO** deve ser commitado no Git (já está no `.gitignore`).

No servidor de produção, você precisa criar um arquivo `.env` com:

```bash
# Configurações do Groq API
GROQ_API_KEY=sua_chave_groq_aqui

# Configurações do Banco de Dados
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=instrumentos
DB_USER=root
DB_PASSWORD=sua_senha_aqui
```

### 2. **Dependências Python**
Instale todas as dependências no servidor:

```bash
pip install -r requirements.txt
```

### 3. **Groq API Key**
- ✅ A API key do Groq está configurada no `.env`
- ✅ A key é válida e tem créditos disponíveis
- ✅ O modelo `llama-3.3-70b-versatile` está disponível

### 4. **Banco de Dados MySQL**
Certifique-se de que:
- ✅ MySQL está instalado e rodando
- ✅ O banco `instrumentos` existe
- ✅ As tabelas `instrumentos` e `grandezas` estão criadas
- ✅ As credenciais no `.env` estão corretas

### 5. **Servidor WSGI (Produção)**
⚠️ **IMPORTANTE**: Não use `app.run()` em produção!

Use um servidor WSGI como **Gunicorn**:

```bash
# Instalar Gunicorn
pip install gunicorn

# Rodar o servidor
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Ou configure com **systemd** para rodar como serviço.

---

## 🔧 Configuração do Servidor

### Opção 1: Gunicorn (Recomendado)

1. **Instale o Gunicorn:**
```bash
pip install gunicorn
```

2. **Crie um arquivo de serviço systemd:**
```bash
sudo nano /etc/systemd/system/metron.service
```

3. **Conteúdo do arquivo:**
```ini
[Unit]
Description=Metron Chat Extrator
After=network.target

[Service]
User=seu_usuario
WorkingDirectory=/caminho/para/leitor_conversor
Environment="PATH=/caminho/para/venv/bin"
ExecStart=/caminho/para/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

4. **Ative e inicie o serviço:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable metron
sudo systemctl start metron
sudo systemctl status metron
```

### Opção 2: PM2 (Node.js Process Manager)

Se você já usa PM2 para outros projetos:

```bash
pm2 start app.py --name metron --interpreter python3
pm2 save
pm2 startup
```

---

## 🌐 Nginx (Proxy Reverso)

Configure o Nginx para servir a aplicação:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Aumentar timeout para processamento de PDFs
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;
}
```

---

## 🔒 Segurança

### 1. **Proteja o arquivo .env**
```bash
chmod 600 .env
```

### 2. **Firewall**
Abra apenas as portas necessárias:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 3. **SSL/HTTPS (Certbot)**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com
```

---

## 📊 Monitoramento

### Verificar logs do Gunicorn:
```bash
sudo journalctl -u metron -f
```

### Verificar logs do Nginx:
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## 🧪 Teste Pós-Deploy

1. **Teste a API Groq:**
```bash
python test_groq.py
```

2. **Teste o servidor:**
```bash
curl http://localhost:5000/health
```

3. **Teste o chat:**
- Acesse `http://seu-dominio.com`
- Envie uma mensagem: "oi"
- Envie um cálculo: "10 + 10"
- Faça upload de um PDF e extraia dados

---

## ⚠️ Problemas Comuns

### 1. **LLaMA não responde**
- ✅ Verifique se a `GROQ_API_KEY` está correta no `.env`
- ✅ Verifique os logs: `sudo journalctl -u metron -f`
- ✅ Teste a API diretamente: `python test_groq.py`

### 2. **Erro de conexão com MySQL**
- ✅ Verifique se o MySQL está rodando: `sudo systemctl status mysql`
- ✅ Verifique as credenciais no `.env`
- ✅ Teste a conexão: `mysql -u root -p`

### 3. **Timeout ao processar PDFs**
- ✅ Aumente o timeout do Nginx (veja configuração acima)
- ✅ Aumente o timeout do Gunicorn: `--timeout 300`

---

## 📝 Notas Importantes

1. **Groq API Key**: Mantenha sua chave segura e nunca a commite no Git
2. **Modelo LLaMA**: O modelo `llama-3.3-70b-versatile` é gratuito no Groq
3. **Rate Limits**: Verifique os limites da API Groq no dashboard
4. **Backup**: Faça backup regular do banco de dados MySQL

---

## 🎯 Resumo

✅ **O LLaMA vai funcionar no deploy** se você:
1. Configurar corretamente o arquivo `.env` no servidor
2. Instalar todas as dependências (`requirements.txt`)
3. Usar um servidor WSGI (Gunicorn) em vez de `app.run()`
4. Garantir que a API key do Groq está válida

**Boa sorte com o deploy! 🚀**
