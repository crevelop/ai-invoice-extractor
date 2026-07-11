"""Shared formatting helpers for the layout templates."""

from __future__ import annotations

import html
from datetime import date
from decimal import Decimal
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def esc(s: str) -> str:
    return html.escape(s)


def money_us(d: Decimal) -> str:
    return f"{d:,.2f}"  # 1,234.56


def money_eu(d: Decimal) -> str:
    return f"{d:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")  # 1.234,56


def qty(d: Decimal) -> str:
    return str(int(d)) if d == d.to_integral_value() else money_eu(d)


def date_es(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def date_de(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def date_en(d: date) -> str:
    return d.strftime("%B %-d, %Y")


# --- Handwriting font (T10) -------------------------------------------------
# We could not redistribute a handwriting font with the repo, so T10 degrades
# gracefully: if an OFL-licensed .ttf is dropped into fixtures/gen/assets/
# (e.g. Homemade Apple or Caveat from Google Fonts, license file alongside),
# it is embedded via @font-face; otherwise we fall back to whatever
# handwriting-ish system font exists, ending at generic `cursive`.
HAND_STACK = ('"FixtureHandwriting", "Bradley Hand", "Marker Felt", '
              '"Segoe Print", "Comic Sans MS", cursive')


def handwriting_font_css() -> str:
    fonts = sorted(ASSETS.glob("*.ttf")) if ASSETS.is_dir() else []
    if not fonts:
        return ""
    return (f'@font-face {{ font-family: "FixtureHandwriting"; '
            f'src: url("file://{fonts[0]}"); }}')
