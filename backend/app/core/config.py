from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration. All values overridable via environment / .env.

    Defaults are chosen so the MVP runs with no external services.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    hairgpt_env: str = "dev"
    secret_key: str = "dev-insecure-secret-change-me-please-32chars"
    access_token_ttl_min: int = 30
    refresh_token_ttl_days: int = 14
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "sqlite:///./hairgpt.db"

    # Storage
    storage_backend: str = "local"
    storage_local_dir: str = "./storage"
    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    image_encryption_key: str | None = None

    # CV
    cv_backend: str = "mock"
    cv_model_dir: str = "./models"

    # RAG
    embedding_provider: str = "hashing"
    embedding_dim: int = 768
    rag_top_k: int = 5

    # LLM
    llm_provider: str = "mock"
    llm_model: str = "claude-sonnet-5"
    anthropic_api_key: str | None = None

    # Safety
    safety_strict: bool = True

    # Domains. The pipeline, CV interfaces and safety engine are all
    # domain-parameterized, and the skin path is fully implemented behind them —
    # but the product deliberately ships ONE domain. A shallow second product
    # costs more credibility than it adds surface area. Flip this to expose it.
    enable_skin_domain: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.hairgpt_env.lower() in {"prod", "production"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
