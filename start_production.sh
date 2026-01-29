#!/bin/bash

# Script de inicialização para produção
# Uso: ./start_production.sh

echo "🚀 Iniciando Metron Chat em modo produção..."

# Verifica se o arquivo .env existe
if [ ! -f .env ]; then
    echo "❌ Erro: Arquivo .env não encontrado!"
    echo "📝 Copie o arquivo .env.example e configure suas variáveis:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Verifica se as dependências estão instaladas
echo "📦 Verificando dependências..."
pip install -r requirements.txt

# Inicia o servidor com Gunicorn
echo "✅ Iniciando servidor Gunicorn..."
echo "📍 Servidor rodando em: http://0.0.0.0:5000"
echo "⏹️  Pressione Ctrl+C para parar"

gunicorn -w 4 -b 0.0.0.0:5000 --timeout 300 app_openai:app
