from core.config import Settings
from embeddings.base import Embedder
from embeddings.mock import MockEmbedder
from embeddings.openai_compatible import OpenAICompatibleEmbedder


def build_embedder(settings: Settings) -> Embedder:
  if settings.embedding_provider == "mock":
    return MockEmbedder(vector_size=settings.qdrant_vector_size)
  if not settings.embedding_base_url:
    raise ValueError("EMBEDDING_BASE_URL is required for non-mock embedding providers")
  return OpenAICompatibleEmbedder(
    model=settings.embedding_model,
    base_url=settings.embedding_base_url,
    api_key=settings.embedding_api_key,
    timeout_seconds=settings.embedding_timeout_seconds,
  )
