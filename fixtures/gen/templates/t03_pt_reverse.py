"""T3 — Portuguese supplier, intra-EU reverse charge (autoliquidação):
zero tax + legal note the extractor must map to reverse_charge=True."""

from ..data import BUYER, Vendor
from ..models import InvoiceTruth
from .common import date_es as date_pt  # dd/mm/yyyy in Portugal too
from .common import esc, money_eu, qty

TEMPLATE_ID = "t03_pt_reverse"
TAGS = ["pt", "eur", "eu_decimals", "reverse_charge"]


def build(inv: InvoiceTruth, vendor: Vendor) -> str:
    rows = "".join(
        f"<tr><td>{esc(li.description)}</td><td class='n'>{qty(li.quantity)}</td>"
        f"<td class='n'>{money_eu(li.unit_price)}</td><td class='n'>0%</td>"
        f"<td class='n'>{money_eu(li.total)}</td></tr>"
        for li in inv.line_items
    )
    return f"""
<style>
  @page {{ size: A4; margin: 20mm; }}
  body {{ font-family: 'Trebuchet MS', Verdana, sans-serif; font-size: 9.5pt; color: #263238; }}
  header {{ border-bottom: 3px double #2e7d32; padding-bottom: 10px;
            display: flex; justify-content: space-between; }}
  header .co {{ font-size: 15pt; color: #2e7d32; font-weight: bold; }}
  .doc {{ text-align: right; }}
  .doc .t {{ font-size: 12pt; font-weight: bold; }}
  .grid {{ display: flex; justify-content: space-between; margin: 16px 0; }}
  .grid h4 {{ margin: 0 0 3px; color: #2e7d32; font-size: 8pt;
              text-transform: uppercase; }}
  table.items {{ width: 100%; border-collapse: collapse; }}
  .items th {{ background: #2e7d32; color: white; padding: 6px; font-size: 8.5pt;
               text-align: left; }}
  .items td {{ padding: 6px; border-bottom: 1px dotted #9e9e9e; }}
  .n {{ text-align: right; }}
  .tot {{ margin-top: 12px; margin-left: 50%; width: 50%; border-collapse: collapse; }}
  .tot td {{ padding: 4px 8px; }}
  .tot .g td {{ font-weight: bold; font-size: 12pt; border-top: 2px solid #2e7d32; }}
  .legal {{ margin-top: 16px; padding: 8px 10px; background: #f1f8e9;
            border-left: 4px solid #2e7d32; font-size: 8.5pt; }}
  footer {{ margin-top: 20px; font-size: 8pt; color: #607d8b; }}
</style>
<header>
  <div><span class="co">{esc(inv.vendor_name)}</span><br>
    {esc(vendor.address)}<br>{esc(vendor.city)}<br>NIF: {esc(inv.vendor_tax_id)}</div>
  <div class="doc"><span class="t">FATURA</span><br>N.º {esc(inv.invoice_number)}<br>
    Data de emissão: {date_pt(inv.issue_date)}<br>
    Data de vencimento: {date_pt(inv.due_date) if inv.due_date else "—"}</div>
</header>
<div class="grid">
  <div><h4>Cliente</h4><b>{BUYER["name"]}</b><br>{BUYER["address"]}<br>
    {BUYER["city"]}<br>NIF: {BUYER["tax_id"]} (Espanha)</div>
  <div><h4>Condições</h4>Moeda: EUR<br>Pagamento: transferência bancária<br>
    IBAN: {vendor.extra.get("iban", "")}</div>
</div>
<table class="items">
  <thead><tr><th>Descrição</th><th class="n">Qtd.</th><th class="n">Preço unit. €</th>
    <th class="n">IVA</th><th class="n">Total €</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<table class="tot">
  <tr><td>Subtotal</td><td class="n">{money_eu(inv.subtotal)} €</td></tr>
  <tr><td>IVA (0%)</td><td class="n">{money_eu(inv.tax_amount)} €</td></tr>
  <tr class="g"><td>TOTAL A PAGAR</td><td class="n">{money_eu(inv.total)} €</td></tr>
</table>
<div class="legal"><b>IVA — autoliquidação.</b> Aplicação do artigo 6.º do CIVA e do
artigo 196.º da Diretiva 2006/112/CE (transmissão intracomunitária — reverse charge).
O adquirente é o devedor do imposto.</div>
<footer>{vendor.extra.get("email", "")} · Capital social 50.000 € ·
Conservatória do Registo Comercial da Maia</footer>
"""
