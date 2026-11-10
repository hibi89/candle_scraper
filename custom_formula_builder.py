# -*- coding: utf-8 -*-
"""Safe no-dependency formula template builder for the canonical P1 JSON DSL.

Builds a rule file only; it never opens source candle databases or trades.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

from custom_formula_scanner import compile_formula

MODES = ("sma_cross", "ema_cross", "bb_upper_breakout", "bb_lower_recover", "close_above")


def _period(value):
    if type(value) is not int or not 2 <= value <= 560:
        raise ValueError("Period must be an integer from 2 to 560")
    return value


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Threshold/sigma must be finite numbers")
    return value


def build_formula(name: str, mode: str, *, fast=20, slow=60,
                  period=20, sigma=2.0, threshold=100.0) -> dict:
    """Restrict parameterized templates to well-defined historical signals."""
    if mode not in MODES:
        raise ValueError("Unsupported formula template")
    if mode in ("sma_cross", "ema_cross"):
        _period(fast)
        _period(slow)
        if fast >= slow:
            raise ValueError("Fast period must be shorter than slow period")
        indicator = "sma" if mode == "sma_cross" else "ema"
        when = {"cross_up": [
            {"indicator": indicator, "field": "close", "period": fast},
            {"indicator": indicator, "field": "close", "period": slow}]}
    elif mode in ("bb_upper_breakout", "bb_lower_recover"):
        _period(period)
        _number(sigma)
        if not 0 < sigma <= 10:
            raise ValueError("Bollinger multiplier must be above 0 and at most 10")
        band = "bb_upper" if mode == "bb_upper_breakout" else "bb_lower"
        when = {"cross_up": [
            {"field": "close"},
            {"indicator": band, "field": "close", "period": period, "multiplier": sigma}]}
    else:
        _number(threshold)
        if threshold <= 0:
            raise ValueError("Price threshold must be positive")
        when = {"left": {"field": "close"}, "op": ">", "right": {"value": threshold}}
    rule = {"version": 1, "name": name, "when": when}
    compile_formula(rule)  # One canonical validation path, no dynamic code.
    return rule


def save_new_rule(rule: dict, output: Path) -> Path:
    """Exclusive create: cannot replace an existing JSON/DB/customer file."""
    output = Path(output).absolute()
    if output.suffix.lower() != ".json" or not output.parent.is_dir():
        raise ValueError("Choose a .json file in an existing folder")
    data = (json.dumps(rule, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return output


def _prompt_number(label: str, converter, default):
    raw = input(f"{label} [{default}]: ").strip()
    return converter(raw if raw else default)


def interactive() -> tuple[dict, Path]:
    print("\n=== Offline Custom Candle Formula Builder ===")
    for index, name in enumerate(MODES, 1):
        print(f"[{index}] {name}")
    choice = _prompt_number("Choose template 1-5", int, 1)
    if not 1 <= choice <= len(MODES):
        raise ValueError("Choose a numbered template 1..5")
    mode = MODES[choice - 1]
    label = input("Formula name: ").strip()
    kwargs = {}
    if mode in ("sma_cross", "ema_cross"):
        kwargs["fast"] = _prompt_number("Fast period", int, 20)
        kwargs["slow"] = _prompt_number("Slow period", int, 60)
    elif mode.startswith("bb_"):
        kwargs["period"] = _prompt_number("BB period", int, 20)
        kwargs["sigma"] = _prompt_number("BB multiplier", float, 2.0)
    else:
        kwargs["threshold"] = _prompt_number("Minimum close", float, 100)
    output = Path(input("New JSON output path [custom_rule.json]: ").strip() or "custom_rule.json")
    return build_formula(label, mode, **kwargs), output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create safe offline customer formulas; no DB access")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--name")
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=60)
    parser.add_argument("--period", type=int, default=20)
    parser.add_argument("--sigma", type=float, default=2.0)
    parser.add_argument("--threshold", type=float, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.interactive or not argv:
            rule, output = interactive()
        else:
            if not args.mode or not args.name or not args.output:
                parser.error("--mode, --name and --output required for non-interactive mode")
            rule = build_formula(args.name, args.mode, fast=args.fast, slow=args.slow,
                                 period=args.period, sigma=args.sigma, threshold=args.threshold)
            output = args.output
        target = save_new_rule(rule, output)
    except (ValueError, OSError, EOFError) as exc:
        print("FORMULA HOLD: " + str(exc), file=sys.stderr)
        return 2
    print("Rule saved:", target)
    print("Use: python custom_formula_batch.py --db YOUR.sqlite3 --rules", target, "--output hits.csv --progress")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
