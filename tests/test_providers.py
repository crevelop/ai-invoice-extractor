"""Provider tests — everything except the network call itself.
Message building, cost math, and OpenAI's stricter schema mode are plain
code, so they get plain tests (no API keys needed)."""

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractor import AnthropicProvider, Document, OpenAIProvider  # noqa: E402
from extractor.engine import _envelope_model  # noqa: E402
from extractor.verify import _readings_model  # noqa: E402
from profiles.iberia_invoice import IBERIA_INVOICE  # noqa: E402

TEXT_DOC = Document(source="a.pdf", kind="text", text="Rechnung Nr. 7")
IMAGE_DOC = Document(source="b.pdf", kind="image",
                     page_images=[Image.new("RGB", (8, 8), "white")])


@pytest.mark.parametrize(
    "provider_cls, text_type",
    [(AnthropicProvider, "text"), (OpenAIProvider, "input_text")],
)
def test_text_document_travels_as_text(provider_cls, text_type):
    messages = provider_cls()._messages(TEXT_DOC, "extract it")
    parts = messages[0]["content"]
    assert parts[0]["type"] == text_type
    assert "Rechnung Nr. 7" in parts[0]["text"]
    assert parts[-1] == {"type": text_type, "text": "extract it"}


def test_image_document_travels_as_anthropic_image_blocks():
    parts = AnthropicProvider()._messages(IMAGE_DOC, "extract it")[0]["content"]
    assert parts[0]["type"] == "image"
    assert parts[0]["source"]["media_type"] == "image/png"


def test_image_document_travels_as_openai_data_urls():
    # Responses API: input_image with the data URL as a plain string.
    parts = OpenAIProvider()._messages(IMAGE_DOC, "extract it")[0]["content"]
    assert parts[0]["type"] == "input_image"
    assert parts[0]["image_url"].startswith("data:image/png;base64,")


def test_openai_cost_uses_its_own_pricing():
    class Usage:  # Responses API reports input/output tokens
        input_tokens = 1_000_000
        output_tokens = 1_000_000

    cost = OpenAIProvider()._cost(Usage())
    price_in, price_out = OpenAIProvider.PRICING[OpenAIProvider.DEFAULT_MODEL]
    assert cost.usd == price_in + price_out


def test_our_schemas_survive_openai_strict_mode():
    # OpenAI's structured outputs are stricter than Anthropic's: every
    # property required, no extras. The SDK validates client-side, so a
    # schema regression fails here — not in a paid API call.
    from openai.lib._pydantic import to_strict_json_schema

    to_strict_json_schema(_envelope_model(IBERIA_INVOICE))
    to_strict_json_schema(_readings_model(IBERIA_INVOICE.gate.critical_fields))
