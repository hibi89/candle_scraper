# -*- coding: utf-8 -*-
"""KRW candle collector. Standard library only; Windows console friendly."""
import csv
import json
import math
import os
import re
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
UNITS = ('month', 'week', 'day', 240, 60, 30, 15, 10, 5, 3, 1)
TARGET = 10000
WORKERS = 5
CONFIG = {
    'upbit': ('https://api.upbit.com/v1', ROOT / 'upbit_candles.sqlite3'),
    'bithumb': ('https://api.bithumb.com/v1', ROOT / 'bithumb_candles.sqlite3'),
}
HEADERS = {'Accept': 'application/json', 'User-Agent': 'CandleCollector/1.0'}
class RateGate:
    def __init__(self, interval=0.17):
        self.lock = threading.Lock()
        self.interval = interval
        self.last = 0.0
        self.blocked_until = 0.0

    def block_for(self, seconds):
        """Fail closed across all threads for one exchange; never sleep 5 workers."""
        with self.lock:
            self.blocked_until = max(self.blocked_until, time.monotonic() + seconds)

    def wait(self):
        with self.lock:
            remaining = self.blocked_until - time.monotonic()
            if remaining > 0:
                raise RuntimeError(f'Exchange API cooldown active: retry after {remaining:.0f}s')
            delay = self.interval - (time.monotonic() - self.last)
            if delay > 0:
                time.sleep(delay)
            self.last = time.monotonic()

GATES = {name: RateGate() for name in CONFIG}
DB_OPEN_LOCK = threading.Lock()  # serialize first-time schema checks and initialization


def verify_existing_schema(connection):
    """Verify uniqueness and conflict targets *before* allowing any writes.

    Column names alone cannot guarantee `INSERT OR IGNORE` prevents duplicates:
    an unrelated/legacy SQLite file might have the columns but no primary key.
    """
    schema = {
        'candles': ('market', 'unit', 'utc'),
        'collection_state': ('market', 'unit'),
    }
    for table, primary_key in schema.items():
        rows = connection.execute(f'PRAGMA table_info({table})').fetchall()
        if not rows:
            if table == 'candles':
                raise RuntimeError('Existing candles table has an incompatible schema; not modified')
            # A genuine legacy collector DB may lack state; it can be created
            # safely only when the candles primary key has been verified.
            continue
        actual = {row[1] for row in rows}
        needed = ({'market','unit','utc','kst','open','high','low','close','volume','trade_value'}
                  if table == 'candles' else {'market','unit','finished'})
        actual_pk = tuple(row[1] for row in sorted(rows, key=lambda row: row[5]) if row[5] > 0)
        if not needed.issubset(actual) or actual_pk != primary_key:
            raise RuntimeError(f'Existing {table} table has an incompatible schema or primary key; not modified')


def retry_after_seconds(raw_value, now=None):
    """Interpret HTTP Retry-After safely, preserving server throttling instructions.

    Supports delta-seconds and HTTP-date. Return None for invalid headers.
    """
    if raw_value is None:
        return None
    try:
        delay = float(str(raw_value).strip())
    except (ValueError, TypeError):
        try:
            until = parsedate_to_datetime(str(raw_value).strip())
            if until.tzinfo is None:
                return None
            now = now if now is not None else datetime.now(timezone.utc)
            delay = (until - now).total_seconds()
        except (ValueError, TypeError, OverflowError, IndexError):
            return None
    if not math.isfinite(delay):
        return None
    return max(0.0, delay)


def request(exchange, path, params=None):
    url = CONFIG[exchange][0] + path
    if params: url += '?' + urllib.parse.urlencode(params)
    for attempt in range(5):
        GATES[exchange].wait()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20) as resp:
                data = json.load(resp)
            if not isinstance(data, list): raise ValueError(f'Unexpected API response: {str(data)[:180]}')
            return data
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504):
                raise
            delay = retry_after_seconds((exc.headers or {}).get('Retry-After'))
            # Do not retry before a provider-specified long cooldown. Fail
            # closed rather than silently capping Retry-After to 30 seconds.
            if delay is not None and delay > 30:
                # A single 429 with a long cooldown must stop all five
                # collection workers from hitting this provider again.
                GATES[exchange].block_for(delay)
                raise RuntimeError(
                    f'Exchange requested a {delay:.0f}s Retry-After cooldown; '
                    'collection paused to respect API rate limits'
                ) from exc
            if attempt == 4:
                raise
            time.sleep(min(30, max(1.0 * 2 ** attempt, delay or 0.0)))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 4: raise
            time.sleep(min(8, 2 ** attempt))
    raise RuntimeError('Retries exhausted')

