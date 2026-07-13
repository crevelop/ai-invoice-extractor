# ai-invoice-extractor

Schema-driven invoice extraction: a deterministic pipeline with exactly one AI
call, measured with evals. See [SPEC.md](SPEC.md) for the full design.

**Status:** build step 4 of 9 — gold-labelled evals with first accuracy and
cost tables (below). Prompt chaining and the schema-swap demo land in later
steps.

## Walkthrough (video chapters)

The numbered lessons live at the repo root, right next to the `extractor/`
package they import — so they run with zero path configuration. Each file
runs top-to-bottom (`uv run python 1-ingestion.py`) and cell-by-cell in the
VS Code interactive window — select this project's `.venv` as the kernel
(ipykernel ships as a dev dependency). Chapters 2+ need `ANTHROPIC_API_KEY`
in `.env`. **Following the whole walkthrough costs well under $0.25 in API
calls** — every cell that spends money says so in its title.

1. [`1-ingestion.py`](1-ingestion.py) — input adapters: PDF, scan,
   and photo normalize into one `Document` shape
2. [`2-ai-inference.py`](2-ai-inference.py) — call the API: content
   + instructions in, plain text out — great until you try to parse it
3. [`3-structured-output.py`](3-structured-output.py) — the same
   call with a typed schema; prose → typed object
4. [`4-validation.py`](4-validation.py) — deterministic rules +
   confidence gate: AUTO_ACCEPT / NEEDS_REVIEW / REJECT, review queue as JSONL

Chapter [`7-evals.py`](7-evals.py) is also runnable already — evals get
built early (build order ≠ chapter order) so every later change can be
measured. Chapters 5–6 land next.

## The engine

The lessons demo concepts; this package owns the implementations.
The pipeline is generic; [`profiles/`](profiles/) holds everything
use-case-specific:

```python
from extractor import extract
from profiles.iberia_invoice import IBERIA_INVOICE

result = extract("invoice.pdf", IBERIA_INVOICE)
result.data        # typed IberiaInvoice instance (None on REJECT)
result.field_meta  # per-field confidence + flags
result.validation  # passed/failed business rules
result.cost        # tokens in/out + $ estimate
result.decision    # AUTO_ACCEPT | NEEDS_REVIEW | REJECT
```

- [`extractor/adapters.py`](extractor/adapters.py) — `DocumentLoader`:
  PDF/scan/photo → one `Document`
- [`extractor/providers/`](extractor/providers/) — the `LLMProvider` interface
  + `AnthropicProvider` wrapping the selected model (pricing single source;
  swapping LLMs = one new subclass)
- [`extractor/validate.py`](extractor/validate.py) — rule runner + locale-aware
  `Money` (accepts `1.234,56`)
- [`extractor/gate.py`](extractor/gate.py) — rules + confidence → decision
- [`extractor/output.py`](extractor/output.py) — `ReviewQueue`: flagged
  documents land in a JSONL file with reasons attached
- [`profiles/iberia_invoice.py`](profiles/iberia_invoice.py) — the worked
  example: schema + 6 business rules + gate policy (SPEC §4)

Rules and gate are plain code, so they get plain tests:
`uv run pytest tests/test_validation.py` (no API key needed).

## Evals — first results (build step 4)

Every document is scored against a verified answer key: the truth sidecars
in [`fixtures/truth/`](fixtures/truth/), cross-checked against the rendered
PDFs by [`evals/verify_gold.py`](evals/verify_gold.py). **You don't need to
run the evals** — the results are committed here. If you change the system,
`uv run python evals/run_evals.py` reproduces them: it prints the estimated
cost and asks before spending, and caches every extraction so re-runs with
unchanged prompts/model are free.

`claude-haiku-4-5` · 43 documents · $0.0067/doc:

| metric | result |
|---|---|
| fully correct documents | 34/37 |
| per-field accuracy | 95–100% (weakest: vendor fields, line items) |
| reject docs correctly refused | 4/4 |
| **gate quality** — auto-accepted docs with any error | **3/37 (8.1%)** |

The failures are the honest kind the failure matrix was built to catch:

- **Vendor/customer confusion (2 scans):** on the scanned German layout the
  model reads the prominent *customer* block as the vendor — the real vendor
  hides in the letterhead — and self-reports high confidence, so the gate
  auto-accepts a wrong vendor. This is the target for chapter 5's
  verification pass and a field-description fix in build step 6.
- **Line-item misreads (2 docs):** one digital German invoice, one scan.
- **Multi-invoice PDFs (t08, known limitation):** auto-accept with only one
  of two invoices extracted, until the multi-invoice adapter heuristic lands.

That 8.1% gate error rate is the number the rest of the build exists to
push down — and now it's measured, not guessed.

## Fixtures (SPEC §5.5 failure matrix)

43 synthetic PDFs (41 invoice records + 4 reject docs) across 12 layout
templates, generated as HTML → PDF with truth sidecars. The size is set by
the eval: 41 records × 12 fields ≈ 490 field comparisons keeps the headline
accuracy table stable (one error ≈ 0.2%), with 3+ documents per
failure-matrix row — bigger buys little, smaller makes gate quality
anecdotal.

```
uv run python fixtures/generate.py   # regenerate (deterministic, seed 20260711)
uv run pytest                        # smoke tests: counts, arithmetic, determinism
```

| Template | Covers |
|---|---|
| t01/t02 Spanish clean & dense | baseline, European decimals, mixed IVA rates |
| t03/t04 Portuguese & German | intra-EU reverse-charge VAT |
| t05 Chinese exporter | US decimals, USD/CNY, non-EU tax id |
| t06 minimalist English | missing fields (no due date) → `None` |
| t07 multi-page | 2–3 page invoices |
| t08 concatenated PDF | two invoices in one attachment |
| t09 simulated scans | rotated, noisy, no text layer |
| t10 handwritten annotations | scrawls + distractor amount over printed values |
| r1/r2 statement & quote | must be REJECTed, not extracted |

`fixtures/photo/` holds a real photographed receipt (user-provided, not
generated) for the chapter-1 adapter demo. All generated docs are internally
consistent by design — seeded extraction errors are simulated in code in
chapter 4, never baked into documents (see `fixtures/gen/__init__.py`).

## Setup

Python 3.12 + [uv](https://docs.astral.sh/uv/). `uv sync`, then copy
`.env.example` to `.env` and add API keys (needed from build step 2 onward).
WeasyPrint (fixture generation only) needs Pango: `brew install pango` on
macOS, `apt install libpango-1.0-0 libpangocairo-1.0-0` on Debian/Ubuntu.
