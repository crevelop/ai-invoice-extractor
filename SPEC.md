# Project Doc — `ai-invoice-extractor`

Schema-driven document extraction with deterministic validation and a measured eval — the "AI system, not AI agent" pattern applied to the #1 document-automation use case. This doc doubles as the CLAUDE.md seed and the video script skeleton.

**Naming note:** named for the problem people search ("invoice"), not the abstraction ("document extractor"). The engine's generality is the reveal inside the repo, and leaves room for a sequel repo/video ("universal document extractor") later.

---

## 1. The problem (video intro material)

When an invoice arrives at a company — usually a PDF attached to an email — an accounts-payable clerk: opens it, confirms it's actually an invoice, identifies the vendor, and retypes everything into the ERP (vendor, invoice number, dates, PO number, currency, line items, subtotal, tax, total, bank details). Then they validate (does the math add up? duplicate? right vendor record?), match against purchase orders, route for approval, code to the right expense account, and archive it for audit.

Why it's a real problem:

- Manual processing takes 10–20 minutes per invoice; fully-loaded cost estimates run ~$10–15 per invoice vs. ~$2–3 automated. Mid-size companies handle thousands per month.
- Every vendor's layout is different — formats, languages, currencies, decimal conventions (`1.234,56` vs `1,234.56`). There is no standard.
- Human errors cost real money: typos in amounts, duplicate payments, missed early-payment discounts, late-payment penalties.
- Pre-LLM automation (template OCR) was brittle: per-vendor templates configured by hand, broken by any redesign. LLM extraction is layout-agnostic — that's the game-changer.

The thesis: **only one step in the whole process requires judgment on unstructured input — reading the document.** Everything else is deterministic logic. So we put AI in exactly one seat and code everywhere else. No agent needed: the workflow is fixed, known in advance, and linear. An agent here would add latency, cost, and nondeterminism for zero benefit.

## 2. Core design: the schema is the contract

The pipeline is generic. The **only thing that changes per company/use case is a Pydantic schema** (plus its attached business rules). One schema definition drives three layers:

1. **Extraction** — the Pydantic model compiles to JSON Schema, passed to the provider's schema-enforced structured-output mode. Field `description`s double as extraction instructions (prompt engineering living inside the type definition).
2. **Structural validation** — Pydantic parses/validates types, enums, optionality, dates. Malformed output never crosses the boundary.
3. **Business-rule validation** — cross-field checks as Pydantic validators / a rules module: line items sum to subtotal; subtotal + tax = total; due date ≥ issue date; locale-aware amount parsing; duplicate detection against a seen-set. Deterministic math catches the LLM's hallucinated digit.

### Public API (the whole point in one signature)

```python
result = extract(document="invoice.pdf", profile=AcmeInvoiceProfile)
# result: ExtractionResult[AcmeInvoice]
#   .data        -> typed AcmeInvoice instance
#   .field_meta  -> per-field confidence + flags
#   .validation  -> list of passed/failed business rules
#   .cost        -> tokens in/out, $ estimate
#   .decision    -> AUTO_ACCEPT | NEEDS_REVIEW | REJECT
```

### Document profile = schema + rules + examples

A "customizable schema" alone is half the story; rules and few-shot examples are schema-specific too. Package them together:

```python
class DocumentProfile:
    schema: type[BaseModel]          # what to extract
    rules: list[Rule]                # cross-field business checks
    examples: list[FewShotExample]   # optional, hard layouts
    gate: GatePolicy                 # thresholds for auto/review/reject
```

Swapping profiles swaps the use case. Same engine: invoices today, delivery notes or receipts tomorrow. **The video's money moment: change one import, rerun, extract a different document type in 60 seconds.**

## 3. Pipeline (technical flow)

```
adapters/   PDF/image in → normalized Document: native text extraction when a text
            layer exists, page rendering (pypdfium2) otherwise; downscaling,
            page selection, multi-invoice detection heuristic
extract/    ONE LLM call, vision-capable model, schema-enforced structured output
            (provider-agnostic: Anthropic + OpenAI behind one interface)
validate/   Pydantic parse → business rules → locale-aware normalization
gate/       per-field confidence + validation results → AUTO_ACCEPT / NEEDS_REVIEW / REJECT
output/     typed JSON to stdout/file/webhook; review queue = a JSONL file (keep it simple)
evals/      answer key (gold set), runner, per-field accuracy, cost table
```

