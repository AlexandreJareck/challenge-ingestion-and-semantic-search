import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# 📌 Configurações
PDF_PATH = os.getenv("PDF_PATH", "./document.pdf")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/semantic_search")
COLLECTION_NAME = os.getenv("PG_VECTOR_COLLECTION_NAME", "documents")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 👇 usa o modelo certo
EMBEDDING_MODEL = os.getenv(
    "GOOGLE_EMBEDDING_MODEL",
    "models/gemini-embedding-001",
)

# 👇 controle de rate limit
BATCH_SIZE = int(os.getenv("INGEST_BATCH_SIZE", 5))
BATCH_SLEEP = float(os.getenv("INGEST_BATCH_SLEEP", 4))

def ingest_pdf():
    pdf_file = Path(PDF_PATH)

    if not pdf_file.exists():
        print(f"❌ Arquivo não encontrado: {PDF_PATH}")
        return

    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY não encontrada no .env")
        return

    print(f"\n📄 Iniciando ingestão: {pdf_file.name}")

    try:
        # 1. Carregar PDF
        print("   📥 Carregando PDF...")
        loader = PyPDFLoader(str(pdf_file))
        documents = loader.load()
        print(f"   ✅ {len(documents)} página(s) carregada(s)")

        # 2. Dividir em chunks (otimizado)
        print("   ✂️  Dividindo em chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,       
            chunk_overlap=150,    
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.split_documents(documents)
        print(f"   ✅ {len(chunks)} chunks gerados")

        # 3. Embeddings
        print(f"   🧠 Modelo de embedding: {EMBEDDING_MODEL}")
        embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GOOGLE_API_KEY,
        )

        # 4. Criar vector store (UMA vez só)
        print("   🗄️  Conectando ao PGVector...")
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=COLLECTION_NAME,
            connection=DATABASE_URL,
            use_jsonb=True,
        )

        # 5. Inserção em batches
        print(f"   🚀 Salvando em lotes de {BATCH_SIZE}...")

        total = len(chunks)

        for i in range(0, total, BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]

            try:
                vector_store.add_documents(batch)

                saved = min(i + BATCH_SIZE, total)
                print(f"   ✅ {saved}/{total} chunks salvos")

                # evita estourar TPM
                if saved < total:
                    time.sleep(BATCH_SLEEP)

            except Exception as batch_error:
                print(f"⚠️ Erro no batch {i}: {batch_error}")
                print("⏳ Aguardando 10s antes de continuar...")
                time.sleep(10)

        print(f"\n🎉 Ingestão concluída! {total} chunks armazenados.")
        print(f"📦 Coleção: {COLLECTION_NAME}")

    except Exception as e:
        print(f"\n❌ Erro geral ao ingerir PDF: {e}")
        raise


if __name__ == "__main__":
    ingest_pdf()