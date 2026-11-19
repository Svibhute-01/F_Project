from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import GOOGLE_API_KEY, EMBEDDING_MODEL


def get_embeddings():
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is required for Google embeddings/RAG, even when Groq is used for code generation.")
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )