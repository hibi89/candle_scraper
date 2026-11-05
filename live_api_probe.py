# -*- coding: utf-8 -*-
"""Bounded live public-API verification on a disposable Windows runner.

No auth, trading, mass harvesting or customer DB access. Only KRW-BTC
11-timeframe two-page checks, then 11 closed daily candles per exchange.
"""
import json
from contextlib import closing
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import collector

EVIDENCE = Path(__file__).resolve().parent / 'live_api_evidence.json'


def check_exchange(exchange, temp_root):
    base_url, original_db = collector.CONFIG[exchange]
    trial_db = Path(temp_root) / (exchange + '_test_only.sqlite3')
    collector.CONFIG[exchange] = (base_url, trial_db)
    try:
        market_count = collector.smoke_check(exchange)
        n, inserted, status = collector.collect_pair(exchange, 'KRW-BTC', 'day', 'initial')
        if not 1 <= n <= 11 or not 1 <= inserted <= 11 or status != 'ok':
            raise RuntimeError(f'invalid bounded initial collection: n={n}, added={inserted}, state={status}')
        n_updated, _, update_status = collector.collect_pair(exchange, 'KRW-BTC', 'day', 'update')
        if n_updated < n or update_status != 'ok':
            raise RuntimeError('incremental update lost candles or failed')
        # sqlite3.Connection.__exit__ commits but does NOT close the file on Windows.
        # closing() releases SQLite/WAL handles before the temp directory is removed.
        with closing(sqlite3.connect(trial_db)) as db:
            actual = db.execute('SELECT COUNT(*) FROM candles WHERE market=? AND unit=?', ('KRW-BTC', 'day')).fetchone()[0]
            distinct = db.execute('SELECT COUNT(*) FROM (SELECT market,unit,utc FROM candles GROUP BY market,unit,utc)').fetchone()[0]
        if actual != n_updated or actual != distinct:
            raise RuntimeError('real collection DB duplicate/count mismatch')
        count, folder = collector.export_csv(exchange, Path(temp_root) / 'csv' / exchange)
        csv_path = folder / 'KRW-BTC_day.csv'
        if count != 1 or not csv_path.is_file() or csv_path.read_bytes()[:3] != b'\xef\xbb\xbf':
            raise RuntimeError('CSV export or UTF-8 BOM mismatch')
        return {'status': 'PASS', 'krw_market_count': market_count,
                'timeframes_checked': len(collector.UNITS), 'historical_pages_checked': 2,
                'initial_closed_daily_candles': n, 'after_incremental_update': n_updated,
                'csv_bom': 'PASS', 'primary_key_uniqueness': 'PASS'}
    finally:
        collector.CONFIG[exchange] = (base_url, original_db)


def main():
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'git_sha': os.environ.get('GITHUB_SHA', 'local'),
              'scope': 'public KRW-BTC 11 units, 2 pages; 11 daily candles, update, temp DB, CSV',
              'exchanges': {}}
    old_target = collector.TARGET
    collector.TARGET = 11
    try:
        with tempfile.TemporaryDirectory(prefix='candle_live_probe_') as tmp:
            for exchange in ('upbit', 'bithumb'):
                try:
                    result['exchanges'][exchange] = check_exchange(exchange, tmp)
                    print(f'PASS live {exchange}: 11 timeframes, 2 pages, temporary SQLite and CSV')
                except Exception as exc:
                    result['exchanges'][exchange] = {'status': 'FAIL',
                                                      'error_type': type(exc).__name__,
                                                      'error': str(exc)[:300]}
                    print(f'FAIL live {exchange}: {type(exc).__name__}: {str(exc)[:200]}', file=sys.stderr)
    finally:
        collector.TARGET = old_target
        EVIDENCE.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print('EVIDENCE:', EVIDENCE.name)
    return int(any(item.get('status') != 'PASS' for item in result['exchanges'].values()) or
               len(result['exchanges']) != 2)


if __name__ == '__main__':
    sys.exit(main())
