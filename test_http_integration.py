"""Network-stack integration with a localhost Upbit/Bithumb contract simulator.

No exchange traffic, user DB, or external service is accessed.
"""
import json
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import collector

START = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
KST = timezone(timedelta(hours=9))


def candle_at(index):
    utc = START + timedelta(minutes=index)
    return {
        'market': 'KRW-BTC',
        'candle_date_time_utc': utc.strftime('%Y-%m-%dT%H:%M:%S'),
        'candle_date_time_kst': utc.astimezone(KST).strftime('%Y-%m-%dT%H:%M:%S'),
        'opening_price': 100, 'high_price': 110,
        'low_price': 90, 'trade_price': 105,
        'candle_acc_trade_volume': 5.1,
        'candle_acc_trade_price': 510.0,
    }


class ExchangeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlsplit(self.path)
        params = parse_qs(parsed.query)
        exchange = self.server.exchange
        try:
            if parsed.path == '/v1/market/all':
                expected_flag = 'isDetails' if exchange == 'bithumb' else 'is_details'
                if params.get(expected_flag) != ['false']:
                    return self.send_error(400, 'Wrong exchange market flag')
                response = [{'market': 'KRW-BTC'}, {'market': 'BTC-USDT'}]
            elif parsed.path.startswith('/v1/candles/'):
                if params.get('market') != ['KRW-BTC']:
                    return self.send_error(400, 'Unknown market')
                count = int(params['count'][0])
                if count < 1 or count > 200:
                    return self.send_error(400, 'Invalid count')
                if parsed.path == '/v1/candles/minutes/1':
                    items = [candle_at(i) for i in range(205, -1, -1)]
                elif (parsed.path.startswith('/v1/candles/minutes/') or parsed.path in
                      ('/v1/candles/days','/v1/candles/weeks','/v1/candles/months')):
                    items = [candle_at(i) for i in (120, 60, 0)]
                else:
                    return self.send_error(404)
                if params.get('to'):
                    raw = params['to'][0]
                    if exchange == 'bithumb':
                        if raw.endswith('Z') or '+' in raw:
                            return self.send_error(400, 'Bithumb cursor must use KST wall clock')
                        cutoff = datetime.fromisoformat(raw).replace(tzinfo=KST).astimezone(timezone.utc)
                    else:
                        if not raw.endswith('Z'):
                            return self.send_error(400, 'Upbit cursor must use UTC Z')
                        cutoff = datetime.fromisoformat(raw.replace('Z','+00:00'))
                    items = [c for c in items if datetime.fromisoformat(c['candle_date_time_utc']).replace(tzinfo=timezone.utc) < cutoff]
                response = items[:count]
            else:
                return self.send_error(404)
            raw = json.dumps(response).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (ValueError, KeyError):
            self.send_error(400, 'Malformed query')

    def log_message(self, format, *args):
        pass


class HttpIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.saved = dict(collector.CONFIG)
        self.gates = dict(collector.GATES)
        self.servers = []
        self.threads = []
        for exchange in ('upbit','bithumb'):
            server = ThreadingHTTPServer(('127.0.0.1',0),ExchangeHandler)
            server.exchange = exchange
            self.servers.append(server)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)
            collector.CONFIG[exchange] = (f'http://127.0.0.1:{server.server_port}/v1', Path(self.temp.name)/(exchange+'.sqlite3'))
            collector.GATES[exchange] = collector.RateGate(0)

    def tearDown(self):
        collector.CONFIG.clear(); collector.CONFIG.update(self.saved)
        collector.GATES.clear(); collector.GATES.update(self.gates)
        for server in self.servers:
            server.shutdown(); server.server_close()
        for thread in self.threads:
            thread.join(2)
        self.temp.cleanup()

    def test_upbit_real_http_paging_and_resume(self):
        self._initial_update('upbit')

    def test_bithumb_real_http_paging_and_resume(self):
        self._initial_update('bithumb')

    def _initial_update(self, exchange):
        self.assertEqual(collector.markets(exchange), ['KRW-BTC'])
        self.assertEqual(collector.collect_pair(exchange,'KRW-BTC',1,'initial'),(206,206,'ok'))
        self.assertEqual(collector.collect_pair(exchange,'KRW-BTC',1,'initial'),(206,0,'already-finished'))
        self.assertEqual(collector.collect_pair(exchange,'KRW-BTC',1,'update'),(206,0,'ok'))
        self.assertEqual(collector.inspect_database(exchange)['candles'],206)
        db=sqlite3.connect(collector.CONFIG[exchange][1]);
        try:
            self.assertEqual(db.execute('SELECT COUNT(DISTINCT utc) FROM candles').fetchone()[0],206)
        finally: db.close()

    def test_both_exchanges_remain_separate(self):
        for exchange in ('upbit','bithumb'):
            self.assertEqual(collector.collect_pair(exchange,'KRW-BTC',1,'initial')[0],206)
        self.assertNotEqual(collector.CONFIG['upbit'][1],collector.CONFIG['bithumb'][1])
        self.assertEqual(collector.inspect_database('upbit')['candles'],206)
        self.assertEqual(collector.inspect_database('bithumb')['candles'],206)

    def test_read_only_full_api_probe_with_paginated_minutes(self):
        for exchange in ('upbit','bithumb'):
            count = collector.smoke_check(exchange, progress=lambda _:None)
            self.assertEqual(count,1)
            self.assertFalse(collector.CONFIG[exchange][1].exists())

    def test_full_menu_backfill_and_csv_network_stack(self):
        for exchange in ('upbit','bithumb'):
            jobs, errors = collector.run(exchange,'initial',progress=lambda _:None)
            self.assertEqual(jobs, 11)
            self.assertEqual(errors, [])
            stats = collector.inspect_database(exchange)
            self.assertEqual((stats['markets'],stats['pairs'],stats['candles']), (1,11,236))
            exported, folder = collector.export_csv(exchange, Path(self.temp.name) / f'{exchange}_csv')
            self.assertEqual(exported,11)
            self.assertTrue((folder/'KRW-BTC_1.csv').exists())
            self.assertTrue((folder/'KRW-BTC_month.csv').exists())
            jobs, errors = collector.run(exchange,'update',progress=lambda _:None)
            self.assertEqual(errors, [])
            self.assertEqual(collector.inspect_database(exchange)['candles'],236)

    def test_pagination_cursors_are_different_provider_contracts(self):
        self.assertEqual(collector.pagination_cursor('upbit','2025-01-01T00:00:00'),'2025-01-01T00:00:00Z')
        self.assertEqual(collector.pagination_cursor('bithumb','2025-01-01T00:00:00'),'2025-01-01T09:00:00')
        self.assertEqual(collector.pagination_cursor('bithumb','2024-12-31T18:00:00'),'2025-01-01T03:00:00')
        self.assertEqual(collector.pagination_cursor('bithumb','2025-01-01T00:00:00Z'),'2025-01-01T09:00:00')
        self.assertEqual(collector.market_query('upbit'),{'is_details':'false'})
        self.assertEqual(collector.market_query('bithumb'),{'isDetails':'false'})


if __name__ == '__main__': unittest.main()
