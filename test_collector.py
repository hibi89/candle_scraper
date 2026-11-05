import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import collector

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original = collector.CONFIG['upbit']
        collector.CONFIG['upbit'] = ('https://mock.invalid', Path(self.tmp.name)/'upbit_candles.sqlite3')
    def tearDown(self):
        collector.CONFIG['upbit'] = self.original
        self.tmp.cleanup()
    def candle(self, n):
        start = datetime(2025,1,1,tzinfo=timezone.utc) + timedelta(minutes=n)
        stamp = start.strftime('%Y-%m-%dT%H:%M:%S')
        return {'market':'KRW-BTC', 'candle_date_time_utc':stamp,
                'candle_date_time_kst':start.astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%dT%H:%M:%S'),
                'opening_price':1,'high_price':2,'low_price':0.5,'trade_price':1.5,
                'candle_acc_trade_volume':10,'candle_acc_trade_price':15}
    def mock_request(self,exchange,path,params):
        if path == '/market/all': return [{'market':'KRW-BTC'}]
        items = [self.candle(i) for i in range(4,-1,-1)]
        if 'to' in params:
            cutoff=params['to'].removesuffix('Z')
            items=[c for c in items if c['candle_date_time_utc'] < cutoff]
        return items[:params['count']]
    def test_schema_and_duplicates(self):
        db=collector.db_open('upbit')
        page=[self.candle(0),self.candle(1)]
        self.assertEqual(collector.insert_page(db,'KRW-BTC',1,page),2)
        self.assertEqual(collector.insert_page(db,'KRW-BTC',1,page),0)
        self.assertEqual(db.execute('select count(*) from candles').fetchone()[0],2)
        db.close()
    def test_initial_and_resume(self):
        with patch.object(collector,'request',side_effect=self.mock_request):
            n,added,status=collector.collect_pair('upbit','KRW-BTC',1,'initial')
            self.assertEqual((n,added,status),(5,5,'ok'))
            n,added,status=collector.collect_pair('upbit','KRW-BTC',1,'initial')
            self.assertEqual((n,added,status),(5,0,'already-finished'))
    def test_update(self):
        db=collector.db_open('upbit')
        collector.insert_page(db,'KRW-BTC',1,[self.candle(0),self.candle(1)])
        db.close()
        with patch.object(collector,'request',side_effect=self.mock_request):
            n,added,status=collector.collect_pair('upbit','KRW-BTC',1,'update')
            self.assertEqual((n,added,status),(5,3,'ok'))
            n,added,status=collector.collect_pair('upbit','KRW-BTC',1,'update')
            self.assertEqual((n,added,status),(5,0,'ok'))
    def test_csv(self):
        db=collector.db_open('upbit')
        collector.insert_page(db,'KRW-BTC',1,[self.candle(0)])
        db.close()
        n,folder=collector.export_csv('upbit',Path(self.tmp.name)/'csv')
        self.assertEqual(n,1)
        self.assertIn('KRW-BTC', (folder/'KRW-BTC_1.csv').read_text(encoding='utf-8-sig'))
    def test_closed(self):
        now=datetime(2025,1,1,0,0,30,tzinfo=timezone.utc)
        self.assertFalse(collector.is_closed(self.candle(0),1,now))
        self.assertTrue(collector.is_closed(self.candle(0),1,now+timedelta(minutes=1)))
    def test_endpoint(self):
        self.assertEqual(collector.endpoint(3),'/candles/minutes/3')
        self.assertEqual(collector.endpoint('day'),'/candles/days')
        self.assertEqual(collector.endpoint('week'),'/candles/weeks')

if __name__=='__main__': unittest.main()

