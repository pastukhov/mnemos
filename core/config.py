from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_DOMAINS = ("self", "project", "operational", "interaction")
ALLOWED_KINDS = ("raw", "fact", "reflection", "summary", "note", "decision", "task", "tension")

DOMAIN_COLLECTIONS = {
  "self": "mnemos_self",
  "project": "mnemos_project",
  "operational": "mnemos_operational",
  "interaction": "mnemos_interaction",
}


class Settings(BaseSettings):
  model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

  mnemos_env: str = Field(default="development", validation_alias="MNEMOS_ENV")
  mnemos_host: str = Field(default="0.0.0.0", validation_alias="MNEMOS_HOST")
  mnemos_port: int = Field(default=8000, validation_alias="MNEMOS_PORT")
  mnemos_log_level: str = Field(default="INFO", validation_alias="MNEMOS_LOG_LEVEL")

  postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
  postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
  postgres_db: str = Field(default="mnemos", validation_alias="POSTGRES_DB")
  postgres_user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
  postgres_password: str = Field(default="postgres", validation_alias="POSTGRES_PASSWORD")
  database_url: str | None = Field(
    default=None,
    validation_alias=AliasChoices("DATABASE_URL"),
  )

  qdrant_url: str = Field(default="http://localhost:6333", validation_alias="QDRANT_URL")
  qdrant_vector_size: int = Field(default=64, validation_alias="QDRANT_VECTOR_SIZE")
  qdrant_timeout_seconds: float = Field(default=5.0, validation_alias="QDRANT_TIMEOUT_SECONDS")

  embedding_provider: str = Field(default="mock", validation_alias="EMBEDDING_PROVIDER")
  embedding_model: str = Field(default="mock-embedding", validation_alias="EMBEDDING_MODEL")
  embedding_base_url: str | None = Field(
    default=None,
    validation_alias="EMBEDDING_BASE_URL",
  )
  embedding_api_key: str | None = Field(default=None, validation_alias="EMBEDDING_API_KEY")
  embedding_timeout_seconds: float = Field(
    default=10.0,
    validation_alias="EMBEDDING_TIMEOUT_SECONDS",
  )

  @computed_field
  @property
  def postgres_dsn(self) -> str:
    if self.database_url:
      return self.database_url
    return (
      f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
      f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    )

  def collection_for_domain(self, domain: str) -> str:
    return DOMAIN_COLLECTIONS[domain]


@lru_cache
def get_settings() -> Settings:
  return Settings()
