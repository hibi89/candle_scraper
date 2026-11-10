# -*- coding: utf-8 -*-
"""Complete-feature E2E: P1/P2 actual scanner + customer CLI + static offline report.

Runs only in the full feature/candle-pattern-analyzer checkout (no customer data).
"""
from __future__ import annotations

from contextlib import closing, redirect_stdout, redirect_stderr
from io import StringIO
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import coin_analyzer
import coin_report


class CanonicalIntegrationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="coin-p3-canonical-")
        self.addCleanup(tmp.cleanup)
        self.folder=Path(tmp.name)
        self.db=self.folder/"upbit_candles.sqlite3"
        self.single=self.folder/"single.json"
        self.batch=self.folder/"batch.json"
        self.single_csv=self.folder/"single.csv"
        self.batch_csv=self.folder/"batch.csv"
        self.report=self.folder/"summary.html"
        with closing(sqlite3.connect(self.db)) as con,con:
            con.execute("""CREATE TABLE candles(market TEXT,unit INT,utc TEXT,kst TEXT,
                  open REAL,high REAL,low REAL,close REAL,volume REAL,trade_value REAL,
                  PRIMARY KEY(market,unit,utc))""")
            con.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?,?,?,?)",[
                ("KRW-BTC",1,f"2026-11-{i+1:02d}T00:00:00",
                 f"2026-11-{i+1:02d}T09:00:00",10.,11.,9.,10.,100.,1000.)
                for i in range(8)])
        self.rule={"name":"High above low","when":{
            "left":{"field":"high"},"op":">","right":{"field":"low"}}}
        self.single.write_text(json.dumps({"version":1,**self.rule}),encoding="utf-8")
        self.batch.write_text(json.dumps({"version":1,"rules":[self.rule]}),encoding="utf-8")

    def runscan(self,path,flag,out,additional=()):
        with redirect_stdout(StringIO()),redirect_stderr(StringIO()):
            return coin_analyzer.main(["--db",str(self.db),flag,str(path),
                                       "--output",str(out),*additional])

    def test_actual_single_and_batch_byte_parity(self):
        before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.assertEqual(self.runscan(self.single,"--rule",self.single_csv),0)
        self.assertEqual(self.runscan(self.batch,"--rules",self.batch_csv),0)
        self.assertEqual(self.single_csv.read_bytes(),self.batch_csv.read_bytes())
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),before)
        with self.batch_csv.open(encoding="utf-8-sig",newline="") as f:
            self.assertEqual(len(list(csv.DictReader(f))),8)

    def test_actual_batch_csv_to_static_html_e2e(self):
        before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.assertEqual(self.runscan(self.batch,"--rules",self.batch_csv),0)
        result=coin_report.render_csv(self.batch_csv,self.report)
        self.assertEqual(result["matches"],8)
        self.assertEqual(result["mode"],"single") # P2 shares P1 CSV columns
        text=self.report.read_text(encoding="utf-8")
        self.assertIn("High above low",text)
        self.assertNotIn("<script",text)
        self.assertEqual(before,hashlib.sha256(self.db.read_bytes()).hexdigest())

    def test_actual_single_and_batch_rule_only_validation(self):
        for argument,file in [("--rule",self.single),("--rules",self.batch)]:
            with self.subTest(argument=argument),redirect_stdout(StringIO()) as output:
                self.assertEqual(coin_analyzer.main([argument,str(file),"--validate-only"]),0)
                self.assertEqual(json.loads(output.getvalue())["rule_count"],1)
        self.assertEqual(list(self.folder.glob("*.csv")),[])

    def test_actual_batch_match_limit_preserves_existing_csv(self):
        self.batch_csv.write_bytes(b"KEEP_EXISTING")
        self.assertEqual(self.runscan(self.batch,"--rules",self.batch_csv,
                                     ("--overwrite","--max-matches","2")),2)
        self.assertEqual(self.batch_csv.read_bytes(),b"KEEP_EXISTING")

if __name__=="__main__":
    unittest.main()
