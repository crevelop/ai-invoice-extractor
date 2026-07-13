"""
Chapter 1 — Ingestion: every document becomes the same thing.

A digital PDF, a scanned PDF, and a phone photo are three different files.
One loader turns them all into a single Document shape, so the rest of the
system never cares where a file came from.
"""

# %% 1. Setup
# ------------------------------------------------------------------
# The implementation lives in extractor/adapters.py — this lesson runs it.

from extractor import DocumentLoader
from extractor.utils import INVOICES, sample_photo

loader = DocumentLoader()

# %% 2. Three very different files in, one shape out
# ------------------------------------------------------------------
# A digital invoice (real text inside), a scan (pixels only), and a photo.

digital = loader.load(INVOICES / "t01-es-clean-01.pdf")
scanned = loader.load(INVOICES / "t09-scanned-01.pdf")
photo = loader.load(sample_photo())

for doc in [digital, scanned, photo]:
    print(f"{doc.source}  →  kind={doc.kind}, pages={doc.pages}")

# %% 3. What is inside each one
# ------------------------------------------------------------------
# "text" documents carry the actual characters. "image" documents carry
# pictures of the pages. That is the ONLY difference downstream code sees.

print("The digital PDF's text starts with:")
print(digital.text[:120])

print("\nThe scan has no text — it carries a page image instead:")
print(f"{scanned.page_images[0].width} × {scanned.page_images[0].height} pixels")

print("\nSo does the photo:")
print(f"{photo.page_images[0].width} × {photo.page_images[0].height} pixels")

# %% 4. Why this matters
# ------------------------------------------------------------------
# From here on, the pipeline sees Document — never a file format.
# Every later chapter only ever asks one question: text or images?
