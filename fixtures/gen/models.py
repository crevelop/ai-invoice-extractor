"""Truth-sidecar models.

InvoiceTruth mirrors the Iberia profile schema from SPEC.md §4 — kept in sync
by hand until `profiles/iberia_invoice.py` exists (build step 3), at which
point the eval runner compares extracted objects against these sidecars.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class LineItem(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal


class InvoiceTruth(BaseModel):
    vendor_name: str
    vendor_tax_id: str
    invoice_number: str
    issue_date: date
    due_date: date | None
    currency: Literal["EUR", "USD", "CNY"]
    line_items: list[LineItem]
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    reverse_charge: bool


class TruthDoc(BaseModel):
    """One sidecar per PDF. Reject docs carry no invoices; multi-invoice PDFs
    carry several."""

    kind: Literal["invoice", "reject"]
    document_type: Literal["invoice", "statement", "quote"]
    invoices: list[InvoiceTruth] = []
