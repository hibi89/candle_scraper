"""Verify customer package contents without requiring Windows on CI."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

import make_customer_packages as packaging
import verify_customer_packages as check


class CustomerZIPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dest = Path(self.temp.name)
        self.files = {}
        for edition in packaging.PRODUCTS:
            exe = self.dest / f'CoinCollector_{edition}.exe'
            exe.write_bytes(f'fake EXE for offline package audit {edition}'.encode())
            self.files[edition] = exe
        self.saved_output = packaging.OUTPUT
        packaging.OUTPUT = self.dest
        self.patcher = patch.object(packaging, 'verify_products', return_value=self.files)
        self.patcher.start()
        packaging.main()

    def tearDown(self):
        self.patcher.stop()
        packaging.OUTPUT = self.saved_output
        self.temp.cleanup()

    def test_all_three_customer_zips_are_verified(self):
        self.assertEqual(set(check.check_customer_packages(launch=False)), set(self.files))

    def test_changed_exe_in_one_zip_is_rejected(self):
        archive = self.dest / 'CoinCollector_bithumb_customer.zip'
        with ZipFile(archive, 'w', ZIP_DEFLATED) as zipped:
            zipped.writestr('CoinCollector_bithumb.exe', b'tampered data')
            zipped.writestr('사용설명서.txt', '\ufeff' + packaging.guide('빗썸'))
        with self.assertRaisesRegex(RuntimeError, 'differs'):
            check.check_customer_packages(launch=False)

    def test_unexpected_file_is_rejected(self):
        archive = self.dest / 'CoinCollector_upbit_customer.zip'
        with ZipFile(archive, 'a') as zipped:
            zipped.writestr('unknown.txt', 'not for customers')
        with self.assertRaisesRegex(RuntimeError, 'unexpected'):
            check.check_customer_packages(launch=False)

    def test_missing_zip_is_rejected(self):
        (self.dest / 'CoinCollector_upbit_customer.zip').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Missing customer package'):
            check.check_customer_packages(launch=False)

    def test_windows_guard_prevents_fake_success(self):
        if check.os.name != 'nt':
            with self.assertRaisesRegex(RuntimeError, 'Windows is required'):
                check.check_customer_packages(launch=True)

if __name__ == '__main__': unittest.main()
