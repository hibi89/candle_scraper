"""Multi-market multi-timeframe recovery regression using synthetic provider pages.

Five markets x eleven timeframes x two exchanges, no external API or real DB.
The mock implements each provider's exclusive UTC / KST paging boundary.
"""
import csv
import sqlite3
import tempfile
from contextlib import closing
import threading
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import collector

MARKETS = tuple(f"KRW-TEST{i}" for i in range(5))
UTC = timezone.utc
KST = timezone(timedelta(hours=9))
START = datetime(2000, 1, 1, tzinfo=UTC)


def make_candle(market, unit, index):
    if unit == 'month':
        year, month = divmod(index, 12)
        stamp = START.replace(year=2000 + year, month=month + 1)
    elif unit == 'week':
        stamp = START + timedelta(weeks=index)
    elif unit == 'day':
        stamp = START + timedelta(days=index)
    else:
        stamp = START + timedelta(minutes=unit * index)
    return {'market':market,
            'candle_date_time_utc':stamp.strftime('%Y-%m-%dT%H:%M:%S'),
            'candle_date_time_kst':stamp.astimezone(KST).strftime('%Y-%m-%dT%H:%M:%S'),
            'opening_price':100.0, 'high_price':110.0,
            'low_price':90.0,'trade_price':105.0,
            'candle_acc_trade_volume':1.0,'candle_acc_trade_price':105.0}


class MarketMatrixTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.saved_config=dict(collector.CONFIG)
        self.saved_gates=dict(collector.GATES)
        for exchange in ('upbit','bithumb'):
            collector.CONFIG[exchange] = ('https://offline.invalid', Path(self.tmp.name)/(exchange+'.sqlite3'))
            collector.GATES[exchange] = collector.RateGate(0)
        self.rows = {}
        for market in MARKETS:
            for unit in collector.UNITS:
                self.rows[(market,unit)]=[make_candle(market,unit,i) for i in range(205,-1,-1)]
        self.failed=set()
        self.calls=Counter()
        self.guard=threading.Lock()
        self.inject_fail = False

    def tearDown(self):
        collector.CONFIG.clear(); collector.CONFIG.update(self.saved_config)
        collector.GATES.clear(); collector.GATES.update(self.saved_gates)
        self.tmp.cleanup()

    def fake_request(self, exchange, path, params=None):
        if path == '/market/all':
            self.assertEqual(params,collector.market_query(exchange))
            return [{'market':x} for x in MARKETS] + [{'market':'BTC-NOPE'}]
        self.assertTrue(path.startswith('/candles/'))
        unit = path.split('/')[-1]
        unit = {'months':'month','weeks':'week','days':'day'}.get(unit,int(unit) if unit.isdigit() else unit)
        market=params['market']
        with self.guard:
            self.calls[(exchange,market,unit)]+=1
            if self.inject_fail and (exchange,market,unit)==('bithumb','KRW-TEST0','month') \
                    and (exchange,market,unit) not in self.failed:
                self.failed.add((exchange,market,unit))
                raise ConnectionError('synthetic one-market one-unit outage')
        records=self.rows[(market,unit)]
        if 'to' in params:
            raw=params['to']
            if exchange=='upbit':
                self.assertTrue(raw.endswith('Z'))
                cutoff=datetime.fromisoformat(raw.replace('Z','+00:00'))
            else:
                self.assertFalse(raw.endswith('Z'))
                cutoff=datetime.fromisoformat(raw).replace(tzinfo=KST).astimezone(UTC)
            records=[x for x in records if datetime.fromisoformat(x['candle_date_time_utc']).replace(tzinfo=UTC) < cutoff]
        return records[:params['count']]

    def test_all_markets_all_units_both_exchanges_and_new_updates(self):
        with patch.object(collector,'request',side_effect=self.fake_request):
            for exchange in ('upbit','bithumb'):
                jobs,errors=collector.run(exchange,'initial',progress=lambda _:None)
                self.assertEqual((jobs,errors),(55,[]))
                info=collector.inspect_database(exchange)
                self.assertEqual((info['markets'],info['pairs'],info['candles']),(5,55,5*11*206))
                jobs,errors=collector.run(exchange,'initial',progress=lambda _:None)
                self.assertEqual((jobs,errors),(55,[]))
                self.assertEqual(collector.inspect_database(exchange)['candles'],5*11*206)
            # Synthetic exchange returns a new completed candle for every pair.
            for key, records in self.rows.items():
                self.rows[key]=[make_candle(key[0],key[1],206)]+records
            for exchange in ('upbit','bithumb'):
                jobs,errors=collector.run(exchange,'update',progress=lambda _:None)
                self.assertEqual((jobs,errors),(55,[]))
                self.assertEqual(collector.inspect_database(exchange)['candles'],5*11*207)
                exported,dest=collector.export_csv(exchange,Path(self.tmp.name)/(exchange+'_csv'))
                self.assertEqual(exported,55)
                for market in MARKETS:
                    for unit in collector.UNITS:
                        file=dest / f'{market}_{unit}.csv'
                        with file.open('r',encoding='utf-8-sig',newline='') as handle:
                            self.assertEqual(sum(1 for _ in csv.reader(handle)),208)
                with closing(sqlite3.connect(collector.CONFIG[exchange][1])) as db:
                    duplicate=db.execute('''
                        SELECT COUNT(*) FROM
                        (SELECT market,unit,utc FROM candles GROUP BY market,unit,utc HAVING COUNT(*) > 1)''').fetchone()[0]
                    self.assertEqual(duplicate,0)
            self.assertNotEqual(collector.CONFIG['upbit'][1],collector.CONFIG['bithumb'][1])

    def test_one_market_outage_is_reported_and_subsequent_run_recovers(self):
        self.inject_fail = True
        # All other 54 market-unit combinations must finish despite a single failure.
        with patch.object(collector,'request',side_effect=self.fake_request):
            jobs,errors=collector.run('bithumb','initial',progress=lambda _:None)
            self.assertEqual(jobs,55)
            self.assertEqual(len(errors),1)
            self.assertEqual(errors[0][0:2],('KRW-TEST0','month'))
            self.assertEqual(collector.inspect_database('bithumb')['pairs'],54)
            self.inject_fail = False
            jobs,errors=collector.run('bithumb','initial',progress=lambda _:None)
            self.assertEqual((jobs,errors),(55,[]))
        self.assertEqual(collector.inspect_database('bithumb')['pairs'],55)
        self.assertEqual(collector.inspect_database('bithumb')['candles'],5*11*206)


if __name__ == '__main__':
    unittest.main()
