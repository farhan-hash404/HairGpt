from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routers import (
    account,
    analyses,
    auth,
    automation,
    comparisons,
    history,
    products,
    qa,
    scans,
    timeline,
    treatments,
)
from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.rag.ingest import ensure_evidence

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hairgpt")


def _warm_caches() -> None:
    """Pre-compute rule evidence so the first analysis is not slowed by the reranker."""
    from app.recommendations.engine import warm_cache

    db = SessionLocal()
    try:
        log.info("warmed evidence for %d recommendation rules", warm_cache(db))
    except Exception as exc:  # warming is an optimisation, never a startup failure
        log.warning("cache warm-up failed: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables. Production uses Alembic migrations.
    if not settings.is_prod:
        init_db()
    # Every environment needs the evidence index. It is idempotent: when the
    # corpus and vectors are already in sync (e.g. baked into the Docker image)
    # this is a quick check, not a rebuild.
    db = SessionLocal()
    try:
        info = ensure_evidence(db)
        log.info("evidence index: %s documents, %s chunks (%s)",
                 info.get("documents"), info.get("chunks"), info.get("embedding"))
    finally:
        db.close()
    if settings.warm_caches:
        import threading

        threading.Thread(target=_warm_caches, name="warm-caches", daemon=True).start()
    log.info(
        "HairGPT %s started | CV_BACKEND=%s LLM=%s EMB=%s DB=%s",
        __version__, settings.cv_backend, settings.llm_provider,
        settings.embedding_provider, settings.database_url.split(":")[0],
    )
    yield


app = FastAPI(
    title="HairGPT API",
    version=__version__,
    description=(
        "Multimodal hair/scalp and skin analysis. Provides image-based observations "
        "and AI inferences, NOT medical diagnoses. Never prescribes; a deterministic "
        "safety layer can override the LLM."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health():
    from app.core.cache import get_redis
    from app.llm.chat import provider_info
    from app.rag.index import get_rag_index

    llm = provider_info()
    index = get_rag_index()
    return {
        "status": "ok",
        "version": __version__,
        "cv_backend": settings.cv_backend,
        "llm": {"provider": llm.provider, "model": llm.model, "available": llm.available},
        "evidence": {"documents": index.state.get("documents"), "chunks": index.state.get("chunks"),
                     "embedding": index.state.get("embedding")},
        "redis": get_redis() is not None,
        "notice": "Image-based observations only. Not a medical diagnosis. Never prescribes.",
    }


API = "/api/v1"
for r in (auth, scans, treatments, timeline, comparisons, products, analyses, account, history, qa, automation):
    app.include_router(r.router, prefix=API)
