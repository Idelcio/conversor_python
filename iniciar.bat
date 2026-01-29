@echo off
echo ============================================================
echo Inicializando Extrator de Certificados
echo ============================================================
echo.

REM Cria venv se não existir
if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
    echo.
)

REM Ativa o venv
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Instala dependências
echo.
echo Instalando dependências...
pip install -r requirements.txt

REM Inicia o servidor
echo.
echo ============================================================
echo Iniciando servidor...
echo ============================================================
echo.
python app_openai.py
