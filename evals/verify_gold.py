"""Spot-check the gold set against the actual documents. No API calls.

The truth sidecars are generated together with the PDFs, so they are true
by construction — but "the generator says so" is not verification. This
script cross-checks every digital PDF's text layer for the sidecar's
critical values (invoice number, tax id, total). Scanned documents have
no text layer; those get checked by eye (see the printed list).

Run: uv run python evals/verify_gold.py
"""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.harness import load_gold  # noqa: E402
from extractor import load  # noqa: E402


def formats(amount: Decimal) -> list[str]:
    """The ways a total can legitimately appear in print."""
    us = f"{amount:,.2f}"  # 1,110.76
    european = us.replace(",", "X").replace(".", ",").replace("X", ".")
    return [us, european, str(amount)]


def check(text: str, truth) -> list[str]:
    problems = []
    if truth.invoice_number not in text:
        problems.append(f"invoice_number {truth.invoice_number!r} not in text")
    if truth.vendor_tax_id not in text:
        problems.append(f"vendor_tax_id {truth.vendor_tax_id!r} not in text")
    if not any(f in text for f in formats(truth.total)):
        problems.append(f"total {truth.total} not found in any format")
    return problems


def main() -> int:
    gold = load_gold()
    needs_eyes = []
    failures = 0

    for doc in gold:
        if doc.kind == "reject":
            continue  # no invoice values to verify
        document = load(doc.pdf)
        if document.kind != "text":
            needs_eyes.append(doc.pdf.name)
            continue
        for truth in doc.invoices:
            problems = check(document.text, truth)
            if problems:
                failures += 1
                print(f"✗ {doc.pdf.name}")
                for problem in problems:
                    print(f"    {problem}")
            else:
                print(f"✓ {doc.pdf.name}")

    print(f"\nno text layer — verify by eye against fixtures/truth/: "
          f"{', '.join(needs_eyes)}")
    if failures:
        print(f"\n{failures} document(s) FAILED the cross-check")
    else:
        print("every digital document matches its sidecar")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
