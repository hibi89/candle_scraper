# -*- coding: utf-8 -*-
"""Read-only BB(20,2,close) + BB(4,4,open) historical pattern search.

Event: close below both lower bands, followed by first close above BB20 lower.
Fix the BB4-open *middle* at the recovery bar. Touch from that bar inclusive
if any later high >= fixed target (including a full-candle gap above).

Python 3.11+, standard library only. No HTTP and no database writes.
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
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

UNITS = (1, 3, 5, 10, 15, 30, 60, 240)
MARKET_RE = re.compile(r"KRW-[A-Z0-9]+\Z")
REQUIRED = frozenset(("market", "unit", "utc", "kst", "open", "high", "low", "close"))
HEADERS = (
    "exchange", "market", "unit", "setup_utc", "setup_kst", "setup_close",
    "setup_bb20_lower", "setup_bb4_lower", "recovery_utc", "recovery_kst",
    "recovery_close", "recovery_bb20_lower", "bb4_open_mid_fixed",
    "recovery_open", "recovery_high", "recovery_low", "status",
    "first_touch_utc", "first_touch_kst", "first_touch_open",
    "first_touch_high", "first_touch_low", "first_touch_close",
    "touch_type", "touch_bars_after_recovery", "touch_minutes_after_recovery",
    "observed_future_bars", "observation_end_utc", "observation_end_kst",
    "pair_max_gap_minutes",
)
STATUS_TOUCHED = "REACHED"
STATUS_UNTOUCHED = "NOT_REACHED_AS_OF_DATA_END"
STATUS_NO_FUTURE = "NO_FUTURE_CANDLES"


class RollingWindow:
    def __init__(self, size: int):
        self.size = size
        self.values: deque[float] = deque()
        self.sum = 0.0

    def push(self, value: float) -> tuple[float, float] | None:
        if len(self.values) == self.size:
            self.sum -= self.values.popleft()
        self.values.append(value)
        self.sum += value
        if len(self.values) != self.size:
            return None
        mid = self.sum / self.size
        variance = math.fsum((v - mid) ** 2 for v in self.values) / self.size
        return mid, math.sqrt(max(0.0, variance))


class Indicators:
    def __init__(self):
        self.close20 = RollingWindow(20)
        self.open4 = RollingWindow(4)

    def push(self, opening: float, closing: float) -> tuple[float, float, float] | None:
        first = self.close20.push(closing)
        second = self.open4.push(opening)
        if first is None or second is None:
            return None
        mid20, dev20 = first
        mid4, dev4 = second
        return mid20 - 2.0 * dev20, mid4 - 4.0 * dev4, mid4


def parse_units(raw: str) -> tuple[int, ...]:
    if raw.strip().lower() in ("all", "*", "전체"):
        return UNITS
    try:
        values = tuple(int(s.strip()) for s in raw.split(","))
    except ValueError as ex:
        raise ValueError("Units must be comma-separated minutes") from ex
    if not values or len(values) != len(set(values)) or any(x not in UNITS for x in values):
        raise ValueError("Unsupported or duplicate unit; use all or 1,3,5,10,15,30,60,240")
    return values


def parse_markets(raw: str) -> frozenset[str] | None:
    if raw.strip().lower() in ("all", "*", "전체"):
        return None
    tokens = [s.strip().upper() for s in raw.split(",")]
    if not tokens or any(not x for x in tokens):
        raise ValueError("Invalid market list")
    values = [x if x.startswith("KRW-") else "KRW-" + x for x in tokens]
    if any(not MARKET_RE.fullmatch(x) for x in values):
        raise ValueError("KRW markets only; example BTC,ETH or KRW-BTC")
    return frozenset(values)


def connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"SQLite DB not found: {path}")
    # Absolute file URI; Path.as_uri percent-escapes Korean, spaces, '#' and '?'.
    uri = path.resolve(strict=True).as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        db.execute("PRAGMA query_only=ON")
        fields = {row[1] for row in db.execute("PRAGMA table_info(candles)")}
        missing = REQUIRED - fields
        if missing:
            raise ValueError("Candle DB incompatible; missing: " + ", ".join(sorted(missing)))
        return db
    except BaseException:
        db.close()
        raise


def pairs_for(db: sqlite3.Connection, units: tuple[int, ...], markets: frozenset[str] | None):
    clauses = ["unit IN (" + ",".join("?" for _ in units) + ")"]
    params: list = list(units)
    if markets is not None:
        clauses.append("market IN (" + ",".join("?" for _ in markets) + ")")
        params.extend(sorted(markets))
    rows = db.execute(
        "SELECT market,unit,COUNT(*) FROM candles WHERE " + " AND ".join(clauses)
        + " GROUP BY market,unit ORDER BY market,unit", params,
    )
    return [(m, int(u), int(c)) for m, u, c in rows if MARKET_RE.fullmatch(m or "")]


def validate_candle(market: str, unit: int, utc: str, vals: tuple):
    try:
        o, h, l, c = (float(x) for x in vals)
    except (TypeError, ValueError) as ex:
        raise ValueError(f"{market}/{unit}/{utc}: invalid OHLC") from ex
    if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
        raise ValueError(f"{market}/{unit}/{utc}: OHLC must be finite and >0")
    if not l <= min(o, c) <= max(o, c) <= h:
        raise ValueError(f"{market}/{unit}/{utc}: inconsistent OHLC")
    return o, h, l, c


def parse_utc(utc: str) -> datetime:
    try:
        # Source collector stores UTC as timezone-naive ISO without Z.
        value = datetime.fromisoformat(utc.replace("Z", "+00:00"))
        if value.tzinfo:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    except (ValueError, TypeError, AttributeError) as ex:
        raise ValueError(f"Non-ISO UTC candle time: {utc!r}") from ex


def _event(exchange: str, market: str, unit: int, setup: dict,
           utc: str, kst: str, index: int, values: tuple, bb20_low: float,
           target: float) -> dict:
    o, h, l, c = values
    return {
        "exchange": exchange, "market": market, "unit": unit,
        "setup_utc": setup["utc"], "setup_kst": setup["kst"],
        "setup_close": setup["close"],
        "setup_bb20_lower": setup["bb20"], "setup_bb4_lower": setup["bb4"],
        "recovery_utc": utc, "recovery_kst": kst,
        "recovery_close": c, "recovery_bb20_lower": bb20_low,
        "bb4_open_mid_fixed": target,
        "recovery_open": o, "recovery_high": h, "recovery_low": l,
        "status": "", "first_touch_utc": "", "first_touch_kst": "",
        "first_touch_open": "", "first_touch_high": "", "first_touch_low": "",
        "first_touch_close": "", "touch_type": "",
        "touch_bars_after_recovery": "", "touch_minutes_after_recovery": "",
        "observed_future_bars": 0, "observation_end_utc": utc,
        "observation_end_kst": kst,
        "pair_max_gap_minutes": 0,
        "_index": index, "_utc": parse_utc(utc),
    }


def _touch(event: dict, utc: str, kst: str, index: int, values: tuple) -> None:
    o, h, l, c = values
    event["status"] = STATUS_TOUCHED
    event["first_touch_utc"] = utc
    event["first_touch_kst"] = kst
    event["first_touch_open"] = o
    event["first_touch_high"] = h
    event["first_touch_low"] = l
    event["first_touch_close"] = c
    target = float(event["bb4_open_mid_fixed"])
    event["touch_type"] = "GAP_ABOVE" if l > target else "CANDLE_RANGE"
    event["touch_bars_after_recovery"] = index - event["_index"]
    event["touch_minutes_after_recovery"] = round(
        (parse_utc(utc) - event["_utc"]).total_seconds() / 60, 6
    )
    event["observed_future_bars"] = index - event["_index"]
    event["observation_end_utc"] = utc
    event["observation_end_kst"] = kst


def scan_pair(db: sqlite3.Connection, market: str, unit: int, count: int,
              exchange: str, last: int = 0,
              tick=None) -> tuple[list[dict], dict]:
    """Each pair streamed in chronological order; target-min-heap resolves all touches.

    O(candles * 20 + events log events), bounded indicator history and O(active)
    target heap. No future indicator values are used for signal generation.
    """
    window = Indicators()
    pending: dict | None = None
    active: list[tuple[float, int, dict]] = []
    events: list[dict] = []
    report_from = max(0, count - last) if last else 0
    last_utc = last_kst = None
    previous_dt = None
    max_gap = 0
    gap_count = 0
    last_index = -1
    for i, (utc, kst, opening, high, low, close) in enumerate(db.execute(
        "SELECT utc,kst,open,high,low,close FROM candles "
        "WHERE market=? AND unit=? ORDER BY utc ASC", (market, unit),
    )):
        opening, high, low, close = validate_candle(market, unit, utc, (opening, high, low, close))
        dt = parse_utc(utc)
        if previous_dt is not None:
            gap = (dt - previous_dt).total_seconds() / 60
            if gap <= 0:
                raise ValueError(f"{market}/{unit}/{utc}: out-of-order/duplicate candle")
            if gap > unit:
                gap_count += 1
                max_gap = max(max_gap, round(gap))
        previous_dt = dt
        last_utc, last_kst, last_index = utc, kst, i
        band = window.push(opening, close)
        if band is not None:
            lower20, lower4, middle4 = band
            if pending is not None and close > lower20:
                if i >= report_from:
                    event = _event(exchange, market, unit, pending, utc, kst, i,
                                   (opening, high, low, close), lower20, middle4)
                    events.append(event)
                    heapq.heappush(active, (middle4, len(events), event))
                pending = None
            elif pending is None and close < lower20 and close < lower4:
                pending = {"utc": utc, "kst": kst, "close": close,
                           "bb20": lower20, "bb4": lower4}
            # Check from recovery candle *inclusive*; any high at or above fixed
            # middle line is a touch, even if low is above (gap case).
            while active and active[0][0] <= high:
                _, _, event = heapq.heappop(active)
                _touch(event, utc, kst, i, (opening, high, low, close))
        if tick is not None and i % 3000 == 0:
            tick(i + 1)
    for _, _, event in active:
        observed = last_index - event["_index"]
        event["status"] = STATUS_UNTOUCHED if observed > 0 else STATUS_NO_FUTURE
        event["observed_future_bars"] = observed
        event["observation_end_utc"] = last_utc
        event["observation_end_kst"] = last_kst
        event["pair_max_gap_minutes"] = max_gap
    for event in events:
        if event["status"] == STATUS_TOUCHED:
            event["pair_max_gap_minutes"] = max_gap
        for key in list(event):
            if key.startswith("_"):
                del event[key]
    return events, {"gaps": gap_count, "max_gap_minutes": max_gap,
                    "setup_pending_at_end": int(pending is not None),
                    "candles": last_index + 1}


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _json_safe(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def make_html(events: list[dict], summary: dict) -> str:
    # Inline, no network, no CDN. JS renders with textContent, never innerHTML
    # for user-controlled fields.
    js_events = [{
        "m": e["market"], "u": e["unit"], "s": e["status"],
        "set": e["setup_kst"], "rec": e["recovery_kst"],
        "price": e["recovery_close"], "target": e["bb4_open_mid_fixed"],
        "touch": e["first_touch_kst"], "bars": e["touch_bars_after_recovery"],
        "mins": e["touch_minutes_after_recovery"], "obs": e["observed_future_bars"],
        "type": e["touch_type"],
    } for e in events]
    return """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; object-src 'none'; form-action 'none'">
