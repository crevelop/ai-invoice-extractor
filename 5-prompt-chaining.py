"""
Chapter 5 — Prompt chaining: a second opinion on the fields that move money.

Chapter 4 ended on an honest weakness: the confidence scores are the model
grading its own homework. For fields where a wrong value costs real money,
we buy one more AI call — an independent verifier that re-reads the document
and checks the claims. It flags disagreements; it never corrects them.
"""

# %% 1. Setup
# ------------------------------------------------------------------

from extractor import extract
from extractor.utils import INVOICES, answer_key, require_api_key, show
from profiles.iberia_invoice import IBERIA_INVOICE

require_api_key()
profile = IBERIA_INVOICE

# %% 2. The failure the gate cannot see   (1 API call, ~$0.01)
# ------------------------------------------------------------------
# The evals caught this one: on scanned German invoices the model reads
# the prominent CUSTOMER block as the vendor — the real vendor hides in
# the letterhead — and reports high confidence doing it. The math is
# internally consistent, so every rule passes.

scan = INVOICES / "t09-scanned-03.pdf"
first = extract(scan, profile)
show(first)

truth = answer_key(scan)
print("\nthe letterhead says:", truth["vendor_name"], "·", truth["vendor_tax_id"])

# Everything the gate can see looks perfect: rules pass, confidence high,
# AUTO_ACCEPT — and the vendor fields are wrong. Rules catch bad math;
# they can't catch a wrong-but-consistent reading. Only a second reader can.

# %% 3. The second opinion   (2 API calls, ~$0.01)
# ------------------------------------------------------------------
# extract(..., verify=True) chains a second call after the first: the
# verifier re-reads ONLY the critical fields — blind. The claimed values
# never enter its context, so there is nothing to anchor on or politely
# agree with. Then CODE compares the two readings; a mismatch downgrades
# the field's confidence to "low"... and that's all it does. The chapter-4
# gate, unchanged, turns low confidence on a critical field into
# NEEDS_REVIEW.

second = extract(scan, profile, verify=True)
show(second)

# The verifier read the letterhead (see the ⚑ flag: the real tax id).
# Two readers disagree → that field is uncertain → a person decides.

# %% 4. Flags, never corrects
# ------------------------------------------------------------------
# Why not let the verifier overwrite the value? Because "the second model
# wins" is a coin flip, not a policy. Two readings agreeing is evidence;
# two readings disagreeing is uncertainty — and uncertainty is a human's
# job, not a third API call's. So the document goes to review carrying
# BOTH readings, and the extracted data is never silently edited.
#
# Note what stayed code: deciding whether two readings match. Models are
# bad at string equality — they'd flag '5.323,18' against '5323.18' — so
# the readings are parsed through the schema's own types (Money again)
# and compared as values, not strings. AI reads; code judges. The chain
# is fixed and linear; still no agent in sight.

# %% 5. What certainty costs   (2 API calls, ~$0.01)
# ------------------------------------------------------------------
# On a clean digital invoice the verifier agrees everywhere: critical
# fields rise to "high", the document still auto-accepts, and the price
# roughly doubles. That is the trade — you pay a second read to know the
# money fields were not one model's opinion.

clean = extract(INVOICES / "t01-es-clean-01.pdf", profile, verify=True)
show(clean)

print(f"\none call : {first.cost}")
print(f"two calls: {second.cost}")

# %% 6. Does the second call pay for itself?
# ------------------------------------------------------------------
# That's a business question, so it gets a measured answer, not a vibe:
# evals/run_evals.py --verify reruns all 43 documents with verification on
# — the ablation table in the README compares gate error and $/doc with
# and without it. One flag, same engine, measurable trade-off.
#
# Next weakness: this whole pipeline still says "invoice" everywhere.
# Or does it? Swap one profile file and find out. → chapter 6
