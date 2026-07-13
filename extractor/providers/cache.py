"""A disk cache around any provider — identical calls stop costing money.

Extraction is deterministic-enough to cache: same document, same model,
same schema, same instructions → reuse the stored answer. Rules, gating
and eval scoring always re-run fresh (they're free); only the API call
is cached. Delete the cache directory to force fresh extractions.
"""

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from ..adapters import Document
from .base import Cost, LLMProvider


class CachedProvider(LLMProvider):
    def __init__(self, inner: LLMProvider, cache_dir: Path | str):
        self.inner = inner
        self.name = f"cached-{inner.name}"
        self.model = inner.model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def has_cached(self, doc: Document, output_model: type[BaseModel],
                   instructions: str) -> bool:
        return self._path(doc, output_model.model_json_schema(),
                          instructions).exists()

    def generate_text(self, doc: Document, instructions: str) -> tuple[str, Cost]:
        path = self._path(doc, "text", instructions)
        if path.exists():
            stored = json.loads(path.read_text())
            self.hits += 1
            return stored["output"], Cost(**stored["cost"])
        text, cost = self.inner.generate_text(doc, instructions)
        self._store(path, text, cost)
        return text, cost

    def extract_structured[T: BaseModel](
        self, doc: Document, output_model: type[T], instructions: str
    ) -> tuple[T, Cost]:
        path = self._path(doc, output_model.model_json_schema(), instructions)
        if path.exists():
            stored = json.loads(path.read_text())
            self.hits += 1
            return (output_model.model_validate(stored["output"]),
                    Cost(**stored["cost"]))
        result, cost = self.inner.extract_structured(doc, output_model,
                                                     instructions)
        self._store(path, result.model_dump(mode="json"), cost)
        return result, cost

    def _path(self, doc: Document, schema, instructions: str) -> Path:
        h = hashlib.sha256()
        h.update(self.inner.name.encode())
        h.update(self.inner.model.encode())
        h.update(json.dumps(schema, sort_keys=True).encode())
        h.update(instructions.encode())
        if doc.kind == "text":
            h.update(doc.text.encode())
        else:
            for png in doc.png_pages():
                h.update(png)
        return self.cache_dir / f"{h.hexdigest()}.json"

    def _store(self, path: Path, output, cost: Cost) -> None:
        self.misses += 1
        path.write_text(json.dumps(
            {"output": output, "cost": cost.model_dump()}))
