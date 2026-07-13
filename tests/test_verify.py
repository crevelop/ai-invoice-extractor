"""Verification-pass tests — the deterministic half of chapter 5.
The second API call itself isn't tested here; the reading comparison, the
merge logic and their effect on the gate are plain code, so they get
plain tests."""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractor import (  # noqa: E402
    Cost,
    Decision,
    FieldMeta,
    decide,
    merge_checks,
)
from profiles.iberia_invoice import (  # noqa: E402
    IBERIA_INVOICE,
    IberiaInvoice,
    LineItem,
)


def valid_invoice() -> IberiaInvoice:
    return IberiaInvoice(
        vendor_name="Cocinas del Ebro, S.L.",
        vendor_tax_id="ESB50823176",
        invoice_number="F-2026-0047",
        issue_date=date(2026, 5, 4),
        due_date=date(2026, 7, 3),
        currency="EUR",
        line_items=[LineItem(description="Ensaladera", quantity=1,
                             unit_price=Decimal("123.45"),
                             total=Decimal("123.45"))],
        subtotal=Decimal("123.45"),
        tax_rate=Decimal("21"),
        tax_amount=Decimal("25.92"),
        total=Decimal("149.37"),
        reverse_charge=False,
    )


def meta_for_critical_fields(confidence: str = "medium") -> dict[str, FieldMeta]:
    return {name: FieldMeta(confidence=confidence)
            for name in IBERIA_INVOICE.gate.critical_fields}


def test_matching_read_raises_confidence():
    meta = meta_for_critical_fields("medium")
    merge_checks(meta, {"total": "149.37"}, valid_invoice())
    assert meta["total"].confidence == "high"
    assert meta["total"].flags == []


def test_mismatch_downgrades_and_flags_with_the_verifier_reading():
    meta = meta_for_critical_fields("high")  # the model felt sure — irrelevant
    merge_checks(meta, {"vendor_tax_id": "DE812940517"}, valid_invoice())
    assert meta["vendor_tax_id"].confidence == "low"
    assert meta["vendor_tax_id"].flags == ["verifier read 'DE812940517'"]


def test_merge_never_touches_other_fields():
    meta = meta_for_critical_fields("medium")
    merge_checks(meta, {"total": "149.37"}, valid_invoice())
    assert meta["invoice_number"].confidence == "medium"


def test_format_differences_are_not_disagreements():
    # The two reads are compared by code, through the schema's own types:
    # '149,37 €' parses to the same Money as '149.37' — agreement, not a
    # flag. Models are bad at string equality; Decimal isn't.
    meta = meta_for_critical_fields("medium")
    merge_checks(meta, {"total": "149,37 €"}, valid_invoice())
    assert meta["total"].confidence == "high"
    assert meta["total"].flags == []


def test_typography_differences_in_names_are_not_disagreements():
    # Same vendor, different typography — casing and punctuation are not
    # a second opinion.
    meta = meta_for_critical_fields("medium")
    merge_checks(meta, {"vendor_name": "COCINAS DEL EBRO SL"}, valid_invoice())
    assert meta["vendor_name"].confidence == "high"
    assert meta["vendor_name"].flags == []


def test_a_different_name_is_a_disagreement():
    meta = meta_for_critical_fields("high")
    merge_checks(meta, {"vendor_name": "Iberia Home Goods, S.L."},
                 valid_invoice())
    assert meta["vendor_name"].confidence == "low"
    assert meta["vendor_name"].flags == ["verifier read 'Iberia Home Goods, S.L.'"]


def test_unparseable_reading_stays_a_disagreement():
    meta = meta_for_critical_fields("high")
    merge_checks(meta, {"total": "illegible"}, valid_invoice())
    assert meta["total"].confidence == "low"


def test_mismatch_forces_needs_review_through_the_gate():
    # The chapter-5 story end to end (minus the API): high self-reported
    # confidence would auto-accept; one verifier mismatch on a critical
    # field downgrades it and the EXISTING gate flips to review.
    meta = {name: FieldMeta(confidence="high")
            for name in IberiaInvoice.model_fields}
    confidence = {name: m.confidence for name, m in meta.items()}
    decision, _ = decide(IBERIA_INVOICE, "invoice", confidence, [])
    assert decision is Decision.AUTO_ACCEPT

    merge_checks(meta, {"vendor_tax_id": "DE812940517"}, valid_invoice())
    confidence = {name: m.confidence for name, m in meta.items()}
    decision, reasons = decide(IBERIA_INVOICE, "invoice", confidence, [])
    assert decision is Decision.NEEDS_REVIEW
    assert "critical field 'vendor_tax_id' has low confidence" in reasons


def test_costs_add_up_across_the_two_calls():
    total = (Cost(input_tokens=1000, output_tokens=200, usd=0.002)
             + Cost(input_tokens=500, output_tokens=50, usd=0.001))
    assert total.input_tokens == 1500
    assert total.output_tokens == 250
    assert total.usd == 0.003
