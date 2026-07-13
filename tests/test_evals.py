"""Eval harness + cache tests — the deterministic half of the eval story.
No API calls."""

import sys
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel

# extractor/, profiles/ and evals/ live at the repo root, one level up
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.harness import (  # noqa: E402
    compare_fields,
    field_accuracy,
    load_gold,
    normalize_name,
    sample,
)
from extractor import CachedProvider, Cost, Document, LLMProvider  # noqa: E402


# ── gold set


def test_gold_set_covers_the_whole_corpus():
    gold = load_gold()
    kinds = [doc.kind for doc in gold]
    assert len(gold) == 43
    assert kinds.count("invoice") == 37
    assert kinds.count("multi") == 2
    assert kinds.count("reject") == 4
    for doc in gold:
        assert doc.pdf.exists(), f"missing PDF for {doc.pdf.name}"


def test_sample_picks_one_doc_per_template():
    picked = sample(load_gold())
    templates = [doc.template for doc in picked]
    assert len(templates) == len(set(templates)) == 12  # t01..t10 + r1 + r2


# ── field comparison


def first_invoice_truth():
    return next(doc for doc in load_gold() if doc.kind == "invoice").truth


def test_identical_extraction_scores_perfect():
    truth = first_invoice_truth()
    checks = compare_fields(truth, truth)
    assert all(checks.values())
    assert len(checks) == 12


def test_wrong_total_is_caught():
    truth = first_invoice_truth()
    wrong = truth.model_copy(update={"total": truth.total + 1})
    checks = compare_fields(wrong, truth)
    assert checks["total"] is False
    assert checks["subtotal"] is True


def test_name_casing_and_punctuation_are_not_errors():
    assert normalize_name("Cocinas del Ebro, S.L.") == normalize_name(
        "COCINAS DEL EBRO SL")


def test_missing_line_item_is_caught():
    truth = first_invoice_truth()
    wrong = truth.model_copy(update={"line_items": truth.line_items[:-1]})
    assert compare_fields(wrong, truth)["line_items"] is False


def test_field_accuracy_aggregates_counts():
    rows = [{"total": True, "currency": True},
            {"total": False, "currency": True}]
    assert field_accuracy(rows) == {"total": (1, 2), "currency": (2, 2)}


# ── the cache


class TinyOutput(BaseModel):
    answer: str


class StubProvider(LLMProvider):
    name = "stub"
    model = "stub-1"

    def __init__(self):
        self.calls = 0

    def generate_text(self, doc, instructions):
        self.calls += 1
        return "prose", Cost(input_tokens=1, output_tokens=1, usd=0.001)

    def extract_structured(self, doc, output_model, instructions):
        self.calls += 1
        return (output_model(answer="42"),
                Cost(input_tokens=1, output_tokens=1, usd=0.001))


def test_cache_stops_repeat_calls_from_paying(tmp_path):
    stub = StubProvider()
    cached = CachedProvider(stub, tmp_path)
    doc = Document(source="a.pdf", kind="text", text="the document")

    first, cost1 = cached.extract_structured(doc, TinyOutput, "extract")
    second, cost2 = cached.extract_structured(doc, TinyOutput, "extract")

    assert stub.calls == 1  # second answer came from disk
    assert first == second
    assert cost1 == cost2  # the stored cost rides along
    assert (cached.hits, cached.misses) == (1, 1)


def test_cache_distinguishes_different_documents(tmp_path):
    stub = StubProvider()
    cached = CachedProvider(stub, tmp_path)
    cached.extract_structured(
        Document(source="a", kind="text", text="one"), TinyOutput, "x")
    cached.extract_structured(
        Document(source="b", kind="text", text="two"), TinyOutput, "x")
    assert stub.calls == 2


def test_cache_distinguishes_different_instructions(tmp_path):
    stub = StubProvider()
    cached = CachedProvider(stub, tmp_path)
    doc = Document(source="a", kind="text", text="one")
    cached.extract_structured(doc, TinyOutput, "instructions v1")
    cached.extract_structured(doc, TinyOutput, "instructions v2")
    assert stub.calls == 2


def test_amounts_compare_exactly():
    truth = first_invoice_truth()
    off_by_a_cent = truth.model_copy(
        update={"total": truth.total + Decimal("0.01")})
    assert compare_fields(off_by_a_cent, truth)["total"] is False
