@echo off
REM Script de inicialização para produção (Windows)
REM Uso: start_production.bat

echo 🚀 Iniciando Metron Chat em modo produção...

REM Verifica se o arquivo .env existe
if not exist .env (
    echo ❌ Erro: Arquivo .env não encontrado!
    echo 📝 Copie o arquivo .env.example e configure suas variáveis:
    echo    copy .env.example .env
    echo    notepad .env
    exit /b 1
)

REM Verifica se as dependências estão instaladas
echo 📦 Instalando dependências...
pip install -r requirements.txt

REM Inicia o servidor com Gunicorn
echo ✅ Iniciando servidor Gunicorn...
echo 📍 Servidor rodando em: http://0.0.0.0:5000
echo ⏹️  Pressione Ctrl+C para parar

gunicorn -w 4 -b 0.0.0.0:5000 --timeout 300 app:app
