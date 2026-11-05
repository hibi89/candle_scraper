# -*- coding: utf-8 -*-
"""Synthetic offline tests. Do not read customer market data."""
import csv
import hashlib
import math
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import dual_bollinger_scanner as s


def rows(future=(), *, recovery=(88, 94, 87, 93), setup=(100, 100, 80, 80), unit=1):
    values = [(100, 101, 99, 100)] * 20 + [setup, recovery] + list(future)
    date = datetime(2026, 10, 1)
    return [(date.__add__(timedelta(minutes=i*unit)).isoformat(timespec="seconds"),
             (date.__add__(timedelta(minutes=i*unit))+timedelta(hours=9)).isoformat(timespec="seconds"),
             *v) for i,v in enumerate(values)]


def make_db(path: Path, entries=None):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE candles(market TEXT,unit INTEGER,utc TEXT,kst TEXT,open REAL,high REAL,low REAL,close REAL,PRIMARY KEY(market,unit,utc))")
        entries = entries if entries is not None else [("KRW-AXS", 1, rows())]
        for market, unit, bars in entries:
            db.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)",
                           ((market,unit,*r) for r in bars))
    return path


def scan_one(path, market="KRW-AXS", unit=1, last=0):
    db = s.connect_readonly(path)
    try:
        n=db.execute("SELECT count(*) FROM candles WHERE market=? AND unit=?",(market,unit)).fetchone()[0]
        return s.scan_pair(db, market, unit, n, "upbit", last=last)
    finally:
        db.close()


