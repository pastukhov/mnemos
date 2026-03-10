import httpx

from embeddings.base import Embedder


class OpenAICompatibleEmbedder(Embedder):
  def __init__(
    self,
    *,
    model: str,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
  ) -> None:
    self.model = model
    self.base_url = base_url.rstrip("/")
    self.api_key = api_key
    self.timeout_seconds = timeout_seconds

  def embed_text(self, text: str) -> list[float]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if self.api_key:
      headers["Authorization"] = f"Bearer {self.api_key}"
    response = httpx.post(
      f"{self.base_url}/embeddings",
      json={"model": self.model, "input": text},
      headers=headers,
      timeout=self.timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["data"][0]["embedding"]
