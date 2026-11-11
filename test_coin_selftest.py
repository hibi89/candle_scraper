"""Executable synthetic P1/P2/P3/P4 product self-test, no customer data."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import unittest
from unittest.mock import patch

import coin_selftest


class InstallSelftestTests(unittest.TestCase):
    def test_real_all_components_in_synthetic_session(self):
        result=coin_selftest.run_selftest()
        self.assertEqual(result['status'],'PASS_SYNTHETIC_ONLY')
        self.assertEqual(result['verified_modes'],2)
        self.assertEqual(result['receipts_verified'],2)
        self.assertEqual(result['verified_matches_per_mode'],8)
        self.assertTrue(result['source_db_unchanged'])
        self.assertFalse(result['ready_for_customer_data'])

    def test_cli_prints_machine_readable_success(self):
        with redirect_stdout(StringIO()) as out:
            self.assertEqual(coin_selftest.main(),0)
        self.assertEqual(json.loads(out.getvalue())['status'],'PASS_SYNTHETIC_ONLY')

    def test_receipt_verification_failure_fails_closed(self):
        with patch.object(coin_selftest.coin_evidence_receipt,'verify',return_value=False):
            with redirect_stdout(StringIO()) as out:
                self.assertEqual(coin_selftest.main(),2)
            self.assertEqual(json.loads(out.getvalue())['status'],'FAIL_CLOSED')

    def test_csv_report_mismatch_fails_closed(self):
        with patch.object(coin_selftest.coin_report,'render_csv',return_value={'matches':7}):
            with redirect_stdout(StringIO()) as out:
                self.assertEqual(coin_selftest.main(),2)
            self.assertEqual(json.loads(out.getvalue())['status'],'FAIL_CLOSED')


if __name__=='__main__': unittest.main()