def db_open(exchange):
    with DB_OPEN_LOCK:
        return _db_open_unlocked(exchange)

def _db_open_unlocked(exchange):
    path = CONFIG[exchange][1]
    required = {'market','unit','utc','kst','open','high','low','close','volume','trade_value'}
    # A foreign/legacy database is never silently converted or modified.
    if path.exists():
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError('Existing database file is invalid; not modified')
        ro_uri = 'file:' + urllib.parse.quote(str(path.resolve())) + '?mode=ro'
        preflight = sqlite3.connect(ro_uri, uri=True, timeout=15)
        try:
            tables = {row[0] for row in preflight.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if 'candles' not in tables and tables:
                raise RuntimeError('Existing database is unrelated; not modified')
            if 'candles' in tables:
                verify_existing_schema(preflight)
        finally:
            preflight.close()
    db = sqlite3.connect(path, timeout=60)
    db.execute('PRAGMA busy_timeout=60000')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('''CREATE TABLE IF NOT EXISTS candles (
        market TEXT NOT NULL, unit INTEGER NOT NULL, utc TEXT NOT NULL,
        kst TEXT NOT NULL, open REAL NOT NULL, high REAL NOT NULL,
        low REAL NOT NULL, close REAL NOT NULL, volume REAL NOT NULL,
        trade_value REAL NOT NULL, PRIMARY KEY (market,unit,utc))''')
    db.execute('''CREATE TABLE IF NOT EXISTS collection_state (
        market TEXT NOT NULL, unit INTEGER NOT NULL, finished INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(market,unit))''')
    db.commit()
    try:
        verify_existing_schema(db)
    except Exception:
        db.close()
        raise
    return db

def endpoint(unit):
    return f'/candles/minutes/{unit}' if isinstance(unit, int) else '/candles/days' if unit == 'day' else '/candles/weeks' if unit == 'week' else '/candles/months'

def is_closed(c, unit, now=None):
    now = now or datetime.now(timezone.utc)
    start = datetime.fromisoformat(c['candle_date_time_utc']).replace(tzinfo=timezone.utc)
    if isinstance(unit, int): return start + timedelta(minutes=unit) <= now
    kst_start = datetime.fromisoformat(c['candle_date_time_kst']).replace(tzinfo=timezone(timedelta(hours=9)))
    if unit == 'day':
        return kst_start + timedelta(days=1) <= now.astimezone(kst_start.tzinfo)
    if unit == 'month':
        next_year = kst_start.year + (kst_start.month == 12)
        next_month = 1 if kst_start.month == 12 else kst_start.month + 1
        boundary = kst_start.replace(year=next_year, month=next_month)
        return boundary <= now.astimezone(kst_start.tzinfo)
    # Weekly candles are seven-day intervals from the provider's stated start,
    # not necessarily midnight on the next Monday.
    return kst_start + timedelta(days=7) <= now.astimezone(kst_start.tzinfo)

def candle_time(c, field='candle_date_time_utc'):
    """Parse exchange wall-clock timestamps, rejecting offset ambiguity."""
    if not isinstance(c, dict):
        raise ValueError('Invalid candle object')
    stamp = c.get(field)
    if not isinstance(stamp, str) or 'T' not in stamp:
        raise ValueError(f'Invalid candle timestamp: {field}')
    try:
        value = datetime.fromisoformat(stamp)
    except ValueError as exc:
        raise ValueError(f'Invalid candle timestamp: {field}') from exc
    if value.tzinfo is not None:
        raise ValueError(f'Invalid timezone in candle timestamp: {field}')
    return value


def validate_candle(c, expected_market=None):
    """Validate the complete API row before writing any part of the page."""
    utc = candle_time(c)
    kst = candle_time(c, 'candle_date_time_kst')
    if kst - utc != timedelta(hours=9):
        raise ValueError('UTC/KST candle timestamp mismatch')
    if expected_market is not None and c.get('market') != expected_market:
        raise ValueError('Candle market mismatch')
    for key in ('opening_price', 'high_price', 'low_price', 'trade_price',
                'candle_acc_trade_volume', 'candle_acc_trade_price'):
        value = c.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'Invalid candle numeric field: {key}')
        if value < 0 or (key in ('opening_price','high_price','low_price','trade_price') and value <= 0):
            raise ValueError(f'Invalid candle numeric field: {key}')
    if c['low_price'] > min(c['opening_price'],c['trade_price']) or c['high_price'] < max(c['opening_price'],c['trade_price']):
        raise ValueError('Inconsistent candle OHLC values')
    if c['high_price'] < c['low_price']:
        raise ValueError('Inconsistent candle OHLC range')


