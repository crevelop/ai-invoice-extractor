"""Anthropic provider: ONE schema-enforced structured-output call.

This file is the project's single source for model choice and pricing
(chapters 2-3 inlined these constants before the package existed).
"""

import base64
import io
import os

import anthropic
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel

from ..adapters import Document

# Cheapest vision-capable Anthropic model (project decision, CLAUDE.md).
MODEL = "claude-haiku-4-5"
PRICING = {  # $ per 1M tokens: (input, output)
    "claude-haiku-4-5": (1.00, 5.00),
}
MAX_TOKENS = 8192  # dense invoices carry many line items; billing is per token used


class Cost(BaseModel):
    input_tokens: int
    output_tokens: int
    usd: float

    def __str__(self) -> str:
        return (f"{self.input_tokens} in / {self.output_tokens} out "
                f"≈ ${self.usd:.4f}")


_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        load_dotenv()
        assert os.environ.get("ANTHROPIC_API_KEY"), (
            "Missing ANTHROPIC_API_KEY — copy .env.example to .env and add your key."
        )
        _client = anthropic.Anthropic()
    return _client


def _png_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


def _content_blocks(doc: Document) -> list[dict]:
    """Chapter-1 payoff: the provider only ever asks 'text or images?'."""
    if doc.kind == "text":
        return [{"type": "text",
                 "text": f"Document text (extracted from a PDF):\n\n{doc.text}"}]
    return [{"type": "image",
             "source": {"type": "base64", "media_type": "image/png",
                        "data": _png_b64(img)}}
            for img in doc.page_images]


def call_structured[T: BaseModel](
    doc: Document,
    output_model: type[T],
    instructions: str,
    model: str | None = None,
) -> tuple[T, Cost]:
    """The one AI call in the whole pipeline. The Pydantic model compiles to
    a JSON Schema the API enforces on the response."""
    model = model or MODEL
    response = client().messages.parse(
        model=model,
        max_tokens=MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": [*_content_blocks(doc),
                        {"type": "text", "text": instructions}],
        }],
        output_format=output_model,
    )
    price_in, price_out = PRICING[model]
    usage = response.usage
    cost = Cost(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        usd=(usage.input_tokens * price_in + usage.output_tokens * price_out) / 1e6,
    )
    return response.parsed_output, cost
