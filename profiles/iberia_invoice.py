"""The worked example: Iberia Home Goods, S.L. (SPEC §4).

Barcelona wholesaler, ~800 supplier invoices/month from ~60 vendors across
Spain, Portugal, Germany and China. This file is EVERYTHING that is specific
to their use case — schema, business rules, gate thresholds. The engine
knows none of it.
"""

import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from extractor import DocumentProfile, GatePolicy, Money, Rule

# ── Schema: what to extract. Field descriptions double as extraction
#    instructions — prompt engineering living inside the type definition.


class LineItem(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Money = Field(description="Per-unit price before tax")
    total: Money = Field(description="Line total (quantity × unit price)")


class IberiaInvoice(BaseModel):
    vendor_name: str = Field(description="Legal name of the issuing vendor")
    vendor_tax_id: str = Field(
        description="CIF/NIF or EU VAT number (e.g. ESB12345678), or the "
                    "vendor's national tax id for non-EU vendors")
    invoice_number: str = Field(description="Exactly as printed, incl. prefixes")
    issue_date: date
    due_date: date | None = Field(description="null if no due date is shown")
    currency: Literal["EUR", "USD", "CNY"]
    line_items: list[LineItem]
    subtotal: Money = Field(description="Total before tax")
    tax_rate: Decimal = Field(description="IVA/VAT percentage as shown, e.g. 21")
    tax_amount: Money
    total: Money = Field(description="Grand total including tax")
    reverse_charge: bool = Field(
        description="True if an intra-EU reverse-charge VAT note is present")


# ── Rules: deterministic math catches the hallucinated digit. Each returns
#    None (pass) or a failure detail (fail). Amounts compare with a ±0.01
#    tolerance — printed totals are rounded per line.

CENT = Decimal("0.01")


def _line_items_sum(inv: IberiaInvoice) -> str | None:
    lines = sum((li.total for li in inv.line_items), Decimal("0"))
    if abs(lines - inv.subtotal) > CENT:
        return f"line items sum to {lines}, subtotal says {inv.subtotal}"
    return None


def _totals_add_up(inv: IberiaInvoice) -> str | None:
    if abs(inv.subtotal + inv.tax_amount - inv.total) > CENT:
        return (f"subtotal {inv.subtotal} + tax {inv.tax_amount} "
                f"= {inv.subtotal + inv.tax_amount}, total says {inv.total}")
    return None


def _tax_matches_rate(inv: IberiaInvoice) -> str | None:
    if inv.reverse_charge:
        return None  # covered by the reverse-charge rule instead
    expected = (inv.subtotal * inv.tax_rate / 100).quantize(CENT)
    if abs(expected - inv.tax_amount) > Decimal("0.02"):
        return (f"{inv.tax_rate}% of {inv.subtotal} is {expected}, "
                f"tax_amount says {inv.tax_amount}")
    return None


def _reverse_charge_zero_tax(inv: IberiaInvoice) -> str | None:
    if inv.reverse_charge and inv.tax_amount != 0:
        return f"reverse charge but tax_amount is {inv.tax_amount}, not 0"
    return None


def _due_after_issue(inv: IberiaInvoice) -> str | None:
    if inv.due_date is not None and inv.due_date < inv.issue_date:
        return f"due {inv.due_date} before issue {inv.issue_date}"
    return None


# EU VAT / Spanish CIF-NIF (country prefix + 8-12 alphanumerics) or a
# Chinese Unified Social Credit Code (18 alphanumerics).
_TAX_ID = re.compile(r"^(?:[A-Z]{2}[A-Z0-9]{8,12}|[0-9A-Z]{18})$")


def _tax_id_format(inv: IberiaInvoice) -> str | None:
    if not _TAX_ID.match(inv.vendor_tax_id):
        return f"'{inv.vendor_tax_id}' is not a recognized tax id format"
    return None


RULES = (
    Rule("line-items-sum-to-subtotal", _line_items_sum,
         fields=("line_items", "subtotal")),
    Rule("subtotal-plus-tax-is-total", _totals_add_up,
         fields=("subtotal", "tax_amount", "total")),
    Rule("tax-matches-rate", _tax_matches_rate,
         fields=("tax_rate", "tax_amount")),
    Rule("reverse-charge-means-zero-tax", _reverse_charge_zero_tax,
         fields=("reverse_charge", "tax_amount")),
    Rule("due-date-not-before-issue-date", _due_after_issue,
         fields=("issue_date", "due_date")),
    Rule("vendor-tax-id-format", _tax_id_format,
         fields=("vendor_tax_id",)),
)


def duplicate_rule(seen: set[tuple[str, str]]) -> Rule:
    """(vendor_tax_id, invoice_number) must not repeat — the classic
    double-payment bug. Stateful by design: every check registers the
    invoice in `seen`, so build one rule per batch/run."""

    def check(inv: IberiaInvoice) -> str | None:
        key = (inv.vendor_tax_id, inv.invoice_number)
        if key in seen:
            return f"invoice {key[1]} from {key[0]} already processed"
        seen.add(key)
        return None

    return Rule("not-a-duplicate", check,
                fields=("vendor_tax_id", "invoice_number"))


# ── The profile: schema + rules + gate. Swap this object, swap the use case.

IBERIA_INVOICE = DocumentProfile(
    schema=IberiaInvoice,
    document_type="invoice",
    rules=RULES,
    gate=GatePolicy(
        # The fields a wrong value actually costs money on.
        critical_fields=("total", "vendor_tax_id", "invoice_number"),
        min_critical_confidence="medium",  # "low" on any of them -> review
    ),
)
