# -*- coding: utf-8 -*-
"""One-pass multi-rule runner for the existing v1 JSON formula contract.

No formula eval/import, no network, no collector modification. A batch file is
{version:1,rules:[{name,when},...]}; a P1 single-rule file is also accepted.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

from custom_formula_scanner import (
    FIELDS, MARKET, MAX_RULE_BYTES, OUTPUT_COLUMNS, UNITS, Evaluator,
    Formula, _finite_number, _read_only, _unique_pairs, _validate_selection,
    compile_formula,
)

MAX_BATCH_RULES = 16
MAX_BATCH_BYTES = MAX_RULE_BYTES
MAX_DBS = 8
DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")


def load_formula_batch(path: Path) -> tuple[Formula, ...]:
    """Use the P1 DSL unchanged; accept one rule or a bounded list of rules."""
    path = Path(path)
    if path.stat().st_size > MAX_BATCH_BYTES:
        raise ValueError("Batch formula JSON exceeds 64 KiB")
    raw = json.loads(path.read_text(encoding="utf-8-sig"),
                     object_pairs_hook=_unique_pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON value")))
    if not isinstance(raw, dict):
        raise ValueError("Formula document must be an object")
    if set(raw) == {"version", "name", "when"}:
        return (compile_formula(raw),)
    if set(raw) != {"version", "rules"} or type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("Expected version=1 batch with rules")
    rules = raw["rules"]
    if not isinstance(rules, list) or not 1 <= len(rules) <= MAX_BATCH_RULES:
        raise ValueError("Batch must contain 1..16 rules")
    formulas = []
    seen = set()
    for entry in rules:
        if not isinstance(entry, dict) or set(entry) != {"name", "when"}:
            raise ValueError("Each batch rule requires name and when")
        formula = compile_formula({"version": 1, **entry})
        if formula.name.casefold() in seen:
            raise ValueError("Duplicate batch rule name")
        seen.add(formula.name.casefold())
        formulas.append(formula)
    return tuple(formulas)


def _pairs(db: sqlite3.Connection, units, markets):
    params = list(units)
    condition = "unit IN (" + ",".join("?" for _ in units) + ")"
    if markets is not None:
        condition += " AND market IN (" + ",".join("?" for _ in markets) + ")"
        params.extend(sorted(markets))
    return db.execute("SELECT market,unit,COUNT(*) FROM candles WHERE " + condition +
                      " GROUP BY market,unit ORDER BY market,unit", params).fetchall()


def _check_candle(market, unit, utc, kst, raw_values, previous_utc):
    if (not isinstance(market, str) or not MARKET.fullmatch(market)
            or type(unit) is not int or unit not in UNITS
            or not isinstance(utc, str) or not DATE_PREFIX.match(utc)
            or previous_utc is not None and utc <= previous_utc
            or not isinstance(kst, str) or not DATE_PREFIX.match(kst)):
        raise ValueError("Invalid market, timeframe or UTC/KST candle order")
    fields = ("open", "high", "low", "close", "volume", "trade_value")
    bar = {key: _finite_number(val) for key, val in zip(fields, raw_values)}
    if (any(v < 0 for v in bar.values()) or
            any(bar[k] <= 0 for k in ("open", "high", "low", "close")) or
            bar["low"] > min(bar["open"], bar["close"]) or
            bar["high"] < max(bar["open"], bar["close"])):
        raise ValueError("Invalid source OHLC/volume: report withheld")
    return bar


def scan_batch(paths: list[Path], output: Path, formulas: tuple[Formula, ...], *,
               units=UNITS, markets=None, last=0, overwrite=False,
               max_matches=500000, progress=False,
               report: Callable[[str], None] = print) -> dict:
    """Process each DB candle once for every requested rule; publish CSV atomically."""
    _validate_selection(units, markets, last, max_matches)
    if not 1 <= len(paths) <= MAX_DBS:
        raise ValueError("Expected 1..8 input databases")
    if not 1 <= len(formulas) <= MAX_BATCH_RULES or any(not isinstance(f, Formula) for f in formulas):
        raise ValueError("Expected 1..16 compiled formulas")
    if len({f.name.casefold() for f in formulas}) != len(formulas):
        raise ValueError("Duplicate formula name")
    paths = [Path(p).resolve(strict=True) for p in paths]
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate input database")
    output = Path(output).resolve()
    if output in paths or output.suffix.lower() != ".csv":
        raise ValueError("Output must be a separate .csv file")
    if not output.parent.is_dir():
        raise NotADirectoryError("Output folder does not exist")
    if output.exists() and not overwrite:
        raise FileExistsError("Existing CSV preserved (use --overwrite explicitly)")
    stats = {"databases": 0, "pairs": 0, "candles_processed": 0,
             "matches": 0, "matches_by_formula": {f.name: 0 for f in formulas}}
    temporary = None
    start = time.perf_counter()
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="",
                                         prefix=".formula-batch-", suffix=".tmp",
                                         dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.DictWriter(stream, OUTPUT_COLUMNS)
            writer.writeheader()
            for db_index, path in enumerate(paths, 1):
                db = _read_only(path, frozenset().union(*(f.sources for f in formulas)))
                try:
                    pairs = _pairs(db, units, markets)
                    total = sum(n for _, _, n in pairs)
                    completed = 0
                    last_show = start
                    exchange = "upbit" if "upbit" in path.stem.lower() else (
                        "bithumb" if "bithumb" in path.stem.lower() else "local")
                    for pair_index, (market, unit, count) in enumerate(pairs, 1):
                        if not MARKET.fullmatch(market or ""):
                            continue
                        stats["pairs"] += 1
                        begin = max(0, count - last) if last else 0
                        evaluators = [(f, Evaluator(f)) for f in formulas]
                        prev_utc = None
                        rows = db.execute(
                            "SELECT utc,kst,open,high,low,close,volume,trade_value FROM candles "
                            "WHERE market=? AND unit=? ORDER BY utc ASC", (market, unit))
                        for index, (utc, kst, *values) in enumerate(rows):
                            candle = _check_candle(market, unit, utc, kst, values, prev_utc)
                            prev_utc = utc
                            stats["candles_processed"] += 1
                            completed += 1
                            for formula, evaluator in evaluators:
                                if evaluator.push(candle) and index >= begin:
                                    stats["matches"] += 1
                                    if stats["matches"] > max_matches:
                                        raise ValueError("Match limit exceeded; CSV not published")
                                    stats["matches_by_formula"][formula.name] += 1
                                    writer.writerow({"exchange": exchange, "market": market,
                                                     "unit": unit, "utc": utc, "kst": kst,
                                                     "close": candle["close"], "formula": formula.name,
                                                     "formula_sha256": formula.digest})
                            if progress and index % 5000 == 0 and time.perf_counter() - last_show >= 2:
                                elapsed = max(.001, time.perf_counter()-start)
                                eta = int((total-completed)*elapsed/max(completed, 1))
                                report(f"DB {db_index}/{len(paths)} {100*completed/max(total,1):.1f}% | "
                                       f"{market}/{unit} | {completed}/{total} rows | ETA ~{eta}s")
                                last_show = time.perf_counter()
                        if progress:
                            report(f"DB {db_index}/{len(paths)} {100*completed/max(total,1):.1f}% | "
                                   f"{market}/{unit} | {completed}/{total} rows")
                    stats["databases"] += 1
                finally:
                    db.close()
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, output)
        else:
            # Same-folder exclusive hardlink: atomic publication without race overwrite.
            os.link(temporary, output)
            temporary.unlink()
        temporary = None
        return stats
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _parse_markets(raw):
    if raw.strip().lower() in ("all", "*", "전체"):
        return None
    vals = []
    for item in raw.split(","):
        token = item.strip().upper()
        market = token if token.startswith("KRW-") else "KRW-" + token
        if not MARKET.fullmatch(market):
            raise ValueError("Invalid KRW market: " + token)
        vals.append(market)
    if len(set(vals)) != len(vals):
        raise ValueError("Duplicate market")
    return frozenset(vals)


def _parse_units(raw):
    if raw.strip().lower() in ("all", "*", "전체"):
        return UNITS
    try:
        vals = tuple(int(v.strip()) for v in raw.split(","))
    except ValueError as exc:
        raise ValueError("Invalid minute timeframe list") from exc
    _validate_selection(vals, None, 0, 1)
    return vals


def main(argv=None):
    parser = argparse.ArgumentParser(description="One-pass bounded batch scan with P1 JSON rule DSL")
    parser.add_argument("--db", action="append", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markets", default="all")
    parser.add_argument("--units", default="all")
    parser.add_argument("--last", type=int, default=0)
    parser.add_argument("--max-matches", type=int, default=500000)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args(argv)
    try:
        formulas = load_formula_batch(args.rules)
        stats = scan_batch(args.db, args.output, formulas, units=_parse_units(args.units),
                           markets=_parse_markets(args.markets), last=args.last,
                           max_matches=args.max_matches, overwrite=args.overwrite,
                           progress=args.progress)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print("SCAN HOLD: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(stats, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
