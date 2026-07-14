"""The standalone tool: extract any document from the command line.

    uv run python -m extractor path/to/invoice.pdf
    uv run python -m extractor invoice.pdf --verify
    uv run python -m extractor invoice.pdf --json > extracted.json

Prints the same one-screen summary the lessons use; --json prints the full
result as JSON for pipes and scripts. The exit code mirrors the decision:
0 = AUTO_ACCEPT, 1 = NEEDS_REVIEW, 2 = REJECT.
"""

import argparse
import json
import sys
from pathlib import Path

# The profiles/ directory sits next to the extractor/ package — make the
# default profile importable no matter where the command is run from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractor import (  # noqa: E402
    AnthropicProvider,
    Decision,
    OpenAIProvider,
    extract,
    verify,
)
from extractor.utils import show  # noqa: E402

PROVIDERS = {"anthropic": AnthropicProvider, "openai": OpenAIProvider}
EXIT_CODES = {Decision.AUTO_ACCEPT: 0, Decision.NEEDS_REVIEW: 1,
              Decision.REJECT: 2}


def load_profile(spec: str):
    """'profiles.iberia_invoice:IBERIA_INVOICE' -> that DocumentProfile."""
    import importlib

    module, _, attr = spec.partition(":")
    return getattr(importlib.import_module(module), attr)


def as_json(result) -> str:
    return json.dumps({
        "source": result.source,
        "decision": str(result.decision),
        "reasons": result.reasons,
        "document_type": result.document_type,
        "data": result.data.model_dump(mode="json") if result.data else None,
        "fields": {name: {"confidence": meta.confidence, "flags": meta.flags}
                   for name, meta in result.field_meta.items()},
        "validation": [{"rule": r.rule, "passed": r.passed, "detail": r.detail}
                       for r in result.validation],
        "cost": result.cost.model_dump(),
    }, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m extractor", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("document", help="PDF or image file to extract")
    parser.add_argument("--profile",
                        default="profiles.iberia_invoice:IBERIA_INVOICE",
                        help="module:attr of the DocumentProfile to use "
                             "(default: the Iberia invoice example)")
    parser.add_argument("--verify", action="store_true",
                        help="chain the second AI read of the critical fields")
    parser.add_argument("--provider", choices=PROVIDERS, default="anthropic",
                        help="LLM vendor (default: anthropic)")
    parser.add_argument("--model", default=None,
                        help="model name (default: the provider's default)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="print the full result as JSON instead of the "
                             "human summary")
    args = parser.parse_args(argv)

    profile = load_profile(args.profile)
    provider = PROVIDERS[args.provider](args.model)

    result = extract(args.document, profile, provider=provider)
    if args.verify:
        result = verify(result, profile, provider=provider)

    if args.as_json:
        print(as_json(result))
    else:
        show(result)
    return EXIT_CODES[result.decision]


if __name__ == "__main__":
    raise SystemExit(main())
