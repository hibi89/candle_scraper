# -*- coding: utf-8 -*-
"""Causal, read-only forward *signal study*, not a trading/backtest claim.

Consumes the original P1/P2 signals.csv and a frozen copy of source candles.
Only future candles after each completed signal bar contribute to the outcome.
Pure Python stdlib, Python >=3.11, no network or exchange calls.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import os
import re
import sqlite3
import stat
import sys
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median

FIELDS = ("exchange", "market", "unit", "utc", "kst", "close", "formula", "formula_sha256")
OUT_FIELDS = ("exchange", "market", "unit", "signal_utc", "formula", "formula_sha256", "signal_close",
              "entry_utc", "exit_utc", "entry_open", "exit_close", "gross_pct", "net_pct", "status")
REGION = re.compile(r"KRW-[A-Z0-9]+\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
ISO = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\Z")
MAX_SIGNALS = 100_000
MAX_CANDLES = 30_000_000
MAX_CSV = 128 * 1024 * 1024
MINUTES = frozenset((1, 3, 5, 10, 15, 30, 60, 240))


class StudyError(ValueError):
    """Input/consistency errors prevent any result from publishing."""


def _protected_file(path: Path, maximum: int | None = None) -> Path:
    absolute = path.expanduser().absolute()
    for part in (absolute, *absolute.parents):
        if part.is_symlink():
            raise StudyError("linked source path is not permitted")
    try:
        info = absolute.stat()
    except OSError as exc:
        raise StudyError("missing source file") from exc
    if not stat.S_ISREG(info.st_mode) or (maximum is not None and info.st_size > maximum):
        raise StudyError("source is not a bounded regular file")
    return absolute


def _utc(text: str) -> datetime:
    if not isinstance(text, str) or not ISO.fullmatch(text):
        raise StudyError("invalid UTC timestamp")
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StudyError("unparseable UTC timestamp") from exc
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


def _finite(text: object, *, positive: bool = False) -> float:
    try:
        if isinstance(text, bool) or text is None or text == "":
            raise ValueError()
        n = float(text)
    except (ValueError, TypeError, OverflowError) as exc:
        raise StudyError("non-numeric price or fee") from exc
    if not math.isfinite(n) or (positive and n <= 0):
        raise StudyError("invalid non-finite or non-positive price")
    return n


def _exchange(path: Path) -> str:
    name = path.stem.lower()
    return "upbit" if "upbit" in name else "bithumb" if "bithumb" in name else "local"


def _signals(path: Path) -> tuple[dict, int, str]:
    original = _protected_file(path, MAX_CSV)
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    groups: dict[tuple[str, str, int], dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    seen = set()
    total = 0
    with original.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise StudyError("signals CSV must use the original eight-column P1/P2 contract")
        for row in reader:
            total += 1
            if total > MAX_SIGNALS:
                raise StudyError("signal count exceeds configured safe cap")
            if None in row or any(not isinstance(row[k], str) for k in FIELDS):
                raise StudyError("malformed CSV row")
            ex, market, name, digest_id = (row[k] for k in ("exchange", "market", "formula", "formula_sha256"))
            if ex not in ("upbit", "bithumb", "local") or not REGION.fullmatch(market):
                raise StudyError("invalid exchange/market")
            if not name or len(name) > 60 or name.startswith(("=", "+", "-", "@")) or any(ord(c) < 32 for c in name):
                raise StudyError("unsafe formula name")
            if not DIGEST.fullmatch(digest_id):
                raise StudyError("invalid rule SHA-256")
            try:
                unit = int(row["unit"])
            except (ValueError, TypeError) as exc:
                raise StudyError("invalid timeframe") from exc
            if unit not in MINUTES or row["unit"] != str(unit):
                raise StudyError("unsupported timeframe")
            _utc(row["utc"])
            _utc(row["kst"])
            _finite(row["close"], positive=True)
            key = (ex, market, unit, row["utc"], name, digest_id)
            if key in seen:
                raise StudyError("duplicate signal row")
            seen.add(key)
            groups[ex, market, unit][row["utc"]].append(row)
    return groups, total, digest


def _readonly(path: Path) -> sqlite3.Connection:
    for suffix in ("-wal", "-shm"):
        if Path(str(path) + suffix).exists():
            raise StudyError("active/uncleared WAL or SHM: use a quiescent private snapshot copy")
    # Immutable mode does not create sidecar journals; must only use offline stable copies.
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=15)
    try:
        connection.execute("PRAGMA query_only=ON")
        names = {r[1] for r in connection.execute("PRAGMA table_info(candles)")}
        if not {"market", "unit", "utc", "kst", "open", "high", "low", "close"}.issubset(names):
            raise StudyError("incompatible candle schema")
        return connection
    except BaseException:
        connection.close()
        raise


def _bar(values: tuple, prior_time: datetime | None, unit: int) -> tuple[dict, datetime, bool]:
    utc, kst, opn, high, low, close = values
    now = _utc(utc)
    _utc(kst)
    if prior_time is not None and now <= prior_time:
        raise StudyError("duplicate or non-increasing UTC candles")
    prices = [_finite(x, positive=True) for x in (opn, high, low, close)]
    opn, high, low, close = prices
    if low > min(opn, close) or high < max(opn, close) or low > high:
        raise StudyError("inconsistent OHLC")
    gap = prior_time is not None and now - prior_time != timedelta(minutes=unit)
    return {"utc": utc, "kst": kst, "open": opn, "high": high, "low": low, "close": close}, now, gap


def _result(item: dict, status: str, entry: dict | None, exit_bar: dict | None, fee: float, slip: float) -> dict:
    ex, market, unit, signal = item["key"]
    row = {"exchange": ex, "market": market, "unit": unit, "signal_utc": signal,
           "formula": item["formula"], "formula_sha256": item["digest"],
           "signal_close": item["signal_close"], "entry_utc": entry["utc"] if entry else "",
           "exit_utc": exit_bar["utc"] if exit_bar else "", "entry_open": entry["open"] if entry else "",
           "exit_close": exit_bar["close"] if exit_bar else "", "gross_pct": "", "net_pct": "", "status": status}
    if status == "COMPLETE":
        buy = entry["open"] * (1 + slip / 10000) * (1 + fee / 10000)
        sell = exit_bar["close"] * (1 - slip / 10000) * (1 - fee / 10000)
        if buy <= 0 or sell <= 0:
            raise StudyError("invalid effective prices")
        row["gross_pct"] = round((exit_bar["close"] / entry["open"] - 1) * 100, 8)
        row["net_pct"] = round((sell / buy - 1) * 100, 8)
    return row


def _metrics(rows: list[dict], split: str | None) -> dict:
    def stats(items):
        finished = [r for r in items if r["status"] == "COMPLETE"]
        vals = [r["net_pct"] for r in finished]
        return {"signals": len(items), "complete": len(vals), "censored_eof": sum(r["status"] == "CENSORED_EOF" for r in items),
                "censored_gap": sum(r["status"] == "CENSORED_GAP" for r in items),
                "mean_net_pct": round(mean(vals), 8) if vals else None,
                "median_net_pct": round(median(vals), 8) if vals else None,
                "win_rate_pct": round(100 * sum(v > 0 for v in vals) / len(vals), 4) if vals else None,
                "min_net_pct": min(vals) if vals else None,
                "max_net_pct": max(vals) if vals else None}
    groups = defaultdict(list)
    for item in rows:
        groups[(item["exchange"], item["market"], item["unit"], item["formula"], item["formula_sha256"])].append(item)
    return {"overall": stats(rows), "by_rule_market": [{"exchange": k[0], "market": k[1], "unit": k[2],
             "formula": k[3], "formula_sha256": k[4], **stats(v)} for k, v in sorted(groups.items())],
            "pre_cutoff": stats([r for r in rows if r["signal_utc"] < split]) if split else None,
            "post_cutoff": stats([r for r in rows if r["signal_utc"] >= split]) if split else None}


def _render_html(summary: dict) -> str:
    metrics = summary["metrics"]["overall"]
    cells = "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>" for k,v in metrics.items())
    details = "".join("<tr><td>" + "</td><td>".join(html.escape(str(row[k])) for k in
                       ("exchange", "market", "unit", "formula", "signals", "complete", "censored_gap", "censored_eof", "win_rate_pct", "mean_net_pct")) + "</td></tr>"
                       for row in summary["metrics"]["by_rule_market"])
    return ("<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'\">"
            "<title>Coin signal forward study</title><style>body{font:15px/1.55 system-ui,sans-serif;max-width:1080px;margin:25px auto;padding:0 16px;background:#111923;color:#f1f6fd}"
            "h1{font-size:28px}p{color:#bccbe0}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{text-align:left;padding:8px;border-bottom:1px solid #425163}"
            "article{padding:18px;background:#1c2938;border-radius:12px;overflow:auto}</style></head><body><h1>시그널 사후 관측 연구</h1>"
            "<p>신호 다음 봉 시가 진입, 신호 후 H번째 봉 종가 청산. 각 거래 비용은 매수·매도 양쪽 반영합니다.</p>"
            "<p><strong>실제 거래 성과 또는 투자 권유가 아닙니다.</strong> 신호별 사건 연구로 중복 신호/체결/유동성/생존편향이 반영되지 않습니다."
            " EOF·캔들 누락 신호는 수익률 집계에서 제외하고 별도 표시합니다.</p><article><h2>전체 요약</h2><table>" + cells +
            "</table></article><article><h2>수식·마켓별 관측</h2><table><tr><th>거래소</th><th>마켓</th><th>분봉</th><th>수식</th>"
            "<th>신호</th><th>완료</th><th>캔들 누락</th><th>미래 부족</th><th>순수익 양수 비율%</th><th>평균 순변화%</th></tr>"
            + details + "</table></article><p>입력 CSV SHA-256: " + summary["signal_csv_sha256"] +
            ". 비용: 매수·매도 각각 fee=" + str(summary["fee_bps_per_side"]) + "bps / slip=" + str(summary["slippage_bps_per_side"]) +
            "bps. 가격 근거: 수신된 로컬 OHLC, 교환소 체결 보장 없음.</p></body></html>\n")


def study(dbs: list[Path], signals: Path, out_dir: Path, *, horizon=5, fee_bps=5., slippage_bps=5.,
          split_utc=None, max_candles=MAX_CANDLES) -> dict:
    if type(horizon) is not int or not 1 <= horizon <= 240:
        raise StudyError("horizon must be 1..240 future candles")
    if type(max_candles) is not int or not 1 <= max_candles <= MAX_CANDLES:
        raise StudyError("invalid global candle limit")
    fee, slip = _finite(fee_bps), _finite(slippage_bps)
    if not (0 <= fee <= 1000 and 0 <= slip <= 1000):
        raise StudyError("fee/slippage must be 0..1000 bps per side")
    cutoff = _utc(split_utc).isoformat() if split_utc else None
    if split_utc and not (len(split_utc) >= 19 and "T" in split_utc):
        raise StudyError("split UTC must use ISO T format")
    if not 1 <= len(dbs) <= 8:
        raise StudyError("require 1..8 source DB snapshots")
    files = [_protected_file(Path(d)) for d in dbs]
    exchanges = [_exchange(f) for f in files]
    if len(set(exchanges)) != len(exchanges):
        raise StudyError("ambiguous duplicate exchange: keep one frozen DB per exchange")
    groups, signal_count, signal_hash = _signals(Path(signals))
    selected = set(groups)
    if any(k[0] not in exchanges for k in selected):
        raise StudyError("signal exchange has no unambiguous source database")
    csv_source = _protected_file(Path(signals), MAX_CSV)
    target = out_dir.expanduser().absolute()
    for part in (target, *target.parents):
        if part.is_symlink():
            raise StudyError("linked output directory not allowed")
    if not target.parent.is_dir() or target.exists() or target in files or target == csv_source or any(target in src.parents for src in files):
        raise StudyError("output must be a new independent folder")
    rows = []
    visited = set()
    processed = 0
    for file, exchange in zip(files, exchanges):
        keys = sorted((m, u) for e,m,u in selected if e == exchange)
        if not keys:
            continue
        with closing(_readonly(file)) as db:
            for market, unit in keys:
                pending = []
                events = groups[exchange, market, unit]
                found = set()
                previous_time = None
                for idx, candle in enumerate(db.execute("SELECT utc,kst,open,high,low,close FROM candles WHERE market=? AND unit=? ORDER BY utc ASC", (market,unit))):
                    processed += 1
                    if processed > max_candles:
                        raise StudyError("candle safety cap reached before publishing")
                    bar, now, gap = _bar(candle, previous_time, unit)
                    previous_time = now
                    if gap:
                        for event in pending:
                            rows.append(_result(event, "CENSORED_GAP", event.get("entry"), None, fee, slip))
                        pending = []
                    remaining = []
                    for event in pending:
                        if event["index"] + 1 == idx:
                            event["entry"] = bar
                        if event["index"] + horizon == idx:
                            rows.append(_result(event, "COMPLETE", event["entry"], bar, fee, slip))
                        else:
                            remaining.append(event)
                    pending = remaining
                    for event in events.get(bar["utc"], []):
                        expected = _finite(event["close"], positive=True)
                        if not math.isclose(expected, bar["close"], rel_tol=1e-10, abs_tol=1e-9):
                            raise StudyError("signal close differs from source candle; possible mismatched database")
                        if event["kst"] != bar["kst"]:
                            raise StudyError("signal KST differs from source candle")
                        pending.append({"key": (exchange,market,unit,bar["utc"]), "formula":event["formula"],
                                        "digest":event["formula_sha256"], "signal_close":expected, "index":idx})
                        found.add((bar["utc"],event["formula"],event["formula_sha256"]))
                for event in pending:
                    rows.append(_result(event, "CENSORED_EOF", event.get("entry"), None, fee, slip))
                required = {(t,ev["formula"],ev["formula_sha256"]) for t,records in events.items() for ev in records}
                if found != required:
                    raise StudyError("some input signals are absent from the selected source DB")
                visited.add((exchange, market, unit))
    if visited != selected or len(rows) != signal_count:
        raise StudyError("signal/source cardinality mismatch; refuse partial results")
    rows.sort(key=lambda r:(r["exchange"],r["market"],r["unit"],r["signal_utc"],r["formula"],r["formula_sha256"]))
    # Compare by parsed datetimes, never lexical offsets, when time split is enabled.
    if cutoff:
        for r in rows:
            r["split_group"] = "post" if _utc(r["signal_utc"]) >= _utc(split_utc) else "pre"
        pre = [r for r in rows if r["split_group"] == "pre"]
        post = [r for r in rows if r["split_group"] == "post"]
    else:
        pre = post = None
    metrics = _metrics(rows, None)
    if cutoff:
        def m(items):
            v = _metrics(items, None)["overall"]
            return v
        metrics["pre_cutoff"] = m(pre)
        metrics["post_cutoff"] = m(post)
    summary = {"schema": "coin-forward-study/v1", "basis": "retrospective_signal_event_study_not_portfolio_backtest",
               "horizon_bars_after_signal": horizon, "entry": "next_bar_open", "exit": "signal_plus_H_bar_close",
               "fee_bps_per_side": fee, "slippage_bps_per_side": slip,
               "split_utc": split_utc, "split_claim": "chronological_partition_only_not_independent_out_of_sample_validation",
               "signal_csv_sha256": signal_hash, "source_db_count": len(files),
               "candles_read": processed, "signal_count": signal_count, "metrics": metrics,
               "warnings": ["Overlapping events are not independent trades; cannot compound net returns.",
                            "Only completed source candles assumed; interrupted live DBs are rejected by WAL/SHM check.",
                            "Retrospective event results are not verified execution, liquidity, price fill or profitability."]}
    target.mkdir(mode=0o700)
    try:
        with (target / "events.csv").open("x", encoding="utf-8-sig", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=OUT_FIELDS)
            writer.writeheader()
            for item in rows:
                writer.writerow({name:item[name] for name in OUT_FIELDS})
        (target / "summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (target / "report.html").write_text(_render_html(summary),encoding="utf-8")
        (target / "manifest.json").write_text(json.dumps({"schema":"coin-forward-study-manifest/v1", "sha256":{
            name: hashlib.sha256((target / name).read_bytes()).hexdigest() for name in ("events.csv","summary.json","report.html")}},indent=2,sort_keys=True)+"\n",encoding="utf-8")
    except BaseException:
        for name in ("events.csv","summary.json","report.html","manifest.json"):
            (target / name).unlink(missing_ok=True)
        target.rmdir()
        raise
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline causal signal event study (not trading backtest)")
    parser.add_argument("--db", action="append", type=Path, required=True)
    parser.add_argument("--signals", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--fee-bps", type=float, default=5)
    parser.add_argument("--slippage-bps", type=float, default=5)
    parser.add_argument("--split-utc", type=str)
    parser.add_argument("--max-candles", type=int, default=MAX_CANDLES)
    args = parser.parse_args(argv)
    try:
        result = study(args.db, args.signals, args.out_dir, horizon=args.horizon,
                       fee_bps=args.fee_bps, slippage_bps=args.slippage_bps,
                       split_utc=args.split_utc, max_candles=args.max_candles)
    except (StudyError, OSError, sqlite3.DatabaseError, csv.Error) as exc:
        print("STUDY_HOLD: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"status":"PASS_SYNTHETIC_OR_OWNER_SNAPSHOT_ONLY", "signal_count":result["signal_count"],
                      "complete":result["metrics"]["overall"]["complete"],"release":"HOLD"},sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
