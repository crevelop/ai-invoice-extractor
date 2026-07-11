# fixtures/

Synthetic test invoices with known correct answers, used by the walkthrough
demos and the eval suite. This is input data, not part of the system to learn
from.

- `docs/` — the generated PDFs: `invoices/` (extract these) and `reject/`
  (statements and quotes the gate must refuse)
- `truth/` — the known-correct JSON answer for each document
- `photo/` — a real photographed receipt for the chapter-1 adapter demo
- `gen/` — the generator code; off the learning path, only relevant if you
  want to change the fixture set
- `MANIFEST.json` — the index mapping each document to its template and
  failure tags; the eval runner uses it to slice accuracy by category

Regenerate everything with `uv run python fixtures/generate.py` — generation
is seeded, so the output is stable. The corpus deliberately covers a failure
matrix (scans, reverse-charge VAT, multi-page, US/EU decimals, …); see
SPEC.md §5 for the design.

To understand the actual system, start at `walkthrough/1-ingestion.py`.
