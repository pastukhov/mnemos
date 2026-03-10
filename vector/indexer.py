from embeddings.base import Embedder
from vector.qdrant_client import MnemosQdrantClient


class MemoryIndexer:
  def __init__(self, qdrant: MnemosQdrantClient, embedder: Embedder) -> None:
    self.qdrant = qdrant
    self.embedder = embedder

  def build_vector(self, text: str) -> list[float]:
    return self.embedder.embed_text(text)
