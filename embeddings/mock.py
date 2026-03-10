import hashlib
import math
import re

from embeddings.base import Embedder


class MockEmbedder(Embedder):
  def __init__(self, vector_size: int = 8) -> None:
    self.vector_size = vector_size

  def embed_text(self, text: str) -> list[float]:
    vector = [0.0] * self.vector_size
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not tokens:
      return vector
    for token in tokens:
      digest = hashlib.sha256(token.encode("utf-8")).digest()
      bucket = int.from_bytes(digest[:4], byteorder="big", signed=False) % self.vector_size
      sign = 1.0 if digest[4] % 2 == 0 else -1.0
      vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
      return vector
    return [value / norm for value in vector]
