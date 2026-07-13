"""
Chapter 5 — Prompt chaining: a second opinion on the fields that move money.

Chapter 4's weakness: confidence is the model grading its own homework.
For critical fields we buy one more AI call — an independent re-read.
It flags disagreements; it never corrects them.
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
# On this scanned German invoice the model reads the prominent CUSTOMER
# block as the vendor — and reports high confidence doing it.

scan = INVOICES / "t09-scanned-03.pdf"
first = extract(scan, profile)
show(first)

truth = answer_key(scan)
print("\nthe letterhead says:", truth["vendor_name"], "·", truth["vendor_tax_id"])

# Rules pass, confidence high, AUTO_ACCEPT — and the vendor is wrong.
# Rules catch bad math, not a wrong-but-consistent reading.

# %% 3. The second opinion   (2 API calls, ~$0.01)
# ------------------------------------------------------------------
# verify=True chains a second call: re-read ONLY the critical fields,
# blind — no claimed values in its context, nothing to anchor on. Code
# compares the two readings; a mismatch downgrades confidence to "low",
# and the chapter-4 gate does the rest.

second = extract(scan, profile, verify=True)
show(second)

# The verifier read the letterhead (the ⚑ flag carries the real tax id).
# Two readers disagree → that field is uncertain → a person decides.

# %% 4. Flags, never corrects
# ------------------------------------------------------------------
# Why not let the verifier overwrite the value? "The second model wins"
# is a coin flip, not a policy. Agreement is evidence; disagreement is
# uncertainty — a human's job. The document goes to review carrying BOTH
# readings; the data is never silently edited.
#
# And code decides whether two readings match: models are bad at string
# equality ('5.323,18' vs '5323.18'), Money isn't. AI reads; code judges.

# %% 5. What certainty costs   (2 API calls, ~$0.01)
# ------------------------------------------------------------------
# On a clean invoice the verifier agrees everywhere: still AUTO_ACCEPT,
# roughly double the price. That's the trade.

clean = extract(INVOICES / "t01-es-clean-01.pdf", profile, verify=True)
show(clean)

print(f"\none call : {first.cost}")
print(f"two calls: {second.cost}")

# %% 6. Does the second call pay for itself?
# ------------------------------------------------------------------
# A business question gets a measured answer: evals/run_evals.py --verify
# reruns all 43 documents — the README table shows gate error 8.1% → 2.9%
# for a fifth of a cent per document.
#
# Next: this pipeline still says "invoice" everywhere. Or does it?
# Swap one profile file and find out. → chapter 6
