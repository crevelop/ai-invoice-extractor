"""Deterministic validation: locale-aware amount parsing + the rule runner.

The AI read the document; this module is the code that checks it. Nothing
here makes an API call — it runs the same way on every take.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator

from .profiles import Rule


def normalize_amount(value: object) -> object:
    """Locale-aware numeric cleanup: '1.234,56', '1,234.56', '€ 1 234,56'
    all become '1234.56' — and unit markers ('4 Stk.', '12 uds')
    fall away too. Non-strings pass through untouched."""
    if not isinstance(value, str):
        return value
    s = re.sub(r"[^\d,.\-]", "", value)  # strip currency symbols and spaces
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):  # 1.234,56 — European
            s = s.replace(".", "").replace(",", ".")
        else:  # 1,234.56 — US
            s = s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        # decimal comma (1234,56) vs pure thousands commas (1,234,567)
        s = head.replace(",", "") + ("." + tail if len(tail) <= 2 else tail)
    elif s.count(".") > 1:  # 1.234.567 — European thousands only
        s = s.replace(".", "")
    return s


# A Decimal that accepts numbers the way documents print them: European
# decimals, currency symbols, unit markers. Money is the name schemas use
# for amounts; Numeric fits counts like a quantity column's '4 Stk.'.
Numeric = Annotated[Decimal, BeforeValidator(normalize_amount)]
Money = Numeric


@dataclass(frozen=True)
class RuleResult:
    rule: str
    passed: bool
    detail: str | None = None


def run_rules(data: BaseModel, rules: tuple[Rule, ...]) -> list[RuleResult]:
    """Run every rule; never short-circuit — the review queue wants the full
    list of what failed, not just the first thing."""
    results = []
    for rule in rules:
        detail = rule.check(data)
        results.append(RuleResult(rule.name, passed=detail is None, detail=detail))
    return results
