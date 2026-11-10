"""Actual P2 SQLite scan -> CSV -> offline hash receipt -> subsequent verification."""
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

import coin_evidence_receipt as e
import custom_formula_batch as batch
from test_custom_formula_scanner import fixture, comparison


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.db = fixture(self.root / "upbit_candles.sqlite3")
        self.rules = self.root / "rules.json"
        self.csv = self.root / "hits.csv"
        self.receipt = self.root / "receipt.json"
        self.rules.write_text(json.dumps({"version": 1, "rules": [
            {"name": "Above ten", "when": comparison({"field": "close"}, ">", {"value": 10})},
            {"name": "Below twenty", "when": comparison({"field": "close"}, "<", {"value": 20})}
        ]}), encoding="utf-8")
        self.formulas = batch.load_formula_batch(self.rules)
        batch.scan_batch([self.db], self.csv, self.formulas)

    def test_e2e_digest_and_file_preservation(self):
        before_db = hashlib.sha256(self.db.read_bytes()).digest()
        before_csv = hashlib.sha256(self.csv.read_bytes()).digest()
        receipt = e.build(self.csv, self.rules)
        self.assertEqual(receipt["matches"], 11)
        self.assertEqual(receipt["csv_sha256"], hashlib.sha256(self.csv.read_bytes()).hexdigest())
        self.assertEqual([x["matches"] for x in receipt["rules"]], [3, 8])
        e.save_new(receipt, self.receipt)
        self.assertTrue(e.verify(self.csv, self.rules, self.receipt))
        self.assertEqual(before_db, hashlib.sha256(self.db.read_bytes()).digest())
        self.assertEqual(before_csv, hashlib.sha256(self.csv.read_bytes()).digest())

    def test_csv_tamper_blocked(self):
        e.save_new(e.build(self.csv, self.rules), self.receipt)
        content = self.csv.read_text(encoding="utf-8-sig")
        self.csv.write_text(content.replace(",14.0,", ",15.0,"), encoding="utf-8-sig")
        self.assertFalse(e.verify(self.csv, self.rules, self.receipt))

    def test_tamper_formula_digest_rejected(self):
        content = self.csv.read_text(encoding="utf-8-sig")
        self.csv.write_text(content.replace(self.formulas[0].digest, "0" * 64), encoding="utf-8-sig")
        with self.assertRaisesRegex(ValueError, "Formula identity"):
            e.build(self.csv, self.rules)
        self.assertFalse(self.receipt.exists())

    def test_changed_rule_without_new_scan_rejected(self):
        orig = json.loads(self.rules.read_text())
        orig["rules"][0]["when"]["right"]["value"] = 20
        self.rules.write_text(json.dumps(orig))
        with self.assertRaisesRegex(ValueError, "Formula identity"):
            e.build(self.csv, self.rules)

    def test_existing_receipt_never_overwritten(self):
        self.receipt.write_bytes(b"USER_ORIGINAL")
        with self.assertRaises(FileExistsError): e.save_new(e.build(self.csv, self.rules), self.receipt)
        self.assertEqual(self.receipt.read_bytes(), b"USER_ORIGINAL")

    def test_malformed_csv_and_duplicate_columns_denied(self):
        self.csv.write_text("a,a\n1,2\n")
        with self.assertRaisesRegex(ValueError, "columns"):
            e.build(self.csv, self.rules)

    def test_rule_symlink_rejected(self):
        link = self.root / "link.json"
        try: link.symlink_to(self.rules)
        except (OSError, NotImplementedError): self.skipTest("symlink unavailable")
        with self.assertRaisesRegex(ValueError, "Symbolic"):
            e.build(self.csv, link)

    def test_hashing_detects_mid_scan_change(self):
        actual = e._info
        first_csv = actual(self.csv, e.MAX_CSV_BYTES)
        first_rules = actual(self.rules, 65536)
        with patch.object(e, "_info", side_effect=[first_csv, first_rules, (-1,-1,-1,-1), first_rules]):
            with self.assertRaisesRegex(ValueError, "changed while scanning"):
                e.build(self.csv, self.rules)
        self.assertFalse(self.receipt.exists())

    def test_cli_create_then_verify_and_invalid_json(self):
        self.assertEqual(e.main(["--csv", str(self.csv), "--rules", str(self.rules), "--receipt", str(self.receipt)]), 0)
        self.assertEqual(e.main(["--csv", str(self.csv), "--rules", str(self.rules), "--verify", str(self.receipt)]), 0)
        self.receipt.write_text("not json", encoding="utf-8")
        self.assertEqual(e.main(["--csv", str(self.csv), "--rules", str(self.rules), "--verify", str(self.receipt)]), 2)

    def test_no_signals_receipt(self):
        f = batch.load_formula_batch(self.rules)
        self.csv.unlink()
        with self.csv.open("w", encoding="utf-8-sig", newline="") as stream:
            csv.writer(stream).writerow(batch.OUTPUT_COLUMNS)
        r = e.build(self.csv, self.rules)
        self.assertEqual(r["matches"], 0)
        self.assertEqual(len(r["rules"]), 2)


if __name__ == "__main__":
    unittest.main()
