# P3 — Safe customer formula template builder (2026-11-11 KST)

## Goal and trade-off
The buyer should not have to hand-author JSON or run arbitrary Python formulas. Choices: (A) new GUI/desktop framework and installer (more dependency cost, larger Windows QA), or (B) tiny Python3.11+ console form that emits the **same vetted P1 JSON DSL** for the P2 scanner (offline, low risk). B was selected as the present intermediate milestone; no claim that this equals a polished paid executable.

## Supported templates
\`sma_cross\`, \`ema_cross\`, \`bb_upper_breakout\`, \`bb_lower_recover\`, \`close_above\`. User can parameterize periods, thresholds and Bollinger sigma within bounded values. Generates a local JSON file with the same P1 \`{"version":1,"name":"...","when":...}\` schema. Never opens a candle DB or uses exchange APIs. Existing JSON output is rejected, no overwrite. The user can still supply fully custom complex allowed JSON rules through the P1/P2 engines.

## Run
\`python custom_formula_builder.py --interactive\` (or optional Windows BAT, **not Windows-verified**).
CLI example: \`python custom_formula_builder.py --mode sma_cross --name "GC 20-60" --fast 20 --slow 60 --output rule.json\`.
Then \`python custom_formula_batch.py --db "C:/candles/upbit_candles.sqlite3" --rules rule.json --output results.csv --progress\`.

## Evidence
Linux Python3.13.5: \`python -W error -m unittest -q test_custom_formula_scanner.py test_custom_formula_batch.py test_custom_formula_builder.py\` **36/36 PASS** (P1 15, P2 14, P3 7), \`python -m compileall -q\` PASS. P3 tests exercise all five templates through the P2 real synthetic SQLite runner, invalid params, file-exclusive creation, no DB overwrite, CLI and interactive prompts. The first local 36-test run revealed a positive-price default mismatch; corrected default before retesting 36/36 PASS. Exact Git blobs builder \`57b9514482b4168151300f751357b0faf8104a55\`, tests \`8798d99476db4a72ce7adb8b05ceb54c7fa2a2d6\`. Full old-pattern/collector regression, Windows cmd/Python3.11/EXE, real owner DB ~3.6GB and commercial license **NOT RUN**.

## Release gate
Coin final-product estimate **50% unchanged**, goal 70% **not verified**; RELEASE HOLD. No main/collector/DB data/other product or Production change. P2 built atop P1; independent draft PR #1 stays separate and unmerged.
