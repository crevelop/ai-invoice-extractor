"""The full eval matrix: every document, scored against the gold set.

You do NOT need to run this to follow the walkthrough — its output tables
are committed to the README. It exists for anyone changing the system
(prompts, rules, models) who wants to know what got better or worse.

Guardrails:
- prints the estimated cost and asks before spending (skip with --yes)
- extractions cache to evals/cache/ — re-runs with unchanged prompts,
  schema and model are free; delete the directory to force fresh calls
- --sample runs one document per template (~12 docs) for quick iteration

Run: uv run python evals/run_evals.py [--sample] [--yes] [--model NAME]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals import harness  # noqa: E402
from extractor import AnthropicProvider, CachedProvider, Decision, extract, load  # noqa: E402
from extractor.engine import _INSTRUCTIONS, _envelope_model  # noqa: E402
from profiles.iberia_invoice import IBERIA_INVOICE  # noqa: E402

EST_COST_PER_DOC = 0.006  # observed average with claude-haiku-4-5
CACHE_DIR = Path(__file__).parent / "cache"
RESULTS_PATH = Path(__file__).parent / "results.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="store_true",
                        help="one document per template (~12 docs)")
    parser.add_argument("--yes", action="store_true",
                        help="skip the cost confirmation")
    parser.add_argument("--model", default=None,
                        help="model name (default: the project default)")
    args = parser.parse_args()

    profile = IBERIA_INVOICE
    gold = harness.load_gold()
    docs = harness.sample(gold) if args.sample else gold
    provider = CachedProvider(AnthropicProvider(args.model), CACHE_DIR)

    # ── cost gate: load every document, count the ones not yet cached
    documents = {g.pdf.name: load(g.pdf) for g in docs}
    envelope = _envelope_model(profile)
    instructions = _INSTRUCTIONS.format(document_type=profile.document_type)
    uncached = {g.pdf.name for g in docs if not provider.has_cached(
        documents[g.pdf.name], envelope, instructions)}
    estimate = len(uncached) * EST_COST_PER_DOC
    print(f"{len(docs)} documents · {len(uncached)} need a fresh API call "
          f"(~${estimate:.2f}) · {len(docs) - len(uncached)} from cache\n")
    if uncached and not args.yes:
        if input("proceed? [y/N] ").strip().lower() != "y":
            print("aborted — nothing spent")
            return 1

    # ── run
    rows = []  # per-field checks, single-invoice docs only
    records = []
    by_template: dict[str, list[dict]] = {}
    spent_usd = 0.0
    equivalent_usd = 0.0

    for g in docs:
        result = extract(documents[g.pdf.name], profile, provider=provider)
        equivalent_usd += result.cost.usd
        if g.pdf.name in uncached:
            spent_usd += result.cost.usd
        record = {
            "doc": g.pdf.name,
            "template": g.template,
            "kind": g.kind,
            "decision": str(result.decision),
            "reasons": result.reasons,
            "cost_usd": result.cost.usd,
        }
        if g.kind == "invoice":
            checks = (harness.compare_fields(result.data, g.truth)
                      if result.data else harness.all_wrong())
            record["fields"] = checks
            rows.append(checks)
            by_template.setdefault(g.template, []).append(
                {"checks": checks, "decision": result.decision})
        records.append(record)
        marker = "·" if g.pdf.name in uncached else "cache"
        print(f"  {g.pdf.name:<28}{result.decision:<14}{marker}")

    # ── tables
    print("\n## Per-field accuracy (single-invoice documents)\n")
    print(f"{'field':<16}{'accuracy':>10}")
    accuracy = harness.field_accuracy(rows)
    for field, (correct, total) in accuracy.items():
        print(f"{field:<16}{correct:>6}/{total:<4}{correct / total:>7.0%}")

    fully = sum(1 for r in rows if all(r.values()))
    print(f"\nfully correct documents: {fully}/{len(rows)}")

    print("\n## Per-template (failure matrix)\n")
    print(f"{'template':<20}{'docs':>5}{'fully correct':>15}{'auto-accepted':>15}")
    for template, entries in sorted(by_template.items()):
        ok = sum(1 for e in entries if all(e["checks"].values()))
        auto = sum(1 for e in entries
                   if e["decision"] is Decision.AUTO_ACCEPT)
        print(f"{template:<20}{len(entries):>5}{ok:>10}/{len(entries):<4}"
              f"{auto:>10}/{len(entries):<4}")

    # gate quality: of the auto-accepted docs, how many had any field error
    auto_docs = [e for entries in by_template.values() for e in entries
                 if e["decision"] is Decision.AUTO_ACCEPT]
    auto_with_error = sum(1 for e in auto_docs if not all(e["checks"].values()))
    print("\n## Gate quality (the number a CFO cares about)\n")
    print(f"auto-accepted: {len(auto_docs)} · with any error: {auto_with_error}"
          f" · error rate: "
          f"{(auto_with_error / len(auto_docs)) if auto_docs else 0:.1%}")

    rejects = [r for r in records if r["kind"] == "reject"]
    ok_rejects = sum(1 for r in rejects if r["decision"] == "REJECT")
    print(f"\nreject documents correctly REJECTed: {ok_rejects}/{len(rejects)}")

    multi = [r for r in records if r["kind"] == "multi"]
    if multi:
        print("\nknown limitation — multi-invoice PDFs (engine extracts one "
              "invoice per document):")
        for r in multi:
            print(f"  {r['doc']} → {r['decision']}")

    print(f"\n## Cost ({provider.model})\n")
    print(f"fresh-run equivalent: ${equivalent_usd:.2f} "
          f"(${equivalent_usd / len(docs):.4f}/doc) · "
          f"spent this run: ${spent_usd:.2f} · cache hits: {provider.hits}")

    RESULTS_PATH.write_text(json.dumps({
        "model": provider.model,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "sample": args.sample,
        "docs": records,
    }, indent=2))
    print(f"\nraw results → {RESULTS_PATH.relative_to(Path.cwd())}"
          if RESULTS_PATH.is_relative_to(Path.cwd()) else RESULTS_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
