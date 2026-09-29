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
    # onnx_minilm: real 384-d semantic embeddings via ONNX Runtime (no PyTorch).
    # hashing: dependency-free fallback used by the unit tests.
    embedding_provider: str = "onnx_minilm"
    embedding_dim: int = 384
    rag_top_k: int = 5
    corpus_file: str = "./data/corpus/documents.jsonl"
    chroma_dir: str = "./data/chroma"
    # Cross-encoder reranking (local ONNX). Best on the benchmark by every
    # precision metric; ~1 s per query on a laptop CPU.
    rag_cross_encoder: bool = True
    # Abstention: refuse only when BOTH signals say the corpus has nothing
    # relevant. Thresholds sit in the gap measured on the benchmark (in-scope
    # cosine >= 0.52 vs out-of-scope <= 0.34; the cross-encoder under-scores lay
    # phrasing, so it cannot veto alone). Recalibrate as the benchmark grows.
    rag_min_relevance: float = 0.43
    rag_min_ce_logit: float = -5.0
    # Pre-compute recommendation evidence in a background thread at startup.
    warm_caches: bool = True

    # Redis: shared cache + rate-limit counters, and the Celery broker. Unset on
    # single-container hosts, where everything falls back to process memory and
    # Celery tasks run inline.
    redis_url: str | None = None
    # How long an identical evidence question reuses its verified answer.
    qa_cache_ttl_s: int = 6 * 3600
    # Shared secret for the n8n webhooks; unset disables them entirely.
    automation_webhook_secret: str | None = None

    # LLM — "auto" picks the first provider with a key, else the deterministic
    # extractive path (fully grounded, never calls a model).
    llm_provider: str = "auto"  # auto | gemini | openai | anthropic | bedrock | none
    llm_model: str = ""  # optional override of the provider's default model
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    bedrock_model_id: str | None = None
    aws_region: str = "us-east-1"
    # Latency budget for synchronous requests: past this the pipeline falls back
    # to the deterministic explainer rather than keep the user waiting.
    llm_timeout_s: float = 6.0
    # Regeneration attempts when the judge rejects an explanation.
    llm_max_revisions: int = 1
    # LangGraph checkpoints: let a paused (human-in-the-loop) analysis resume in
    # a later request or after a restart. ":memory:" for tests.
    checkpoint_db: str = "./data/checkpoints.sqlite"

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
