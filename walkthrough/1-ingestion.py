# %% cell 1: setup — imports + locate fixtures/ (run this cell first)
# Chapter 1 — Input adapters: a PDF is not text, and a photographed receipt
# is not a PDF. Two very different inputs normalize into ONE Document shape,
# and the rest of the pipeline never thinks about sources again.

from dataclasses import dataclass, field
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

# fixtures/ lives at the repo root — find it whether this runs as a script
# (__file__) or cell-by-cell in the interactive window (no __file__, use cwd)
_here = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
FIXTURES = next(p / "fixtures" for p in [_here, *_here.parents]
                if (p / "fixtures").is_dir())

# %% cell 2: the Document shape + the three adapters (defines, no output)
# The one shape everything funnels into. Two kinds:
#   "text"  — the PDF had a real text layer; we read it directly (cheap, exact)
#   "image" — scan or photo; no text to read, we carry page images instead
# Downstream (chapters 2+) only ever asks: text or images?


@dataclass
class Document:
    source: str
    kind: str  # "text" | "image"
    text: str | None = None
    page_images: list[Image.Image] = field(default_factory=list)

    @property
    def pages(self) -> int:
        return max(1, len(self.page_images))


MAX_EDGE = 1568  # downscale page renders: plenty for a vision model, cheap to send


def load_pdf(path: Path) -> Document:
    # Try the text layer first — digital-native PDFs carry the actual characters.
    pdf = pdfium.PdfDocument(path)
    text = "\n".join(p.get_textpage().get_text_bounded() for p in pdf)
    if len(text.strip()) > 100:  # a real text layer, not OCR junk or emptiness
        pdf.close()
        return Document(source=path.name, kind="text", text=text)

    # No text layer (a scan): rasterize each page instead.
    images = []
    for page in pdf:
        img = page.render(scale=2).to_pil()
        img.thumbnail((MAX_EDGE, MAX_EDGE))
        images.append(img)
    pdf.close()
    return Document(source=path.name, kind="image", page_images=images)


def load_image(path: Path) -> Document:
    # A photo is already an image — just normalize the size.
    img = Image.open(path).convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    return Document(source=path.name, kind="image", page_images=[img])


def load(path: Path) -> Document:
    # The adapter: one entry point, any supported source.
    if path.suffix.lower() == ".pdf":
        return load_pdf(path)
    return load_image(path)


# %% cell 3: run the adapter — three sources in, one table out
# Three real inputs, three very different files on disk:
#   1. a digital-native vendor PDF        (has a text layer)
#   2. a scanned copy of an invoice       (PDF, but zero extractable text)
#   3. a photographed restaurant receipt  (not a PDF at all)

photos = sorted(p for p in (FIXTURES / "photo").iterdir()
                if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
# prefer the real photo once it replaces the committed placeholder
photo = next((p for p in photos if "placeholder" not in p.name), photos[0])

inputs = [
    FIXTURES / "docs/invoices/t01-es-clean-01.pdf",
    FIXTURES / "docs/invoices/t09-scanned-01.pdf",
    photo,
]

docs = [load(p) for p in inputs]

print(f"{'source':<28}{'kind':<8}{'pages':>6}{'text chars':>12}")
print("-" * 54)
for doc in docs:
    chars = len(doc.text) if doc.text else 0
    print(f"{doc.source:<28}{doc.kind:<8}{doc.pages:>6}{chars:>12,}")

# %% cell 4: peek inside each Document (needs cell 3's `docs`)
# Same shape, three sources. Peek inside each one:

digital, scanned, photographed = docs

print("digital PDF → first lines of its text layer:")
print("   " + "\n   ".join(digital.text.splitlines()[:4]))

print(f"\nscanned PDF → no text layer; carrying {scanned.pages} page image "
      f"({scanned.page_images[0].width}×{scanned.page_images[0].height} px)")

print(f"photo       → {photographed.pages} image "
      f"({photographed.page_images[0].width}×{photographed.page_images[0].height} px)")

print("\nFrom here on, the pipeline sees `Document` — never a file format.")
