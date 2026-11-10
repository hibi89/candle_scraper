# P4 — Customer formula evidence receipt (2026-11-11 KST)

## Goal and decision
The current product already has canonical P1 single formula, P2 multi-formula, P3 generator/CLI and an offline HTML report. Duplicating an HTML report or merging the incompatible experimental batch DSL was rejected. Instead add a *separate* local evidence receipt: hash the exact customer result CSV and JSON rules, and check every CSV row's named formula and rule SHA256 against the canonical P1/P2 compiler. Unlike a plain file hash, this catches a mismatched rule even if the CSV is parsable. No source DB data is read by this feature.

## Usage
After generating results with the existing supported P1/P2 scanner:

\`\`\`powershell
python coin_evidence_receipt.py --csv "C:\reports\signals.csv" --rules "C:\rules\customer_rules.json" --receipt "C:\reports\signals.receipt.json"
python coin_evidence_receipt.py --csv "C:\reports\signals.csv" --rules "C:\rules\customer_rules.json" --verify "C:\reports\signals.receipt.json"
\`\`\`

The JSON receipt records the CSV file SHA256, rules file SHA256, each compiled formula's canonical SHA256 and row count, and overall match count. It contains no candle rows or customer DB paths. It is not an electronic signature, not external attestation, not a trading result, and not proof of exchange data accuracy. If an adversary replaces *all* files and receipt, local verification alone cannot establish authenticity; retain a trusted SHA separately.

## Safety
- Inputs must be ordinary non-symlink CSV/JSON files. P1/P2 canonical CSV columns are required; unknown or mismatched formula identities are rejected.
- Entire CSV checked with bounded 512MiB / 1 million rows / 4KiB per field; up to 16 named formulas from the existing JSON compiler. No Python eval or remote API.
- Source CSV and rule file identities checked before/after scan and hash. No source writes. Receipt created via exclusive same-directory hard link; existing receipt never overwritten.
- SHA256 is useful for integrity comparison, not a signature or assurance of customer data provenance.
- Previous collector/main, fixed patterns, and customer E: database remain unmodified. Release HOLD.

## Evidence and exact tested source
- Local Linux Python 3.13.5: \`python -W error -m unittest -q test_custom_formula_scanner.py test_custom_formula_batch.py test_custom_formula_builder.py test_coin_evidence_receipt.py\` **46/46 PASS, 0 FAIL** (P1 15, P2 14, P3 7, P4 10); compileall of P4 source/tests PASS.
- Actual in-memory SQLite P2 scan -> CSV -> receipt -> verify, original DB and CSV SHA256 unchanged; mismatched SHA/rules/file tamper, symlink input, bad CSV, failed verification and overwrite protection tested.
- Code blob \`cf9850f5fb1aae4fb7a64eb111c7098355296fa9\`, test blob \`8449fa430db59dfba794f236e6a31848ef6dfb53\` equal locally tested git objects. Existing GitHub P3 coin_analyzer.py / coin_report.py and full repository suite NOT RUN on this snapshot; Windows 10/11, consumer Python3.11, 3.6GB customer DB, chart parity, EXE/installer, licensing NOT RUN.
- No GitHub Actions forced; no Vercel/Production; product final-completion estimate remains **50%**, goal 70%, RELEASE HOLD.

## Next
Verify from one authorized complete feature checkout: \`python -W error -m unittest discover -p "test_*.py"\` and P3+P4 actual CLI integration. Then on customer-approved Windows copy, verify JSON rule -> CSV -> HTML/receipt flow and per-market chart parity, packaging/entitlements before reassessing final rate.


> **Central score reconciliation (2026-11-11 KST):** After this P4 feature was created, the command-center branch recognized **65% provisional product completion** for the P1–P4 canonical customer CLI/report scope. This separate evidence-receipt enhancement is **not an extra scored uplift**. 70% remains unverified; customer Windows, real DB, release/rights gates remain HOLD.
