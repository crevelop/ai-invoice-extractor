"""The schema-swap demo (chapter 6): same engine, different document type.

A delivery note (albarán) lists what arrived — quantities but NO prices.
This file is EVERYTHING the pipeline knows about delivery notes: a 5-field
schema, two rules, a gate policy. Swap this object for IBERIA_INVOICE and
the same engine reads a different document.
"""

from datetime import date

from pydantic import BaseModel, Field

from extractor import DocumentProfile, GatePolicy, Numeric, Rule


class DeliveryLine(BaseModel):
    description: str = Field(
        description="The article text from the description column only — "
                    "never append the quantity")
    quantity: Numeric


class DeliveryNote(BaseModel):
    supplier_name: str = Field(
        description="Legal name of the party that ISSUED the note — "
                    "letterhead, logo, stamp — never the recipient")
    delivery_note_number: str = Field(description="Exactly as printed, "
                                                  "incl. prefixes")
    delivery_date: date
    order_reference: str | None = Field(
        description="The purchase-order number this delivery fulfils; "
                    "null if none is shown")
    line_items: list[DeliveryLine]


def _has_lines(note: DeliveryNote) -> str | None:
    if not note.line_items:
        return "a delivery note with nothing delivered"
    return None


def _positive_quantities(note: DeliveryNote) -> str | None:
    bad = [li.description for li in note.line_items if li.quantity <= 0]
    if bad:
        return f"non-positive quantity on: {', '.join(bad)}"
    return None


DELIVERY_NOTE = DocumentProfile(
    schema=DeliveryNote,
    document_type="delivery note",
    rules=(
        Rule("has-line-items", _has_lines, fields=("line_items",)),
        Rule("positive-quantities", _positive_quantities,
             fields=("line_items",)),
    ),
    gate=GatePolicy(
        # A delivery you can't match to an order needs a human anyway, so
        # order_reference is critical even though the schema allows null.
        critical_fields=("delivery_note_number", "order_reference",
                         "supplier_name"),
        min_critical_confidence="medium",
    ),
)
