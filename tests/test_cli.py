"""CLI tests — everything except the API call: argument surface, profile
loading, JSON serialization. No key needed."""

import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractor import Cost, Decision, Document, ExtractionResult, FieldMeta  # noqa: E402
from extractor.__main__ import EXIT_CODES, as_json, load_profile  # noqa: E402
from profiles.iberia_invoice import IBERIA_INVOICE, IberiaInvoice, LineItem  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_help_runs_without_a_key():
    done = subprocess.run(
        [sys.executable, "-m", "extractor", "--help"],
        cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0
    assert "AUTO_ACCEPT" in done.stdout


def test_default_profile_spec_resolves_to_the_iberia_example():
    assert load_profile("profiles.iberia_invoice:IBERIA_INVOICE") is IBERIA_INVOICE


def test_exit_codes_mirror_the_decision():
    assert EXIT_CODES[Decision.AUTO_ACCEPT] == 0
    assert EXIT_CODES[Decision.NEEDS_REVIEW] == 1
    assert EXIT_CODES[Decision.REJECT] == 2


def test_json_output_is_valid_and_complete():
    result = ExtractionResult(
        document=Document(source="doc.pdf", kind="text", text="…"),
        data=IberiaInvoice(
            vendor_name="Cocinas del Ebro, S.L.",
            vendor_tax_id="ESB50823176",
            invoice_number="F-2026-0047",
            issue_date=date(2026, 5, 4),
            due_date=None,
            currency="EUR",
            line_items=[LineItem(description="Ensaladera", quantity=1,
                                 unit_price=Decimal("123.45"),
                                 total=Decimal("123.45"))],
            subtotal=Decimal("123.45"),
            tax_rate=Decimal("21"),
            tax_amount=Decimal("25.92"),
            total=Decimal("149.37"),
            reverse_charge=False,
        ),
        document_type="invoice",
        field_meta={"total": FieldMeta(confidence="low",
                                       flags=["verifier read '149.38'"])},
        validation=[],
        cost=Cost(input_tokens=10, output_tokens=5, usd=0.001),
        decision=Decision.NEEDS_REVIEW,
        reasons=["critical field 'total' has low confidence"],
    )
    parsed = json.loads(as_json(result))
    assert parsed["decision"] == "NEEDS_REVIEW"
    assert parsed["data"]["total"] == "149.37"  # Decimal survives as string
    assert parsed["fields"]["total"]["flags"] == ["verifier read '149.38'"]
    assert parsed["cost"]["usd"] == 0.001
