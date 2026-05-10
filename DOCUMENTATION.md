# RAG-PDF — Documentação Técnica

Pipeline de **Retrieval-Augmented Generation (RAG)** sobre PDFs, utilizando **LangChain**, **pgVector** (PostgreSQL) e **Google Gemini** para embeddings e geração de respostas.

---

## Sumário

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Estrutura de Arquivos](#estrutura-de-arquivos)
4. [Pré-requisitos](#pré-requisitos)
5. [Configuração](#configuração)
6. [Docker Compose](#docker-compose)
7. [init-setup.sh](#setupsh)
8. [Código Python](#código-python)
   - [ingest.py](#ingestpy)
   - [search.py](#searchpy)
   - [chat.py](#chatpy)
9. [pyproject.toml](#pyprojecttoml)
10. [Como Rodar](#como-rodar)
    - [Localmente](#localmente)
    - [Via Docker](#via-docker)
11. [Problemas Conhecidos](#problemas-conhecidos)

---

## Visão Geral

O projeto implementa um chatbot que responde perguntas com base exclusivamente no conteúdo de um PDF fornecido. O fluxo é dividido em duas etapas:

**Ingestão** — o PDF é carregado, dividido em chunks, transformado em vetores (embeddings) e armazenado no PostgreSQL com a extensão pgVector.

**Consulta** — a pergunta do usuário é vetorizada, os chunks mais relevantes são recuperados por similaridade cosine, um prompt é montado com esse contexto e enviado ao Gemini, que retorna a resposta.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                     INGESTÃO                            │
│                                                         │
│  PDF → PyPDFLoader → RecursiveCharacterTextSplitter     │
│     → GoogleGenerativeAIEmbeddings → PGVector (pg)      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                     CONSULTA (RAG)                      │
│                                                         │
│  Pergunta → embed → similarity_search (top-10)          │
│          → PromptTemplate → Gemini → Resposta           │
└─────────────────────────────────────────────────────────┘
```

---

## Estrutura de Arquivos

```
rag-pdf/
├── data/
│   └── document.pdf          # PDF a ser ingerido
├── src/
│   ├── ingest.py             # Pipeline de ingestão
│   ├── search.py             # Pipeline RAG (busca + LLM)
│   └── chat.py               # Chat interativo no terminal
├── docker-compose.yml        # PostgreSQL + pgVector + init_db
├── pyproject.toml            # Dependências do projeto (uv)
├── init-setup.sh                  # Script de configuração do ambiente
├── .env                      # Variáveis de ambiente (não commitar)
└── .env.example              # Modelo do .env
```

---

## Pré-requisitos

- Python 3.11+
- [uv](https://astral.sh/uv) — gerenciador de pacotes
- Docker + Docker Compose
- Chave de API do Google Gemini ([Google AI Studio](https://aistudio.google.com))

### Instalação do uv

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

## Configuração

Copie o `.env.example` e preencha com suas credenciais:

```bash
cp .env.example .env
```

Conteúdo do `.env`:

```env
# === Google AI ===
GOOGLE_API_KEY=AIza...
GOOGLE_EMBEDDING_MODEL=models/gemini-embedding-2
GEMINI_CHAT_MODEL=gemini-2.5-flash

# === PostgreSQL ===
# Usar postgresql+psycopg para evitar problemas de encoding no Windows
# Ajustar a porta se houver conflito com PostgreSQL local (ex: 5433)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/semantic_search

# === LangChain PGVector ===
PG_VECTOR_COLLECTION_NAME=documents

# === Ingestão ===
PDF_PATH=./document.pdf

# === Rate limit ===
INGEST_BATCH_SIZE=5
INGEST_BATCH_SLEEP=4.0
```

> **Nota sobre portas no Windows:** se houver um PostgreSQL local instalado na máquina, ele ocupa a porta 5432 e conflita com o Docker. Use a porta `5433` no `docker-compose.yml` e no `DATABASE_URL`.

> **Nota sobre modelos de embedding:** os modelos `models/embedding-001` e `models/text-embedding-004` foram descontinuados ou não estão disponíveis em todas as chaves. Use `models/gemini-embedding-2` ou `models/gemini-embedding-001`.

---

## Docker Compose

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: postgres_rag
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: semantic_search
    ports:
      - "5433:5432"   # 5433 evita conflito com PostgreSQL local no Windows
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d semantic_search"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  init_db:
    image: pgvector/pgvector:pg17
    depends_on:
      postgres:
        condition: service_healthy
    entrypoint: ["/bin/sh", "-c"]
    command: >
      sh -c "
      echo 'Waiting for PostgreSQL...';
      until pg_isready -h postgres -U postgres; do
        sleep 2;
      done;

      echo 'Creating vector extension...';
      PGPASSWORD=postgres psql postgresql://postgres:postgres@postgres:5432/semantic_search \
      -v ON_ERROR_STOP=1 \
      -c 'CREATE EXTENSION IF NOT EXISTS vector;';

      echo 'Init finished!';
      "
    restart: "no"

volumes:
  postgres_data:
```

**Serviços:**

- `postgres` — PostgreSQL 17 com a extensão pgVector pré-instalada. O healthcheck garante que o banco está pronto antes do `init_db` rodar.
- `init_db` — container temporário que cria a extensão `vector` no banco. Roda uma única vez e encerra. As tabelas de embeddings são criadas automaticamente pelo LangChain no primeiro `PGVector.from_documents()`.

---

## init-setup.sh

Script de preparação do ambiente local. Realiza as seguintes verificações e ações:

1. Verifica e instala o `uv` se necessário
2. Verifica se o Docker está instalado e rodando
3. Detecta o comando correto do Docker Compose (`docker-compose` ou `docker compose`)
4. Cria o `.env` a partir do `.env.example` se não existir
5. Valida se a `GOOGLE_API_KEY` está configurada
6. Cria a pasta `data/`
7. Cria o ambiente virtual `.venv`
8. Instala as dependências com `uv sync`

```bash
chmod +x init-setup.sh && ./init-setup.sh
```

---

## Código Python

### ingest.py

Responsável pelo pipeline completo de ingestão do PDF.

**Fluxo:**
1. Lê o PDF com `PyPDFLoader` (LangChain Community)
2. Divide o texto em chunks com `RecursiveCharacterTextSplitter` — 1000 caracteres com overlap de 150
3. Configura os embeddings com `GoogleGenerativeAIEmbeddings`
4. Conecta ao `PGVector` e insere os chunks em lotes para respeitar o rate limit da API

**Controle de rate limit:**

A API do Gemini tem limite de tokens por minuto (TPM). Para evitar erros, a inserção é feita em lotes controlados pelas variáveis:

```env
INGEST_BATCH_SIZE=5    # chunks por lote
INGEST_BATCH_SLEEP=4.0 # segundos de pausa entre lotes
```

Se um lote falhar, o script aguarda 10 segundos e continua o próximo.

**Variáveis utilizadas:**

| Variável | Descrição |
|---|---|
| `PDF_PATH` | Caminho para o arquivo PDF |
| `DATABASE_URL` | Connection string do PostgreSQL |
| `PG_VECTOR_COLLECTION_NAME` | Nome da coleção no pgVector |
| `GOOGLE_API_KEY` | Chave da API do Google |
| `GOOGLE_EMBEDDING_MODEL` | Modelo de embedding |
| `INGEST_BATCH_SIZE` | Tamanho do lote de inserção |
| `INGEST_BATCH_SLEEP` | Pausa entre lotes em segundos |

```bash
uv run python src/ingest.py
```

---

### search.py

Contém a lógica do pipeline RAG e o prompt template.

**Fluxo da `search_prompt()`:**
1. Configura embeddings e conecta ao vector store
2. Configura o LLM (`ChatGoogleGenerativeAI`) com `temperature=0` para respostas determinísticas
3. Monta a chain: `PromptTemplate | LLM | StrOutputParser`
4. Retorna a função `query_chain` como callable

**Comportamento da função:**

```python
# Retorna a função callable (usado pelo chat.py)
chain = search_prompt()
resposta = chain("sua pergunta")

# Executa imediatamente (útil para testes)
resposta = search_prompt("sua pergunta")
```

**Prompt template:**

```
CONTEXTO:
{contexto}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.
```

O prompt é projetado para que o modelo nunca use conhecimento externo — apenas o contexto recuperado do banco vetorial.

**Busca vetorial:**

```python
results = vectorstore.similarity_search_with_score(user_question, k=10)
```

Recupera os 10 chunks mais similares usando distância cosine. O contexto é montado concatenando o conteúdo de todos os chunks recuperados.

---

### chat.py

Interface de chat interativo no terminal.

**Fluxo:**
1. Chama `search_prompt()` sem argumento para inicializar a chain
2. Se a inicialização falhar (ex: `GOOGLE_API_KEY` ausente), encerra com mensagem de erro
3. Entra no loop interativo: lê a pergunta, chama `chain(question)` e exibe a resposta
4. Encerra com `sair`, `exit`, `quit`, `q` ou `Ctrl+C`

```bash
uv run python src/chat.py
```

---

## pyproject.toml

```toml
[project]
name = "rag-pdf"
version = "0.1.0"
description = "RAG pipeline com PDF, pgVector e Gemini"
requires-python = ">=3.11"
dependencies = [
    "langchain>=0.3.0",
    "langchain-community>=0.3.0",
    "langchain-google-genai>=1.0.10,<2.0.0",
    "langchain-postgres>=0.0.12",
    "langchain-text-splitters>=0.3.0",
    "pypdf>=4.2.0",
    "psycopg2-binary>=2.9.9",
    "psycopg[binary]>=3.0.0",
    "python-dotenv>=1.0.1",
    "typer>=0.12.3",
    "rich>=13.7.1",
]
```

> **Atenção:** fixar `langchain-google-genai<2.0.0` é necessário porque a versão 2.x usa a API `v1beta` do Google, que não suporta todos os modelos de embedding disponíveis na versão 1.x.

---

## Como Rodar

### Localmente

```bash
# 1. Preparar o ambiente
chmod +x init-setup.sh && ./init-setup.sh

# 2. Editar o .env com suas credenciais

# 3. Subir o banco
docker compose up -d

# 4. Verificar se o init_db terminou
docker compose logs init_db
# Esperado: "Init finished!" no final

# 5. Colocar o PDF na pasta data/ ou ajustar PDF_PATH no .env

# 6. Ingerir o PDF
uv run python src/ingest.py

# 7. Iniciar o chat
uv run python src/chat.py
```

### Via Docker

```bash
# 1. Criar o Dockerfile na raiz do projeto
# (ver seção Dockerfile abaixo)

# 2. Ajustar DATABASE_URL no .env para usar o nome do serviço:
# DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/semantic_search

# 3. Build e subir
docker compose up --build -d

# 4. Ingerir o PDF
docker compose run --rm app uv run python src/ingest.py

# 5. Chat interativo
docker compose run --rm -it app uv run python src/chat.py
```

**Dockerfile:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv sync --no-dev

COPY src/ ./src/
COPY data/ ./data/

ENV PYTHONPATH=/app/src
CMD ["uv", "run", "python", "src/chat.py"]
```

**Comandos úteis:**

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

## Problemas Conhecidos

### `models/embedding-001` ou `text-embedding-004` retorna 404
Os modelos foram descontinuados ou não estão disponíveis em todas as chaves. Use `models/gemini-embedding-2` ou `models/gemini-embedding-001`.

### `UnicodeDecodeError: utf-8 codec can't decode` no Windows
O `psycopg2` tem problemas com encoding no Windows. Solução: usar o driver `psycopg3` trocando o prefixo da connection string:
```
postgresql+psycopg://...
```

### Conflito de porta 5432 no Windows
Se houver um PostgreSQL local instalado, ele ocupa a porta 5432. Solução: mapear o Docker para a porta 5433 no `docker-compose.yml` e atualizar o `DATABASE_URL`.

### Rate limit da API do Gemini (TPM)
A API tem limite de tokens por minuto. Reduzir o `INGEST_BATCH_SIZE` e aumentar o `INGEST_BATCH_SLEEP` no `.env` resolve.

### `ModuleNotFoundError: No module named 'langchain.prompts'`
O import foi movido nas versões recentes. Usar:
```python
from langchain_core.prompts import PromptTemplate
```
