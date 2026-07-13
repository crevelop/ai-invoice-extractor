"""DocumentProfile: the ONE thing that changes per company / use case.

The pipeline is generic — swap the profile, extract a different document
type. A profile packages what to extract (schema), how to check it (rules)
and when to trust it (gate policy).
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Literal

from pydantic import BaseModel

Confidence = Literal["high", "medium", "low"]
CONFIDENCE_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class Rule:
    """One deterministic business check. check() returns None when the rule
    passes, or a human-readable failure detail when it doesn't."""

    name: str
    check: Callable[[BaseModel], str | None]
    fields: tuple[str, ...] = ()  # schema fields involved — flagged on failure


@dataclass(frozen=True)
class GatePolicy:
    """Thresholds for AUTO_ACCEPT / NEEDS_REVIEW — a business decision (cost
    of a wrong auto-post vs. cost of a human review), not an ML metric."""

    critical_fields: tuple[str, ...] = ()
    # A critical field reported below this confidence forces NEEDS_REVIEW.
    min_critical_confidence: Confidence = "medium"


@dataclass(frozen=True)
class DocumentProfile[T: BaseModel]:
    """Schema + rules + gate = the contract. Same engine, any document type."""

    schema: type[T]
    document_type: str = "invoice"  # anything else on the page -> REJECT
    rules: tuple[Rule, ...] = ()
    examples: tuple = ()  # few-shot examples for hard layouts (later chapter)
    gate: GatePolicy = field(default_factory=GatePolicy)

    def with_rule(self, rule: Rule) -> "DocumentProfile[T]":
        """A new profile with one more rule. Profiles are immutable —
        adding a rule gives you a copy, the original stays untouched."""
        return replace(self, rules=(*self.rules, rule))
