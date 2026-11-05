# -*- coding: utf-8 -*-
"""Launch each actual customer EXE for bounded, read-only API menu checks.

Run only after Windows build and customer ZIP integrity checks pass. Never
starts collection or touches an existing SQLite database.
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
CUSTOMER = ROOT / 'customer_packages'
REPORT = ROOT / 'live_exe_evidence.json'
EDT = {
    'upbit': ('Upbit', '5\n\n0\n', ('upbit',)),
    'bithumb': ('Bithumb', '5\n\n0\n', ('bithumb',)),
    'both': ('Upbit + Bithumb', '5\n3\n\n0\n', ('upbit', 'bithumb')),
}


def check(edition, title, stdin, exchanges):
    zipped = CUSTOMER / f'CoinCollector_{edition}_customer.zip'
    if not zipped.is_file():
        raise RuntimeError(f'missing built customer package: {zipped.name}')
    with tempfile.TemporaryDirectory(prefix='coin_live_exe_') as root:
        root = Path(root)
        with ZipFile(zipped) as archive:
            if archive.testzip() is not None:
                raise RuntimeError(f'{edition}: damaged customer ZIP')
            archive.extractall(root)
        exe = root / f'CoinCollector_{edition}.exe'
        if not exe.is_file():
            raise RuntimeError(f'{edition}: missing executable after extract')
        outcome = subprocess.run([str(exe)], input=stdin, encoding='utf-8',
                                 errors='replace', stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, cwd=root, timeout=240)
        edition_line = f'Edition: {title}'
        if outcome.returncode != 0 or edition_line not in outcome.stdout:
            raise RuntimeError(f'{edition}: unexpected exit or wrong edition: {outcome.stdout[-400:]}')
        checked = {}
        for exchange in exchanges:
            token = f'PASS {exchange} KRW-BTC '
            count = sum(line.startswith(token) for line in outcome.stdout.splitlines())
            if count != 11:
                raise RuntimeError(f'{edition}: {exchange} expected 11 live candle unit checks, got {count}; {outcome.stdout[-400:]}')
            checked[exchange] = count
        if list(root.glob('*.sqlite3*')):
            raise RuntimeError(f'{edition}: read-only API menu created a customer DB')
        return checked


def main():
    if os.name != 'nt':
        raise RuntimeError('Windows EXE verification requires Windows')
    evidence = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                'git_sha': os.environ.get('GITHUB_SHA', 'local'),
                'scope': 'read-only menu [5] in 3 independent actual customer EXEs',
                'editions': {}}
    failed = False
    for edition, (title, stdin, exchanges) in EDT.items():
        try:
            evidence['editions'][edition] = {'status': 'PASS', 'timeframes_by_exchange': check(edition, title, stdin, exchanges)}
            print(f'PASS live customer EXE {edition}: {exchanges}')
        except Exception as exc:
            evidence['editions'][edition] = {'status': 'FAIL', 'error_type': type(exc).__name__,
                                             'error': str(exc)[:300]}
            print(f'FAIL live customer EXE {edition}: {type(exc).__name__}: {str(exc)[:200]}', file=sys.stderr)
            failed = True
    REPORT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
