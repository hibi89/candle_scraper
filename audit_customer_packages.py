# -*- coding: utf-8 -*-
"""Offline, read-only integrity audit of all three *unreleased* customer ZIPs.

This audits package bytes against the exact locally verified EXEs and the
source-generated Korean guide. A PASS is never an API license or sale approval.
"""
import stat
import sys
from hashlib import sha256
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import make_customer_packages as packages

MAX_PACKAGE_BYTES = 512 * 1024 * 1024
MAX_GUIDE_BYTES = 64 * 1024
GUIDE_NAME = '사용설명서.txt'


def audit_one(edition, exe):
    archive_path = packages.OUTPUT / f'CoinCollector_{edition}_customer.zip'
    if not archive_path.is_file() or archive_path.is_symlink():
        raise RuntimeError(f'{edition}: package missing or symlinked')
    if archive_path.stat().st_size > MAX_PACKAGE_BYTES:
        raise RuntimeError(f'{edition}: oversized package')
    raw = archive_path.read_bytes()
    # The builder writes ordinary, comment-free ZIPs: no SFX prefix, trailer,
    # ZIP comments or appended payloads should enter a customer candidate.
    if (len(raw) < 22 or raw[:4] != b'PK\x03\x04' or
            raw[-22:-18] != b'PK\x05\x06' or raw[-2:] != b'\x00\x00'):
        raise RuntimeError(f'{edition}: noncanonical ZIP envelope')
    try:
        with ZipFile(archive_path, 'r') as archive:
            infos = archive.infolist()
            expected = [exe.name, GUIDE_NAME]
            if [info.filename for info in infos] != expected:
                raise RuntimeError(f'{edition}: unexpected/duplicate ZIP members or order')
            if infos[0].header_offset != 0 or archive.comment:
                raise RuntimeError(f'{edition}: prepended content or ZIP comment')
            for info in infos:
                mode = (info.external_attr >> 16) & 0xFFFF
                if (info.flag_bits & 1 or info.is_dir() or stat.S_ISLNK(mode)
                        or info.compress_type != ZIP_DEFLATED):
                    raise RuntimeError(f'{edition}: unsafe ZIP entry')
            if (infos[0].file_size != exe.stat().st_size or
                    infos[1].file_size > MAX_GUIDE_BYTES):
                raise RuntimeError(f'{edition}: incorrect ZIP member size')
            if archive.testzip() is not None:
                raise RuntimeError(f'{edition}: ZIP CRC error')
            if sha256(archive.read(exe.name)).digest() != sha256(exe.read_bytes()).digest():
                raise RuntimeError(f'{edition}: EXE differs from verified build')
            expected_guide = ('\ufeff' + packages.guide(packages.PRODUCTS[edition])).encode('utf-8')
            if archive.read(GUIDE_NAME) != expected_guide:
                raise RuntimeError(f'{edition}: customer guide altered from reviewed source')
    except (BadZipFile, EOFError, OSError, ValueError, RuntimeError) as exc:
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(f'{edition}: invalid ZIP: {exc}') from exc
    return sha256(raw).hexdigest()


def audit_all():
    """Return hash evidence only; do not mutate, repackage or authorize sale."""
    verified = packages.verify_products()  # Windows manifest + local EXE SHA checks
    if set(verified) != set(packages.PRODUCTS):
        raise RuntimeError('verified edition set is incomplete')
    expected_names = {f'CoinCollector_{e}_customer.zip' for e in packages.PRODUCTS}
    found_names = {p.name for p in packages.OUTPUT.glob('CoinCollector_*_customer.zip')}
    if found_names != expected_names:
        raise RuntimeError('customer ZIP edition set is missing or includes extras')
    hashes = {}
    for edition, exe in verified.items():
        hashes[edition] = audit_one(edition, exe)
    return hashes


def main():
    hashes = audit_all()
    for edition, digest in hashes.items():
        print(f'PASS unreleased customer ZIP: {edition} sha256={digest}')
    print('HOLD: technical ZIP audit does not grant exchange API rights or release approval')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'HOLD customer ZIP audit: {exc}', file=sys.stderr)
        sys.exit(1)