def validate_page(page, market, cutoff_utc=None):
    """A page must be descending, unique and strictly older than the cursor."""
    if not isinstance(page, list):
        raise ValueError('Invalid candle page')
    previous = candle_time({'candle_date_time_utc': cutoff_utc}) if cutoff_utc else None
    for c in page:
        validate_candle(c, expected_market=market)
        current = candle_time(c)
        if previous is not None and current >= previous:
            raise ValueError('Unordered, duplicated or cursor-exceeding candle page')
        previous = current


def insert_page(db, market, unit, page):
    for candle in page:
        validate_candle(candle, expected_market=market)
    rows = [(market, unit, c['candle_date_time_utc'], c['candle_date_time_kst'],
             c['opening_price'], c['high_price'], c['low_price'], c['trade_price'],
             c['candle_acc_trade_volume'], c['candle_acc_trade_price'])
            for c in page if is_closed(c, unit)]
    before = db.total_changes
    db.executemany('''INSERT OR IGNORE INTO candles
        (market,unit,utc,kst,open,high,low,close,volume,trade_value)
        VALUES (?,?,?,?,?,?,?,?,?,?)''', rows)
    db.commit()
    return db.total_changes - before

def market_query(exchange):
    """The two exchanges expose different names for the market detail flag."""
    if exchange == 'upbit':
        return {'is_details': 'false'}
    if exchange == 'bithumb':
        return {'isDetails': 'false'}
    raise ValueError('Unknown exchange')


