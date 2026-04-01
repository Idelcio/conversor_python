# Workflow: Deploy para o VPS

**VPS:** 46.202.148.205
**Diretório de produção:** `/root/app_python/`
**Porta:** 5001 (gunicorn)
**Branch:** main

---

## Pré-requisitos

- Código commitado e com push feito no GitHub (`git push origin main`)
- Acesso SSH ao VPS configurado

---

## Passo a passo do deploy

### 1. Fazer push local para o GitHub
```bash
cd c:/Users/Forest/Projetos/Labster/Python/leitor_conversor
git push origin main
```

### 2. Conectar no VPS
```bash
ssh root@46.202.148.205
```

### 3. Fazer pull no VPS
```bash
cd /root/app_python
git pull origin main
```

### 4. Restaurar o .env (se o pull sobrescrever)
O `.env` do VPS **não está no git** (está no .gitignore). Se for a primeira vez:
```bash
# .env já existe em /root/.env_backup_metron como backup
cp /root/.env_backup_metron /root/app_python/.env
```

### 5. Reiniciar o serviço
O gunicorn é gerenciado pelo **systemd** (service `metron.service`). NUNCA matar manualmente — ele reinicia sozinho e causa conflito de porta.

```bash
systemctl restart metron.service
```

Verificar status:
```bash
systemctl status metron.service
```

### 6. Verificar se subiu
```bash
curl http://localhost:5001/health
# Resposta esperada: {"extractor":"ok","mode":"openai_vision","status":"ok"}
```

---

## Deploy rápido (após git já configurado)

```bash
ssh root@46.202.148.205 "cd /root/app_python && git pull origin main && systemctl restart metron.service"
```

---

## Observações importantes

- O `.env` do VPS tem credenciais de **produção** (banco remoto `u693215843_teste`)
- O `.env` local tem credenciais do banco **local** (`laboratorios`)
- **Nunca sobrescrever o `.env` do VPS** com o local
- O backup do `.env` fica em `/root/.env_backup_metron`
- Há dois diretórios: `app_python/` (porta 5001) e `app_python2/` (porta 5002) — produção é o 5001

---

## Deploy para app_python2 e app_python3 (sem git)

`app_python2` e `app_python3` **não têm git**. O deploy copia todos os arquivos relevantes do `app_python` após o pull.

**Arquivos que devem ser copiados em todo deploy:**
- `app_openai.py`
- `static/js/gocal_chat.js`
- `static/js/widget_loader.js`
- `openai_extractor/extractor.py`
- `openai_extractor/prompts.py`
- `templates/gocal_chat.html`

### app_python2 (homologação — porta 5002)
```bash
ssh root@46.202.148.205 "cd /root/app_python && git pull origin main && cp app_openai.py /root/app_python2/app_openai.py && cp static/js/gocal_chat.js /root/app_python2/static/js/gocal_chat.js && cp openai_extractor/extractor.py /root/app_python2/openai_extractor/extractor.py && cp openai_extractor/prompts.py /root/app_python2/openai_extractor/prompts.py && cp static/js/widget_loader.js /root/app_python2/static/js/widget_loader.js && cp templates/gocal_chat.html /root/app_python2/templates/gocal_chat.html && systemctl restart metron2.service && curl -s http://localhost:5002/health"
```

### app_python3 (demo/store — porta 5003)
```bash
ssh root@46.202.148.205 "cd /root/app_python && git pull origin main && cp app_openai.py /root/app_python3/app_openai.py && cp static/js/gocal_chat.js /root/app_python3/static/js/gocal_chat.js && cp openai_extractor/extractor.py /root/app_python3/openai_extractor/extractor.py && cp openai_extractor/prompts.py /root/app_python3/openai_extractor/prompts.py && cp static/js/widget_loader.js /root/app_python3/static/js/widget_loader.js && cp templates/gocal_chat.html /root/app_python3/templates/gocal_chat.html && systemctl restart metron3.service && curl -s http://localhost:5003/health"
```

### app_python4 (gocal.com.br — porta 5004)
```bash
ssh root@46.202.148.205 "cd /root/app_python && git pull origin main && cp app_openai.py /root/app_python4/app_openai.py && cp static/js/gocal_chat.js /root/app_python4/static/js/gocal_chat.js && cp openai_extractor/extractor.py /root/app_python4/openai_extractor/extractor.py && cp openai_extractor/prompts.py /root/app_python4/openai_extractor/prompts.py && cp static/js/widget_loader.js /root/app_python4/static/js/widget_loader.js && cp templates/gocal_chat.html /root/app_python4/templates/gocal_chat.html && systemctl restart metron4.service && curl -s http://localhost:5004/health"
```
> **Atenção:** nunca sobrescrever o `.env` do app_python4 — banco é `u693215843_lab`, diferente dos outros.