<title>이중 볼린저밴드 패턴 전수 조사</title><style>
:root{font-family:system-ui,'Malgun Gothic',sans-serif;color:#162239;background:#f4f7fc}body{margin:0}.wrap{max-width:1320px;margin:35px auto;padding:0 20px}h1{font-size:27px;margin:0 0 12px}.subtitle{color:#51627d;font-size:14px;line-height:1.7}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:22px 0} .card,.panel{background:#fff;border:1px solid #e1e6f0;border-radius:13px;padding:17px} .num{font-size:25px;font-weight:800;margin:8px 0}.muted{color:#687b94;font-size:12px}.filters{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}input,select{padding:10px;border:1px solid #cdd8e6;border-radius:8px;font:inherit}input{min-width:200px}.scroller{overflow:auto}table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:13px}th,td{padding:11px 10px;border-bottom:1px solid #eef0f3;text-align:left}th{background:#f1f4f9;color:#415372}td.price{font-weight:700}.pagination{display:flex;align-items:center;gap:12px;justify-content:flex-end;padding:16px 0}button{padding:9px 13px;background:#fff;border:1px solid #aebbd1;border-radius:8px;cursor:pointer}button:disabled{opacity:.4}.warn{color:#8e4b16;background:#fff7df;padding:12px;border-radius:8px;margin:15px 0;font-size:13px}@media(max-width:700px){.cards{grid-template-columns:repeat(2,1fr)}}
</style></head><body><main class="wrap"><h1>이중 볼린저밴드 · 복귀 후 목표가 미도달</h1><p class="subtitle">이탈: 종가 &lt; BB(20,2,Close) 하단 및 BB(4,4,Open) 하단 → 복귀: 종가 &gt; BB20 하단 → 그 복귀봉의 BB(4,4,Open) 중앙선 고정.<br>복귀봉 포함 고가 ≥ 고정 목표가면 도달. 갭상승 포함. 검색 결과는 저장된 캔들 구간 안에서만 유효.</p>
<div class="cards"><div class="card"><div class="muted">복귀 신호</div><div class="num" id="total"></div></div><div class="card"><div class="muted">현재까지 미도달</div><div class="num" id="untouched"></div></div><div class="card"><div class="muted">최초 도달 확인</div><div class="num" id="touched"></div></div><div class="card"><div class="muted">후속 캔들 없음</div><div class="num" id="insufficient"></div></div></div>
<div class="warn">미도달은 과거 DB의 마지막 관측 시점까지의 결과이며 미래 100%를 뜻하지 않습니다. 복귀봉 내 고가 선행 여부는 OHLC만으로 알 수 없습니다. 동일한 이탈 구간에서 최초 복귀 신호 하나를 기록합니다.</div>
<section class="panel"><div class="filters"><input id="market" placeholder="종목 검색: AXS, BTC"><select id="unit"><option value="">전체 분봉</option></select><select id="status"><option value="">전체 상태</option><option value="NOT_REACHED_AS_OF_DATA_END">미도달</option><option value="REACHED">도달</option><option value="NO_FUTURE_CANDLES">후속봉 없음</option></select><select id="sort"><option value="desc">최신 복귀순</option><option value="asc">과거 복귀순</option></select></div><div class="muted" id="matched"></div><div class="scroller"><table><thead><tr><th>상태</th><th>종목</th><th>분봉</th><th>이탈 시각(KST)</th><th>복귀 시각(KST)</th><th>복귀 종가</th><th>고정 BB4 중앙선</th><th>최초 도달(KST)</th><th>소요 봉</th><th>소요 분</th><th>후속 관찰봉</th></tr></thead><tbody id="body"></tbody></table></div><div class="pagination"><button id="prev">이전</button><span id="page"></span><button id="next">다음</button></div></section><p class="muted">정밀 데이터(OHLC, UTC, 원본 기준값)는 같은 폴더의 CSV 파일에 있습니다. 외부 통신을 하지 않는 로컬 보고서입니다.</p></main>
<script>""" + "const items=" + _json_safe(js_events) + ";const summary=" + _json_safe(summary) + ";" + """
const $=id=>document.getElementById(id);const unitSet=[...new Set(items.map(x=>x.u))].sort((a,b)=>a-b);for(const u of unitSet){const opt=document.createElement('option');opt.value=String(u);opt.textContent=u+'분';$('unit').appendChild(opt)}
$('total').textContent=items.length.toLocaleString();$('touched').textContent=(summary.reached||0).toLocaleString();$('untouched').textContent=(summary.untouched||0).toLocaleString();$('insufficient').textContent=(summary.no_future||0).toLocaleString();
const label={REACHED:'재도달',NOT_REACHED_AS_OF_DATA_END:'미도달',NO_FUTURE_CANDLES:'관측불가'};let page=0;let filtered=[];const size=100;function fill(){const tbody=$('body');tbody.replaceChildren();const rows=filtered.slice(page*size,(page+1)*size);for(const item of rows){const tr=document.createElement('tr');const cols=[label[item.s]||item.s,item.m,item.u+'m',item.set,item.rec,item.price,item.target,item.touch||'-',item.bars===''?'-':item.bars,item.mins===''?'-':item.mins,item.obs];for(const value of cols){const td=document.createElement('td');td.textContent=String(value);tr.appendChild(td)}tbody.appendChild(tr)}$('matched').textContent='필터 결과 '+filtered.length.toLocaleString()+'건';const pages=Math.ceil(filtered.length/size);$('page').textContent=pages?(page+1)+' / '+pages:'0 / 0';$('prev').disabled=page<=0;$('next').disabled=page+1>=pages}
function apply(){const q=$('market').value.trim().toUpperCase(),u=$('unit').value,s=$('status').value;filtered=items.filter(x=>(!q||x.m.includes(q))&&(!u||String(x.u)===u)&&(!s||x.s===s));filtered.sort((a,b)=>$('sort').value==='asc'?a.rec.localeCompare(b.rec):b.rec.localeCompare(a.rec));page=0;fill()}for(const id of ['market','unit','status','sort'])$(id).addEventListener(id==='market'?'input':'change',apply);$('prev').addEventListener('click',()=>{if(page){page--;fill()}});$('next').addEventListener('click',()=>{if((page+1)*size<filtered.length){page++;fill()}});apply();
</script></body></html>"""


def run(db_path: Path, out_root: Path, *, markets=None, units=UNITS,
        last: int = 0, verbose=True) -> tuple[Path, dict]:
    db_path = Path(db_path).resolve(strict=True)
    out_root = Path(out_root).resolve()
    if not out_root.is_dir():
        raise NotADirectoryError(f"Output root folder missing: {out_root}")
    if last < 0:
        raise ValueError("--last must be >= 0")
    db = connect_readonly(db_path)
    tmp = None
    try:
        pairs = pairs_for(db, units, markets)
        if not pairs:
            raise ValueError("No market/timeframe candles matching selection")
        if markets is not None:
            known = {m for m, _, _ in pairs}
            if markets - known:
                raise ValueError("Markets absent in selected timeframe(s): " + ",".join(sorted(markets-known)))
        total_candles = sum(c for _, _, c in pairs)
        tmp = Path(tempfile.mkdtemp(prefix=".dual-bb-tmp-", dir=out_root))
        all_events: list[dict] = []
        pair_summaries: list[dict] = []
        done = 0
        since = time.perf_counter()
        last_update = since
        exchange = "upbit" if "upbit" in db_path.stem.lower() else "bithumb" if "bithumb" in db_path.stem.lower() else db_path.stem
        if verbose:
            print(f"READ ONLY: {db_path}\nScanning {len(pairs):,} pairs / {total_candles:,} candles; latest signal filter: {'ALL' if last==0 else last}", flush=True)
        for pair_id, (market, unit, count) in enumerate(pairs, 1):
            def tick(n):
                nonlocal last_update
                now = time.perf_counter()
                if verbose and now-last_update>=2.5:
                    pct = (done+n)/max(total_candles, 1)*100
                    rate = (done+n)/max(now-since, 1e-3)
                    eta = int((total_candles-done-n)/rate) if rate else 0
                    print(f"[{pct:5.1f}%] {pair_id}/{len(pairs)} {market} {unit}m "
                          f"{done+n:,}/{total_candles:,} candles; ETA {eta//60}m{eta%60}s", flush=True)
                    last_update = now
            events, stats = scan_pair(db, market, unit, count, exchange, last=last, tick=tick)
            all_events.extend(events)
            pair_summaries.append({"market": market, "unit": unit, **stats, "recovery_signals": len(events)})
            done += count
            if verbose:
                tick(0)
        all_events.sort(key=lambda e:(e["recovery_utc"],e["market"],e["unit"]), reverse=True)
        touched = [e for e in all_events if e["status"] == STATUS_TOUCHED]
        untouched = [e for e in all_events if e["status"] == STATUS_UNTOUCHED]
        no_future = [e for e in all_events if e["status"] == STATUS_NO_FUTURE]
        summary = {
            "pattern": "Dual BB lower breakout + BB20 lower reentry, fixed BB4(open) mid target",
            "database_filename": db_path.name,
            "database_path_on_runner": str(db_path),
            "source_mode": "sqlite_read_only",
            "units": list(units), "markets": sorted(markets) if markets else "ALL",
            "latest_n_filter": last, "pairs": len(pairs),
            "candles_processed": done, "signals": len(all_events),
            "reached": len(touched), "untouched": len(untouched), "no_future": len(no_future),
            "reentry_and_touch_same_bar": sum(e["touch_bars_after_recovery"] == 0 for e in touched),
            "gap_above_touch": sum(e["touch_type"] == "GAP_ABOVE" for e in touched),
            "timeframe_counts": dict(Counter(str(e["unit"]) for e in all_events)),
            "pair_data_gaps": sum(x["gaps"] for x in pair_summaries),
            "max_gap_minutes": max((x["max_gap_minutes"] for x in pair_summaries),default=0),
            "pending_setups_not_recovered": sum(x["setup_pending_at_end"] for x in pair_summaries),
            "notes": ["Unreached means only until last stored candle, not guaranteed forever.",
                      "Same recovery candle counted; intrabar execution order unknown.",
                      "Candles may be sparse. Gaps mean some time intervals had no recorded candle."],
        }
        write_csv(tmp / "01_not_reached.csv", untouched)
        write_csv(tmp / "02_reached_first_touch.csv", touched)
        write_csv(tmp / "03_no_future_candles.csv", no_future)
        write_csv(tmp / "04_all_recovery_signals.csv", all_events)
        (tmp / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        (tmp / "report.html").write_text(make_html(all_events, summary), encoding="utf-8")
        (tmp / "README.txt").write_text(
            "Open report.html locally. 01=not reached up to latest DB candle; "
            "02=first touch backtest; 03=no future bars; 04=all recovery signals.\n"
            "Read-only SQLite. No network. Recovery candle counts in touch check.\n",
            encoding="utf-8",
        )
        filename = "dual_bb_results_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        target = out_root / filename
        index = 1
        while target.exists():
            target = out_root / f"{filename}_{index:02d}"
            index += 1
        os.rename(tmp, target)
        tmp = None
        if verbose:
            print(f"\nCOMPLETE: {done:,} candles, {len(all_events):,} recoveries: "
                  f"unreached {len(untouched):,} / reached {len(touched):,} / "
                  f"no-future {len(no_future):,}",flush=True)
            print("REPORT:", target / "report.html",flush=True)
        return target, summary
    finally:
        db.close()
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Dual Bollinger Band fixed-target historical scanner")
    parser.add_argument("--db", type=Path, default=Path(r"E:\업비트 캔들긁어오기\upbit_candles.sqlite3"),
                        help="Path to the source candle SQLite (default: known E: path)")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent,
                        help="Parent folder for new timestamped results folder")
    parser.add_argument("--markets", default="all", help="all or BTC,ETH,AXS")
    parser.add_argument("--units", default="all", help="all or 1,3,5,10,15,30,60,240")
    parser.add_argument("--last", type=int, default=0, help="Only emit recoveries in last N candles/pair (0=all)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    try:
        result, _ = run(args.db, args.output_dir, markets=parse_markets(args.markets),
                        units=parse_units(args.units), last=args.last, verbose=not args.quiet)
        if args.quiet:
            print(result)
        return 0
    except (ValueError, OSError, sqlite3.Error) as ex:
        print("ERROR:", ex, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted; source DB unchanged and partial reports removed.",file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
