"""Verification pass: a second opinion on the fields that move money.

Prompt chaining in the evaluator pattern — a separate step chained after
extract(), not a flag on it:

    result = verify(extract("invoice.pdf", profile), profile)

The second call re-reads ONLY the critical fields, blind: the claimed
values never enter its context, so there is nothing to anchor on or agree
with. Deterministic code compares the two readings. The verifier flags, it
never corrects: matching reads raise a field's confidence, a mismatch
downgrades it to "low" — and the gate's existing critical-field floor turns
that into NEEDS_REVIEW. Two reads agreeing is evidence; two reads
disagreeing is uncertainty, and uncertainty is a human's job, not a third
API call's.

Cost control: only the critical fields are re-read, and the verifier can be
a different model (provider=). Here the extractor already runs the cheapest
vision-capable tier, so the default second opinion is the same model on a
much narrower brief.
"""

import re
from dataclasses import replace

from pydantic import BaseModel, Field, ValidationError, create_model

from .adapters import Document
from .engine import ExtractionResult, FieldMeta
from .gate import decide
from .profiles import DocumentProfile
from .providers import Cost, LLMProvider, default_provider

_INSTRUCTIONS = """\
You are the verification step of an accounts-payable pipeline: a second, \
independent reading of the fields that matter most. Report each requested \
field exactly as the document shows it — your reading is compared against \
another reader's to catch mistakes.

Business documents name several parties. Attribute each field to the right \
one: fields about the document's issuer (vendor, supplier, seller) must be \
read from the party who ISSUED the document — letterhead, logo, stamp, bank \
details — never from the customer, recipient or addressee.

Formats: dates as YYYY-MM-DD; amounts with a decimal point and no thousands \
separators.\
"""

# One readings model per critical-field tuple, built once and cached.
_readings_models: dict[tuple[str, ...], type[BaseModel]] = {}


def _readings_model(fields: tuple[str, ...]) -> type[BaseModel]:
    """Deliberately generic — field names only, none of the profile schema's
    descriptions. The verifier must not inherit the extraction's prompt
    engineering: shared hints mean shared blind spots (measured: an example
    tax id in a field description steered BOTH readers to the same wrong
    block of the page). Independent briefs make disagreement a real signal."""
    if fields not in _readings_models:
        _readings_models[fields] = create_model(
            "CriticalFieldReadings",
            **{name: (str, Field(description="Exactly as the document "
                                             "shows it"))
               for name in fields},
        )
    return _readings_models[fields]


def verify_fields(
    doc: Document,
    fields: tuple[str, ...],
    provider: LLMProvider,
) -> tuple[dict[str, str], Cost]:
    """The second AI call: document in, the verifier's own reading of each
    critical field out. It never sees what the first call extracted —
    by design, this function cannot even be handed the claims.

    Fields are read in the given order, and order matters: values generate
    one after another, so an early unambiguous field anchors the later
    ones. Put distinctive identifiers (a tax id) before ambiguous prose
    (a company name) — measured on the vendor/customer-confusion scans,
    name-first made the verifier repeat the extractor's mistake."""
    readings, cost = provider.extract_structured(
        doc, _readings_model(fields), _INSTRUCTIONS)
    return {name: getattr(readings, name) for name in fields}, cost


def _same_value(data: BaseModel, name: str, reading: str) -> bool:
    """Deterministic comparison of the two reads: parse the verifier's
    reading through the schema's own field type and compare typed values.
    Models are bad at string equality — '5.323,18' and '5323.18' are the
    same amount — so Money's locale-aware parsing settles the format
    question the same way it did at extraction time."""
    try:
        patched = type(data).model_validate(
            {**data.model_dump(), name: reading})
    except ValidationError:
        return False
    got, want = getattr(patched, name), getattr(data, name)
    if isinstance(want, str):
        # Text fields (names, ids) compare like values, not bytes: casing,
        # punctuation and spacing are typography, not disagreement.
        return _normalize(got) == _normalize(want)
    return got == want


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def merge_checks(field_meta: dict, readings: dict[str, str],
                 data: BaseModel) -> None:
    """Fold the second read into the per-field metadata — flag, never correct.

    A matching read is the best confidence evidence we have (two independent
    readings agree) → "high". A mismatch → "low" plus a flag carrying the
    verifier's reading, so the reviewer sees both candidate values; the gate
    does the rest. The extracted data itself is never touched: when two
    readings differ, "the second model wins" would be a coin flip, not a
    policy.
    """
    for name, reading in readings.items():
        meta = field_meta[name]
        if _same_value(data, name, reading):
            meta.confidence = "high"
        else:
            meta.confidence = "low"
            meta.flags.append(f"verifier read '{reading}'")


def verify[T: BaseModel](
    result: ExtractionResult[T],
    profile: DocumentProfile[T],
    *,
    provider: LLMProvider | None = None,
) -> ExtractionResult[T]:
    """The chain's second link: extraction result in, verified result out.

    Re-reads the critical fields from the result's document, folds the
    second read into the confidence metadata, and lets the same gate decide
    again. Costs accumulate. The original result is left untouched, so the
    two are easy to compare side by side."""
    if result.data is None or not profile.gate.critical_fields:
        return result  # nothing extracted or nothing critical: no-op

    readings, cost = verify_fields(
        result.document, profile.gate.critical_fields,
        provider or default_provider())
    field_meta = {name: FieldMeta(meta.confidence, [*meta.flags])
                  for name, meta in result.field_meta.items()}
    merge_checks(field_meta, readings, result.data)

    decision, reasons = decide(
        profile,
        result.document_type,
        {name: meta.confidence for name, meta in field_meta.items()},
        result.validation,
    )
    return replace(result, field_meta=field_meta, cost=result.cost + cost,
                   decision=decision, reasons=reasons)
