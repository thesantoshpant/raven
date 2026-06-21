"""Document ingestion (M5): PDF / docx / html / md -> markdown -> memory items -> facts.

`markdown_to_items` is pure + offline-testable. `document_to_markdown` lazy-imports
`markitdown` (optional) for binary formats, and decodes .md/.txt directly without it.
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import List, Union

_HEADING = re.compile(r"^#{1,6}\s+", re.M)
_LIST_LINE = re.compile(r"^\s*(?:[\-\*\+]|\d+[.)])\s+")  # bullets and numbered lists
_BLANKLINE = re.compile(r"\n\s*\n")


def markdown_to_items(md: str, source: str = "upload") -> List[dict]:
    """Split markdown into corpus-shaped memory items ({id, kind, text}).

    Blank lines separate blocks; a block that is a LIST (any line is a bullet/numbered
    item) is split per line so a tight list doesn't collapse several constraints into one
    item (a prose paragraph stays a single item). Light markdown stripping throughout."""
    items: List[dict] = []
    idx = 0
    for block in _BLANKLINE.split(md or ""):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        units = lines if any(_LIST_LINE.match(ln) for ln in lines) else ["\n".join(lines)]
        for unit in units:
            text = _HEADING.sub("", unit)
            text = _LIST_LINE.sub("", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 3:
                continue
            items.append({"id": f"{source}_{idx}", "kind": "document", "text": text})
            idx += 1
    return items


def document_to_markdown(data: Union[bytes, str], filename: str = "") -> str:
    """Bytes (or a path) -> markdown. .md/.txt are decoded directly; other formats go
    through markitdown (lazy import). Raises RuntimeError if markitdown is needed but
    absent."""
    name = (filename or "").lower()
    if name.endswith((".md", ".txt", ".markdown")):
        return data.decode("utf-8", errors="replace") if isinstance(data, (bytes, bytearray)) else str(data)

    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "markitdown is not installed (pip install -r requirements-docs.txt), "
            "or upload a .md/.txt file instead."
        ) from exc

    md = MarkItDown()
    if isinstance(data, (bytes, bytearray)):
        suffix = os.path.splitext(name)[1] or ".bin"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            tmp.write(data)
            tmp.close()
            return md.convert(tmp.name).text_content
        finally:
            try:
                os.unlink(tmp.name)  # best-effort; don't mask a parse error on Windows locks
            except OSError:
                pass
    return md.convert(str(data)).text_content


def load_document(data: Union[bytes, str], filename: str = "", source: str = "upload") -> List[dict]:
    """Full path: a document (bytes/path) -> memory items."""
    return markdown_to_items(document_to_markdown(data, filename), source=source)
