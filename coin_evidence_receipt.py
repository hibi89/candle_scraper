# -*- coding: utf-8 -*-
"""Offline SHA256 receipt for P1/P2 rule-to-signal CSV provenance (not a signature)."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

from custom_formula_batch import load_formula_batch
from custom_formula_scanner import OUTPUT_COLUMNS, UNITS, MARKET

MAX_CSV_BYTES = 512 * 1024 * 1024
MAX_ROWS = 1_000_000
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _info(path: Path, limit: int) -> tuple:
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Symbolic-link input rejected")
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
        raise ValueError("Input must be a bounded regular file")
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build(csv_path: Path, rules_path: Path) -> dict:
    """Validate full rows and formula hash against the supplied canonical P1/P2 rule."""
    csv_path, rules_path = Path(csv_path), Path(rules_path)
    if csv_path.suffix.lower() != ".csv" or rules_path.suffix.lower() != ".json":
        raise ValueError("Expected a P1/P2 .csv and corresponding .json rules")
    csv_before = _info(csv_path, MAX_CSV_BYTES)
    rule_before = _info(rules_path, 65536)
    compiled = load_formula_batch(rules_path)
    expected = {f.name: f.digest for f in compiled}
    if len(expected) != len(compiled):
        raise ValueError("Ambiguous rule names")
    counts: Counter[str] = Counter()
    count = 0
    old_limit = csv.field_size_limit(4096)
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if tuple(reader.fieldnames or ()) != OUTPUT_COLUMNS:
                raise ValueError("Unexpected custom-formula CSV columns")
            for row in reader:
                count += 1
                if count > MAX_ROWS or None in row or any(v is None for v in row.values()):
                    raise ValueError("CSV row count or field mismatch")
                name, digest = row["formula"], row["formula_sha256"]
                if name not in expected or not SHA256.fullmatch(digest) or expected[name] != digest:
                    raise ValueError("Formula identity mismatch; receipt withheld")
                if not MARKET.fullmatch(row["market"]):
                    raise ValueError("Invalid market in CSV")
                try:
                    unit = int(row["unit"])
                    close = float(row["close"])
                except ValueError as exc:
                    raise ValueError("Invalid numeric CSV field") from exc
                if unit not in UNITS or not math.isfinite(close) or close <= 0:
                    raise ValueError("Invalid candle unit or close")
                if not row["utc"] or not row["kst"] or len(row["utc"]) > 64 or len(row["kst"]) > 64:
                    raise ValueError("Invalid candle timestamps")
                counts[name] += 1
    finally:
        csv.field_size_limit(old_limit)
    if _info(csv_path, MAX_CSV_BYTES) != csv_before or _info(rules_path, 65536) != rule_before:
        raise ValueError("Input changed while scanning")
    csv_sha, rules_sha = _digest(csv_path), _digest(rules_path)
    if _info(csv_path, MAX_CSV_BYTES) != csv_before or _info(rules_path, 65536) != rule_before:
        raise ValueError("Input changed while hashing")
    return {
        "contract": "coin-formula-evidence.v1",
        "csv_sha256": csv_sha,
        "rules_sha256": rules_sha,
        "matches": count,
        "rules": [{"name": f.name, "sha256": f.digest, "matches": counts[f.name]} for f in compiled],
        "verification": "HASHES_AND_ROW_RULE_BINDING_ONLY_NOT_A_SIGNATURE_OR_TRADING_RESULT",
    }


def save_new(receipt: dict, output: Path) -> Path:
    output = Path(output).absolute()
    if output.suffix.lower() != ".json" or output.is_symlink() or not output.parent.is_dir():
        raise ValueError("Output must be a new regular .json file in an existing folder")
    if output.exists():
        raise FileExistsError("Existing receipt preserved; choose a new filename")
    data = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, name = tempfile.mkstemp(prefix=".coin-evidence-", suffix=".tmp", dir=output.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    return output


def verify(csv_path: Path, rules_path: Path, receipt_path: Path) -> bool:
    receipt_path = Path(receipt_path)
    if receipt_path.is_symlink() or _info(receipt_path, 65536)[2] == 0:
        raise ValueError("Invalid receipt file")
    stored = json.loads(receipt_path.read_text(encoding="utf-8"))
    if type(stored) is not dict or set(stored) != {"contract", "csv_sha256", "rules_sha256", "matches", "rules", "verification"}:
        raise ValueError("Invalid receipt contract")
    return stored == build(csv_path, rules_path)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Offline formula CSV hash & rule-binding receipt")
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--rules", required=True, type=Path)
    dest = p.add_mutually_exclusive_group(required=True)
    dest.add_argument("--receipt", type=Path, help="Create a new JSON receipt")
    dest.add_argument("--verify", type=Path, help="Verify an existing receipt")
    args = p.parse_args(argv)
    try:
        if args.verify is not None:
            if not verify(args.csv, args.rules, args.verify):
                raise ValueError("Receipt no longer matches CSV and rule files")
            print("VERIFIED: match to current files; not an authenticated signature")
        else:
            receipt = build(args.csv, args.rules)
            save_new(receipt, args.receipt)
            print(json.dumps({"status": "CREATED", "matches": receipt["matches"],
                              "rules": len(receipt["rules"]), "csv_sha256": receipt["csv_sha256"]}, sort_keys=True))
    except (OSError, ValueError, UnicodeError, csv.Error, json.JSONDecodeError) as exc:
        print("EVIDENCE HOLD: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
