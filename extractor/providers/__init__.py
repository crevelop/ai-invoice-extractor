"""Model providers behind one interface (LLMProvider).

Anthropic today; openai.py lands in build step 7 so the eval table can
compare providers without touching the engine or the walkthrough.
"""

from .anthropic import AnthropicProvider
from .base import Cost, LLMProvider
from .cache import CachedProvider

_default: LLMProvider | None = None


def default_provider() -> LLMProvider:
    """The provider used when nothing is passed explicitly. Swap the class
    here — or pass provider= to extract() — to change LLMs."""
    global _default
    if _default is None:
        _default = AnthropicProvider()
    return _default


__all__ = ["AnthropicProvider", "CachedProvider", "Cost", "LLMProvider",
           "default_provider"]
