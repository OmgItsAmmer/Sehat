"""RAG clinic knowledge retrieval."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services import rag

pytestmark = pytest.mark.unit


def test_retrieve_keyword_hours() -> None:
    chunks = rag.retrieve_keyword("what are clinic timings and hours", top_k=2)
    assert chunks
    combined = " ".join(chunks).lower()
    assert "9" in combined or "hour" in combined or "open" in combined


def test_format_context_joins_chunks() -> None:
    out = rag.format_context(["a", "b"])
    assert "a" in out and "b" in out


@patch("app.services.rag.embed_text", return_value=[0.1] * 1536)
@patch("app.services.rag._pgvector_available", return_value=False)
def test_retrieve_falls_back_without_pgvector(_mock_pg: object, _mock_emb: object) -> None:
    chunks = rag.retrieve(None, "Dr Saeed general doctor")
    assert chunks
