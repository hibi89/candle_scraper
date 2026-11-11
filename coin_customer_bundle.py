# -*- coding: utf-8 -*-
"""Package an offline coin-rule scan as a new, integrity-checked customer ZIP.

Pure stdlib; no network, orders or source-database writes. Reuses canonical P2,
P3 HTML report and P4 rule/CSV receipt. Explicitly not a standalone EXE.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
import zipfile

from custom_formula_batch import MAX_DBS, load_formula_batch, scan_batch, _parse_markets, _parse_units
from coin_evidence_receipt import build as build_evidence, save_new as save_evidence, verify as verify_evidence

ARCHIVE_FILES = ("rules.json", "signals.csv", "report.html", "evidence.json", "manifest.json")
MAX_ZIP_BYTES = 512 * 1024 * 1024


def _regular(path: Path, limit: int | None = None) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Symlink inputs are not supported")
    resolved = path.resolve(strict=True)
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode) or (limit is not None and info.st_size > limit):
        raise ValueError("Input must be a bounded regular file")
    return resolved


def create_bundle(db_paths: list[Path], rules: Path, destination: Path, *,
                  markets: str = "all", units: str = "all", last: int = 0,
                  max_matches: int = 500000) -> dict:
    """Build, self-test, and atomically publish a *new* ZIP; never overwrite."""
    if not 1 <= len(db_paths) <= MAX_DBS:
        raise ValueError("Expected 1..8 SQLite databases")
    sources = [_regular(p) for p in db_paths]
    if len(set(sources)) != len(sources):
        raise ValueError("Duplicate source databases")
    rule_path = _regular(rules, 65536)
    output = Path(destination).absolute()
    if output.suffix.lower() != ".zip" or not output.parent.is_dir():
        raise ValueError("Output must be a new ZIP in an existing directory")
    if output.is_symlink() or output.exists():
        raise FileExistsError("Existing customer ZIP must not be overwritten")
    if output in sources or output == rule_path:
        raise ValueError("Output cannot equal a source file")
    compiled = load_formula_batch(rule_path)
    chosen_markets, chosen_units = _parse_markets(markets), _parse_units(units)
    if not isinstance(last, int) or isinstance(last, bool) or last < 0:
        raise ValueError("Invalid last-N window")
    if not isinstance(max_matches, int) or isinstance(max_matches, bool) or not 1 <= max_matches <= 1000000:
        raise ValueError("Invalid match limit")

    # Stage all content outside of the real customer output name.
    temporary_zip = None
    with tempfile.TemporaryDirectory(prefix=".coin-customer-stage-", dir=output.parent) as stage:
        stage = Path(stage)
        csv_path = stage / "signals.csv"
        html_path = stage / "report.html"
        receipt_path = stage / "evidence.json"
        staged_rules = stage / "rules.json"
        staged_rules.write_bytes(rule_path.read_bytes())
        if staged_rules.stat().st_size > 65536:
            raise ValueError("Rule file too large")
        # Rescan the staged rules, not the mutable user-provided path.
        formulas = load_formula_batch(staged_rules)
        if [f.digest for f in formulas] != [f.digest for f in compiled]:
            raise ValueError("Rule changed during staging")
        scanned = scan_batch(sources, csv_path, formulas, units=chosen_units,
                             markets=chosen_markets, last=last,
                             max_matches=max_matches)
        import coin_report  # Existing GitHub P3, fail before publish if absent.
        reported = coin_report.render_csv(csv_path, html_path)
        receipt = build_evidence(csv_path, staged_rules)
        save_evidence(receipt, receipt_path)
        if not verify_evidence(csv_path, staged_rules, receipt_path):
            raise ValueError("Receipt failed after packaging-stage verification")
        if scanned["matches"] != reported["matches"] or scanned["matches"] != receipt["matches"]:
            raise ValueError("Scanner, HTML and receipt disagree on match count")
        manifest = {
            "contract": "coin-customer-bundle.v1",
            "kind": "historical-signals-not-investment-advice",
            "matches": scanned["matches"], "pairs": scanned["pairs"],
            "candles_processed": scanned["candles_processed"],
            "formula_count": len(formulas),
            "csv_sha256": receipt["csv_sha256"],
            "rules_sha256": receipt["rules_sha256"],
            "included": list(ARCHIVE_FILES),
            "limitations": "Synthetic/local checks only; no guaranteed trading execution, performance or ROI",
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, sort_keys=True,
                                                       ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        try:
            with tempfile.NamedTemporaryFile(prefix=".coin-customer-", suffix=".tmp",
                                             dir=output.parent, delete=False) as stream:
                temporary_zip = Path(stream.name)
            with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED,
                                 compresslevel=6, allowZip64=True) as package:
                for name in ARCHIVE_FILES:
                    package.write(stage / name, arcname=name)
            if temporary_zip.stat().st_size > MAX_ZIP_BYTES:
                raise ValueError("Customer package exceeds bounded archive size")
            with zipfile.ZipFile(temporary_zip) as package:
                if set(package.namelist()) != set(ARCHIVE_FILES) or package.testzip() is not None:
                    raise ValueError("Customer ZIP self-check failed")
            # Same-folder hard-link is exclusive even if output is created concurrently.
            os.link(temporary_zip, output)
            return {"status": "CREATED", "archive": str(output),
                    "matches": manifest["matches"], "formula_count": len(formulas),
                    "files": len(ARCHIVE_FILES)}
        finally:
            if temporary_zip is not None:
                temporary_zip.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline read-only coin scan -> validated customer ZIP")
    parser.add_argument("--db", type=Path, action="append", required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markets", default="all")
    parser.add_argument("--units", default="all")
    parser.add_argument("--last", type=int, default=0)
    parser.add_argument("--max-matches", type=int, default=500000)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(create_bundle(args.db, args.rules, args.output,
                  markets=args.markets, units=args.units, last=args.last,
                  max_matches=args.max_matches), ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error, zipfile.BadZipFile) as exc:
        print("BUNDLE HOLD: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
