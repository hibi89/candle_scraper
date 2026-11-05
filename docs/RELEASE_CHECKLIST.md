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
