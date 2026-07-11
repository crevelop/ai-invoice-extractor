"""extract(document, profile) — the generic core.

One AI call reads the page (extract), then code takes over: Pydantic parses
(structural validation), rules check the math (business validation), and the
gate decides. AI in exactly one seat; everything around it is deterministic.
"""

from dataclasses import dataclass, field as dc_field
from pathlib import Path

from pydantic import BaseModel, Field, create_model

from . import adapters
from .adapters import Document
from .gate import Decision, decide
from .profiles import Confidence, DocumentProfile
from .providers import anthropic as provider
from .providers.anthropic import Cost
from .validate import RuleResult, run_rules


@dataclass
class FieldMeta:
    """Per-field confidence plus flags: failed rules touching the field now,
    verifier disagreement from chapter 5 later."""

    confidence: Confidence
    flags: list[str] = dc_field(default_factory=list)


@dataclass
class ExtractionResult[T: BaseModel]:
    data: T | None  # typed instance of the profile schema; None on REJECT
    document_type: str  # what the model says the page actually is
    field_meta: dict[str, FieldMeta]
    validation: list[RuleResult]
    cost: Cost
    decision: Decision
    reasons: list[str]  # why the gate decided what it decided


_INSTRUCTIONS = """\
You are the extraction step of an accounts-payable pipeline.

First decide what kind of business document this is (invoice, receipt, \
statement, quote, delivery note, ...) and report it in `document_type`.

Only if it is a {document_type}: fill `data`, reading every value exactly as \
printed. A field the document does not show is null — never invent a value. \
If it is NOT a {document_type}, set `data` to null.

Formats: dates as YYYY-MM-DD; amounts with a decimal point and no thousands \
separators.

For every extracted field report your confidence:
- "high" — clearly printed and unambiguous
- "medium" — readable but ambiguous (unusual format, dense layout, faint print)
- "low" — obscured, overwritten by hand, cut off, or partly guessed\
"""

# One envelope model per profile schema, built once and cached.
_envelopes: dict[tuple[type[BaseModel], str], type[BaseModel]] = {}


def _envelope_model(profile: DocumentProfile) -> type[BaseModel]:
    """Wrap the profile schema in what the API call actually returns: the
    data, a document-type check, and self-reported per-field confidence."""
    key = (profile.schema, profile.document_type)
    if key not in _envelopes:
        confidence_model = create_model(
            f"{profile.schema.__name__}Confidence",
            **{name: (Confidence, ...) for name in profile.schema.model_fields},
        )
        _envelopes[key] = create_model(
            f"{profile.schema.__name__}Extraction",
            document_type=(str, Field(
                description="What this document actually is, lowercase — "
                            "'invoice', 'receipt', 'statement', 'quote', ...")),
            data=(profile.schema | None, Field(
                description="The extracted fields; null if the document is "
                            f"not a {profile.document_type}.")),
            field_confidence=(confidence_model | None, Field(
                description="Your confidence per extracted field; null if "
                            "data is null.")),
        )
    return _envelopes[key]


def extract[T: BaseModel](
    document: Document | Path | str,
    profile: DocumentProfile[T],
    *,
    model: str | None = None,
) -> ExtractionResult[T]:
    doc = document if isinstance(document, Document) else adapters.load(document)

    # The one AI call.
    envelope, cost = provider.call_structured(
        doc,
        _envelope_model(profile),
        _INSTRUCTIONS.format(document_type=profile.document_type),
        model=model,
    )

    # From here on: code.
    data = envelope.data
    field_meta: dict[str, FieldMeta] = {}
    validation: list[RuleResult] = []
    if data is not None:
        reported = (envelope.field_confidence.model_dump()
                    if envelope.field_confidence else {})
        field_meta = {name: FieldMeta(confidence=reported.get(name, "low"))
                      for name in profile.schema.model_fields}
        validation = run_rules(data, profile.rules)
        for rule, result in zip(profile.rules, validation):
            if not result.passed:
                for name in rule.fields:
                    if name in field_meta:
                        field_meta[name].flags.append(f"rule:{rule.name}")

    decision, reasons = decide(
        profile,
        envelope.document_type,
        {name: meta.confidence for name, meta in field_meta.items()},
        validation,
        has_data=data is not None,
    )
    return ExtractionResult(
        data=data,
        document_type=envelope.document_type,
        field_meta=field_meta,
        validation=validation,
        cost=cost,
        decision=decision,
        reasons=reasons,
    )
