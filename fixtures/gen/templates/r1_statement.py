"""R1 — Account statement (extracto de cuenta). Same letterhead style as a
vendor invoice, lists invoice numbers and amounts — but it is NOT an invoice.
The gate must REJECT it, not extract from it."""

import random
from datetime import date, timedelta
from decimal import Decimal

from ..data import BUYER, Vendor
from .common import date_es, esc, money_eu

TEMPLATE_ID = "r1_statement"
TAGS = ["es", "reject", "statement"]


def build(rng: random.Random, vendor: Vendor) -> str:
    as_of = date(2026, rng.randint(4, 6), rng.randint(10, 28))
    rows, balance = [], Decimal("0")
    for i in range(rng.randint(5, 8)):
        amt = (Decimal(rng.randint(18000, 240000)) / 100).quantize(Decimal("0.01"))
        paid = rng.random() < 0.5
        if not paid:
            balance += amt
        d = as_of - timedelta(days=rng.randint(5, 120))
        rows.append(
            f"<tr><td>{date_es(d)}</td><td>F-2026-{rng.randint(100, 999):04d}</td>"
            f"<td>Factura</td><td class='n'>{money_eu(amt)} €</td>"
            f"<td class='n'>{'0,00 €' if paid else money_eu(amt) + ' €'}</td>"
            f"<td>{'Pagada' if paid else 'Pendiente'}</td></tr>"
        )
    return f"""
<style>
  @page {{ size: A4; margin: 18mm; }}
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #1d2733; }}
  .band {{ background: #475569; color: white; padding: 14px 18px; border-radius: 6px;
           display: flex; justify-content: space-between; align-items: baseline; }}
  .band h1 {{ margin: 0; font-size: 17pt; letter-spacing: 1px; }}
  .meta {{ margin: 18px 0; display: flex; justify-content: space-between; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; font-size: 8pt; text-transform: uppercase;
        border-bottom: 2px solid #475569; padding: 6px 8px; color: #475569; }}
  td {{ padding: 7px 8px; border-bottom: 1px solid #e2e8f0; }}
  .n {{ text-align: right; }}
  .bal {{ margin-top: 14px; text-align: right; font-size: 13pt; }}
  .note {{ margin-top: 20px; font-size: 9pt; color: #64748b; }}
</style>
<div class="band"><h1>EXTRACTO DE CUENTA</h1><div>a {date_es(as_of)}</div></div>
<div class="meta">
  <div><b>{esc(vendor.name)}</b><br>CIF: {esc(vendor.tax_id)}<br>
    {esc(vendor.address)}<br>{esc(vendor.city)}</div>
  <div><b>Cliente:</b> {BUYER["name"]}<br>CIF: {BUYER["tax_id"]}<br>
    {BUYER["address"]}<br>{BUYER["city"]}</div>
</div>
<table>
  <thead><tr><th>Fecha</th><th>Documento</th><th>Tipo</th><th class="n">Importe</th>
    <th class="n">Pendiente</th><th>Estado</th></tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>
<div class="bal">Saldo pendiente: <b>{money_eu(balance)} €</b></div>
<p class="note">Este documento es un extracto informativo de su cuenta a la fecha
indicada. <b>No es una factura</b> ni un documento con validez fiscal. Las facturas
originales fueron remitidas en su momento.</p>
"""
