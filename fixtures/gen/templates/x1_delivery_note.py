"""X1 — Spanish delivery note (albarán): the chapter-6 schema-swap document.

Not part of the eval corpus (no truth sidecar): quantities and articles but
NO prices — the document that proves the pipeline was never about invoices.
Generated from its own RNG stream so the invoice corpus stays byte-identical.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..data import BUYER, PRODUCTS, VENDORS
from .common import date_es, esc, qty

TEMPLATE_ID = "x1_delivery_note"
TAGS = ["es", "delivery_note", "schema_swap"]


@dataclass(frozen=True)
class DeliveryLine:
    description: str
    quantity: Decimal


@dataclass(frozen=True)
class DeliveryNoteData:
    number: str
    delivery_date: date
    order_reference: str
    lines: list[DeliveryLine]


def make(rng: random.Random) -> DeliveryNoteData:
    lines = [DeliveryLine(desc, Decimal(rng.choice([2, 4, 6, 10, 12, 24])))
             for desc in rng.sample(PRODUCTS["es"], k=rng.randint(4, 6))]
    return DeliveryNoteData(
        number=f"ALB-2026-{rng.randint(200, 900):04d}",
        delivery_date=date(2026, rng.randint(1, 6), rng.randint(1, 28)),
        order_reference=f"PO-2026-{rng.randint(80, 400):04d}",
        lines=lines,
    )


def build(note: DeliveryNoteData) -> str:
    vendor = VENDORS["es_clean"]
    rows = "".join(
        f"<tr><td>{i + 1}</td><td>{esc(li.description)}</td>"
        f"<td class='n'>{qty(li.quantity)}</td></tr>"
        for i, li in enumerate(note.lines)
    )
    return f"""
<style>
  @page {{ size: A4; margin: 18mm; }}
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #1d2733; }}
  .band {{ background: #166534; color: white; padding: 14px 18px; border-radius: 6px;
           display: flex; justify-content: space-between; align-items: baseline; }}
  .band h1 {{ margin: 0; font-size: 20pt; letter-spacing: 2px; }}
  .meta {{ display: flex; justify-content: space-between; margin: 22px 0; }}
  .meta h3 {{ margin: 0 0 4px; font-size: 8pt; text-transform: uppercase; color: #166534; }}
  table.items {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  .items th {{ text-align: left; font-size: 8pt; text-transform: uppercase;
               border-bottom: 2px solid #166534; padding: 6px 8px; color: #166534; }}
  .items td {{ padding: 7px 8px; border-bottom: 1px solid #e2e8f0; }}
  .n {{ text-align: right; }}
  .sign {{ margin-top: 40px; display: flex; justify-content: space-between; }}
  .sign div {{ width: 45%; border-top: 1px solid #94a3b8; padding-top: 6px;
               font-size: 8pt; color: #64748b; }}
  footer {{ margin-top: 30px; font-size: 8pt; color: #64748b; }}
</style>
<div class="band"><h1>ALBARÁN DE ENTREGA</h1><div>{esc(note.number)}</div></div>
<div class="meta">
  <div><h3>Emisor</h3><b>{esc(vendor.name)}</b><br>
    CIF: {esc(vendor.tax_id)}<br>{esc(vendor.address)}<br>{esc(vendor.city)}</div>
  <div><h3>Entregar a</h3><b>{BUYER["name"]}</b><br>
    CIF: {BUYER["tax_id"]}<br>{BUYER["address"]}<br>{BUYER["city"]}</div>
  <div><h3>Datos</h3>
    Fecha de entrega: <b>{date_es(note.delivery_date)}</b><br>
    Pedido: <b>{esc(note.order_reference)}</b><br>
    Bultos: {len(note.lines)}</div>
</div>
<table class="items">
  <tr><th>#</th><th>Artículo</th><th class="n">Cantidad</th></tr>
  {rows}
</table>
<p>Mercancía entregada sin cargo en factura — los importes se facturarán
según pedido {esc(note.order_reference)}.</p>
<div class="sign">
  <div>Firma del transportista</div>
  <div>Recibí conforme (sello y firma del cliente)</div>
</div>
<footer>{esc(vendor.name)} · CIF {esc(vendor.tax_id)} · Este albarán no es
una factura y no incluye precios.</footer>
"""
