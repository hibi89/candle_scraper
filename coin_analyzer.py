# -*- coding: utf-8 -*-
"""One customer-facing entry point for P1 and P2-compatible candle-rule scanners.

No eval, customer database writes, network access, or imported user Python code.
The existing verified single-formula and batch JSON contracts remain unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

MAX_MATCHES = 1_000_000


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline KRW candle formula analyzer (read-only SQLite, safe JSON)"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rule", type=Path, help="Existing single-formula JSON contract")
    mode.add_argument("--rules", type=Path, help="New batch JSON contract (up to 16 rules)")
    parser.add_argument("--db", action="append", type=Path,
                        help="Candle SQLite DB; repeat for more sources")
    parser.add_argument("--output", type=Path, help="Output CSV path")
    parser.add_argument("--markets", default="all", help="ALL or BTC,ETH etc.")
    parser.add_argument("--units", default="all", help="ALL or 1,3,5,10,15,30,60,240")
    parser.add_argument("--last", type=int, default=0,
                        help="Only emit matches from last N bars; 0=all")
    parser.add_argument("--max-matches", type=int, default=500000,
                        help="Maximum emitted rows (1..1000000)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Explicitly replace a prior result CSV")
    parser.add_argument("--validate-only", action="store_true",
                        help="Validate formula without opening source DB or writing CSV")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    options = parser.parse_args(argv)
    if (type(options.last) is not int or options.last < 0
            or type(options.max_matches) is not int
            or not 1 <= options.max_matches <= MAX_MATCHES):
        parser.error("--last must be >=0, --max-matches must be 1..1000000")
    is_batch = options.rules is not None
    input_file = options.rules if is_batch else options.rule
    try:
        if is_batch:
            import custom_formula_batch as engine
            load = engine.load_formula_batch
        else:
            import custom_formula_scanner as engine
            load = engine.load_formula
        if options.validate_only:
            formula = load(input_file.resolve())
            return_code = {
                "contract": "coin-analyzer.validate.v1",
                "status": "VALID",
                "mode": "batch" if is_batch else "single",
                "rule_count": len(formula) if is_batch else 1,
                "read_customer_db": False,
                "wrote_csv": False,
            }
            print(json.dumps(return_code, sort_keys=True))
            return 0
        if not options.db or not options.output:
            parser.error("--db and --output are required except with --validate-only")
        # The established engine main handles its own schema validation, source
        # protection, selected pair traversal, progress and atomic CSV publishing.
        forward: list[str] = []
        for path in options.db:
            forward.extend(("--db", str(path)))
        forward.extend(("--rules" if is_batch else "--rule", str(input_file)))
        forward.extend(("--output", str(options.output),
                        "--markets", options.markets, "--units", options.units,
                        "--last", str(options.last),
                        "--max-matches", str(options.max_matches)))
        if options.overwrite:
            forward.append("--overwrite")
        return engine.main(forward)
    except (OSError, ValueError) as exc:
        print("RULE_VALIDATION_FAILED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
