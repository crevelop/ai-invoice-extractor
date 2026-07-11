"""Generate the synthetic fixture corpus (SPEC.md §5.5).

Usage:
    uv run python fixtures/generate.py [--out DIR]

Deterministic: same seed → same corpus → same truth sidecars. The photographed
receipt in fixtures/photo/ is user-provided and not touched here.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen import FIXTURE_SEED  # noqa: E402
from gen.corpus import build_corpus  # noqa: E402
from gen.render import page_count  # noqa: E402


def generate(out_dir: Path, seed: int = FIXTURE_SEED) -> dict:
    """Build the corpus and write PDFs, truth sidecars, and MANIFEST.json."""
    rng = random.Random(seed)
    docs = build_corpus(rng)

    for sub in ("docs/invoices", "docs/reject", "truth"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    entries = []
    for doc in docs:
        pdf_rel = f"docs/{doc.subdir}/{doc.name}.pdf"
        truth_rel = f"truth/{doc.name}.json"
        (out_dir / pdf_rel).write_bytes(doc.pdf)
        (out_dir / truth_rel).write_text(doc.truth.model_dump_json(indent=2) + "\n")
        entries.append({
            "file": pdf_rel,
            "template": doc.template,
            "tags": doc.tags,
            "pages": page_count(doc.pdf),
            "truth": truth_rel,
        })

    manifest = {
        "seed": seed,
        "generated_by": "fixtures/generate.py",
        "counts": {
            "invoice_docs": sum(1 for d in docs if d.subdir == "invoices"),
            "reject_docs": sum(1 for d in docs if d.subdir == "reject"),
            "total_docs": len(docs),
            "invoice_records": sum(len(d.truth.invoices) for d in docs),
        },
        "by_template": dict(sorted(Counter(d.template for d in docs).items())),
        "docs": entries,
    }
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def print_summary(manifest: dict) -> None:
    print(f"\nFixture corpus — seed {manifest['seed']}")
    print(f"{'template':<22}{'docs':>6}{'pages':>8}")
    print("-" * 36)
    pages_by_tpl: dict[str, list[int]] = {}
    for e in manifest["docs"]:
        pages_by_tpl.setdefault(e["template"], []).append(e["pages"])
    for tpl, n in manifest["by_template"].items():
        print(f"{tpl:<22}{n:>6}{sum(pages_by_tpl[tpl]):>8}")
    print("-" * 36)
    c = manifest["counts"]
    print(f"{'total PDFs':<22}{c['total_docs']:>6}"
          f"{sum(e['pages'] for e in manifest['docs']):>8}")
    print(f"\ninvoice records: {c['invoice_records']} "
          f"(incl. multi-invoice PDFs) · reject docs: {c['reject_docs']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent,
                        help="output directory (default: fixtures/)")
    args = parser.parse_args()
    print_summary(generate(args.out))
