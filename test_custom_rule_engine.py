"""Synthetic offline contract tests; no market API or customer DB."""
from __future__ import annotations
import csv
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import custom_rule_engine as e


class RuleEngineTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='custom-pattern-test-')
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.db=self.root/'upbit_candles.sqlite3'
        self.rules=self.root/'rule.json'
        self.output=self.root/'hits.csv'
        with closing(sqlite3.connect(self.db)) as conn,conn:
            conn.execute('CREATE TABLE candles(market TEXT, unit INT, utc TEXT, kst TEXT, open REAL,high REAL,low REAL,close REAL,PRIMARY KEY(market,unit,utc))')

    def fill(self, prices, *, market='KRW-BTC', unit=1):
        with closing(sqlite3.connect(self.db)) as conn,conn:
            conn.executemany('INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)',
                [(market,unit,f'2026-11-{i:05d}',f'KST-{i:05d}',v,v*1.01,v*.99,v) for i,v in enumerate(prices)])

    def rulefile(self, condition, rule_id='CUSTOM_1'):
        self.rules.write_text(json.dumps({'version':1,'rules':[{'id':rule_id,'when':condition}]}),encoding='utf-8')
        return e.load_rules(self.rules)

    def runscan(self, cond, **kw):
        return e.scan([self.db],self.rulefile(cond),self.output,**kw)

    def readrows(self):
        with self.output.open(encoding='utf-8-sig',newline='') as stream:
            return list(csv.DictReader(stream))

    def test_sma_cross_reads_full_history_once(self):
        self.fill([10.0]*6+[20.0]+[20.0]*4)
        signal={'cross_up':[{'sma':[3,'close']},{'sma':[5,'close']}]}
        before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        r=self.runscan(signal)
        self.assertEqual((r['matches'],r['candles_processed']), (1,11))
        self.assertEqual(self.readrows()[0]['utc'],'2026-11-00006')
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),before)

    def test_last_window_does_not_backfill_old_signal(self):
        self.fill([10.0]*6+[20.0]+[20.0]*4)
        signal={'cross_up':[{'sma':[3,'close']},{'sma':[5,'close']}]}
        r=self.runscan(signal,last=3)
        self.assertEqual(r['matches'],0)
        self.assertEqual(r['candles_processed'],11)
        self.assertEqual(self.readrows(),[])

    def test_source_readonly_pragma_and_source_preserved(self):
        self.fill([10.0]*5)
        before=self.db.read_bytes()
        result=self.runscan({'gt':['high','low']})
        self.assertEqual(result['matches'],5)
        self.assertEqual(self.db.read_bytes(),before)
        self.assertTrue(self.output.read_bytes().startswith(b'\xef\xbb\xbf'))

    def test_all_any_not_grouping(self):
        self.fill([10.0]*3)
        cond={'all':[{'gt':['high','close']},{'any':[{'lt':['low','close']},{'eq':['high','low']}]},{'not':{'lt':['high','close']}}]}
        self.assertEqual(self.runscan(cond)['matches'],3)

    def test_not_unwarmed_indicator_does_not_emit_false_signals(self):
        self.fill([10.0]*3)
        self.assertEqual(self.runscan({'not':{'gt':[{'sma':[20,'close']},'close']}})['matches'],0)

    def test_boolean_unknown_warmup_any_and_all(self):
        self.fill([10.0]*3)
        any_cond={'any':[{'gt':[{'sma':[20,'close']},'close']},{'lt':['high','low']}]}
        self.assertEqual(self.runscan(any_cond)['matches'],0)
        all_cond={'all':[{'gt':['high','low']},{'gt':[{'sma':[20,'close']},'close']}]}
        self.assertEqual(self.runscan(all_cond,overwrite=True)['matches'],0)

    def test_bollinger_and_ema(self):
        self.fill([10.0]*20+[15.0])
        cond={'all':[{'gt':['close',{'bb_upper':[20,1,'close']}]},{'gt':[{'ema':[3,'close']},{'sma':[5,'close']}]}]}
        r=self.runscan(cond)
        self.assertEqual(r['matches'],1)

    def test_two_markets_units_and_filters(self):
        self.fill([10.0]*3,market='KRW-BTC',unit=1)
        self.fill([20.0]*4,market='KRW-ETH',unit=3)
        cond={'gt':['high','low']}
        r=self.runscan(cond,markets='eth',units='3')
        self.assertEqual((r['pairs'],r['matches']), (1,4))
        self.assertEqual({x['market'] for x in self.readrows()},{'KRW-ETH'})

    def test_second_db_aggregates_but_not_mix_history(self):
        self.fill([10.0]*3)
        other=self.root/'bithumb_candles.sqlite3'
        with closing(sqlite3.connect(other)) as conn,conn:
            conn.execute('CREATE TABLE candles(market TEXT,unit INT,utc TEXT,kst TEXT,open REAL,high REAL,low REAL,close REAL)')
            conn.executemany('INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)',
                [('KRW-BTC',1,f'2026-11-{i:05d}',f'KST-{i:05d}',20.0,21.0,19.0,20.0) for i in range(4)])
        r=e.scan([self.db,other],self.rulefile({'gt':['high','low']}),self.output)
        self.assertEqual((r['databases'],r['pairs'],r['matches']), (2,2,7))
        self.assertEqual({x['source'] for x in self.readrows()},{'bithumb_candles','upbit_candles'})

    def test_output_overwrite_requires_explicit_option(self):
        self.fill([10.0]*3)
        cond={'gt':['high','low']}
        self.output.write_bytes(b'CUSTOMER_OUTPUT_UNTOUCHED')
        with self.assertRaises(FileExistsError): self.runscan(cond)
        self.assertEqual(self.output.read_bytes(),b'CUSTOMER_OUTPUT_UNTOUCHED')
        self.assertEqual(self.runscan(cond,overwrite=True)['matches'],3)

    def test_database_is_never_output_target(self):
        self.fill([10.0]*3)
        with self.assertRaises(e.RuleError):
            e.scan([self.db],self.rulefile({'gt':['high','low']}),self.db,overwrite=True)

    def test_bad_ohlc_rolls_back_without_csv(self):
        self.fill([10.0,10.0,10.0])
        with closing(sqlite3.connect(self.db)) as conn,conn:
            conn.execute("UPDATE candles SET high=NULL WHERE utc='2026-11-00002'")
        with self.assertRaisesRegex(e.RuleError,'Invalid OHLC'):
            self.runscan({'gt':['high','low']})
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.custom-pattern-*.tmp')),[])

    def test_invalid_rules_unknown_syntax_rejected(self):
        for cond in ({'exec':['close','high']}, {'gt':['close']},
                     {'gt':[{'sma':[0,'close']},'close']},
                     {'gt':[{'bb_upper':[20,float('nan'),'close']},'close']},
                     {'gt':[{'sma':[20,'secret']},'close']},
                     {'any':[]}, {'not':{'not':{'not':{'not':{'not':{'not':{'not':{'eq':['close','close']}}}}}}}}):
            with self.subTest(cond=str(cond)), self.assertRaises(e.RuleError):
                self.rulefile(cond)

    def test_duplicate_json_keys_and_nonfinite_rejected(self):
        for raw in ('{"version":1,"version":1,"rules":[]}',
                    '{"version":1,"rules":[{"id":"a","when":{"gt":["close",NaN]}}]}'):
            self.rules.write_text(raw,encoding='utf-8')
            with self.assertRaises(e.RuleError): e.load_rules(self.rules)

    def test_rule_file_symlink_rejected(self):
        self.rulefile({'gt':['high','low']})
        link=self.root/'rules-link.json'
        try: link.symlink_to(self.rules)
        except (NotImplementedError,OSError): self.skipTest('symlink unavailable')
        with self.assertRaises(e.RuleError): e.load_rules(link)

    def test_rule_file_size_cap(self):
        self.rules.write_bytes(b'x'*(e.MAX_RULE_FILE+1))
        with self.assertRaises(e.RuleError): e.load_rules(self.rules)

    def test_invalid_period_bool_not_accepted(self):
        with self.assertRaises(e.RuleError):
            self.rulefile({'gt':[{'ema':[True,'close']},'close']})

    def test_cli_real_synthetic_db_end_to_end(self):
        self.fill([10.0]*3)
        self.rulefile({'gt':['high','low']})
        code=e.main(['--db',str(self.db),'--rules',str(self.rules),'--output',str(self.output),'--markets','BTC','--units','1'])
        self.assertEqual(code,0)
        self.assertEqual(len(self.readrows()),3)

    def test_constant_threshold_and_cross_up(self):
        self.fill([10.0]*3+[20.0]+[20.0]*2)
        cond={'all':[{'cross_up':['close',{'const':15}]}, {'gt':[{'sma':[2,'close']},{'const':10}]}]}
        self.assertEqual(self.runscan(cond)['matches'],1)
        self.assertEqual(self.readrows()[0]['utc'],'2026-11-00003')

    def test_numeric_threshold_validation(self):
        for threshold in (True,float('inf'),float('nan'),1e15,'1','__import__'):
            with self.subTest(threshold=str(threshold)), self.assertRaises(e.RuleError):
                self.rulefile({'gt':['close',{'const':threshold}]})

    def test_formula_injection_is_escaped_in_csv(self):
        self.fill([10.0]*3)
        with closing(sqlite3.connect(self.db)) as conn,conn:
            conn.execute("UPDATE candles SET kst='=1+1' WHERE utc='2026-11-00002'")
        self.runscan({'gt':['high','low']})
        self.assertEqual(self.readrows()[-1]['kst'],"'=1+1")

    def test_existing_output_survives_failed_overwrite(self):
        self.fill([10.0]*3)
        self.output.write_bytes(b'PREVIOUS_CUSTOMER_REPORT')
        with closing(sqlite3.connect(self.db)) as conn,conn:
            conn.execute("UPDATE candles SET close=NULL WHERE utc='2026-11-00002'")
        with self.assertRaises(e.RuleError):
            self.runscan({'gt':['high','low']},overwrite=True)
        self.assertEqual(self.output.read_bytes(),b'PREVIOUS_CUSTOMER_REPORT')
        self.assertEqual(list(self.root.glob('.custom-pattern-*.tmp')),[])

    def test_invalid_market_filter_rejected(self):
        self.fill([10.0]*3)
        for kw in ('BTC,','BTC;DROP TABLE candles','!'):
            with self.subTest(kw=kw),self.assertRaises(e.RuleError):
                self.runscan({'gt':['high','low']},markets=kw)
        self.assertFalse(self.output.exists())


if __name__=='__main__': unittest.main()
