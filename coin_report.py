# -*- coding: utf-8 -*-
"""Static, offline HTML summary for the existing coin analyzer CSV contracts.

Reads already-generated customer-selected CSV; publishes a new report without network,
executing formula contents or modifying source CSV/SQLite. Standard library only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import html
import json
import math
import os
from pathlib import Path
import tempfile

MAX_INPUT_BYTES = 256 * 1024 * 1024
MAX_RECORDS = 1_000_000
MAX_GROUPS = 20_000
PREVIEW_ROWS = 120
MAX_CELL = 4096
BATCH = ("source", "market", "unit", "utc", "kst", "close", "rule_id")
SINGLE = ("exchange", "market", "unit", "utc", "kst", "close", "formula", "formula_sha256")
CSS = """
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#101720;color:#e6eef6}
*{box-sizing:border-box}body{max-width:1200px;margin:auto;padding:28px}
h1{letter-spacing:-.04em}p{line-height:1.5;color:#a8b7c8}
header{padding-bottom:22px;border-bottom:1px solid #354352}header small{color:#7be2cc}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:22px 0}
.card,.panel{background:#182533;border:1px solid #354352;border-radius:14px;padding:18px}
.card strong{display:block;font-size:29px;margin:5px 0}.tag{font-size:12px;color:#7be2cc}
.panel{margin-top:18px;overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #344454;white-space:nowrap}
th{color:#a8b7c8}code{color:#8ee5d4}
.bar{height:9px;background:#334353;border-radius:8px;overflow:hidden;min-width:120px}
.bar span{display:block;height:100%;background:#43bca8}
footer{margin-top:24px;color:#a8b7c8;font-size:12px}
"""


def _safe(value: object) -> str:
    return html.escape(str(value), quote=True)


def _publish(target: Path, body: str, overwrite: bool) -> None:
    target = target.absolute()
    if target.suffix.lower() not in (".html", ".htm") or not target.parent.is_dir():
        raise ValueError("Output must be .html in an existing folder")
    if target.exists() and not overwrite:
        raise FileExistsError("HTML output exists; --overwrite required")
    fd, name = tempfile.mkstemp(prefix=".coin-report-", suffix=".tmp", dir=target.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temp, target)
        else:
            os.link(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def render_csv(csv_path: Path, output: Path, *, overwrite: bool = False) -> dict:
    source_argument = Path(csv_path)
    if source_argument.is_symlink():
        raise ValueError("Symlink CSV source is not permitted")
    csv_path = source_argument.resolve(strict=True)
    output = Path(output).absolute()
    if (not csv_path.is_file() or csv_path.stat().st_size > MAX_INPUT_BYTES):
        raise ValueError("Input must be a bounded regular CSV")
    if output.resolve() == csv_path:
        raise ValueError("HTML output cannot replace source CSV")
    if output.exists() and not overwrite:
        raise FileExistsError("Existing report preserved")
    if output.suffix.lower() not in (".html", ".htm") or not output.parent.is_dir():
        raise ValueError("Invalid HTML destination")
    preview = []
    rules, markets, units = Counter(), Counter(), Counter()
    records = 0
    previous_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(MAX_CELL)
        with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = tuple(reader.fieldnames or ())
            if fields == BATCH:
                kind = "batch"
                rule_field, source_field = "rule_id", "source"
            elif fields == SINGLE:
                kind = "single"
                rule_field, source_field = "formula", "exchange"
            else:
                raise ValueError("Unsupported coin analyzer CSV header")
            for row in reader:
                records += 1
                if records > MAX_RECORDS or None in row or any(v is None for v in row.values()):
                    raise ValueError("CSV row count or columns invalid")
                if any(len(v) > MAX_CELL for v in row.values()):
                    raise ValueError("CSV field exceeds bounded length")
                try:
                    price = float(row["close"])
                except (ValueError, OverflowError):
                    raise ValueError("CSV contains invalid close") from None
                if not math.isfinite(price) or price <= 0:
                    raise ValueError("CSV contains invalid close")
                key = row[rule_field]
                if not key or not row["market"] or not row["unit"]:
                    raise ValueError("CSV missing required grouping field")
                if len(rules) >= MAX_GROUPS and key not in rules:
                    raise ValueError("Too many distinct rule groups")
                rules[key] += 1
                markets[row["market"]] += 1
                units[row["unit"]] += 1
                if len(preview) < PREVIEW_ROWS:
                    preview.append((row[source_field],row["market"],row["unit"],
                                    row["utc"],row["kst"],row["close"],key))
    finally:
        csv.field_size_limit(previous_limit)

    def summary_row(label, count):
        width = (count/records*100) if records else 0
        return ("<tr><td>" + _safe(label) + "</td><td>" + str(count) +
                "</td><td><div class='bar'><span style='width:" +
                ("%.2f" % width) + "%'></span></div></td></tr>")

    def panel(title, counter):
        rows = "".join(summary_row(name,count) for name,count in counter.most_common(30))
        if not rows:
            rows = "<tr><td colspan='3'>No matches</td></tr>"
        return ("<section class='panel'><h2>" + _safe(title) +
                "</h2><table><thead><tr><th>Group</th><th>Hits</th><th>Share</th>"
                "</tr></thead><tbody>" + rows + "</tbody></table></section>")

    cells = "".join("<tr>"+"".join("<td>"+_safe(cell)+"</td>" for cell in row)+"</tr>"
                    for row in preview)
    if not cells:
        cells = "<tr><td colspan='7'>No matches; source CSV may contain only a header.</td></tr>"
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; "
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
        "<title>Coin Analyzer · Offline Report</title><style>" + CSS +
        "</style></head><body><header><small>COIN ANALYZER · OFFLINE RESEARCH</small>"
        "<h1>Custom signal scan</h1><p>Catalog of historical matches from an explicit CSV; "
        "no trading simulation, earnings promise, network calls or source DB access.</p>"
        "</header><div class='cards'><div class='card'><span class='tag'>MATCHES</span>"
        "<strong>" + str(records) + "</strong>recorded signals</div>"
        "<div class='card'><span class='tag'>RULES</span><strong>" + str(len(rules)) +
        "</strong>distinct formulas</div><div class='card'><span class='tag'>MARKETS</span>"
        "<strong>" + str(len(markets)) + "</strong>distinct markets</div>"
        "<div class='card'><span class='tag'>SOURCE CONTRACT</span><strong>" +
        _safe(kind.upper()) + "</strong>read-only result</div></div>"
        + panel("Matches by rule",rules)+panel("Matches by market",markets)
        + panel("Matches by timeframe",units)
        + "<section class='panel'><h2>First " + str(len(preview)) +
        " events (in CSV order)</h2><table><thead><tr>" +
        "".join("<th>"+_safe(c)+"</th>" for c in
                ("Source","Market","Unit","UTC","KST","Close","Rule")) +
        "</tr></thead><tbody>" + cells + "</tbody></table></section>"
        "<footer>Preview is bounded to 120 records. Totals include up to 1,000,000 rows. "
        "Candles do not establish live fill, profitability, or chart parity. "
        "No network access. Retain source CSV for complete results.</footer></body></html>"
    )
    _publish(output,page,overwrite)
    return {"status":"CREATED_OFFLINE_REPORT","mode":kind,"matches":records,
            "rule_count":len(rules),"market_count":len(markets),
            "preview_count":len(preview),"contains_all_rows":records<=PREVIEW_ROWS,
            "source_csv_modified":False,"network_requests":0}


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Static offline coin scan CSV -> HTML report")
    parser.add_argument("--csv",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--overwrite",action="store_true")
    args=parser.parse_args(argv)
    try:
        result=render_csv(args.csv,args.output,overwrite=args.overwrite)
    except (OSError,ValueError,csv.Error) as exc:
        print("REPORT_FAILED: "+str(exc))
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
