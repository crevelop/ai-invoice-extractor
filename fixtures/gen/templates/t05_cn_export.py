"""T5 — Chinese exporter commercial invoice in English. US decimal format
(1,234.56), USD/CNY currencies, USCC tax id (not an EU VAT — the Iberia
profile's tax-id regex rule will legitimately flag these; that is realistic,
not a fixture bug)."""

from ..data import BUYER, Vendor
from ..models import InvoiceTruth
from .common import date_en, esc, money_us, qty

TEMPLATE_ID = "t05_cn_export"
TAGS = ["en", "us_decimals", "non_eur"]

SYMBOL = {"USD": "US$", "CNY": "¥", "EUR": "€"}


def build(inv: InvoiceTruth, vendor: Vendor) -> str:
    sym = SYMBOL[inv.currency]
    rows = "".join(
        f"<tr><td>BW-{3100 + i * 13}</td><td>{esc(li.description)}</td>"
        f"<td class='n'>{qty(li.quantity)}</td><td class='n'>{money_us(li.unit_price)}</td>"
        f"<td class='n'>{money_us(li.total)}</td></tr>"
        for i, li in enumerate(inv.line_items)
    )
    return f"""
<style>
  @page {{ size: A4; margin: 16mm; }}
  body {{ font-family: 'Arial', sans-serif; font-size: 9.5pt; color: #202020; }}
  h1 {{ text-align: center; font-size: 15pt; letter-spacing: 4px; margin: 4px 0 2px;
        border-bottom: 3px solid #b71c1c; padding-bottom: 6px; }}
  .co {{ text-align: center; font-size: 11pt; font-weight: bold; color: #b71c1c; }}
  .co small {{ display: block; font-weight: normal; color: #202020; font-size: 8.5pt; }}
  .blocks {{ display: flex; gap: 8px; margin-top: 12px; }}
  .blocks > div {{ border: 1px solid #b71c1c; flex: 1; padding: 6px 8px; }}
  .blocks h4 {{ margin: 0 0 3px; font-size: 8pt; color: #b71c1c;
                text-transform: uppercase; }}
  table.items {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  .items th {{ background: #b71c1c; color: #fff; padding: 6px; font-size: 8.5pt; }}
  .items td {{ border: 1px solid #ccc; padding: 6px; }}
  .n {{ text-align: right; }}
  .tot td {{ padding: 4px 8px; }}
  .tot {{ margin-left: 55%; width: 45%; margin-top: 10px; }}
  .tot .g {{ font-weight: bold; font-size: 12pt; border-top: 2px solid #b71c1c; }}
  .terms {{ margin-top: 14px; font-size: 8.5pt; }}
</style>
<div class="co">{esc(inv.vendor_name)}
  <small>{esc(vendor.address)}, {esc(vendor.city)} ·
  Unified Social Credit Code: {esc(inv.vendor_tax_id)}</small></div>
<h1>COMMERCIAL INVOICE</h1>
<div class="blocks">
  <div><h4>Sold to</h4><b>{BUYER["name"]}</b><br>{BUYER["address"]}<br>
    {BUYER["city"]}<br>VAT: {BUYER["tax_id"]}</div>
  <div><h4>Invoice details</h4>
    Invoice No.: <b>{esc(inv.invoice_number)}</b><br>
    Invoice date: {date_en(inv.issue_date)}<br>
    Due date: {date_en(inv.due_date) if inv.due_date else "As per contract"}<br>
    Currency: <b>{inv.currency}</b></div>
  <div><h4>Shipment</h4>Incoterms: {vendor.extra.get("terms", "")}<br>
    Port of loading: Guangzhou<br>Port of discharge: Barcelona</div>
</div>
<table class="items">
  <thead><tr><th>Item No.</th><th>Description of goods</th><th class="n">Qty (pcs)</th>
    <th class="n">Unit price ({inv.currency})</th><th class="n">Amount ({inv.currency})</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<table class="tot">
  <tr><td>Subtotal</td><td class="n">{sym}{money_us(inv.subtotal)}</td></tr>
  <tr><td>VAT / Tax (0%)</td><td class="n">{sym}{money_us(inv.tax_amount)}</td></tr>
  <tr class="g"><td>TOTAL</td><td class="n">{sym}{money_us(inv.total)}</td></tr>
</table>
<p class="terms"><b>Payment:</b> {vendor.extra.get("terms", "")} ·
<b>Beneficiary bank:</b> {vendor.extra.get("bank", "")}.<br>
Export goods — zero-rated for Chinese VAT. Country of origin: P.R. China.</p>
"""