class BoundaryTests(unittest.TestCase):
    def test_weekly_closure_monday_kst(self):
        c={'candle_date_time_utc':'2025-01-05T15:00:00','candle_date_time_kst':'2025-01-06T00:00:00'}
        self.assertFalse(collector.is_closed(c,'week',datetime(2025,1,12,14,59,tzinfo=timezone.utc)))
        self.assertTrue(collector.is_closed(c,'week',datetime(2025,1,12,15,0,tzinfo=timezone.utc)))
    def test_daily_closure_kst(self):
        c={'candle_date_time_utc':'2025-01-05T15:00:00','candle_date_time_kst':'2025-01-06T00:00:00'}
        self.assertFalse(collector.is_closed(c,'day',datetime(2025,1,6,14,59,tzinfo=timezone.utc)))
        self.assertTrue(collector.is_closed(c,'day',datetime(2025,1,6,15,0,tzinfo=timezone.utc)))
    def test_bad_mode_rejected_without_network(self):
        with self.assertRaises(ValueError): collector.run('upbit','bad')

class SafetyTests(CollectorTests):
    def test_reject_unsafe_csv_filename(self):
        db=collector.db_open('upbit')
        db.execute('INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)',
                   ('KRW-../../evil',1,'2025-01-01T00:00:00','2025-01-01T09:00:00',1,2,0.5,1,10,10))
        db.commit(); db.close()
        with self.assertRaises(ValueError):
            collector.export_csv('upbit',Path(self.tmp.name)/'exports')
    def test_existing_db_schema_check(self):
        import sqlite3
        path=collector.CONFIG['upbit'][1]
        db=sqlite3.connect(path)
        db.execute('CREATE TABLE candles (market TEXT)')
        db.commit(); db.close()
        with self.assertRaisesRegex(RuntimeError,'incompatible schema'):
            collector.db_open('upbit')

class EditionTests(unittest.TestCase):
    def test_single_exchange_has_no_selection_prompt(self):
        import menu
        with patch('builtins.input', side_effect=AssertionError('must not prompt')):
            self.assertEqual(menu.choose_exchange(('upbit',)), ['upbit'])
            self.assertEqual(menu.choose_exchange(('bithumb',)), ['bithumb'])
    def test_both_edition_choices(self):
        import menu
        with patch('builtins.input', return_value='3'):
            self.assertEqual(menu.choose_exchange(('upbit','bithumb')), ['upbit','bithumb'])
    def test_invalid_edition(self):
        import menu
        with self.assertRaises(ValueError): menu.main(('unknown',))


class LiveSmokeTests(CollectorTests):
    def test_smoke_does_not_create_database(self):
        def fake_request(exchange, path, params):
            if path == '/market/all': return [{'market':'KRW-BTC'}]
            return [self.candle(0)]
        db_path = collector.CONFIG['upbit'][1]
        with patch.object(collector,'request',side_effect=fake_request):
            self.assertEqual(collector.smoke_check('upbit', lambda _:None),1)
        self.assertFalse(db_path.exists())
    def test_smoke_detects_incompatible_api_response(self):
        def fake_request(exchange,path,params):
            if path == '/market/all': return [{'market':'KRW-BTC'}]
            return [{'candle_date_time_utc':'x'}]
        with patch.object(collector,'request',side_effect=fake_request):
            with self.assertRaisesRegex(RuntimeError,'missing'):
                collector.smoke_check('upbit',lambda _:None)

class ProviderValidationTests(CollectorTests):
    def test_reject_nan_without_writing(self):
        db=collector.db_open('upbit')
        bad=self.candle(0)
        bad['trade_price']=float('nan')
        with self.assertRaisesRegex(ValueError,'numeric'):
            collector.insert_page(db,'KRW-BTC',1,[self.candle(1),bad])
        self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0],0)
        db.close()
    def test_reject_invalid_ohlc_without_writing(self):
        db=collector.db_open('upbit')
        bad=self.candle(0)
        bad['high_price']=1
        with self.assertRaisesRegex(ValueError,'OHLC'):
            collector.insert_page(db,'KRW-BTC',1,[bad])
        self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0],0)
        db.close()
    def test_reject_invalid_timestamp(self):
        bad=self.candle(0)
        bad['candle_date_time_utc']='not-a-time'
        with self.assertRaisesRegex(ValueError,'timestamp'):
            collector.validate_candle(bad)

