"""Regression: failed SQLite page writes are atomic and Windows handles close."""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import collector

UTC = timezone.utc
KST = timezone(timedelta(hours=9))


def candle(index):
    dt = datetime(2025, 1, 1, tzinfo=UTC) + timedelta(minutes=index)
    return {
        'market': 'KRW-BTC',
        'candle_date_time_utc': dt.strftime('%Y-%m-%dT%H:%M:%S'),
        'candle_date_time_kst': dt.astimezone(KST).strftime('%Y-%m-%dT%H:%M:%S'),
        'opening_price': 100.0, 'high_price': 110.0,
        'low_price': 90.0, 'trade_price': 105.0,
        'candle_acc_trade_volume': 1.0, 'candle_acc_trade_price': 105.0,
    }


class SqliteFailureSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = collector.CONFIG['upbit']
        self.dbpath = Path(self.temp.name) / 'fresh_candles.sqlite3'
        collector.CONFIG['upbit'] = ('https://never-api.invalid', self.dbpath)

    def tearDown(self):
        collector.CONFIG['upbit'] = self.previous
        self.temp.cleanup()

    def test_failed_second_row_rolls_back_entire_page_and_preserves_prior_commit(self):
        db = collector.db_open('upbit')
        try:
            self.assertEqual(collector.insert_page(db,'KRW-BTC',1,[candle(0)]),1)
            db.execute('''
                CREATE TRIGGER abort_selected_row BEFORE INSERT ON candles
                WHEN NEW.utc = '2025-01-01T00:02:00'
                BEGIN SELECT RAISE(ABORT,'synthetic disk-like failure'); END
            ''')
            db.commit()
            with self.assertRaisesRegex(sqlite3.IntegrityError,'synthetic disk-like failure'):
                collector.insert_page(db,'KRW-BTC',1,[candle(1),candle(2)])
            self.assertEqual(db.execute(
                'SELECT utc FROM candles ORDER BY utc').fetchall(),
                [('2025-01-01T00:00:00',)])
            db.execute('DROP TRIGGER abort_selected_row')
            db.commit()
            self.assertEqual(collector.insert_page(db,'KRW-BTC',1,[candle(1),candle(2)]),2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0],3)
        finally:
            db.close()

    def test_schema_setup_exception_closes_connection_before_propagation(self):
        connection = Mock()
        connection.execute.side_effect = sqlite3.OperationalError('synthetic WAL permission error')
        with patch.object(collector.sqlite3,'connect',return_value=connection):
            with self.assertRaisesRegex(sqlite3.OperationalError,'WAL permission error'):
                collector.db_open('upbit')
        connection.close.assert_called_once()
        self.assertEqual(connection.execute.call_count,1)

    def test_keyboard_interrupt_during_schema_init_closes_handle(self):
        connection = Mock()
        connection.execute.side_effect = KeyboardInterrupt
        with patch.object(collector.sqlite3,'connect',return_value=connection):
            with self.assertRaises(KeyboardInterrupt):
                collector.db_open('upbit')
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
