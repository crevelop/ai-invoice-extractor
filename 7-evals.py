"""
Chapter 7 — Evals: unit tests for AI, with an answer key.

How do you know the extractor is good — and STAYS good when you change a
prompt? Run it against documents whose correct answers you already know,
and count. Running this whole lesson costs about $0.15.

(Evals were built early on purpose — build order ≠ chapter order — so
chapters 5 and 6 could be measured as they landed. The gate-error history
table in the README is that payoff: 8.1% → 2.8%, one number per change.)
"""

# %% 1. Setup
# ------------------------------------------------------------------
# The comparison logic lives in evals/harness.py.

from evals.harness import (compare_fields, field_accuracy, load_gold,
                           sample, with_description)
from extractor import extract
from extractor.utils import require_api_key
from profiles.iberia_invoice import IBERIA_INVOICE

require_api_key()

# %% 2. The answer key
# ------------------------------------------------------------------
# fixtures/truth/ holds one verified JSON per document — what a correct
# extraction MUST say. Here is the answer sheet for one invoice:

gold = load_gold()
invoices = [doc for doc in gold if doc.kind == "invoice"]
example = invoices[0]

print("document      :", example.pdf.name)
print("invoice number:", example.truth.invoice_number)
print("issue date    :", example.truth.issue_date)
print("total         :", example.truth.total, example.truth.currency)

# %% 3. Run the exam   (9 API calls, ~$0.05)
# ------------------------------------------------------------------
# One document per layout template — clean, dense, multi-page, scanned,
# handwritten... Extract each one and grade it against the answer key.

exam = [doc for doc in sample(gold) if doc.kind == "invoice"]

scores = []
for doc in exam:
    result = extract(doc.pdf, IBERIA_INVOICE)
    checks = compare_fields(result.data, doc.truth)
    scores.append(checks)
    print(doc.pdf.name, "→", sum(checks.values()), "of", len(checks),
          "fields correct")

# %% 4. The report card
# ------------------------------------------------------------------
# Aggregate by field: which fields is the model reliable on, which fail?

for field, (correct, total) in field_accuracy(scores).items():
    print(f"{field}: {correct}/{total}")

# %% 5. The experiment: two versions of one sentence   (no API call)
# ------------------------------------------------------------------
# Field descriptions are the prompt (chapter 3). vendor_name's used to
# be one bland line — until the evals caught the model reading the
# CUSTOMER as the vendor. Bring the old sentence back, side by side:

old_profile = with_description(IBERIA_INVOICE, "vendor_name",
                               "Legal name of the vendor")

print("old:", old_profile.schema.model_fields["vendor_name"].description)
print("new:", IBERIA_INVOICE.schema.model_fields["vendor_name"].description)

# %% 6. Same scan, both sentences   (2 API calls, ~$0.02)
# ------------------------------------------------------------------
# Extract the noisiest scan twice. The ONLY difference is that sentence:

scan = next(doc for doc in gold if doc.pdf.name == "t09-scanned-03.pdf")

for label, profile in [("old", old_profile), ("new", IBERIA_INVOICE)]:
    data = extract(scan.pdf, profile).data
    print(f"{label} sentence reads:", data.vendor_name, "·", data.vendor_tax_id)
print("the document says:", scan.truth.vendor_name, "·", scan.truth.vendor_tax_id)

# The old sentence doesn't make a typo — it picks the WRONG COMPANY:
# Iberia itself, the customer. The new one finds the real vendor (minus
# one letter: that's pixels, not prompts — chapter 5's verifier catches it).

# %% 7. Was that luck? Grade every scan   (8 API calls, ~$0.08)
# ------------------------------------------------------------------
# One document proves nothing — that's this chapter's whole point.
# Run both sentences over ALL the scans and ask the answer key one
# question: did it identify the right company (vendor_tax_id)?

scans = [doc for doc in gold if doc.template == "t09-scanned"]

for label, profile in [("old", old_profile), ("new", IBERIA_INVOICE)]:
    graded = [compare_fields(extract(doc.pdf, profile).data, doc.truth)
              for doc in scans]
    correct, total = field_accuracy(graded)["vendor_tax_id"]
    print(f"{label} sentence: right company on {correct}/{total} scans")

# One sentence changed, and a number moved. Without the answer key that
# fix would have been a feeling; with it, it's a regression test.

# %% 8. Why this matters
# ------------------------------------------------------------------
# This table is the difference between "the demo looked good" and "we
# measured it". Change a prompt, rerun, compare the numbers — regression
# tests for AI. The full matrix (all 43 documents, gate quality, cost
# tables) lives in evals/run_evals.py; its results are committed to the
# README, so you never have to run it yourself.
