"""Corpus assembly: the concrete ~43-doc plan over the failure matrix.

Doc counts per template are the SPEC §5.5 coverage plan; change them here,
regenerate, and re-verify goldset spot checks.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal

from . import render
from .data import VENDORS, make_invoice
from .models import InvoiceTruth, TruthDoc
from .templates import (r1_statement, r2_quote, t01_es_clean, t02_es_dense,
                        t03_pt_reverse, t04_de_reverse, t05_cn_export,
                        t06_en_minimal, t07_es_multipage, t10_es_handwritten)


@dataclass
class Doc:
    name: str  # file stem, e.g. "t01-es-clean-01"
    subdir: str  # "invoices" | "reject"
    template: str
    tags: list[str]
    truth: TruthDoc
    pdf: bytes


def _truth(*invoices: InvoiceTruth) -> TruthDoc:
    return TruthDoc(kind="invoice", document_type="invoice", invoices=list(invoices))


def build_corpus(rng: random.Random) -> list[Doc]:
    docs: list[Doc] = []
    seqs = {key: 40 + 61 * i for i, key in enumerate(VENDORS)}

    def nxt(key: str) -> int:
        seqs[key] += rng.randint(1, 9)
        return seqs[key]

    def mk(key: str, **kw) -> InvoiceTruth:
        return make_invoice(rng, VENDORS[key], nxt(key), **kw)

    # T1 — Spanish clean (baseline, EU decimals)
    for i in range(6):
        inv = mk("es_clean")
        docs.append(Doc(f"t01-es-clean-{i + 1:02d}", "invoices", t01_es_clean.TEMPLATE_ID,
                        t01_es_clean.TAGS, _truth(inv),
                        render.html_to_pdf(t01_es_clean.build(inv, VENDORS["es_clean"]))))

    # T2 — Spanish dense; docs 3 and 5 at 10% IVA (mixed-rate coverage)
    for i, rate in enumerate([21, 21, 10, 21, 10]):
        inv = mk("es_dense", tax_rate=Decimal(rate))
        docs.append(Doc(f"t02-es-dense-{i + 1:02d}", "invoices", t02_es_dense.TEMPLATE_ID,
                        t02_es_dense.TAGS, _truth(inv),
                        render.html_to_pdf(t02_es_dense.build(inv, VENDORS["es_dense"]))))

    # T3 / T4 — intra-EU reverse charge (PT and DE)
    for i in range(4):
        inv = mk("pt_reverse", locale="pt", reverse_charge=True)
        docs.append(Doc(f"t03-pt-reverse-{i + 1:02d}", "invoices", t03_pt_reverse.TEMPLATE_ID,
                        t03_pt_reverse.TAGS, _truth(inv),
                        render.html_to_pdf(t03_pt_reverse.build(inv, VENDORS["pt_reverse"]))))
    for i in range(4):
        inv = mk("de_reverse", locale="de", reverse_charge=True)
        docs.append(Doc(f"t04-de-reverse-{i + 1:02d}", "invoices", t04_de_reverse.TEMPLATE_ID,
                        t04_de_reverse.TAGS, _truth(inv),
                        render.html_to_pdf(t04_de_reverse.build(inv, VENDORS["de_reverse"]))))

    # T5 — Chinese exporter: US decimals, USD/CNY, zero-rated export tax
    for i, cur in enumerate(["USD", "USD", "USD", "CNY", "CNY"]):
        inv = mk("cn_export", locale="en", currency=cur, tax_rate=Decimal("0"))
        docs.append(Doc(f"t05-cn-export-{i + 1:02d}", "invoices", t05_cn_export.TEMPLATE_ID,
                        t05_cn_export.TAGS, _truth(inv),
                        render.html_to_pdf(t05_cn_export.build(inv, VENDORS["cn_export"]))))

    # T6 — minimalist, missing due date (must extract as None)
    for i in range(4):
        inv = mk("en_minimal", locale="en", with_due_date=False)
        docs.append(Doc(f"t06-en-minimal-{i + 1:02d}", "invoices", t06_en_minimal.TEMPLATE_ID,
                        t06_en_minimal.TAGS, _truth(inv),
                        render.html_to_pdf(t06_en_minimal.build(inv, VENDORS["en_minimal"]))))

    # T7 — multi-page (48–95 line items over 2–3 pages)
    for i in range(3):
        inv = mk("es_multipage", n_items=(48, 95))
        docs.append(Doc(f"t07-es-multipage-{i + 1:02d}", "invoices", t07_es_multipage.TEMPLATE_ID,
                        t07_es_multipage.TAGS, _truth(inv),
                        render.html_to_pdf(t07_es_multipage.build(inv, VENDORS["es_multipage"]))))

    # T8 — two invoices concatenated into one PDF (multi-invoice attachment)
    for i in range(2):
        a, b = mk("es_clean"), mk("es_dense")
        pdf = render.concat_pdfs([
            render.html_to_pdf(t01_es_clean.build(a, VENDORS["es_clean"])),
            render.html_to_pdf(t02_es_dense.build(b, VENDORS["es_dense"])),
        ])
        docs.append(Doc(f"t08-multi-invoice-{i + 1:02d}", "invoices", "t08_multi_invoice",
                        ["es", "eur", "eu_decimals", "multi_invoice"], _truth(a, b), pdf))

    # T9 — simulated scans (rasterized + rotated + noise, no text layer)
    scan_sources = [("es_clean", t01_es_clean, {}),
                    ("es_clean", t01_es_clean, {}),
                    ("de_reverse", t04_de_reverse, {"locale": "de", "reverse_charge": True}),
                    ("de_reverse", t04_de_reverse, {"locale": "de", "reverse_charge": True})]
    for i, (key, tpl, kw) in enumerate(scan_sources):
        inv = mk(key, **kw)
        pdf = render.scanify(render.html_to_pdf(tpl.build(inv, VENDORS[key])), rng)
        docs.append(Doc(f"t09-scanned-{i + 1:02d}", "invoices", "t09_scanned",
                        sorted({*tpl.TAGS, "scanned", "rotated", "no_text_layer"}),
                        _truth(inv), pdf))

    # T10 — handwritten annotations over printed values
    for i in range(2):
        inv = mk("es_handwritten")
        docs.append(Doc(f"t10-es-handwritten-{i + 1:02d}", "invoices",
                        t10_es_handwritten.TEMPLATE_ID, t10_es_handwritten.TAGS, _truth(inv),
                        render.html_to_pdf(
                            t10_es_handwritten.build(inv, VENDORS["es_handwritten"], variant=i))))

    # R1 / R2 — statement and quote: gate must REJECT, never extract
    for i in range(2):
        docs.append(Doc(f"r1-statement-{i + 1:02d}", "reject", r1_statement.TEMPLATE_ID,
                        r1_statement.TAGS,
                        TruthDoc(kind="reject", document_type="statement"),
                        render.html_to_pdf(r1_statement.build(rng, VENDORS["es_clean"]))))
    for i in range(2):
        docs.append(Doc(f"r2-quote-{i + 1:02d}", "reject", r2_quote.TEMPLATE_ID,
                        r2_quote.TAGS,
                        TruthDoc(kind="reject", document_type="quote"),
                        render.html_to_pdf(r2_quote.build(rng, VENDORS["es_dense"]))))

    return docs
