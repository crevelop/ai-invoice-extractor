# ai-invoice-extractor

Schema-driven invoice extraction: a deterministic pipeline with exactly one AI
call, measured with evals. See [SPEC.md](SPEC.md) for the full design.

**Status:** build step 7 of 9 — second provider: `OpenAIProvider` behind
the same interface, and the model-tier comparison is measured (tables
below). The schema-swap demo lands next.

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
5. [`5-prompt-chaining.py`](5-prompt-chaining.py) — a second, blind AI
   read of the fields that move money; code compares the two readings,
   a mismatch forces review

Chapter [`7-evals.py`](7-evals.py) is also runnable already — evals get
built early (build order ≠ chapter order) so every later change can be
measured. Chapter 6 lands next.

## The engine

The lessons demo concepts; this package owns the implementations.
The pipeline is generic; [`profiles/`](profiles/) holds everything
use-case-specific:

```python
from extractor import extract, verify
from profiles.iberia_invoice import IBERIA_INVOICE

result = extract("invoice.pdf", IBERIA_INVOICE)
result = verify(result, IBERIA_INVOICE)  # optional second AI read (chapter 5)
result.data        # typed IberiaInvoice instance (None on REJECT)
result.field_meta  # per-field confidence + flags
result.validation  # passed/failed business rules
result.cost        # tokens in/out + $ estimate
result.decision    # AUTO_ACCEPT | NEEDS_REVIEW | REJECT
```

- [`extractor/adapters.py`](extractor/adapters.py) — `DocumentLoader`:
  PDF/scan/photo → one `Document`
