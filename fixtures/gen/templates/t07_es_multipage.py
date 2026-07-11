"""T7 — Multi-page Spanish invoice: 48–95 line items flow over 2–3 A4 pages,
repeating table header + page counter. Totals appear only on the last page."""

from ..data import BUYER, Vendor
from ..models import InvoiceTruth
from .common import date_es, esc, money_eu, qty

TEMPLATE_ID = "t07_es_multipage"
TAGS = ["es", "eur", "eu_decimals", "multi_page"]


def build(inv: InvoiceTruth, vendor: Vendor) -> str:
    rows = "".join(
        f"<tr><td>{i + 1:03d}</td><td>{esc(li.description)}</td>"
        f"<td class='n'>{qty(li.quantity)}</td><td class='n'>{money_eu(li.unit_price)}</td>"
        f"<td class='n'>{money_eu(li.total)}</td></tr>"
        for i, li in enumerate(inv.line_items)
    )
    return f"""
<style>
  @page {{
    size: A4; margin: 16mm 16mm 22mm;
    @bottom-right {{ content: "Página " counter(page) " de " counter(pages);
                     font-size: 8pt; color: #555; font-family: Helvetica, sans-serif; }}
    @bottom-left {{ content: "{esc(inv.vendor_name)} — Factura {esc(inv.invoice_number)}";
                    font-size: 8pt; color: #555; font-family: Helvetica, sans-serif; }}
  }}
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #17202a; }}
  header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #5b2c6f;
            padding-bottom: 8px; }}
  header .co {{ font-size: 14pt; font-weight: bold; color: #5b2c6f; }}
  .meta {{ display: flex; justify-content: space-between; margin: 12px 0; }}
  .meta h4 {{ margin: 0 0 3px; font-size: 7.5pt; color: #5b2c6f;
              text-transform: uppercase; }}
  table.items {{ width: 100%; border-collapse: collapse; }}
  .items thead {{ display: table-header-group; }}
  .items th {{ background: #5b2c6f; color: white; padding: 5px 6px; font-size: 8pt;
               text-align: left; }}
  .items td {{ padding: 4px 6px; border-bottom: 0.5px solid #d5d8dc; }}
  .n {{ text-align: right; }}
  .tot {{ margin-top: 10px; margin-left: 55%; width: 45%; border-collapse: collapse;
          page-break-inside: avoid; }}
  .tot td {{ padding: 4px 8px; }}
  .tot .g td {{ font-weight: bold; font-size: 12pt; background: #f4ecf7;
                border-top: 2px solid #5b2c6f; }}
</style>
<header>
  <div><span class="co">{esc(inv.vendor_name)}</span><br>
    {esc(vendor.address)} · {esc(vendor.city)} · CIF {esc(inv.vendor_tax_id)}</div>
  <div style="text-align:right">FACTURA<br><b style="font-size:13pt">
    {esc(inv.invoice_number)}</b></div>
</header>
<div class="meta">
  <div><h4>Cliente</h4><b>{BUYER["name"]}</b> · CIF {BUYER["tax_id"]}<br>
    {BUYER["address"]} · {BUYER["city"]}</div>
  <div><h4>Fechas</h4>Emisión: <b>{date_es(inv.issue_date)}</b> ·
    Vencimiento: <b>{date_es(inv.due_date) if inv.due_date else "—"}</b></div>
  <div><h4>Pago</h4>Transferencia · {vendor.extra.get("iban", "")}</div>
</div>
<table class="items">
  <thead><tr><th>Línea</th><th>Descripción</th><th class="n">Cant.</th>
    <th class="n">Precio €</th><th class="n">Importe €</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<table class="tot">
  <tr><td>Base imponible</td><td class="n">{money_eu(inv.subtotal)} €</td></tr>
  <tr><td>IVA {qty(inv.tax_rate)}%</td><td class="n">{money_eu(inv.tax_amount)} €</td></tr>
  <tr class="g"><td>TOTAL FACTURA</td><td class="n">{money_eu(inv.total)} €</td></tr>
</table>
"""