def pagination_cursor(exchange, candle_utc):
    """Upbit accepts UTC ISO8601; Bithumb documents its `to` in KST.

    Work exclusively in UTC internally; convert to the provider's documented
    timezone only at the HTTP boundary. The reference instant is exclusive.
    """
    if exchange not in CONFIG:
        raise ValueError('Unknown exchange')
    if not isinstance(candle_utc, str):
        raise ValueError('Invalid UTC timestamp for pagination')
    timestamp = datetime.fromisoformat(candle_utc.replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    if exchange == 'bithumb':
        return timestamp.astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%dT%H:%M:%S')
    return timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')


def markets(exchange):
    return sorted({c['market'] for c in request(exchange, '/market/all', market_query(exchange))
                   if isinstance(c, dict) and isinstance(c.get('market'), str)
                   and re.fullmatch(r'KRW-[A-Z0-9]+', c['market'])})

def collect_pair(exchange, market, unit, mode):
    if mode not in ('initial', 'update'):
        raise ValueError('Unknown mode')
    db = db_open(exchange)
    try:
        n = db.execute('SELECT COUNT(*) FROM candles WHERE market=? AND unit=?', (market,unit)).fetchone()[0]
        oldest, newest = db.execute('SELECT MIN(utc),MAX(utc) FROM candles WHERE market=? AND unit=?', (market,unit)).fetchone()
        if mode == 'initial':
            state = db.execute('SELECT finished FROM collection_state WHERE market=? AND unit=?', (market,unit)).fetchone()
            if state and state[0]: return n, 0, 'already-finished'
            if n >= TARGET: return n, 0, 'target-reached'
            cursor = pagination_cursor(exchange, oldest) if oldest else None
        else:
            cursor = None
        added = 0
        seen = set()
        exclusive_before = oldest if mode == 'initial' else None
        exhausted = False
        while True:
            if mode == 'initial' and n >= TARGET: break
            # New pairs in update mode also obey the initial history limit.
            backfill = mode == 'initial' or (mode == 'update' and newest is None)
            count = min(200, max(1, TARGET - n + (1 if cursor is None else 0))) if backfill else 200
            params = {'market': market, 'count': count}
            if cursor: params['to'] = cursor
            page = request(exchange, endpoint(unit), params)
            if not page:
                exhausted = True
                break
            validate_page(page, market, cutoff_utc=exclusive_before)
            first = page[0]['candle_date_time_utc']
            if first in seen:
                raise RuntimeError('Repeated API page; initial history remains resumable')
            seen.add(first)
            if mode == 'update' and newest:
                fresh = [c for c in page if c['candle_date_time_utc'] > newest]
                added += insert_page(db, market, unit, fresh)
                if len(fresh) < len(page): break
            else:
                # Never exceed the requested initial-history cap, even if a
                # provider returns an extra overlapping/closed candle.
                remaining = max(0, TARGET - n)
                eligible = [c for c in page if is_closed(c, unit)]
                eligible.sort(key=lambda c: c['candle_date_time_utc'], reverse=True)
                added += insert_page(db, market, unit, eligible[:remaining])
            n = db.execute('SELECT COUNT(*) FROM candles WHERE market=? AND unit=?', (market,unit)).fetchone()[0]
            if len(page) < count:
                exhausted = True
                break
            exclusive_before = page[-1]['candle_date_time_utc']
            next_cursor = pagination_cursor(exchange, exclusive_before)
            if next_cursor == cursor:
                raise RuntimeError('Pagination cursor stalled; initial history remains resumable')
            cursor = next_cursor
            if mode == 'update' and newest is None and n >= TARGET:
                break
        n = db.execute('SELECT COUNT(*) FROM candles WHERE market=? AND unit=?', (market,unit)).fetchone()[0]
        if (mode == 'initial' or (mode == 'update' and newest is None)) and (n >= TARGET or exhausted):
            db.execute('''INSERT INTO collection_state(market,unit,finished) VALUES(?,?,1)
                ON CONFLICT(market,unit) DO UPDATE SET finished=1''', (market,unit))
            db.commit()
        return n, added, 'ok'
    finally:
        db.close()

def run(exchange, mode, units=UNITS, progress=print):
    if exchange not in CONFIG: raise ValueError('Unknown exchange')
    if mode not in ('initial', 'update'): raise ValueError('Unknown mode')
    if any(u not in UNITS for u in units): raise ValueError('Unknown candle unit')
    selected = tuple(dict.fromkeys(units))
    if not selected or any(u not in UNITS for u in selected): raise ValueError('No valid candle units selected')
    symbols = markets(exchange)
    if not symbols: raise RuntimeError(f'{exchange}: no KRW markets returned')
    ordered = tuple(u for u in UNITS if u in selected)
    jobs = [(m,u) for u in ordered for m in symbols]
    errors = []
    start = time.monotonic()
    progress(f'{exchange.upper()}: {len(symbols)} KRW markets, {len(jobs)} jobs, mode={mode}')
    completed = 0
    # Complete each timeframe before starting the next; within a timeframe, use 5 workers.
    interrupted = False
    for unit in ordered:
        progress(f'--- {exchange.upper()} {unit}: {len(symbols)} markets ---')
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(collect_pair, exchange, m, unit, mode): m for m in symbols}
            try:
                for f in as_completed(futures):
                    m = futures[f]
                    completed += 1
                    elapsed = max(0.001, time.monotonic()-start)
                    eta = elapsed / completed * (len(jobs)-completed)
                    try:
                        n, added, status = f.result()
                        progress(f'[{completed}/{len(jobs)} {completed/len(jobs):.1%} ETA {eta/60:.0f}m] {exchange} {m} {unit}: {status}, total={n}, new={added}')
                    except Exception as exc:
                        errors.append((m,str(unit),str(exc)))
                        progress(f'[{completed}/{len(jobs)}] ERROR {exchange} {m} {unit}: {exc}')
            except KeyboardInterrupt:
                progress('Interrupted; committed data retained. Waiting for active workers to finish.')
                for f in futures: f.cancel()
                interrupted = True
        if interrupted: break
    if errors:
        path = ROOT / f'{exchange}_errors.csv'
        with path.open('w', newline='', encoding='utf-8-sig') as out:
            w = csv.writer(out); w.writerow(['market','unit','error']); w.writerows(errors)
        progress(f'Errors: {len(errors)} (see {path.name})')
    progress(f'{exchange.upper()}: {"INTERRUPTED" if interrupted else "PARTIAL FAILURE" if errors else "COMPLETE"} '
             f'{completed}/{len(jobs)} jobs, errors={len(errors)}')
    return len(jobs),errors

