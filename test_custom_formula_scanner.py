# -*- coding: utf-8 -*-
"""Synthetic E2E and parser security regressions, no customer files or HTTP."""
import csv
from contextlib import closing
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import custom_formula_scanner as s


def indicator(kind, period, field="close", multiplier=None):
    val = {"indicator": kind, "field": field, "period": period}
    if multiplier is not None:
        val["multiplier"] = multiplier
    return val


def rule(when, name="Test rule"):
    return {"version": 1, "name": name, "when": when}


def comparison(left, operator, right):
    return {"left": left, "op": operator, "right": right}


def fixture(path, closes=(10, 10, 10, 10, 10, 14, 15, 16), market="KRW-BTC", unit=1):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("""CREATE TABLE candles (market TEXT,unit INTEGER,utc TEXT,kst TEXT,
                   open REAL,high REAL,low REAL,close REAL,volume REAL,trade_value REAL,
                   PRIMARY KEY(market,unit,utc))""")
        db.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?,?,?,?)", [
            (market,unit,f"2026-11-{i+1:02d}T00:00:00",f"2026-11-{i+1:02d}T09:00:00",
             c,c+1,c-1,c,100+i,200+i) for i,c in enumerate(closes)])
    return path


class FormulaCompileTests(unittest.TestCase):
    def test_sma_golden_cross_and_bollinger(self):
        f=s.compile_formula(rule({"all": [
            {"cross_up":[indicator("sma",2),indicator("sma",4)]},
            comparison({"field":"close"},">",indicator("bb_upper",3,multiplier=0))]}))
        self.assertEqual(len(f.digest),64)
        evaluator=s.Evaluator(f)
        values=[10,10,10,10,10,14,15,16]
        matches=[i for i,c in enumerate(values) if evaluator.push({"close":c})]
        self.assertEqual(matches,[5])

    def test_downcross_and_boolean(self):
        f=s.compile_formula(rule({"any":[
            {"cross_down":[indicator("sma",2),indicator("sma",3)]},
            {"not":comparison({"field":"close"},">",{"value":0})}]}))
        hits=[s.Evaluator(f)]
        self.assertFalse(hits[0].push({"close":20}))
        for c in [20,20,20,10]:
            result=hits[0].push({"close":c})
        self.assertTrue(result)

    def test_warmup_not_signal_on_missing_rolling_value(self):
        f=s.compile_formula(rule({"not":comparison(indicator("sma",3),">",{"value":100})}))
        e=s.Evaluator(f)
        self.assertFalse(e.push({"close":1}))
        self.assertFalse(e.push({"close":1}))
        self.assertTrue(e.push({"close":1}))

    def test_wrong_formulas_rejected(self):
        valid=comparison({"field":"close"},">",{"value":10})
        rejected=[
            {"version":2,"name":"x","when":valid},
            rule(valid,name=""), rule(valid,name="a\nb"), rule(valid,name="=RUN()"),
            rule(comparison({"field":"close"},"exec",{"value":1})),
            rule(comparison({"value":float("inf")},">",{"value":1})),
            rule(comparison({"value":True},">",{"value":1})),
            rule(comparison({"field":"__import__"},">",{"value":1})),
            rule(comparison(indicator("sma",0),">",{"value":1})),
            rule(comparison(indicator("sma",561),">",{"value":1})),
            rule(comparison(indicator("bb_upper",2,multiplier=-1),">",{"value":1})),
            rule({"cross_up":[{"field":"close"}]}),
            rule({"all":[]}),rule({"not":{}}),
            rule(valid) | {"extra":"data"},
        ]
        for r in rejected:
            with self.subTest(r=r),self.assertRaises(ValueError):s.compile_formula(r)

    def test_reject_duplicate_json_keys_and_oversize(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"rules.json"
            p.write_text('{"version":1,"version":1,"name":"x","when":{}}')
            with self.assertRaisesRegex(ValueError,"Duplicate JSON key"):s.load_formula(p)
            p.write_text("x" * (s.MAX_RULE_BYTES+1))
            with self.assertRaisesRegex(ValueError,"exceeds"):s.load_formula(p)

    def test_formula_digest_independent_of_key_order(self):
        when=comparison({"field":"close"},">",{"value":10})
        a=s.compile_formula(rule(when))
        b=s.compile_formula({"name":"Test rule","when":when,"version":1})
        self.assertEqual(a.digest,b.digest)


class EndToEnd(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.dir=Path(t.name)
        self.db=fixture(self.dir/"업비트 한글 #?.sqlite3")
        self.out=self.dir/"matched.csv"
        self.rules=rule({"cross_up":[indicator("sma",2),indicator("sma",4)]})
        self.formula=s.compile_formula(self.rules)

    def read_results(self):
        with self.out.open(encoding="utf-8-sig",newline="") as fd:
            return list(csv.DictReader(fd))

    def test_actual_db_cross_and_bom_and_source_unchanged(self):
        digest=hashlib.sha256(self.db.read_bytes()).hexdigest()
        result=s.scan([self.db],self.out,self.formula)
        self.assertEqual(result,{"databases":1,"pairs":1,"candles_processed":8,"matches":1})
        self.assertEqual(self.read_results()[0]["utc"],"2026-11-06T00:00:00")
        self.assertEqual(self.read_results()[0]["formula_sha256"],self.formula.digest)
        self.assertTrue(self.out.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),digest)
        self.assertFalse(Path(str(self.db)+"-wal").exists())

    def test_latest_n_is_output_filter_not_indicator_seed(self):
        full=s.scan([self.db],self.out,self.formula)
        last=s.scan([self.db],self.out,self.formula,last=2,overwrite=True)
        self.assertEqual(full["matches"],1)
        self.assertEqual(last["candles_processed"],8)
        self.assertEqual(last["matches"],0)

    def test_select_units_and_markets(self):
        self.assertEqual(s.scan([self.db],self.out,self.formula,units=(3,))["pairs"],0)
        self.assertEqual(s.scan([self.db],self.out,self.formula,markets=frozenset({"KRW-ETH"}),overwrite=True)["pairs"],0)
        self.assertEqual(s.scan([self.db],self.out,self.formula,markets=frozenset({"KRW-BTC"}),overwrite=True)["matches"],1)

    def test_preserve_existing_csv_and_no_temp_files(self):
        self.out.write_text("KEEP")
        with self.assertRaises(FileExistsError):s.scan([self.db],self.out,self.formula)
        self.assertEqual(self.out.read_text(),"KEEP")
        self.assertFalse(list(self.dir.glob(".formula-*.tmp")))
        self.assertEqual(s.scan([self.db],self.out,self.formula,overwrite=True)["matches"],1)

    def test_output_limit_atomic_failure_and_old_output_preserved(self):
        self.out.write_text("KEEP")
        all_candles=s.compile_formula(rule(comparison({"field":"close"},">",{"value":0})))
        with self.assertRaisesRegex(ValueError,"safety limit"):
            s.scan([self.db],self.out,all_candles,overwrite=True,max_matches=2)
        self.assertEqual(self.out.read_text(),"KEEP")
        self.assertFalse(list(self.dir.glob(".formula-*.tmp")))

    def test_readonly_missing_schema_preserves_db(self):
        bad=self.dir/"bad.sqlite3"
        with closing(sqlite3.connect(bad)) as conn, conn:conn.execute("CREATE TABLE candles (close REAL)")
        before=hashlib.sha256(bad.read_bytes()).digest()
        with self.assertRaisesRegex(ValueError,"Incompatible"):
            s.scan([bad],self.out,self.formula)
        self.assertEqual(hashlib.sha256(bad.read_bytes()).digest(),before)
        self.assertFalse(self.out.exists())

    def test_invalid_candle_fail_closed(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE candles SET close=? WHERE utc='2026-11-06T00:00:00'",(float('inf'),))
        with self.assertRaises(ValueError):s.scan([self.db],self.out,self.formula)
        self.assertFalse(self.out.exists())

    def test_cli_local_rule_and_exit_code(self):
        rule_path=self.dir/"user_rule.json"
        rule_path.write_text(json.dumps(self.rules,ensure_ascii=False),encoding="utf-8")
        args=["--db",str(self.db),"--rule",str(rule_path),"--output",str(self.out),
              "--markets","BTC","--units","1"]
        self.assertEqual(s.main(args),0)
        self.assertEqual(len(self.read_results()),1)
        self.assertEqual(s.main(args),2)
        self.assertEqual(s.main(args+["--overwrite"]),0)

    def test_duplicate_input_and_invalid_selection(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            s.scan([self.db,self.db],self.out,self.formula)
        with self.assertRaises(ValueError):s.scan([self.db],self.out,self.formula,units=(1,1))
        with self.assertRaises(ValueError):s.scan([self.db],self.out,self.formula,markets={"BTC"})
        with self.assertRaises(ValueError):s.scan([self.db],self.out,self.formula,last=-1)
        with self.assertRaises(ValueError):s.scan([self.db],self.db,self.formula)

if __name__ == "__main__":unittest.main()