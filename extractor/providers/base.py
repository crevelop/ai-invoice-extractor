"""The provider interface: any vision-capable LLM behind two methods.

The engine and the walkthrough talk to LLMProvider, never to a vendor SDK.
Adding a provider (OpenAI lands in build step 7) means one new subclass —
nothing else in the system changes.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from ..adapters import Document


class Cost(BaseModel):
    """Tokens in/out plus a dollar estimate — attached to every call."""

    input_tokens: int
    output_tokens: int
    usd: float

    def __str__(self) -> str:
        return (f"{self.input_tokens} in / {self.output_tokens} out "
                f"≈ ${self.usd:.4f}")

    def __add__(self, other: "Cost") -> "Cost":
        """Costs accumulate — a verified extraction is the sum of two calls."""
        return Cost(input_tokens=self.input_tokens + other.input_tokens,
                    output_tokens=self.output_tokens + other.output_tokens,
                    usd=self.usd + other.usd)


class LLMProvider(ABC):
    """One selected model behind two calls.

    generate_text      — content + instructions in, prose out (chapter 2)
    extract_structured — same call with a schema the API enforces (chapter 3+)
    """

    name: str
    model: str

    @abstractmethod
    def generate_text(self, doc: Document, instructions: str) -> tuple[str, Cost]:
        """Send the document and instructions, get plain text back."""

    @abstractmethod
    def extract_structured[T: BaseModel](
        self, doc: Document, output_model: type[T], instructions: str
    ) -> tuple[T, Cost]:
        """Same call, schema-enforced: returns a validated output_model
        instance instead of prose."""
