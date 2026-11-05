# -*- coding: utf-8 -*-
"""Bounded real 10,000-minute-candle recovery proof on disposable SQLite only.

Single KRW-BTC minute market per exchange, <=70 candle API calls/exchange.
Inject one synthetic interruption after two committed pages, resume to 10k,
verify idempotency, incremental update, SQLite integrity and CSV row count.
The output evidence contains counts only; no market data is uploaded.
"""
import csv
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import collector

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "live_history_evidence.json"
MARKET = "KRW-BTC"
UNIT = 1
CAP = 70


def assert_true(value, why):
    if not value:
        raise AssertionError(why)


def inspect(db_path):
    with closing(sqlite3.connect(db_path)) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        count, distinct_count, first, last = db.execute("""
            SELECT COUNT(*), COUNT(DISTINCT utc), MIN(utc), MAX(utc)
            FROM candles WHERE market=? AND unit=?""", (MARKET, UNIT)).fetchone()
        stray = db.execute("SELECT COUNT(*) FROM candles WHERE market!=? OR unit!=?",
                           (MARKET, UNIT)).fetchone()[0]
        state = db.execute("SELECT finished FROM collection_state WHERE market=? AND unit=?",
                           (MARKET, UNIT)).fetchone()
        return {"count": count, "distinct": distinct_count,
                "integrity_ok": integrity == "ok", "stray": stray,
                "finished": None if state is None else state[0],
                "first": first, "last": last}


def check_exchange(exchange, root):
    original = collector.CONFIG[exchange]
    original_request = collector.request
    trial = Path(root) / (exchange + "_history_test_only.sqlite3")
    count_calls = 0
    interrupted = False

    def bounded_request(given_exchange, path, params=None):
        nonlocal count_calls, interrupted
        assert_true(given_exchange == exchange, "unexpected exchange API request")
        assert_true(path == "/candles/minutes/1", "unexpected endpoint")
        assert_true(params and params.get("market") == MARKET, "unexpected market")
        count_calls += 1
        if count_calls > CAP:
            raise RuntimeError("bounded live request budget exceeded")
        if count_calls == 3 and not interrupted:
            interrupted = True
            raise RuntimeError("EXPECTED_SYNTHETIC_INTERRUPTION")
        return original_request(given_exchange, path, params)

    collector.CONFIG[exchange] = (original[0], trial)
    collector.request = bounded_request
    try:
        try:
            collector.collect_pair(exchange, MARKET, UNIT, "initial")
        except RuntimeError as exc:
            assert_true(str(exc) == "EXPECTED_SYNTHETIC_INTERRUPTION", "unexpected collection failure")
        else:
            raise AssertionError("synthetic interruption was not triggered")

        partial = inspect(trial)
        assert_true(350 <= partial["count"] <= 400, "first two pages were not persisted")
        assert_true(partial["integrity_ok"] and partial["stray"] == 0, "invalid partial DB")
        assert_true(partial["finished"] is None, "interrupted collection marked finished")
        print(f"PASS {exchange}: simulated interruption persisted {partial['count']} actual candles")

        n, added, state = collector.collect_pair(exchange, MARKET, UNIT, "initial")
        assert_true((n, state) == (10000, "ok"), f"initial/resume incomplete: {n}, {state}")
        assert_true(n == partial["count"] + added, "resume double-counted candles")
        complete = inspect(trial)
        assert_true(complete["count"] == complete["distinct"] == 10000, "duplicate/short candle history")
        assert_true(complete["finished"] == 1 and complete["integrity_ok"], "broken completion state")
        assert_true(complete["stray"] == 0, "unrequested candles")
        print(f"PASS {exchange}: 10,000 actual complete minute candles after resume")

        again, zero, status = collector.collect_pair(exchange, MARKET, UNIT, "initial")
        assert_true(again == 10000 and zero == 0 and status == "already-finished",
                    "idempotent initial collection failed")

        updated, update_added, status = collector.collect_pair(exchange, MARKET, UNIT, "update")
        assert_true(status == "ok" and updated == 10000 + update_added,
                    "incremental update failed or count decreased")
        after = inspect(trial)
        assert_true(after["count"] == after["distinct"] == updated and after["integrity_ok"],
                    "incremental update corrupted data")
        assert_true(after["first"] == complete["first"] and after["last"] >= complete["last"],
                    "incremental update lost history")
        csv_count, folder = collector.export_csv(exchange, Path(root) / (exchange + "_csv"))
        csv_path = folder / "KRW-BTC_1.csv"
        assert_true(csv_count == 1 and csv_path.exists(), "CSV not created")
        with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            exported = sum(1 for row in reader if len(row) == len(header) == 10)
        assert_true(exported == updated, f"CSV rows {exported} do not match DB {updated}")
        assert_true(csv_path.read_bytes().startswith(b"\xef\xbb\xbf"), "CSV BOM missing")
        print(f"PASS {exchange}: incremental/idempotency/CSV {updated} rows, {count_calls} API calls")
        return {"status": "PASS", "market": MARKET, "unit_minutes": UNIT,
                "interrupted_saved_candles": partial["count"], "resumed_history": 10000,
                "incremental_added": update_added, "total_after_update": updated,
                "api_calls": count_calls, "api_call_cap": CAP,
                "sqlite_integrity": "PASS", "no_duplicate_primary_keys": "PASS",
                "csv_rows_match": "PASS", "clean_temp_db_only": "PASS"}
    finally:
        collector.request = original_request
        collector.CONFIG[exchange] = original


def main():
    assert_true(collector.TARGET == 10000, "release default target unexpectedly changed")
    result = {"source_sha": os.environ.get("GITHUB_SHA", "local"),
              "utc": datetime.now(timezone.utc).isoformat(),
              "scope": "2 exchanges; 1 KRW-BTC 1-minute pair each; 10k each; temporary DB",
              "exchanges": {}}
    try:
        with tempfile.TemporaryDirectory(prefix="candle_10k_live_test_") as temp_root:
            for exchange in ("upbit", "bithumb"):
                try:
                    result["exchanges"][exchange] = check_exchange(exchange, temp_root)
                except Exception as exc:
                    result["exchanges"][exchange] = {
                        "status": "FAIL", "error_type": type(exc).__name__,
                        "error": str(exc)[:180]}
                    print(f"FAIL {exchange}: {type(exc).__name__}: {exc}", file=sys.stderr)
    finally:
        EVIDENCE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    return int(len(result["exchanges"]) != 2 or
               any(v.get("status") != "PASS" for v in result["exchanges"].values()))


if __name__ == "__main__":
    sys.exit(main())
