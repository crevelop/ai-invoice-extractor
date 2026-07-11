"""Validation & gate tests — the deterministic half of the pipeline.
No API calls: rules and the gate are plain code, so they get plain tests."""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from extractor import Decision, decide, normalize_amount, run_rules  # noqa: E402
from profiles.iberia_invoice import (  # noqa: E402
    IBERIA_INVOICE,
    IberiaInvoice,
    LineItem,
    duplicate_rule,
)


def valid_invoice(**overrides) -> IberiaInvoice:
    base = dict(
        vendor_name="Cocinas del Ebro, S.L.",
        vendor_tax_id="ESB50823176",
        invoice_number="F-2026-0047",
        issue_date=date(2026, 5, 4),
        due_date=date(2026, 7, 3),
        currency="EUR",
        line_items=[
            LineItem(description="Ensaladera", quantity=2,
                     unit_price=Decimal("50.00"), total=Decimal("100.00")),
            LineItem(description="Vajilla", quantity=1,
                     unit_price=Decimal("23.45"), total=Decimal("23.45")),
        ],
        subtotal=Decimal("123.45"),
        tax_rate=Decimal("21"),
        tax_amount=Decimal("25.92"),
        total=Decimal("149.37"),
        reverse_charge=False,
    )
    return IberiaInvoice(**{**base, **overrides})


def failed_rules(inv: IberiaInvoice) -> set[str]:
    return {r.rule for r in run_rules(inv, IBERIA_INVOICE.rules) if not r.passed}


# ── locale-aware amount normalization


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.234,56", "1234.56"),  # European
        ("1,234.56", "1234.56"),  # US
        ("€ 1 234,56", "1234.56"),  # currency symbol + thin spaces
        ("1234,56", "1234.56"),  # bare decimal comma
        ("1,234,567", "1234567"),  # thousands commas only
        ("1.234.567", "1234567"),  # thousands dots only
        ("-42,10", "-42.10"),
        ("99.95", "99.95"),  # already fine
    ],
)
def test_normalize_amount(raw, expected):
    assert normalize_amount(raw) == expected


def test_normalize_amount_passes_non_strings_through():
    assert normalize_amount(Decimal("12.30")) == Decimal("12.30")


def test_money_field_accepts_european_string():
    li = LineItem(description="x", quantity=1,
                  unit_price="1.234,56", total="1.234,56")
    assert li.total == Decimal("1234.56")


# ── the Iberia business rules


def test_valid_invoice_passes_every_rule():
    assert failed_rules(valid_invoice()) == set()


def test_wrong_digit_in_total_breaks_the_math():
    inv = valid_invoice().model_copy(update={"total": Decimal("749.37")})
    assert "subtotal-plus-tax-is-total" in failed_rules(inv)


def test_line_items_must_sum_to_subtotal():
    inv = valid_invoice(subtotal=Decimal("200.00"),
                        tax_amount=Decimal("42.00"), total=Decimal("242.00"))
    assert "line-items-sum-to-subtotal" in failed_rules(inv)


def test_cent_rounding_tolerance_is_allowed():
    inv = valid_invoice(subtotal=Decimal("123.44"), total=Decimal("149.36"))
    assert "line-items-sum-to-subtotal" not in failed_rules(inv)


def test_tax_must_match_rate():
    inv = valid_invoice(tax_amount=Decimal("10.00"), total=Decimal("133.45"))
    assert "tax-matches-rate" in failed_rules(inv)


def test_reverse_charge_means_zero_tax():
    inv = valid_invoice(reverse_charge=True)
    fails = failed_rules(inv)
    assert "reverse-charge-means-zero-tax" in fails
    assert "tax-matches-rate" not in fails  # skipped under reverse charge


def test_due_date_before_issue_date_fails():
    inv = valid_invoice(due_date=date(2026, 4, 1))
    assert "due-date-not-before-issue-date" in failed_rules(inv)


def test_missing_due_date_is_fine():
    assert failed_rules(valid_invoice(due_date=None)) == set()


@pytest.mark.parametrize(
    "tax_id", ["ESB50823176", "DE812940517", "PT509884217",
               "91440101MA9W2XK37L"],
)
def test_known_tax_id_formats_pass(tax_id):
    assert "vendor-tax-id-format" not in failed_rules(
        valid_invoice(vendor_tax_id=tax_id))


def test_garbage_tax_id_fails():
    assert "vendor-tax-id-format" in failed_rules(
        valid_invoice(vendor_tax_id="B-508.231"))


def test_duplicate_rule_flags_second_sighting():
    rule = duplicate_rule(set())
    inv = valid_invoice()
    assert rule.check(inv) is None
    assert "already processed" in rule.check(inv)


# ── the gate


def all_high() -> dict[str, str]:
    return {name: "high" for name in IberiaInvoice.model_fields}


def test_gate_auto_accepts_clean_result():
    checks = run_rules(valid_invoice(), IBERIA_INVOICE.rules)
    decision, reasons = decide(IBERIA_INVOICE, "invoice", all_high(), checks)
    assert decision is Decision.AUTO_ACCEPT
    assert reasons == []


def test_gate_reviews_on_rule_failure():
    inv = valid_invoice().model_copy(update={"total": Decimal("749.37")})
    checks = run_rules(inv, IBERIA_INVOICE.rules)
    decision, reasons = decide(IBERIA_INVOICE, "invoice", all_high(), checks)
    assert decision is Decision.NEEDS_REVIEW
    assert any("subtotal-plus-tax-is-total" in r for r in reasons)


def test_gate_reviews_low_confidence_critical_field():
    checks = run_rules(valid_invoice(), IBERIA_INVOICE.rules)
    confidence = all_high() | {"total": "low"}
    decision, reasons = decide(IBERIA_INVOICE, "invoice", confidence, checks)
    assert decision is Decision.NEEDS_REVIEW
    assert "critical field 'total' has low confidence" in reasons


def test_gate_ignores_low_confidence_on_non_critical_field():
    checks = run_rules(valid_invoice(), IBERIA_INVOICE.rules)
    confidence = all_high() | {"due_date": "low"}
    decision, _ = decide(IBERIA_INVOICE, "invoice", confidence, checks)
    assert decision is Decision.AUTO_ACCEPT


def test_gate_rejects_wrong_document_type():
    decision, reasons = decide(IBERIA_INVOICE, "quote", {}, [], has_data=False)
    assert decision is Decision.REJECT
    assert "looks like 'quote'" in reasons[0]


def test_gate_rejects_when_no_data_extracted():
    decision, _ = decide(IBERIA_INVOICE, "invoice", {}, [], has_data=False)
    assert decision is Decision.REJECT
