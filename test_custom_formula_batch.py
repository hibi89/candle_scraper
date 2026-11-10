# -*- coding: utf-8 -*-
"""P1 JSON DSL compatibility, multi-rule same-stream and failure-safety tests."""
import csv
import hashlib
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import custom_formula_scanner as single
import custom_formula_batch as batch
from test_custom_formula_scanner import fixture, indicator, rule, comparison


def cross():
    return {"cross_up": [indicator("sma", 2), indicator("sma", 4)]}


class BatchTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="coin-batch-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = fixture(self.root/"upbit_candles.sqlite3")
        self.out = self.root/"result.csv"
        self.rules = self.root/"rules.json"

    def load(self, rules):
        self.rules.write_text(json.dumps(rules, ensure_ascii=False), encoding="utf-8")
        return batch.load_formula_batch(self.rules)

    def rows(self):
        with self.out.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def test_p1_single_rule_byte_parity(self):
        formula = single.compile_formula(rule(cross(), "GC"))
        a = self.root/"single.csv"
        original = hashlib.sha256(self.db.read_bytes()).digest()
        self.assertEqual(single.scan([self.db], a, formula)["matches"], 1)
        formulas = self.load(rule(cross(), "GC"))
        stats = batch.scan_batch([self.db], self.out, formulas)
        self.assertEqual(stats["matches"], 1)
        self.assertEqual(a.read_bytes(), self.out.read_bytes())
        self.assertEqual(original, hashlib.sha256(self.db.read_bytes()).digest())

    def test_multi_rule_and_zero_lookahead(self):
        rules = {"version":1,"rules":[{"name":"GC","when":cross()},
                                        {"name":"Above 14","when":comparison({"field":"close"},">",{"value":14})}]}
        stats = batch.scan_batch([self.db],self.out,self.load(rules))
        self.assertEqual(stats["candles_processed"],8)
        self.assertEqual(stats["matches_by_formula"], {"GC":1,"Above 14":2})
        self.assertEqual(stats["matches"],3)
        self.assertEqual([x["formula"] for x in self.rows()],["GC","Above 14","Above 14"])
        self.assertEqual(len({x["formula_sha256"] for x in self.rows()}),2)

    def test_recent_window_preserves_warmup(self):
        f=self.load(rule(cross()))
        stats=batch.scan_batch([self.db],self.out,f,last=2)
        self.assertEqual(stats["candles_processed"],8)
        self.assertEqual(stats["matches"],0)

    def test_independent_markets_and_dbs(self):
        other=fixture(self.root/"bithumb_candles.sqlite3",closes=(10,)*8,market="KRW-ETH",unit=3)
        f=self.load(rule(comparison({"field":"close"},">",{"value":0})))
        stats=batch.scan_batch([self.db,other],self.out,f)
        self.assertEqual((stats["databases"],stats["pairs"],stats["matches"]),(2,2,16))
        self.assertEqual({r["exchange"] for r in self.rows()},{"upbit","bithumb"})

    def test_duplicate_names_casefold_and_invalid_shape(self):
        base={"version":1,"rules":[{"name":"GC","when":cross()},{"name":"gc","when":cross()}]}
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            self.load(base)
        for raw in ({"version":True,"rules":[]},{"version":1,"rules":[]},
                    {"version":1,"rules":[{"name":"x","when":cross(),"extra":0}]},
                    {"version":1,"rules":[{"name":"x","when":cross()}]*17}):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                self.load(raw)

    def test_bad_json_duplicate_key_nan_and_size(self):
        for text in ('{"version":1,"version":1,"rules":[]}',
                     '{"version":1,"rules":NaN}'):
            self.rules.write_text(text)
            with self.assertRaises(ValueError):batch.load_formula_batch(self.rules)
        self.rules.write_text('x'*(batch.MAX_BATCH_BYTES+1))
        with self.assertRaises(ValueError):batch.load_formula_batch(self.rules)

    def test_atomic_existing_csv_and_failure_cleanup(self):
        f=self.load(rule(comparison({"field":"close"},">",{"value":0})))
        self.out.write_bytes(b"ORIGINAL_REPORT")
        with self.assertRaises(FileExistsError):batch.scan_batch([self.db],self.out,f)
        with self.assertRaisesRegex(ValueError,"Match limit"):
            batch.scan_batch([self.db],self.out,f,overwrite=True,max_matches=2)
        self.assertEqual(self.out.read_bytes(),b"ORIGINAL_REPORT")
        self.assertEqual(list(self.root.glob('.formula-batch-*.tmp')),[])

    def test_corrupt_ohlc_report_not_published(self):
        f=self.load(rule(cross()))
        with closing(sqlite3.connect(self.db)) as db,db:
            db.execute('UPDATE candles SET high=5 WHERE utc=?',('2026-11-06T00:00:00',))
        with self.assertRaisesRegex(ValueError,"Invalid"):
            batch.scan_batch([self.db],self.out,f)
        self.assertFalse(self.out.exists())
        self.assertEqual(list(self.root.glob('.formula-batch-*.tmp')),[])

    def test_progress_100_percent_and_no_data(self):
        f=self.load(rule(cross()))
        lines=[]
        batch.scan_batch([self.db],self.out,f,progress=True,report=lines.append)
        self.assertTrue(lines)
        self.assertIn("100.0%",lines[-1])
        self.assertNotIn("2026-11-",lines[-1])

    def test_filters_and_market_validation(self):
        f=self.load(rule(cross()))
        stats=batch.scan_batch([self.db],self.out,f,units=(3,))
        self.assertEqual(stats["pairs"],0)
        self.assertEqual(batch._parse_markets("BTC,ETH"),frozenset({"KRW-BTC","KRW-ETH"}))
        self.assertEqual(batch._parse_units("1,3,240"),(1,3,240))
        for bad in ("BTC,", "BTC;ETH", "1+1"):
            with self.subTest(bad=bad),self.assertRaises(ValueError):batch._parse_markets(bad)

    def test_cli_and_existing_output_fail_closed(self):
        f=self.load(rule(cross()))
        self.assertEqual(batch.main(["--db",str(self.db),"--rules",str(self.rules),
                                     "--output",str(self.out),"--progress"]),0)
        self.assertEqual(len(self.rows()),1)
        self.assertEqual(batch.main(["--db",str(self.db),"--rules",str(self.rules),"--output",str(self.out)]),2)

    def test_no_output_db_overwrite_even_requested(self):
        f=self.load(rule(cross()))
        digest=hashlib.sha256(self.db.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):batch.scan_batch([self.db],self.db,f,overwrite=True)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),digest)

    def test_resource_limits_for_db_and_matches(self):
        f=self.load(rule(cross()))
        with self.assertRaises(ValueError):batch.scan_batch([self.db]*9,self.out,f)
        with self.assertRaises(ValueError):batch.scan_batch([self.db,self.db],self.out,f)
        with self.assertRaises(ValueError):batch.scan_batch([self.db],self.out,f,max_matches=0)

    def test_formula_operand_malformed_is_hold_not_crash(self):
        # Malformed customer JSON must be reported as invalid, not a TypeError.
        for doc in [rule(comparison({"field":"close"},[],{"value":1})),
                    rule(comparison({"field":"close"},">",{"indicator":[],"field":"close","period":2})),
                    rule(comparison({"field":[]},">",{"value":2}))]:
            with self.subTest(doc=doc),self.assertRaises(ValueError):single.compile_formula(doc)


if __name__ == "__main__":
    unittest.main()
