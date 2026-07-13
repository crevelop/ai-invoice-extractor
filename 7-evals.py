"""
Chapter 7 — Evals: unit tests for AI, with an answer key.

How do you know the extractor is good — and STAYS good when you change a
prompt? Run it against documents whose correct answers you already know,
and count. Running this whole lesson costs about $0.05.

(Chapters 5 and 6 don't exist yet — evals get built early on purpose,
so every later change can be measured.)
"""

# %% 1. Setup
# ------------------------------------------------------------------
# The comparison logic lives in evals/harness.py.

from evals.harness import compare_fields, field_accuracy, load_gold, sample
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

# %% 5. Why this matters
# ------------------------------------------------------------------
# This table is the difference between "the demo looked good" and "we
# measured it". Change a prompt, rerun, compare the numbers — regression
# tests for AI. The full matrix (all 43 documents, gate quality, cost
# tables) lives in evals/run_evals.py; its results are committed to the
# README, so you never have to run it yourself.
