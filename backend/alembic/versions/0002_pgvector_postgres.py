"""pgvector: enable extension and convert evidence_chunks.embedding to vector(768)

This migration is a NO-OP on SQLite (dev) and only applies on PostgreSQL, where
it enables pgvector, converts the portable JSON embedding column into a native
`vector` column, and creates an HNSW cosine index for fast retrieval.

Revision ID: 0002_pgvector
Revises: fecd21625f17
Create Date: 2026-08-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_pgvector"
down_revision: Union[str, None] = "fecd21625f17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # dev/SQLite keeps the portable JSON column

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    # Convert JSONB array -> vector. Existing rows are re-embedded by the admin
    # ingest job; we drop and recreate to avoid a lossy cast.
    op.execute("ALTER TABLE evidence_chunks DROP COLUMN IF EXISTS embedding")
    op.execute(f"ALTER TABLE evidence_chunks ADD COLUMN embedding vector({EMBEDDING_DIM})")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_evidence_chunks_embedding_hnsw "
        "ON evidence_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_evidence_chunks_embedding_hnsw")
    op.execute("ALTER TABLE evidence_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE evidence_chunks ADD COLUMN embedding JSONB")
