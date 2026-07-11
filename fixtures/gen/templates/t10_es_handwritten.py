"""T10 — Printed invoice with handwritten annotations over/near the values.
The annotations include a *distractor amount* (a partial payment) that is NOT
any schema field — truth stays the printed values. Trap: extractor must not
read handwriting as data."""

from ..data import BUYER, Vendor
from ..models import InvoiceTruth
from .common import HAND_STACK, date_es, esc, handwriting_font_css, money_eu, qty

TEMPLATE_ID = "t10_es_handwritten"
TAGS = ["es", "eur", "eu_decimals", "handwritten"]

# Scrawls near the values anchor to the totals block (its page position varies
# with line-item count); header scrawls anchor to the header.
# variant 0: paid stamp-style scrawl + circled total
# variant 1: partial-payment note with a distractor amount + urgency scrawl
ANNOTATIONS = [
    {"tot": """<div class="hand" style="top:-14mm; right:4mm; color:#1a54c7;
                 transform: rotate(-8deg); font-size:16pt;">PAGADO 15/06 ✓</div>
               <div class="circle" style="bottom:-4mm; right:-5mm;"></div>""",
     "head": ""},
    {"tot": """<div class="hand" style="bottom:-16mm; right:2mm; color:#c0392b;
                 transform: rotate(-4deg); font-size:13pt;">abonar 500 € a cuenta<br>
                 resto s/vencimiento</div>""",
     "head": """<div class="hand" style="top:14mm; left:64mm; color:#c0392b;
                 transform: rotate(-12deg); font-size:18pt;">¡URGENTE!</div>"""},
]


def build(inv: InvoiceTruth, vendor: Vendor, variant: int = 0) -> str:
    ann = ANNOTATIONS[variant % len(ANNOTATIONS)]
    rows = "".join(
        f"<tr><td>{esc(li.description)}</td><td class='n'>{qty(li.quantity)}</td>"
        f"<td class='n'>{money_eu(li.unit_price)}</td>"
        f"<td class='n'>{money_eu(li.total)}</td></tr>"
        for li in inv.line_items
    )
    return f"""
<style>
  @page {{ size: A4; margin: 18mm; }}
  {handwriting_font_css()}
  body {{ font-family: 'Courier New', monospace; font-size: 9.5pt; color: #222; }}
  .head {{ display: flex; justify-content: space-between; position: relative;
           border-bottom: 1px solid #222; padding-bottom: 8px; }}
  .head .co {{ font-size: 12pt; font-weight: bold; }}
  .parties {{ margin: 12px 0; display: flex; justify-content: space-between; }}
  table.items {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  .items th {{ border-top: 1px solid #222; border-bottom: 1px solid #222;
               text-align: left; padding: 5px 6px; font-size: 8.5pt; }}
  .items td {{ padding: 5px 6px; border-bottom: 1px dashed #aaa; }}
  .n {{ text-align: right; }}
  .totwrap {{ position: relative; margin-top: 10px; margin-left: 50%; width: 50%; }}
  .tot {{ width: 100%; }}
  .tot td {{ padding: 3px 6px; }}
  .tot .g td {{ font-weight: bold; border-top: 1px solid #222;
                border-bottom: 3px double #222; }}
  .hand {{ position: absolute; font-family: {HAND_STACK}; z-index: 10;
           line-height: 1.15; white-space: nowrap; }}
  .circle {{ position: absolute; width: 88mm; height: 13mm; z-index: 9;
             border: 2.5px solid #1a54c7; border-radius: 50%;
             transform: rotate(-2deg); opacity: 0.85; }}
</style>
<div class="head">
  <div class="co">{esc(inv.vendor_name)}<br>
    <span style="font-size:8pt;font-weight:normal">{esc(vendor.address)} ·
    {esc(vendor.city)} · CIF {esc(inv.vendor_tax_id)} ·
    Tel. {vendor.extra.get("phone", "")}</span></div>
  <div style="text-align:right">FACTURA Nº <b>{esc(inv.invoice_number)}</b><br>
    Fecha: {date_es(inv.issue_date)}<br>
    Vencimiento: {date_es(inv.due_date) if inv.due_date else "—"}</div>
  {ann["head"]}
</div>
<div class="parties">
  <div>Cliente: <b>{BUYER["name"]}</b> · CIF {BUYER["tax_id"]}<br>
    {BUYER["address"]} · {BUYER["city"]}</div>
</div>
<table class="items">
  <thead><tr><th>Concepto</th><th class="n">Cant.</th><th class="n">Precio €</th>
    <th class="n">Importe €</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<div class="totwrap">
<table class="tot">
  <tr><td>Base imponible</td><td class="n">{money_eu(inv.subtotal)} €</td></tr>
  <tr><td>IVA {qty(inv.tax_rate)}%</td><td class="n">{money_eu(inv.tax_amount)} €</td></tr>
  <tr class="g"><td>TOTAL</td><td class="n">{money_eu(inv.total)} €</td></tr>
</table>
{ann["tot"]}
</div>
"""
