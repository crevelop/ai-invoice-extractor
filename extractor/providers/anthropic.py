"""Anthropic behind the LLMProvider interface.

This file is the project's single source for model choice and pricing.
Everything Anthropic-specific — the SDK client, the content-block message
format — stays inside this class.
"""

import base64
import os

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

from ..adapters import Document
from .base import Cost, LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    # Cheapest vision-capable Anthropic model (project decision, CLAUDE.md).
    DEFAULT_MODEL = "claude-haiku-4-5"
    PRICING = {  # $ per 1M tokens: (input, output) — add a row per model tried
        "claude-haiku-4-5": (1.00, 5.00),
    }
    MAX_TOKENS = 8192  # dense invoices carry many line items; billed per token used

    def __init__(self, model: str | None = None):
        self.model = model or self.DEFAULT_MODEL
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:  # lazy: importing the package needs no key
            load_dotenv()
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "Missing ANTHROPIC_API_KEY — copy .env.example to .env "
                    "and add your key."
                )
            self._client = anthropic.Anthropic()
        return self._client

    def generate_text(self, doc: Document, instructions: str) -> tuple[str, Cost]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.MAX_TOKENS,
            messages=self._messages(doc, instructions),
        )
        text = next(b.text for b in response.content if b.type == "text")
        return text, self._cost(response.usage)

    def extract_structured[T: BaseModel](
        self, doc: Document, output_model: type[T], instructions: str
    ) -> tuple[T, Cost]:
        # The Pydantic model compiles to a JSON Schema the API enforces.
        # temperature=0: extraction wants the model's single most likely
        # reading, every take — variety is for prose, not for pipelines.
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=self.MAX_TOKENS,
            temperature=0,
            messages=self._messages(doc, instructions),
            output_format=output_model,
        )
        return response.parsed_output, self._cost(response.usage)

    def _messages(self, doc: Document, instructions: str) -> list[dict]:
        """Chapter-1 payoff: the provider only ever asks 'text or images?'."""
        if doc.kind == "text":
            content = [{"type": "text",
                        "text": f"Document text (extracted from a PDF):\n\n{doc.text}"}]
        else:
            content = [{"type": "image",
                        "source": {"type": "base64", "media_type": "image/png",
                                   "data": base64.standard_b64encode(png).decode()}}
                       for png in doc.png_pages()]
        return [{"role": "user",
                 "content": [*content, {"type": "text", "text": instructions}]}]

    def _cost(self, usage) -> Cost:
        price_in, price_out = self.PRICING[self.model]
        return Cost(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            usd=(usage.input_tokens * price_in
                 + usage.output_tokens * price_out) / 1e6,
        )
