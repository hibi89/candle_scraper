# Custom Rule Engine Batch P0 — 2026-11-11 KST

## Feature boundary / design decision
The concurrent feature/candle-pattern-analyzer branch already added custom_formula_scanner.py (single formula per scan) and its own tests. This independent feature/custom-batch-rule-engine branch adds a DIFFERENT capability: execute up to 16 customer rules on the same read-only SQLite candle stream and export one tagged CSV. It is experimental until consolidated into the product. Dynamic Python plugins were rejected in favor of an allow-listed JSON DSL to avoid arbitrary code execution.

## Rule contract
JSON version 1, 1..16 named rules, <=32 KiB file, no duplicate JSON keys, NaN, symlinks or arbitrary expression execution. Supports OHLC price fields; SMA/EMA [period,field], Bollinger upper/lower [period,sigma,field], numeric thresholds, comparisons gt/gte/lt/lte/eq/ne/cross_up/cross_down, boolean all/any/not. Period 2..560, <=32 distinct metrics, <=64 clauses, max nesting depth 6. Unknown warmup is three-valued; NOT unavailable does not create a false signal. Cross checks prior and current prepared bars, no lookahead.

## Example and CLI
See examples/custom_rules_batch.json. Python 3.11+ standard library intended:
python custom_rule_engine.py --db "C:/candles/upbit_candles.sqlite3" --rules "C:/rules/custom_rules_batch.json" --output "C:/reports/matches.csv" --markets BTC,ETH --units 1,5,240 --last 10000
Repeat --db for additional SQLite sources. --last 0 searches all stored history; last-N filters emitted events, not indicator history. SQLite mode=ro and PRAGMA query_only. CSV UTF-8 BOM, source/market/unit/utc/kst/close/rule_id, formula-injection escaping. Output creation via exclusive same-directory hard link, explicit --overwrite uses replace, no partial report if source corrupt. No network, trading, customer DB mutation or external data transfer.

## Actual evidence
Exact local source Git blob: f0d16c11cdb8b57ec8cee52771206b2eb27fe705. Exact test Git blob: 6119c8302763e80d3e64481bbcb2b1f7b3b2c613. Local Linux Python3.13.5 strict ResourceWarning: **23/23 PASS, 0 FAIL/0 SKIP**, synthetic SQLite real SQL and CSV. Tests include SMA/EMA/BB and numeric thresholds, cross/warmup/boolean logic, multi-DB and filters, input DB hash preservation, existing CSV rollback, CSV injection, strict file/rule security and CLI.

## Unverified / release
Whole current product suite, overlap/integration with custom_formula_scanner.py, consumer Windows Python3.11 and real 3.63GB customer SQLite, GUI, EXE packaging, license and user acceptance NOT RUN. This **separate branch does not change the command-center 50% product final readiness**; substantive engine scope exists but commercial milestone uplift requires product-level integration. No Actions paid or Production, main or original collector changes. Release HOLD.

## Next
Compare single-formula and batch API semantics and choose one unified customer JSON contract. Avoid shipping two near-duplicate engines. Verify integration tests on authorized complete feature checkout, benchmark with synthetic large DB/Windows, create safe rule builder and result reports, then recalculate 50->70 milestones. Rollback this branch by closing PR, without force history or changing the existing working branch.
