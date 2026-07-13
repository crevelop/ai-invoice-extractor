# %% cell 1: setup — imports (run this cell first)
# Chapter 1 — Input adapters: a PDF is not text, and a photographed receipt
# is not a PDF. Two very different inputs normalize into ONE Document shape,
# and the rest of the pipeline never thinks about sources again.
#
# The implementation is extractor/adapters.py — keep it open alongside;
# this lesson just runs it. (Lessons sit at the repo root next to extractor/,
# so imports work as a script and in the interactive window, no path setup.)

from extractor import DocumentLoader
from extractor.utils import INVOICES, sample_photo

# %% cell 2: run the adapter — three sources in, one table out
# Three real inputs, three very different files on disk:
#   1. a digital-native vendor PDF        (has a text layer)
#   2. a scanned copy of an invoice       (PDF, but zero extractable text)
#   3. a photographed restaurant receipt  (not a PDF at all)

loader = DocumentLoader()

docs = [loader.load(INVOICES / "t01-es-clean-01.pdf"),
        loader.load(INVOICES / "t09-scanned-01.pdf"),
        loader.load(sample_photo())]

print(f"{'source':<28}{'kind':<8}{'pages':>6}{'text chars':>12}")
print("-" * 54)
for doc in docs:
    chars = len(doc.text) if doc.text else 0
    print(f"{doc.source:<28}{doc.kind:<8}{doc.pages:>6}{chars:>12,}")

# %% cell 3: peek inside each Document (needs cell 2's `docs`)
# Same shape, three sources. Two kinds only:
#   "text"  — the PDF carried real characters; we read them directly
#   "image" — scan or photo; we carry downscaled page images instead

digital, scanned, photographed = docs

print("digital PDF → first lines of its text layer:")
print("   " + "\n   ".join(digital.text.splitlines()[:4]))

print(f"\nscanned PDF → no text layer; carrying {scanned.pages} page image "
      f"({scanned.page_images[0].width}×{scanned.page_images[0].height} px)")

print(f"photo       → {photographed.pages} image "
      f"({photographed.page_images[0].width}×{photographed.page_images[0].height} px)")

# %% cell 4: wrap-up (narration only, nothing to run)
# From here on, the pipeline sees `Document` — never a file format.
# Downstream code only ever asks one question: text or images?
