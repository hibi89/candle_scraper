# Coin Pattern Analyzer P85 — scoped verification and handoff (2026-11-12 KST)

## Goal and design decision
The existing local P1–P6 signal analyzer was 70% provisional engineering. This is a new bounded offline Python 3.11+ signal-forward **event study** reading its eight-column signals CSV and the owner-selected frozen SQLite snapshot, without rewriting old scanners or touching collector/main. Compared A (embed new trading logic into P1/P2: one scan, risky source/DSL coupling and regression) vs B (independent read-only post-signal evaluator: second scan but no paid dependency and robust legacy preservation). Chose B.

## Implemented
- Completed signal candle at t, hypothetical next candle open at t+1, exit close of t+H, where H is 1..240 future bars. No same-bar fill or observed-future-dependent entry.
- Entry and exit each apply configurable fee (default 5 bps) and slippage (default 5 bps) separately. Settings are modeling assumptions, not real tier prices.
- Missing post-signal candle or end-of-file before H: CENSORED_GAP / CENSORED_EOF, excluded from net-return and positive-outcome counts.
- By exchange/market/timeframe/formula counts, mean/median/positive ratio/limits, optional chronology cutoff pre/post; not independent OOS validation.
- Offline Korean dark HTML, per-signal CSV, JSON statistics, output SHA256 manifest, reproducible contents. Only a brand-new results directory is permitted; no output overwrite.
- Input guard: exact P1/P2 CSV schema, matching source price/KST, valid increasing UTC, finite consistent OHLC, safe formula names, SHA256 IDs, 100000 signals, global 30m candles, no symlink, active WAL/SHM STOP, one unambiguous snapshot per exchange. SQLite URI mode=ro&immutable=1 on quiescent copy, query_only=ON.

## Exact verified evidence
Linux Python 3.13.5 local isolated test run: python -W error::ResourceWarning -m unittest -q test_coin_forward_eval.py => 25 tests PASS, 0 FAIL, 0 SKIP. compileall => PASS. Corrected 2 early synthetic fixture errors, then clean 25 PASS.
Locally executed file Git blobs matched GitHub feature source: coin_forward_eval.py 6d92c1c832a5899c6493229cb494f0ef9eca6f38; test_coin_forward_eval.py 03f35cb69f977836495adbfc5b82d11213efe27b. Actual 100000 synthetic 1-minute candle / 201 synthetic signal H5 read-only study took 0.41s with all 201 complete, unchanged SQLite input SHA256 and manifest. This is NOT real customer/3.6GB performance proof.

## Owner usage
Run original coin_analyzer.py on a legally permitted quiescent PRIVATE COPY to produce signals.csv, then:
    python coin_forward_eval.py --db PATH_TO_FROZEN_UPBIT_DB --signals PATH_TO_SIGNALS_CSV --out-dir PATH_TO_NEW_RESULT_FOLDER --horizon 5 --fee-bps 5 --slippage-bps 5 --split-utc 2026-07-01T00:00:00
For upbit+bithumb add a second --db with distinct exact source filename. Review report.html offline; preserve original CSV/DB. Do not use active collector SQLite. No actual orders, API or network.

## P85 provisional rubric and no-overclaim
P1-P6 preexisting 70% remains unchanged. New independent subsequent-candle evaluation +4%p, two-sided transaction cost +3%p, market/rule/time split statistics +3%p, bounded safe offline 4-artifact result and manifest +3%p, 25 scoped tests and 100k small benchmark +2%p, total 85% provisional engineering. This is subjective function-scope readiness, not 85% trade accuracy, sale readiness, or full system acceptance. Overlapping events are not independent; no order sizing, taxes, order fill, partial fills, liquidity, stop-loss, portfolio compounding, slippage validation, full out-of-sample or survivorship-bias correction.

## Remaining release gates
Old source-exact 101 P1-P6 tests and entire legacy collector suite NOT rerun on the new feature HEAD, although no old code was changed. Full GitHub Actions CI NOT RUN. Physical Windows10/11 Python3.11 and actual 3.6GB source copy with complete WAL checkpoint, chart/time/fee reconciliation, customer EXE package/SmartScreen, legal resale rights, commercial model, signed installer and pilot NOT VERIFIED. RELEASE HOLD / SALE NO-GO. Score will be revisited if full regression fails.

## Ten-point handoff
1. Goal/confirmed scope/stack: above.
2. Implemented functions and A/B decision: above.
3. Exact commands, 25 PASS/0 FAIL, 100k bounded benchmark, unverified legacy/Windows: above.
4. Current stopping point: engineering P85 provisional, customer release blocked.
5. Previous issues: two test-only synthetic fixture mistakes corrected; private unauthenticated clone not a supported source path; no blind retries. No identified production regression.
6. Repository/private Git source: hibi89/candle_scraper, base feature/candle-pattern-analyzer@8eafcb075959985c4f7aa0757c2e19e192ed27fa, new isolated feature/coin-pattern-p85-forward-eval-20261112. Added coin_forward_eval.py/test_coin_forward_eval.py, this docs file; final HEAD verify after writes.
7. No Vercel/Production; local Python3.13.5 synthetic only, Windows3.11 customer N/A/unverified.
8. Original collector/main/DSL, E: SQLite/WAL/SHM/CSV/ZIP/credentials unmodified; Git base branch backup and normal revert path, no secrets or external network.
9. Next: authorized checkout full P1-P6+legacy suite at exact source/QA SHA; owner-approved checkpointed large DB copy+chart/fee cross-check, Windows/EXE/rights/pilot, explicit owner release authorization.
10. Current date 2026-11-12 KST. Scope: exact Git blob matching and isolated local test/benchmark, not full commercial acceptance.
