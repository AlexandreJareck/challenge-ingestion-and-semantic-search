#!/usr/bin/env bash

set -e

echo "🔍 Verificando dependências..."

# ---- UV ----
if ! command -v uv &> /dev/null; then
    echo "⚠️ uv não encontrado. Instalando..."
    curl -LsSf https://astral.sh/uv/install.sh | sh || {
        echo "❌ Falha ao instalar uv"
        exit 1
    }
    export PATH="$HOME/.local/bin:$PATH"
    echo "✅ uv instalado"
else
    echo "✅ uv encontrado: $(uv --version)"
fi

# ---- Docker ----
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado"
    echo "👉 https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker está instalado mas não está rodando"
    exit 1
fi

echo "✅ Docker OK"

# ---- Docker Compose ----
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ Docker Compose não encontrado"
    exit 1
fi

echo "✅ Docker Compose OK ($COMPOSE_CMD)"

# ---- ENV ----
if [ ! -f .env ]; then
    echo "⚠️ .env não encontrado"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env criado a partir do .env.example"
        echo "⚠️ Edite o .env antes de continuar"
    else
        echo "❌ .env.example não encontrado"
        exit 1
    fi
else
    echo "✅ .env encontrado"
fi

# Validação básica
if ! grep -q "OPENAI_API_KEY=" .env; then
    echo "⚠️ OPENAI_API_KEY não configurada"
fi

# ---- VENV ----
if [ ! -d .venv ]; then
    echo "📦 Criando ambiente virtual..."
    uv venv
    echo "✅ Ambiente virtual criado"
else
    echo "✅ Ambiente virtual já existe"
fi

# ---- DEPENDÊNCIAS ----
echo "📦 Sincronizando dependências..."
uv sync
echo "✅ Dependências sincronizadas"

echo ""
echo "🎉 Ambiente pronto!"
echo ""
echo "🚀 Próximos passos:"
echo "1. Configure o .env"
echo "2. Suba o banco:"
echo "   $COMPOSE_CMD up -d"
echo ""
echo "3. Execute:"
echo "   Ingestão: uv run python src/ingest.py ingest"
echo "   Busca:    uv run python src/search.py search \"texto\""
echo "   Chat:     uv run python src/chat.py chat"