class SelectionAndMonthlyTests(unittest.TestCase):
    def test_priority_order(self):
        self.assertEqual(collector.UNITS, ('month','week','day',240,60,30,15,10,5,3,1))
    def test_month_endpoint(self):
        self.assertEqual(collector.endpoint('month'), '/candles/months')
    def test_month_closure_leap_year(self):
        c={'candle_date_time_utc':'2024-01-31T15:00:00','candle_date_time_kst':'2024-02-01T00:00:00'}
        self.assertFalse(collector.is_closed(c,'month',datetime(2024,2,29,14,59,tzinfo=timezone.utc)))
        self.assertTrue(collector.is_closed(c,'month',datetime(2024,2,29,15,0,tzinfo=timezone.utc)))
    def test_month_closure_december(self):
        c={'candle_date_time_utc':'2024-11-30T15:00:00','candle_date_time_kst':'2024-12-01T00:00:00'}
        self.assertTrue(collector.is_closed(c,'month',datetime(2024,12,31,15,0,tzinfo=timezone.utc)))
    def test_selection(self):
        import menu
        with patch('builtins.input',return_value='1,4,11'):
            self.assertEqual(menu.choose_units(),('month',240,1))
        with patch('builtins.input',return_value='a'):
            self.assertEqual(menu.choose_units(),collector.UNITS)
        with patch('builtins.input',return_value='99'):
            self.assertEqual(menu.choose_units(),())
    def test_run_processes_units_in_priority_order(self):
        from unittest.mock import Mock
        seen=[]
        def fake_pair(exchange,market,unit,mode):
            seen.append(unit)
            return (1,1,'ok')
        with patch.object(collector,'markets',return_value=['KRW-BTC']),patch.object(collector,'collect_pair',side_effect=fake_pair):
            collector.run('upbit','initial',units=(1,'month',240),progress=lambda _:None)
        self.assertEqual(seen,['month',240,1])

class ExportAtomicityTests(CollectorTests):
    def test_export_preserves_existing_csv_on_failure(self):
        import csv
        from unittest.mock import patch
        db=collector.db_open('upbit')
        collector.insert_page(db,'KRW-BTC',1,[self.candle(1)])
        db.close()
        out=collector.ROOT/'exports'/'upbit'
        out.mkdir(parents=True,exist_ok=True)
        target=out/'KRW-BTC_1.csv'
        target.write_text('previous good export',encoding='utf-8')
        with patch.object(collector.csv,'writer',side_effect=OSError('simulated disk failure')):
            with self.assertRaises(OSError):
                collector.export_csv('upbit')
        self.assertEqual(target.read_text(encoding='utf-8'),'previous good export')
        self.assertFalse((out/'KRW-BTC_1.csv.partial').exists())

    def test_export_replaces_csv_after_success(self):
        db=collector.db_open('upbit')
        collector.insert_page(db,'KRW-BTC',1,[self.candle(1)])
        db.close()
        n,out=collector.export_csv('upbit')
        self.assertEqual(n,1)
        self.assertIn('KRW-BTC', (out/'KRW-BTC_1.csv').read_text(encoding='utf-8-sig'))
        self.assertFalse((out/'KRW-BTC_1.csv.partial').exists())

if __name__ == "__main__":
    unittest.main()

