"""Schema-driven document extraction: one AI call in a system of code.

Public surface:

    result = extract("invoice.pdf", profile=IBERIA_INVOICE)
    result.data        # typed instance of the profile's schema (None on REJECT)
    result.field_meta  # per-field confidence + flags
    result.validation  # passed/failed business rules
    result.cost        # tokens in/out + $ estimate
    result.decision    # AUTO_ACCEPT | NEEDS_REVIEW | REJECT

Pieces (one module per pipeline stage): DocumentLoader normalizes inputs,
LLMProvider wraps the selected model, rules + gate turn the extraction into
a decision. Swap the profile to change the use case; swap the provider to
change the LLM.
"""

from .adapters import Document, DocumentLoader, load
from .engine import ExtractionResult, FieldMeta, extract
from .gate import Decision, decide
from .output import ReviewQueue
from .profiles import DocumentProfile, GatePolicy, Rule
from .providers import (
    AnthropicProvider,
    CachedProvider,
    Cost,
    LLMProvider,
    default_provider,
)
from .validate import Money, RuleResult, normalize_amount, run_rules
from .verify import merge_checks, verify_fields

__all__ = [
    "AnthropicProvider",
    "CachedProvider",
    "Cost",
    "Decision",
    "Document",
    "DocumentLoader",
    "DocumentProfile",
    "ExtractionResult",
    "FieldMeta",
    "GatePolicy",
    "LLMProvider",
    "Money",
    "ReviewQueue",
    "Rule",
    "RuleResult",
    "decide",
    "default_provider",
    "extract",
    "load",
    "merge_checks",
    "normalize_amount",
    "run_rules",
    "verify_fields",
]
