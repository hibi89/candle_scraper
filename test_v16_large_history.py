"""Full 10,000-candle cap, subsequent unlimited updates, and safe resume."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import collector

UTC = timezone.utc
KST = timezone(timedelta(hours=9))
START = datetime(2025, 1, 1, tzinfo=UTC)


def make_candle(i):
    instant = START + timedelta(minutes=i)
    return {
        'market': 'KRW-BTC',
        'candle_date_time_utc': instant.strftime('%Y-%m-%dT%H:%M:%S'),
        'candle_date_time_kst': instant.astimezone(KST).strftime('%Y-%m-%dT%H:%M:%S'),
        'opening_price': 100, 'high_price': 110,
        'low_price': 90, 'trade_price': 105,
        'candle_acc_trade_volume': 2, 'candle_acc_trade_price': 210,
    }


class LargeHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.saved = dict(collector.CONFIG)
        self.records = [make_candle(i) for i in range(10002)][::-1]
        self.requests = 0
        self.fail_on_call = None
        for exchange in ('upbit','bithumb'):
            collector.CONFIG[exchange] = ('https://never-contacts-real-api.invalid',
                                          Path(self.temp.name) / (exchange+'.sqlite3'))

    def tearDown(self):
        collector.CONFIG.clear(); collector.CONFIG.update(self.saved)
        self.temp.cleanup()

    def simulated_api(self, exchange, path, params):
        self.requests += 1
        if self.requests == self.fail_on_call:
            raise ConnectionError('simulated one-time outage')
        count = params['count']
        self.assertLessEqual(count, 200)
        rows = self.records
        if params.get('to'):
            cursor = params['to']
            if exchange == 'upbit':
                limit = datetime.fromisoformat(cursor.replace('Z','+00:00'))
            else:
                limit = datetime.fromisoformat(cursor).replace(tzinfo=KST).astimezone(UTC)
            rows = [r for r in self.records
                    if datetime.fromisoformat(r['candle_date_time_utc']).replace(tzinfo=UTC) < limit]
        return rows[:count]

    def test_initial_10000_then_unlimited_three_updates_both_exchanges(self):
        for exchange in ('upbit', 'bithumb'):
            self.requests = 0
            with patch.object(collector, 'request', side_effect=self.simulated_api):
                self.assertEqual(collector.collect_pair(exchange,'KRW-BTC',1,'initial')[:2], (10000,10000))
                self.assertLessEqual(self.requests, 52)
                self.assertEqual(collector.collect_pair(exchange,'KRW-BTC',1,'initial')[1], 0)
                self.records = [make_candle(i) for i in range(10005)][::-1]
                self.assertEqual(collector.collect_pair(exchange,'KRW-BTC',1,'update')[:2], (10003,3))
                self.assertEqual(collector.collect_pair(exchange,'KRW-BTC',1,'update')[:2], (10003,0))
                self.assertEqual(collector.inspect_database(exchange)['candles'],10003)
            self.records = [make_candle(i) for i in range(10002)][::-1]

    def test_partial_failure_resume_is_lossless(self):
        self.fail_on_call = 3
        with patch.object(collector, 'request', side_effect=self.simulated_api):
            with self.assertRaisesRegex(ConnectionError, 'outage'):
                collector.collect_pair('upbit','KRW-BTC',1,'initial')
        self.assertEqual(collector.inspect_database('upbit')['candles'],400)
        self.fail_on_call = None
        with patch.object(collector, 'request', side_effect=self.simulated_api):
            self.assertEqual(collector.collect_pair('upbit','KRW-BTC',1,'initial')[:2], (10000,9600))
            self.assertEqual(collector.collect_pair('upbit','KRW-BTC',1,'initial')[1], 0)
        self.assertEqual(collector.inspect_database('upbit')['candles'],10000)


if __name__=='__main__': unittest.main()
