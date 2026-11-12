"""Zero-network synthetic validation of read-only, no-lookahead forward signal study."""
from __future__ import annotations

import csv
from contextlib import closing
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import coin_forward_eval as f


class ForwardStudyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="p85-coin-")
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)
        self.db=self.base/'upbit_candles.sqlite3'
        self.signals=self.base/'signals.csv'
        self.out=self.base/'results'
        self.rule_name='SMA GOLDEN'
        self.rule_hash='a'*64
        self.bars=[(10.,10.),(10.,10.),(10.,10.),(12.,12.),(14.,14.),(15.,15.),(16.,16.)]
        self.make_db()
        self.make_signals([(2,self.rule_name),(4,self.rule_name)])

    def make_db(self,*, market='KRW-BTC', unit=1, dates=None):
        self.db.unlink(missing_ok=True)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute('CREATE TABLE candles (market TEXT,unit INTEGER,utc TEXT,kst TEXT,open REAL,high REAL,low REAL,close REAL,volume REAL,trade_value REAL,PRIMARY KEY(market,unit,utc))')
            start=datetime(2026,11,1,0,0,0)
            for i,(op,cl) in enumerate(self.bars):
                t=(dates[i] if dates else start+timedelta(minutes=i)).isoformat()
                k=((dates[i] if dates else start+timedelta(minutes=i))+timedelta(hours=9)).isoformat()
                conn.execute('INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)',(market,unit,t,k,op,max(op,cl)+1,min(op,cl)-1,cl,10.,20.))

    def make_signals(self,items,*, exchange='upbit',market='KRW-BTC',unit=1):
        with self.signals.open('w', encoding='utf-8-sig',newline='') as handle:
            w=csv.DictWriter(handle,fieldnames=f.FIELDS)
            w.writeheader()
            for idx,name in items:
                time=(datetime(2026,11,1)+timedelta(minutes=idx))
                w.writerow({'exchange':exchange,'market':market,'unit':unit,'utc':time.isoformat(),
                            'kst':(time+timedelta(hours=9)).isoformat(),'close':self.bars[idx][1],
                            'formula':name,'formula_sha256':self.rule_hash})

    def go(self, **kwargs):
        return f.study([self.db],self.signals,self.out,**kwargs)

    def rows(self):
        with (self.out/'events.csv').open(encoding='utf-8-sig', newline='') as handle:
            return list(csv.DictReader(handle))

    def test_next_open_exits_signal_plus_h_not_signal_bar(self):
        summary=self.go(horizon=2,fee_bps=0,slippage_bps=0)
        rows=self.rows()
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['status'],'COMPLETE')
        self.assertTrue(rows[0]['entry_utc'].endswith('00:03:00'))
        self.assertTrue(rows[0]['exit_utc'].endswith('00:04:00'))
        self.assertAlmostEqual(float(rows[0]['gross_pct']), (14/12-1)*100,6)
        self.assertEqual(summary['metrics']['overall']['complete'],2)

    def test_horizon_one_same_next_bar_open_and_close(self):
        self.go(horizon=1,fee_bps=0,slippage_bps=0)
        rows=self.rows()
        self.assertEqual(rows[0]['entry_utc'],rows[0]['exit_utc'])
        self.assertAlmostEqual(float(rows[0]['net_pct']),0)

    def test_fee_slippage_two_sided_formula_and_gross(self):
        self.go(horizon=2,fee_bps=25,slippage_bps=50)
        row=self.rows()[0]
        net=((14*(1-.005)*(1-.0025))/(12*(1+.005)*(1+.0025))-1)*100
        self.assertAlmostEqual(float(row['net_pct']),net,6)
        self.assertAlmostEqual(float(row['gross_pct']),16.66666667,6)
        self.assertLess(float(row['net_pct']),float(row['gross_pct']))

    def test_right_censor_eof_excluded_no_fake_losses(self):
        self.make_signals([(5,self.rule_name),(6,self.rule_name)])
        result=self.go(horizon=3)
        self.assertEqual(result['metrics']['overall']['complete'],0)
        self.assertEqual(result['metrics']['overall']['censored_eof'],2)
        self.assertIsNone(result['metrics']['overall']['win_rate_pct'])
        self.assertTrue(all(row['net_pct']=='' for row in self.rows()))

    def test_gap_is_censored_not_fake_contiguous_horizon(self):
        times=[datetime(2026,11,1)+timedelta(minutes=i+(1 if i>=4 else 0)) for i in range(7)]
        self.make_db(dates=times)
        self.make_signals([(2,self.rule_name)])
        result=self.go(horizon=3)
        self.assertEqual(result['metrics']['overall']['censored_gap'],1)
        self.assertEqual(result['metrics']['overall']['complete'],0)

    def test_closed_future_only_no_future_signal(self):
        self.make_signals([(6,self.rule_name)])
        r=self.go(horizon=1)
        self.assertEqual(r['metrics']['overall']['censored_eof'],1)
        self.assertFalse(self.rows()[0]['entry_utc'])

    def test_overlapping_events_explicitly_not_portfolio_profit(self):
        self.make_signals([(1,self.rule_name),(2,self.rule_name),(3,self.rule_name)])
        r=self.go(horizon=3)
        self.assertEqual(r['metrics']['overall']['signals'],3)
        self.assertIn('not_portfolio_backtest',r['basis'])
        self.assertIn('Overlapping events',r['warnings'][0])

    def test_chronological_time_split(self):
        r=self.go(horizon=1,split_utc='2026-11-01T00:04:00')
        self.assertEqual(r['metrics']['pre_cutoff']['signals'],1)
        self.assertEqual(r['metrics']['post_cutoff']['signals'],1)
        self.assertIn('not_independent',r['split_claim'])

    def test_multi_rule_same_candle_permitted(self):
        self.make_signals([(2,'A'),(2,'B')])
        r=self.go(horizon=2)
        self.assertEqual(r['signal_count'],2)
        self.assertEqual(r['metrics']['overall']['complete'],2)

    def test_missing_source_signal_fails_without_outputs(self):
        self.make_signals([(1,self.rule_name)],exchange='bithumb')
        with self.assertRaises(f.StudyError): self.go()
        self.assertFalse(self.out.exists())

    def test_tampered_signal_price_fails_no_output(self):
        self.bars[2]=(30.,30.)
        self.make_db()
        with self.assertRaises(f.StudyError): self.go()
        self.assertFalse(self.out.exists())

    def test_duplicate_signal_rejected(self):
        self.make_signals([(2,self.rule_name),(2,self.rule_name)])
        with self.assertRaises(f.StudyError):self.go()

    def test_bad_rule_spreadsheet_injection_rejected(self):
        self.make_signals([(2,'=HYPERLINK()')])
        with self.assertRaises(f.StudyError):self.go()

    def test_report_html_escapes_formula_markups(self):
        self.make_signals([(2,'<script>alert(1)</script>')])
        self.go(horizon=2)
        body=(self.out/'report.html').read_text(encoding='utf8')
        self.assertNotIn('<script>',body)
        self.assertIn('&lt;script&gt;',body)
        self.assertIn('Content-Security-Policy',body)
        self.assertNotIn('https://',body)

    def test_no_source_db_wal_or_shm_mutation(self):
        sha=hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.go()
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),sha)
        self.assertFalse(Path(str(self.db)+'-wal').exists())
        self.assertFalse(Path(str(self.db)+'-shm').exists())

    def test_active_wal_rejected(self):
        Path(str(self.db)+'-wal').write_bytes(b'x')
        with self.assertRaises(f.StudyError):self.go()
        self.assertFalse(self.out.exists())

    def test_existing_output_rejected_preserved(self):
        self.out.mkdir()
        (self.out/'keep.txt').write_text('ORIGINAL')
        with self.assertRaises(f.StudyError):self.go()
        self.assertEqual((self.out/'keep.txt').read_text(),'ORIGINAL')

    def test_candle_limit_rejects_no_partial_output(self):
        with self.assertRaises(f.StudyError):self.go(max_candles=3)
        self.assertFalse(self.out.exists())

    def test_bad_fees_and_horizon(self):
        for opts in ({'fee_bps':-1},{'slippage_bps':1001},{'horizon':0},{'horizon':241},{'horizon':True},{'max_candles':0}):
            with self.subTest(opts=opts),self.assertRaises(f.StudyError):self.go(**opts)
            self.assertFalse(self.out.exists())

    def test_determinism_and_manifest_digests(self):
        source_hash=hashlib.sha256(self.signals.read_bytes()).hexdigest()
        one=self.go(horizon=2)
        blobs={p.name:p.read_bytes() for p in self.out.iterdir()}
        receipt=json.loads((self.out/'manifest.json').read_text())
        self.assertEqual(receipt['sha256'],{name:hashlib.sha256(blobs[name]).hexdigest() for name in ('events.csv','summary.json','report.html')})
        self.out=self.base/'again'
        two=self.go(horizon=2)
        self.assertEqual(blobs,{p.name:p.read_bytes() for p in self.out.iterdir()})
        self.assertEqual(one,two)
        self.assertEqual(one['signal_csv_sha256'],source_hash)

    def test_csv_schema_mismatch(self):
        self.signals.write_text('market,unit,utc\nBTC,1,bad\n')
        with self.assertRaises(f.StudyError):self.go()

    def test_unreasonable_ohlc_rejected(self):
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('UPDATE candles SET high=0 WHERE utc=?',('2026-11-01T00:03:00',))
        with self.assertRaises(f.StudyError):self.go()
        self.assertFalse(self.out.exists())

    def test_empty_signal_still_deterministic_summary(self):
        self.make_signals([])
        result=self.go()
        self.assertEqual(result['signal_count'],0)
        self.assertEqual(result['metrics']['overall']['signals'],0)

    def test_cli_runs_without_network(self):
        argv=[sys.executable,str(Path(f.__file__)),'--db',str(self.db),'--signals',str(self.signals),'--out-dir',str(self.out),'--horizon','2']
        r=subprocess.run(argv,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('PASS_SYNTHETIC_OR_OWNER_SNAPSHOT_ONLY',r.stdout)

    def test_cli_exit_nonzero_no_partial_on_bad_fee(self):
        argv=[sys.executable,str(Path(f.__file__)),'--db',str(self.db),'--signals',str(self.signals),'--out-dir',str(self.out),'--fee-bps','-2']
        r=subprocess.run(argv,capture_output=True,text=True)
        self.assertEqual(r.returncode,2)
        self.assertIn('STUDY_HOLD',r.stderr)
        self.assertFalse(self.out.exists())


if __name__=='__main__': unittest.main()
