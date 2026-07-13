# %% cell 1: setup — .env key, provider (run this cell first)
# Chapter 3 — Structured outputs: the SAME call as chapter 2, plus a typed
# schema. The contrast is the lesson: prose out → typed object out.

import json
from datetime import date, timedelta
from decimal import Decimal

from pydantic import BaseModel, Field

from extractor import AnthropicProvider, load
from walkthrough.utils import INVOICES, require_api_key

require_api_key()
llm = AnthropicProvider()  # same model, same document, same instruction

INSTRUCTIONS = ("Extract the vendor name, invoice number, issue date, "
                "currency and total from this invoice.")

# %% cell 2: the contract — a Pydantic model + the JSON Schema it compiles to
# This schema is the whole concept of the chapter, so it lives right here.
# One Pydantic model does three jobs at once:
#   1. it compiles to a JSON Schema the API *enforces* on the response
#   2. field descriptions double as extraction instructions
#   3. it parses/validates the reply — Decimal for money, date for dates


class InvoiceSummary(BaseModel):
    vendor_name: str = Field(description="Legal name of the issuing vendor")
    invoice_number: str = Field(description="Exactly as printed, incl. prefixes")
    issue_date: date
    currency: str = Field(description="ISO 4217 code, e.g. EUR")
    total: Decimal = Field(description="Grand total including tax. Use a decimal "
                                       "point and no thousands separators.")


print(json.dumps(InvoiceSummary.model_json_schema(), indent=2)[:520], "…")

# %% cell 3: the same call, schema-enforced — first typed result (~$0.002)
# extract_structured() is generate_text() with the schema riding along.
# Nothing else changes — and prose can no longer come back.

inv, cost = llm.extract_structured(load(INVOICES / "t01-es-clean-01.pdf"),
                                   InvoiceSummary, INSTRUCTIONS)
print(inv)
print(f"\n[{llm.model} · {cost}]")

# %% cell 4: typed payoff — Decimal math + date arithmetic (needs cell 3's `inv`)
# Not a string — a typed object. The things chapter 2 couldn't do:

print(f"inv.total       = {inv.total}  ({type(inv.total).__name__})")
print(f"inv.issue_date  = {inv.issue_date}  ({type(inv.issue_date).__name__})")
print(f"due in 30 days  = {inv.issue_date + timedelta(days=30)}  (real date arithmetic)")
print(f"total × 2       = {inv.total * 2}  (exact Decimal math, no float drift)")

# %% cell 5: the chapter-2 pain, replayed — two vendors, one shape (2 API calls)
# And the chapter-2 pain, replayed: the same two invoices, different vendors,
# different languages, different number formats — one shape out.

print(f"{'vendor':<32}{'invoice #':<16}{'date':<12}{'total':>12}")
print("-" * 72)
for pdf in ["t01-es-clean-01.pdf", "t04-de-reverse-01.pdf"]:
    row, _ = llm.extract_structured(load(INVOICES / pdf),
                                    InvoiceSummary, INSTRUCTIONS)
    print(f"{row.vendor_name:<32}{row.invoice_number:<16}"
          f"{row.issue_date.isoformat():<12}{f'{row.total} {row.currency}':>12}")

# %% cell 6: wrap-up (narration only, nothing to run)
# No regex. No format guessing. `row.total` — every time, any vendor.
# But is it CORRECT? The model can still misread a digit. Code can check
# that — deterministically. → chapter 4: validation & gating.
