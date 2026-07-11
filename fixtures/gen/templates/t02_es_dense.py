"""T2 — Spanish traditional dense layout: serif, boxed, busy. EU decimals,
some docs at 10% IVA (mixed-rate coverage)."""

from ..data import BUYER, Vendor
from ..models import InvoiceTruth
from .common import date_es, esc, money_eu, qty

TEMPLATE_ID = "t02_es_dense"
TAGS = ["es", "eur", "eu_decimals", "dense_layout"]


def build(inv: InvoiceTruth, vendor: Vendor) -> str:
    rows = "".join(
        f"<tr><td>ART-{2400 + i * 7}</td><td>{esc(li.description)}</td>"
        f"<td class='n'>{qty(li.quantity)}</td><td class='n'>{money_eu(li.unit_price)}</td>"
        f"<td class='n'>0,00</td><td class='n'>{money_eu(li.total)}</td></tr>"
        for i, li in enumerate(inv.line_items)
    )
    return f"""
<style>
  @page {{ size: A4; margin: 14mm; }}
  body {{ font-family: Georgia, 'Times New Roman', serif; font-size: 9pt; color: #111; }}
  .head {{ border: 2px solid #111; padding: 8px 12px; display: flex;
           justify-content: space-between; }}
  .head .co {{ font-size: 13pt; font-weight: bold; }}
  .docbox {{ border: 2px solid #111; border-top: 0; padding: 6px 12px;
             display: flex; justify-content: space-between; background: #f2efe9; }}
  .parties {{ display: flex; margin-top: 10px; gap: 10px; }}
  .parties div {{ border: 1px solid #111; padding: 8px 10px; flex: 1; }}
  .parties h4 {{ margin: 0 0 4px; font-size: 8pt; border-bottom: 1px solid #111; }}
  table.items {{ width: 100%; border-collapse: collapse; margin-top: 10px;
                 border: 1px solid #111; }}
  .items th, .items td {{ border: 1px solid #555; padding: 4px 6px; }}
  .items th {{ background: #f2efe9; font-size: 8pt; }}
  .n {{ text-align: right; }}
  .sum {{ margin-top: 10px; width: 100%; border-collapse: collapse; }}
  .sum td {{ border: 1px solid #111; padding: 5px 8px; }}
  .sum .lbl {{ background: #f2efe9; font-size: 8pt; }}
  footer {{ margin-top: 14px; font-size: 7.5pt; }}
</style>
<div class="head">
  <div class="co">{esc(inv.vendor_name)}<br>
    <span style="font-size:8pt;font-weight:normal">{esc(vendor.address)} ·
    {esc(vendor.city)}<br>C.I.F.: {esc(inv.vendor_tax_id)} ·
    Tel. {vendor.extra.get("phone", "")}</span></div>
  <div style="text-align:right">FACTURA<br><b style="font-size:14pt">
    {esc(inv.invoice_number)}</b></div>
</div>
<div class="docbox">
  <span>Fecha factura: <b>{date_es(inv.issue_date)}</b></span>
  <span>Forma de pago: Transferencia</span>
  <span>Vencimiento: <b>{date_es(inv.due_date) if inv.due_date else "—"}</b></span>
</div>
<div class="parties">
  <div><h4>DATOS DEL CLIENTE</h4><b>{BUYER["name"]}</b><br>{BUYER["address"]}<br>
    {BUYER["city"]}<br>C.I.F.: {BUYER["tax_id"]}</div>
  <div><h4>ENVIAR A</h4>{BUYER["name"]}<br>Almacén central<br>{BUYER["address"]}<br>
    {BUYER["city"]}</div>
</div>
<table class="items">
  <thead><tr><th>Ref.</th><th>Descripción</th><th class="n">Cantidad</th>
    <th class="n">Precio</th><th class="n">Dto. %</th><th class="n">Importe €</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<table class="sum"><tr>
  <td class="lbl">BASE IMPONIBLE</td><td class="n">{money_eu(inv.subtotal)} €</td>
  <td class="lbl">% IVA</td><td class="n">{qty(inv.tax_rate)}%</td>
  <td class="lbl">CUOTA IVA</td><td class="n">{money_eu(inv.tax_amount)} €</td>
  <td class="lbl"><b>TOTAL FACTURA</b></td>
  <td class="n" style="font-size:12pt"><b>{money_eu(inv.total)} €</b></td>
</tr></table>
<footer>Domiciliación bancaria: {vendor.extra.get("iban", "")}. Operación sujeta a IVA.
Inscrita en el Registro Mercantil de Valencia, Tomo 4.812, Folio 33.</footer>
"""
