"""Fixture-generator smoke tests: regenerate into a tmp dir, then check
manifest counts, truth-sidecar arithmetic, and determinism vs the committed
corpus."""

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fixtures"))

from gen.render import page_count  # noqa: E402
from generate import generate  # noqa: E402


@pytest.fixture(scope="session")
def corpus(tmp_path_factory):
    out = tmp_path_factory.mktemp("fixtures")
    return generate(out), out


def test_manifest_counts(corpus):
    manifest, _ = corpus
    assert manifest["counts"] == {
        "invoice_docs": 39,
        "reject_docs": 4,
        "total_docs": 43,
        "invoice_records": 41,  # 39 invoice PDFs, two of which hold 2 invoices
    }
    assert len(manifest["docs"]) == 43


def test_all_files_written(corpus):
    manifest, out = corpus
    for entry in manifest["docs"]:
        assert (out / entry["file"]).stat().st_size > 0
        assert (out / entry["truth"]).stat().st_size > 0


def test_truth_arithmetic(corpus):
    """Every invoice sidecar must be internally consistent (no lying docs —
    see fixtures/gen/__init__.py)."""
    manifest, out = corpus
    checked = 0
    for entry in manifest["docs"]:
        truth = json.loads((out / entry["truth"]).read_text())
        for inv in truth["invoices"]:
            sub, tax = Decimal(inv["subtotal"]), Decimal(inv["tax_amount"])
            line_sum = sum(Decimal(li["total"]) for li in inv["line_items"])
            assert line_sum == sub, entry["file"]
            assert sub + tax == Decimal(inv["total"]), entry["file"]
            if inv["reverse_charge"]:
                assert tax == 0, entry["file"]
            checked += 1
    assert checked == 41


def test_failure_matrix_cases(corpus):
    manifest, out = corpus
    by_tpl = {}
    for e in manifest["docs"]:
        by_tpl.setdefault(e["template"], []).append(e)

    for e in by_tpl["t07_es_multipage"]:
        assert e["pages"] >= 2, "multi-page fixtures must actually paginate"
    for e in by_tpl["t08_multi_invoice"]:
        truth = json.loads((out / e["truth"]).read_text())
        assert len(truth["invoices"]) == 2
    for e in by_tpl["t09_scanned"]:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(out / e["file"]))
        assert doc[0].get_textpage().get_text_bounded() == "", "scan must have no text layer"
        doc.close()
    for tpl in ("r1_statement", "r2_quote"):
        for e in by_tpl[tpl]:
            truth = json.loads((out / e["truth"]).read_text())
            assert truth["kind"] == "reject" and truth["invoices"] == []
    for e in by_tpl["t06_en_minimal"]:
        truth = json.loads((out / e["truth"]).read_text())
        assert truth["invoices"][0]["due_date"] is None


def test_deterministic_vs_committed(corpus):
    """Same seed → same corpus: the freshly generated manifest must equal the
    committed one (regenerating never drifts the goldset)."""
    manifest, _ = corpus
    committed = json.loads((ROOT / "fixtures" / "MANIFEST.json").read_text())
    assert manifest == committed


def test_pages_match_manifest(corpus):
    manifest, out = corpus
    for entry in manifest["docs"][:5]:
        assert page_count((out / entry["file"]).read_bytes()) == entry["pages"]
