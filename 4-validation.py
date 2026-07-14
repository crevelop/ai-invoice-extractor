"""
Chapter 4 — Validation & gating: the AI reads, code decides.

Deterministic rules check the math the model can't be trusted with, and a
gate sorts every document into one of three buckets: AUTO_ACCEPT (no human
needed), NEEDS_REVIEW (a person checks), REJECT (not an invoice at all).
"""

# %% 1. Setup
# ------------------------------------------------------------------

from extractor import Decision, ReviewQueue, decide, extract, run_rules
from extractor.utils import INVOICES, REJECTS, require_api_key, show
from profiles.iberia_invoice import IBERIA_INVOICE, duplicate_rule

require_api_key()
profile = IBERIA_INVOICE

# %% 2. The profile: everything specific to ONE company
# ------------------------------------------------------------------
# Schema (what to extract), rules (checks the model can't sweet-talk its
# way past), gate policy (when a human looks). The engine knows none of it —
# it all lives in profiles/iberia_invoice.py.

print("document type  :", profile.document_type)
print("schema         :", profile.schema.__name__)
print("critical fields:", ", ".join(profile.gate.critical_fields))
print("rules:")
for rule in profile.rules:
    print("  ·", rule.name)

# %% 3. The happy path   (1 API call, ~$0.006)
# ------------------------------------------------------------------
# One call runs the whole pipeline: load → AI reads → rules check the
# math → gate decides. Everything passes: no human sees this document.

good = extract(INVOICES / "t01-es-clean-01.pdf", profile)
show(good)

# %% 4. Flip one digit — watch the rules catch it   (no API call)
# ------------------------------------------------------------------
# The classic failure: the model misreads ONE digit in the total. We fake
# it on purpose (so this demo works on every take) by corrupting the good
# extraction, then re-running the checks. Validation is plain code — free.

tampered = good.data.model_copy(update={"total": good.data.total + 600})
print("total:", good.data.total, "→", tampered.total, "\n")

checks = run_rules(tampered, profile.rules)
decision, reasons = decide(profile, good.document_type, good.confidence, checks)

print("decision:", decision)
for reason in reasons:
    print("  !", reason)

# The math doesn't care how confident the model felt. A wrong digit breaks
# the arithmetic → NEEDS_REVIEW, with the exact discrepancy for the clerk.

# %% 5. Feed it something that is NOT an invoice   (1 API call)
# ------------------------------------------------------------------
# A price quote has amounts, a vendor, line items... a naive extractor
# would happily "extract" it — and someone would pay a document that was
# never a bill. The document-type check refuses it instead.

quote = extract(REJECTS / "r2-quote-01.pdf", profile)
show(quote)

# %% 6. A morning's mail   (6 API calls, ~$0.03)
# ------------------------------------------------------------------
# Six documents: clean invoices, one with no due date, a scrawled-over
# one, a bank statement — and the same invoice twice (the double-payment
# classic). One extra rule joins the profile for the batch.

profile = IBERIA_INVOICE.with_rule(duplicate_rule())

mail = [
    INVOICES / "t01-es-clean-02.pdf",
    INVOICES / "t04-de-reverse-01.pdf",
    INVOICES / "t06-en-minimal-01.pdf",
    INVOICES / "t10-es-handwritten-01.pdf",
    REJECTS / "r1-statement-01.pdf",
    INVOICES / "t01-es-clean-02.pdf",  # the duplicate
]

results = []
for pdf in mail:
    result = extract(pdf, profile)
    results.append(result)
    print(pdf.name, "→", result.decision)

# %% 7. The review queue — what the clerk actually opens
# ------------------------------------------------------------------
# Everything the gate didn't auto-accept lands in one file, with the
# reasons attached. The clerk reviews a handful, not the whole mailbox.

queue = ReviewQueue("review_queue.jsonl")
for result in results:
    if result.decision != Decision.AUTO_ACCEPT:
        queue.add(result)

print(f"the clerk reviews {len(queue)} of {len(mail)} documents:")
for entry in queue:
    print("  ·", entry["source"], "—", entry["reasons"][0])

# %% 8. What we built
# ------------------------------------------------------------------
# Human-in-the-loop as a design choice: nothing doubtful gets posted, and
# every flagged document says WHY. One honest weakness remains — the
# confidence scores are the model grading its own homework. For fields
# that move money, we can buy a second, independent opinion. → chapter 5
