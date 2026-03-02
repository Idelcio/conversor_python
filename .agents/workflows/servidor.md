# Workflow: Servidor Metron (Flask)

## Ligar o servidor

```bash
cd c:/Users/Forest/Projetos/Labster/Python/leitor_conversor
python app_openai.py
```

- Roda na porta **5001**
- Interface principal: http://localhost:5001
- Modo debug ativo — recarrega automaticamente ao editar arquivos

## Verificar se está ligado

**Via curl:**
```bash
curl http://localhost:5001/health
```
Resposta esperada:
```json
{"status": "ok", "mode": "openai_vision", "extractor": "ok"}
```

**Via logs (background task):**
```bash
tail -20 C:/Users/Forest/AppData/Local/Temp/claude/.../tasks/<task_id>.output
```
Procurar por: `Running on http://127.0.0.1:5001`

**Via navegador:**
Acessar http://localhost:5001 — deve abrir o chat do Metron.

## Parar o servidor

Se rodando em foreground: `Ctrl+C`

Se rodando em background pelo Claude Code: usar o `TaskStop` com o task_id.

## Dependências necessárias

- Python com Flask, flask-cors, mysql-connector-python, PyMuPDF (fitz), openai, python-dotenv
- MySQL rodando na porta 3306 com banco `laboratorios`
- `.env` com `OPENAI_API_KEY` configurada

## Observações

- O servidor usa o banco `laboratorios` (mesmo banco do Gocal/Laravel)
- PDFs são servidos pela rota `/certificado-pdf/<calibracao_id>` direto do banco
- Tokens acumulados da sessão visíveis no header do chat
