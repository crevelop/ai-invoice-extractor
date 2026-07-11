"""Schema-driven document extraction: one AI call in a system of code.

The chapters 1-3 walkthrough code, packaged (build step 3). Public surface:

    result = extract("invoice.pdf", profile=IBERIA_INVOICE)
    result.data        # typed instance of the profile's schema (None on REJECT)
    result.field_meta  # per-field confidence + flags
    result.validation  # passed/failed business rules
    result.cost        # tokens in/out + $ estimate
    result.decision    # AUTO_ACCEPT | NEEDS_REVIEW | REJECT
"""

from .adapters import Document, load
from .engine import ExtractionResult, FieldMeta, extract
from .gate import Decision, decide
from .profiles import DocumentProfile, GatePolicy, Rule
from .validate import Money, RuleResult, normalize_amount, run_rules

__all__ = [
    "Decision",
    "Document",
    "DocumentProfile",
    "ExtractionResult",
    "FieldMeta",
    "GatePolicy",
    "Money",
    "Rule",
    "RuleResult",
    "decide",
    "extract",
    "load",
    "normalize_amount",
    "run_rules",
]