class DatabaseInspectionTests(CollectorTests):
    def test_missing_database_does_not_create_one(self):
        path=collector.CONFIG['upbit'][1]
        info=collector.inspect_database('upbit')
        self.assertFalse(info['exists'])
        self.assertFalse(path.exists())

    def test_existing_database_counts_without_writes(self):
        db=collector.db_open('upbit')
        collector.insert_page(db,'KRW-BTC',1,[self.candle(0),self.candle(1)])
        collector.insert_page(db,'KRW-ETH',3,[dict(self.candle(0), market='KRW-ETH')])
        db.close()
        info=collector.inspect_database('upbit')
        self.assertEqual((info['markets'],info['pairs'],info['candles']),(2,2,3))
        db=collector.db_open('upbit')
        self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0],3)
        db.close()

    def test_invalid_schema_reports_error(self):
        import sqlite3
        db=sqlite3.connect(collector.CONFIG['upbit'][1])
        db.execute('CREATE TABLE candles (market TEXT)')
        db.commit(); db.close()
        with self.assertRaisesRegex(RuntimeError,'Incompatible'):
            collector.inspect_database('upbit')


class PaginationSafetyTests(CollectorTests):
    def test_repeated_page_does_not_mark_initial_finished(self):
        repeated = [self.candle(i) for i in range(199,-1,-1)]
        with patch.object(collector, 'request', return_value=repeated):
            with self.assertRaisesRegex(ValueError, 'Unordered, duplicated or cursor-exceeding'):
                collector.collect_pair('upbit', 'KRW-BTC', 1, 'initial')
        db = collector.db_open('upbit')
        try:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0], 200)
            self.assertIsNone(db.execute('SELECT finished FROM collection_state WHERE market=? AND unit=?', ('KRW-BTC',1)).fetchone())
        finally: db.close()
    def test_empty_history_is_marked_exhausted(self):
        with patch.object(collector, 'request', return_value=[]):
            self.assertEqual(collector.collect_pair('upbit', 'KRW-BTC', 1, 'initial'), (0,0,'ok'))
        db=collector.db_open('upbit')
        try:
            self.assertEqual(db.execute('SELECT finished FROM collection_state').fetchone()[0],1)
        finally: db.close()


class ProviderBoundaryTests(unittest.TestCase):
    def test_weekly_nine_am_kst_boundary(self):
        c = {'candle_date_time_utc':'2025-01-06T00:00:00',
             'candle_date_time_kst':'2025-01-06T09:00:00'}
        boundary = datetime(2025,1,13,0,0,tzinfo=timezone.utc)
        self.assertFalse(collector.is_closed(c,'week',boundary-timedelta(seconds=1)))
        self.assertTrue(collector.is_closed(c,'week',boundary))

    def test_monthly_nine_am_kst_boundary(self):
        c = {'candle_date_time_utc':'2025-01-01T00:00:00',
             'candle_date_time_kst':'2025-01-01T09:00:00'}
        boundary = datetime(2025,2,1,0,0,tzinfo=timezone.utc)
        self.assertFalse(collector.is_closed(c,'month',boundary-timedelta(seconds=1)))
        self.assertTrue(collector.is_closed(c,'month',boundary))

class InitialCapTests(CollectorTests):
    def test_initial_never_exceeds_target_with_overlapping_page(self):
        db = collector.db_open('upbit')
        try:
            for i in range(collector.TARGET - 1):
                db.execute('INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)',
                           ('KRW-BTC', 1, f'2026-01-{1+i//1440:02d}T{i%1440//60:02d}:{i%60:02d}:00',
                            '2024-01-01T00:00:00',1,2,0.5,1.5,10,15))
            db.commit()
        finally: db.close()
        with patch.object(collector, 'request', return_value=[self.candle(2),self.candle(1)]):
            n, added, _ = collector.collect_pair('upbit','KRW-BTC',1,'initial')
        self.assertEqual(n, collector.TARGET)
        self.assertEqual(added, 1)

    def test_update_existing_pair_can_grow_past_initial_cap(self):
        db = collector.db_open('upbit')
        collector.insert_page(db,'KRW-BTC',1,[self.candle(0)])
        db.close()
        with patch.object(collector,'request',side_effect=self.mock_request):
            n, added, _ = collector.collect_pair('upbit','KRW-BTC',1,'update')
        self.assertEqual((n,added),(5,4))
