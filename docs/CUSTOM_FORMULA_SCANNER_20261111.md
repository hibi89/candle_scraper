# Custom Formula Scanner — 2026-11-11 KST

Offline customer-specific candle rule search. This is a separate Python 3.11+ tool for the private \`candle_scraper@feature/candle-pattern-analyzer\` branch; the collector and fixed historical scanners are not modified.

## Tradeoff
- Dynamic Python user rules: fast to extend but executes arbitrary code against customer files. Rejected.
- Strict JSON conditions + allow-listed indicators: lower flexibility but safer and reproducible, without network/packages. Selected.

## Example JSON

\`\`\`json
{"version":1,"name":"SMA cross","when":{"all":[{"cross_up":[{"indicator":"sma","field":"close","period":20},{"indicator":"sma","field":"close","period":60}]},{"left":{"field":"close"},"op":">","right":{"indicator":"sma","field":"close","period":20}}]}}
\`\`\`

Supports direct field (open/high/low/close/volume/trade_value), finite constant, SMA, EMA, bb_upper, bb_lower, comparisons, cross_up/cross_down, all/any/not, up to 560 bars. Evaluates each market/timeframe independently using prior candles; no external code execution, future bars or API calls.

\`\`\`powershell
python custom_formula_scanner.py --db "E:\업비트 캔들긁어오기\upbit_candles.sqlite3" --rule my_rule.json --markets BTC,ETH --units 1,3,240 --last 10000 --output matched.csv
python -W error -m unittest -v test_custom_formula_scanner.py
\`\`\`

--db can repeat. --last 0 searches full stored history; a positive number filters output signals to the most recent N candles per pair but indicators still warm up using full history. Output UTF-8 BOM CSV with canonical-rule SHA256. Existing CSV preserved unless --overwrite. On failure, new CSV is not published; temp files cleaned. Default max 500,000 matches, max permitted 1,000,000. Full collector OHLC+volume+trade_value schema required. SQLite mode=ro/query_only protects DB at application level. Concurrent WAL writers not verified.

## Verification and release boundary

- Linux Python 3.13 local SQLite E2E/parser/security suite: 15/15 PASS, compileall PASS.
- GitHub source and tests checked in on feature branch; exact Git object should be read back to confirm provenance.
- Repo-wide regression, Windows 10/11, end-user ~3GB SQLite, large-history performance, chart parity, interactive/GUI and EXE packaging: NOT RUN.
- Customer arbitrary complex expressions, multiple report types, TA-Lib, backtest execution/fill modeling: NOT IMPLEMENTED. This is a bounded DSL MVP, not unrestricted formula entry.
- No paid release, automatic trading, real return guarantee. Existing collector release HOLD and exchange licensing restrictions remain.
- No market/customer database, binary, ZIP, keys, customer files, or credentials are committed.

## Recovery / next gates

Git revert can undo isolated new source/test/doc commits; main and legacy fixed scanners are unmodified. On authorized full checkout, run \`python -W error -m unittest -v test_custom_formula_scanner.py test_pattern_analyzer.py test_dual_bollinger_scanner.py\`, then repository-wide collector regression and Windows 3GB DB read-only performance/chart parity in a separate copy of source DB. Verify customer delivery EXE and licensing before product progress credit or release. Never infer 70% merely from 15 green synthetic tests.
