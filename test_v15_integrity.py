"""v1.5 regression: reject poisoned pages before any commit, preserve old DBs."""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import collector

UTC = timezone.utc
KST = timezone(timedelta(hours=9))


def candle(n, market='KRW-BTC'):
    instant = datetime(2025, 1, 1, tzinfo=UTC) + timedelta(minutes=n)
    return {
        'market': market,
        'candle_date_time_utc': instant.strftime('%Y-%m-%dT%H:%M:%S'),
        'candle_date_time_kst': instant.astimezone(KST).strftime('%Y-%m-%dT%H:%M:%S'),
        'opening_price': 100, 'high_price': 120, 'low_price': 90,
        'trade_price': 110, 'candle_acc_trade_volume': 2, 'candle_acc_trade_price': 200,
    }


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.save = collector.CONFIG['upbit']
        self.path = Path(self.tmp.name) / 'upbit.sqlite3'
        collector.CONFIG['upbit'] = ('https://no-network.example', self.path)

    def tearDown(self):
        collector.CONFIG['upbit'] = self.save
        self.tmp.cleanup()

    def test_valid_provider_timestamp_pair(self):
        collector.validate_candle(candle(0), 'KRW-BTC')

    def test_valid_descending_page(self):
        collector.validate_page([candle(3), candle(2), candle(1)], 'KRW-BTC')

    def test_mismatched_kst_timestamp(self):
        bad = candle(0); bad['candle_date_time_kst'] = bad['candle_date_time_utc']
        with self.assertRaisesRegex(ValueError, 'UTC/KST'): collector.validate_candle(bad)

    def test_mismatched_market(self):
        with self.assertRaisesRegex(ValueError, 'market mismatch'):
            collector.validate_candle(candle(0, 'KRW-ETH'), 'KRW-BTC')

    def test_missing_market(self):
        bad = candle(0); del bad['market']
        with self.assertRaisesRegex(ValueError, 'market mismatch'):
            collector.validate_candle(bad, 'KRW-BTC')

    def test_offset_in_utc_timestamp(self):
        bad = candle(0); bad['candle_date_time_utc'] += 'Z'
        with self.assertRaisesRegex(ValueError, 'timezone'):
            collector.validate_candle(bad)

    def test_offset_in_kst_timestamp(self):
        bad = candle(0); bad['candle_date_time_kst'] += '+09:00'
        with self.assertRaisesRegex(ValueError, 'timezone'):
            collector.validate_candle(bad)

    def test_bad_utc_timestamp(self):
        bad = candle(0); bad['candle_date_time_utc'] = '2025-20-92T01:00:00'
        with self.assertRaisesRegex(ValueError, 'timestamp'):
            collector.validate_candle(bad)

    def test_missing_timestamp(self):
        bad = candle(0); del bad['candle_date_time_kst']
        with self.assertRaisesRegex(ValueError, 'timestamp'):
            collector.validate_candle(bad)

    def test_invalid_object(self):
        with self.assertRaisesRegex(ValueError, 'object'):
            collector.validate_candle(None)

    def test_unsorted_page(self):
        with self.assertRaisesRegex(ValueError, 'Unordered'):
            collector.validate_page([candle(1), candle(2)], 'KRW-BTC')

    def test_duplicate_page_timestamp(self):
        with self.assertRaisesRegex(ValueError, 'duplicated'):
            collector.validate_page([candle(2), candle(2)], 'KRW-BTC')

    def test_page_equal_cursor(self):
        with self.assertRaisesRegex(ValueError, 'cursor'):
            collector.validate_page([candle(2)], 'KRW-BTC', candle(2)['candle_date_time_utc'])

    def test_page_newer_than_cursor(self):
        with self.assertRaisesRegex(ValueError, 'cursor'):
            collector.validate_page([candle(3)], 'KRW-BTC', candle(2)['candle_date_time_utc'])

    def test_page_older_than_cursor(self):
        collector.validate_page([candle(1), candle(0)], 'KRW-BTC', candle(2)['candle_date_time_utc'])

    def test_wrong_market_cannot_write_any_rows(self):
        db = collector.db_open('upbit')
        try:
            with self.assertRaisesRegex(ValueError, 'market mismatch'):
                collector.insert_page(db, 'KRW-BTC', 1, [candle(1), candle(0, 'KRW-ETH')])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0], 0)
        finally: db.close()

    def test_wrong_timezone_cannot_write_any_rows(self):
        db = collector.db_open('upbit')
        try:
            bad = candle(0); bad['candle_date_time_kst'] = '2025-01-01T00:00:00'
            with self.assertRaisesRegex(ValueError, 'UTC/KST'):
                collector.insert_page(db, 'KRW-BTC', 1, [candle(1), bad])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0], 0)
        finally: db.close()

    def test_poisoned_second_page_does_not_commit_that_page(self):
        saved = [candle(i) for i in range(200, 0, -1)]
        wrong = [candle(-1, 'KRW-ETH')]
        with patch.object(collector, 'request', side_effect=[saved, wrong]):
            with self.assertRaisesRegex(ValueError, 'market mismatch'):
                collector.collect_pair('upbit', 'KRW-BTC', 1, 'initial')
        db = collector.db_open('upbit')
        try:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0], 200)
            self.assertIsNone(db.execute('SELECT * FROM collection_state').fetchone())
        finally: db.close()

    def test_foreign_database_not_modified(self):
        db = sqlite3.connect(self.path)
        db.execute('CREATE TABLE private_data (id INTEGER PRIMARY KEY, value TEXT)')
        db.execute('INSERT INTO private_data(value) VALUES (?)', ('preserve',))
        db.commit(); db.close()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'unrelated'):
            collector.db_open('upbit')
        self.assertEqual(before, self.path.read_bytes())

    def test_foreign_schema_not_modified(self):
        db = sqlite3.connect(self.path)
        db.execute('CREATE TABLE candles (market TEXT)')
        db.commit(); db.close()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'incompatible schema'):
            collector.db_open('upbit')
        self.assertEqual(before, self.path.read_bytes())

    def test_empty_existing_file_not_modified(self):
        self.path.touch()
        with self.assertRaisesRegex(RuntimeError, 'invalid'):
            collector.db_open('upbit')
        self.assertEqual(self.path.stat().st_size, 0)

    def test_invalid_pair_mode_without_db_write(self):
        with self.assertRaisesRegex(ValueError, 'Unknown mode'):
            collector.collect_pair('upbit', 'KRW-BTC', 1, 'delete')
        self.assertFalse(self.path.exists())

    def test_bad_markets_filtered(self):
        with patch.object(collector, 'request', return_value=[
                {'market': 'KRW-BTC'}, {'market': 'KRW-../../etc'},
                {'market': 'KRW-ABC/DEF'}, {'market': 'BTC-ETH'},
                {'market': 'KRW-ABC'}, {'market': 'KRW-BTC'}]):
            self.assertEqual(collector.markets('upbit'), ['KRW-ABC', 'KRW-BTC'])

    def test_no_markets_is_error_not_false_success(self):
        with patch.object(collector, 'markets', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'no KRW markets'):
                collector.run('upbit', 'initial', units=(1,), progress=lambda _: None)
        self.assertFalse(self.path.exists())

    def test_empty_unit_selection_does_not_hit_api(self):
        with patch.object(collector, 'markets', side_effect=AssertionError('API must not be called')):
            with self.assertRaisesRegex(ValueError, 'No valid'):
                collector.run('upbit', 'initial', units=(), progress=lambda _: None)


if __name__ == '__main__':
    unittest.main()

class ConcurrentDbTests(unittest.TestCase):
    def test_five_parallel_markets_share_sqlite_without_lock_errors(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as temp:
            saved = collector.CONFIG['upbit']
            collector.CONFIG['upbit'] = ('https://no-network.example', Path(temp)/'upbit.sqlite3')
            symbols = [f'KRW-X{i}' for i in range(5)]
            def fake_request(exchange, path, params):
                return [candle(0, params['market'])]
            try:
                with patch.object(collector,'request',side_effect=fake_request):
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        results = list(executor.map(
                            lambda market: collector.collect_pair('upbit', market, 1, 'initial'),
                            symbols))
                self.assertEqual([r[0] for r in results], [1]*5)
                self.assertEqual(collector.inspect_database('upbit')['candles'], 5)
            finally:
                collector.CONFIG['upbit'] = saved
