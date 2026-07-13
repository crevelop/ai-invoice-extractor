# %% cell 1: setup — .env key, provider (run this cell first)
# Chapter 2 — AI inference: content + instructions in, plain text out.
# The answer looks perfect — right up until you try to use it in code.
#
# The chapter-1 adapter feeds the model whatever the Document carries —
# the text layer here, page images for scans. AnthropicProvider wraps the
# selected model (extractor/providers/); swapping LLMs is this one line.

import re

from extractor import AnthropicProvider, load
from walkthrough.utils import INVOICES, require_api_key

require_api_key()
llm = AnthropicProvider()  # the one line that picks the model

INSTRUCTIONS = ("Extract the vendor name, invoice number, issue date "
                "and total amount from this invoice.")

# %% cell 2: API call #1 — Spanish invoice (~$0.002)
# Invoice #1 — a Spanish vendor. Watch how good this looks:

answer_1, cost_1 = llm.generate_text(load(INVOICES / "t01-es-clean-01.pdf"),
                                     INSTRUCTIONS)
print(answer_1)
print(f"\n[{llm.model} · {cost_1}]")

# %% cell 3: API call #2 — German invoice, same instruction
# Impressive. Now the exact same instruction on a different vendor — a German
# invoice this time:

answer_2, cost_2 = llm.generate_text(load(INVOICES / "t04-de-reverse-01.pdf"),
                                     INSTRUCTIONS)
print(answer_2)
print(f"\n[{llm.model} · {cost_2}]")

# %% cell 4: the pain — try to parse both answers with code (needs cells 2+3)
# Two perfect answers... in two different shapes. Different labels, different
# ordering, different number formats. Now try to USE them — pull the total
# out with code:

for name, answer in [("invoice 1", answer_1), ("invoice 2", answer_2)]:
    match = re.search(r"[Tt]otal[^\d]*([\d.,]+)", answer)
    raw = match.group(1) if match else "NO MATCH"
    try:
        value = float(raw)
        verdict = f"float() gives {value}"
    except ValueError:
        verdict = f"float() ValueError — {raw!r} is European-formatted!"
    print(f"{name}: regex found {raw!r:<14} → {verdict}")

# %% cell 5: wrap-up (narration only, nothing to run)
# The information is all there. The FORMAT is the problem — prose was written
# for humans. Every prompt tweak ("reply in JSON please!") is a patch on the
# wrong layer. What we want is a contract, not a request. → chapter 3.
