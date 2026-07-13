"""
Chapter 3 — Structured output: same call, but with a contract.

Instead of asking nicely for a format, we hand the API a schema it must
fill in. Prose out becomes a typed object out — the contrast with
chapter 2 is the whole lesson.
"""

# %% 1. Setup
# ------------------------------------------------------------------
# Same provider, same document, same instruction as chapter 2.

from datetime import date, timedelta
from decimal import Decimal

from pydantic import BaseModel, Field

from extractor import AnthropicProvider, load
from extractor.utils import INVOICES, require_api_key

require_api_key()
llm = AnthropicProvider()

INSTRUCTIONS = ("Extract the vendor name, invoice number, issue date, "
                "currency and total from this invoice.")

# %% 2. The contract — this schema IS the chapter
# ------------------------------------------------------------------
# One Pydantic model does three jobs at once:
#   1. it becomes a JSON Schema the API *enforces* on the response
#   2. the field descriptions double as extraction instructions
#   3. it validates the reply — real dates, exact decimal money


class InvoiceSummary(BaseModel):
    vendor_name: str = Field(description="Legal name of the issuing vendor")
    invoice_number: str = Field(description="Exactly as printed, incl. prefixes")
    issue_date: date
    currency: str = Field(description="ISO 4217 code, e.g. EUR")
    total: Decimal = Field(description="Grand total including tax. Use a decimal "
                                       "point and no thousands separators.")


# %% 3. The same call as chapter 2 — plus the schema   (1 API call)
# ------------------------------------------------------------------
# Prose can no longer come back. The reply IS an InvoiceSummary.

invoice = load(INVOICES / "t01-es-clean-01.pdf")
summary, cost = llm.extract_structured(invoice, InvoiceSummary, INSTRUCTIONS)

print(summary)
print("\ncost:", cost)

# %% 4. Not text — a typed object   (no API call)
# ------------------------------------------------------------------
# Everything chapter 2 couldn't do:

print("total is a", type(summary.total).__name__, "→", summary.total)
print("date is a", type(summary.issue_date).__name__, "→", summary.issue_date)
print("due in 30 days:", summary.issue_date + timedelta(days=30))
print("total × 2:", summary.total * 2)

# %% 5. The chapter-2 pain, replayed   (2 API calls)
# ------------------------------------------------------------------
# The same two invoices — different vendors, languages, number formats.
# One shape out, every time:

for pdf in ["t01-es-clean-01.pdf", "t04-de-reverse-01.pdf"]:
    row, cost = llm.extract_structured(load(INVOICES / pdf),
                                       InvoiceSummary, INSTRUCTIONS)
    print(row.vendor_name, "|", row.invoice_number, "|",
          row.issue_date, "|", row.total, row.currency)

# %% 6. But is it CORRECT?
# ------------------------------------------------------------------
# No regex, no format guessing — but the model can still misread a digit.
# Code can check that, deterministically. → chapter 4
