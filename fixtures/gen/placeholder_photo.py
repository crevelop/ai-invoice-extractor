"""Placeholder photographed receipt — stand-in until the real photo is dropped
into fixtures/photo/ (see that folder's README). NOT part of generate.py: the
photo fixture is user-owned; this exists only so chapter 1 runs on a fresh
clone. Regenerate with: uv run python fixtures/gen/placeholder_photo.py

Simulates a phone photo: narrow thermal-ticket HTML -> raster -> slight
rotation + perspective -> warm cast + noise -> JPEG on a desk background.
"""

from __future__ import annotations

import random
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageEnhance
from weasyprint import HTML

OUT = Path(__file__).resolve().parent.parent / "photo" / "receipt-placeholder.jpg"

TICKET_HTML = """
<style>
  @page { size: 80mm 150mm; margin: 6mm; }
  body { font-family: 'Courier New', monospace; font-size: 8.5pt; color: #222; }
  .c { text-align: center; }
  hr { border: 0; border-top: 1px dashed #555; }
  table { width: 100%; font-size: 8.5pt; }
  td.n { text-align: right; }
  .tot { font-size: 11pt; font-weight: bold; }
</style>
<div class="c"><b>BAR RESTAURANTE CAN TONI</b><br>
Carrer del Rec 14, 08003 Barcelona<br>NIF 46.882.113-P · Tel 933 195 402</div>
<hr>
Fecha: 08/07/2026 14:21 &nbsp; Mesa: 6 &nbsp; Ticket: 0447<br>
<hr>
<table>
<tr><td>2x Menú del día</td><td class="n">27,00</td></tr>
<tr><td>1x Agua con gas 50cl</td><td class="n">2,40</td></tr>
<tr><td>2x Café solo</td><td class="n">2,80</td></tr>
<tr><td>1x Crema catalana</td><td class="n">4,50</td></tr>
</table>
<hr>
<table>
<tr class="tot"><td>TOTAL</td><td class="n">36,70 EUR</td></tr>
<tr><td>IVA 10% incluido</td><td class="n">3,34</td></tr>
<tr><td>Pago: tarjeta</td><td class="n"></td></tr>
</table>
<hr>
<div class="c">GRACIAS POR SU VISITA<br>Propina no incluida</div>
"""


def make(out: Path = OUT, seed: int = 7) -> Path:
    rng = random.Random(seed)
    doc = pdfium.PdfDocument(HTML(string=TICKET_HTML).write_pdf())
    ticket = doc[0].render(scale=150 / 72).to_pil().convert("RGB")
    doc.close()

    # rotate like a hand-held shot, drop onto a dark desk background
    ticket = ticket.rotate(rng.uniform(2.5, 4.5), resample=Image.BICUBIC,
                           expand=True, fillcolor=(72, 58, 48))
    bg = Image.new("RGB", (ticket.width + 120, ticket.height + 160), (72, 58, 48))
    bg.paste(ticket, (60, 80))

    # phone-camera look: warm cast, soft contrast, sensor noise, downscale
    warm = Image.new("RGB", bg.size, (255, 214, 170))
    img = Image.blend(bg, warm, 0.10)
    img = Image.blend(img, Image.effect_noise(img.size, 16).convert("RGB"), 0.05)
    img = ImageEnhance.Contrast(img).enhance(0.9)
    img = img.resize((img.width * 3 // 4, img.height * 3 // 4), Image.LANCZOS)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=82)
    return out


if __name__ == "__main__":
    print(f"wrote {make()}")
