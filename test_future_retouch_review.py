# -*- coding: utf-8 -*-
import csv
import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import future_retouch_review as review

FIELDS = ["exchange", "market", "unit", "utc", "kst", "close", "sma280", "sma560", "ema280", "ema560", "bb_upper", "sma_spread_previous", "sma_spread_current"]
BASE = datetime(2026, 11, 1, 0, 0, 0)


def utc(minutes):
    return (BASE + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def kst(minutes):
    return (BASE + timedelta(hours=9, minutes=minutes)).isoformat(timespec="seconds")


class ReviewTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db_path = self.root / "한글 # ? upbit_candles.sqlite3"
        self.csv_path = self.root / "results.csv"
        self.out = self.root / "review"
        self.candles = []
        self.signals = []

    def candle(self, market, unit, at, close, *, op=None, high=None, low=None):
        op = close if op is None else op
        high = max(op, close) if high is None else high
        low = min(op, close) if low is None else low
        self.candles.append((market, unit, utc(at), kst(at), op, high, low, close))

    def signal(self, market, unit, at, price, exchange="upbit"):
        self.signals.append(dict(exchange=exchange,market=market,unit=unit,utc=utc(at),kst=kst(at),close=price,
             sma280=price, sma560=price, ema280=price, ema560=price, bb_upper=price,
             sma_spread_previous=-1,sma_spread_current=1))

    def materialize(self):
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute("""CREATE TABLE candles(market TEXT NOT NULL, unit INTEGER NOT NULL, utc TEXT NOT NULL,
            kst TEXT NOT NULL, open REAL, high REAL, low REAL, close REAL, PRIMARY KEY(market,unit,utc))""")
            db.executemany("INSERT INTO candles(market,unit,utc,kst,open,high,low,close) VALUES (?,?,?,?,?,?,?,?)",self.candles)
        with self.csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            wr = csv.DictWriter(f,fieldnames=FIELDS)
            wr.writeheader();wr.writerows(self.signals)

    def run_case(self):
        self.materialize()
        return review.run(self.db_path,self.csv_path,self.out,report=None)

    def rows(self,filename):
        with (self.out/filename).open(encoding="utf-8-sig",newline="") as f:
            return list(csv.DictReader(f))

    def test_first_touch_in_second_future_bar_with_wait(self):
        self.signal("KRW-BTC", 60, 0, 100)
        self.candle("KRW-BTC", 60, 0, 100, high=110,low=90) # own candle must be ignored
        self.candle("KRW-BTC", 60, 60, 91,high=99,low=80)
        self.candle("KRW-BTC", 60, 120, 98,high=100,low=89)
        summary = self.run_case()
        self.assertEqual((summary["untouched"],summary["touched"],summary["unresolved"]),(0,1,0))
        e = self.rows("02_retouch_backtest.csv")[0]
        self.assertEqual(e["bars_to_first_touch"],"2")
        self.assertEqual(e["elapsed_minutes"],"120")
        self.assertEqual(e["first_touch_type"],"RANGE_TOUCH")
        self.assertEqual(e["first_touch_utc"],utc(120))
        self.assertEqual(len(self.rows("01_untouched.csv")),0)
        self.assertIn("KRW-BTC",(self.out/"report.html").read_text())

    def test_gap_above_range_retouch(self):
        self.signal("KRW-ETH", 5, 0, 100)
        self.candle("KRW-ETH",5,0,100)
        self.candle("KRW-ETH",5,5,120,op=125,high=130,low=111)
        self.run_case()
        self.assertEqual(self.rows("02_retouch_backtest.csv")[0]["first_touch_type"],"FULL_CANDLE_ABOVE")

    def test_no_retouch_with_future_bars(self):
        self.signal("KRW-DOGE",1,0,100)
        self.candle("KRW-DOGE",1,0,100,high=115,low=90)
        self.candle("KRW-DOGE",1,1,98,high=99,low=80)
        self.candle("KRW-DOGE",1,2,97,high=99.99,low=90)
        self.run_case()
        e = self.rows("01_untouched.csv")[0]
        self.assertEqual(e["outcome"],"UNTOUCHED_OBSERVED")
        self.assertEqual(e["observed_future_bars"],"2")
        self.assertEqual(e["last_observed_utc"],utc(2))

    def test_no_future_not_a_valid_untouched(self):
        self.signal("KRW-BTC",240,0,100);self.candle("KRW-BTC",240,0,100)
        self.run_case()
        self.assertEqual(self.rows("03_unresolved.csv")[0]["outcome"],"NO_FUTURE_CANDLES")
        self.assertEqual(self.rows("01_untouched.csv"),[])

    def test_missing_signal_in_db(self):
        self.signal("KRW-ETH",1,0,100)
        self.candle("KRW-ETH",1,1,99,high=99)
        self.run_case()
        self.assertEqual(self.rows("03_unresolved.csv")[0]["outcome"],"SIGNAL_NOT_FOUND")

    def test_signal_price_mismatch(self):
        self.signal("KRW-ETH",1,0,100)
        self.candle("KRW-ETH",1,0,99)
        self.candle("KRW-ETH",1,1,101)
        self.run_case()
        self.assertEqual(self.rows("03_unresolved.csv")[0]["outcome"],"SIGNAL_PRICE_MISMATCH")

    def test_multiple_signals_same_group_hit_at_different_times(self):
        self.signal("KRW-BTC",1,0,100)
        self.signal("KRW-BTC",1,2,105)
        self.candle("KRW-BTC",1,0,100)
        self.candle("KRW-BTC",1,1,90,high=99)
        self.candle("KRW-BTC",1,2,105,op=105,high=110,low=90)
        self.candle("KRW-BTC",1,3,96,high=101)
        self.candle("KRW-BTC",1,4,107,high=108)
        self.run_case()
        e=self.rows("02_retouch_backtest.csv")
        self.assertEqual([r["bars_to_first_touch"] for r in e],["2","2"])
        self.assertEqual([r["first_touch_utc"] for r in e],[utc(2),utc(4)])

    def test_duplicate_signals_rejected(self):
        self.signal("KRW-BTC",1,0,100)
        self.signal("KRW-BTC",1,0,100)
        self.candle("KRW-BTC",1,0,100)
        self.materialize()
        with self.assertRaisesRegex(ValueError,"duplicate signal"):
            review.run(self.db_path,self.csv_path,self.out,report=None)
        self.assertFalse(self.out.exists())

    def test_corrupt_ohlc_no_false_untouched_or_partial_output(self):
        self.signal("KRW-BTC",1,0,100)
        self.candle("KRW-BTC",1,0,100)
        self.candle("KRW-BTC",1,1,90,op=90,high=80,low=91)
        self.materialize()
        with self.assertRaisesRegex(ValueError,"Invalid OHLC range"):
            review.run(self.db_path,self.csv_path,self.out,report=None)
        self.assertFalse(self.out.exists())

    def test_existing_output_protected(self):
        self.signal("KRW-BTC",1,0,100)
        self.candle("KRW-BTC",1,0,100)
        self.materialize();self.out.mkdir();(self.out/"old.txt").write_text("safe")
        with self.assertRaises(FileExistsError):
            review.run(self.db_path,self.csv_path,self.out,report=None)
        self.assertEqual((self.out/"old.txt").read_text(),"safe")

    def test_original_db_and_csv_hash_unchanged(self):
        self.signal("KRW-BTC",1,0,100)
        self.candle("KRW-BTC",1,0,100)
        self.candle("KRW-BTC",1,1,99)
        self.materialize()
        before=(hashlib.sha256(self.db_path.read_bytes()).hexdigest(),hashlib.sha256(self.csv_path.read_bytes()).hexdigest())
        review.run(self.db_path,self.csv_path,self.out,report=None)
        after=(hashlib.sha256(self.db_path.read_bytes()).hexdigest(),hashlib.sha256(self.csv_path.read_bytes()).hexdigest())
        self.assertEqual(before,after)
        self.assertFalse(Path(str(self.db_path)+"-wal").exists())

    def test_no_index_rejected(self):
        with closing(sqlite3.connect(self.db_path)) as db,db:
            db.execute("CREATE TABLE candles (market TEXT,unit INTEGER,utc TEXT,kst TEXT,open REAL,high REAL,low REAL,close REAL)")
        with self.assertRaisesRegex(ValueError,"indexed"):
            review.connect_readonly(self.db_path)

    def test_html_escaped_script_boundary(self):
        h=review.make_html([{"market":"KRW-BTC","unit":"1","outcome":"RETOUCHED","utc":utc(0),"danger":"</script><script>alert(1)</script>"}],dict(total=1,untouched=0,touched=1,unresolved=0))
        self.assertNotIn('"danger": "</script>',h)
        self.assertIn('\\u003c/script>',h)

    def test_reference_sma280_can_be_selected_not_signal_close(self):
        self.signal("KRW-BTC",1,0,100)
        self.signals[0]["sma280"] = 110  # golden-cross level differs from trade close
        self.candle("KRW-BTC",1,0,100,high=120,low=90)
        self.candle("KRW-BTC",1,1,105,high=108,low=98)
        self.materialize()
        review.run(self.db_path,self.csv_path,self.out,price_field="sma280",report=None)
        self.assertEqual(self.rows("01_untouched.csv")[0]["reference_price"],"110")
        self.assertEqual(len(self.rows("02_retouch_backtest.csv")),0)
        # Choosing candle close instead must classify this same high as reached.
        summary=review.run(self.db_path,self.csv_path,self.root/"close_based",price_field="close",report=None)
        self.assertEqual(summary["touched"],1)

    def test_default_bb_upper_fixed_at_signal_and_not_sma(self):
        # BB upper=95, SMA280=110, close=100: 100~109 future wick reaches BB,
        # but must NOT be treated as reaching the higher golden-cross SMA.
        self.signal("KRW-AXS",240,0,100)
        self.signals[0]["sma280"] = 110
        self.signals[0]["bb_upper"] = 95
        self.candle("KRW-AXS",240,0,100,high=120,low=80)
        self.candle("KRW-AXS",240,240,90,op=90,high=94.9999,low=85)
        self.candle("KRW-AXS",240,480,100,op=96,high=105,low=95)
        summary=self.run_case()
        self.assertEqual(summary["reference_field"],"bb_upper")
        self.assertEqual((summary["untouched"],summary["touched"]),(0,1))
        row=self.rows("02_retouch_backtest.csv")[0]
        self.assertEqual(row["reference_price"],"95")
        self.assertEqual(row["reference_field"],"bb_upper")
        self.assertEqual(row["first_touch_utc"],utc(480))
        self.assertEqual(row["bars_to_first_touch"],"2")
        self.assertIn("볼린저밴드 상단",(self.out/"report.html").read_text(encoding="utf-8"))
        summary2=review.run(self.db_path,self.csv_path,self.root/"sma_compare",price_field="sma280",report=None)
        self.assertEqual(summary2["untouched"],1)

    def test_bb_upper_equal_high_counts_touch(self):
        self.signal("KRW-BTC",1,0,100)
        self.signals[0]["bb_upper"] = 95.0
        self.candle("KRW-BTC",1,0,100,high=130,low=90)
        self.candle("KRW-BTC",1,1,94,high=95,low=91)
        self.run_case()
        self.assertEqual(self.rows("02_retouch_backtest.csv")[0]["first_touch_type"],"RANGE_TOUCH")

    def test_bb_upper_missing_header_fails_without_output(self):
        self.signal("KRW-BTC",1,0,100);self.candle("KRW-BTC",1,0,100)
        self.materialize()
        with self.csv_path.open(encoding="utf-8-sig",newline="") as inp:
            rows=list(csv.DictReader(inp))
        columns=[c for c in FIELDS if c!="bb_upper"]
        with self.csv_path.open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
            writer.writeheader();writer.writerows(rows)
        with self.assertRaisesRegex(ValueError,"Reference price column missing: bb_upper"):
            review.run(self.db_path,self.csv_path,self.out,report=None)
        self.assertFalse(self.out.exists())

    def test_status_counts_partition_correctly(self):
        self.signal("KRW-ETH",1,0,100)
        self.signal("KRW-BTC",1,0,100)
        self.signal("KRW-DOGE",1,0,100)
        self.candle("KRW-ETH",1,0,100);self.candle("KRW-ETH",1,1,101)
        self.candle("KRW-BTC",1,0,100);self.candle("KRW-BTC",1,1,99)
        self.candle("KRW-DOGE",1,0,100)
        summary=self.run_case()
        self.assertEqual((summary["total"],summary["untouched"],summary["touched"],summary["unresolved"]),(3,1,1,1))
        self.assertEqual(sum(len(self.rows(n)) for n in ("01_untouched.csv","02_retouch_backtest.csv","03_unresolved.csv")),3)
        self.assertEqual(len(self.rows("04_all_classified.csv")),3)
        self.assertEqual(json.loads((self.out/"summary.json").read_text())["total"],3)

if __name__=="__main__":
    unittest.main()
