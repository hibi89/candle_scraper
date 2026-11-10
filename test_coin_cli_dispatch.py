"""Canonical P1/P2 CLI option propagation (mock engines only).

Actual SQL/indicator equivalence is tested separately by test_coin_analyzer.py on full checkout.
"""
from __future__ import annotations

from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import coin_analyzer


class CommandLineDispatch(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.folder=Path(t.name)
        self.input=self.folder/"rule.json"
        self.input.write_text('{"version":1}',encoding="utf-8")
        self.db=self.folder/"data.sqlite3"
        self.out=self.folder/"out.csv"
        self.calls=[]
        single=types.ModuleType("custom_formula_scanner")
        batch=types.ModuleType("custom_formula_batch")
        single.main=lambda args: self.calls.append(("single",args)) or 0
        batch.main=lambda args: self.calls.append(("batch",args)) or 0
        single.load_formula=lambda path: types.SimpleNamespace(name="single")
        batch.load_formula_batch=lambda path: ("first","second")
        self.inject=patch.dict(sys.modules,{"custom_formula_scanner":single,
                                             "custom_formula_batch":batch})
        self.inject.start();self.addCleanup(self.inject.stop)

    def run_cli(self,mode):
        with redirect_stdout(StringIO()):
            return coin_analyzer.main(["--db",str(self.db),mode,str(self.input),
                                       "--output",str(self.out),
                                       "--last","100","--max-matches","50"])

    def test_dispatch_batch_to_p2_main(self):
        self.assertEqual(self.run_cli("--rules"),0)
        name,args=self.calls[0]
        self.assertEqual(name,"batch")
        self.assertIn("--rules",args)
        self.assertNotIn("--rule",args)
        self.assertEqual(args[-2:],["--max-matches","50"])

    def test_dispatch_single_to_p1_main(self):
        self.assertEqual(self.run_cli("--rule"),0)
        name,args=self.calls[0]
        self.assertEqual(name,"single")
        self.assertIn("--rule",args)
        self.assertNotIn("--rules",args)

    def test_validate_batch_without_db_and_output(self):
        with redirect_stdout(StringIO()) as stream:
            rc=coin_analyzer.main(["--rules",str(self.input),"--validate-only"])
        self.assertEqual(rc,0)
        result=json.loads(stream.getvalue())
        self.assertEqual((result["mode"],result["rule_count"]),("batch",2))
        self.assertFalse(result["read_customer_db"])
        self.assertEqual(self.calls,[])

    def test_validate_single_without_db_and_output(self):
        with redirect_stdout(StringIO()) as stream:
            rc=coin_analyzer.main(["--rule",str(self.input),"--validate-only"])
        self.assertEqual(rc,0)
        result=json.loads(stream.getvalue())
        self.assertEqual((result["mode"],result["rule_count"]),("single",1))
        self.assertEqual(self.calls,[])

    def test_both_rules_mutually_exclusive(self):
        with redirect_stderr(StringIO()),self.assertRaises(SystemExit) as err:
            coin_analyzer.main(["--rule",str(self.input),"--rules",str(self.input)])
        self.assertEqual(err.exception.code,2)

    def test_missing_db_and_output_fails_before_dispatch(self):
        with redirect_stderr(StringIO()),self.assertRaises(SystemExit) as err:
            coin_analyzer.main(["--rules",str(self.input)])
        self.assertEqual(err.exception.code,2)
        self.assertEqual(self.calls,[])

    def test_invalid_max_matches_fails_before_scan(self):
        with redirect_stderr(StringIO()),self.assertRaises(SystemExit):
            coin_analyzer.main(["--rules",str(self.input),"--max-matches","0","--validate-only"])
        self.assertEqual(self.calls,[])

    def test_overwrite_explicitly_forwarded(self):
        with redirect_stdout(StringIO()):
            coin_analyzer.main(["--db",str(self.db),"--rules",str(self.input),
                                "--output",str(self.out),"--overwrite"])
        self.assertIn("--overwrite",self.calls[0][1])

if __name__=="__main__":
    unittest.main()
