# HairGPT — Medical RAG Architecture

**Goal:** every important medical claim is traceable to a high-quality source. The LLM may only assert medical guidance that is grounded in retrieved evidence; ungrounded claims are stripped.

## Allowed sources (allowlist, enforced at ingestion)
`AAD` (American Academy of Dermatology), `FDA`, `NICE`, `NHS`, `peer_reviewed` dermatology literature, `systematic_review`, clinical `guideline`. **Social media, forums, blogs, and marketing copy are rejected by the ingestion allowlist** (`source` is an enum; ingestion refuses anything else). Each document stores `publisher`, `url`, `pub_date`, and an `evidence_grade`.

## Ingestion pipeline (`backend/app/rag/ingest.py`)
```
curated source doc ─► allowlist check ─► clean/normalize ─► chunk (≈512 tok, overlap 64)
   ─► embed (EmbeddingProvider) ─► store evidence_chunks(embedding vector(768)) + evidence_documents
```
Ingestion is **offline/admin-only**. A seed corpus of short, quote-safe summaries of public guidance ships for the MVP (see `backend/app/rag/seed_corpus.py`) so the pipeline is demonstrable without redistributing copyrighted full texts.

## Embeddings (`backend/app/rag/embeddings.py`)
`EmbeddingProvider` ABC with:
- `HashingEmbedding` (default, dependency-free, deterministic) — lets RAG run with no ML stack.
- `SentenceTransformerEmbedding` (real) — e.g. a 768-dim biomedical/sentence model, enabled by config.
Same-interface swap, mirroring the CV layer.

## Retrieval (`backend/app/rag/retriever.py`)
```
concern terms (from observations) + domain ─► embed query
   ─► pgvector cosine top-k (filter by domain/source/grade)
   ─► rerank by evidence_grade & recency ─► EvidenceRef[]
```
Retrieval is **concern-driven**: the observed concerns (e.g. "patterned thinning", "scalp inflammation", "acne-like lesions") form the query, never the raw image. Vector search uses pgvector; a NumPy cosine fallback exists for environments without the extension (dev only).

## Grounding contract
1. Recommendation Engine proposes candidate guidance.
2. Each candidate must attach ≥1 `EvidenceRef` from retrieval, or it is dropped (except pure "see a clinician" referrals, which need no citation).
3. The LLM prompt includes the evidence text; the system instruction forbids introducing medical claims not present in the provided evidence.
4. The response's `evidence[]` is populated from the actually-used refs; the **"Evidence"** button surfaces them with source + grade.

## Provenance & traceability
`recommendations.evidence_refs → evidence_documents`. `GET /analyses/{id}/evidence` resolves the full chain. Nothing that looks like a medical claim renders in the UI without an attached, resolvable source (or an explicit "general wellness, not medical evidence" label for non-medical tips).

## Freshness & governance
Documents carry `retrieved_at` and `pub_date`; the admin corpus can be refreshed. Guidelines that are superseded are marked `deprecated` and excluded from retrieval. Evidence grading follows a simple hierarchy (systematic review > guideline > peer-reviewed study > agency page) used in reranking and shown to the user.
