# -*- coding: utf-8 -*-
"""Offline, read-only historical candle pattern search (Python 3.11+).

No exchange API, no collector imports, no source database writes.
Run without arguments for an interactive market/timeframe/limit menu.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sqlite3
import sys
import tempfile
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable

MINUTE_UNITS = (1, 3, 5, 10, 15, 30, 60, 240)
FIELDS = (
    "exchange", "market", "unit", "utc", "kst", "close",
    "sma280", "sma560", "ema280", "ema560", "bb_upper",
    "sma_spread_previous", "sma_spread_current",
)
REQUIRED_COLUMNS = frozenset(("market", "unit", "utc", "kst", "close"))
MARKET_RE = re.compile(r"KRW-[A-Z0-9]+\Z")


class RollingMean:
    """Bounded-memory, constant-time simple moving average."""

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
    """SMA/EMA(280,560) and Bollinger(20,2). EMA seeded at first close."""

    def __init__(self) -> None:
        self.sma280 = RollingMean(280)
        self.sma560 = RollingMean(560)
        self.bb20 = RollingMean(20)
        self.ema280: float | None = None
        self.ema560: float | None = None
        self.previous_spread: float | None = None

    def bollinger_upper(self) -> float:
        """Numerically stable variance; called only for candidate crosses in scan."""
        basis = self.bb20.total / 20
        variance = math.fsum((value - basis) ** 2 for value in self.bb20.values) / 20
        return basis + 2 * math.sqrt(max(0.0, variance))

    def push(self, close: float, *, compute_band: bool = True) -> dict | None:
        sma280 = self.sma280.push(close)
        sma560 = self.sma560.push(close)
        bb_basis = self.bb20.push(close)
        self.ema280 = (close if self.ema280 is None else
                       self.ema280 + (2 / 281) * (close - self.ema280))
        self.ema560 = (close if self.ema560 is None else
                       self.ema560 + (2 / 561) * (close - self.ema560))
        if sma280 is None or sma560 is None or bb_basis is None:
            return None
        spread = sma280 - sma560
        result = {
            "sma280": sma280, "sma560": sma560,
            "ema280": self.ema280, "ema560": self.ema560,
            "bb_upper": self.bollinger_upper() if compute_band else None,
            "sma_spread_previous": self.previous_spread,
            "sma_spread_current": spread,
        }
        self.previous_spread = spread
        return result


def is_candidate(values: dict) -> bool:
    """Cross and relative order; Bollinger is evaluated only if these pass."""
    previous = values["sma_spread_previous"]
    return bool(
        previous is not None and previous <= 0
        and values["sma_spread_current"] > 0
        and values["ema560"] > values["ema280"]
        > values["sma280"] > values["sma560"]
    )


def is_signal(values: dict) -> bool:
    return bool(
        is_candidate(values)
        and values["bb_upper"] is not None
        and values["sma560"] > values["bb_upper"]
    )


def _database_uri(path: Path) -> str:
    # as_uri handles spaces, non-ASCII and # or ? in Windows paths.
    return path.resolve(strict=True).as_uri() + "?mode=ro"


def _connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"Candle database missing: {path}")
    db = sqlite3.connect(_database_uri(path), uri=True, timeout=30)
    try:
        db.execute("PRAGMA query_only=ON")
        _check_schema(db)
        return db
    except BaseException:
        db.close()
        raise


def _check_schema(db: sqlite3.Connection) -> None:
    columns = {row[1] for row in db.execute("PRAGMA table_info(candles)")}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError("Incompatible candle database; missing fields: "
                         + ", ".join(sorted(missing)))


def list_markets(paths: list[Path]) -> list[str]:
    """Read only the indexed market keys. Never access any exchange API."""
    found: set[str] = set()
    for path in paths:
        db = _connect_readonly(Path(path))
        try:
            found.update(m for (m,) in db.execute(
                "SELECT DISTINCT market FROM candles ORDER BY market"
            ) if MARKET_RE.fullmatch(m or ""))
        finally:
            db.close()
    return sorted(found)


def parse_markets(raw: str) -> frozenset[str] | None:
    """Allow BTC,ETH as shorthand for KRW-BTC,KRW-ETH."""
    if not raw.strip() or raw.strip().lower() in ("all", "전체", "*"):
        return None
    selected: set[str] = set()
    for token in raw.split(","):
        token = token.strip().upper()
        if not token:
            raise ValueError("Empty market name (e.g. BTC,ETH)")
        market = token if token.startswith("KRW-") else "KRW-" + token
        if not MARKET_RE.fullmatch(market):
            raise ValueError(f"Invalid market: {token!r}")
        selected.add(market)
    return frozenset(selected)


def parse_units(raw: str) -> tuple[int, ...]:
    if not raw.strip():
        raise ValueError("Timeframes cannot be empty")
    if raw.strip().lower() in ("all", "전체", "*"):
        return MINUTE_UNITS
    try:
        units = tuple(int(unit.strip()) for unit in raw.split(","))
    except ValueError as exc:
        raise ValueError("Timeframes must be comma-separated minutes") from exc
    if len(set(units)) != len(units) or any(u not in MINUTE_UNITS for u in units):
        raise ValueError("Unsupported or duplicate minute timeframe")
    return units


def _pairs(db: sqlite3.Connection, units: tuple[int, ...],
           markets: frozenset[str] | None) -> list[tuple[str, int, int]]:
    """One ordered index scan returns per-pair row counts for accurate progress."""
    if markets is not None:
        market_sql = ",".join("?" for _ in markets)
        market_clause = f"market IN ({market_sql}) AND "
        params: list = list(sorted(markets))
    else:
        market_clause = ""
        params = []
    unit_sql = ",".join("?" for _ in units)
    params.extend(units)
    sql = ("SELECT market,unit,COUNT(*) FROM candles WHERE " + market_clause
           + f"unit IN ({unit_sql}) GROUP BY market,unit ORDER BY market,unit")
    return [(m, int(u), int(n)) for m, u, n in db.execute(sql, params)]


def _format_eta(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds >= 3600:
        return f"{seconds // 3600}h{(seconds % 3600) // 60}m"
    if seconds >= 60:
        return f"{seconds // 60}m{seconds % 60}s"
    return f"{seconds}s"


class Progress:
    def __init__(self, total: int, pairs: int, output: Callable[[str], None]):
        self.total = total
        self.pairs = pairs
        self.output = output
        self.done = 0
        self.hits = 0
        self.started = time.perf_counter()
        self.last_print = self.started

    def show(self, market: str, unit: int, pair_index: int, *, force=False):
        now = time.perf_counter()
        if not force and now - self.last_print < 2.5:
            return
        self.last_print = now
        elapsed = max(0.01, now - self.started)
        pct = self.done / self.total * 100 if self.total else 100.0
        speed = self.done / elapsed
        eta = _format_eta((self.total - self.done) / speed) if speed else "--"
        self.output(
            f"[{pct:5.1f}%] {pair_index}/{self.pairs} pairs | "
            f"{market} {unit}m | {self.done:,}/{self.total:,} candles | "
            f"matches {self.hits:,} | ETA {eta}"
        )


def scan_database(
    db_path: Path, writer: csv.DictWriter, *,
    units: tuple[int, ...] = MINUTE_UNITS, last: int = 0,
    markets: frozenset[str] | None = None,
    progress: bool = False,
    report: Callable[[str], None] = print,
) -> tuple[int, int, int]:
    """Scan a source entirely in UTC order, report matches in latest N or all.

    Although last>0 constrains result timestamps, historical indicator seed
    prices are processed from the first recorded candle to avoid false crosses.
    """
    db_path = Path(db_path)
    db = _connect_readonly(db_path)
    try:
        if progress:
            report(f"Reading index from {db_path.name} (read only)...")
        pairs = _pairs(db, units, markets)
        count_total = sum(count for _, _, count in pairs)
        meter = Progress(count_total, len(pairs), report) if progress else None
        if progress:
            report(f"Plan: {len(pairs):,} market/timeframe pairs, "
                   f"{count_total:,} stored candles; last={'all' if last == 0 else last}")
        candles = hits = 0
        stem = db_path.stem.lower()
        exchange = "upbit" if "upbit" in stem else (
            "bithumb" if "bithumb" in stem else stem
        )
        for pair_index, (market, unit, count) in enumerate(pairs, 1):
            report_from = max(0, count - last) if last else 0
            indicators = Indicators()
            cursor = db.execute(
                "SELECT utc,kst,close FROM candles "
                "WHERE market=? AND unit=? ORDER BY utc ASC", (market, unit)
            )
            for index, (utc, kst, price) in enumerate(cursor):
                if price is None:
                    raise ValueError(f"{market}/{unit}/{utc}: missing close")
                close = float(price)
                if not math.isfinite(close) or close <= 0:
                    raise ValueError(f"{market}/{unit}/{utc}: invalid close")
                # Big speedup: BB(20) stddev only at candidate cross candles.
                current = indicators.push(close, compute_band=False)
                candles += 1
                if meter:
                    meter.done += 1
                if current and index >= report_from and is_candidate(current):
                    current["bb_upper"] = indicators.bollinger_upper()
                    if is_signal(current):
                        writer.writerow({
                            "exchange": exchange, "market": market,
                            "unit": unit, "utc": utc, "kst": kst,
                            "close": close, **current,
                        })
                        hits += 1
                        if meter:
                            meter.hits += 1
                if meter and index % 2000 == 0:
                    meter.show(market, unit, pair_index)
            if meter:
                meter.show(market, unit, pair_index, force=True)
        return len(pairs), candles, hits
    finally:
        db.close()


def scan(
    db_paths: list[Path], output: Path, *,
    units: tuple[int, ...] = MINUTE_UNITS, last: int = 0,
    markets: frozenset[str] | None = None, overwrite: bool = False,
    progress: bool = False, report: Callable[[str], None] = print,
) -> dict[str, int]:
    """Atomically export UTF-8 BOM CSV, while all source DBs stay read-only."""
    if not db_paths:
        raise ValueError("At least one database is required")
    if last < 0:
        raise ValueError("--last must be >= 0 (0 means entire history)")
    if not units or any(u not in MINUTE_UNITS for u in units):
        raise ValueError("Unsupported minute timeframe")
    output = Path(output).resolve()
    sources = [Path(p).resolve(strict=True) for p in db_paths]
    if len(set(sources)) != len(sources):
        raise ValueError("Duplicate input database paths")
    if output in sources or output.suffix.lower() != ".csv":
        raise ValueError("Output must be a separate .csv file, not a database")
    if output.exists() and not overwrite:
        raise FileExistsError(f"CSV already exists; choose a new name: {output}")
    if not output.parent.is_dir():
        raise NotADirectoryError(f"Output folder not found: {output.parent}")
    if markets is not None:
        available = set(list_markets(sources))
        unknown = markets - available
        if unknown:
            raise ValueError("Markets absent from input DB: " + ", ".join(sorted(unknown)))
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", suffix=".tmp",
            prefix=".pattern-", dir=output.parent, delete=False,
        ) as file:
            temporary = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            total_pairs = total_candles = total_matches = 0
            for db_path in sources:
                pairs, candles, matches = scan_database(
                    db_path, writer, units=units, last=last, markets=markets,
                    progress=progress, report=report,
                )
                total_pairs += pairs
                total_candles += candles
                total_matches += matches
        if output.exists() and not overwrite:
            raise FileExistsError(f"CSV already exists; choose a new name: {output}")
        os.replace(temporary, output)
        temporary = None
        return {
            "databases": len(sources), "pairs": total_pairs,
            "candles_processed": total_candles, "matches": total_matches,
        }
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _prompt(question: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    result = input(f"{question}{hint}: ").strip()
    return result if result else default


def _interactive_markets(available: list[str]) -> frozenset[str] | None:
    print(f"\nDatabase contains {len(available):,} KRW markets.")
    print("[1] All markets (default)")
    print("[2] One or more markets (BTC,ETH,KRW-XRP)")
    print("[3] Find available markets by keyword")
    while True:
        choice = _prompt("Market selection", "1")
        if choice == "1":
            return None
        if choice == "3":
            keyword = _prompt("Ticker search (e.g. SAHARA)").upper()
            results = [m for m in available if keyword in m.upper()]
            print("Found:", ", ".join(results[:60]) or "none")
            if len(results) > 60:
                print(f"... and {len(results) - 60} more")
            continue
        if choice == "2":
            selected = parse_markets(_prompt("Markets, comma-separated"))
            if selected is None:
                continue
            unknown = selected - set(available)
            if unknown:
                print("Not in database:", ", ".join(sorted(unknown)))
                continue
            print("Selected:", ", ".join(sorted(selected)))
            return selected
        print("Choose 1, 2 or 3.")


def interactive(db_paths: list[Path] | None = None) -> int:
    print("\n=== CANDLE PATTERN SEARCH v1.0 (READ ONLY) ===")
    print("SMA280 cross up SMA560, EMA560 > EMA280 > both SMAs > BB upper")
    sources = list(db_paths or [])
    if not sources:
        guesses = [p for p in (
            Path.cwd() / "upbit_candles.sqlite3",
            Path.cwd() / "bithumb_candles.sqlite3",
            Path(__file__).resolve().parent / "upbit_candles.sqlite3",
        ) if p.is_file()]
        default = str(guesses[0]) if guesses else ""
        raw = _prompt("SQLite DB path (paste full path)", default)
        if not raw:
            print("No input database chosen.")
            return 2
        sources = [Path(raw.strip('"\''))]
    available = list_markets(sources)
    if not available:
        print("No KRW market candles found in selected database(s).")
        return 2
    selected = _interactive_markets(available)
    units = parse_units(_prompt("Minute units (all or 1,3,5,10,15,30,60,240)", "all"))
    last = int(_prompt("Search signals from latest N candles (0 = ALL)", "0"))
    if last < 0:
        raise ValueError("Candle count cannot be negative")
    suggested = "pattern_matches_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
    output = Path(_prompt("Results CSV path", suggested).strip('"\''))
    if output.exists():
        raise FileExistsError("Output file exists; please choose another CSV filename")
    print("\nInput(s):", ", ".join(str(p) for p in sources))
    print("Markets:", "ALL" if selected is None else ", ".join(sorted(selected)))
    print("Minutes:", ",".join(str(u) for u in units), "| Lookback:", last or "ALL")
    if _prompt("Run search? (Y/n)", "Y").lower() not in ("y", "yes", "ㅇ"):
        print("Cancelled. No files changed.")
        return 0
    totals = scan(sources, output, units=units, last=last,
                  markets=selected, progress=True)
    print(f"\nCOMPLETE: {totals['pairs']:,} pairs / "
          f"{totals['candles_processed']:,} processed candles / "
          f"{totals['matches']:,} matches")
    print("CSV:", output.resolve())
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(
        description="Read-only, full-history SMA/EMA golden-cross pattern search"
    )
    parser.add_argument("--interactive", action="store_true", help="Market selection menu")
    parser.add_argument("--db", action="append", type=Path,
                        help="Source SQLite path; may repeat")
    parser.add_argument("--list-markets", action="store_true",
                        help="List market codes from selected DB, then exit")
    parser.add_argument("--output", type=Path, default=Path("pattern_matches.csv"))
    parser.add_argument("--last", type=int, default=0,
                        help="Recent N signal candles per pair, 0=all")
    parser.add_argument("--units", default="all")
    parser.add_argument("--markets", default="all",
                        help="ALL, BTC,ETH, or full KRW-BTC,KRW-ETH")
    parser.add_argument("--overwrite", action="store_true",
                        help="Explicitly overwrite output CSV")
    parser.add_argument("--quiet", action="store_true", help="Disable progress output")
    args = parser.parse_args(argv)
    try:
        if args.interactive or not argv:
            return interactive(args.db)
        if not args.db:
            parser.error("--db PATH is required unless using interactive menu")
        if args.list_markets:
            for market in list_markets(args.db):
                print(market)
            return 0
        units = parse_units(args.units)
        markets = parse_markets(args.markets)
        result = scan(args.db, args.output, units=units, last=args.last,
                      markets=markets, overwrite=args.overwrite,
                      progress=not args.quiet)
        print(f"COMPLETE: {result['databases']} DB, {result['pairs']:,} pairs, "
              f"{result['candles_processed']:,} candles, "
              f"{result['matches']:,} matches -> {args.output.resolve()}")
        return 0
    except (OSError, ValueError, sqlite3.DatabaseError, EOFError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted safely. Partial results have been removed.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())