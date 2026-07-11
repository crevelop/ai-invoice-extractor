"""T6 — Minimalist startup invoice, English. Deliberately missing fields:
no due date, no PO, no payment terms. Extractor must return None, not invent."""

from ..data import BUYER, Vendor
from ..models import InvoiceTruth
from .common import date_en, esc, money_eu, qty

TEMPLATE_ID = "t06_en_minimal"
TAGS = ["en", "eur", "missing_fields"]


def build(inv: InvoiceTruth, vendor: Vendor) -> str:
    assert inv.due_date is None, "T6 exists to cover the missing-due-date case"
    rows = "".join(
        f"<tr><td>{esc(li.description)}</td><td class='n'>{qty(li.quantity)}</td>"
        f"<td class='n'>€{money_eu(li.unit_price)}</td>"
        f"<td class='n'>€{money_eu(li.total)}</td></tr>"
        for li in inv.line_items
    )
    return f"""
<style>
  @page {{ size: A4; margin: 28mm; }}
  body {{ font-family: 'Helvetica Neue', Helvetica, sans-serif; font-size: 10pt;
          color: #333; }}
  h1 {{ font-weight: 300; font-size: 26pt; letter-spacing: 6px; margin: 0 0 24px; }}
  .row {{ display: flex; justify-content: space-between; margin-bottom: 28px; }}
  .muted {{ color: #999; font-size: 8pt; text-transform: uppercase;
            letter-spacing: 1px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; font-size: 8pt; color: #999; text-transform: uppercase;
        letter-spacing: 1px; padding: 8px 0; border-bottom: 1px solid #ddd; }}
  td {{ padding: 10px 0; border-bottom: 1px solid #eee; }}
  .n {{ text-align: right; }}
  .totals {{ margin-top: 8px; width: 40%; margin-left: 60%; }}
  .totals td {{ border: 0; padding: 4px 0; }}
  .grand td {{ font-size: 14pt; border-top: 1px solid #333; padding-top: 10px; }}
</style>
<h1>INVOICE</h1>
<div class="row">
  <div><span class="muted">From</span><br><b>{esc(inv.vendor_name)}</b><br>
    {esc(vendor.address)}<br>{esc(vendor.city)}<br>VAT {esc(inv.vendor_tax_id)}</div>
  <div><span class="muted">Billed to</span><br><b>{BUYER["name"]}</b><br>
    {BUYER["address"]}<br>{BUYER["city"]}</div>
  <div class="n"><span class="muted">Invoice</span><br><b>{esc(inv.invoice_number)}</b><br>
    <span class="muted">Date</span><br>{date_en(inv.issue_date)}</div>
</div>
<table>
  <thead><tr><th>Item</th><th class="n">Qty</th><th class="n">Price</th>
    <th class="n">Amount</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<table class="totals">
  <tr><td>Subtotal</td><td class="n">€{money_eu(inv.subtotal)}</td></tr>
  <tr><td>VAT {qty(inv.tax_rate)}%</td><td class="n">€{money_eu(inv.tax_amount)}</td></tr>
  <tr class="grand"><td><b>Total</b></td><td class="n"><b>€{money_eu(inv.total)}</b></td></tr>
</table>
<p style="margin-top:40px;color:#999;font-size:9pt">Thank you!
· {vendor.extra.get("email", "")}</p>
"""
