"""Offline, bounded, user-defined candle rule scanner. Python 3.11+ stdlib only.

Inputs: explicit read-only SQLite candle DB(s) and restricted JSON rules.
No eval/imported user code, exchange HTTP, source writes, or orders/trades.
"""
from __future__ import annotations

import argparse
import csv
from collections import deque
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import tempfile

MAX_RULE_FILE = 32768
MAX_RULES = 16
MAX_TERMS = 64
MAX_METRICS = 32
MAX_PERIOD = 560
UNITS = (1, 3, 5, 10, 15, 30, 60, 240)
PRICE_FIELDS = frozenset(('open', 'high', 'low', 'close'))
COMPARISONS = frozenset(('gt', 'gte', 'lt', 'lte', 'eq', 'ne', 'cross_up', 'cross_down'))
FIELDS = ('source', 'market', 'unit', 'utc', 'kst', 'close', 'rule_id')
_ID = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}\Z')
_MARKET = re.compile(r'KRW-[A-Z0-9]+\Z')


class RuleError(ValueError):
    """Input contract failed; no execution of arbitrary user expressions."""


def _pairs_no_duplicates(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise RuleError('Duplicate JSON rule key')
        data[key] = value
    return data


def load_rules(path: Path) -> tuple[tuple[str, dict], ...]:
    """Strict size-bounded JSON, symlink denied, duplicate keys and NaN denied."""
    path = Path(path)
    if not path.is_absolute() or path.is_symlink():
        raise RuleError('Rules require an absolute regular file path')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        info = os.fstat(stream.fileno())
        on_path = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_size > MAX_RULE_FILE
                or (info.st_dev, info.st_ino) != (on_path.st_dev, on_path.st_ino)):
            raise RuleError('Invalid or too-large rules file')
        raw = stream.read(MAX_RULE_FILE + 1)
    if len(raw) > MAX_RULE_FILE:
        raise RuleError('Rules file too large')
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs_no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(RuleError('Invalid numeric constant')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuleError('Invalid rules JSON') from exc
    if type(data) is not dict or set(data) != {'version', 'rules'} or type(data['version']) is not int or data['version'] != 1:
        raise RuleError('Unsupported rules contract')
    rules = data['rules']
    if type(rules) is not list or not 1 <= len(rules) <= MAX_RULES:
        raise RuleError('Choose 1 to 16 rules')
    seen = set()
    output = []
    metric_keys = set()
    node_counter = [0]
    for rule in rules:
        if type(rule) is not dict or set(rule) != {'id', 'when'} or type(rule['id']) is not str or not _ID.fullmatch(rule['id']):
            raise RuleError('Invalid rule name/structure')
        if rule['id'] in seen:
            raise RuleError('Duplicate rule ID')
        seen.add(rule['id'])
        _validate_condition(rule['when'], metric_keys, node_counter, 0)
        output.append((rule['id'], rule['when']))
    return tuple(output)


def _metric(value, keys: set) -> tuple:
    if type(value) is str and value in PRICE_FIELDS:
        key = ('field', value)
    elif type(value) is dict and set(value) == {'const'}:
        num = value['const']
        if type(num) not in (int, float) or not math.isfinite(num) or abs(num) > 1e12:
            raise RuleError('Invalid numeric threshold')
        key = ('const', float(num))
    elif type(value) is dict and len(value) == 1:
        op, args = next(iter(value.items()))
        if op not in ('sma', 'ema', 'bb_upper', 'bb_lower') or type(args) is not list:
            raise RuleError('Unsupported indicator')
        if op in ('sma', 'ema'):
            if len(args) != 2:
                raise RuleError('SMA/EMA format is [period, field]')
            period, field = args
            sigma = None
        else:
            if len(args) != 3:
                raise RuleError('Bollinger format is [period, sigma, field]')
            period, sigma, field = args
            if type(sigma) not in (int, float) or not math.isfinite(sigma) or not 0 < sigma <= 10:
                raise RuleError('Bollinger sigma outside allowed range')
        if type(period) is not int or not 2 <= period <= MAX_PERIOD or type(field) is not str or field not in PRICE_FIELDS:
            raise RuleError('Invalid indicator period or field')
        key = (op, period, field) if sigma is None else (op, period, float(sigma), field)
    else:
        raise RuleError('Only price fields and approved indicators are supported')
    keys.add(key)
    if len(keys) > MAX_METRICS:
        raise RuleError('Too many distinct indicators')
    return key


def _validate_condition(rule, keys: set, count: list[int], depth: int) -> None:
    count[0] += 1
    if count[0] > MAX_TERMS or depth > 6 or type(rule) is not dict or len(rule) != 1:
        raise RuleError('Condition nesting or size is invalid')
    op, args = next(iter(rule.items()))
    if op in ('all', 'any'):
        if type(args) is not list or not 1 <= len(args) <= 16:
            raise RuleError('Expected bounded condition group')
        for child in args:
            _validate_condition(child, keys, count, depth + 1)
    elif op == 'not':
        _validate_condition(args, keys, count, depth + 1)
    elif op in COMPARISONS:
        if type(args) is not list or len(args) != 2:
            raise RuleError('Expected two indicator operands')
        for value in args:
            _metric(value, keys)
    else:
        raise RuleError('Unknown condition operator')


def _canonical(value) -> tuple:
    if isinstance(value, str):
        return ('field', value)
    op, args = next(iter(value.items()))
    if op == 'const':
        return ('const', float(args))
    if op in ('sma', 'ema'):
        return (op, args[0], args[1])
    return (op, args[0], float(args[1]), args[2])


def _metric_keys(rules):
    keys = set()
    def visit(cond):
        op, val = next(iter(cond.items()))
        if op in ('all', 'any'):
            for child in val: visit(child)
        elif op == 'not': visit(val)
        else:
            keys.add(_canonical(val[0])); keys.add(_canonical(val[1]))
    for _, condition in rules: visit(condition)
    return keys


class Indicator:
    def __init__(self, key: tuple):
        self.key = key
        self.previous = None
        self.current = None
        self.period = key[1] if key[0] not in ('field', 'const') else 1
        self.window = deque()
        self.total = 0.0
        self.ema = None
        self.count = 0

    def push(self, bar: dict) -> None:
        self.previous = self.current
        if self.key[0] == 'field':
            self.current = bar[self.key[1]]
            return
        if self.key[0] == 'const':
            self.current = self.key[1]
            return
        value = bar[self.key[-1]]
        self.count += 1
        if self.key[0] == 'ema':
            self.ema = value if self.ema is None else self.ema + 2.0 / (self.period + 1) * (value - self.ema)
            self.current = self.ema if self.count >= self.period else None
            return
        if len(self.window) == self.period:
            self.total -= self.window.popleft()
        self.window.append(value)
        self.total += value
        if len(self.window) < self.period:
            self.current = None
            return
        center = self.total / self.period
        if self.key[0] == 'sma':
            self.current = center
        else:
            sigma = math.sqrt(max(0.0, math.fsum((v-center)**2 for v in self.window) / self.period))
            offset = self.key[2] * sigma
            self.current = center + offset if self.key[0] == 'bb_upper' else center - offset


def _eval(condition: dict, indicators: dict) -> bool | None:
    """Three-valued predicate: no warmed indicator is UNKNOWN, never true by NOT."""
    op, args = next(iter(condition.items()))
    if op == 'all':
        results = [_eval(child, indicators) for child in args]
        return False if False in results else None if None in results else True
    if op == 'any':
        results = [_eval(child, indicators) for child in args]
        return True if True in results else None if None in results else False
    if op == 'not':
        value = _eval(args, indicators)
        return None if value is None else not value
    left, right = (indicators[_canonical(item)] for item in args)
    a, b = left.current, right.current
    if a is None or b is None: return None
    if op == 'gt': return a > b
    if op == 'gte': return a >= b
    if op == 'lt': return a < b
    if op == 'lte': return a <= b
    if op == 'eq': return a == b
    if op == 'ne': return a != b
    if left.previous is None or right.previous is None: return None
    if op == 'cross_up': return left.previous <= right.previous and a > b
    if op == 'cross_down': return left.previous >= right.previous and a < b
    raise RuleError('Invalid condition')


def _parse_csv_tokens(raw: str, *, market: bool) -> tuple | None:
    if raw.lower() in ('all', '*', '전체'):
        return None
    parts = [p.strip().upper() for p in raw.split(',')]
    if not parts or any(not x for x in parts):
        raise RuleError('Empty market or timeframe token')
    if market:
        values = tuple(x if x.startswith('KRW-') else 'KRW-'+x for x in parts)
        if any(not _MARKET.fullmatch(v) for v in values): raise RuleError('Invalid market')
    else:
        try: values = tuple(int(x) for x in parts)
        except ValueError as exc: raise RuleError('Invalid timeframe') from exc
        if any(type(v) is not int or v not in UNITS for v in values): raise RuleError('Unsupported timeframe')
    if len(set(values)) != len(values): raise RuleError('Duplicate filter')
    return values


def scan(paths: list[Path], rules: tuple[tuple[str, dict], ...], output: Path, *,
         markets: str = 'all', units: str = 'all', last: int = 0, overwrite: bool = False) -> dict:
    if not paths or type(last) is not int or last < 0:
        raise RuleError('Invalid database list or candle count')
    chosen_markets = _parse_csv_tokens(markets, market=True)
    chosen_units = _parse_csv_tokens(units, market=False)
    if len(paths) > 8: raise RuleError('Maximum eight source databases')
    sources = [Path(p).resolve(strict=True) for p in paths]
    target = Path(output).absolute()
    if any(target.resolve() == source for source in sources):
        raise RuleError('Results cannot replace source database')
    if target.exists() and not overwrite:
        raise FileExistsError('Output exists; choose --overwrite explicitly')
    if not target.parent.is_dir():
        raise RuleError('Output directory does not exist')
    all_keys = _metric_keys(rules)
    stats = {'databases': 0, 'pairs': 0, 'candles_processed': 0, 'matches': 0}
    fd, temporary = tempfile.mkstemp(prefix='.custom-pattern-', suffix='.tmp', dir=target.parent)
    tmp = Path(temporary)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            for source in sources:
                if not source.is_file(): raise RuleError('Source is not a regular SQLite file')
                db = sqlite3.connect(source.as_uri()+'?mode=ro', uri=True, timeout=30)
                try:
                    db.execute('PRAGMA query_only=ON')
                    columns = {row[1] for row in db.execute('PRAGMA table_info(candles)')}
                    required = set(('market','unit','utc','kst')) | set(PRICE_FIELDS)
                    if required - columns: raise RuleError('Input candles schema missing required OHLC columns')
                    filters = []
                    params = []
                    if chosen_markets is not None:
                        filters.append('market IN ('+','.join('?' for _ in chosen_markets)+')')
                        params.extend(chosen_markets)
                    if chosen_units is not None:
                        filters.append('unit IN ('+','.join('?' for _ in chosen_units)+')')
                        params.extend(chosen_units)
                    where = ' WHERE '+' AND '.join(filters) if filters else ''
                    group_sql = 'SELECT market,unit,COUNT(*) FROM candles'+where+' GROUP BY market,unit ORDER BY market,unit'
                    pairs = db.execute(group_sql, params).fetchall()
                    stats['databases'] += 1
                    stats['pairs'] += len(pairs)
                    for market, unit, total in pairs:
                        active = {key: Indicator(key) for key in all_keys}
                        threshold = total-last if last else 0
                        rows = db.execute('SELECT utc,kst,open,high,low,close FROM candles WHERE market=? AND unit=? ORDER BY utc ASC', (market, unit))
                        for index, (utc,kst,opening,high,low,close) in enumerate(rows):
                            values = (opening,high,low,close)
                            if any(type(v) not in (float,int) or not math.isfinite(v) or v<=0 for v in values) or high<low:
                                raise RuleError('Invalid OHLC values in source; no output published')
                            bar = dict(zip(('open','high','low','close'), values))
                            for indicator in active.values(): indicator.push(bar)
                            stats['candles_processed'] += 1
                            if index < threshold: continue
                            for name, when in rules:
                                if _eval(when, active) is True:
                                    writer.writerow({'source': _csv_safe(source.stem), 'market': market, 'unit': unit,
                                                     'utc': _csv_safe(utc), 'kst': _csv_safe(kst),
                                                     'close': close, 'rule_id': name})
                                    stats['matches'] += 1
                finally:
                    db.close()
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(tmp, target)
        else:
            # Same-directory hard link creates an exclusive final filename: no race overwrite.
            os.link(tmp, target)
        return stats
    finally:
        tmp.unlink(missing_ok=True)


def _csv_safe(value: object) -> str:
    """Avoid formula execution when CSV is opened in a spreadsheet."""
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text[:1] in ('\t', '\r', '\n') else text


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description='Read-only custom candle rules (safe JSON DSL)')
    parser.add_argument('--db', type=Path, required=True, action='append', help='Read-only SQLite source, may repeat')
    parser.add_argument('--rules', type=Path, required=True, help='Absolute path to JSON rules')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markets', default='all')
    parser.add_argument('--units', default='all')
    parser.add_argument('--last', type=int, default=0)
    parser.add_argument('--overwrite', action='store_true')
    args=parser.parse_args(argv)
    try:
        result=scan(args.db, load_rules(args.rules.resolve()), args.output,
                    markets=args.markets, units=args.units, last=args.last, overwrite=args.overwrite)
    except (OSError, sqlite3.DatabaseError, RuleError, ValueError) as exc:
        print('ERROR: '+str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
