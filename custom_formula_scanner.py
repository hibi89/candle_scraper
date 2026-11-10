# -*- coding: utf-8 -*-
"""Offline, allow-listed customer formula scanner for existing candle SQLite DBs.

JSON rules are data, never Python code. No dynamic SQL identifiers or network.
Python 3.11+ / standard library only. Input databases are opened read-only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path

UNITS = (1, 3, 5, 10, 15, 30, 60, 240)
FIELDS = frozenset(("open", "high", "low", "close", "volume", "trade_value"))
OPERATORS = {">", ">=", "<", "<=", "==", "!="}
INDICATORS = {"sma", "ema", "bb_upper", "bb_lower"}
MARKET = re.compile(r"KRW-[A-Z0-9]+\Z")
OUTPUT_COLUMNS = ("exchange", "market", "unit", "utc", "kst", "close", "formula", "formula_sha256")
MAX_RULE_BYTES = 65536
MAX_NODES = 64
MAX_INDICATORS = 16
MAX_DEPTH = 6


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _keys(obj, required, optional=()):
    if not isinstance(obj, dict) or set(obj) - (set(required) | set(optional)) or set(required) - set(obj):
        raise ValueError(f"Expected JSON object keys: required={sorted(required)}, optional={sorted(optional)}")


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Formula constants must be finite JSON numbers")
    return float(value)


def _operand(obj):
    if not isinstance(obj, dict) or len(obj) != 1 and "indicator" not in obj:
        raise ValueError("Operand must be a field, value, or indicator object")
    if "field" in obj and "indicator" not in obj:
        _keys(obj, {"field"})
        if obj["field"] not in FIELDS:
            raise ValueError("Unsupported candle field")
        return ("field", obj["field"])
    if "value" in obj and "indicator" not in obj:
        _keys(obj, {"value"})
        return ("value", _finite_number(obj["value"]))
    _keys(obj, {"indicator", "field", "period"}, {"multiplier"})
    name, field, period = obj["indicator"], obj["field"], obj["period"]
    if name not in INDICATORS or field not in FIELDS:
        raise ValueError("Unsupported indicator or source field")
    if isinstance(period, bool) or not isinstance(period, int) or not 2 <= period <= 560:
        raise ValueError("Indicator period must be 2..560")
    if name.startswith("bb_"):
        multiplier = _finite_number(obj.get("multiplier", 2))
        if not 0 <= multiplier <= 10:
            raise ValueError("Bollinger multiplier must be 0..10")
        return (name, field, period, multiplier)
    if "multiplier" in obj:
        raise ValueError("Multiplier is only supported on Bollinger bands")
    return (name, field, period)


def _node(obj, operands, counter, depth=0):
    if depth > MAX_DEPTH:
        raise ValueError("Formula nesting is too deep")
    counter[0] += 1
    if counter[0] > MAX_NODES:
        raise ValueError("Too many formula conditions")
    if not isinstance(obj, dict):
        raise ValueError("Formula condition must be a JSON object")
    if len(obj) == 1 and ("all" in obj or "any" in obj):
        key = "all" if "all" in obj else "any"
        items = obj[key]
        if not isinstance(items, list) or not 1 <= len(items) <= 32:
            raise ValueError("all/any requires 1..32 conditions")
        return (key, tuple(_node(it, operands, counter, depth + 1) for it in items))
    if len(obj) == 1 and "not" in obj:
        return ("not", _node(obj["not"], operands, counter, depth + 1))
    if len(obj) == 1 and ("cross_up" in obj or "cross_down" in obj):
        key = "cross_up" if "cross_up" in obj else "cross_down"
        pair = obj[key]
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("cross_up/cross_down requires two operands")
        left, right = map(_operand, pair)
        operands.update((left, right))
        return (key, left, right)
    _keys(obj, {"left", "op", "right"})
    if obj["op"] not in OPERATORS:
        raise ValueError("Comparison operator not supported")
    left, right = _operand(obj["left"]), _operand(obj["right"])
    operands.update((left, right))
    return ("cmp", obj["op"], left, right)


@dataclass(frozen=True)
class Formula:
    name: str
    digest: str
    tree: tuple
    operands: tuple[tuple, ...]
    sources: frozenset[str]


def compile_formula(raw: dict) -> Formula:
    _keys(raw, {"version", "name", "when"})
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("Formula version must be 1")
    name = raw["name"]
    if not isinstance(name, str) or not 1 <= len(name) <= 60 or any(ord(c) < 32 for c in name) or name.startswith(("=", "+", "-", "@")):
        raise ValueError("Formula name must be 1..60 printable characters")
    operands = set()
    tree = _node(raw["when"], operands, [0])
    indicators = [op for op in operands if op[0] in INDICATORS]
    if len(indicators) > MAX_INDICATORS:
        raise ValueError("Too many separate indicators in formula")
    sources = frozenset(op[1] for op in operands if op[0] != "value")
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return Formula(name, hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                   tree, tuple(sorted(operands)), sources)


def load_formula(path: Path) -> Formula:
    path = Path(path)
    if path.stat().st_size > MAX_RULE_BYTES:
        raise ValueError("Formula JSON exceeds 64 KiB")
    raw = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON value")))
    return compile_formula(raw)


class Rolling:
    def __init__(self, key):
        self.key = key
        self.values = deque()
        self.total = 0.0
        self.ema = None

    def push(self, value):
        kind, _field, period, *args = self.key
        if kind == "ema":
            self.ema = value if self.ema is None else self.ema + 2 / (period + 1) * (value - self.ema)
        self.values.append(value)
        self.total += value
        if len(self.values) > period:
            self.total -= self.values.popleft()
        if len(self.values) < period:
            return None
        if kind == "ema":
            return self.ema
        mean = self.total / period
        if kind == "sma":
            return mean
        variance = math.fsum((v - mean) ** 2 for v in self.values) / period
        spread = args[0] * math.sqrt(max(0.0, variance))
        return mean + spread if kind == "bb_upper" else mean - spread


def _compare(a, op, b):
    return {">": lambda: a > b, ">=": lambda: a >= b,
            "<": lambda: a < b, "<=": lambda: a <= b,
            "==": lambda: a == b, "!=": lambda: a != b}[op]()


def _evaluate(node, current, previous):
    kind = node[0]
    if kind == "all":
        return all(_evaluate(it, current, previous) for it in node[1])
    if kind == "any":
        return any(_evaluate(it, current, previous) for it in node[1])
    if kind == "not":
        return not _evaluate(node[1], current, previous)
    if kind == "cmp":
        _, op, left, right = node
        a, b = current[left], current[right]
        return a is not None and b is not None and _compare(a, op, b)
    _, left, right = node
    a, b = current[left], current[right]
    p, q = previous.get(left), previous.get(right)
    if None in (a, b, p, q):
        return False
    return (p <= q and a > b) if kind == "cross_up" else (p >= q and a < b)


class Evaluator:
    def __init__(self, formula: Formula):
        self.formula = formula
        self.rolling = {op: Rolling(op) for op in formula.operands if op[0] in INDICATORS}
        self.previous = {}

    def push(self, row: dict) -> bool:
        # Reject corrupted indicators rather than silently match on NaN/Infinity.
        fields = {}
        for field in self.formula.sources:
            value = _finite_number(row[field])
            if value < 0 or (field in {"open", "high", "low", "close"} and value <= 0):
                raise ValueError(f"Invalid candle {field}")
            fields[field] = value
        current = {}
        for op in self.formula.operands:
            kind = op[0]
            current[op] = (op[1] if kind == "value" else
                           fields[op[1]] if kind == "field" else
                           self.rolling[op].push(fields[op[1]]))
        # Comparisons require all needed operands to be ready. 'not' should
        # not produce a positive signal during indicator warm-up.
        ready = all(current[op] is not None for op in self.formula.operands)
        matched = ready and _evaluate(self.formula.tree, current, self.previous)
        self.previous = current
        return matched


def _read_only(path: Path, sources: frozenset[str]):
    if not path.is_file():
        raise FileNotFoundError(f"Missing candle database: {path}")
    connection = sqlite3.connect(path.resolve(strict=True).as_uri() + "?mode=ro", uri=True, timeout=30)
    try:
        connection.execute("PRAGMA query_only=ON")
        columns = {r[1] for r in connection.execute("PRAGMA table_info(candles)")}
        required = {"market", "unit", "utc", "kst"} | FIELDS | sources
        if not required.issubset(columns):
            raise ValueError("Incompatible candle schema: " + ",".join(sorted(required - columns)))
        return connection
    except BaseException:
        connection.close()
        raise


def _validate_selection(units, markets, last, max_matches):
    if not units or len(set(units)) != len(units) or any(type(u) is not int or u not in UNITS for u in units):
        raise ValueError("Unsupported/duplicate minute units")
    if markets is not None and (not markets or any(not isinstance(m, str) or not MARKET.fullmatch(m) for m in markets)):
        raise ValueError("Invalid KRW market")
    if type(last) is not int or last < 0:
        raise ValueError("--last must be >= 0")
    if type(max_matches) is not int or not 1 <= max_matches <= 1000000:
        raise ValueError("--max-matches must be 1..1000000")


def scan(paths: list[Path], output: Path, formula: Formula, *, units=UNITS, markets=None,
         last=0, overwrite=False, max_matches=500000):
    _validate_selection(units, markets, last, max_matches)
    if not paths:
        raise ValueError("At least one database is required")
    paths = [Path(p).resolve(strict=True) for p in paths]
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate database paths")
    output = Path(output).resolve()
    if output.suffix.lower() != ".csv" or output in paths:
        raise ValueError("Output must be a distinct .csv file")
    if not output.parent.is_dir():
        raise NotADirectoryError("Output directory does not exist")
    if output.exists() and not overwrite:
        raise FileExistsError("Existing CSV preserved (use --overwrite explicitly)")
    totals = {"databases": 0, "pairs": 0, "candles_processed": 0, "matches": 0}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="", prefix=".formula-",
                                         suffix=".tmp", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.DictWriter(stream, OUTPUT_COLUMNS)
            writer.writeheader()
            for path in paths:
                conn = _read_only(path, formula.sources)
                try:
                    predicates = "unit IN (" + ",".join("?" for _ in units) + ")"
                    params = list(units)
                    if markets is not None:
                        predicates += " AND market IN (" + ",".join("?" for _ in markets) + ")"
                        params.extend(sorted(markets))
                    pairs = conn.execute("SELECT market,unit,COUNT(*) FROM candles WHERE " + predicates
                                         + " GROUP BY market,unit ORDER BY market,unit", params).fetchall()
                    exchange = "upbit" if "upbit" in path.stem.lower() else (
                        "bithumb" if "bithumb" in path.stem.lower() else "local")
                    for market, unit, count in pairs:
                        if not MARKET.fullmatch(market or ""):
                            continue
                        totals["pairs"] += 1
                        begin = max(0, count - last) if last else 0
                        evaluator = Evaluator(formula)
                        prev_utc = None
                        for index, values in enumerate(conn.execute(
                            "SELECT utc,kst,open,high,low,close,volume,trade_value FROM candles "
                            "WHERE market=? AND unit=? ORDER BY utc ASC", (market, unit)
                        )):
                            utc, kst, opn, high, low, close, volume, trade_value = values
                            if not isinstance(utc, str) or not utc or (prev_utc is not None and utc <= prev_utc):
                                raise ValueError("Missing/non-increasing UTC candle index")
                            if not isinstance(kst, str) or not re.match(r"^\d{4}-\d{2}-\d{2}", kst) or not re.match(r"^\d{4}-\d{2}-\d{2}", utc):
                                raise ValueError("Invalid candle UTC/KST date")
                            prev_utc = utc
                            candle = dict(zip(("open", "high", "low", "close", "volume", "trade_value"),
                                              (opn, high, low, close, volume, trade_value)))
                            for fld in FIELDS:
                                value = _finite_number(candle[fld])
                                if value < 0 or (fld in {"open", "high", "low", "close"} and value <= 0):
                                    raise ValueError(f"Invalid candle {fld}")
                                candle[fld] = value
                            if candle["low"] > min(candle["open"], candle["close"]) or candle["high"] < max(candle["open"], candle["close"]):
                                raise ValueError("Inconsistent candle OHLC values")
                            matched = evaluator.push(candle)
                            totals["candles_processed"] += 1
                            if matched and index >= begin:
                                totals["matches"] += 1
                                if totals["matches"] > max_matches:
                                    raise ValueError("Match count exceeds safety limit; no CSV published")
                                writer.writerow({"exchange": exchange, "market": market, "unit": unit,
                                                 "utc": utc, "kst": kst, "close": close,
                                                 "formula": formula.name, "formula_sha256": formula.digest})
                finally:
                    conn.close()
                totals["databases"] += 1
        if overwrite:
            os.replace(temporary, output)
        else:
            # Atomic creation, without racing an existing customer CSV.
            os.link(temporary, output)
            temporary.unlink()
        temporary = None
        return totals
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _markets(text):
    if text.strip().lower() in {"all", "*", "전체"}:
        return None
    result = set()
    for value in text.split(","):
        token = value.strip().upper()
        name = token if token.startswith("KRW-") else "KRW-" + token
        if not MARKET.fullmatch(name):
            raise ValueError("Invalid market: " + token)
        result.add(name)
    return frozenset(result)


def _units(text):
    if text.strip().lower() in {"all", "*", "전체"}:
        return UNITS
    try:
        result = tuple(int(it.strip()) for it in text.split(","))
    except ValueError as exc:
        raise ValueError("Invalid minute units") from exc
    _validate_selection(result, None, 0, 1)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline read-only, allow-listed customer candle formula search")
    parser.add_argument("--db", type=Path, action="append", required=True)
    parser.add_argument("--rule", type=Path, required=True, help="Local validated JSON formula")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markets", default="all", help="ALL or comma-separated KRW tickers")
    parser.add_argument("--units", default="all", help="ALL or 1,3,5,10,15,30,60,240")
    parser.add_argument("--last", type=int, default=0, help="Most recent N candles per pair, 0=all")
    parser.add_argument("--max-matches", type=int, default=500000)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        rule = load_formula(args.rule)
        result = scan(args.db, args.output, rule, units=_units(args.units), markets=_markets(args.markets),
                      last=args.last, max_matches=args.max_matches, overwrite=args.overwrite)
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"SCAN HOLD: {error}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "formula": rule.name, "sha256": rule.digest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())