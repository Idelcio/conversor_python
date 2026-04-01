# VPS — Projetos e Infraestrutura

**IP:** 46.202.148.205
**Acesso:** `ssh root@46.202.148.205`

---

## Projetos Python ativos

### app_python — Metron (produção principal)
- **Diretório:** `/root/app_python/`
- **Porta:** 5001
- **Serviço systemd:** `metron.service`
- **URL Metron:** https://metron.gocal.site
- **Usado no Gocal:** widget carregado via `https://metron.gocal.site/static/js/widget_loader.js`
- **Banco:** MySQL `u693215843_teste` em `195.35.61.57:3306`
- **Git:** sim — `git pull origin main` para deploy
- **Deploy:** `cd /root/app_python && git pull origin main && systemctl restart metron.service`

### app_python2 — Metron (homologação/teste)
- **Diretório:** `/root/app_python2/`
- **Porta:** 5002
- **Serviço systemd:** `metron2.service`
- **URL Metron:** http://46.202.148.205:5002 (sem domínio/SSL)
- **Usado no Gocal:** não integrado em produção (ambiente de teste)
- **Banco:** MySQL `u693215843_teste` em `srv1781.hstgr.io:3306`
- **Git:** não — deploy feito copiando arquivos do app_python
- **Deploy:** ver seção abaixo

### app_python3 — Metron (demo)
- **Diretório:** `/root/app_python3/`
- **Porta:** 5003
- **Serviço systemd:** `metron3.service`
- **URL Metron:** https://metron2.gocal.store
- **Usado no Gocal:** ambiente demo separado
- **Banco:** MySQL `u693215843_demo` em `srv1147.hstgr.io:3306`
- **Git:** não — deploy manual
- **Deploy:** copiar arquivos manualmente

---

## Projeto Node.js

### chatbot — WhatsApp Bot
- **Diretório:** `/root/chatbot/`
- **Tecnologia:** Node.js + Baileys
- **Gerenciador:** PM2 (config em `/root/.pm2/`)
- **Arquivo principal:** `server.js`
- **Banco:** não identificado

---

### app_python4 — Metron (gocal.com.br)
- **Diretório:** `/root/app_python4/`
- **Porta:** 5004
- **Serviço systemd:** `metron4.service`
- **URL Metron:** https://metron.gocal.com.br
- **Usado no Gocal:** `https://metron.gocal.com.br/static/js/widget_loader.js`
- **Banco:** MySQL `u693215843_lab` em `srv1147.hstgr.io:3306`
- **Git:** não — deploy manual copiando do app_python
- **Nginx config:** `/etc/nginx/conf.d/metron.conf`

---

## Resumo — Qual Metron cada ambiente usa

| Ambiente Gocal       | Widget URL                                                       | Metron       | Banco               |
|----------------------|------------------------------------------------------------------|--------------|---------------------|
| gocal.com.br         | `https://metron.gocal.com.br/static/js/widget_loader.js`        | app_python4  | u693215843_lab      |
| gocal (teste/site)   | `https://metron.gocal.site/static/js/widget_loader.js`          | app_python   | u693215843_teste    |
| Demo (gocal.store)   | `https://metron2.gocal.store/static/js/widget_loader.js`        | app_python3  | u693215843_demo     |
| Homologação          | `http://46.202.148.205:5002/static/js/widget_loader.js`         | app_python2  | u693215843_teste    |

---

## Nginx — Sites configurados

| Domínio               | Proxy para | SSL |
|-----------------------|------------|-----|
| metron.gocal.site     | :5001      | sim |
| metron2.gocal.store   | :5003      | sim |

Configurações em `/etc/nginx/sites-enabled/`.

---

## Deploy rápido

### app_python (produção)
```bash
ssh root@46.202.148.205 "cd /root/app_python && git pull origin main && systemctl restart metron.service && curl -s http://localhost:5001/health"
```

### app_python2 (homologação) — sem git, copia do app_python
```bash
ssh root@46.202.148.205 "cd /root/app_python && git pull origin main && cp app_openai.py /root/app_python2/app_openai.py && cp static/js/gocal_chat.js /root/app_python2/static/js/gocal_chat.js && systemctl restart metron2.service && curl -s http://localhost:5002/health"
```

---

## Comandos úteis

```bash
# Status dos serviços
systemctl status metron.service
systemctl status metron2.service
systemctl status metron3.service

# Logs em tempo real
journalctl -u metron.service -f

# Verificar saúde
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health
```
