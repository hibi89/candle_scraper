"""Synthetic-only sale-HOLD delivery integrity regression; never calls exchange APIs."""
import json
import tempfile
import unittest
import warnings
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import audit_customer_packages as audit
import make_customer_packages as packages


class RetailPackageAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.dist, self.output = base / 'dist', base / 'customer_packages'
        self.dist.mkdir()
        self.output.mkdir()
        self.patch_dist = patch.object(packages, 'DIST', self.dist)
        self.patch_output = patch.object(packages, 'OUTPUT', self.output)
        self.patch_dist.start()
        self.patch_output.start()
        self.addCleanup(self.patch_dist.stop)
        self.addCleanup(self.patch_output.stop)
        manifest = {'schema_version': 1, 'platform': 'Windows', 'products': {}}
        for edition in packages.PRODUCTS:
            exe = self.dist / f'CoinCollector_{edition}.exe'
            exe.write_bytes(b'MZ\x00synthetic_' + edition.encode('ascii'))
            manifest['products'][edition] = {
                'filename': exe.name, 'size': exe.stat().st_size,
                'sha256': sha256(exe.read_bytes()).hexdigest()}
        (self.dist / 'exe_verification.json').write_text(json.dumps(manifest), encoding='utf-8')
        packages.main()

    def path(self, edition='upbit'):
        return self.output / f'CoinCollector_{edition}_customer.zip'

    def rewrite(self, replacement, edition='upbit'):
        archive_path = self.path(edition)
        with ZipFile(archive_path) as z:
            original = [(i.filename, z.read(i.filename)) for i in z.infolist()]
        with ZipFile(archive_path, 'w', ZIP_DEFLATED) as z:
            for name, data in original:
                z.writestr(name, replacement.get(name, data))

    def test_all_three_exact_original_packages_pass(self):
        result = audit.audit_all()
        self.assertEqual(set(result), set(packages.PRODUCTS))
        for edition, digest in result.items():
            self.assertEqual(digest, sha256(self.path(edition).read_bytes()).hexdigest())

    def test_altered_guide_keeps_old_keywords_but_fails_exact_comparison(self):
        self.rewrite({'사용설명서.txt': b'\xef\xbb\xbf' + '캔들 수집기 SQLite ZIP / MODIFIED'.encode()})
        with self.assertRaisesRegex(RuntimeError, 'guide altered'):
            audit.audit_all()

    def test_replaced_executable_inside_zip_fails(self):
        self.rewrite({'CoinCollector_upbit.exe': b'MZaltered'})
        with self.assertRaisesRegex(RuntimeError, 'EXE differs|member size'):
            audit.audit_all()

    def test_duplicate_member_fails(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with ZipFile(self.path(), 'a') as z:
                z.writestr('사용설명서.txt', b'bad')
        with self.assertRaisesRegex(RuntimeError, 'duplicate'):
            audit.audit_all()

    def test_extra_market_data_entry_fails(self):
        with ZipFile(self.path(), 'a') as z:
            z.writestr('market_data.csv', 'private')
        with self.assertRaisesRegex(RuntimeError, 'unexpected'):
            audit.audit_all()

    def test_hidden_prefix_and_trailer_fail(self):
        original = self.path().read_bytes()
        for corrupted in (b'junk' + original, original + b'junk'):
            with self.subTest(kind='prefix' if corrupted.startswith(b'junk') else 'trailer'):
                self.path().write_bytes(corrupted)
                with self.assertRaisesRegex(RuntimeError, 'noncanonical'):
                    audit.audit_all()
        self.path().write_bytes(original)

    def test_comment_fails(self):
        with ZipFile(self.path(), 'a') as z:
            z.comment = b'hidden'
        with self.assertRaisesRegex(RuntimeError, 'noncanonical'):
            audit.audit_all()

    def test_symlinked_zip_member_fails(self):
        path = self.path()
        with ZipFile(path) as z:
            exe = (z.infolist()[0].filename, z.read(z.infolist()[0].filename))
            guide = z.read('사용설명서.txt')
        link = ZipInfo(exe[0])
        link.create_system = 3
        link.external_attr = (0o120777 << 16)
        link.compress_type = ZIP_DEFLATED
        with ZipFile(path, 'w') as z:
            z.writestr(link, exe[1])
            z.writestr('사용설명서.txt', guide, compress_type=ZIP_DEFLATED)
        with self.assertRaisesRegex(RuntimeError, 'unsafe'):
            audit.audit_all()

    def test_missing_and_extra_edition_fails(self):
        original = self.path('both').read_bytes()
        self.path('both').unlink()
        with self.assertRaisesRegex(RuntimeError, 'edition set'):
            audit.audit_all()
        self.path('both').write_bytes(original)
        (self.output / 'CoinCollector_old_customer.zip').write_bytes(original)
        with self.assertRaisesRegex(RuntimeError, 'edition set'):
            audit.audit_all()

    def test_changed_original_exe_rejected_by_manifest(self):
        (self.dist / 'CoinCollector_upbit.exe').write_bytes(b'MZtampered')
        with self.assertRaisesRegex(RuntimeError, 'changed since verification'):
            audit.audit_all()


if __name__ == '__main__':
    unittest.main()
