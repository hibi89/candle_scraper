"""Static customer report regression: real batch CSV, legacy single contract, XSS and rollback."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import coin_report as report


class OfflineReportTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="coin-report-tests-")
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.csv=self.root/"hits.csv"
        self.html=self.root/"report.html"

    def make_batch(self):
        with self.csv.open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(report.BATCH)
            for i in range(5):
                for rule_id in ("BUY_DEMO","SELL_DEMO"):
                    writer.writerow(["upbit","KRW-BTC",1,f"2026-11-{i+1:02d}",
                                     f"2026-11-{i+1:02d}",10.,rule_id])

    def test_synthetic_batch_csv_to_report_and_source_hash_unchanged(self):
        self.make_batch()
        orig=hashlib.sha256(self.csv.read_bytes()).hexdigest()
        summary=report.render_csv(self.csv,self.html)
        self.assertEqual(summary["matches"],10)
        self.assertEqual(summary["rule_count"],2)
        self.assertEqual(summary["market_count"],1)
        self.assertEqual(summary["mode"],"batch")
        self.assertEqual(hashlib.sha256(self.csv.read_bytes()).hexdigest(),orig)
        html=self.html.read_text(encoding="utf-8")
        self.assertIn("BUY_DEMO",html)
        self.assertIn("SELL_DEMO",html)
        self.assertIn("KRW-BTC",html)
        self.assertNotIn("<script",html.lower())
        self.assertIn("default-src 'none'",html)

    def test_existing_report_protected_on_success_without_flag(self):
        self.make_batch()
        self.html.write_bytes(b"EXISTING_REPORT")
        with self.assertRaises(FileExistsError):
            report.render_csv(self.csv,self.html)
        self.assertEqual(self.html.read_bytes(),b"EXISTING_REPORT")

    def test_existing_report_preserved_on_bad_input_with_overwrite(self):
        self.csv.write_text("WRONG,HEADERS\na,b",encoding="utf-8")
        self.html.write_bytes(b"KEEP_EXISTING")
        with self.assertRaisesRegex(ValueError,"header"):
            report.render_csv(self.csv,self.html,overwrite=True)
        self.assertEqual(self.html.read_bytes(),b"KEEP_EXISTING")
        self.assertEqual(list(self.root.glob(".coin-report-*.tmp")),[])

    def test_legacy_single_csv_supported(self):
        with self.csv.open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(report.SINGLE)
            writer.writerow(["upbit","KRW-ETH","240","2026-01-01","2026-01-01","100",
                             "My SMA Cross","deadbeef"])
        result=report.render_csv(self.csv,self.html)
        self.assertEqual(result["mode"],"single")
        self.assertEqual((result["matches"],result["rule_count"]),(1,1))
        self.assertIn("My SMA Cross",self.html.read_text(encoding="utf-8"))

    def test_xss_identifier_escaped_and_no_outbound_url(self):
        with self.csv.open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(report.BATCH)
            writer.writerow(["local", "KRW-BTC", "1", "2026-01-01","2026-01-01",10,
                             '<img src=x onerror=alert(1)>'])
        report.render_csv(self.csv,self.html)
        html=self.html.read_text(encoding="utf-8")
        self.assertNotIn('<img src=x onerror=alert(1)>',html)
        self.assertIn('&lt;img',html)
        self.assertNotIn('http://',html)
        self.assertNotIn('https://',html)

    def test_row_limit_does_not_publish(self):
        self.make_batch()
        with patch.object(report,"MAX_RECORDS",9),self.assertRaisesRegex(ValueError,"row count"):
            report.render_csv(self.csv,self.html)
        self.assertFalse(self.html.exists())

    def test_csv_input_file_size_limit(self):
        self.make_batch()
        with patch.object(report,"MAX_INPUT_BYTES",10),self.assertRaisesRegex(ValueError,"bounded"):
            report.render_csv(self.csv,self.html)
        self.assertFalse(self.html.exists())

    def test_invalid_close_rejects_and_existing_output_kept(self):
        with self.csv.open("w",encoding="utf-8",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(report.BATCH)
            writer.writerow(["local","KRW-BTC","1","t1","k1","nan","SMA"])
        self.html.write_bytes(b"KEEP")
        with self.assertRaisesRegex(ValueError,"invalid close"):
            report.render_csv(self.csv,self.html,overwrite=True)
        self.assertEqual(self.html.read_bytes(),b"KEEP")

    def test_symlink_input_denied(self):
        self.make_batch()
        link=self.root/"link.csv"
        try: link.symlink_to(self.csv)
        except (OSError,NotImplementedError): self.skipTest("symlink unavailable")
        with self.assertRaisesRegex(ValueError,"Symlink"):
            report.render_csv(link,self.html)

    def test_empty_header_only_report(self):
        with self.csv.open("w",encoding="utf-8-sig",newline="") as f:
            csv.writer(f).writerow(report.BATCH)
        x=report.render_csv(self.csv,self.html)
        self.assertEqual(x["matches"],0)
        self.assertIn("No matches",self.html.read_text(encoding="utf-8"))
        self.assertEqual(x["preview_count"],0)

    def test_bounded_preview_not_entire_input(self):
        self.make_batch()
        with patch.object(report,"PREVIEW_ROWS",2):
            x=report.render_csv(self.csv,self.html)
        self.assertEqual(x["preview_count"],2)
        self.assertFalse(x["contains_all_rows"])

    def test_report_input_and_output_must_differ(self):
        self.make_batch()
        with self.assertRaisesRegex(ValueError,"replace source"):
            report.render_csv(self.csv,self.csv,overwrite=True)

    def test_cli_report_end_to_end(self):
        self.make_batch()
        self.assertEqual(report.main(["--csv",str(self.csv),"--output",str(self.html)]),0)
        self.assertTrue(self.html.is_file())


if __name__=="__main__":
    unittest.main()
