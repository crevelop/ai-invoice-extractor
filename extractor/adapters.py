"""Input adapters (chapter 1): PDF, scan, photo -> one Document shape.

A PDF is not text, and a photographed receipt is not a PDF. DocumentLoader
normalizes every source into Document here, and the rest of the pipeline
never thinks about file formats again.
"""

import io
from dataclasses import dataclass, field
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image


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
    page_count: int = 1  # real page count — text documents carry no images

    @property
    def pages(self) -> int:
        return max(self.page_count, len(self.page_images))

    def png_pages(self) -> list[bytes]:
        """Each page image as PNG bytes — the form vision APIs consume."""
        pages = []
        for img in self.page_images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pages.append(buf.getvalue())
        return pages


class DocumentLoader:
    """One entry point, any supported source.

    PDFs try the text layer first (digital-native files carry the actual
    characters); anything without one — scans, photos — becomes page images,
    downscaled so they stay cheap to send to a vision model.
    """

    def __init__(self, max_edge: int = 1568):
        self.max_edge = max_edge  # plenty of pixels for a vision model

    def load(self, path: Path | str) -> Document:
        path = Path(path)
        if path.suffix.lower() == ".pdf":
            return self._from_pdf(path)
        return self._from_image(path)

    def _from_pdf(self, path: Path) -> Document:
        pdf = pdfium.PdfDocument(path)
        pages = len(pdf)
        text = "\n".join(p.get_textpage().get_text_bounded() for p in pdf)
        if len(text.strip()) > 100:  # a real text layer, not OCR junk
            pdf.close()
            return Document(source=path.name, kind="text", text=text,
                            page_count=pages)

        # No text layer (a scan): rasterize each page instead.
        images = [self._shrink(page.render(scale=2).to_pil()) for page in pdf]
        pdf.close()
        return Document(source=path.name, kind="image", page_images=images)

    def _from_image(self, path: Path) -> Document:
        # A photo is already an image — just normalize mode and size.
        img = self._shrink(Image.open(path).convert("RGB"))
        return Document(source=path.name, kind="image", page_images=[img])

    def _shrink(self, img: Image.Image) -> Image.Image:
        img.thumbnail((self.max_edge, self.max_edge))
        return img


def load(path: Path | str) -> Document:
    """Convenience: load one file with default settings."""
    return DocumentLoader().load(path)
