# P2: One-pass customer rule batch using the P1 DSL — 2026-11-11 KST

## Decision
Keep **one canonical customer JSON formula contract**: the existing P1 \`{"version":1,"name":"...","when":...}\`. New P2 uses the same compiled formula/evaluator with a \`{"version":1,"rules":[{"name":"...","when":...}]}\` envelope; up to 16 rules / 8 local SQLite sources, 64 KiB JSON, no Python user-code execution. Compared alternatives: (A) independent batch DSL on draft PR #1 has richer independent implementation but duplicate customer syntax and maintenance; (B) reuse existing P1 compiler and evaluator in a new streaming batch runner. **Selected B** to preserve compatibility and lower regression risk. Draft PR #1 remains isolated and unmerged; no force push/merge.

## Implementation
- \`custom_formula_batch.py\` adds multi-formula single SQLite pass, per-source/market/timeframe isolated indicator state, full-history warm-up with last-N output filtering, progress and per-formula counts.
- The single/P2 CSV columns are identical and contain named formula + SHA256; byte-parity test with a single rule.
- Reject malformed UTC/KST/ohlc, invalid source schema, duplicate rule names, corrupt rules, excess matches. Use read-only SQLite, strict numeric validation, same-directory atomic CSV publication, and preserve an existing CSV without explicit overwrite.
- \`custom_formula_scanner.py\` handles malformed JSON field/indicator/operator types with ValueError instead of uncaught TypeError. No collector or previous fixed searchers modified.
- Usage: \`python custom_formula_batch.py --db SOURCE.sqlite3 --rules RULES.json --output matches.csv --progress\`, optional repeated \`--db\`, \`--markets BTC,ETH\`, \`--units 1,3,240\`, \`--last N\`.

## Evidence (no real customer data)
- Local Linux Python3.13.5: \`python -W error -m unittest -q test_custom_formula_scanner.py test_custom_formula_batch.py\`: **29/29 PASS**, 0 FAIL, 0 SKIP after fixing three reproduced malformed-JSON TypeErrors. \`python -m compileall -q\` source/tests PASS.
- Separate synthetic stress: 80,000 candles across four market pairs and 16 independent SMA crossover rules; 5,056 rows, ~3.2s elapsed in this Linux container; source SHA256 unchanged, CSV generated. This is NOT a benchmark for the real ~3.6GB Windows user DB.
- Exact checked Git blobs: P1 parser \`8b98d12556767e877c2bd360ee5b609e6ab3b047\`, new P2 runner \`97c6bef5871c1ead33ca95aabcac272b334dae3b\`, P2 tests \`452159c687b80fb091e22eb34534d1f624a67c82\`. The local P1 file differs from remote only by a trailing newline.
- Full repository collector/old pattern/future-retouch/dual-BB suite, Windows10/11 Python3.11, actual E: SQLite + WAL, chart parity, release EXE, commercial license and production **NOT RUN**.

## Gate and next steps
Keep **coin pattern final product 50%** until full-source regression, user-oriented rule selection, customer Windows/3.6GB DB, standalone packaging/license and usability gates pass; goal 70% is NOT yet certified. Keep RELEASE HOLD. Do not overwrite existing data/archives, merge draft PR #1, publish an EXE or run potentially billable CI without permission. No Vercel/production for this local tool.

## Git/rollback
Private \`hibi89/candle_scraper@feature/candle-pattern-analyzer\`; this file plus 3 code/test changes only, \`main\` collector untouched. Normal Git revert of the P2 commit is possible. Date 2026-11-11 KST.
