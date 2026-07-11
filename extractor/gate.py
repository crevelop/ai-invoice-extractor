"""The gate: rule results + per-field confidence -> one of three decisions.

Human-in-the-loop as a design choice: the pipeline never silently posts a
doubtful document — it routes it to a person, with reasons attached.
"""

from enum import StrEnum

from .profiles import CONFIDENCE_RANK, Confidence, DocumentProfile
from .validate import RuleResult


class Decision(StrEnum):
    AUTO_ACCEPT = "AUTO_ACCEPT"  # straight to the ERP, no human touches it
    NEEDS_REVIEW = "NEEDS_REVIEW"  # a person confirms; reasons say what to look at
    REJECT = "REJECT"  # not the document type this profile extracts


def decide(
    profile: DocumentProfile,
    document_type: str,
    confidence: dict[str, Confidence],
    validation: list[RuleResult],
    *,
    has_data: bool = True,
) -> tuple[Decision, list[str]]:
    """Pure function of the extraction outcome — no API, fully deterministic."""
    if document_type != profile.document_type:
        return Decision.REJECT, [
            f"document looks like '{document_type}', "
            f"expected '{profile.document_type}'"
        ]
    if not has_data:
        return Decision.REJECT, ["model returned no extractable data"]

    reasons = [f"rule failed: {r.rule} — {r.detail}" for r in validation if not r.passed]
    floor = CONFIDENCE_RANK[profile.gate.min_critical_confidence]
    for name in profile.gate.critical_fields:
        level = confidence.get(name, "low")
        if CONFIDENCE_RANK[level] < floor:
            reasons.append(f"critical field '{name}' has {level} confidence")

    if reasons:
        return Decision.NEEDS_REVIEW, reasons
    return Decision.AUTO_ACCEPT, []
