"""Rendering helpers: HTML→PDF (WeasyPrint), scan simulation, PDF concat.

Everything here is byte-deterministic: Pillow and PDFium stamp the current
time into the PDFs they write, so both stamps are pinned to the corpus seed
date — same seed, same bytes, clean `git diff` after a regenerate.
"""

from __future__ import annotations

import io
import random
import re
import time

import pypdfium2 as pdfium
from PIL import Image, ImageEnhance
from weasyprint import HTML

# 2026-07-11, the FIXTURE_SEED date.
_PINNED_DATE = time.struct_time((2026, 7, 11, 0, 0, 0, 0, 0, 0))


def html_to_pdf(html: str) -> bytes:
    return HTML(string=html).write_pdf()


def page_count(pdf: bytes) -> int:
    doc = pdfium.PdfDocument(pdf)
    try:
        return len(doc)
    finally:
        doc.close()


def concat_pdfs(parts: list[bytes]) -> bytes:
    """Merge PDFs into one (the 'two invoices in one attachment' case)."""
    dest = pdfium.PdfDocument.new()
    for part in parts:
        src = pdfium.PdfDocument(part)
        dest.import_pages(src)
        src.close()
    buf = io.BytesIO()
    dest.save(buf)
    dest.close()
    # PDFium offers no way to suppress its timestamp — pin it after the fact
    # (same byte length, so the xref offsets stay valid).
    return re.sub(rb"/CreationDate\(D:\d{14}\)",
                  b"/CreationDate(D:20260711000000)", buf.getvalue())


def scanify(pdf: bytes, rng: random.Random, dpi: int = 150) -> bytes:
    """Simulate a flatbed scan: rasterize, rotate slightly, add noise.

    The result is an image-only PDF — no text layer — so the ingestion
    adapter must take the page-rendering path (SPEC.md §3).
    """
    doc = pdfium.PdfDocument(pdf)
    angle = rng.uniform(1.0, 3.0) * rng.choice([-1, 1])
    pages = []
    for page in doc:
        img = page.render(scale=dpi / 72).to_pil().convert("RGB")
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True,
                         fillcolor=(252, 252, 250))
        noise = Image.effect_noise(img.size, 14).convert("RGB")
        img = Image.blend(img, noise, 0.06)
        img = ImageEnhance.Contrast(img).enhance(0.92)
        img = ImageEnhance.Brightness(img).enhance(1.03)
        pages.append(img)
    doc.close()

    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:],
                  resolution=dpi, creationDate=_PINNED_DATE,
                  modDate=_PINNED_DATE)
    return buf.getvalue()
