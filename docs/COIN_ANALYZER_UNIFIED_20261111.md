# Coin Analyzer — Unified entry and offline report (2026-11-11 KST)

## Goal and selected design
Two independent already-implemented scanners existed with different JSON contracts:
- `custom_formula_scanner.py`: one customer formula, full OHLCV/trade_value, canonical SHA256 in CSV; original feature branch implementation preserved.
- `custom_rule_engine.py`: batch of 1–16 independent formulas, shared indicator evaluation on a single read-only stream, tagged CSV; experimental on this branch.

**Selected:** one customer-facing CLI `coin_analyzer.py` that dispatches to the existing fully tested single or batch engine without reimplementing their formulas. Safer and cheaper than rewriting both algorithm implementations on deadline. The two JSON inputs/output columns remain different and are explicitly named in the CLI. A later common DSL is desirable but would add migration/regression risk now.

Alternative: one rewritten universal evaluator. Rejected this phase: difficult to demonstrate legacy parity and preserve volume/trade_value and canonical SHA behavior in the available runtime. No dynamic Python rule execution or network.

## Run — Python 3.11+
One formula (existing, not duplicated):
```
python coin_analyzer.py --db "C:\\market\\upbit_candles.sqlite3" --rule custom_rule_single_example.json --output "C:\\reports\\signals.csv" --markets BTC,ETH --units 1,3,240 --last 10000
```
Up to 16 rules on one candle stream (existing batch JSON input):
```
python coin_analyzer.py --db "C:\\market\\upbit_candles.sqlite3" --rules examples/custom_rules_batch.json --output "C:\\reports\\signals.csv" --markets BTC --units 1,5,240 --last 10000 --max-matches 500000
```
Repeat `--db` for distinct exchange sources; batch disallows ambiguous duplicate file stems. Both modes are offline/read-only and require completed OHLC from the existing collector schema. Rule-only syntax verification does not open SQLite:
```
python coin_analyzer.py --rules examples/custom_rules_batch.json --validate-only
```
Customer-readable static HTML report (reads already-generated CSV, never opens DB):
```
python coin_report.py --csv "C:\\reports\\signals.csv" --output "C:\\reports\\signals.html"
```
Optional Windows `.bat` wrappers forward the same flags using `py -3` (Python installation needed). Neither is a packaged/no-install EXE.

## Safety and actual function
- Batch now has row cap (default 500,000; hard max 1,000,000), duplicate SQLite path / ambiguous source label guard, `.csv` extension guard, KRW-only result filtering, finite positive OHLC bounds including high>=open/close and low<=open/close, timestamp presence, fail-closed rollback.
- SQLite `mode=ro`, `PRAGMA query_only=ON`; CSV is UTF-8 BOM, symlink rule JSON rejected, limited JSON DSL and no Python eval/import of user rules. Existing CSV is not overwritten unless `--overwrite`.
- HTML report supports original single and batch CSV header layouts; escapes every dynamic value, disables network/script via CSP, shows total rules/markets and bounded first 120 rows, computes aggregate counts through up to 1,000,000 signals. HTML creates via temporary file and hard link; no pre-existing report overwritten unless explicit flag. Source CSV remains unchanged.
- Reporting is a **separate command**; a generated CSV is not rolled back if a later separately invoked report fails. No auto-trading, P&L claims, chart UI, live exchange API, customer DB migration or remote uploads.

## Verification
- Exact modified batch engine and three new test modules used in local Python3.13.5 Linux strict ResourceWarning run:
  `python -W error::ResourceWarning -m unittest -v test_custom_rule_engine.py test_customer_ready_batch.py test_coin_analyzer.py test_coin_report.py`
- **57/57 PASS, 0 FAIL/0 SKIP**: 23 original batch +11 batch hardening +10 unified CLI +13 HTML reporting. Real temporary SQLite / CSV E2E, original DB hash invariance, XLS/CSV-injection string encoding, rollback, large cap and untrusted HTML escaping.
- Single-formula mode dispatch is unit-tested with a stub only; the full **actual legacy single-scanner source and its 15 tests were not reconstructed in this runtime**, so same-SHA end-to-end cross-contract performance/parity is NOT VERIFIED. Its existing GitHub `custom_formula_scanner.py` source is not modified.
- Full collector/test suites, Windows Python3.11, user E: original ~3GB database, packaged EXE, exact chart parity, and exchange data licensing all **NOT RUN**. Release HOLD.
- Source/test Git object SHA must match the tested local `git hash-object` values after push, and branch HEAD/author must be verified. New files on separate feature/custom-batch-rule-engine only, draft PR #1 remains unmerged.

## Readiness judgement
The original command center product-completion estimate was 50%. Working batch search, unified customer CLI, strong CSV safety and local HTML summary add material product functionality, but **70% final-product readiness cannot be asserted from synthetic-only tests**. Actual Windows/tested real DB/packaging and license/customer delivery gates remain outstanding. This result is an integration milestone, not release approval.
