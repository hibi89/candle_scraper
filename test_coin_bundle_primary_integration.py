"""P6 source-authentic P1/P2/P3/P4/P5 ZIP integration on synthetic SQLite.

Unlike the P5 unit shim, this imports the actual canonical coin_report.py.
"""
from __future__ import annotations

from contextlib import closing
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile

import coin_customer_bundle as bundle
import coin_evidence_receipt as evidence


class ActualCustomerBundleIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='coin-p6-full-real-')
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.db=self.root/'upbit 한글 #?.sqlite3'
        self.other=self.root/'bithumb_candles.sqlite3'
        self.rules=self.root/'batch.json'
        self.out=self.root/'deliverable.zip'
        for path in (self.db,self.other):
            with closing(sqlite3.connect(path)) as con,con:
                con.execute('CREATE TABLE candles(market TEXT,unit INTEGER,utc TEXT,kst TEXT,open REAL,high REAL,low REAL,close REAL,volume REAL,trade_value REAL,PRIMARY KEY(market,unit,utc))')
                con.executemany('INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)', [
                    ('KRW-BTC',1,f'2026-11-{i+1:02d}T00:00:00',f'2026-11-{i+1:02d}T09:00:00',
                     10.,11.,9.,10.,100.,1000.) for i in range(8)])
        self.rules.write_text(json.dumps({'version':1,'rules':[
            {'name':'ALWAYS_HIGH','when':{'left':{'field':'high'},'op':'>','right':{'field':'low'}}},
            {'name':'NEVER_200','when':{'left':{'field':'close'},'op':'>','right':{'value':200}}}
        ]}),encoding='utf-8')

    def test_exact_five_files_and_sha_manifest_with_actual_report(self):
        before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        r=bundle.create_bundle([self.db],self.rules,self.out)
        self.assertEqual((r['matches'],r['files']),(8,5))
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),before)
        with zipfile.ZipFile(self.out) as pkg:
            self.assertIsNone(pkg.testzip())
            self.assertEqual(set(pkg.namelist()),set(bundle.ARCHIVE_FILES))
            manifest=json.loads(pkg.read('manifest.json'))
            receipt=json.loads(pkg.read('evidence.json'))
            self.assertEqual(manifest['csv_sha256'],hashlib.sha256(pkg.read('signals.csv')).hexdigest())
            self.assertEqual(manifest['rules_sha256'],hashlib.sha256(pkg.read('rules.json')).hexdigest())
            self.assertEqual(manifest['matches'],receipt['matches'])
            report=pkg.read('report.html').decode('utf8')
            self.assertIn('ALWAYS_HIGH',report)
            self.assertNotIn('<script',report)
            self.assertNotIn(str(self.db),report)
            self.assertFalse(any(name.endswith('.sqlite3') for name in pkg.namelist()))
            with tempfile.TemporaryDirectory() as unpack:
                pkg.extractall(unpack)
                folder=Path(unpack)
                self.assertTrue(evidence.verify(folder/'signals.csv',folder/'rules.json',folder/'evidence.json'))
                with (folder/'signals.csv').open(encoding='utf-8-sig',newline='') as stream:
                    self.assertEqual(len(list(csv.DictReader(stream))),8)

    def test_two_independent_databases_and_rules(self):
        b1=hashlib.sha256(self.db.read_bytes()).hexdigest()
        b2=hashlib.sha256(self.other.read_bytes()).hexdigest()
        self.assertEqual(bundle.create_bundle([self.db,self.other],self.rules,self.out)['matches'],16)
        with zipfile.ZipFile(self.out) as pkg:
            manifest=json.loads(pkg.read('manifest.json'))
            self.assertEqual((manifest['matches'],manifest['pairs'],manifest['formula_count']),(16,2,2))
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),b1)
        self.assertEqual(hashlib.sha256(self.other.read_bytes()).hexdigest(),b2)

    def test_existing_customer_zip_is_unchanged(self):
        self.out.write_bytes(b'CUSTOMER_ORIGINAL_PACKAGE')
        with self.assertRaises(FileExistsError):
            bundle.create_bundle([self.db],self.rules,self.out)
        self.assertEqual(self.out.read_bytes(),b'CUSTOMER_ORIGINAL_PACKAGE')

    def test_invalid_candle_has_no_partial_customer_delivery(self):
        with closing(sqlite3.connect(self.db)) as con,con:
            con.execute("UPDATE candles SET low=NULL WHERE utc='2026-11-08T00:00:00'")
        with self.assertRaises((ValueError,TypeError)):
            bundle.create_bundle([self.db],self.rules,self.out)
        self.assertFalse(self.out.exists())
        self.assertEqual(list(self.root.glob('.coin-customer-*')),[])

    def test_match_cap_does_not_publish_zip_or_leave_staging(self):
        with self.assertRaisesRegex(ValueError,'Match limit'):
            bundle.create_bundle([self.db],self.rules,self.out,max_matches=2)
        self.assertFalse(self.out.exists())
        self.assertEqual(list(self.root.glob('.coin-customer-*')),[])


if __name__=='__main__': unittest.main()
