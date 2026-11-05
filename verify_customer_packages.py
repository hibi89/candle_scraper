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


def check_unicode_and_space_paths():
    """Run actual customer EXEs from a Hangul/space directory, without API calls.

    Windows runner is not a customer Windows 10/11 device; this checks
    UTF-8 menu handling and PyInstaller path resolution only.
    """
    if os.name != 'nt':
        raise RuntimeError('Windows is required for Unicode EXE verification')
    paths = packages.verify_products()
    for edition, original in paths.items():
        zip_path = packages.OUTPUT / f'CoinCollector_{edition}_customer.zip'
        with tempfile.TemporaryDirectory(prefix='캔들 수집기 한글 경로_') as folder:
            with ZipFile(zip_path) as archive:
                if set(archive.namelist()) != {original.name, '사용설명서.txt'}:
                    raise RuntimeError(f'{edition}: unverified customer package')
                archive.extractall(folder)
            exe = Path(folder) / original.name
            # Menu [6] queries only local DB existence; no exchange API calls.
            # The both edition prompts for its exchanges and checks both.
            menu_input = '6\n3\n\n0\n' if edition == 'both' else '6\n\n0\n'
            result = subprocess.run([str(exe)], input=menu_input, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    encoding='utf-8', errors='replace',
                                    cwd=folder, timeout=80)
            expected_db_messages = 2 if edition == 'both' else 1
            if (result.returncode != 0 or
                    f'Edition: {EDITION_TITLES[edition]}' not in result.stdout or
                    result.stdout.count('아직 DB가 없습니다:') != expected_db_messages or
                    '오류 ' in result.stdout):
                raise RuntimeError(f'{edition}: Unicode-path menu [6] check failed: '
                                   f'rc={result.returncode}, {result.stdout[-500:]}')
            if any(Path(folder).glob('*.sqlite3*')):
                raise RuntimeError(f'{edition}: read-only menu created database')
            print(f'PASS Unicode/space customer EXE: {edition} '
                  f'({expected_db_messages} missing-DB checks, no database writes)')


def main():
    checked = check_customer_packages(launch=True)
    print(f'PASS {len(checked)}/{len(EDITION_TITLES)} independent customer ZIP executions')
    check_unicode_and_space_paths()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'FAIL customer package verification: {exc}', file=sys.stderr)
        sys.exit(1)
