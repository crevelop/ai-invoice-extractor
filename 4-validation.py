# %% cell 1: setup — .env key, the Iberia profile (run this cell first)
# Chapter 4 — Validation & gating: the AI read the document; code now checks
# it and decides. AUTO_ACCEPT / NEEDS_REVIEW / REJECT.

import json
from dataclasses import replace
from pathlib import Path

from extractor import Decision, decide, extract, run_rules
from extractor.utils import (
    FIXTURES, INVOICES, REJECTS, ROOT, require_api_key, show,
)
from profiles.iberia_invoice import IBERIA_INVOICE, duplicate_rule

require_api_key()

# %% cell 2: the profile — schema + rules + gate, printed (no API call)
# Everything specific to Iberia Home Goods lives in ONE object
# (profiles/iberia_invoice.py). The schema says what to extract; the rules
# are deterministic math the model can't sweet-talk its way past; the gate
# policy says when a human looks.

profile = IBERIA_INVOICE
print(f"document type   {profile.document_type}")
print(f"schema          {profile.schema.__name__} "
      f"({len(profile.schema.model_fields)} fields)")
print(f"critical fields {', '.join(profile.gate.critical_fields)}")
print("rules:")
for rule in profile.rules:
    print(f"  · {rule.name}")

# %% cell 3: the happy path — one clean invoice, end to end (~$0.003)
# One call runs the whole pipeline: adapter → AI extraction → Pydantic parse
# → rules → gate. Every rule passes, every field is confident: no human
# needs to see this document.

ok = extract(INVOICES / "t01-es-clean-01.pdf", profile)
show(ok)

# %% cell 4: DEMO TAMPER — flip one digit, watch the rules catch it (no API call)
# The classic failure: the model misreads ONE digit in the total. We simulate
# it deterministically — take the good extraction and corrupt it in code —
# so this take works every time. Validation is plain Python: re-running it
# costs nothing and calls no API.

bad = ok.data.model_copy(update={"total": ok.data.total + 600})  # 1110.76 → 1710.76
print(f"tampered total: {ok.data.total} → {bad.total}\n")

checks = run_rules(bad, profile.rules)
confidences = {name: meta.confidence for name, meta in ok.field_meta.items()}
decision, reasons = decide(profile, "invoice", confidences, checks)

print(f"decision: {decision}")
for reason in reasons:
    print(f"  ! {reason}")
# The arithmetic doesn't care how confident the model felt. A wrong digit
# breaks the math → NEEDS_REVIEW, with the exact discrepancy for the clerk.

# %% cell 5: REJECT — feed it a quote, not an invoice (~$0.003)
# r2-quote-01.pdf is a price quote. It has amounts, a vendor, line items —
# a naive extractor would happily "extract" it and someone would pay a
# document that isn't a bill. The document-type check refuses it instead.

quote = extract(REJECTS / "r2-quote-01.pdf", profile)
show(quote)

# %% cell 6: the gate at work — a mini batch + the review queue (6 calls, ~$0.02)
# A morning's mail: clean invoices, a reverse-charge invoice, one with no due
# date, a scrawled-over one, a bank statement, and a duplicate (same PDF
# twice — the double-payment classic). One stateful rule joins the profile
# for the batch: rules are data, adding one is a one-liner.

batch_profile = replace(profile, rules=(*profile.rules, duplicate_rule(set())))

mail = [
    "docs/invoices/t01-es-clean-02.pdf",
    "docs/invoices/t04-de-reverse-01.pdf",
    "docs/invoices/t06-en-minimal-01.pdf",
    "docs/invoices/t10-es-handwritten-01.pdf",
    "docs/reject/r1-statement-01.pdf",
    "docs/invoices/t01-es-clean-02.pdf",  # the duplicate
]

queue_path = ROOT / "review_queue.jsonl"
queue_path.unlink(missing_ok=True)

print(f"{'document':<28}{'decision':<15}{'why'}")
print("-" * 76)
with queue_path.open("a") as queue:
    for name in mail:
        result = extract(FIXTURES / name, batch_profile)
        why = result.reasons[0] if result.reasons else ""
        print(f"{Path(name).name:<28}{result.decision:<15}{why[:44]}")
        if result.decision is not Decision.AUTO_ACCEPT:
            queue.write(json.dumps({
                "source": Path(name).name,
                "decision": result.decision,
                "reasons": result.reasons,
                "data": result.data.model_dump(mode="json") if result.data else None,
            }) + "\n")

flagged = len(queue_path.read_text().splitlines())
print(f"\nreview queue: {queue_path.name} — {flagged} of {len(mail)} documents")

# %% cell 7: wrap-up (narration only, nothing to run)
# The clerk stopped retyping 800 invoices; they review the handful the gate
# flags — each with the reason attached. That's human-in-the-loop as a
# design choice, not an afterthought.
#
# One honest weakness remains: confidence is SELF-reported — the model
# grading its own homework. For the fields that move money, we can buy a
# second, independent opinion. → chapter 5: prompt chaining.
