"""Clinic knowledge retrieval — pgvector when available, keyword fallback otherwise."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import rollback_db
from app.models.clinic_chunk import ClinicChunk

logger = logging.getLogger(__name__)

_KB_PATH = Path(__file__).resolve().parents[2] / "data" / "clinic_kb.md"
_EMBEDDING_DIM = 1536

# In-memory cache for keyword fallback (tests + no pgvector)
_chunk_cache: list[tuple[str, str, str]] | None = None  # (key, content, keywords)


def _load_kb_markdown() -> str:
    if not _KB_PATH.is_file():
        raise FileNotFoundError(f"Clinic KB not found: {_KB_PATH}")
    return _KB_PATH.read_text(encoding="utf-8")


def _split_kb_into_chunks(md: str) -> list[tuple[str, str]]:
    """Split markdown into sections by ## headings."""
    parts = re.split(r"\n(?=## )", md.strip())
    chunks: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        title = lines[0].lstrip("#").strip()
        key = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "intro"
        chunks.append((key, part))
    return chunks


def _keywords_from_content(content: str) -> str:
    return content.lower()


def _ensure_chunk_cache() -> list[tuple[str, str, str]]:
    global _chunk_cache
    if _chunk_cache is None:
        md = _load_kb_markdown()
        _chunk_cache = [
            (key, body, _keywords_from_content(body))
            for key, body in _split_kb_into_chunks(md)
        ]
    return _chunk_cache


def _embedding_literal(embedding: list[float]) -> str:
    """pgvector text input format for CAST(... AS vector)."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


def embed_text(text_input: str, *, model: str | None = None) -> list[float]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings")
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    _model = model or settings.embedding_model
    resp = client.embeddings.create(input=text_input, model=_model)
    data = resp.data[0].embedding
    return list(data)


def _pgvector_available(db: Session) -> bool:
    try:
        bind = db.get_bind()
        if bind.dialect.name != "postgresql":
            return False
        ext = db.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        ).scalar()
        table = db.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'clinic_chunks')"
            )
        ).scalar()
        return bool(ext and table)
    except Exception:
        rollback_db(db)
        return False


def retrieve_keyword(query: str, top_k: int | None = None) -> list[str]:
    """Overlap-based retrieval without DB (unit tests, no Postgres)."""
    k = top_k or settings.rag_top_k
    q = query.lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 2]
    scored: list[tuple[int, str]] = []
    for _key, body, kw in _ensure_chunk_cache():
        score = sum(1 for t in tokens if t in kw)
        if score > 0:
            scored.append((score, body))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return [body for _key, body, _kw in _ensure_chunk_cache()[:k]]
    return [body for _score, body in scored[:k]]


def retrieve(db: Session | None, query: str, top_k: int | None = None) -> list[str]:
    """Return top-k clinic knowledge chunk texts for a patient query."""
    if not settings.rag_enabled:
        return []

    k = top_k or settings.rag_top_k

    if db is None or not _pgvector_available(db):
        return retrieve_keyword(query, top_k=k)

    try:
        embedding = embed_text(query)
        rows = db.execute(
            text(
                """
                SELECT content FROM clinic_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT :k
                """
            ),
            {"vec": _embedding_literal(embedding), "k": k},
        ).fetchall()
        if rows:
            return [r[0] for r in rows]
    except Exception:
        logger.exception("pgvector retrieve failed — using keyword fallback")
        rollback_db(db)

    return retrieve_keyword(query, top_k=k)


def seed_kb(db: Session) -> int:
    """
    Idempotent seed: upsert clinic_chunks from clinic_kb.md with embeddings.
    Returns number of chunks written.
    """
    chunks = _split_kb_into_chunks(_load_kb_markdown())
    count = 0
    use_vector = _pgvector_available(db)

    for key, content in chunks:
        existing = db.scalar(select(ClinicChunk).where(ClinicChunk.chunk_key == key))
        if existing is None:
            row = ClinicChunk(
                id=uuid.uuid4(),
                chunk_key=key,
                content=content,
                metadata_={"source": "clinic_kb.md"},
            )
            db.add(row)
            db.flush()
            chunk_id = row.id
        else:
            existing.content = content
            chunk_id = existing.id

        if use_vector and settings.openai_api_key:
            emb = embed_text(content)
            db.execute(
                text(
                    "UPDATE clinic_chunks SET embedding = CAST(:vec AS vector) WHERE id = :id"
                ),
                {"vec": _embedding_literal(emb), "id": chunk_id},
            )
        count += 1

    db.commit()
    global _chunk_cache
    _chunk_cache = None
    _ensure_chunk_cache()
    return count


def format_context(chunks: list[str]) -> str:
    if not chunks:
        return ""
    return "\n\n---\n\n".join(chunks)
