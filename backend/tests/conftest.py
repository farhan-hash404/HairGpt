from __future__ import annotations

import importlib
import os
import tempfile
from io import BytesIO
from pathlib import Path

# --- Test configuration, set BEFORE any app module is imported ---------------
# Unit tests check logic (grounding, prescription safety, abstention, fusion
# maths) fast and offline. Retrieval QUALITY is measured by the benchmark in
# scripts/eval_rag.py against the full corpus and real embeddings.
_FIXTURES = Path(__file__).parent / "fixtures"
_SCRATCH = tempfile.mkdtemp(prefix="hairgpt-tests-")
os.environ.update({
    # Never the developer's database, even for code that opens its own session.
    "DATABASE_URL": f"sqlite:///{_SCRATCH}/unit.db",
    "STORAGE_LOCAL_DIR": f"{_SCRATCH}/storage",
    "CORPUS_FILE": str(_FIXTURES / "corpus_subset.jsonl"),  # 14 real documents
    "CHROMA_DIR": ":memory:",
    "EMBEDDING_PROVIDER": "hashing",
    "RAG_CROSS_ENCODER": "false",
    # Hashing embeddings are lexical, so their cosines run lower than MiniLM's;
    # the production threshold (0.43) is calibrated for the real model.
    "RAG_MIN_RELEVANCE": "0.05",
    "WARM_CACHES": "false",
    "LLM_PROVIDER": "none",
    "CHECKPOINT_DB": ":memory:",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_cache():
    """The answer cache and rate-limit counters are module-level; don't let one
    test's cached answer satisfy another's question."""
    from app.core.cache import reset_cache

    reset_cache()
    yield
    reset_cache()


@pytest.fixture
def client(monkeypatch):
    """A TestClient bound to an isolated database and storage directory."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmpdir}/test.db")
    monkeypatch.setenv("STORAGE_LOCAL_DIR", f"{tmpdir}/storage")
    monkeypatch.setenv("HAIRGPT_ENV", "dev")

    import app.core.config as config

    config.get_settings.cache_clear()
    config.settings = config.Settings()
    for mod in ("app.db.session", "app.services.storage", "app.main"):
        importlib.reload(importlib.import_module(mod))
    # Storage resolves its backend lazily; drop any cached one so it picks up
    # this test's temp directory.
    from app.services.storage import reset_storage

    reset_storage()
    from app.main import app as fresh_app

    with TestClient(fresh_app) as c:
        yield c


def make_jpeg(size: int = 1024, shade: int = 200) -> bytes:
    """A sufficiently large, sharp, evenly-lit image so the quality gate passes."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (size, size), (shade, shade - 28, shade - 48))
    d = ImageDraw.Draw(img)
    for i in range(0, size, 6):
        d.line([(0, i), (size, i)], fill=(52, 46, 42), width=2)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def authenticate(client, email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def grant_consent(client, headers) -> None:
    for purpose in ("storage", "analysis"):
        client.post("/api/v1/auth/consents", json={"purpose": purpose, "granted": True}, headers=headers)


def complete_scan(client, headers, domain: str = "hair", image: bytes | None = None) -> str:
    """Upload every required view and analyze, returning the session id."""
    created = client.post("/api/v1/scans", json={"domain": domain}, headers=headers).json()
    sid = created["session_id"]
    data = image or make_jpeg()
    for view in created["required_views"]:
        client.post(
            f"/api/v1/scans/{sid}/images/upload",
            data={"view": view},
            files={"file": ("x.jpg", data, "image/jpeg")},
            headers=headers,
        )
    client.post(f"/api/v1/scans/{sid}/analyze", json={}, headers=headers)
    return sid


@pytest.fixture
def client_with_reference(client):
    """A client whose user already has one COMPLETED scan, so a later capture has
    a reference to be framed against."""
    headers = authenticate(client, "reference@example.com")
    grant_consent(client, headers)
    reference_sid = complete_scan(client, headers, "hair")
    return client, headers, reference_sid
