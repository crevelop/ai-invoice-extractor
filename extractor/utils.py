"""Shared demo plumbing for the chapter scripts — presentation only, never
pipeline logic. Paths, the API-key check, and pretty-printers live here so
each lesson shows nothing but the concept it teaches.
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent  # the repo root
FIXTURES = ROOT / "fixtures"
INVOICES = FIXTURES / "docs" / "invoices"
REJECTS = FIXTURES / "docs" / "reject"
OTHER = FIXTURES / "docs" / "other"  # non-invoice docs (the schema swap)


def require_api_key() -> None:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "Missing ANTHROPIC_API_KEY — copy .env.example to .env and add your key."
        )


def answer_key(pdf: Path) -> dict:
    """The verified correct values for a fixture document — its truth
    sidecar, the same answer key the evals score against."""
    sidecar = FIXTURES / "truth" / f"{pdf.stem}.json"
    return json.loads(sidecar.read_text())["invoices"][0]


def sample_photo() -> Path:
    """The photographed receipt; prefers the real photo over the committed
    placeholder once it exists."""
    photos = sorted(p for p in (FIXTURES / "photo").iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    return next((p for p in photos if "placeholder" not in p.name), photos[0])


def strip_fence(text: str) -> str:
    """Peel a ```json ... ``` markdown fence off a model answer. The patch
    every codebase grows once 'reply with JSON' starts coming back fenced."""
    match = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", text, re.DOTALL)
    return match.group(1) if match else text


def show_answer(text: str) -> None:
    """Print a model answer. In the VS Code interactive window it renders
    as formatted markdown (the way a chat app would show it); running as a
    plain script it prints the raw text, asterisks and all."""
    try:
        import IPython

        shell = IPython.get_ipython()
        # ZMQInteractiveShell = a Jupyter kernel (the interactive window)
        if shell is not None and type(shell).__name__ == "ZMQInteractiveShell":
            from IPython.display import Markdown, display

            display(Markdown(text))
            return
    except ImportError:
        pass
    print(text)


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
    width = max(len(name) for name in result.field_meta) + 2
    print(f"  {'field':<{width}}{'value':<34}{'confidence'}")
    for name, meta in result.field_meta.items():
        value = getattr(result.data, name)
        text = f"{len(value)} items" if name == "line_items" else str(value)
        flags = f"   ⚑ {', '.join(meta.flags)}" if meta.flags else ""
        print(f"  {name:<{width}}{text[:32]:<34}{meta.confidence}{flags}")
