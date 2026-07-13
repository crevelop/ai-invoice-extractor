"""Eval harness: load the gold set, compare extractions field by field,
aggregate accuracy. Pure code — nothing here calls an API.

Comparison policy (SPEC §5): exact match for ids, dates, amounts and
enums; normalized match for names (case and punctuation don't count as
errors); line items match when every row matches.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from profiles.iberia_invoice import IberiaInvoice

ROOT = Path(__file__).resolve().parent.parent
TRUTH_DIR = ROOT / "fixtures" / "truth"
DOCS_DIR = ROOT / "fixtures" / "docs"

# Fields compared by simple equality. vendor_name and line_items get
# special treatment below.
EXACT_FIELDS = (
    "vendor_tax_id", "invoice_number", "issue_date", "due_date",
    "currency", "subtotal", "tax_rate", "tax_amount", "total",
    "reverse_charge",
)


@dataclass
class GoldDoc:
    pdf: Path
    template: str  # e.g. "t01-es-clean" — one failure-matrix cell
    kind: str  # "invoice" | "multi" | "reject"
    invoices: list[IberiaInvoice]

    @property
    def truth(self) -> IberiaInvoice:
        return self.invoices[0]


def load_gold() -> list[GoldDoc]:
    """One GoldDoc per PDF, parsed from the truth sidecars."""
    gold = []
    for sidecar in sorted(TRUTH_DIR.glob("*.json")):
        data = json.loads(sidecar.read_text())
        invoices = [IberiaInvoice.model_validate(inv)
                    for inv in data["invoices"]]
        if data["kind"] == "reject":
            kind, folder = "reject", "reject"
        elif len(invoices) > 1:
            kind, folder = "multi", "invoices"
        else:
            kind, folder = "invoice", "invoices"
        name = sidecar.stem
        gold.append(GoldDoc(
            pdf=DOCS_DIR / folder / f"{name}.pdf",
            template=name.rsplit("-", 1)[0],
            kind=kind,
            invoices=invoices,
        ))
    return gold


def sample(gold: list[GoldDoc]) -> list[GoldDoc]:
    """The first document of every template — one per failure-matrix cell."""
    seen = set()
    picked = []
    for doc in gold:
        if doc.template not in seen:
            seen.add(doc.template)
            picked.append(doc)
    return picked


def normalize_name(name: str) -> str:
    """Casing and punctuation are not extraction errors:
    'Cocinas del Ebro, S.L.' == 'COCINAS DEL EBRO SL'."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def compare_fields(got: IberiaInvoice, want: IberiaInvoice) -> dict[str, bool]:
    """Field-by-field verdict for one document."""
    checks = {"vendor_name":
              normalize_name(got.vendor_name) == normalize_name(want.vendor_name)}
    for field in EXACT_FIELDS:
        checks[field] = getattr(got, field) == getattr(want, field)
    checks["line_items"] = _line_items_match(got, want)
    return checks


def _line_items_match(got: IberiaInvoice, want: IberiaInvoice) -> bool:
    if len(got.line_items) != len(want.line_items):
        return False
    for g, w in zip(got.line_items, want.line_items):
        if normalize_name(g.description) != normalize_name(w.description):
            return False
        if (g.quantity, g.unit_price, g.total) != (w.quantity, w.unit_price, w.total):
            return False
    return True


def all_wrong() -> dict[str, bool]:
    """The score sheet for a doc where extraction returned no data."""
    checks = {field: False for field in EXACT_FIELDS}
    checks["vendor_name"] = False
    checks["line_items"] = False
    return checks


def field_accuracy(rows: list[dict[str, bool]]) -> dict[str, tuple[int, int]]:
    """Aggregate per-field: {field: (correct, total)} across documents."""
    totals: dict[str, tuple[int, int]] = {}
    for row in rows:
        for field, ok in row.items():
            correct, total = totals.get(field, (0, 0))
            totals[field] = (correct + (1 if ok else 0), total + 1)
    return totals
