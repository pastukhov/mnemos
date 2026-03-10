from abc import ABC, abstractmethod


class Embedder(ABC):
  @abstractmethod
  def embed_text(self, text: str) -> list[float]:
    raise NotImplementedError
