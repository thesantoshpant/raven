"""OPTIONAL smoke test for fastembed (ONNX embeddings, no torch). NOT part of the
pytest gate — the core/tests run on the stdlib BM25 path with fastembed absent.

Run manually only:  python bench/smoke_fastembed.py
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from fastembed import TextEmbedding  # type: ignore
    except Exception as e:  # pragma: no cover - optional dependency
        print(f"fastembed not installed/available ({e}). Skipping (this is fine).")
        return 0
    try:
        model = TextEmbedding()  # downloads a small ONNX model on first run
        vecs = list(model.embed(["Maya is vegetarian", "the bar was loud"]))
        print(f"fastembed OK: produced {len(vecs)} vectors of dim {len(vecs[0])}.")
        return 0
    except Exception as e:  # pragma: no cover
        print(f"fastembed present but failed to run ({e}).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
