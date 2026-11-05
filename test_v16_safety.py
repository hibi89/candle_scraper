"""v1.6: verify uniqueness before reuse of a customer's existing database."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import collector


class ExistingSchemaSafetyTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'upbit.sqlite3'
        self.saved = collector.CONFIG['upbit']
        collector.CONFIG['upbit'] = ('https://offline.invalid', self.path)

    def tearDown(self):
        collector.CONFIG['upbit'] = self.saved
        self.folder.cleanup()

    def _create_candles(self, pk='PRIMARY KEY (market,unit,utc)', state=None):
        db = sqlite3.connect(self.path)
        db.execute(f'''CREATE TABLE candles (
            market TEXT, unit INTEGER, utc TEXT, kst TEXT,
            open REAL, high REAL, low REAL, close REAL, volume REAL, trade_value REAL,
            {pk})''' if pk else '''CREATE TABLE candles (
            market TEXT, unit INTEGER, utc TEXT, kst TEXT,
            open REAL, high REAL, low REAL, close REAL, volume REAL, trade_value REAL)''')
        if state is not None:
            db.execute(f'''CREATE TABLE collection_state (
                market TEXT, unit INTEGER, finished INTEGER DEFAULT 0, {state})''')
        db.execute('INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)',
                   ('KRW-BTC',1,'2025-01-01T00:00:00','2025-01-01T09:00:00',1,2,0.5,1.5,3,4.5))
        db.commit(); db.close()

    def test_existing_unconstrained_candles_does_not_modify_data(self):
        self._create_candles(pk='')
        before=self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError,'primary key'):
            collector.db_open('upbit')
        self.assertEqual(before,self.path.read_bytes())

    def test_existing_wrong_order_primary_key_rejected(self):
        self._create_candles(pk='PRIMARY KEY (market,utc,unit)')
        before=self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError,'primary key'):
            collector.db_open('upbit')
        self.assertEqual(before,self.path.read_bytes())

    def test_existing_bad_state_table_rejected(self):
        self._create_candles(state='PRIMARY KEY (market,finished)')
        before=self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError,'collection_state'):
            collector.db_open('upbit')
        self.assertEqual(before,self.path.read_bytes())

    def test_legacy_valid_pk_without_state_can_open(self):
        self._create_candles()
        db=collector.db_open('upbit')
        try:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0],1)
            self.assertIn('collection_state',[row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")])
        finally: db.close()

    def test_created_db_has_expected_pks(self):
        db=collector.db_open('upbit')
        try:
            collector.verify_existing_schema(db)
            self.assertEqual(tuple(r[1] for r in db.execute('PRAGMA table_info(candles)') if r[5]), ('market','unit','utc'))
        finally: db.close()

if __name__ == '__main__': unittest.main()
