# P6 — source-exact 101-test scoped regression (2026-11-11 KST)

## Scope and purpose
This is additional evidence for the previously recorded **70% provisional engineering milestone**, NOT an increase beyond 70% and NOT a customer sales release. The source commit was checked at `c8a1637ab4d07db577d4d971ccad5f5adac22593`; the P6 docs checkpoint was `62b5ceb6230ac0e404dab95e03b13838ae52f116`. This verification uses exact original GitHub source and tests, not an adapter: all **19 Python files** below matched their Git Blob SHA-1 (0 mismatches), including the real `coin_report.py`, `coin_analyzer.py`, P5 ZIP packager and P6 selftest.

## Exact executed command and output
Local ephemeral Linux Python **3.13.5**:
```sh
python -W error::ResourceWarning -m unittest -q \
  test_custom_formula_scanner.py \
  test_custom_formula_batch.py \
  test_custom_formula_builder.py \
  test_coin_evidence_receipt.py \
  test_coin_customer_bundle.py \
  test_coin_report.py \
  test_coin_cli_dispatch.py \
  test_coin_analyzer.py \
  test_coin_bundle_primary_integration.py \
  test_coin_customer_e2e_p5.py \
  test_coin_selftest.py
python -m compileall -q \
  custom_formula_scanner.py custom_formula_batch.py custom_formula_builder.py \
  coin_evidence_receipt.py coin_customer_bundle.py coin_analyzer.py coin_report.py coin_selftest.py \
  test_custom_formula_scanner.py test_custom_formula_batch.py test_custom_formula_builder.py \
  test_coin_evidence_receipt.py test_coin_customer_bundle.py test_coin_report.py \
  test_coin_cli_dispatch.py test_coin_analyzer.py test_coin_bundle_primary_integration.py \
  test_coin_customer_e2e_p5.py test_coin_selftest.py
python coin_selftest.py
```
Results: **101 tests / 101 PASS / 0 FAIL**, 0 test skips; compileall exit code **0**. `coin_selftest.py` returns `PASS_SYNTHETIC_ONLY` with two modes and two verified receipts, `scanned_real_customer_db=false`, `ready_for_customer_data=false`. Test groups: P1 15 + P2 14 + builder 7 + P4 receipt 10 + P5 ZIP 14 + P3 report 13 + P3 CLI dispatch 8 + actual analyzer E2E 4 + P6 exact bundle 5 + P6 customer E2E 7 + P6 selftest 4 = **101**.

Synthetic integration verified read-only SQLite source SHA unchanged, P1/P2 CSV parity, original P3 offline HTML, canonical formula receipt + verify, P5 ZIP five contents + CRC and extraction, multi DB including Hangul/special chars, controlled failures and protection of previously created outputs. No external exchange HTTP, no credentials and no original customer data.

## Git Blob exactness
```text
custom_formula_scanner.py         8b98d12556767e877c2bd360ee5b609e6ab3b047
test_custom_formula_scanner.py    75974dd5c656e74b1295f803216384d95d24220c
custom_formula_batch.py           97c6bef5871c1ead33ca95aabcac272b334dae3b
test_custom_formula_batch.py      452159c687b80fb091e22eb34534d1f624a67c82
custom_formula_builder.py         57b9514482b4168151300f751357b0faf8104a55
test_custom_formula_builder.py    8798d99476db4a72ce7adb8b05ceb54c7fa2a2d6
coin_evidence_receipt.py          cf9850f5fb1aae4fb7a64eb111c7098355296fa9
test_coin_evidence_receipt.py     8449fa430db59dfba794f236e6a31848ef6dfb53
coin_report.py                    f8e4a4cfed99d914291ba4c8b953143d9690026a
test_coin_report.py               56f86eb2098a6bbf1ca77266cd671ccf47b253b1
coin_analyzer.py                  a2cf74ae31ec201ca5c354036220144a5540d44f
test_coin_analyzer.py             dc5c75bc116bcb4b92fb48c603f904cf36b06a84
test_coin_cli_dispatch.py         5e3e11ef5ac43401aedb9bcde863edea8e11b45a
coin_customer_bundle.py           85a74ef719a8fe774612cc0b66fa09baf77a26f2
test_coin_customer_bundle.py      24286bbabaa1b4eb1b5caa51fb1eae8f5e4adf60
coin_selftest.py                  b399664df61965a845c3cb66463558882c2834f9
test_coin_selftest.py             35c7e385f041906c646518c23f729131419e79c1
test_coin_bundle_primary_integration.py 5bd9c993dca053ae36377ae5309d129a7a586848
test_coin_customer_e2e_p5.py     5438c6de358cbb4ec2c5d3215ba5bcca3fef9e8e
```

## Not verified / release gates
- Entire `candle_scraper` repo including unrelated collector and legacy `test_*.py`: **NOT RUN**. It must not be inferred from 101 focused tests.
- Native **Windows 10/11 + Python3.11**, actual client 3.6GB source with potentially active WAL/SHM, live chart parity, timing under customer volume, EXE packaging/SmartScreen, third-party market data license/terms, and actual customer acceptance **NOT RUN**.
- GitHub Actions whole-repo CI not triggered by this docs-only checkpoint, Vercel/Production **N/A**, feature branch not a commercial release.
- Draft PR #1 incompatible experimental DSL remains unmerged; original collector `main` and all user-created source files unchanged.
- File hashes/receipts demonstrate consistency under the local trust model, not cryptographic authorship or exchange truth.

## Current milestone, rollback, and next
The command center already records Coin Pattern Analyzer **70% provisional** (16 active product mean **64.6875%** if other 15 scores unchanged from the preceding 68% checkpoint). This report **adds confidence, not percentage**. Keep **RELEASE HOLD**. Source changes from other checkpoints can be reverted normally; this commit only adds verification docs. Next independent gate: fully authorized Windows copy and whole repository test discovery, then on a backup copy of the customer's DB compare chart signals and validate a packaged Windows executable before claiming any further progress or sales readiness.
