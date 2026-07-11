"""Input adapters (chapter 1): PDF, scan, photo -> one Document shape.

A PDF is not text, and a photographed receipt is not a PDF. Everything
normalizes into Document here, and the rest of the pipeline never thinks
about file formats again.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

# Downscale page renders: plenty for a vision model, cheap to send.
MAX_EDGE = 1568


@dataclass
class Document:
    """The one shape everything funnels into. Two kinds:

    "text"  — the PDF had a real text layer; we read it directly (cheap, exact)
    "image" — scan or photo; no text to read, we carry page images instead
    """

    source: str
    kind: str  # "text" | "image"
    text: str | None = None
    page_images: list[Image.Image] = field(default_factory=list)

    @property
    def pages(self) -> int:
        return max(1, len(self.page_images))


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


def load(path: Path | str) -> Document:
    # The adapter: one entry point, any supported source.
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return load_pdf(path)
    return load_image(path)
