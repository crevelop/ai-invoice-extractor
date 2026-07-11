"""R2 — Quote (presupuesto). Looks exactly like an invoice — line items,
totals, IVA — but it's an offer, not a bill. The gate must REJECT it."""

import random
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from ..data import BUYER, PRODUCTS, Vendor
from .common import date_es, esc, money_eu, qty

TEMPLATE_ID = "r2_quote"
TAGS = ["es", "reject", "quote"]


def build(rng: random.Random, vendor: Vendor) -> str:
    issue = date(2026, rng.randint(1, 6), rng.randint(1, 28))
    items = []
    for desc in rng.sample(PRODUCTS["es"], k=rng.randint(3, 6)):
        q = Decimal(rng.choice([2, 6, 12, 24]))
        unit = (Decimal(rng.randint(300, 8000)) / 100).quantize(Decimal("0.01"))
        items.append((desc, q, unit, (q * unit).quantize(Decimal("0.01"))))
    subtotal = sum(t for *_, t in items)
    tax = (subtotal * 21 / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rows = "".join(
        f"<tr><td>{esc(d)}</td><td class='n'>{qty(q)}</td>"
        f"<td class='n'>{money_eu(u)}</td><td class='n'>{money_eu(t)}</td></tr>"
        for d, q, u, t in items
    )
    return f"""
<style>
  @page {{ size: A4; margin: 18mm; }}
  body {{ font-family: Georgia, serif; font-size: 10pt; color: #212121; }}
  .head {{ display: flex; justify-content: space-between; align-items: baseline;
           border-bottom: 3px solid #e65100; padding-bottom: 8px; }}
  .head h1 {{ color: #e65100; font-size: 19pt; margin: 0; letter-spacing: 2px; }}
  .ref {{ font-size: 11pt; }}
  .meta {{ display: flex; justify-content: space-between; margin: 16px 0; }}
  table.items {{ width: 100%; border-collapse: collapse; }}
  .items th {{ background: #fff3e0; border-bottom: 2px solid #e65100;
               text-align: left; padding: 6px 8px; font-size: 8.5pt; }}
  .items td {{ padding: 6px 8px; border-bottom: 1px solid #eee; }}
  .n {{ text-align: right; }}
  .tot {{ margin-left: 55%; width: 45%; margin-top: 10px; }}
  .tot td {{ padding: 4px 8px; }}
  .tot .g td {{ font-weight: bold; font-size: 12pt; border-top: 2px solid #e65100; }}
  .validity {{ margin-top: 16px; padding: 10px 12px; background: #fff3e0;
               border-left: 4px solid #e65100; font-size: 9pt; }}
</style>
<div class="head"><h1>PRESUPUESTO</h1>
  <span class="ref">Ref. PRE-2026-{rng.randint(100, 999)}</span></div>
<div class="meta">
  <div><b>{esc(vendor.name)}</b><br>CIF: {esc(vendor.tax_id)}<br>
    {esc(vendor.address)}<br>{esc(vendor.city)}</div>
  <div><b>Solicitado por:</b><br>{BUYER["name"]}<br>{BUYER["address"]}<br>
    {BUYER["city"]}</div>
  <div>Fecha: <b>{date_es(issue)}</b><br>Validez: <b>30 días</b></div>
</div>
<table class="items">
  <thead><tr><th>Concepto</th><th class="n">Cant.</th><th class="n">Precio €</th>
    <th class="n">Importe €</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<table class="tot">
  <tr><td>Base imponible</td><td class="n">{money_eu(subtotal)} €</td></tr>
  <tr><td>IVA 21%</td><td class="n">{money_eu(tax)} €</td></tr>
  <tr class="g"><td>TOTAL PRESUPUESTADO</td><td class="n">{money_eu(subtotal + tax)} €</td></tr>
</table>
<div class="validity"><b>Este presupuesto no es una factura</b> y carece de validez
fiscal. Precios válidos durante 30 días desde la fecha indicada. La factura se
emitirá a la aceptación del pedido.</div>
"""
