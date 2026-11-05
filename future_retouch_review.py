# -*- coding: utf-8 -*-
"""Classify historical candle signals by first *later* high >= fixed signal-time Bollinger upper.

Default reference is the original signal CSV bb_upper. Older SMA/close
reference rules remain explicit opt-ins for comparison, not the default.

Offline-only and read-only. Scan each (market, timeframe) once using the
(market,unit,utc) SQLite index; no indicator recomputation or external APIs.
"""
from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Callable

PRICE_FIELDS = ("bb_upper", "sma280", "sma560", "close")
COLUMNS = (
    "outcome", "reference_field", "reference_price", "first_touch_utc", "first_touch_kst",
    "bars_to_first_touch", "elapsed_minutes", "elapsed_hours", "first_touch_open",
    "first_touch_high", "first_touch_low", "first_touch_close", "first_touch_type",
    "observed_future_bars", "last_observed_utc", "last_observed_kst", "note",
)
SIGNAL_REQUIRED = {"exchange", "market", "unit", "utc", "kst", "close"}
DB_REQUIRED = {"market", "unit", "utc", "kst", "open", "high", "low", "close"}
UNIT_VALUES = {1, 3, 5, 10, 15, 30, 60, 240}
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\Z")
MARKET = re.compile(r"KRW-[A-Z0-9]+\Z")
EXCHANGE = re.compile(r"[a-z][a-z0-9_]*\Z")
DEFAULT_DB = Path(r"E:\업비트 캔들긁어오기\upbit_candles.sqlite3")


def parse_utc(s: str) -> datetime:
    if not TIMESTAMP.fullmatch(s):
        raise ValueError(f"UTC timestamp must be YYYY-MM-DDTHH:MM:SS: {s!r}")
    return datetime.fromisoformat(s)


def _number(s: str | float | int, label: str) -> float:
    try:
        n = float(s)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric {label}: {s!r}") from exc
    if not math.isfinite(n) or n <= 0:
        raise ValueError(f"Nonpositive or nonfinite {label}: {s!r}")
    return n


def read_signals(path: Path, *, price_field: str = "bb_upper") -> tuple[list[dict], list[str]]:
    """Parse the existing output CSV without recomputing or altering signals."""
    if price_field not in PRICE_FIELDS:
        raise ValueError("Unknown reference price field")
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        if not SIGNAL_REQUIRED.issubset(fields) or len(fields) != len(set(fields)):
            raise ValueError("Signal CSV missing/duplicate headers: " + ", ".join(sorted(SIGNAL_REQUIRED-set(fields))))
        if price_field not in fields:
            raise ValueError(f"Reference price column missing: {price_field}")
        if set(fields) & set(COLUMNS):
            raise ValueError("Provide the original pattern signals CSV, not a previous backtest output")
        events = []
        seen = set()
        for i, raw in enumerate(reader, 2):
            if None in raw or any(v is None for v in raw.values()):
                raise ValueError(f"CSV row {i}: wrong number of fields")
            event = dict(raw)
            exchange = event["exchange"].strip().lower()
            market = event["market"].strip().upper()
            if not EXCHANGE.fullmatch(exchange) or not MARKET.fullmatch(market):
                raise ValueError(f"CSV row {i}: unsupported exchange/market")
            try:
                unit = int(event["unit"])
            except ValueError as exc:
                raise ValueError(f"CSV row {i}: invalid timeframe") from exc
            if unit not in UNIT_VALUES:
                raise ValueError(f"CSV row {i}: unsupported minute timeframe")
            utc = event["utc"].strip()
            parse_utc(utc)
            _number(event["close"], f"row {i} signal close")
            price = _number(event[price_field], f"row {i} reference {price_field}")
            identity = (exchange, market, unit, utc)
            if identity in seen:
                raise ValueError(f"CSV row {i}: duplicate signal {identity}")
            seen.add(identity)
            event.update(exchange=exchange, market=market, unit=str(unit), utc=utc)
            event["_key"] = identity
            event["_price"] = price
            event["_time"] = parse_utc(utc)
            event["_anchor_index"] = None
            event.update(dict.fromkeys(COLUMNS, ""))
            event["reference_field"] = price_field
            event["reference_price"] = event[price_field]
            events.append(event)
    return events, fields


def connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"SQLite DB not found: {path}")
    uri = path.resolve(strict=True).as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        con.execute("PRAGMA query_only = ON")
        columns = {r[1] for r in con.execute("PRAGMA table_info(candles)")}
        if not DB_REQUIRED.issubset(columns):
            raise ValueError("SQLite candles schema missing: " + ", ".join(sorted(DB_REQUIRED-columns)))
        indexed = any(
            [r[2] for r in con.execute(f"PRAGMA index_info({json.dumps(row[1])})")][:3]
            == ["market", "unit", "utc"]
            for row in con.execute("PRAGMA index_list(candles)")
        )
        if not indexed:
            raise ValueError("SQLite candles requires indexed (market,unit,utc); refusing potentially slow full scans")
        con.execute("BEGIN")  # One consistent read snapshot while a collector might be active.
        return con
    except BaseException:
        con.close()
        raise


def validate_candle(values: tuple, market: str, unit: int) -> tuple:
    utc, kst, op, high, low, close = values
    parse_utc(str(utc))
    if not kst:
        raise ValueError(f"Missing KST at {market}/{unit}/{utc}")
    prices = [_number(s, f"{market}/{unit}/{utc}: {name}")
              for name, s in zip(("open", "high", "low", "close"), (op, high, low, close))]
    op, high, low, close = prices
    eps = max(high, op, close, low) * 1e-12
    if (high + eps < low or high + eps < max(op, close)
            or low - eps > min(op, close)):
        raise ValueError(f"Invalid OHLC range at {market}/{unit}/{utc}; stopping instead of misclassifying")
    return str(utc), str(kst), op, high, low, close


def _elapsed_minutes(event: dict, touch_utc: str) -> int:
    delta = (parse_utc(touch_utc) - event["_time"]).total_seconds() / 60
    if delta < 0 or delta != int(delta):
        raise ValueError("Unexpected event timestamp interval")
    return int(delta)


def classify(db: sqlite3.Connection, events: list[dict], *,
             report: Callable[[str], None] | None = print) -> None:
    """One chronological scan for each signal-bearing pair, heap of pending levels.

    A signal's own candle never counts. A whole future candle above the level
    counts as reached even if its low is greater than reference (gap case).
    """
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    exchanges = {e["exchange"] for e in events}
    if len(exchanges) > 1:
        raise ValueError("One source SQLite per exchange; multiple exchanges in CSV")
    for event in events:
        grouped[(event["market"], int(event["unit"]))].append(event)
    start = time.monotonic()
    last_report = start
    totals = Counter()
    for ordinal, ((market, unit), items) in enumerate(sorted(grouped.items()), 1):
        items.sort(key=lambda r: r["utc"])
        earliest = items[0]["utc"]
        cursor = db.execute(
            "SELECT utc,kst,open,high,low,close FROM candles "
            "WHERE market=? AND unit=? AND utc>=? ORDER BY utc",
            (market, unit, earliest),
        )
        pending: list[tuple[float, int, dict]] = []
        next_event = 0
        index = -1
        last_utc = last_kst = ""
        for raw in cursor:
            utc, kst, op, high, low, close = validate_candle(raw, market, unit)
            if last_utc and utc <= last_utc:
                raise ValueError(f"Unordered or duplicated candles: {market}/{unit}/{utc}")
            index += 1
            # Any earlier signal absent from DB cannot be classified reliably.
            while next_event < len(items) and items[next_event]["utc"] < utc:
                items[next_event]["outcome"] = "SIGNAL_NOT_FOUND"
                items[next_event]["note"] = "신호 시각에 해당하는 DB 봉 없음"
                next_event += 1
            # Resolve only prior candles' signals; do not count the signal candle.
            while pending and pending[0][0] <= high:
                price, _, event = heapq.heappop(pending)
                bars = index - event["_anchor_index"]
                if bars < 1:
                    raise AssertionError("Signal candle incorrectly treated as future")
                elapsed = _elapsed_minutes(event, utc)
                event.update(
                    outcome="RETOUCHED", first_touch_utc=utc, first_touch_kst=kst,
                    bars_to_first_touch=str(bars), elapsed_minutes=str(elapsed),
                    elapsed_hours=f"{elapsed / 60:.6f}".rstrip("0").rstrip("."),
                    first_touch_open=str(op), first_touch_high=str(high),
                    first_touch_low=str(low), first_touch_close=str(close),
                    first_touch_type=("FULL_CANDLE_ABOVE" if low > price else "RANGE_TOUCH"),
                    observed_future_bars=str(bars),
                )
                totals["RETOUCHED"] += 1
            # Activate events occurring at *this* candle only after hit checks.
            while next_event < len(items) and items[next_event]["utc"] == utc:
                event = items[next_event]
                if not math.isclose(float(event["close"]), close, rel_tol=1e-10, abs_tol=1e-10):
                    event["outcome"] = "SIGNAL_PRICE_MISMATCH"
                    event["note"] = f"CSV 신호 종가 {event['close']} != SQLite 신호 종가 {close}"
                else:
                    event["_anchor_index"] = index
                    event["outcome"] = "PENDING"
                    heapq.heappush(pending, (event["_price"], next_event, event))
                next_event += 1
            last_utc, last_kst = utc, kst
        for event in items:
            event["last_observed_utc"] = last_utc
            event["last_observed_kst"] = last_kst
            if event["outcome"] == "PENDING":
                future = index - event["_anchor_index"]
                event["observed_future_bars"] = str(future)
                event["outcome"] = "UNTOUCHED_OBSERVED" if future else "NO_FUTURE_CANDLES"
                event["note"] = ("관측된 이후 봉의 모든 고가가 신호 당시 선택된 기준가 미만; 이후 미래는 알 수 없음"
                                 if future else "신호 이후 저장된 봉 없음; 도달 여부 판단 보류")
            elif not event["outcome"]:
                event["outcome"] = "SIGNAL_NOT_FOUND"
                event["note"] = "신호 시각 또는 데이터 존재하지 않음"
            totals[event["outcome"]] += 1 if event["outcome"] != "RETOUCHED" else 0
        now = time.monotonic()
        if report and (ordinal == len(grouped) or ordinal % 10 == 0 or now-last_report >= 2.5):
            speed = ordinal / max(now-start, 0.001)
            eta = (len(grouped)-ordinal) / speed
            report(f"[{ordinal}/{len(grouped)} pairs] {market} {unit}m | "
                   f"reached={totals['RETOUCHED']} untouched={totals['UNTOUCHED_OBSERVED']} | "
                   f"ETA {eta:.0f}s")
            last_report = now


