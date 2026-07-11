"""Shared walkthrough plumbing — presentation only, never pipeline logic.

Paths, the API-key check, and pretty-printers live here so each step shows
nothing but the concept it teaches.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent  # the repo root
FIXTURES = ROOT / "fixtures"
INVOICES = FIXTURES / "docs" / "invoices"
REJECTS = FIXTURES / "docs" / "reject"


def require_api_key() -> None:
    load_dotenv(ROOT / ".env")
    assert os.environ.get("ANTHROPIC_API_KEY"), (
        "Missing ANTHROPIC_API_KEY — copy .env.example to .env and add your key."
    )


def sample_photo() -> Path:
    """The photographed receipt; prefers the real photo over the committed
    placeholder once it exists."""
    photos = sorted(p for p in (FIXTURES / "photo").iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    return next((p for p in photos if "placeholder" not in p.name), photos[0])


def show(result) -> None:
    """One ExtractionResult, one screen: decision, checks, fields, cost."""
    print(f"decision: {result.decision}   [{result.cost}]")
    for reason in result.reasons:
        print(f"  ! {reason}")
    for check in result.validation:
        mark = "✓" if check.passed else "✗"
        detail = f" — {check.detail}" if check.detail else ""
        print(f"  {mark} {check.rule}{detail}")
    if result.data is None:
        print(f"  (no data extracted — document read as '{result.document_type}')")
        return
    print(f"  {'field':<16}{'value':<34}{'confidence'}")
    for name, meta in result.field_meta.items():
        value = getattr(result.data, name)
        text = f"{len(value)} items" if name == "line_items" else str(value)
        flags = f"   ⚑ {', '.join(meta.flags)}" if meta.flags else ""
        print(f"  {name:<16}{text[:32]:<34}{meta.confidence}{flags}")
