"""
Chapter 2 — AI inference: ask the model to read the invoice.

Content + instructions in, plain text out. The answer looks perfect —
right up until you try to use it in code.
"""

# %% 1. Setup
# ------------------------------------------------------------------
# One provider object wraps the selected model (extractor/providers/).
# Swapping models — or vendors — later means changing this one line.

import json
import re

from extractor import AnthropicProvider, load
from extractor.utils import INVOICES, require_api_key, show_answer

require_api_key()
llm = AnthropicProvider()

INSTRUCTIONS = ("Extract the vendor name, invoice number, issue date "
                "and total amount from this invoice.")

# %% 2. Read a Spanish invoice   (1 API call, ~$0.001)
# ------------------------------------------------------------------
# Watch how good this looks:

invoice_1 = load(INVOICES / "t01-es-clean-01.pdf")
answer_1, cost_1 = llm.generate_text(invoice_1, INSTRUCTIONS)

show_answer(answer_1)  # renders the markdown, like a chat app would
print("\ncost:", cost_1)

# %% 3. Same instruction, German invoice   (1 API call)
# ------------------------------------------------------------------

invoice_2 = load(INVOICES / "t04-de-reverse-01.pdf")
answer_2, cost_2 = llm.generate_text(invoice_2, INSTRUCTIONS)

show_answer(answer_2)
print("\ncost:", cost_2)

# %% 4. Now BE the next line of code   (no API call)
# ------------------------------------------------------------------
# The rendering above was for OUR eyes. Code receives the raw characters —
# headers, asterisks and all. Pull the total out and turn it into a number:

found = re.search(r"[Tt]otal[^\d]*([\d.,]+)", answer_1)
print("the regex found:", found.group(1))

float(found.group(1))  # ValueError — a European-format number

# %% 5. The same failure, systematically   (no API call)
# ------------------------------------------------------------------
# That traceback wasn't bad luck. Run both answers through the same two
# lines of consumer code and log every way they fall over:

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

# %% 6. The obvious patch: "reply in JSON please!"   (2 API calls)
# ------------------------------------------------------------------
# Everyone's first fix. Same two invoices, one sentence added — watch
# what we actually get back:

for name, pdf in [("invoice 1", "t01-es-clean-01.pdf"),
                  ("invoice 2", "t04-de-reverse-01.pdf")]:
    answer, _ = llm.generate_text(load(INVOICES / pdf),
                                  INSTRUCTIONS + " Reply with JSON only.")
    try:
        data = json.loads(answer)
    except json.JSONDecodeError:
        print(f"{name}: not even valid JSON — starts with {answer[:30]!r}")
        continue
    total = next((v for k, v in data.items() if "total" in k.lower()), None)
    print(f"{name}: parses! keys = {list(data)}")
    print(f"   but total is a {type(total).__name__}: {total!r}")

# %% 7. The lesson
# ------------------------------------------------------------------
# A polite request is not a contract. Maybe it parses, maybe it comes
# fenced in ```json; the keys are whatever the model picked today; the
# total is a string in whatever format the page printed. Nothing here
# is ENFORCED — and a model update can quietly change all of it.
# We don't want to ask for a shape. We want to guarantee one. → chapter 3
