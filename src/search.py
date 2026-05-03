import os

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/semantic_search")
COLLECTION_NAME = os.getenv("PG_VECTOR_COLLECTION_NAME", "documents")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
EMBEDDING_MODEL = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
LLM_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")

PROMPT_TEMPLATE = """
CONTEXTO:
{contexto}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{pergunta}

RESPONDA A "PERGUNTA DO USUÁRIO"
"""


def search_prompt(question=None):
    """
    Configura a chain RAG e retorna um callable.

    Args:
        question: Se fornecido, executa imediatamente (útil para testes).

    Returns:
        - callable query_chain(str) -> str  (quando question=None)
        - str com a resposta                (quando question é fornecida)
        - None em caso de erro de configuração
    """
    if not GOOGLE_API_KEY:
        print("❌ ERRO: GOOGLE_API_KEY não encontrada no arquivo .env")
        return None

    try:
        # Embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GOOGLE_API_KEY,  # type: ignore[arg-type]
        )

        # Vector store
        vectorstore = PGVector(
            embeddings=embeddings,
            collection_name=COLLECTION_NAME,
            connection=DATABASE_URL,
            use_jsonb=True,
        )

        # LLM
        llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GOOGLE_API_KEY,  # type: ignore[arg-type]
            temperature=0,
        )

        # Chain: prompt | llm | parser
        prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["contexto", "pergunta"],
        )
        chain = prompt | llm | StrOutputParser()

        def query_chain(user_question: str) -> str:
            """Executa busca vetorial + LLM e retorna a resposta."""
            results = vectorstore.similarity_search_with_score(user_question, k=10)

            if not results:
                return "Não tenho informações necessárias para responder sua pergunta."

            contexto = "\n\n".join([doc.page_content for doc, _score in results])
            return chain.invoke({"contexto": contexto, "pergunta": user_question})

        # Execução imediata (modo teste)
        if question:
            return query_chain(question)

        return query_chain

    except Exception as e:
        print(f"❌ ERRO ao configurar busca: {e}")
        import traceback
        traceback.print_exc()
        return None
