# -*- coding: utf-8 -*-
"""Run the built EXEs with '0' to verify console startup and clean exit.

No exchange network access and no database writes are requested by this test.
"""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
EDITIONS = {'upbit': ('Upbit', 'Bithumb'),
            'bithumb': ('Bithumb', 'Upbit'),
            'both': ('Upbit + Bithumb', None)}


def main():
    if os.name != 'nt':
        raise RuntimeError('Windows runtime is required for EXE execution validation')
    verified = {}
    for edition, (expected, forbidden) in EDITIONS.items():
        exe = DIST / f'CoinCollector_{edition}.exe'
        if not exe.is_file():
            raise RuntimeError(f'Missing built executable: {exe}')
        before = {p.name for p in DIST.glob('*_candles.sqlite3*')}
        res = subprocess.run([str(exe)], input='0\n', text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             encoding='utf-8', errors='replace', cwd=DIST, timeout=60)
        if res.returncode != 0 or 'COIN CANDLE COLLECTOR' not in res.stdout or expected not in res.stdout:
            raise RuntimeError(f'{edition}: EXE smoke FAIL rc={res.returncode}: {res.stdout[-500:]}')
        edition_line = next((x.strip() for x in res.stdout.splitlines() if x.strip().startswith('Edition:')), '')
        if forbidden and forbidden in edition_line:
            raise RuntimeError(f'{edition}: incorrect edition menu: {edition_line}')
        after = {p.name for p in DIST.glob('*_candles.sqlite3*')}
        if after != before:
            raise RuntimeError(f'{edition}: EXE startup unexpectedly created DB: {after-before}')
        verified[edition] = {'filename': exe.name, 'sha256': sha256(exe.read_bytes()).hexdigest(),
                             'size': exe.stat().st_size}
        print(f'PASS Windows executable startup: {exe.name} | {edition_line}')
    manifest = {'schema_version': 1, 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
                'platform': 'Windows', 'products': verified}
    destination = DIST / 'exe_verification.json'
    temporary = destination.with_suffix('.partial')
    try:
        temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        temporary.replace(destination)
    finally:
        if temporary.exists(): temporary.unlink()
    print('PASS 3/3 Windows executable startup checks; wrote EXE hash manifest')


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
