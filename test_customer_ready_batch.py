"""Safety/consistency regressions on the real batch rule scanner with synthetic SQLite."""
from __future__ import annotations

import csv
from contextlib import closing
import sqlite3
from pathlib import Path
import tempfile
import unittest

import custom_rule_engine as e


class CustomerReadyBatchTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="coin-batch-hardening-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.db = self.root / "upbit.sqlite3"
        self.out = self.root / "matches.csv"
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute("""CREATE TABLE candles(
               market TEXT,unit INTEGER,utc TEXT,kst TEXT,
               open REAL,high REAL,low REAL,close REAL,
               PRIMARY KEY(market,unit,utc))""")
            c.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)",
                          [("KRW-BTC",1,"t%03d"%i,"k%03d"%i,10.,11.,9.,10.) for i in range(10)])
        self.rules=(("SAFE_RULE", {"gt": ["high", "low"]}),)

    def scan(self,**kwargs):
        return e.scan([self.db], self.rules, self.out, **kwargs)

    def test_max_matches_exact_boundary(self):
        self.assertEqual(self.scan(max_matches=10)["matches"], 10)

    def test_max_matches_fail_closed_and_preserve_existing_csv(self):
        self.out.write_bytes(b"KEEP_CUSTOMER_REPORT")
        with self.assertRaisesRegex(e.RuleError, "safety limit"):
            self.scan(overwrite=True, max_matches=9)
        self.assertEqual(self.out.read_bytes(), b"KEEP_CUSTOMER_REPORT")
        self.assertEqual(list(self.root.glob(".custom-pattern-*.tmp")), [])

    def test_max_matches_invalid_type_and_range(self):
        for count in (0,-1,1_000_001,True,1.2,"100"):
            with self.subTest(count=count), self.assertRaises(e.RuleError):
                self.scan(max_matches=count)
        self.assertFalse(self.out.exists())

    def test_duplicate_source_rejected_before_read(self):
        with self.assertRaisesRegex(e.RuleError, "Duplicate source"):
            e.scan([self.db,self.db],self.rules,self.out)
        self.assertFalse(self.out.exists())

    def test_identical_stems_across_directories_rejected(self):
        other=self.root/"other";other.mkdir()
        duplicate=other/self.db.name
        duplicate.write_bytes(self.db.read_bytes())
        with self.assertRaisesRegex(e.RuleError, "Duplicate source labels"):
            e.scan([self.db,duplicate],self.rules,self.out)
        self.assertFalse(self.out.exists())

    def test_non_csv_extension_refused(self):
        with self.assertRaisesRegex(e.RuleError, "CSV"):
            e.scan([self.db],self.rules,self.root/"customer.sqlite3",overwrite=True)

    def test_ohlc_impossible_high_prevents_published_output(self):
        with closing(sqlite3.connect(self.db)) as c,c:
            c.execute("UPDATE candles SET high=8 WHERE utc='t002'")
        with self.assertRaisesRegex(e.RuleError,"Invalid OHLC"):
            self.scan()
        self.assertFalse(self.out.exists())

    def test_ohlc_impossible_low_prevents_published_output(self):
        with closing(sqlite3.connect(self.db)) as c,c:
            c.execute("UPDATE candles SET low=12 WHERE utc='t002'")
        with self.assertRaisesRegex(e.RuleError,"Invalid OHLC"):
            self.scan()
        self.assertFalse(self.out.exists())

    def test_nonkrw_market_is_excluded(self):
        with closing(sqlite3.connect(self.db)) as c,c:
            c.execute("INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)",
                      ("USDT-BTC",1,"t100","k100",10.,11.,9.,10.))
        result=self.scan()
        self.assertEqual(result["pairs"],1)
        self.assertEqual(result["matches"],10)
        with self.out.open(encoding="utf-8-sig",newline="") as f:
            self.assertEqual({r["market"] for r in csv.DictReader(f)},{"KRW-BTC"})

    def test_invalid_timestamp_causes_full_result_rollback(self):
        with closing(sqlite3.connect(self.db)) as c,c:
            c.execute("UPDATE candles SET kst=NULL WHERE utc='t003'")
        with self.assertRaisesRegex(e.RuleError,"timestamp"):
            self.scan()
        self.assertFalse(self.out.exists())

    def test_no_output_when_source_invalid_late(self):
        with closing(sqlite3.connect(self.db)) as c,c:
            c.execute("UPDATE candles SET high=3 WHERE utc='t009'")
        self.out.write_bytes(b"OLD_OK")
        with self.assertRaises(e.RuleError):
            self.scan(overwrite=True)
        self.assertEqual(self.out.read_bytes(),b"OLD_OK")
