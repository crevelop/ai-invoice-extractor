# ai-invoice-extractor

Schema-driven invoice extraction: a deterministic pipeline with exactly one AI
call, measured with evals. See [SPEC.md](SPEC.md) for the full design.

**Status:** build step 1 of 9 — fixture corpus. The extraction engine,
walkthrough chapters, and eval tables land in later steps.

## Fixtures (SPEC §5.5 failure matrix)

43 synthetic PDFs (41 invoice records + 4 reject docs) across 12 layout
templates, generated as HTML → PDF with truth sidecars:

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
