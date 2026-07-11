"""Synthetic fixture generator (SPEC.md §5.5 failure matrix).

Design decision — no lying documents: every generated fixture is internally
consistent (line items sum to subtotal, subtotal + tax = total, reverse-charge
docs carry zero tax). Do NOT add seeded arithmetic errors here. Chapter 4's
"rules catch a wrong digit" demo tampers with the *extracted object* in code,
in a clearly-labeled cell, so the demo is deterministic on every take.

Truth sidecars in fixtures/truth/ are emitted by this generator and are true
by construction; step-4 "hand-verification" means spot-checking them against
the rendered PDFs plus genuinely hand-labeling the photographed receipt.
"""

FIXTURE_SEED = 20260711
