from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_DOMAINS = ("self", "project", "operational", "interaction")
ALLOWED_KINDS = ("raw", "fact", "reflection", "summary", "note", "decision", "task", "tension")
CANDIDATE_STATUSES = ("pending", "accepted", "rejected", "superseded")
MEMORY_ITEM_STATUSES = ("accepted", "superseded")
ALLOWED_CANDIDATE_WRITE_MODES = ("create", "upsert")
CONFIDENCE_ALIASES = {
  "low": 0.35,
  "medium": 0.65,
  "high": 0.9,
}

MEMORY_STATEMENT_MIN_LENGTH = 1
MEMORY_CONFIDENCE_MIN = 0.0
MEMORY_CONFIDENCE_MAX = 1.0

QUERY_MIN_LENGTH = 1
QUERY_TOP_K_MIN = 1
QUERY_TOP_K_MAX = 50

CANDIDATE_STATEMENT_MIN_LENGTH = 10
CANDIDATE_STATEMENT_MAX_LENGTH = 500
NOTE_STATEMENT_MAX_LENGTH = 50_000
CANDIDATE_AGENT_ID_MAX_LENGTH = 64
SOURCE_EXCERPT_MAX_LENGTH = 2_000
REVIEW_SESSION_ID_MAX_LENGTH = 128
REVIEW_SESSION_LABEL_MAX_LENGTH = 200
EVIDENCE_REF_MAX_LENGTH = 200

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
  mnemos_timeout_seconds: float = Field(
    default=10.0,
    validation_alias="MNEMOS_TIMEOUT_SECONDS",
  )
  mcp_server_host: str = Field(default="0.0.0.0", validation_alias="MCP_SERVER_HOST")
  mcp_server_port: int = Field(default=9000, validation_alias="MCP_SERVER_PORT")
  mcp_server_transport: str = Field(default="stdio", validation_alias="MCP_SERVER_TRANSPORT")

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
  qdrant_vector_size: int = Field(default=1536, validation_alias="QDRANT_VECTOR_SIZE")
  qdrant_timeout_seconds: float = Field(default=5.0, validation_alias="QDRANT_TIMEOUT_SECONDS")

  embedding_model: str = Field(
    default="openai/text-embedding-3-small",
    validation_alias="EMBEDDING_MODEL",
  )
  embedding_base_url: str | None = Field(
    default="https://openrouter.ai/api/v1",
    validation_alias="EMBEDDING_BASE_URL",
  )
  embedding_api_key: str | None = Field(default=None, validation_alias="EMBEDDING_API_KEY")
  embedding_timeout_seconds: float = Field(
    default=10.0,
    validation_alias="EMBEDDING_TIMEOUT_SECONDS",
  )
  fact_llm_model: str = Field(default="openai/gpt-4.1-mini", validation_alias="FACT_LLM_MODEL")
  fact_llm_base_url: str | None = Field(
    default="https://openrouter.ai/api/v1",
    validation_alias="FACT_LLM_BASE_URL",
  )
  fact_llm_api_key: str | None = Field(default=None, validation_alias="FACT_LLM_API_KEY")
  fact_llm_timeout_seconds: float = Field(
    default=20.0,
    validation_alias="FACT_LLM_TIMEOUT_SECONDS",
  )
  fact_max_facts_per_item: int = Field(default=5, validation_alias="FACT_MAX_FACTS_PER_ITEM")
  fact_min_chars: int = Field(default=10, validation_alias="FACT_MIN_CHARS")
  fact_max_chars: int = Field(default=300, validation_alias="FACT_MAX_CHARS")
  reflection_llm_model: str = Field(
    default="openai/gpt-4.1-mini",
    validation_alias="REFLECTION_LLM_MODEL",
  )
  reflection_llm_base_url: str | None = Field(
    default="https://openrouter.ai/api/v1",
    validation_alias="REFLECTION_LLM_BASE_URL",
  )
  reflection_llm_api_key: str | None = Field(
    default=None,
    validation_alias="REFLECTION_LLM_API_KEY",
  )
  reflection_llm_timeout_seconds: float = Field(
    default=20.0,
    validation_alias="REFLECTION_LLM_TIMEOUT_SECONDS",
  )
  reflection_max_per_theme: int = Field(
    default=5,
    validation_alias="REFLECTION_MAX_PER_THEME",
  )
  reflection_min_chars: int = Field(default=20, validation_alias="REFLECTION_MIN_CHARS")
  reflection_max_chars: int = Field(default=300, validation_alias="REFLECTION_MAX_CHARS")
  pipeline_worker_enabled: bool = Field(
    default=True,
    validation_alias="PIPELINE_WORKER_ENABLED",
  )
  pipeline_worker_interval_seconds: float = Field(
    default=60.0,
    validation_alias="PIPELINE_WORKER_INTERVAL_SECONDS",
  )
  wiki_schema_path: str = Field(
    default="data/wiki_schema.yaml",
    validation_alias="WIKI_SCHEMA_PATH",
  )
  wiki_llm_timeout_seconds: float = Field(
    default=20.0,
    validation_alias="WIKI_LLM_TIMEOUT_SECONDS",
  )
  wiki_max_page_chars: int = Field(
    default=5000,
    validation_alias="WIKI_MAX_PAGE_CHARS",
  )
  wiki_min_facts_per_page: int = Field(
    default=3,
    validation_alias="WIKI_MIN_FACTS_PER_PAGE",
  )
  wiki_query_auto_persist_enabled: bool = Field(
    default=False,
    validation_alias="WIKI_QUERY_AUTO_PERSIST_ENABLED",
  )
  wiki_query_auto_persist_min_confidence: float = Field(
    default=0.75,
    validation_alias="WIKI_QUERY_AUTO_PERSIST_MIN_CONFIDENCE",
  )
  wiki_query_auto_persist_min_sources: int = Field(
    default=2,
    validation_alias="WIKI_QUERY_AUTO_PERSIST_MIN_SOURCES",
  )
  wiki_query_auto_persist_prefix: str = Field(
    default="qa",
    validation_alias="WIKI_QUERY_AUTO_PERSIST_PREFIX",
  )
  wiki_query_promote_to_canonical_enabled: bool = Field(
    default=True,
    validation_alias="WIKI_QUERY_PROMOTE_TO_CANONICAL_ENABLED",
  )
  wiki_query_maintenance_enabled: bool = Field(
    default=True,
    validation_alias="WIKI_QUERY_MAINTENANCE_ENABLED",
  )
  wiki_query_maintenance_max_pages_per_cycle: int = Field(
    default=10,
    validation_alias="WIKI_QUERY_MAINTENANCE_MAX_PAGES_PER_CYCLE",
  )
  wiki_query_dedupe_enabled: bool = Field(
    default=True,
    validation_alias="WIKI_QUERY_DEDUPE_ENABLED",
  )
  wiki_query_near_dedupe_min_token_jaccard: float = Field(
    default=0.6,
    validation_alias="WIKI_QUERY_NEAR_DEDUPE_MIN_TOKEN_JACCARD",
  )
  wiki_query_near_dedupe_min_source_jaccard: float = Field(
    default=1.0,
    validation_alias="WIKI_QUERY_NEAR_DEDUPE_MIN_SOURCE_JACCARD",
  )
  wiki_query_merge_provenance_max_entries: int = Field(
    default=3,
    validation_alias="WIKI_QUERY_MERGE_PROVENANCE_MAX_ENTRIES",
  )
  wiki_source_highlights_target_count: int = Field(
    default=3,
    validation_alias="WIKI_SOURCE_HIGHLIGHTS_TARGET_COUNT",
  )
  wiki_facts_kinds: list[str] = Field(
    default=["fact", "decision", "summary", "note", "task"],
    validation_alias="WIKI_FACTS_KINDS",
  )
  wiki_reflections_kinds: list[str] = Field(
    default=["reflection"],
    validation_alias="WIKI_REFLECTIONS_KINDS",
  )
  pipeline_worker_enabled: bool = Field(
    default=True,
    validation_alias="PIPELINE_WORKER_ENABLED",
  )
  pipeline_worker_interval_seconds: float = Field(
    default=60.0,
    validation_alias="PIPELINE_WORKER_INTERVAL_SECONDS",
  )

  @computed_field
  @property
  def wiki_llm_model(self) -> str:
    """Default to reflection LLM model for wiki"""
    return self.reflection_llm_model

  @computed_field
  @property
  def wiki_llm_base_url(self) -> str | None:
    """Default to reflection LLM base URL for wiki"""
    return self.reflection_llm_base_url

  @computed_field
  @property
  def wiki_llm_api_key(self) -> str | None:
    """Default to reflection LLM API key for wiki"""
    return self.reflection_llm_api_key

  @computed_field
  @property
  def mnemos_url(self) -> str:
    host = self.mnemos_host
    if host in {"0.0.0.0", "::"}:
      host = "localhost"
    return f"http://{host}:{self.mnemos_port}"

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
