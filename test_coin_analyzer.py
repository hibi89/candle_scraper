"""Combined customer entry point tests. Real batch SQLite, mocked single dispatch only."""
from __future__ import annotations

from contextlib import closing, redirect_stderr, redirect_stdout
import csv
from io import StringIO
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import coin_analyzer as app


class UnifiedCliTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="coin-unified-")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.db = self.root / "upbit.sqlite3"
        self.rules = self.root / "rules.json"
        self.out = self.root / "out.csv"
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("""CREATE TABLE candles(market TEXT,unit INT,utc TEXT,kst TEXT,
                          open REAL,high REAL,low REAL,close REAL)""")
            con.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)",
                            [("KRW-BTC",1,str(n).zfill(3),str(n).zfill(3),10.,11.,9.,10.)
                             for n in range(4)])
        self.rules.write_text(json.dumps({"version":1,"rules":[
            {"id":"one","when":{"gt":["high","close"]}},
            {"id":"two","when":{"lt":["low","close"]}}
        ]}),encoding="utf-8")

    def test_batch_real_cli_multiple_rules_one_stream(self):
        with redirect_stdout(StringIO()) as buf:
            code = app.main(["--db",str(self.db),"--rules",str(self.rules),
                             "--output",str(self.out),"--markets","BTC","--units","1"])
        self.assertEqual(code,0)
        summary=json.loads(buf.getvalue())
        self.assertEqual(summary["candles_processed"],4)
        self.assertEqual(summary["matches"],8)
        with self.out.open(encoding="utf-8-sig",newline="") as f:
            self.assertEqual({row["rule_id"] for row in csv.DictReader(f)},{"one","two"})

    def test_batch_validate_only_no_database_or_csv(self):
        with redirect_stdout(StringIO()) as buf:
            rc=app.main(["--rules",str(self.rules),"--validate-only"])
        self.assertEqual(rc,0)
        result=json.loads(buf.getvalue())
        self.assertEqual(result["rule_count"],2)
        self.assertFalse(result["read_customer_db"])
        self.assertFalse(result["wrote_csv"])
        self.assertFalse(self.out.exists())

    def test_batch_cap_rolls_back_new_csv(self):
        with redirect_stderr(StringIO()):
            rc=app.main(["--db",str(self.db),"--rules",str(self.rules),
                         "--output",str(self.out),"--max-matches","5"])
        self.assertEqual(rc,2)
        self.assertFalse(self.out.exists())

    def test_existing_csv_preserved_by_default(self):
        self.out.write_text("ORIGINAL",encoding="utf-8")
        with redirect_stderr(StringIO()):
            rc=app.main(["--db",str(self.db),"--rules",str(self.rules),"--output",str(self.out)])
        self.assertEqual(rc,2)
        self.assertEqual(self.out.read_text(encoding="utf-8"),"ORIGINAL")

    def test_last_per_pair_and_filters_forwarded(self):
        with redirect_stdout(StringIO()):
            rc=app.main(["--db",str(self.db),"--rules",str(self.rules),
                         "--output",str(self.out),"--last","1"])
        self.assertEqual(rc,0)
        with self.out.open(encoding="utf-8-sig",newline="") as f:
            self.assertEqual(len(list(csv.DictReader(f))),2)

    def test_single_legacy_contract_dispatch_is_preserved(self):
        commands=[]
        fake=types.ModuleType("custom_formula_scanner")
        fake.main=lambda argv: commands.append(argv) or 0
        fake.load_formula=lambda path: types.SimpleNamespace(name="single")
        with patch.dict(sys.modules,{"custom_formula_scanner":fake}):
            with redirect_stdout(StringIO()):
                rc=app.main(["--db",str(self.db),"--rule",str(self.rules),
                             "--output",str(self.out),"--max-matches","7"])
                validate=app.main(["--rule",str(self.rules),"--validate-only"])
        self.assertEqual((rc,validate),(0,0))
        self.assertIn("--rule",commands[0])
        self.assertNotIn("--rules",commands[0])
        self.assertEqual(commands[0][-2:],["--max-matches","7"])

    def test_invalid_rule_does_not_touch_db_or_output(self):
        self.rules.write_text('{"version":1,"rules":[]}',encoding="utf-8")
        with redirect_stderr(StringIO()):
            rc=app.main(["--rules",str(self.rules),"--validate-only"])
        self.assertEqual(rc,2)
        self.assertFalse(self.out.exists())

    def test_input_type_is_mutually_exclusive(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as cm:
            app.main(["--rule",str(self.rules),"--rules",str(self.rules),"--validate-only"])
        self.assertEqual(cm.exception.code,2)

    def test_invalid_output_cap_rejected(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as cm:
            app.main(["--rules",str(self.rules),"--max-matches","0","--validate-only"])
        self.assertEqual(cm.exception.code,2)

    def test_missing_db_or_output_refused(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as cm:
            app.main(["--rules",str(self.rules)])
        self.assertEqual(cm.exception.code,2)


if __name__ == "__main__":
    unittest.main()
