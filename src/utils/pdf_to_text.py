"""Extract plain text from a PDF resume using PyMuPDF (fitz)."""

from __future__ import annotations

from pathlib import Path


def pdf_to_text(pdf_path: Path, output_path: Path) -> str:
    """Extract text from *pdf_path*, write it to *output_path*, and return it.

    Uses PyMuPDF (``import fitz``) which ships as the ``pymupdf`` package.
    """
    import fitz  # PyMuPDF

    text_parts: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())

    text = "\n".join(text_parts).strip()
    output_path.write_text(text, encoding="utf-8")
    return text
