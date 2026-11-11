# -*- coding: utf-8 -*-
"""Offline synthetic ZIP tests. Uses installed P3 coin_report; local shim may be used."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from contextlib import closing
from unittest.mock import patch

import coin_customer_bundle as bundle
from test_custom_formula_scanner import fixture, comparison


class CustomerBundleTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="coin-customer-bundle-test-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.db = fixture(self.root / "upbit_candles.sqlite3")
        self.rules = self.root / "rule.json"
        self.out = self.root / "customer.zip"
        self.rules.write_text(json.dumps({"version":1,"rules":[
            {"name":"Above 10", "when": comparison({"field":"close"}, ">", {"value":10})},
            {"name":"Below 20", "when": comparison({"field":"close"}, "<", {"value":20})},
        ]}), encoding="utf-8")

    def make(self, **kwargs):
        return bundle.create_bundle([self.db], self.rules, self.out, **kwargs)

    def test_real_sql_to_zip_five_members_and_unmodified_db_rules(self):
        db_sha, rule_sha = (hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.db,self.rules))
        result = self.make()
        self.assertEqual((result["matches"],result["files"]),(11,5))
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), db_sha)
        self.assertEqual(hashlib.sha256(self.rules.read_bytes()).hexdigest(), rule_sha)
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual(z.testzip(), None)
            self.assertEqual(set(z.namelist()), set(bundle.ARCHIVE_FILES))
            self.assertNotIn("<script",z.read("report.html").decode("utf-8"))
            receipt=json.loads(z.read("evidence.json"))
            manifest=json.loads(z.read("manifest.json"))
            self.assertEqual(manifest["csv_sha256"],receipt["csv_sha256"])
            self.assertEqual(manifest["matches"],11)
            self.assertEqual(receipt["rules_sha256"],hashlib.sha256(z.read("rules.json")).hexdigest())
            with tempfile.TemporaryDirectory() as d:
                z.extractall(d)
                import coin_evidence_receipt as evidence
                self.assertTrue(evidence.verify(Path(d)/"signals.csv",Path(d)/"rules.json",Path(d)/"evidence.json"))

    def test_no_overwrite_of_original_package(self):
        self.out.write_bytes(b"CUSTOMER_ORIGINAL")
        with self.assertRaises(FileExistsError):self.make()
        self.assertEqual(self.out.read_bytes(),b"CUSTOMER_ORIGINAL")

    def test_midscan_invalid_ohlc_rolls_back_package_and_temp(self):
        with closing(sqlite3.connect(self.db)) as db,db:
            db.execute("UPDATE candles SET high=NULL WHERE utc='2026-11-04T00:00:00'")
        with self.assertRaises(ValueError):self.make()
        self.assertFalse(self.out.exists())
        self.assertFalse(list(self.root.glob(".coin-customer-*")))

    def test_invalid_formula_does_not_publish(self):
        self.rules.write_text("{not JSON",encoding="utf-8")
        with self.assertRaises((ValueError, json.JSONDecodeError)):self.make()
        self.assertFalse(self.out.exists())

    def test_missing_report_dependency_rolls_back(self):
        with patch.dict(sys.modules,{"coin_report":None}):
            with self.assertRaises(ModuleNotFoundError):self.make()
        self.assertFalse(self.out.exists())
        self.assertFalse(list(self.root.glob(".coin-customer-*")))

    def test_failed_report_render_does_not_publish(self):
        import coin_report
        with patch.object(coin_report,"render_csv",side_effect=ValueError("bad HTML")):
            with self.assertRaisesRegex(ValueError,"bad HTML"):self.make()
        self.assertFalse(self.out.exists())

    def test_failed_receipt_verify_does_not_publish(self):
        with patch.object(bundle,"verify_evidence",return_value=False):
            with self.assertRaisesRegex(ValueError,"Receipt failed"):self.make()
        self.assertFalse(self.out.exists())

    def test_mismatched_report_count_does_not_publish(self):
        import coin_report
        with patch.object(coin_report,"render_csv",return_value={"matches":0}):
            with self.assertRaisesRegex(ValueError,"disagree"):self.make()
        self.assertFalse(self.out.exists())

    def test_no_matches_is_valid_bundle(self):
        self.rules.write_text(json.dumps({"version":1,"name":"No hits","when":
            comparison({"field":"close"}, ">", {"value":1e9})}),encoding="utf-8")
        self.assertEqual(self.make()["matches"],0)
        with zipfile.ZipFile(self.out) as z:
            with z.open("signals.csv") as stream:
                lines=stream.read().decode("utf-8-sig").splitlines()
            self.assertEqual(len(lines),1)

    def test_match_limit_holds_without_partial_zip(self):
        with self.assertRaisesRegex(ValueError,"Match limit"):
            self.make(max_matches=3)
        self.assertFalse(self.out.exists())

    def test_symlink_rule_input_denied(self):
        alias=self.root/"alias.json"
        try:alias.symlink_to(self.rules)
        except (OSError,NotImplementedError):self.skipTest("symlink unsupported")
        with self.assertRaisesRegex(ValueError,"Symlink"):
            bundle.create_bundle([self.db],alias,self.out)
        self.assertFalse(self.out.exists())

    def test_duplicate_db_and_invalid_last_denied(self):
        with self.assertRaisesRegex(ValueError,"Duplicate source"):
            bundle.create_bundle([self.db,self.db],self.rules,self.out)
        with self.assertRaisesRegex(ValueError,"last-N"):
            self.make(last=-1)
        self.assertFalse(self.out.exists())

    def test_interactive_no_network_and_no_sqlite_in_zip(self):
        self.make(markets="BTC",units="1",last=3)
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual(len(z.namelist()),5)
            self.assertTrue(all(not x.endswith(".sqlite3") for x in z.namelist()))
            self.assertNotIn(str(self.db).encode(),z.read("manifest.json"))
            self.assertNotIn("https://",z.read("report.html").decode("utf-8").lower())
            self.assertNotIn("http://",z.read("report.html").decode("utf-8").lower())

    def test_cli_end_to_end(self):
        self.assertEqual(bundle.main(["--db",str(self.db),"--rules",str(self.rules),"--output",str(self.out)]),0)
        self.assertTrue(self.out.exists())


if __name__ == "__main__":unittest.main()
