from core.config import Settings
from embeddings.base import Embedder
from embeddings.openai_compatible import OpenAICompatibleEmbedder


def build_embedder(settings: Settings) -> Embedder:
  if settings.embedding_provider != "openai_compatible":
    raise ValueError("EMBEDDING_PROVIDER must be 'openai_compatible'")
  if not settings.embedding_base_url:
    raise ValueError("EMBEDDING_BASE_URL is required for EMBEDDING_PROVIDER=openai_compatible")
  return OpenAICompatibleEmbedder(
    model=settings.embedding_model,
    base_url=settings.embedding_base_url,
    api_key=settings.embedding_api_key,
    timeout_seconds=settings.embedding_timeout_seconds,
  )
