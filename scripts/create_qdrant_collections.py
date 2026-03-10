from core.config import DOMAIN_COLLECTIONS, get_settings
from vector.qdrant_client import MnemosQdrantClient


def main() -> None:
  settings = get_settings()
  client = MnemosQdrantClient(
    url=settings.qdrant_url,
    vector_size=settings.qdrant_vector_size,
    timeout_seconds=settings.qdrant_timeout_seconds,
  )
  for collection_name in DOMAIN_COLLECTIONS.values():
    client.ensure_collection(collection_name)


if __name__ == "__main__":
  main()