- [`extractor/providers/`](extractor/providers/) — the `LLMProvider`
  interface with `AnthropicProvider` and `OpenAIProvider` behind it
  (pricing single source per file; swapping LLMs = one new subclass,
  and nothing else in the repo changes — that's the proof)
- [`extractor/validate.py`](extractor/validate.py) — rule runner + locale-aware
  `Money` (accepts `1.234,56`)
- [`extractor/verify.py`](extractor/verify.py) — the optional verification
  step, chained after extraction (`verify(result, profile)`): a second,
  blind read of the critical fields; deterministic comparison, flags but
  never corrects
- [`extractor/gate.py`](extractor/gate.py) — rules + confidence → decision
- [`extractor/output.py`](extractor/output.py) — `ReviewQueue`: flagged
  documents land in a JSONL file with reasons attached
- [`profiles/iberia_invoice.py`](profiles/iberia_invoice.py) — the worked
  example: schema + 6 business rules + gate policy (SPEC §4)

Rules and gate are plain code, so they get plain tests:
`uv run pytest tests/test_validation.py` (no API key needed).

## Evals — measured, improved, re-measured (build steps 4–7)

Every document is scored against a verified answer key: the truth sidecars
in [`fixtures/truth/`](fixtures/truth/), cross-checked against the rendered
PDFs by [`evals/verify_gold.py`](evals/verify_gold.py). **You don't need to
run the evals** — the results are committed here. If you change the system,
`uv run python evals/run_evals.py` reproduces them (`--verify` for the
ablation row, `--provider openai` for the other vendor, `--verify-provider`
to have one vendor check the other): it prints the estimated cost and asks
before spending, and caches every extraction so re-runs with unchanged
prompts/model are free.

`claude-haiku-4-5` · 43 documents · with and without the chapter-5
verification pass:

| metric | baseline | + verification |
|---|---|---|
| fully correct documents | 35/37 | 35/37 |
| per-field accuracy | 97–100% | 97–100% |
| reject docs correctly refused | 4/4 | 4/4 |
| **gate quality** — auto-accepted docs with any error | **2/37 (5.4%)** | **1/36 (2.8%)** |
| cost per document | $0.0074 | $0.0088 |

Accuracy doesn't move between the columns — the verifier flags, it never
corrects — but gate quality does: what slips past one read gets caught by
the second and lands in review with both readings attached.

The eval's whole point is watching numbers move when the system changes:

| gate error (auto-accepted docs with any error) | baseline | + verification |
|---|---|---|
| build step 4 — first measured baseline | 8.1% | — |
| build step 5 — verification pass | 8.1% | 2.9% |
| build step 6 — field-description fixes | 5.4% | 2.8% |

Step 6 fixed the two failure classes prompts *can* fix, by sharpening field
descriptions in [`profiles/iberia_invoice.py`](profiles/iberia_invoice.py):
vendor/customer confusion on the German scans (the vendor is "the party
that ISSUED the invoice — letterhead, logo, bank details", not the
prominent customer block) and quantity markers glued onto line-item
descriptions ("'10 Stk.' belongs in quantity").

### Model tiers, measured (build step 7)

Same 43 documents, same engine — only the provider argument changes.
`gpt-5.4-mini` is OpenAI's small tier as of July 2026, the fair peer to
Haiku 4.5; `gpt-4o-mini` (2024) stays in the table as the budget floor:

| configuration | fully correct | gate error | reviews (false alarms) | $/doc |
|---|---|---|---|---|
| `claude-haiku-4-5` | 35/37 | 5.4% | 0 | $0.0074 |
| — + same-model verification | 35/37 | **2.8%** | 1 (0) | $0.0088 |
| — + `gpt-5.4-mini` as verifier | 35/37 | **2.8%** | 1 (0) | $0.0083 |
| `gpt-5.4-mini` | 28/37 | 24.3% | 0 | $0.0036 |
| — + same-model verification | 28/37 | 24.3% | 0 | $0.0045 |
| `gpt-4o-mini` (budget floor) | 24/37 | 27.3% | 4 (0) | $0.0011 |
| — + same-model verification | 24/37 | 8.7% | 14 (3) | $0.0017 |

Three findings the table buys:

- **Model choice dominates everything else on this page.** The peer-tier
  `gpt-5.4-mini` costs half as much and gets 9 more documents wrong — and
  auto-accepts every one of them, because it never doubts itself. Every
  wrong auto-post lands in the ERP. The extra $0.004/doc for the stronger
  reader is the cheapest line item in the system.
- **Self-verification is worth exactly as much as the model's self-variance.**
  Haiku checking itself halves its gate error; `gpt-5.4-mini` checking
  itself catches *zero* of its nine errors — a highly self-consistent
  model re-reads its way into the same mistakes, so the second call buys
  the same opinion twice.
- **A cross-provider verifier works when it's a peer.** `gpt-5.4-mini`
  verifying Haiku matches same-model verification exactly (2.8%, no false
  alarms, marginally cheaper) — two different models agreeing is the
  strongest evidence on this page. The 2024 budget model in the same seat
  was a *worse* witness: five false alarms and it missed the real error.

Swapping providers also surfaced two vendor quirks, both absorbed at the
validation boundary without touching the engine: `gpt-4o-mini` reports the
*string* `"null"` for a not-applicable confidence even in strict-schema
mode, and copies quantity columns verbatim (`"4 Stk."`) — which the same
locale-aware parsing that handles `1.234,56` now swallows too.

What remains, honestly:

- **Single-letter scan misreads (2 docs):** on the two noisiest scans the
  model drops a letter from the vendor's name on one ("Küchenprof") and
  doubles a letter in a line-item description on the other ("Auflauffform").
  Prompts can't fix pixels. The name misread is on a critical field, so
  verification catches it → review; the line-item one isn't — it IS the
  remaining 2.8%. Widening the critical set is a thresholds-vs-cost
  decision, not a code change.
- **Multi-invoice PDFs (t08, known limitation):** auto-accept with only one
  of two invoices extracted, until the multi-invoice adapter heuristic
  lands. (One of the two now trips verification by luck — the two reads
  picked different invoices — but the fix belongs in the adapter.)

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
`.env.example` to `.env` and add API keys: `ANTHROPIC_API_KEY` for the
walkthrough (build step 2 onward), `OPENAI_API_KEY` only if you want the
cross-model evals.
WeasyPrint (fixture generation only) needs Pango: `brew install pango` on
macOS, `apt install libpango-1.0-0 libpangocairo-1.0-0` on Debian/Ubuntu.
