# P5 — Offline customer results ZIP packaging (2026-11-11 KST)

## Customer goal and alternatives
The canonical product has one P1/P2 bounded formula DSL, a P3 static HTML report, and P4 rule/CSV SHA256 receipt. Customers should not have to manually execute three separate commands or accidentally overwrite a previous deliverable.

- A: write CSV/HTML/receipt directly into the chosen results folder. Fast and simple, but a late report error can expose a partial deliverable.
- B (selected): run on a temporary same-parent staging directory, validate scan/report/receipt consistency, then build a fixed-filename ZIP and publish with an *exclusive* hardlink. No unapproved installation, APIs or external data transfer. Slight disk-space overhead; supports an unchanged source DB.

## New source
- \`coin_customer_bundle.py\`, P5 feature only, imports canonical \`custom_formula_batch\`, existing \`coin_report\` and \`coin_evidence_receipt\`.
- Exactly five allowed archive entries: \`rules.json\`, \`signals.csv\`, \`report.html\`, \`evidence.json\`, \`manifest.json\`.
- 1..8 source DBs, 1..16 formulas under the P1/P2 contract, optional market/timeframe/last-N filters, 500k default / <=1m max matches. No customer DB bytes placed in ZIP.
- Reject missing/duplicate DBs, symbolic-link rule file, existing output ZIP, corrupt rule JSON/OHLC, excessive matches, report failure, receipt failure or mismatching match counts; no ZIP is published on failure. Stage and temporary ZIP cleaned on Python exceptions. ZIP CRC verified before exclusive publication.
- \`manifest.json\` holds counts and result/rule hashes but not the source DB absolute paths. The rule JSON and CSV *do contain user-provided inputs and historical results*, so the final ZIP is sensitive and must remain local until user intentionally shares it.
- No guarantee against sudden machine power loss, storage device faults or concurrent SQLite WAL writer changes. Same-volume Windows hardlink publication/antivirus behavior remains unverified.

## Usage
\`\`\`powershell
py -3.11 coin_customer_bundle.py --db "E:\업비트 캔들긁어오기\upbit_candles.sqlite3" --rules "C:\rules\customer.json" --output "C:\reports\customer_results_001.zip" --markets BTC,ETH --units 1,5,240 --last 10000
\`\`\`
The result ZIP is produced only when all analysis and verification stages pass. Extraction is manual. Python 3.11+ is still required; this is not a Windows EXE and not an approved paid customer release.

## Actual verification and limits
Local Linux Python 3.13.5 in a distinct working folder:
\`python -W error::ResourceWarning -m unittest -q test_custom_formula_scanner.py test_custom_formula_batch.py test_custom_formula_builder.py test_coin_evidence_receipt.py test_coin_customer_bundle.py\`: **60/60 PASS, 0 FAIL, 0 SKIP**; P1=15 P2=14 P3 builder=7 P4 receipt=10 P5 ZIP=14. \`compileall\` for P5 PASS. The 14 P5 tests use actual P2 SQLite and P4 receipt, but HTML comes from a separately tested local \`custom_formula_report.py\` adapter to the P3 \`coin_report.render_csv\` API because the full GitHub P3 checkout was unavailable in this runtime.

- Core source blob \`85a74ef719a8fe774612cc0b66fa09baf77a26f2\`; test source blob \`24286bbabaa1b4eb1b5caa51fb1eae8f5e4adf60\` match local git-hash-object.
- **Not run**: exact GitHub P3 report integration with P5, P3 full existing four tests, whole-branch \`unittest discover\`, Windows native Python3.11/Windows 10/11, 3.6GB actual user DB, chart parity, EXE/installer or policy/licensing review. No GitHub Actions minutes consumed, no Production/Vercel.

## Score and next
Original command-center provisional completion was 65% for P1~P4. P5 customer packaging is incremental product delivery functionality. Credit is at most +3%p **provisional engineering progress to 68%** pending the exact P3/P5 integration and all-source regressions; do not certify 70% or release. Commercial RELEASE HOLD. Draft PR #1 alternate JSON DSL remains unmerged.

Next from a complete authorized checkout:
\`\`\`powershell
py -3.11 -W error::ResourceWarning -m unittest -v test_custom_formula_scanner.py test_custom_formula_batch.py test_custom_formula_builder.py test_coin_evidence_receipt.py test_coin_analyzer.py test_coin_report.py test_coin_cli_dispatch.py test_coin_customer_bundle.py
py -3.11 -W error::ResourceWarning -m unittest discover -p "test_*.py"
\`\`\`
Then run P5 on a **copy** of the customer-approved local SQLite, open HTML and verify chart signals. Keep original DB/WAL/SHM untouched. Roll back P5 with a regular Git revert without affecting collector main.
