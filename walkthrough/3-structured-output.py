# %% cell 1: setup — .env key, client, model (run this cell first)
# Chapter 3 — Structured outputs: the SAME call as chapter 2, plus a typed
# schema. The contrast is the lesson: prose out → typed object out.

import base64
import io
import json
import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import anthropic
import pypdfium2 as pdfium
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()
assert os.environ.get("ANTHROPIC_API_KEY"), \
    "Missing ANTHROPIC_API_KEY — copy .env.example to .env and add your key."

MODEL = "claude-haiku-4-5"  # same model, same page image, same instruction
# works as a script (__file__) and cell-by-cell in the interactive window (cwd)
_here = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
FIXTURES = next(p / "fixtures" for p in [_here, *_here.parents]
                if (p / "fixtures").is_dir())
client = anthropic.Anthropic()

# %% cell 2: the contract — Pydantic model + the JSON Schema it compiles to
# The contract. A Pydantic model does three jobs at once:
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

# %% cell 3: extract() + first typed result (~$0.002 API call)
# Same call as chapter 2 — messages.parse() instead of messages.create(),
# and the schema rides along. Nothing else changes.


def page_as_b64_png(pdf_path: Path) -> str:
    pdf = pdfium.PdfDocument(pdf_path)
    img = pdf[0].render(scale=2).to_pil()
    img.thumbnail((1568, 1568))
    pdf.close()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


def extract(pdf_path: Path) -> InvoiceSummary:
    response = client.messages.parse(
        model=MODEL,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                 "media_type": "image/png", "data": page_as_b64_png(pdf_path)}},
                {"type": "text", "text": "Extract the vendor name, invoice number, "
                                         "issue date, currency and total from this invoice."},
            ],
        }],
        output_format=InvoiceSummary,
    )
    return response.parsed_output


inv = extract(FIXTURES / "docs/invoices/t01-es-clean-01.pdf")
print(inv)

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
    row = extract(FIXTURES / "docs/invoices" / pdf)
    print(f"{row.vendor_name:<32}{row.invoice_number:<16}"
          f"{row.issue_date.isoformat():<12}{f'{row.total} {row.currency}':>12}")

# %% cell 6: wrap-up (narration only, nothing to run)
# No regex. No format guessing. `row.total` — every time, any vendor.
# But is it CORRECT? The model can still misread a digit. Code can check
# that — deterministically. → chapter 4: validation & gating.
