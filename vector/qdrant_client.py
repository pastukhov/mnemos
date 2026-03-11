from qdrant_client import QdrantClient
from qdrant_client.http import models

from core.logging import get_logger

logger = get_logger(__name__)


class MnemosQdrantClient:
  def __init__(self, *, url: str, vector_size: int, timeout_seconds: float) -> None:
    self.client = QdrantClient(
      url=url,
      timeout=timeout_seconds,
      check_compatibility=False,
    )
    self.vector_size = vector_size
    self._known_collections: set[str] = set()

  def ping(self) -> None:
    self.client.get_collections()

  def has_collection(self, collection_name: str) -> bool:
    if collection_name in self._known_collections:
      return True
    try:
      exists = self.client.collection_exists(collection_name)
    except AttributeError:
      existing = {item.name for item in self.client.get_collections().collections}
      self._known_collections.update(existing)
      return collection_name in existing
    if exists:
      self._known_collections.add(collection_name)
    return exists

  def ensure_collection(self, collection_name: str) -> None:
    if self.has_collection(collection_name):
      return
    self.client.create_collection(
      collection_name=collection_name,
      vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE),
    )
    self._known_collections.add(collection_name)
    logger.info("qdrant collection ensured", extra={"event": "qdrant_collection_created"})

  def upsert_item(
    self,
    *,
    collection_name: str,
    item_id: str,
    vector: list[float],
    payload: dict[str, str],
  ) -> None:
    self.client.upsert(
      collection_name=collection_name,
      points=[
        models.PointStruct(
          id=item_id,
          vector=vector,
          payload=payload,
        )
      ],
    )

  def query_items(
    self,
    *,
    collection_name: str,
    vector: list[float],
    limit: int,
  ) -> list[dict[str, str]]:
    if not self.has_collection(collection_name):
      return []
    response = self.client.query_points(
      collection_name=collection_name,
      query=vector,
      limit=limit,
      with_payload=True,
      with_vectors=False,
    )
    points = response.points if hasattr(response, "points") else response
    return [point.payload for point in points]
