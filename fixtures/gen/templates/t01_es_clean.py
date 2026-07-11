"""T1 — Spanish modern/clean layout. Baseline case + European decimals."""

from ..data import BUYER, Vendor
from ..models import InvoiceTruth
from .common import date_es, esc, money_eu, qty

TEMPLATE_ID = "t01_es_clean"
TAGS = ["es", "eur", "eu_decimals"]


def build(inv: InvoiceTruth, vendor: Vendor) -> str:
    rows = "".join(
        f"<tr><td>{esc(li.description)}</td><td class='n'>{qty(li.quantity)}</td>"
        f"<td class='n'>{money_eu(li.unit_price)} €</td>"
        f"<td class='n'>{money_eu(li.total)} €</td></tr>"
        for li in inv.line_items
    )
    return f"""
<style>
  @page {{ size: A4; margin: 18mm; }}
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #1d2733; }}
  .band {{ background: #0e7490; color: white; padding: 14px 18px; border-radius: 6px;
           display: flex; justify-content: space-between; align-items: baseline; }}
  .band h1 {{ margin: 0; font-size: 20pt; letter-spacing: 2px; }}
  .meta {{ display: flex; justify-content: space-between; margin: 22px 0; }}
  .meta h3 {{ margin: 0 0 4px; font-size: 8pt; text-transform: uppercase; color: #0e7490; }}
  table.items {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  .items th {{ text-align: left; font-size: 8pt; text-transform: uppercase;
               border-bottom: 2px solid #0e7490; padding: 6px 8px; color: #0e7490; }}
  .items td {{ padding: 7px 8px; border-bottom: 1px solid #e2e8f0; }}
  .n {{ text-align: right; }}
  .totals {{ width: 45%; margin-left: 55%; margin-top: 14px; border-collapse: collapse; }}
  .totals td {{ padding: 5px 8px; }}
  .totals .grand {{ font-size: 13pt; font-weight: bold; background: #ecfeff;
                    border-top: 2px solid #0e7490; }}
  footer {{ margin-top: 30px; font-size: 8pt; color: #64748b; }}
</style>
<div class="band"><h1>FACTURA</h1><div>{esc(inv.invoice_number)}</div></div>
<div class="meta">
  <div><h3>Emisor</h3><b>{esc(inv.vendor_name)}</b><br>
    CIF: {esc(inv.vendor_tax_id)}<br>{esc(vendor.address)}<br>{esc(vendor.city)}</div>
  <div><h3>Cliente</h3><b>{BUYER["name"]}</b><br>
    CIF: {BUYER["tax_id"]}<br>{BUYER["address"]}<br>{BUYER["city"]}</div>
  <div><h3>Datos</h3>
    Fecha de emisión: <b>{date_es(inv.issue_date)}</b><br>
    Vencimiento: <b>{date_es(inv.due_date) if inv.due_date else "—"}</b><br>
    Moneda: EUR</div>
</div>
<table class="items">
  <thead><tr><th>Concepto</th><th class="n">Cant.</th><th class="n">Precio ud.</th>
  <th class="n">Importe</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<table class="totals">
  <tr><td>Base imponible</td><td class="n">{money_eu(inv.subtotal)} €</td></tr>
  <tr><td>IVA ({qty(inv.tax_rate)}%)</td><td class="n">{money_eu(inv.tax_amount)} €</td></tr>
  <tr class="grand"><td>TOTAL</td><td class="n">{money_eu(inv.total)} €</td></tr>
</table>
<footer>Pago por transferencia a {vendor.extra.get("iban", "")} ·
{vendor.extra.get("email", "")} · Inscrita en el Registro Mercantil de Zaragoza</footer>
"""