Deterministic (code): adapters, validate, gate, output, evals. AI: the single extract call (plus the optional verification call). That ratio — one AI seat in a system of code — is the diagram and the thesis.

### Confidence: two implemented mechanisms + one discussed

- **Self-reported (default, always on)** — the schema includes per-field confidence the model fills in. Cheap, zero extra calls, but models are poorly calibrated; treat as a heuristic.
- **Verification pass (implemented, optional flag)** — `extract(..., verify=True)`. A prompt-chaining step in the evaluator pattern: after extraction, a second call re-reads the **critical fields only** (total, tax id, invoice number) **blind** — the claimed values never enter its context, so there is nothing to anchor on — and deterministic code compares the two readings through the schema's own types (found empirically: showing the verifier the claims made it agree with wrong values on the exact documents it exists to catch, and models judge string equality badly — `5.323,18` vs `5323.18`).
  - **Design rule: the verifier flags, it never silently corrects.** Matching reads raise field confidence; a mismatch downgrades it and forces NEEDS_REVIEW. Two reads agreeing is evidence; two reads disagreeing is uncertainty — a human decides, not a third LLM call.
  - Cost control: critical fields only, and the verifier can be a different/cheaper model (`verifier=` argument); the default reuses the extraction tier, which is already the cheapest vision-capable model.
  - Measured, not assumed: the eval table carries a with/without-verification ablation (gate quality vs. $/doc) so the second call justifies itself with numbers.
- **Logprobs (discussed in README, not implemented)** — real signal where providers expose it; limited availability on structured outputs.

The senior point: confidence exists to drive the gate, and the gate's thresholds are a business decision (cost of a wrong auto-post vs. cost of a human review), not an ML metric.

## 4. Worked example: Company X

**Iberia Home Goods, S.L.** — a fictional Barcelona-based e-commerce wholesaler importing kitchenware. ~800 supplier invoices/month from ~60 vendors across Spain, Portugal, Germany, and China. Invoices arrive as PDF email attachments in Spanish, English, and German; amounts in EUR (mostly) with European decimal format; Spanish invoices carry IVA at mixed rates, intra-EU invoices carry reverse-charge VAT notes.

**Input (A):** vendor PDFs — digital-native and scanned, one clerk currently retypes into Holded (Spanish ERP), ~12 min each ≈ 160 hours/month of data entry.

**Output (B):** JSON matching their ERP import format:

```python
class LineItem(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal = Field(description="Per-unit price before tax")
    total: Decimal

class IberiaInvoice(BaseModel):
    vendor_name: str
    vendor_tax_id: str = Field(description="CIF/NIF or EU VAT number, e.g. ESB12345678")
    invoice_number: str
    issue_date: date
    due_date: date | None
    currency: Literal["EUR", "USD", "CNY"]
    line_items: list[LineItem]
    subtotal: Decimal
    tax_rate: Decimal = Field(description="IVA/VAT percentage as shown, e.g. 21")
    tax_amount: Decimal
    total: Decimal
    reverse_charge: bool = Field(description="True if intra-EU reverse-charge VAT note present")
```

**Business rules for this profile:** sum(line totals) == subtotal (±0.01 tolerance); subtotal + tax_amount == total; tax_amount == subtotal × tax_rate when not reverse_charge; if reverse_charge then tax_amount == 0; vendor_tax_id matches CIF/NIF/EU-VAT regex; (vendor_tax_id, invoice_number) not already seen; European decimal normalization on all amounts.

**Gate policy:** all rules pass + no low-confidence critical field (total, tax_id, invoice_number) → AUTO_ACCEPT; any rule failure or low-confidence critical field → NEEDS_REVIEW; document-type check says "not an invoice" → REJECT.

**Narrative outcome for the video:** clerk goes from retyping 800 invoices to reviewing the ~100–150 the gate flags. LLM cost at ~$0.02/invoice ≈ $16/month vs ~160 hours of data entry. Do this math on screen.

**The schema-swap demo:** define a second 10-line profile (`DeliveryNote` or `ExpenseReceipt`), rerun the same engine on a sample doc, get typed output. No engine changes. This is the proof the design is a pattern, not a demo.

## 5. Eval harness (the senior signal)

