"""T4 — German supplier (DIN-letter style), reverse charge §13b UStG.
German dates (dd.mm.yyyy), German decimals, German field names."""

from ..data import BUYER, Vendor
from ..models import InvoiceTruth
from .common import date_de, esc, money_eu, qty

TEMPLATE_ID = "t04_de_reverse"
TAGS = ["de", "eur", "eu_decimals", "reverse_charge"]


def build(inv: InvoiceTruth, vendor: Vendor) -> str:
    rows = "".join(
        f"<tr><td>{i + 1}</td><td>{esc(li.description)}</td>"
        f"<td class='n'>{qty(li.quantity)} Stk.</td>"
        f"<td class='n'>{money_eu(li.unit_price)}</td>"
        f"<td class='n'>{money_eu(li.total)}</td></tr>"
        for i, li in enumerate(inv.line_items)
    )
    return f"""
<style>
  @page {{ size: A4; margin: 22mm 20mm; }}
  body {{ font-family: 'Arial', 'Helvetica Neue', sans-serif; font-size: 10pt; color: #000; }}
  .sender {{ font-size: 7pt; text-decoration: underline; margin-bottom: 6px; }}
  .win {{ width: 85mm; min-height: 30mm; }}
  .infoblock {{ float: right; width: 60mm; margin-top: -34mm; font-size: 9pt; }}
  .infoblock td {{ padding: 1px 4px; }}
  h1 {{ font-size: 13pt; margin: 18mm 0 4mm; clear: both; }}
  table.items {{ width: 100%; border-collapse: collapse; margin-top: 4mm; }}
  .items th {{ border-top: 1.5px solid #000; border-bottom: 1.5px solid #000;
               text-align: left; padding: 5px 6px; font-size: 9pt; }}
  .items td {{ padding: 5px 6px; border-bottom: 0.5px solid #999; }}
  .n {{ text-align: right; }}
  .tot {{ width: 60%; margin-left: 40%; border-collapse: collapse; margin-top: 5mm; }}
  .tot td {{ padding: 3px 6px; }}
  .tot .g td {{ border-top: 1.5px solid #000; border-bottom: 3px double #000;
                font-weight: bold; }}
  .hint {{ margin-top: 8mm; font-size: 9pt; }}
  footer {{ position: fixed; bottom: 8mm; left: 0; right: 0; font-size: 7pt;
            color: #444; border-top: 0.5px solid #999; padding-top: 2mm; }}
</style>
<div class="sender">{esc(inv.vendor_name)} · {esc(vendor.address)} · {esc(vendor.city)}</div>
<div class="win"><b>{BUYER["name"]}</b><br>{BUYER["address"]}<br>{BUYER["city"]}<br>Spanien
  <br><br>USt-IdNr. des Kunden: {BUYER["tax_id"]}</div>
<table class="infoblock">
  <tr><td>Rechnungs-Nr.:</td><td><b>{esc(inv.invoice_number)}</b></td></tr>
  <tr><td>Rechnungsdatum:</td><td>{date_de(inv.issue_date)}</td></tr>
  <tr><td>Fällig am:</td><td>{date_de(inv.due_date) if inv.due_date else "—"}</td></tr>
  <tr><td>Kunden-Nr.:</td><td>K-40217</td></tr>
  <tr><td>USt-IdNr.:</td><td>{esc(inv.vendor_tax_id)}</td></tr>
</table>
<h1>Rechnung {esc(inv.invoice_number)}</h1>
<table class="items">
  <thead><tr><th>Pos.</th><th>Bezeichnung</th><th class="n">Menge</th>
    <th class="n">Einzelpreis €</th><th class="n">Gesamt €</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<table class="tot">
  <tr><td>Nettobetrag</td><td class="n">{money_eu(inv.subtotal)} €</td></tr>
  <tr><td>Umsatzsteuer (0&nbsp;%)</td><td class="n">{money_eu(inv.tax_amount)} €</td></tr>
  <tr class="g"><td>Rechnungsbetrag</td><td class="n">{money_eu(inv.total)} €</td></tr>
</table>
<p class="hint">Steuerfreie innergemeinschaftliche Lieferung. <b>Steuerschuldnerschaft
des Leistungsempfängers (Reverse-Charge-Verfahren)</b> gemäß §&nbsp;13b UStG bzw.
Art.&nbsp;196 MwStSystRL. Zahlbar ohne Abzug auf: {vendor.extra.get("iban", "")}.</p>
<footer>{esc(inv.vendor_name)} · {vendor.extra.get("hrb", "")} ·
Geschäftsführerin: Petra Willems · USt-IdNr. {esc(inv.vendor_tax_id)}</footer>
"""
