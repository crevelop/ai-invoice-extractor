"""
Chapter 6 — Schema as contract: the system was never about invoices.

Five chapters of pipeline — adapters, one AI call, rules, gate, verifier —
and none of it knows what an invoice is. Everything specific lives in one
profile object. Swap it, and the same engine reads a new document type.
"""

# %% 1. Setup
# ------------------------------------------------------------------

from extractor import extract
from extractor.utils import INVOICES, OTHER, require_api_key, show
from profiles.iberia_invoice import IBERIA_INVOICE

require_api_key()

# %% 2. A delivery note hits the invoice pipeline   (1 API call, ~$0.01)
# ------------------------------------------------------------------
# The albarán that travels with a shipment: same vendor, same articles,
# quantities — but NO prices. It is not a bill.

note = OTHER / "x1-delivery-note-01.pdf"
show(extract(note, IBERIA_INVOICE))

# REJECT — not a half-extraction with invented amounts. The document-type
# check from chapter 4 is the pipeline's immune system.

# %% 3. Swap the profile   (1 API call, ~$0.01)
# ------------------------------------------------------------------
# profiles/delivery_note.py is one page: a 5-field schema, two rules, a
# gate policy. That file is everything the pipeline knows about albaranes.

from profiles.delivery_note import DELIVERY_NOTE  # noqa: E402 — the swap IS the demo

show(extract(note, DELIVERY_NOTE))

# Same engine, same call — typed DeliveryNote out. Nothing in extractor/
# changed; the CLI swaps the same way (--profile profiles.delivery_note:DELIVERY_NOTE).

# %% 4. And the contract cuts both ways   (1 API call, ~$0.01)
# ------------------------------------------------------------------
# Feed an invoice to the delivery-note pipeline: refused, same mechanism.

show(extract(INVOICES / "t01-es-clean-01.pdf", DELIVERY_NOTE))

# One engine, any document type — the profile is the product. Is any of
# this actually good? That's not a feeling, it's a number. → chapter 7