def export_csv(exchange, folder=None):
    folder = Path(folder) if folder else ROOT / 'exports' / exchange
    folder.mkdir(parents=True, exist_ok=True)
    dbpath = CONFIG[exchange][1]
    if not dbpath.exists(): raise FileNotFoundError(dbpath)
    db = sqlite3.connect(f'file:{urllib.parse.quote(str(dbpath))}?mode=ro', uri=True)
    try:
        pairs = db.execute('SELECT DISTINCT market,unit FROM candles ORDER BY market,unit').fetchall()
        for i,(market,unit) in enumerate(pairs,1):
            if not market.startswith('KRW-') or not market[4:].replace('-', '').isalnum() or unit not in UNITS:
                raise ValueError(f'Unsafe or unsupported market/unit in database: {market!r}/{unit!r}')
            filename = f'{market}_{unit}.csv'
            destination = folder / filename
            temporary = folder / (filename + '.partial')
            try:
                with temporary.open('w',newline='',encoding='utf-8-sig') as out:
                    writer=csv.writer(out)
                    writer.writerow(['market','unit','utc','kst','open','high','low','close','volume','trade_value'])
                    for row in db.execute('''SELECT market,unit,utc,kst,open,high,low,close,volume,trade_value
                                            FROM candles WHERE market=? AND unit=? ORDER BY utc''',(market,unit)):
                        writer.writerow(row)
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    temporary.unlink()
            if i % 100 == 0: print(f'CSV {i}/{len(pairs)}')
        return len(pairs),folder
    finally: db.close()


def inspect_database(exchange):
    """Read-only inspection: never creates an empty DB or modifies an existing one."""
    if exchange not in CONFIG:
        raise ValueError('Unknown exchange')
    path = CONFIG[exchange][1]
    if not path.is_file():
        return {'exists': False, 'path': str(path), 'markets': 0, 'pairs': 0, 'candles': 0}
    uri = 'file:' + urllib.parse.quote(str(path.resolve())) + '?mode=ro'
    db = sqlite3.connect(uri, uri=True, timeout=15)
    try:
        db.execute('PRAGMA query_only=ON')
        columns = {row[1] for row in db.execute('PRAGMA table_info(candles)')}
        required = {'market','unit','utc','kst','open','high','low','close','volume','trade_value'}
        if not required.issubset(columns):
            raise RuntimeError('Incompatible candles schema')
        markets_count, candles_count = db.execute(
            'SELECT COUNT(DISTINCT market), COUNT(*) FROM candles').fetchone()
        pairs_count = db.execute(
            'SELECT COUNT(*) FROM (SELECT 1 FROM candles GROUP BY market,unit)').fetchone()[0]
        return {'exists': True, 'path': str(path), 'markets': markets_count,
                'pairs': pairs_count, 'candles': candles_count}
    finally:
        db.close()


def smoke_check(exchange, progress=print):
    """Read-only live API check. Never creates or writes a database."""
    if exchange not in CONFIG: raise ValueError('Unknown exchange')
    symbols = markets(exchange)
    if not symbols: raise RuntimeError(f'{exchange}: no KRW markets returned')
    market = 'KRW-BTC' if 'KRW-BTC' in symbols else symbols[0]
    progress(f'{exchange}: {len(symbols)} KRW markets; checking {market}')
    for unit in UNITS:
        candles = request(exchange, endpoint(unit), {'market':market,'count':2})
        if not candles: raise RuntimeError(f'{exchange} {market} {unit}: empty response')
        for key in ('candle_date_time_utc','candle_date_time_kst','opening_price','high_price','low_price','trade_price','candle_acc_trade_volume','candle_acc_trade_price'):
            if key not in candles[0]: raise RuntimeError(f'{exchange} {market} {unit}: missing {key}')
        validate_page(candles, market)
        # Verify real pagination too, not just the first page. A wrong timezone
        # or malformed `to` can pass a one-page smoke check and ruin backfill.
        if len(candles) >= 2:
            cutoff = min(c['candle_date_time_utc'] for c in candles)
            older = request(exchange, endpoint(unit), {'market':market, 'count':2,
                            'to':pagination_cursor(exchange, cutoff)})
            if older:
                validate_page(older, market, cutoff_utc=cutoff)
        progress(f'PASS {exchange} {market} {unit}: first-page and pagination response')
    return len(symbols)