class IndicatorsTests(unittest.TestCase):
    def test_warmup_and_open_center(self):
        indicator=s.Indicators()
        for _ in range(19):
            self.assertIsNone(indicator.push(100, 100))
        self.assertEqual(indicator.push(100,100),(100.,100.,100.))
        lower20,lower4,mid=indicator.push(100,80)
        self.assertAlmostEqual(lower20,90.2822021129, places=8)
        self.assertEqual(lower4,100)
        self.assertEqual(mid,100)
        lower20,lower4,mid=indicator.push(88,93)
        self.assertEqual(mid,97.0)
        self.assertAlmostEqual(lower4,76.21539030917,places=8)

    def test_open_and_close_sources_not_swapped(self):
        ind=s.Indicators()
        for _ in range(20):ind.push(100, 100)
        low20, low4, mid4=ind.push(150, 80)
        self.assertEqual(mid4,112.5)
        self.assertLess(low20,100)
        self.assertNotEqual(low4, low20)

    def test_unit_market_validation(self):
        self.assertEqual(s.parse_units("all"),s.UNITS)
        self.assertEqual(s.parse_units("1,240"),(1,240))
        self.assertEqual(s.parse_markets("AXS,btc"),frozenset(("KRW-AXS","KRW-BTC")))
        for invalid in ("0","1,1","4,foo",""):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):s.parse_units(invalid)
        for invalid in ("BTC,","ETH/USD",""):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):s.parse_markets(invalid)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.db=self.folder/"한글 DB #?.sqlite3"

    def make(self, future=(), recovery=(88,94,87,93),setup=(100,100,80,80), unit=1):
        return make_db(self.db,[("KRW-AXS",unit,rows(future,recovery=recovery,setup=setup,unit=unit))])

    def test_no_future_candles_not_falsely_counted_unreached(self):
        self.make()
        result,meta=scan_one(self.db)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["status"],s.STATUS_NO_FUTURE)
        self.assertEqual(result[0]["observed_future_bars"],0)
        self.assertEqual(result[0]["bb4_open_mid_fixed"],97.0)

    def test_recovery_candle_included_and_touch_at_equal_high(self):
        self.make(recovery=(88,97,87,93))
        result,_=scan_one(self.db)
        self.assertEqual(result[0]["status"],s.STATUS_TOUCHED)
        self.assertEqual(result[0]["touch_bars_after_recovery"],0)
        self.assertEqual(result[0]["touch_minutes_after_recovery"],0)
        self.assertEqual(result[0]["touch_type"],"CANDLE_RANGE")

    def test_future_first_touch_count_and_delay(self):
        self.make([(92,96,90,94),(96,98,95,96)])
        result,_=scan_one(self.db)
        hit=result[0]
        self.assertEqual(hit["status"],s.STATUS_TOUCHED)
        self.assertEqual(hit["touch_bars_after_recovery"],2)
        self.assertEqual(hit["touch_minutes_after_recovery"],2)
        self.assertEqual(hit["bb4_open_mid_fixed"],97.0)
        self.assertEqual(hit["first_touch_high"],98)

    def test_midline_fixed_not_recomputed_on_future_bars(self):
        self.make([(92,96,90,92),(92,96,89,92),(92,96,89,92),(92,96,89,92)])
        result,_=scan_one(self.db)
        self.assertEqual(result[0]["status"],s.STATUS_UNTOUCHED)
        self.assertEqual(result[0]["bb4_open_mid_fixed"],97.)
        self.assertEqual(result[0]["observed_future_bars"],4)

    def test_gap_above_target_counts_as_hit(self):
        self.make([(101,103,100,102)])
        result,_=scan_one(self.db)
        self.assertEqual(result[0]["touch_type"],"GAP_ABOVE")
        self.assertEqual(result[0]["status"],s.STATUS_TOUCHED)

    def test_gap_from_before_reentry_not_counted(self):
        self.make([(89,94,88,91)])
        result,_=scan_one(self.db)
        self.assertEqual(result[0]["status"],s.STATUS_UNTOUCHED)

    def test_reached_then_future_does_not_duplicate_touch(self):
        self.make([(98,102,90,100),(105,106,104,105)])
        result,_=scan_one(self.db)
        self.assertEqual(result[0]["touch_bars_after_recovery"],1)
        self.assertEqual(result[0]["first_touch_high"],102)

    def test_multiple_pending_targets_resolve_independently(self):
        # Older signal target 97 remains active through a later breach/reentry.
        # Newer target 76 is reached earlier, old target later.
        self.make([(90,92,89,92),(90,90,29,30),
                   (36,75,35,75),(80,81,78,80),
                   (80,82,79,81),(100,103,99,102)])
        result,_=scan_one(self.db)
        self.assertEqual(len(result),2)
        self.assertEqual([round(r["bb4_open_mid_fixed"]) for r in result],[97,76])
        self.assertEqual([r["touch_bars_after_recovery"] for r in result],[6,1])

    def test_consecutive_double_lower_breaches_one_episode(self):
        # Both breaches precede first valid reentry. No second duplicate setup.
        self.make([],recovery=(88,89,65,65))
        result,_=scan_one(self.db)
        self.assertEqual(result,[])

    def test_must_close_below_both_lower_not_only_one(self):
        self.make(setup=(100,100,91,91))
        result,_=scan_one(self.db)
        self.assertEqual(len(result),0)

    def test_must_close_above_base20_to_recover(self):
        self.make(recovery=(88,89,83,84))
        result,_=scan_one(self.db)
        self.assertEqual(len(result),0)
        self.assertEqual(result,[])

    def test_setup_before_recovery_does_not_preemptively_touch(self):
        self.make(recovery=(88,94,87,93))
        result,_=scan_one(self.db)
        self.assertEqual(result[0]["status"],s.STATUS_NO_FUTURE)
        self.assertEqual(result[0]["setup_close"],80)
        self.assertEqual(result[0]["recovery_close"],93)

    def test_nonzero_unit_has_actual_minutes(self):
        self.make([(92,96,90,94),(96,98,95,96)], unit=240)
        result,_=scan_one(self.db, unit=240)
        self.assertEqual(result[0]["touch_minutes_after_recovery"],480)

    def test_recent_N_filters_only_recovery_not_indicator_history(self):
        self.make([(92,96,90,94),(96,98,95,96)])
        result,_=scan_one(self.db,last=2)
        self.assertEqual(result,[])
        result,_=scan_one(self.db,last=3)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["status"],s.STATUS_TOUCHED)

    def test_multiple_pairs_isolated_and_filter(self):
        base=rows([(92,96,90,92)])
        other=rows([(101,102,99,101)],unit=240)
        make_db(self.db,[("KRW-AXS",1,base),("KRW-BTC",240,other)])
        with s.connect_readonly(self.db) as conn:
            self.assertEqual(len(s.pairs_for(conn,s.UNITS,None)),2)
            self.assertEqual(len(s.pairs_for(conn,(1,),frozenset(["KRW-AXS"]))),1)
        out,summary=s.run(self.db,self.folder,verbose=False)
        self.assertEqual(summary["signals"],2)
        self.assertEqual(summary["untouched"],1)
        self.assertEqual(summary["reached"],1)
        self.assertTrue((out/"report.html").exists())

    def test_run_readonly_original_hash_and_bom_and_reports(self):
        self.make([(92,96,90,94),(96,98,95,96)])
        before=hashlib.sha256(self.db.read_bytes()).digest()
        out,stats=s.run(self.db,self.folder,verbose=False)
        self.assertEqual(stats["reached"],1)
        self.assertEqual(before,hashlib.sha256(self.db.read_bytes()).digest())
        self.assertFalse(Path(str(self.db)+"-wal").exists())
        self.assertTrue((out/"01_not_reached.csv").read_bytes().startswith(b"\xef\xbb\xbf"))
        with (out/"02_reached_first_touch.csv").open(encoding="utf-8-sig",newline="") as f:
            self.assertEqual(len(list(csv.DictReader(f))),1)
        html=(out/"report.html").read_text(encoding="utf-8")
        self.assertIn('const items=',html)
        self.assertIn('KRW-AXS',html)

    def test_runs_do_not_overwrite_prior_results(self):
        self.make()
        first,_=s.run(self.db,self.folder,verbose=False)
        second,_=s.run(self.db,self.folder,verbose=False)
        self.assertNotEqual(first,second)
        self.assertTrue(first.exists() and second.exists())

    def test_bad_ohlc_does_not_leave_partial_result(self):
        self.make()
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE candles SET high=1 WHERE utc=(SELECT MAX(utc) FROM candles)")
        with self.assertRaisesRegex(ValueError,"inconsistent OHLC"):
            s.run(self.db,self.folder,verbose=False)
        self.assertEqual(list(self.folder.glob(".dual-bb-tmp-*")),[])

    def test_missing_db_does_not_create(self):
        missing=self.folder/"missing.sqlite3"
        with self.assertRaises(FileNotFoundError):s.run(missing,self.folder,verbose=False)
        self.assertFalse(missing.exists())

    def test_wrong_schema_preserved(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE candles(utc TEXT)")
        before=self.db.read_bytes()
        with self.assertRaisesRegex(ValueError,"missing"):
            s.run(self.db,self.folder,verbose=False)
        self.assertEqual(before,self.db.read_bytes())

    def test_no_external_dependencies_and_no_network(self):
        # Explicit source inspection: no requests, http, socket imports or DB writes.
        content=Path(s.__file__).read_text(encoding="utf-8")
        for dangerous in ("import requests", "import urllib.request", "import socket", "INSERT INTO candles", "UPDATE candles", "DELETE FROM candles"):
            self.assertNotIn(dangerous,content)


if __name__=="__main__":unittest.main()
