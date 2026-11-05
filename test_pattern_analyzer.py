# -*- coding: utf-8 -*-
"""Offline tests only: no exchange API and no customer market database."""
import csv
from contextlib import closing
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, call

import pattern_analyzer as analyzer


def make_db(folder: Path, name="upbit_candles.sqlite3", count=650, *,
            invalid_at=None, market="KRW-BTC", unit=240) -> Path:
    path = folder / name
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("""CREATE TABLE candles(
            market TEXT NOT NULL, unit INTEGER NOT NULL, utc TEXT NOT NULL,
            kst TEXT NOT NULL, open REAL, high REAL, low REAL,
            close REAL, volume REAL, trade_value REAL,
            PRIMARY KEY(market,unit,utc))""")
        db.executemany(
            "INSERT INTO candles(market,unit,utc,kst,close) VALUES(?,?,?,?,?)",
            ((market, unit, f"2026-01-{i:05d}", f"KST-{i:05d}",
              -1.0 if i == invalid_at else 100.0) for i in range(count)),
        )
    return path


class SignalTests(unittest.TestCase):
    def test_exact_order_golden_cross_above_bollinger(self):
        sample = dict(
            sma_spread_previous=-0.01, sma_spread_current=0.01,
            ema560=14, ema280=13, sma280=12, sma560=11, bb_upper=10,
        )
        self.assertTrue(analyzer.is_signal(sample))
        for field, replacement in [
            ("sma_spread_previous", 0.01), ("sma_spread_current", 0),
            ("ema560", 12), ("ema280", 11), ("bb_upper", 11),
        ]:
            with self.subTest(field=field):
                self.assertFalse(analyzer.is_signal({**sample, field: replacement}))

    def test_flat_series_560_warmup(self):
        model = analyzer.Indicators()
        for n in range(559):
            self.assertIsNone(model.push(100.0))
        result = model.push(100.0)
        self.assertAlmostEqual(result["sma280"], 100)
        self.assertAlmostEqual(result["sma560"], 100)
        self.assertAlmostEqual(result["ema280"], 100)
        self.assertAlmostEqual(result["ema560"], 100)
        self.assertAlmostEqual(result["bb_upper"], 100)
        self.assertIsNone(result["sma_spread_previous"])
        self.assertFalse(analyzer.is_signal(result))
        self.assertFalse(analyzer.is_signal(model.push(100.0)))

    def test_unit_validation(self):
        self.assertEqual(analyzer.parse_units("1,3,5,10,15,30,60,240"),
                         analyzer.MINUTE_UNITS)
        for invalid in ["", "1,1", "1,day", "0", "480"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    analyzer.parse_units(invalid)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_source_hash_unchanged_and_bom_csv(self):
        source = make_db(self.folder)
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        out = self.folder / "matches.csv"
        totals = analyzer.scan([source], out)
        self.assertEqual(totals,
                         {"databases": 1, "pairs": 1,
                          "candles_processed": 650, "matches": 0})
        self.assertEqual(before, hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertTrue(out.read_bytes().startswith(b"\xef\xbb\xbf"))
        with out.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(rows, [])

    def test_all_or_last_n_with_full_history_warmup(self):
        source = make_db(self.folder, count=1000)
        out = self.folder / "matches.csv"
        with patch.object(analyzer, "is_candidate", return_value=True), \
             patch.object(analyzer, "is_signal", return_value=True):
            last = analyzer.scan([source], out, last=10)
        self.assertEqual(last["candles_processed"], 1000)
        self.assertEqual(last["matches"], 10)
        with out.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["utc"], "2026-01-00990")
        self.assertEqual(rows[-1]["utc"], "2026-01-00999")
        with patch.object(analyzer, "is_candidate", return_value=True), \
             patch.object(analyzer, "is_signal", return_value=True):
            all_ = analyzer.scan([source], out, last=0, overwrite=True)
        self.assertEqual(all_["matches"], 441)  # valid from #560 onward

    def test_market_unit_filter(self):
        source = make_db(self.folder, count=700)
        out = self.folder / "matches.csv"
        self.assertEqual(analyzer.scan([source], out, units=(1,))["pairs"], 0)
        with self.assertRaisesRegex(ValueError, "absent from input DB"):
            analyzer.scan([source], out, markets=frozenset(("KRW-ETH",)),
                          overwrite=True)

    def test_existing_file_not_overwritten_unless_flag(self):
        source = make_db(self.folder)
        out = self.folder / "matches.csv"
        out.write_bytes(b"DO_NOT_CHANGE")
        with self.assertRaises(FileExistsError):
            analyzer.scan([source], out)
        self.assertEqual(out.read_bytes(), b"DO_NOT_CHANGE")
        analyzer.scan([source], out, overwrite=True)
        self.assertNotEqual(out.read_bytes(), b"DO_NOT_CHANGE")

    def test_atomic_csv_failure_does_not_leave_partial_output(self):
        source = make_db(self.folder, invalid_at=600)
        out = self.folder / "matches.csv"
        with self.assertRaisesRegex(ValueError, "invalid close"):
            analyzer.scan([source], out)
        self.assertFalse(out.exists())
        self.assertEqual(list(self.folder.glob(".pattern-*.tmp")), [])

    def test_missing_db_not_created_and_output_source_guard(self):
        missing = self.folder / "nonexistent.sqlite3"
        with self.assertRaises(FileNotFoundError):
            analyzer.scan([missing], self.folder / "matches.csv")
        self.assertFalse(missing.exists())
        source = make_db(self.folder)
        with self.assertRaises(ValueError):
            analyzer.scan([source], source)

    def test_incompatible_schema_preserved(self):
        source = self.folder / "other.sqlite3"
        with closing(sqlite3.connect(source)) as db, db:
            db.execute("CREATE TABLE candles (utc TEXT)")
        original = source.read_bytes()
        with self.assertRaisesRegex(ValueError, "Incompatible"):
            analyzer.scan([source], self.folder / "matches.csv")
        self.assertEqual(source.read_bytes(), original)


    def test_real_calculated_cross_from_synthetic_price_history(self):
        """An actual indicator series (not mocked) must emit one match."""
        segments = [
            (15,35.29), (34,28.26), (99,45.13), (53,48.11),
            (95,22.02), (65,15.44), (83,14.42), (53,12.29),
            (90,46.93), (26,47.07), (26,8.20), (66,23.36),
            (54,9.38), (49,19.26), (65,14.36),
        ]
        prices = [price for count, price in segments for _ in range(count)]
        source = make_db(self.folder, count=0)
        with closing(sqlite3.connect(source)) as db, db:
            db.executemany(
                "INSERT INTO candles(market,unit,utc,kst,close) VALUES(?,?,?,?,?)",
                (("KRW-BTC", 240, f"2026-01-{i:05d}",
                  f"KST-{i:05d}", price) for i, price in enumerate(prices))
            )
        out = self.folder / "matches.csv"
        totals = analyzer.scan([source], out)
        self.assertEqual(totals["matches"], 1)
        with out.open(encoding="utf-8-sig", newline="") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["utc"], "2026-01-00669")
        self.assertGreater(float(row["sma560"]), float(row["bb_upper"]))
        self.assertGreater(float(row["ema560"]), float(row["ema280"]))
        self.assertEqual(analyzer.scan(
            [source], out, last=100, overwrite=True
        )["matches"], 0)

    def test_ticker_parse_search_and_market_list(self):
        source = make_db(self.folder, count=700)
        self.assertEqual(analyzer.parse_markets("btc,KRW-ETH"),
                         frozenset({"KRW-BTC", "KRW-ETH"}))
        self.assertIsNone(analyzer.parse_markets("all"))
        self.assertEqual(analyzer.list_markets([source]), ["KRW-BTC"])
        for invalid in ["BTC,", "BTC;ETH", "KRW-", "!BTC"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    analyzer.parse_markets(invalid)

    def test_selected_market_and_all_markets_independent(self):
        source = make_db(self.folder, count=800)
        with closing(sqlite3.connect(source)) as db, db:
            db.executemany(
                "INSERT INTO candles(market,unit,utc,kst,close) VALUES(?,?,?,?,?)",
                (("KRW-ETH", 240, f"2026-01-{i:05d}",
                  f"KST-{i:05d}", 110.0) for i in range(800))
            )
        out = self.folder / "matches.csv"
        selected = analyzer.scan([source], out,
                                 markets=analyzer.parse_markets("ETH"))
        self.assertEqual(selected["pairs"], 1)
        self.assertEqual(selected["candles_processed"], 800)
        both = analyzer.scan([source], out, overwrite=True)
        self.assertEqual(both["pairs"], 2)
        self.assertEqual(both["candles_processed"], 1600)

    def test_interactive_specific_selection(self):
        source = make_db(self.folder, count=700)
        out = self.folder / "selected.csv"
        # DB was given; choose selected market, timeframe, limit, result, start.
        answers = ["2", "BTC", "240", "100", str(out), "Y"]
        with patch.object(analyzer, "_prompt", side_effect=answers):
            self.assertEqual(analyzer.main(["--interactive", "--db", str(source)]), 0)
        self.assertTrue(out.exists())
        with out.open(encoding="utf-8-sig", newline="") as file:
            self.assertEqual(list(csv.DictReader(file)), [])

    def test_interactive_unknown_market_then_retry(self):
        markets = ["KRW-BTC", "KRW-ETH"]
        with patch.object(analyzer, "_prompt", side_effect=["3", "XRP", "2", "DOGE", "2", "ETH"]):
            self.assertEqual(analyzer._interactive_markets(markets),
                             frozenset({"KRW-ETH"}))

    def test_cli_select_market_and_list(self):
        source = make_db(self.folder, count=700)
        out = self.folder / "cli.csv"
        self.assertEqual(analyzer.main(["--db", str(source), "--markets", "BTC",
                                        "--units", "240", "--last", "20",
                                        "--quiet", "--output", str(out)]), 0)
        self.assertEqual(analyzer.main(["--db", str(source), "--list-markets"]), 0)
        self.assertEqual(analyzer.main(["--db", str(source), "--markets", "ETH",
                                        "--output", str(self.folder / "missing.csv")]), 2)
        self.assertFalse((self.folder / "missing.csv").exists())

    def test_progress_and_source_safety(self):
        source = make_db(self.folder, count=5000)
        original = hashlib.sha256(source.read_bytes()).digest()
        log = []
        output = self.folder / "progress.csv"
        result = analyzer.scan([source], output, progress=True, report=log.append)
        self.assertEqual(result["candles_processed"], 5000)
        self.assertTrue(any("100.0%" in row for row in log))
        self.assertEqual(original, hashlib.sha256(source.read_bytes()).digest())
        self.assertFalse((self.folder / "upbit_candles.sqlite3-wal").exists())

    def test_refuses_non_csv_target_even_with_overwrite(self):
        source = make_db(self.folder)
        original = source.read_bytes()
        with self.assertRaisesRegex(ValueError, "separate .csv"):
            analyzer.scan([source], self.folder / "other.sqlite3", overwrite=True)
        self.assertEqual(source.read_bytes(), original)

    def test_bollinger_only_on_cross_candidates(self):
        source = make_db(self.folder, count=1000)
        out = self.folder / "matches.csv"
        with patch.object(analyzer.Indicators, "bollinger_upper", side_effect=AssertionError("not called")):
            result = analyzer.scan([source], out)
        self.assertEqual(result["matches"], 0)

    def test_large_history_with_last_1000(self):
        source = make_db(self.folder, count=12345)
        out = self.folder / "large.csv"
        with patch.object(analyzer, "is_candidate", return_value=True), \
             patch.object(analyzer, "is_signal", return_value=True):
            result = analyzer.scan([source], out, last=1000)
        self.assertEqual(result["candles_processed"], 12345)
        self.assertEqual(result["matches"], 1000)
        with out.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(rows[0]["utc"], "2026-01-11345")

    def test_unicode_database_path(self):
        source = make_db(self.folder, name="한글 공백#?.sqlite3")
        out = self.folder / "out.csv"
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        result = analyzer.scan([source], out)
        self.assertEqual(result["candles_processed"], 650)
        self.assertEqual(digest, hashlib.sha256(source.read_bytes()).hexdigest())

    def test_multiple_databases_output(self):
        source1 = make_db(self.folder, name="upbit_candles.sqlite3")
        source2 = make_db(self.folder, name="bithumb_candles.sqlite3")
        out = self.folder / "combined.csv"
        stats = analyzer.scan([source1, source2], out)
        self.assertEqual(stats["pairs"], 2)
        self.assertEqual(stats["candles_processed"], 1300)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analyzer.scan([source1, source1], out, overwrite=True)

    def test_cli_smoke(self):
        source = make_db(self.folder)
        out = self.folder / "matches.csv"
        self.assertEqual(analyzer.main([
            "--db", str(source), "--output", str(out), "--last", "10000",
            "--units", "240", "--markets", "KRW-BTC",
        ]), 0)
        self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
