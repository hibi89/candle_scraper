"""Offline builder tests. Synthetic rules only; no exchange or customer DB."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import custom_formula_builder as builder
import custom_formula_scanner as scanner
import custom_formula_batch as batch
from test_custom_formula_scanner import fixture


class BuilderTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_every_template_compiles_and_runs(self):
        db = fixture(self.root/"sample.sqlite3")
        for mode in builder.MODES:
            with self.subTest(mode=mode):
                rule = builder.build_formula("Korean rule 한글", mode)
                self.assertEqual(scanner.compile_formula(rule).name,"Korean rule 한글")
                target = self.root / (mode + ".json")
                builder.save_new_rule(rule, target)
                actual = batch.load_formula_batch(target)
                self.assertEqual(len(actual), 1)
                report = self.root/(mode + ".csv")
                stats = batch.scan_batch([db], report, actual)
                self.assertEqual(stats["candles_processed"],8)
                self.assertTrue(report.is_file())

    def test_parameterized_ema_matches_p1_rule_structure(self):
        rule=builder.build_formula("EMA 전략", "ema_cross", fast=7, slow=14)
        legs=rule["when"]["cross_up"]
        self.assertEqual((legs[0]["period"],legs[1]["period"]),(7,14))
        self.assertEqual(legs[0]["indicator"],"ema")

    def test_invalid_templates_do_not_write(self):
        for params in [dict(name="x", mode="sma_cross", fast=30, slow=20),
                       dict(name="x", mode="sma_cross", fast=True),
                       dict(name="x", mode="ema_cross", slow=561),
                       dict(name="=HYPERLINK()", mode="sma_cross"),
                       dict(name="x", mode="bb_upper_breakout", sigma=0),
                       dict(name="x", mode="bb_lower_recover", sigma=float("nan")),
                       dict(name="x", mode="close_above", threshold=float("inf")),
                       dict(name="x", mode="close_above", threshold=-1),
                       dict(name="x", mode="os.system")]:
            with self.subTest(params=params),self.assertRaises(ValueError):builder.build_formula(**params)
        self.assertEqual(list(self.root.iterdir()),[])

    def test_exclusive_output_never_replaces_existing(self):
        path=self.root/"rule.json"
        path.write_text("OWNER_ORIGINAL",encoding="utf-8")
        with self.assertRaises(FileExistsError):
            builder.save_new_rule(builder.build_formula("Sample","sma_cross"),path)
        self.assertEqual(path.read_text(encoding="utf-8"),"OWNER_ORIGINAL")

    def test_non_json_target_denied(self):
        with self.assertRaises(ValueError):
            builder.save_new_rule(builder.build_formula("Sample","sma_cross"),self.root/"old.sqlite3")
        self.assertEqual(list(self.root.iterdir()),[])

    def test_cli_created_rule_and_failure_exit(self):
        target=self.root/"ema.json"
        argv=["--mode","ema_cross","--name","Custom","--fast","3","--slow","8","--output",str(target)]
        self.assertEqual(builder.main(argv),0)
        self.assertEqual(builder.main(argv),2)
        self.assertEqual(batch.load_formula_batch(target)[0].name,"Custom")

    def test_interactive_template_uses_safe_generator(self):
        with patch("builtins.input",side_effect=["1","내 수식","3","8",str(self.root/"new.json")]):
            self.assertEqual(builder.main(["--interactive"]),0)
        self.assertEqual(json.loads((self.root/"new.json").read_text())["name"],"내 수식")


if __name__ == "__main__":unittest.main()