1. **Corpus:** 30–50 synthetic invoices generated as HTML → PDF across ~10 layout templates, covering the failure matrix below, plus a handful of real public-domain samples if available. Committed to `fixtures/`. Size rationale (built: 43 docs / 41 records): 41 records × 12 fields ≈ 490 field comparisons keeps the headline table stable (one error ≈ 0.2%), with 3+ docs per failure-matrix cell — bigger buys little, smaller makes gate quality anecdotal. Cost control lives in the runner, not the corpus: extractions cache to disk, so only changed prompts/schema/model re-pay.
2. **Gold labels:** hand-verified JSON per document. Yes, by hand — this is the Stage 4 warm-up.
3. **Metrics (per field):** exact-match accuracy for ids/dates/amounts, normalized match for names; plus document-level "fully correct" rate; plus **gate quality**: of AUTO_ACCEPTed docs, how many had any error (the metric a CFO actually cares about).
4. **Cost table:** $/document by model tier (e.g., Haiku-class vs Sonnet-class vs GPT-4o-mini-class), accuracy vs. cost trade-off.
   - **Verification ablation:** each config run with and without `verify=True` — does gate quality improve enough to justify the extra call? This table answers it with data.
5. **Failure matrix (build these cases deliberately):**
   - scanned/rotated/photographed pages
   - European vs US decimal formats
   - multi-page invoices; multiple invoices in one PDF
   - a statement and a quote (must be REJECTed, not extracted)
   - missing fields (no due date, no PO) — must come back None, not invented
   - reverse-charge VAT invoices
   - handwritten annotations over printed values

README headline = the per-field accuracy table + the gate-quality number + the cost table.

## 6. Repo layout (walkthrough + reusable engine)

