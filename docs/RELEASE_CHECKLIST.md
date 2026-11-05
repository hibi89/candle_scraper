# Release gate — Windows 3-edition candle collector

**HOLD** until all steps are evidenced at the same commit. This is a commercial product, not a live trading bot. No automatic payments, remote execution, or authenticated API access are needed.

1. Source integrity: checkout commit SHA, compare against `SOURCE_MANIFEST.json`, inspect `.github/workflows/windows-build.yml`, pin any altered dependencies before building.
2. Windows build: Windows 10 or later, Python 3.11+, PyInstaller 6.x installed with explicit owner permission. In a **new** writable directory run `build_windows.bat`. Expect offline unittest PASS, 3 EXEs built, startup/exit verification, 3 customer ZIPs, independent extract/start/exit check. Windows 2022 GitHub Actions manual workflow is an alternative but its artifact expiry means GitHub is not a long-term binary archive.
3. Test all 3 editions from **separate unpacked customer ZIPs** on a real Windows machine. Confirm menu displayed, cancel/exit works, no unexpected DB creation before collection, clean machine/Windows Defender warning behavior; do not disable protection.
4. Real endpoints: Upbit and Bithumb public KRW market list, 11 supported timeframe queries and historical page 2 `to` cursor. Check KST/UTC values, no partial candle storage and 429 backoff; avoid abusive API rates. Use **small** test limits first.
5. End-to-end: new test-only SQLite files for each exchange; initial collection, update (including >10k cumulative), stop/resume, failure/recovery, duplicate key count 0, CSV BOM and ordering; compare sample candles against exchanges.
6. Data safety: Never use or migrate the original personal `E:\업비트 캔들긁어오기\upbit_candles.sqlite3` in tests. Verify backup/restore and lock behavior. Do not distribute API keys, raw market datasets, or DB files.
7. Commercial: verify API terms/rate limits for user collection and any market data redistribution, check packaging and product description and support policy. User explicitly approves release.

### Report fields

Commit SHA / workflow run ID / artifact SHA256 / Windows OS / Python & PyInstaller version / PASS & FAIL counts / Upbit API / Bithumb API / three actual EXEs / three actual customer ZIPs / outstanding items / RELEASE or HOLD.

Vercel production deployment: **not applicable** (offline Windows EXE product).

## Commercial policy hard gate discovered 2026-11-05

- **UPBIT: confirmed contractual blocker** for paid programs using its Open API. Article 6(3) prohibits selling/paid distribution/use rights of API-connected programs; Article 5 restricts unlicensed commercial use of API data. See `docs/COMMERCIAL_API_POLICY.md` and the official Upbit terms linked there. **Upbit-only and both-exchange ZIPs must not be sold absent express permission or approved redesign.**
- **BITHUMB: commercial software redistribution not verified** solely by public documentation. Its no-key public API and rate-limit instructions are not licenses for third-party sales; confirm written rights.
- Release HOLD must remain even if all Windows/10,000-candle technical gates PASS. Permission, customer terms and commercial product scope need separate approval; this new policy issue takes priority over packaging or price listing.

### Verified technical evidence and remaining hard commercial gate (2026-11-05)
- Latest `main` functionality CI SHA `da582b1c4c6db6740c08d2ddce7788d8e658724d`: Windows tests **140/140**, 3 EXEs, independent 3 customer ZIP launches, live menus all PASS ([run #42033704161](https://github.com/hibi89/candle_scraper/actions/runs/42033704161)). Full 10k real BTC minute-candle resume per exchange PASS separately (#42031303797).
- **Do not release based on passing CI**: Upbit expressly restricts selling/distributing API-using applications; Bithumb third-party data-transfer rule is evidenced, but current EXE commercialization rights remain unverified. Request written permission; see `docs/COMMERCIAL_API_POLICY.md` and unsent `docs/LICENSING_REQUEST_DRAFTS.md`.
- Customer Windows10/11 non-admin, SmartScreen/Defender and all-market prolonged actual runs are **NOT_RUN**; user final approval required.

### Current final CI milestone — 2026-11-05 22:30 KST
- **Validated source SHA `75bdd6ea6d78887200b93f29fab9b389c3054e3f`** / [Windows CI #42035893214](https://github.com/hibi89/candle_scraper/actions/runs/42035893214) **SUCCESS**; 144 unit/integration tests, 3 EXEs/ZIPs independent startup, three Korean/space extraction paths and local DB inspection menus with no accidental DB creation, actual public API check for all three editions.
- 5×11×2 fake-provider matrix validates initial, incremental, CSV and one-pair recovery. Prior 10k BTC 1-min real sample for both exchanges remains valid. **These are not substitutes** for end-user Windows10/11/SmartScreen/Defender verification or policy permission.
- **RELEASE HOLD still mandatory**: Upbit API software paid redistribution restricted; Bithumb commercial software permission absent. No payment/marketing release/customer use until official written clarification and final user release authorization. Latest ZIP hashes/status in `STATUS.md`.
