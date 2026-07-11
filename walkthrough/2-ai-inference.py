# %% cell 1: setup — .env key, client, model (run this cell first)
# Chapter 2 — AI inference: content + instructions in, plain text out.
# The answer looks perfect — right up until you try to use it in code.

import base64
import io
import os
import re
from pathlib import Path

import anthropic
import pypdfium2 as pdfium
from dotenv import load_dotenv

load_dotenv()
assert os.environ.get("ANTHROPIC_API_KEY"), \
    "Missing ANTHROPIC_API_KEY — copy .env.example to .env and add your key."

# Cheapest vision-capable Anthropic model (project decision, CLAUDE.md).
# Chapters 1–3 are standalone; the single-source constants module arrives
# with the extractor/ package in build step 3.
MODEL = "claude-haiku-4-5"
PRICE_IN, PRICE_OUT = 1.00, 5.00  # $ per 1M tokens

# works as a script (__file__) and cell-by-cell in the interactive window (cwd)
_here = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
FIXTURES = next(p / "fixtures" for p in [_here, *_here.parents]
                if (p / "fixtures").is_dir())
client = anthropic.Anthropic()

# %% cell 2: helpers — page→PNG, ask(), cost() (defines, no output)
# The chapter-1 adapter gave us page images — a vision model reads the page
# exactly like the clerk does. Send one page + one instruction, get text back.


def page_as_b64_png(pdf_path: Path) -> str:
    pdf = pdfium.PdfDocument(pdf_path)
    img = pdf[0].render(scale=2).to_pil()
    img.thumbnail((1568, 1568))
    pdf.close()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


def ask(pdf_path: Path, instructions: str) -> tuple[str, object]:
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                 "media_type": "image/png", "data": page_as_b64_png(pdf_path)}},
                {"type": "text", "text": instructions},
            ],
        }],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return text, response.usage


def cost(usage) -> str:
    dollars = (usage.input_tokens * PRICE_IN + usage.output_tokens * PRICE_OUT) / 1e6
    return f"{usage.input_tokens} in / {usage.output_tokens} out ≈ ${dollars:.4f}"


INSTRUCTIONS = ("Extract the vendor name, invoice number, issue date "
                "and total amount from this invoice.")

# %% cell 3: API call #1 — Spanish invoice (~$0.002)
# Invoice #1 — a Spanish vendor. Watch how good this looks:

answer_1, usage_1 = ask(FIXTURES / "docs/invoices/t01-es-clean-01.pdf", INSTRUCTIONS)
print(answer_1)
print(f"\n[{MODEL} · {cost(usage_1)}]")

# %% cell 4: API call #2 — German invoice, same instruction
# Impressive. Now the exact same instruction on a different vendor — a German
# invoice this time:

answer_2, usage_2 = ask(FIXTURES / "docs/invoices/t04-de-reverse-01.pdf", INSTRUCTIONS)
print(answer_2)
print(f"\n[{MODEL} · {cost(usage_2)}]")

# %% cell 5: the pain — try to parse both answers with code (needs cells 3+4)
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

# %% cell 6: wrap-up (narration only, nothing to run)
# The information is all there. The FORMAT is the problem — prose was written
# for humans. Every prompt tweak ("reply in JSON please!") is a patch on the
# wrong layer. What we want is a contract, not a request. → chapter 3.
