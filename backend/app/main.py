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
    comparisons,
    history,
    products,
    scans,
    timeline,
    treatments,
)
from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.rag.ingest import seed_corpus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hairgpt")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables and seed the medical corpus. Production uses
    # Alembic migrations + an explicit admin ingest, not auto-create.
    if not settings.is_prod:
        init_db()
        db = SessionLocal()
        try:
            n = seed_corpus(db)
            if n:
                log.info("Seeded %d evidence documents", n)
        finally:
            db.close()
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
    return {
        "status": "ok",
        "version": __version__,
        "cv_backend": settings.cv_backend,
        "llm_provider": settings.llm_provider,
        "notice": "Image-based observations only. Not a medical diagnosis. Never prescribes.",
    }


API = "/api/v1"
for r in (auth, scans, treatments, timeline, comparisons, products, analyses, account, history):
    app.include_router(r.router, prefix=API)
