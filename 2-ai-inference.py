"""
Chapter 2 — AI inference: ask the model to read the invoice.

Content + instructions in, plain text out. The answer looks perfect —
right up until you try to use it in code.
"""

# %% 1. Setup
# ------------------------------------------------------------------
# One provider object wraps the selected model (extractor/providers/).
# Swapping models — or vendors — later means changing this one line.

import re

from extractor import AnthropicProvider, load
from extractor.utils import INVOICES, require_api_key

require_api_key()
llm = AnthropicProvider()

INSTRUCTIONS = ("Extract the vendor name, invoice number, issue date "
                "and total amount from this invoice.")

# %% 2. Read a Spanish invoice   (1 API call, ~$0.001)
# ------------------------------------------------------------------
# Watch how good this looks:

invoice_1 = load(INVOICES / "t01-es-clean-01.pdf")
answer_1, cost_1 = llm.generate_text(invoice_1, INSTRUCTIONS)

print(answer_1)
print("\ncost:", cost_1)

# %% 3. Same instruction, German invoice   (1 API call)
# ------------------------------------------------------------------

invoice_2 = load(INVOICES / "t04-de-reverse-01.pdf")
answer_2, cost_2 = llm.generate_text(invoice_2, INSTRUCTIONS)

print(answer_2)
print("\ncost:", cost_2)

# %% 4. Now try to USE those answers in code   (no API call)
# ------------------------------------------------------------------
# Two perfect answers — in two different shapes. Pull the total out of
# each one and turn it into a number:

for name, answer in [("invoice 1", answer_1), ("invoice 2", answer_2)]:
    found = re.search(r"[Tt]otal[^\d]*([\d.,]+)", answer)
    if not found:
        print(f"{name}: could not even find a total")
        continue
    total_text = found.group(1)
    try:
        total = float(total_text)
        print(f"{name}: float('{total_text}') gives {total}")
    except ValueError:
        print(f"{name}: float('{total_text}') CRASHES — European number format")

# %% 5. The lesson
# ------------------------------------------------------------------
# The information is all there. The FORMAT is the problem — prose was
# written for humans. Asking nicely ("reply in JSON please!") is a patch
# on the wrong layer. We want a contract, not a request. → chapter 3
