"""M5 document ingestion -- offline (the md->items->facts path needs no markitdown)."""

import pytest

from raven.ingest import ingest_corpus
from raven.ingest_docs import document_to_markdown, load_document, markdown_to_items


def test_markdown_to_items_splits_and_strips():
    md = "# Heading\n\nMaya is vegetarian.\n\n- Keep dinners under $40\n- Always confirm before paying\n\n   \n"
    items = markdown_to_items(md, source="doc")
    texts = [it["text"] for it in items]
    assert "Maya is vegetarian." in texts
    assert any("under $40" in t for t in texts)
    assert all(it["kind"] == "document" for it in items)
    assert all(len(it["text"]) >= 3 for it in items)


def test_tight_bullet_list_splits_per_item():
    # A bullet list with no blank lines must NOT collapse into one item (which would
    # single-label to one type and drop the other constraints).
    md = "- Maya is vegetarian\n- Keep dinners under $40\n- Always confirm before paying"
    items = markdown_to_items(md, source="d")
    assert len(items) == 3
    types = {f.type for f in ingest_corpus(items)}
    assert {"dietary", "budget_limit", "permission"} <= types


def test_load_document_txt_path_needs_no_markitdown():
    # Atomic sentences (the corpus/ingest path is single-label, like the real corpus).
    data = b"Maya is vegetarian.\n\nKeep dinners under $40.\n\nAlways confirm before paying."
    items = load_document(data, "notes.txt", source="notes")
    assert len(items) == 3
    facts = ingest_corpus(items)
    types = {f.type for f in facts}
    assert {"dietary", "budget_limit", "permission"} <= types


def test_pdf_without_markitdown_raises_clear_error():
    import importlib.util

    # find_spec, NOT import -> the offline test never pulls markitdown into sys.modules.
    if importlib.util.find_spec("markitdown") is not None:
        pytest.skip("markitdown installed; the missing-dependency path cannot be exercised")
    with pytest.raises(RuntimeError):
        document_to_markdown(b"%PDF-1.4 fake", "x.pdf")
