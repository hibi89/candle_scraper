# -*- coding: utf-8 -*-
"""Offline candle-pattern scanner. Never imports or calls the exchange collector."""
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sqlite3
import sys
import tempfile
from collections import deque
from pathlib import Path

MINUTE_UNITS = (1, 3, 5, 10, 15, 30, 60, 240)
FIELDS = (
    "exchange", "market", "unit", "utc", "kst", "close",
    "sma280", "sma560", "ema280", "ema560", "bb_upper",
    "sma_spread_previous", "sma_spread_current",
)
REQUIRED_COLUMNS = frozenset(("market", "unit", "utc", "kst", "close"))


class RollingMean:
    """Constant-memory SMA with oldest value removal."""

    def __init__(self, period: int) -> None:
        self.period = period
        self.values: deque[float] = deque()
        self.total = 0.0

    def push(self, value: float) -> float | None:
        if len(self.values) == self.period:
            self.total -= self.values.popleft()
        self.values.append(value)
        self.total += value
        return self.total / self.period if len(self.values) == self.period else None


class Indicators:
    """SMA/EMA 280/560 and BB(20, 2, population std) on recorded closes."""

    def __init__(self) -> None:
        self.sma280 = RollingMean(280)
        self.sma560 = RollingMean(560)
        self.bb20 = RollingMean(20)
        self.ema280: float | None = None
        self.ema560: float | None = None
        self.previous_spread: float | None = None

    def push(self, close: float) -> dict[str, float] | None:
        sma280 = self.sma280.push(close)
        sma560 = self.sma560.push(close)
        bb_basis = self.bb20.push(close)
        self.ema280 = (close if self.ema280 is None else
                       self.ema280 + (2 / 281) * (close - self.ema280))
        self.ema560 = (close if self.ema560 is None else
                       self.ema560 + (2 / 561) * (close - self.ema560))
        if sma280 is None or sma560 is None or bb_basis is None:
            return None
        # Centered variance prevents catastrophic cancellation on flat candles.
        bb_variance = math.fsum(
            (v - bb_basis) ** 2 for v in self.bb20.values
        ) / 20
        bb_upper = bb_basis + 2 * math.sqrt(max(0.0, bb_variance))
        spread = sma280 - sma560
        result = {
            "sma280": sma280, "sma560": sma560,
            "ema280": self.ema280, "ema560": self.ema560,
            "bb_upper": bb_upper,
            "sma_spread_previous": self.previous_spread,
            "sma_spread_current": spread,
        }
        self.previous_spread = spread
        return result


def is_signal(indicators: dict[str, float]) -> bool:
    """SMA280 crosses up SMA560, both above BB upper, below EMA280/560."""
    previous = indicators["sma_spread_previous"]
    return bool(
        previous is not None and previous <= 0
        and indicators["sma_spread_current"] > 0
        and indicators["ema560"] > indicators["ema280"]
        > indicators["sma280"] > indicators["sma560"]
        > indicators["bb_upper"]
    )


def _database_uri(path: Path) -> str:
    # as_uri percent-escapes Korean, spaces, # and ? correctly on Windows.
    return path.resolve(strict=True).as_uri() + "?mode=ro"


def _check_schema(db: sqlite3.Connection) -> None:
    columns = {row[1] for row in db.execute("PRAGMA table_info(candles)")}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError("Incompatible read-only candle database; missing: "
                         + ", ".join(sorted(missing)))


def _pairs(
    db: sqlite3.Connection, units: tuple[int, ...], markets: frozenset[str] | None
) -> list[tuple[str, int]]:
    unit_sql = ",".join("?" for _ in units)
    sql = ("SELECT DISTINCT market,unit FROM candles WHERE unit IN (" +
           unit_sql + ") ORDER BY market,unit")
    result = []
    for market, unit in db.execute(sql, units):
        if markets is None or market in markets:
            result.append((market, int(unit)))
    return result