def _safe_json(value: object) -> str:
    # Prevent untrusted CSV text forming a closing script tag.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")


def make_html(rows: list[dict], summary: dict) -> str:
    display = [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]
    payload = _safe_json({"rows": display, "summary": summary})
    return r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; object-src 'none'">
<title>골든크로스 이후 가격 재도달 검사</title>
<style>
:root{font-family:system-ui,"Malgun Gothic",sans-serif;color:#172438;background:#f2f5fa}*{box-sizing:border-box}body{margin:0}main{max-width:1320px;margin:auto;padding:28px 22px 80px}h1{font-size:clamp(22px,3vw,32px);margin:0 0 10px}.sub{font-size:13px;color:#67788f;line-height:1.7}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}.stat,.paper{background:#fff;border:1px solid #e1e7f0;border-radius:12px;padding:18px}.label{color:#66778e;font-size:12px}.value{font-size:30px;font-weight:800;margin-top:6px}.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:20px 0 12px}input,select{border:1px solid #cbd5e1;border-radius:8px;padding:10px;background:white;color:#203047;font-size:14px}input{min-width:220px;flex:1}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}th{text-align:left;background:#f5f8fc;color:#60738b;font-size:12px;position:sticky;top:0}th,td{padding:13px 12px;border-bottom:1px solid #e8edf3}td.price{font-weight:700}td time{font-variant-numeric:tabular-nums}.pill{font-weight:800;padding:4px 8px;border-radius:18px;font-size:11px;background:#e7edfa;color:#315a9d}.u{background:#def6e8;color:#176441}.t{background:#fcebcf;color:#875c0b}.n{background:#fee2e2;color:#963c3c}details{white-space:normal;max-width:420px;min-width:130px}summary{color:#315a9d;cursor:pointer}dl{display:grid;grid-template-columns:1fr 1fr;gap:5px}dt{color:#728299}dd{margin:0;text-align:right;word-break:break-all}.foot{margin-top:12px;color:#67778b;font-size:13px}.hint{margin:16px 0;color:#52627b;font-size:12px;line-height:1.6}@media(max-width:680px){.stats{grid-template-columns:repeat(2,1fr)}main{padding:18px 10px}.stat,.paper{padding:12px}.value{font-size:25px}}
</style></head><body><main>
<h1>골든크로스 이후 가격 재도달 분석</h1>
<p class="sub">기준가 = 골든크로스가 발생한 그 봉의 볼린저밴드 상단(BB upper, 기본). 신호봉 다음 봉부터 고가 ≥ 당시 고정된 BB 상단 가격인 첫 봉을 추적합니다. 이후 BB 값은 재계산하거나 추종하지 않습니다. 이후 데이터가 없거나 신호가 DB와 불일치하면 보류합니다. 모든 계산은 저장된 캔들 기준이며, 봉 내부 정확한 체결 시각은 알 수 없습니다.</p>
<p class="sub" id="basis"></p><div class="stats" id="stats"></div>
<div class="paper"><div class="toolbar"><select id="status"><option value="UNTOUCHED_OBSERVED">미재도달만 (기본)</option><option value="RETOUCHED">재도달 백테스트</option><option value="UNRESOLVED">판단 보류</option><option value="ALL">전체</option></select><input id="search" placeholder="종목 검색 (BTC, ETH 등)"><select id="unit"><option value="ALL">전체 분봉</option></select><select id="order"><option value="latest">최신 신호순</option><option value="oldest">오래된 신호순</option></select></div><div class="table-wrap"><table><thead><tr><th>구분</th><th>종목</th><th>분봉</th><th>신호(KST)</th><th>기준가</th><th>최초 도달(KST)</th><th>몇 봉 후</th><th>경과 시간</th><th>상세</th></tr></thead><tbody id="body"></tbody></table></div><div class="foot" id="count"></div></div>
<p class="hint">※ 미재도달 = 데이터에 저장된 후속 봉에서만 재도달하지 않음. 미래에도 영원히 재도달하지 않는다는 의미가 아닙니다. 결측 캔들 사이의 거래는 판정 불가할 수 있습니다. 빈 데이터 또는 잘못된 OHLC는 검증에서 제외/오류로 처리합니다.</p>
<script type="application/json" id="payload">__DATA__</script><script>
(()=>{'use strict';const data=JSON.parse(document.getElementById('payload').textContent),rows=data.rows,summary=data.summary;const el=id=>document.getElementById(id);el('basis').textContent='분석 기준: '+summary.reference_label+' ['+summary.reference_field+'] · 신호봉 당시 고정가격 (신호봉 다음 봉부터 재도달 판정)';const stats=[['기존 신호',summary.total],['미재도달',summary.untouched],['재도달',summary.touched],['판단 보류',summary.unresolved]];for(const [label,value] of stats){const b=document.createElement('div');b.className='stat';const l=document.createElement('div');l.className='label';l.textContent=label;const v=document.createElement('div');v.className='value';v.textContent=Number(value).toLocaleString('ko-KR');b.append(l,v);el('stats').appendChild(b)}
for(const u of [...new Set(rows.map(r=>r.unit))].sort((a,b)=>Number(a)-Number(b))){const opt=document.createElement('option');opt.value=u;opt.textContent=u+'분봉';el('unit').appendChild(opt)}
const cell=(tr,text,cls)=>{const td=document.createElement('td');td.textContent=text==null?'':String(text);if(cls)td.className=cls;tr.appendChild(td);return td};function render(){const s=el('status').value,q=el('search').value.trim().toUpperCase(),u=el('unit').value;const arr=rows.filter(r=>(s==='ALL'||(s==='UNRESOLVED'?!['UNTOUCHED_OBSERVED','RETOUCHED'].includes(r.outcome):r.outcome===s))&&(u==='ALL'||r.unit===u)&&(r.market.toUpperCase().includes(q))).sort((a,b)=>el('order').value==='latest'?b.utc.localeCompare(a.utc):a.utc.localeCompare(b.utc));el('body').replaceChildren();for(const r of arr){const tr=document.createElement('tr');const name=r.outcome==='UNTOUCHED_OBSERVED'?'미재도달':r.outcome==='RETOUCHED'?'재도달':'보류';const c=cell(tr,'');const badge=document.createElement('span');badge.className='pill '+(r.outcome==='UNTOUCHED_OBSERVED'?'u':r.outcome==='RETOUCHED'?'t':'n');badge.textContent=name;c.appendChild(badge);cell(tr,r.market);cell(tr,r.unit+'m');cell(tr,r.kst);cell(tr,r.reference_price+' ('+r.reference_field+')','price');cell(tr,r.first_touch_kst||'-');cell(tr,r.bars_to_first_touch||'-');cell(tr,r.elapsed_minutes?r.elapsed_minutes+'분 ('+r.elapsed_hours+'시간)':'-');const d=document.createElement('td');const de=document.createElement('details');const su=document.createElement('summary');su.textContent='상세 정보';de.appendChild(su);const dl=document.createElement('dl');for(const [k,v] of [['시그널 UTC',r.utc],['신호 고가/저가','신호봉 제외'],['처음 도달한 봉 고가',r.first_touch_high||'-'],['처음 도달한 봉 저가',r.first_touch_low||'-'],['도달 방식',r.first_touch_type||'-'],['이후 관측한 봉 수',r.observed_future_bars||'-'],['마지막 DB 기록',r.last_observed_kst||'-'],['설명',r.note||'-']]){const dt=document.createElement('dt');dt.textContent=k;const dd=document.createElement('dd');dd.textContent=v;dl.append(dt,dd)}de.appendChild(dl);d.appendChild(de);tr.appendChild(d);el('body').appendChild(tr)}el('count').textContent=arr.length.toLocaleString('ko-KR')+'건 표시';}
for(const id of ['status','search','unit','order'])el(id).addEventListener(id==='search'?'input':'change',render);render();})();
</script></main></body></html>'''.replace("__DATA__", payload)


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(db_path: Path, signals_path: Path, output_dir: Path, *,
        price_field: str = "bb_upper", report: Callable[[str], None] | None = print) -> dict:
    db_path = Path(db_path).resolve(strict=True)
    signals_path = Path(signals_path).resolve(strict=True)
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists (no overwrites): {output_dir}")
    if not output_dir.parent.is_dir():
        raise NotADirectoryError(f"Output parent missing: {output_dir.parent}")
    events, original_fields = read_signals(signals_path, price_field=price_field)
    with closing(connect_readonly(db_path)) as db:
        classify(db, events, report=report)
    untouched = [e for e in events if e["outcome"] == "UNTOUCHED_OBSERVED"]
    touched = [e for e in events if e["outcome"] == "RETOUCHED"]
    unresolved = [e for e in events if e["outcome"] not in ("UNTOUCHED_OBSERVED", "RETOUCHED")]
    summary = {
        "total": len(events), "untouched": len(untouched), "touched": len(touched),
        "unresolved": len(unresolved), "outcomes": dict(Counter(e["outcome"] for e in events)),
        "reference": f"signal candle {price_field}", "reference_field": price_field,
        "reference_label": "신호 당시 볼린저밴드 상단" if price_field == "bb_upper" else f"신호 당시 {price_field}",
        "touch_rule": "later candle high >= fixed price of signal-time reference",
        "timestamp_basis": "candle open UTC; not exact intrabar trade time",
        "important": "No future reach observed does not prove it will never happen; missing candles are not trades",
    }
    temp_dir = Path(tempfile.mkdtemp(prefix=".future-review-", dir=output_dir.parent))
    try:
        fields = original_fields + list(COLUMNS)
        _write_csv(temp_dir / "01_untouched.csv", untouched, fields)
        _write_csv(temp_dir / "02_retouch_backtest.csv", touched, fields)
        _write_csv(temp_dir / "03_unresolved.csv", unresolved, fields)
        _write_csv(temp_dir / "04_all_classified.csv", events, fields)
        (temp_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        (temp_dir / "report.html").write_text(make_html(events, summary), encoding="utf-8")
        # Atomic publication as a brand new directory, never modifying an old result.
        os.replace(temp_dir, output_dir)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Post-signal price retouch review (offline SQLite, read-only)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help="Original Upbit SQLite database (default known Windows E: path)")
    parser.add_argument("--signals", type=Path, default=Path(__file__).resolve().parent / "results.csv",
                        help="Original pattern results.csv (default beside this script)")
    parser.add_argument("--price-field", choices=PRICE_FIELDS, default="bb_upper",
                        help="Fixed signal-candle reference: bb_upper(default), sma280, sma560, close")
    parser.add_argument("--out", type=Path,
                        help="New output directory; default next to CSV with a timestamp")
    args = parser.parse_args(argv)
    out = args.out or (args.signals.resolve().parent / ("future_review_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")))
    try:
        summary = run(args.db, args.signals, out, price_field=args.price_field)
    except (OSError, ValueError, sqlite3.DatabaseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Stopped. Existing DB and input CSV untouched.", file=sys.stderr)
        return 130
    print("REFERENCE:", summary["reference_label"], f"({summary['reference_field']})")
    print("COMPLETE:", summary["total"], "signals,", summary["untouched"], "untouched,",
          summary["touched"], "retouched,", summary["unresolved"], "unresolved")
    print("Open this report:", out / "report.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