Structure rules: numbered scripts = video chapters; every script runnable top-to-bottom in the VS Code interactive window; steps stay lean — they import the engine and demo ONE concept, and the only inline definitions are the concept itself (e.g. chapter 3's schema); mermaid diagram in the README before any code; copy-paste friendly.

The numbered scripts live at the repo root, siblings of `extractor/` — that makes imports work with ZERO path configuration in both run modes (a script's own directory lands on `sys.path`; the interactive window's kernel starts in the file's directory). Clone, `uv sync`, run — nothing hidden.

```
ai-invoice-extractor/
  1-ingestion.py       # concept: input adapters — PDF and photo normalize into one Document shape
  2-ai-inference.py    # concept: AI inference — call the API: content + instructions in, plain text out
  3-structured-output.py  # concept: structured outputs — same call, typed schema; the plain-text pain, solved
  4-validation.py      # concept: deterministic validation & gating — rules + confidence → AUTO / REVIEW / REJECT
  5-prompt-chaining.py # concept: prompt chaining — a second AI call verifies critical fields; disagreement → review
  6-schema-swap.py     # concept: schema as contract — swap the profile, same pipeline, new document type
  7-evals.py           # concept: evals — unit tests for AI with an answer key; ~10 docs live, full matrix in evals/
  extractor/           # the reusable engine (every chapter imports from here)
    engine.py          # extract(document, profile) — the generic core
    profiles.py        # DocumentProfile, Rule, GatePolicy
    providers/         # LLMProvider interface; anthropic.py today, openai.py later
    adapters.py        # DocumentLoader: PDF, image → normalized Document (text layer / page images)
    validate.py        # rule runner, locale normalization
    verify.py          # optional prompt-chaining verification
    gate.py
    output.py          # ReviewQueue — flagged docs land in a JSONL file
    utils.py           # demo plumbing: fixture paths, key check, pretty-printers
  profiles/
    iberia_invoice.py
    delivery_note.py   # the swap demo
  evals/
    harness.py         # gold loading, field comparison, accuracy aggregation
    verify_gold.py     # spot-check truth sidecars against the rendered PDFs (no API)
    run_evals.py       # full matrix: all docs, providers, ablations → the README tables
                       # gold set = fixtures/truth (true by construction, verified)
  fixtures/            # synthetic PDFs + photo receipt + generator script
  README.md            # mermaid pipeline diagram + the tables + chapter index
```

Teaching arc — **follow the process; each step introduces the concept the process needs next**:

1. *Input adapters*: a PDF is not text, and a photographed receipt is not a PDF. Show two real inputs (digital PDF → text layer; photo → image) normalizing into one `Document` shape — the rest of the pipeline never thinks about sources again. Tiny script, real concept.
2. *AI inference*: call the API. Content + instructions in, plain text out. Print the answer — it looks great, until you try to use it in code.
3. *Structured output*: the pain of chapter 2 (parsing prose, inconsistent formats) solved by a typed schema. Show the same extraction twice; the contrast IS the lesson.
4. *Validation & gating*: the AI read the document; code now checks it (rules, arithmetic) and decides — AUTO_ACCEPT / NEEDS_REVIEW / REJECT. Human-in-the-loop as a design choice.
5. *Prompt chaining*: some fields matter too much for one opinion — a second, cheaper call verifies critical fields. Flags, never corrects.
6. *Schema as contract*: swap one profile file, process a different document type. The system was never about invoices.
7. *Evals*: unit tests for AI, with an answer key. Chapter runs the loop on ~10 documents, shows the table, then makes one improvement and reruns — the before/after is the lesson. The full matrix (all docs, providers, ablations) lives in `evals/` and feeds the README tables.

Every chapter imports from `extractor/` — implementations live in the package behind proper abstractions (`DocumentLoader` for inputs, `LLMProvider`/`AnthropicProvider` wrapping the selected model), and shared demo plumbing (paths, key check, pretty-printers) lives in `extractor/utils.py`, never in a step. Copy-pasters grab the package plus a chapter script; developers import `extractor/`.

Style rules: plain Python scripts runnable cell-by-cell in the VS Code interactive window, `uv` for deps, no framework, no DB, no UI. The CLI + interactive window is the demo surface.

## 7. Build order (with Claude Code)

1. Fixture generator: synthetic invoices as HTML→PDF templates + one photographed receipt image (FIRST — everything downstream needs documents; the photo powers the chapter-1 adapter demo).
2. `1-ingestion`, `2-ai-inference`, `3-structured-output` — lean steps over the package's adapters + provider. These three are small; get the teaching contrast (plain text → typed schema) right.
3. Round out the `extractor/` package (engine, rules, gate); build `4-validation` on top: rules + confidence gate + JSONL review queue.
4. Gold labels + eval runner; first accuracy/cost tables (`7-evals` v1).
5. Prompt chaining (`5-prompt-chaining`): verification call on critical fields, flag-don't-correct merge; rerun evals for the ablation rows.
6. Failure matrix docs; fix what's fixable (field descriptions, few-shot examples), document what isn't.
7. Second provider; rerun eval table across models.
8. `6-schema-swap` demo (`delivery_note.py`).
9. README with the numbers; record video.

Estimated: 2 weeks at ~10 hrs/wk. API budget ~$10–20.

## 8. Explicitly out of scope (say so in README + video)

PO matching, approval routing, GL coding, ERP integration, OCR-model training, email ingestion, UI. Mention them to show you understand the full AP context — then don't build them. Restraint is the teaching point: this is a system with one AI call, and it never needed to be an agent.

## 9. Video outline

**Format:** no live coding. Code is pre-written; recording = running the chapter scripts cell-by-cell in the interactive window, side by side with the results, explaining. The files are the script: comments = narration cues, cell boundaries = pacing beats, print output = the on-screen visual. Target ~20 minutes total.

*Title: "Automate Invoice Processing with AI (Done Right)"*
*Alternates: "How to Extract Invoice Data with AI" · "AI Invoice Processing That Actually Works" · "Stop Typing Invoices — Let AI Do It"*

Rough time budget (~20 min):

1. (~3 min) The human process + why it's expensive — the Section 1 story, Iberia example, the pipeline diagram: one AI seat in a system of code.
2. (~2 min) Ch. 1 input adapters: PDF and photo → one Document shape.
3. (~2 min) Ch. 2 AI inference: call the API, plain text back — looks great, unusable in code.
4. (~2.5 min) Ch. 3 structured output: same call, typed schema; the contrast is the lesson.
5. (~3 min) Ch. 4 validation & gating: rules catch a seeded wrong digit; AUTO / REVIEW / REJECT.
6. (~2.5 min) Ch. 5 prompt chaining: verification disagreement downgrades a field to review, with the ablation numbers.
7. (~1.5 min) Ch. 6 schema swap: delivery note, same pipeline — the reveal.
8. (~3 min) Ch. 7 evals: answer key, loop, table; make one improvement, rerun, watch the number move. Then the full README tables + the Iberia cost math.
9. (~1 min) Outro: failure matrix honesty in the README; when you WOULD reach for an agent — bridge to the next video.
