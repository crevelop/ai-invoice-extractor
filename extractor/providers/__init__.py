"""Model providers behind one interface (LLMProvider).

Two vendors, one contract: the engine, the chapters and the evals talk to
LLMProvider and never notice which company answers.
"""

from .anthropic import AnthropicProvider
from .base import Cost, LLMProvider
from .cache import CachedProvider
from .openai import OpenAIProvider

_default: LLMProvider | None = None


def default_provider() -> LLMProvider:
    """The provider used when nothing is passed explicitly. Swap the class
    here — or pass provider= to extract() — to change LLMs."""
    global _default
    if _default is None:
        _default = AnthropicProvider()
    return _default


__all__ = ["AnthropicProvider", "CachedProvider", "Cost", "LLMProvider",
           "OpenAIProvider", "default_provider"]
