# -*- coding: utf-8 -*-
"""Self-contained customer install verification; no market data, network or source DB access.

Runs canonical P1/P2 through the public coin_analyzer entry point, then a real
CSV -> HTML -> evidence receipt round trip on generated temporary SQLite only.
"""
from __future__ import annotations

from contextlib import closing, redirect_stdout, redirect_stderr
import hashlib
from io import StringIO
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

import coin_analyzer
import coin_report
import coin_evidence_receipt


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_selftest() -> dict:
    with tempfile.TemporaryDirectory(prefix="coin-analyzer-selftest-") as tmp:
        root = Path(tmp)
        db = root / "synthetic_upbit.sqlite3"
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("""CREATE TABLE candles (
                market TEXT, unit INTEGER, utc TEXT, kst TEXT,
                open REAL, high REAL, low REAL, close REAL,
                volume REAL, trade_value REAL, PRIMARY KEY(market,unit,utc))""")
            conn.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)", [
                ("KRW-BTC", 1, f"2026-01-{i+1:02d}T00:00:00",
                 f"2026-01-{i+1:02d}T09:00:00", c,c+1,c-1,c,100.,1000.)
                for i,c in enumerate([10.,10.,10.,10.,10.,14.,15.,16.])])
        original = _sha(db)
        rule = {"name": "High above low", "when": {
            "left": {"field": "high"}, "op": ">", "right": {"field": "low"}}}
        single = root / "single.json"
        batch = root / "batch.json"
        single.write_text(json.dumps({"version": 1, **rule}), encoding="utf-8")
        batch.write_text(json.dumps({"version": 1, "rules": [rule]}), encoding="utf-8")
        results = []
        for flag, source, stem in (("--rule",single,"single"),("--rules",batch,"batch")):
            csv_path = root / f"{stem}.csv"
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                rc = coin_analyzer.main(["--db",str(db),flag,str(source),
                                         "--output",str(csv_path),"--markets","BTC",
                                         "--units","1"])
            if rc != 0:
                raise ValueError("SYNTHETIC_SCAN_FAILED")
            html_file = root / f"{stem}.html"
            summary = coin_report.render_csv(csv_path,html_file)
            if summary["matches"] != 8:
                raise ValueError("SYNTHETIC_REPORT_MISMATCH")
            receipt_data = coin_evidence_receipt.build(csv_path,source)
            receipt_file = root / f"{stem}.receipt.json"
            coin_evidence_receipt.save_new(receipt_data,receipt_file)
            if not coin_evidence_receipt.verify(csv_path,source,receipt_file):
                raise ValueError("SYNTHETIC_RECEIPT_MISMATCH")
            if "High above low" not in html_file.read_text(encoding="utf-8"):
                raise ValueError("SYNTHETIC_HTML_MISSING_FORMULA")
            results.append({"mode":stem,"matches":receipt_data["matches"],
                            "csv_sha256":receipt_data["csv_sha256"]})
        if results[0]["csv_sha256"] != results[1]["csv_sha256"]:
            raise ValueError("SINGLE_BATCH_CSV_PARITY_FAILED")
        if _sha(db) != original:
            raise ValueError("SYNTHETIC_SOURCE_MODIFIED")
        return {"contract": "coin-analyzer.selftest.v1", "status":"PASS_SYNTHETIC_ONLY",
                "scanned_real_customer_db":False,"network_calls":0,
                "verified_modes":2,"verified_matches_per_mode":8,
                "source_db_unchanged":True,"receipts_verified":2,
                "ready_for_customer_data":False}


def main() -> int:
    try:
        result = run_selftest()
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (OSError, ValueError, sqlite3.DatabaseError) as exc:
        print(json.dumps({"contract":"coin-analyzer.selftest.v1","status":"FAIL_CLOSED",
                          "reason":str(exc) if str(exc).startswith("SYNTHETIC_") else "INTEGRATION_FAILURE",
                          "ready_for_customer_data":False},sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
