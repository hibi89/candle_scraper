# -*- coding: utf-8 -*-
"""Verify the actual shipped ZIPs, not only the pre-packaging executables.

When running on Windows this extracts each edition to an independent temporary
folder and starts the extracted EXE without network or database writes.
"""
import os
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import make_customer_packages as packages


EDITION_TITLES = {
    'upbit': 'Upbit',
    'bithumb': 'Bithumb',
    'both': 'Upbit + Bithumb',
}


def check_customer_packages(launch=False):
    """Reject replaced EXE, extra files, damaged ZIPs and wrong editions."""
    if launch and os.name != 'nt':
        raise RuntimeError('Windows is required for customer EXE execution validation')
    paths = packages.verify_products()
    checked = {}
    for edition, original in paths.items():
        package_path = packages.OUTPUT / f'CoinCollector_{edition}_customer.zip'
        if not package_path.is_file():
            raise RuntimeError(f'Missing customer package: {package_path.name}')
        with ZipFile(package_path) as archive:
            wanted = {original.name, '사용설명서.txt'}
            if set(archive.namelist()) != wanted:
                raise RuntimeError(f'{edition}: unexpected ZIP contents')
            if archive.testzip() is not None:
                raise RuntimeError(f'{edition}: damaged ZIP entry')
            content = archive.read(original.name)
            if sha256(content).hexdigest() != sha256(original.read_bytes()).hexdigest():
                raise RuntimeError(f'{edition}: bundled EXE differs from verified build')
            guide = archive.read('사용설명서.txt').decode('utf-8-sig')
            if not all(x in guide for x in ('캔들 수집기', 'SQLite', 'ZIP')):
                raise RuntimeError(f'{edition}: customer guide is missing or incomplete')
            if launch:
                with tempfile.TemporaryDirectory(prefix='coin_customer_verify_') as folder:
                    archive.extractall(folder)
                    exe = Path(folder) / original.name
                    result = subprocess.run([str(exe)], input='0\n', text=True,
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            encoding='utf-8', errors='replace',
                                            cwd=folder, timeout=80)
                    edition_line = next((line.strip() for line in result.stdout.splitlines()
                                         if line.strip().startswith('Edition:')), '')
                    if (result.returncode != 0 or
                            'COIN CANDLE COLLECTOR' not in result.stdout or
                            edition_line != f'Edition: {EDITION_TITLES[edition]}'):
                        raise RuntimeError(f'{edition}: customer EXE startup failure: '
                                           f'rc={result.returncode}, {result.stdout[-400:]}')
                    if list(Path(folder).glob('*.sqlite3*')):
                        raise RuntimeError(f'{edition}: unexpected database file on clean startup')
        checked[edition] = sha256(package_path.read_bytes()).hexdigest()
        print(f'PASS customer ZIP: {edition} ({"Windows EXE run" if launch else "static verified"})')
    return checked


def main():
    checked = check_customer_packages(launch=True)
    print(f'PASS {len(checked)}/{len(EDITION_TITLES)} independent customer ZIP executions')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'FAIL customer package verification: {exc}', file=sys.stderr)
        sys.exit(1)
