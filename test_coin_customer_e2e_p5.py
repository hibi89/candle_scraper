"""P5 actual canonical P1/P2/P3/P4 customer journey: synthetic SQLite only."""
from __future__ import annotations

from contextlib import closing, redirect_stdout, redirect_stderr
import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import coin_analyzer
import coin_report
import coin_evidence_receipt


class CustomerWorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="coin-p5-e2e-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = self.root / "upbit 한글 #?.sqlite3"
        self.other = self.root / "bithumb_candles.sqlite3"
        self.single = self.root / "rule.json"
        self.batch = self.root / "batch.json"
        self.out = self.root / "signals.csv"
        self.html = self.root / "signals.html"
        self.receipt = self.root / "signals.receipt.json"
        self.table_sql = ("CREATE TABLE candles (market TEXT,unit INT,utc TEXT,kst TEXT,"
                          "open REAL,high REAL,low REAL,close REAL,volume REAL,trade_value REAL,"
                          "PRIMARY KEY(market,unit,utc))")
        for path in [self.db, self.other]:
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute(self.table_sql)
                connection.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)", [
                    ("KRW-BTC", 1, f"2026-11-{i+1:02d}T00:00:00", f"2026-11-{i+1:02d}T09:00:00",
                     close,close+1,close-1,close,100+i,200+i)
                    for i, close in enumerate([10.,10.,10.,10.,10.,14.,15.,16.])])
        self.rules = [
            {"name": "HIGH>LOW", "when": {"left": {"field":"high"}, "op": ">", "right": {"field":"low"}}},
            {"name": "SMA-CROSS", "when": {"cross_up": [
                {"indicator": "sma", "field": "close", "period": 2},
                {"indicator": "sma", "field": "close", "period": 4}]}}
        ]
        self.single.write_text(json.dumps({"version":1, **self.rules[0]}), encoding="utf8")
        self.batch.write_text(json.dumps({"version":1, "rules": self.rules}), encoding="utf8")

    def _sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def runscan(self, flag, source, output, *, dbs=None, args=()):
        argv=[]
        for db in (dbs or [self.db]):
            argv.extend(["--db", str(db)])
        argv.extend([flag, str(source), "--output", str(output), *args])
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return coin_analyzer.main(argv)

    def rows(self, path=None):
        with (path or self.out).open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def test_single_pipeline_csv_html_receipt_and_source_sha(self):
        before = self._sha(self.db)
        self.assertEqual(self.runscan("--rule",self.single,self.out),0)
        self.assertEqual(len(self.rows()),8)
        report=coin_report.render_csv(self.out,self.html)
        self.assertEqual(report["matches"],8)
        receipt=coin_evidence_receipt.build(self.out,self.single)
        self.assertEqual(receipt["matches"],8)
        coin_evidence_receipt.save_new(receipt,self.receipt)
        self.assertTrue(coin_evidence_receipt.verify(self.out,self.single,self.receipt))
        self.assertEqual(self._sha(self.db),before)
        self.assertEqual(self._sha(self.out),receipt["csv_sha256"])
        self.assertFalse(Path(str(self.db)+"-wal").exists())

    def test_batch_pipeline_two_rules_and_two_dbs(self):
        original=(self._sha(self.db),self._sha(self.other))
        self.assertEqual(self.runscan("--rules",self.batch,self.out,dbs=[self.db,self.other]),0)
        rows=self.rows()
        self.assertEqual(len(rows),18)  # (8 high-low + 1 cross) x 2 independent DBs
        self.assertEqual({r['formula'] for r in rows},{'HIGH>LOW','SMA-CROSS'})
        self.assertEqual(coin_report.render_csv(self.out,self.html)['matches'],18)
        rec=coin_evidence_receipt.build(self.out,self.batch)
        self.assertEqual(rec['matches'],18)
        self.assertEqual({f['name']:f['matches'] for f in rec['rules']},{'HIGH>LOW':16,'SMA-CROSS':2})
        coin_evidence_receipt.save_new(rec,self.receipt)
        self.assertTrue(coin_evidence_receipt.verify(self.out,self.batch,self.receipt))
        self.assertEqual((self._sha(self.db),self._sha(self.other)),original)

    def test_latest_N_filters_output_but_keeps_history_for_indicator(self):
        self.assertEqual(self.runscan("--rules",self.batch,self.out,args=['--last','2']),0)
        rows=self.rows()
        self.assertEqual(len(rows),2)
        self.assertEqual({r['formula'] for r in rows},{'HIGH>LOW'})
        self.assertEqual(coin_evidence_receipt.build(self.out,self.batch)['matches'],2)

    def test_missing_or_tampered_rule_prevents_receipt_but_not_originals(self):
        self.assertEqual(self.runscan("--rules",self.batch,self.out),0)
        stable=self._sha(self.out)
        altered={"version":1,"rules":[{"name":"NEW_RULE","when":self.rules[0]['when']}]}
        self.batch.write_text(json.dumps(altered),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Formula identity mismatch'):
            coin_evidence_receipt.build(self.out,self.batch)
        self.assertEqual(self._sha(self.out),stable)
        self.assertFalse(self.receipt.exists())

    def test_output_limit_with_overwrite_preserves_existing_csv_report_receipt(self):
        self.out.write_bytes(b'SOURCE_CUSTOMER_RESULT')
        self.html.write_text('CUSTOMER_REPORT',encoding='utf8')
        self.receipt.write_text('CUSTOMER_RECEIPT',encoding='utf8')
        initial=(self.out.read_bytes(),self.html.read_bytes(),self.receipt.read_bytes())
        self.assertEqual(self.runscan("--rules",self.batch,self.out,args=['--overwrite','--max-matches','3']),2)
        self.assertEqual((self.out.read_bytes(),self.html.read_bytes(),self.receipt.read_bytes()),initial)
        self.assertEqual(list(self.root.glob('.formula-batch-*.tmp')),[])

    def test_protected_report_and_receipt_do_not_erase_good_csv(self):
        self.assertEqual(self.runscan("--rules",self.batch,self.out),0)
        good=self.out.read_bytes()
        coin_report.render_csv(self.out,self.html)
        coin_evidence_receipt.save_new(coin_evidence_receipt.build(self.out,self.batch),self.receipt)
        with self.assertRaises(FileExistsError): coin_report.render_csv(self.out,self.html)
        with self.assertRaises(FileExistsError): coin_evidence_receipt.save_new({},self.receipt)
        self.assertEqual(self.out.read_bytes(),good)
        self.assertTrue(coin_evidence_receipt.verify(self.out,self.batch,self.receipt))

    def test_report_escaped_identifier_and_no_script_execution(self):
        with closing(sqlite3.connect(self.db)) as con,con:
            con.execute("UPDATE candles SET kst='<img src=x onerror=alert(1)>' WHERE utc='2026-11-01T00:00:00'")
        # Canonical P2 rejects invalid timestamp; no unsafe output is published.
        self.assertEqual(self.runscan("--rules",self.batch,self.out),2)
        self.assertFalse(self.out.exists())
        self.assertFalse(self.html.exists())
        self.assertFalse(self.receipt.exists())


if __name__=='__main__': unittest.main()
