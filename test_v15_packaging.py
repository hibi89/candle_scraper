"""Offline customer package tests. Fake EXE bytes are test-only and never shipped."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import make_customer_packages as packages


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dist = Path(self.tmp.name)/'dist'
        self.output = Path(self.tmp.name)/'output'
        self.dist.mkdir()
        self.old_dist, self.old_out = packages.DIST, packages.OUTPUT
        packages.DIST, packages.OUTPUT = self.dist, self.output

    def tearDown(self):
        packages.DIST, packages.OUTPUT = self.old_dist, self.old_out
        self.tmp.cleanup()

    def create_stubs(self, platform='Windows'):
        manifest = {'platform': platform, 'schema_version': 1, 'products': {}}
        for edition in packages.PRODUCTS:
            exe = self.dist / f'CoinCollector_{edition}.exe'
            exe.write_bytes((f'FAKE-TEST-EXE-{edition}').encode())
            manifest['products'][edition] = {
                'filename': exe.name, 'size': exe.stat().st_size,
                'sha256': hashlib.sha256(exe.read_bytes()).hexdigest()}
        (self.dist / 'exe_verification.json').write_text(json.dumps(manifest), encoding='utf-8')

    def test_refuses_exe_without_verified_manifest(self):
        with self.assertRaisesRegex(RuntimeError, 'No verified Windows EXE'):
            packages.main()
        self.assertFalse(self.output.exists())

    def test_refuses_changed_exe_after_verification(self):
        self.create_stubs()
        with (self.dist/'CoinCollector_bithumb.exe').open('ab') as out:
            out.write(b'CHANGED')
        with self.assertRaisesRegex(RuntimeError, 'changed since verification'):
            packages.main()
        self.assertFalse(self.output.exists())

    def test_refuses_foreign_platform_manifest(self):
        self.create_stubs('Linux')
        with self.assertRaisesRegex(RuntimeError, 'Invalid Windows'):
            packages.main()

    def test_refuses_incomplete_manifest(self):
        self.create_stubs()
        path = self.dist/'exe_verification.json'
        manifest = json.loads(path.read_text())
        manifest['products'].pop('bithumb')
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            packages.main()

    def test_validated_stubs_produce_three_isolated_zips(self):
        self.create_stubs()
        packages.main()
        self.assertEqual(len(list(self.output.glob('*.zip'))), 3)
        for edition in packages.PRODUCTS:
            path = self.output/f'CoinCollector_{edition}_customer.zip'
            with ZipFile(path) as z:
                self.assertEqual(sorted(z.namelist()), sorted([f'CoinCollector_{edition}.exe', '사용설명서.txt']))
                self.assertIn('SQLite', z.read('사용설명서.txt').decode('utf-8-sig'))
                self.assertTrue(z.read(f'CoinCollector_{edition}.exe').startswith(b'FAKE-TEST-EXE'))


if __name__ == '__main__': unittest.main()