def scan_database(
    db_path: Path, writer: csv.DictWriter, *,
    units: tuple[int, ...] = MINUTE_UNITS, last: int = 0,
    markets: frozenset[str] | None = None,
) -> tuple[int, int, int]:
    """Return pairs/candles/matches. Query each pair in UTC ascending order.

    last=0 tests every historical signal; last>0 tests the newest 'last'
    stored candles per pair, but warms up indicators on all previous history.
    """
    db_path = Path(db_path)
    if not db_path.is_file():
        raise FileNotFoundError(f"Candle DB does not exist: {db_path}")
    db = sqlite3.connect(_database_uri(db_path), uri=True, timeout=30)
    try:
        db.execute("PRAGMA query_only=ON")
        _check_schema(db)
        pairs = _pairs(db, units, markets)
        candles = hits = 0
        stem = db_path.stem.lower()
        exchange = "upbit" if "upbit" in stem else (
            "bithumb" if "bithumb" in stem else stem
        )
        for market, unit in pairs:
            count = db.execute(
                "SELECT COUNT(*) FROM candles WHERE market=? AND unit=?",
                (market, unit),
            ).fetchone()[0]
            report_from = max(0, count - last) if last else 0
            indicators = Indicators()
            cursor = db.execute(
                "SELECT utc,kst,close FROM candles "
                "WHERE market=? AND unit=? ORDER BY utc ASC",
                (market, unit),
            )
            for index, (utc, kst, price) in enumerate(cursor):
                if price is None:
                    raise ValueError(f"{market}/{unit}/{utc}: missing close")
                close = float(price)
                if not math.isfinite(close) or close <= 0:
                    raise ValueError(f"{market}/{unit}/{utc}: invalid close")
                current = indicators.push(close)
                candles += 1
                if current and index >= report_from and is_signal(current):
                    writer.writerow({
                        "exchange": exchange, "market": market,
                        "unit": unit, "utc": utc, "kst": kst,
                        "close": close, **current,
                    })
                    hits += 1
        return len(pairs), candles, hits
    finally:
        db.close()


def scan(
    db_paths: list[Path], output: Path, *,
    units: tuple[int, ...] = MINUTE_UNITS, last: int = 0,
    markets: frozenset[str] | None = None, overwrite: bool = False,
) -> dict[str, int]:
    """Write a UTF-8 BOM CSV atomically; never write to a source database."""
    if not db_paths:
        raise ValueError("At least one --db is required")
    if last < 0:
        raise ValueError("--last must be >= 0 (0 means all history)")
    if not units or any(unit not in MINUTE_UNITS for unit in units):
        raise ValueError("Only 1/3/5/10/15/30/60/240-minute candles supported")
    output = Path(output).resolve()
    sources = [Path(p).resolve(strict=True) for p in db_paths]
    if len(set(sources)) != len(sources):
        raise ValueError("Duplicate source database paths")
    if output in sources:
        raise ValueError("Output cannot overwrite an input database")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Results exist (use --overwrite): {output}")
    if not output.parent.is_dir():
        raise NotADirectoryError(f"Output directory missing: {output.parent}")
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", suffix=".tmp",
            prefix=".pattern-", dir=output.parent, delete=False,
        ) as file:
            temp_path = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            total_pairs = total_candles = total_hits = 0
            for path in sources:
                pairs, candles, hits = scan_database(
                    path, writer, units=units, last=last, markets=markets,
                )
                total_pairs += pairs
                total_candles += candles
                total_hits += hits
        if output.exists() and not overwrite:
            raise FileExistsError(f"Results exist (use --overwrite): {output}")
        os.replace(temp_path, output)
        temp_path = None
        return {
            "databases": len(sources), "pairs": total_pairs,
            "candles_processed": total_candles, "matches": total_hits,
        }
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def parse_units(raw: str) -> tuple[int, ...]:
    if not raw.strip():
        raise ValueError("Timeframes must not be empty")
    units = tuple(int(unit.strip()) for unit in raw.split(","))
    if len(set(units)) != len(units) or any(u not in MINUTE_UNITS for u in units):
        raise ValueError("Unsupported or duplicate timeframe")
    return units


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only historical SMA280/SMA560 golden-cross search."
    )
    parser.add_argument("--db", action="append", type=Path, required=True,
                        help="Existing collector SQLite path; repeat for multiple DBs")
    parser.add_argument("--output", type=Path, default=Path("pattern_matches.csv"))
    parser.add_argument("--last", type=int, default=0,
                        help="Latest N candles per market/timeframe; 0=all history")
    parser.add_argument("--units", default="1,3,5,10,15,30,60,240")
    parser.add_argument("--markets", default="",
                        help="Comma-separated exact markets; default all")
    parser.add_argument("--overwrite", action="store_true",
                        help="Explicitly replace an existing results CSV")
    args = parser.parse_args(argv)
    try:
        units = parse_units(args.units)
        markets = (
            frozenset(part.strip() for part in args.markets.split(","))
            if args.markets.strip() else None
        )
        if markets is not None and any(
            not re.fullmatch(r"KRW-[A-Z0-9]+", m) for m in markets
        ):
            raise ValueError("Market must be KRW-SYMBOL")
        totals = scan(args.db, args.output, units=units, last=args.last,
                      markets=markets, overwrite=args.overwrite)
    except (ValueError, OSError, sqlite3.DatabaseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Completed: {totals['databases']} DB, {totals['pairs']} pairs, "
          f"{totals['candles_processed']} candles processed, "
          f"{totals['matches']} matches -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
