"""
Chapter 5 — Prompt chaining: a second opinion on the fields that move money.

Chapter 4's weakness: confidence is the model grading its own homework.
So we chain a second AI call — an independent re-read of the critical
fields. It flags disagreements; it never corrects them.
"""

# %% 1. Setup
# ------------------------------------------------------------------

from extractor import extract, verify
from extractor.utils import INVOICES, answer_key, require_api_key, show
from profiles.iberia_invoice import IBERIA_INVOICE

require_api_key()
profile = IBERIA_INVOICE

# %% 2. The failure the gate cannot see   (1 API call, ~$0.01)
# ------------------------------------------------------------------
# On this noisy scan the model drops one letter from the vendor's legal
# name — the name the ERP matches the payee on — and reports high
# confidence doing it.

scan = INVOICES / "t09-scanned-03.pdf"
first = extract(scan, profile)
show(first)

truth = answer_key(scan)
print("\nthe letterhead says:", truth["vendor_name"], "·", truth["vendor_tax_id"])

# Rules pass, confidence high, AUTO_ACCEPT — and the name is wrong.
# Rules catch bad math; they can't catch a bad read of good math.

# %% 3. Chain the second call   (1 API call, ~$0.01)
# ------------------------------------------------------------------
# verify() re-reads ONLY the critical fields, blind — it never sees what
# the first call extracted. Code compares the two readings; a mismatch
# downgrades confidence, and the same chapter-4 gate flips to review.

second = verify(first, profile)
show(second)

# Both readings on screen (the ⚑ flags), data untouched: the verifier
# flags, it never corrects. Two readers disagree → a person decides.

# %% 4. The happy path   (2 API calls, ~$0.01)
# ------------------------------------------------------------------
# On a clean invoice the two reads agree everywhere: still AUTO_ACCEPT,
# roughly double the price. That's the trade — and it composes: verify
# wraps extract, nothing upstream changes.

clean = verify(extract(INVOICES / "t01-es-clean-01.pdf", profile), profile)
show(clean)

print(f"\nread once : {first.cost}")
print(f"read twice: {second.cost}")

# %% 5. Does the second call pay for itself?
# ------------------------------------------------------------------
# Measured, not guessed: evals/run_evals.py --verify reruns all 43
# documents — gate error drops 5.4% → 2.8% for under a fifth of a cent
# per document (table in the README).
#
# Next: swap one profile file, extract a different document. → chapter 6
