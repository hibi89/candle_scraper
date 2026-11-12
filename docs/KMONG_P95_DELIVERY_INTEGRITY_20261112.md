# Kmong Coin Candle Collector — P95 customer ZIP integrity (2026-11-12 KST)

## Scope and score
- Baseline: productization 94%, separately tracked collector technical 99% at main 1f976770db4797bcaa846ed32962e306318971ca.
- New scope: one additional customer-delivery assurance point (+1%p provisional productization, target 95%) for fail-closed byte-exact package verification. This is a scoped internal estimate, NOT formal retail acceptance, Windows 10/11 certification, commercial permission, or release.
- RELEASE HOLD regardless of score. Upbit paid connected EXE terms restrict redistribution, Bithumb commercial permission remains unverified, human approval, actual consumer Windows and Defender/SmartScreen remain outstanding.

## Design comparison
- A. Modify existing verify_customer_packages.py directly: fewer files, but this workflow path triggers billable-risk Windows Actions on main and couples new audit to EXE smoke; risk to existing 3-edition packaging.
- B. Add a separate static, standard-library audit at the final build stage: offline, zero exchange API requests, no DB writes, testable on Linux, 3-edition baseline preserved. Selected B for cost, reversibility, and independent failure reasons.

## Implementation
- New audit_customer_packages.py checks all 3 ZIP edition names; enforces exactly 2 ordered files (the Windows-verified matching EXE and original source-derived Korean guide); rejects duplicate/extra entries, CRC failures, altered EXE, modified guide even if keywords remain, ZIP comments, leading/trailing payload, symlinks/encryption/non-deflate entries, size anomalies, missing or surplus editions.
- It calls existing make_customer_packages.verify_products() to compare the local EXE to its prior verified Windows manifest. It emits only ZIP SHA-256 + a mandatory HOLD message; no legal grant, signing, customer issuance, network or exchange calls.
- build_windows.bat appends stage 6 of 6 and fails the build on audit error. The 3 EXE builds, Windows smoke, 3 ZIP builds and prior 5 phases are left as they were.
- New test_v20_customer_zip_integrity.py supplies three independent synthetic EXEs/manifests/ZIPs, tests clean baseline plus 9 corruption classes; it never accesses personal databases or real API.

## Evidence
- Local Python 3.13.5: python -m unittest -q test_v20_customer_zip_integrity => 10 PASS / 0 FAIL / 0 SKIP.
- python -m compileall -q audit_customer_packages.py test_v20_customer_zip_integrity.py => PASS.
- Local test used an interface-compatible test-only make_customer_packages stub; the actual GitHub make_customer_packages.py was read and its PRODUCTS, guide() and verify_products() contracts checked. Not the full actual Windows run or end-to-end real EXE/ZIP test.
- Git Blob parity of local execution and committed source: audit 36959c113e4e3043ca8a6d68673165c26d16a85e; test 4136b09620c1478d5d1621c85a93d781bd446509.
- Earlier true Windows baseline at main functional SHA 9e0632890c5621f4756e9ca7328480d860b2b710, Actions #42038795999: 147 PASS, 3 real EXEs/3 ZIPs and live API probe. This prior success does NOT validate the new build-stage 6.

## Outstanding and rollback
- Run the exact feature SHA in an approved Windows runner/owner machine with installed Python3.11 and PyInstaller6.16.0: full unittest (expected prior147 + new10 = 157), build_windows.bat stage 1–6, 3 extracted customer ZIP EXEs, actual static ZIP bytes, Korean path, and no unexpected DB modification. Do not infer success until observed.
- Then validate Windows10/11, Defender/SmartScreen, license and rights, signed/customer handoff and explicit owner release GO. NO paid runner/distribution without separate authorization.
- Existing main 1f976770db4797bcaa846ed32962e306318971ca remains untouched. Feature branch is reversible by ignoring/closing it; all previous packages and local customer SQLite untouched. Existing Windows workflow triggers only on main tracked paths and did NOT auto-run for this branch.

Classification: P95 provisional on internal code-and-test scope; user-sale release HOLD; native integrated acceptance pending.
