# Desafio MBA Engenharia de Software com IA - Full Cycle

# RAG-PDF 🔍

Pipeline de **Retrieval-Augmented Generation (RAG)** sobre PDFs usando **LangChain**, **pgVector** (PostgreSQL) e **Google Gemini** para embeddings e geração de respostas.

---

## Como funciona

```
INGESTÃO
PDF → PyPDFLoader → RecursiveCharacterTextSplitter → GoogleGenerativeAIEmbeddings → PGVector

CONSULTA
Pergunta → embed → similarity_search (top-10) → PromptTemplate → Gemini → Resposta
```

---

## Pré-requisitos

- Python 3.11+
- [uv](https://astral.sh/uv) — gerenciador de pacotes
- Docker + Docker Compose
- Chave de API do Google Gemini ([Google AI Studio](https://aistudio.google.com))

### Instalando o uv

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # ou ~/.zshrc
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Instalação e execução

### 1. Preparar o ambiente

**macOS / Linux:**
```bash
chmod +x init-setup.sh && ./init-setup.sh
```

**Windows (Git Bash ou WSL):**
```bash
bash init-setup.sh
```

**Windows (PowerShell) — alternativa manual caso não tenha Git Bash/WSL:**
```powershell
# 1. Instalar dependências com uv
uv sync

# 2. Criar a pasta data
mkdir -p data
```

### 2. Configurar credenciais

**macOS / Linux:**
```bash
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

Edite o `.env` e preencha suas credenciais:

```env
GOOGLE_API_KEY=AIza...
GOOGLE_EMBEDDING_MODEL=models/gemini-embedding-2
GEMINI_CHAT_MODEL=gemini-2.5-flash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/semantic_search
PG_VECTOR_COLLECTION_NAME=documents
PDF_PATH=./document.pdf
INGEST_BATCH_SIZE=5
INGEST_BATCH_SLEEP=4.0
```

> **Windows:** use sempre o driver `psycopg3` no `DATABASE_URL` (prefixo `postgresql+psycopg://`) para evitar erros de encoding. Se tiver um PostgreSQL local instalado, ele ocupa a porta `5432` — use a porta `5433` no `DATABASE_URL` e no `docker-compose.yml`.

### 3. Subir o banco de dados

```bash
docker compose up -d
```

### 4. Verificar a inicialização do banco

```bash
docker compose logs init_db
# Aguarde "Init finished!" no final
```

### 5. Adicionar o PDF

Coloque o arquivo em `data/document.pdf` ou ajuste `PDF_PATH` no `.env`.

### 6. Ingerir o PDF

```bash
uv run python src/ingest.py
```

### 7. Iniciar o chat

```bash
uv run python src/chat.py
```

> Para encerrar o chat, digite `sair`, `exit`, `quit`, `q` ou pressione `Ctrl+C`.

---

## Estrutura do projeto

```
rag-pdf/
├── data/
│   └── document.pdf
├── src/
│   ├── ingest.py       # Pipeline de ingestão
│   ├── search.py       # Pipeline RAG (busca + LLM)
│   └── chat.py         # Chat interativo no terminal
├── docker-compose.yml
├── pyproject.toml
├── init-setup.sh
├── .env
└── .env.example
```

---

## Executando via Docker

```bash
# Ajustar DATABASE_URL no .env para usar o nome do serviço:
# DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/semantic_search

# Build e subir
docker compose up --build -d

# Ingerir o PDF
docker compose run --rm app uv run python src/ingest.py

# Chat interativo
docker compose run --rm -it app uv run python src/chat.py
```

---

## Comandos úteis

```bash
# Ver logs
docker compose logs -f

# Parar os containers
docker compose down

# Parar e apagar o volume (reseta o banco)
docker compose down -v

# Reingerir após trocar o PDF
uv run python src/ingest.py
```

---

## Problemas conhecidos

| Problema | Solução |
|---|---|
| `models/embedding-001` retorna 404 | Use `models/gemini-embedding-2` ou `models/gemini-embedding-001` |
| `UnicodeDecodeError` no Windows | Use o driver `psycopg3` com prefixo `postgresql+psycopg://` |
| Conflito na porta 5432 no Windows | Mapeie o Docker para a porta `5433` no `docker-compose.yml` e atualize o `DATABASE_URL` |
| Rate limit da API do Gemini | Reduza `INGEST_BATCH_SIZE` e aumente `INGEST_BATCH_SLEEP` no `.env` |
| `ModuleNotFoundError: No module named 'langchain.prompts'` | Use `from langchain_core.prompts import PromptTemplate` |
