"""evidence provenance: licence, attribution, stable keys; vectors move to ChromaDB

The hand-written seed corpus is replaced by a scraped, openly-licensed corpus.
Every document now carries its licence and attribution, and a stable key so
rebuilds are idempotent. Dense vectors move out of SQL into ChromaDB, so the
old ``evidence_chunks.embedding`` column (a pgvector column on PostgreSQL) is
dropped; its HNSW index goes with it.

Legacy rows without a ``doc_key`` are removed by the next index sync, not here,
so this migration stays a pure schema change.

Revision ID: d6bfebc41d0f
Revises: 5153637a15a3
Create Date: 2026-09-29 14:18:29.578185
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.base  # noqa: F401 - custom GUID/JSONType column types


revision: str = 'd6bfebc41d0f'
down_revision: Union[str, None] = '5153637a15a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Server defaults let the NOT NULL columns be added to populated tables.
    with op.batch_alter_table('evidence_chunks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('section', sa.String(length=300), nullable=False, server_default=''))
        batch_op.drop_column('embedding')

    with op.batch_alter_table('evidence_documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('doc_key', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('source_type', sa.String(length=16), nullable=False, server_default='scraped'))
        batch_op.add_column(sa.Column('license', sa.String(length=48), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('license_url', sa.String(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('attribution', sa.Text(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('content_hash', sa.String(length=64), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('meta', app.db.base.JSONType(), nullable=True))
        batch_op.create_index(batch_op.f('ix_evidence_documents_doc_key'), ['doc_key'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('evidence_documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_evidence_documents_doc_key'))
        batch_op.drop_column('meta')
        batch_op.drop_column('content_hash')
        batch_op.drop_column('attribution')
        batch_op.drop_column('license_url')
        batch_op.drop_column('license')
        batch_op.drop_column('source_type')
        batch_op.drop_column('doc_key')

    with op.batch_alter_table('evidence_chunks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding', sa.TEXT(), nullable=False, server_default='[]'))
        batch_op.drop_column('section')
