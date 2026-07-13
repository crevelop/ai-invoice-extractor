"""OpenAI behind the same LLMProvider interface.

The point of this file is how little is in it: the engine, the chapters and
the evals never change when the LLM does. Everything OpenAI-specific — the
SDK client, the data-URL image format, the strict JSON-schema mode — stays
inside this class.
"""

import base64
import os

import openai
from dotenv import load_dotenv
from pydantic import BaseModel

from ..adapters import Document
from .base import Cost, LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    # OpenAI's small tier as of July 2026 — the fair peer to Haiku 4.5.
    DEFAULT_MODEL = "gpt-5.4-mini"
    PRICING = {  # $ per 1M tokens: (input, output) — add a row per model tried
        "gpt-5.4-mini": (0.75, 4.50),
        "gpt-4o-mini": (0.15, 0.60),  # two generations older; the budget floor
    }
    MAX_TOKENS = 8192  # dense invoices carry many line items; billed per token used

    def __init__(self, model: str | None = None):
        self.model = model or self.DEFAULT_MODEL
        self._client: openai.OpenAI | None = None

    @property
    def client(self) -> openai.OpenAI:
        if self._client is None:  # lazy: importing the package needs no key
            load_dotenv()
            assert os.environ.get("OPENAI_API_KEY"), (
                "Missing OPENAI_API_KEY — add it to .env to use the "
                "OpenAI provider."
            )
            self._client = openai.OpenAI()
        return self._client

    def generate_text(self, doc: Document, instructions: str) -> tuple[str, Cost]:
        response = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=self.MAX_TOKENS,
            messages=self._messages(doc, instructions),
            **self._sampling(),
        )
        return response.choices[0].message.content, self._cost(response.usage)

    def extract_structured[T: BaseModel](
        self, doc: Document, output_model: type[T], instructions: str
    ) -> tuple[T, Cost]:
        # Same idea as Anthropic's parse: the Pydantic model compiles to a
        # JSON Schema the API enforces (OpenAI calls it structured outputs).
        response = self.client.chat.completions.parse(
            model=self.model,
            max_completion_tokens=self.MAX_TOKENS,
            messages=self._messages(doc, instructions),
            response_format=output_model,
            **self._sampling(),
        )
        return response.choices[0].message.parsed, self._cost(response.usage)

    def _sampling(self) -> dict:
        """Reasoning-tier models (gpt-5*) fix temperature at the default and
        reject the parameter; everything older gets the extraction-friendly
        temperature=0 (the single most likely reading, every take)."""
        return {} if self.model.startswith("gpt-5") else {"temperature": 0}

    def _messages(self, doc: Document, instructions: str) -> list[dict]:
        """Chapter-1 payoff again: the provider only asks 'text or images?'."""
        if doc.kind == "text":
            content = [{"type": "text",
                        "text": f"Document text (extracted from a PDF):\n\n{doc.text}"}]
        else:
            content = [{"type": "image_url",
                        "image_url": {"url": "data:image/png;base64,"
                                      + base64.standard_b64encode(png).decode()}}
                       for png in doc.png_pages()]
        return [{"role": "user",
                 "content": [*content, {"type": "text", "text": instructions}]}]

    def _cost(self, usage) -> Cost:
        price_in, price_out = self.PRICING[self.model]
        return Cost(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            usd=(usage.prompt_tokens * price_in
                 + usage.completion_tokens * price_out) / 1e6,
        )
