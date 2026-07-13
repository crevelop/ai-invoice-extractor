"""Output stage: the review queue — the human side of the gate.

Every document the gate doesn't auto-accept lands in one JSONL file
(one JSON object per line) with the reasons attached. Deliberately
simple: a real deployment might post to a ticket system or an inbox
instead — same idea, different destination.
"""

import json
from pathlib import Path

from .engine import ExtractionResult


class ReviewQueue:
    """A fresh queue file per run, so every demo take is repeatable.
    A production queue would append across runs instead."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.entries: list[dict] = []
        self.path.unlink(missing_ok=True)

    def add(self, result: ExtractionResult) -> None:
        entry = {
            "source": result.source,
            "decision": str(result.decision),
            "reasons": result.reasons,
            "data": result.data.model_dump(mode="json") if result.data else None,
        }
        self.entries.append(entry)
        with self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)
