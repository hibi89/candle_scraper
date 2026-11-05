# Latest — 2026-11-05 22:30 KST

- [CI #42035893214](https://github.com/hibi89/candle_scraper/actions/runs/42035893214), source SHA `75bdd6ea6d78887200b93f29fab9b389c3054e3f`, Windows Server 2022 Python3.11.9/PyInstaller6.16.0, **completed SUCCESS**.
- **144/144 offline tests PASS**, EXE 3/3 startup, ZIP 3/3 independent execution, Hangul/space directory EXE 3/3 menu [6] read-only/no DB creation, EXE 3-edition live API menus PASS.
- Matrix in `test_v18_market_matrix.py`: 5 markets × 11 timeframes × 2 providers; each pair 206 completed synthetic candles, then +1 update, exported 55 CSVs/exchange, no duplicates, one-market failure recovery. New shared short/no-header 429 gate tests.
- Failed intermediate [#42035413941](https://github.com/hibi89/candle_scraper/actions/runs/42035413941): test fixture Windows SQLite handle leak and obsolete 429 call-count assertion; both repaired. Passing intermediate [#42035667647](https://github.com/hibi89/candle_scraper/actions/runs/42035667647) 144/144.
- Latest ZIP internal artifact `13418123592`, live EXE evidence `13417524024`; expire Nov 19 KST. GitHub artifact archive sha256 `46651307e7fad65502f2bb46e0d6ba29284afb5df09ddc310748e099ebfa68eb`. Independent ZIP digests: Upbit `e308076d4e8dd85b829361cb5ee16d0b6710f56a92d9307788aa24d82f0664f3`, Bithumb `5bf396c39fbae5c3bdc82fab0bbecb0c11d098396e7739171fed74aec0079cd9`, both `7b253ba2e058a42aa72a90d606efce1238cce6c7a15eb50907fe502842baf985`; all ZIP CRC PASS.
- No customer Win10/11 or antivirus evidence, no all KRW/11 timeframes real prolonged collection, no exchange distribution permission. **SALES RELEASE HOLD**.

---

# 2026-11-05 22:15 KST — Latest release-safety Windows integration SUCCESS

- Run [#42033704161](https://github.com/hibi89/candle_scraper/actions/runs/42033704161), functionality source SHA `da582b1c4c6db6740c08d2ddce7788d8e658724d`, Windows Server 2022 Python3.11.9/PyInstaller6.16.0.
- Unittest **140/140 PASS**; `compileall -q .` PASS; 3/3 EXE startup checks; 3/3 individually unzipped customer EXEs start/exit and read-only live-API menus PASS for both exchanges.
- Added safety cases for Retry-After numeric/HTTP-date, invalid/negative values, fifth/final retry long cooldown, shared cooldown blocking 5 worker threads, resume after expiry, non-retryable 403.
- Customer ZIP hashes: Upbit `32cc7ee09682410bc0205c88b464bb1667d34eeb167f024215e90d0ea935885f`; Bithumb `bc22cab45bdd2579c4cc5cd06733dbf64441942de1f5911097e3d42ce0cb4f81`; Both `26a27c2c063579d0c39ee4f9b2669d36ec6a0583686d01127d6ec35ffa57e711`.
- Private internal artifacts (not a customer release): ZIP ID `13417935853`, live EXE evidence ID `13418225561`; expire 2026-11-19 22:13–22:14 KST.
- **RELEASE HOLD** — Windows10/11 real client, full-market long-run and API commercial distribution rights not verified. Market data/raw user DB never published to GitHub.

---

# 2026-11-05 21:59 KST — Two real 10,000-minute-candle live recovery tests PASS

- [GitHub Actions run #42031303797](https://github.com/hibi89/candle_scraper/actions/runs/42031303797), SHA `f6ba8768dcd59e985354a11e4d98e7a7626d4e46`, SUCCESS; both public-api and live-history-10k jobs PASS on Windows Server 2022 Python 3.11.
- Each exchange uses *only* KRW-BTC 1-minute public candles with a hard cap of 70 per-exchange logical API requests, achieved 53 each.
- **Upbit:** 399 actual candles committed -> injected crash on API page 3 -> resumed exactly to 10,000; initial second run idempotent; update +0; SQLite integrity/PK uniqueness and CSV 10,000 rows PASS.
- **Bithumb:** 399 actual candles committed -> same injected crash -> resumed 10,000; initial second run idempotent; update +1 / 10,001 total; SQLite integrity/PK uniqueness and CSV 10,001 rows PASS.
- No customer DB accessed, CSV and SQLite remain in automatically deleted ephemeral Windows runner. CI archive contains **counts-only** JSON artifact ID `13415414502`, expires Nov 19 2026 21:58 KST.
- Not an all-KRW-market test or an 11-timeframe 10,000-count per pair test, and not a rights-to-resell API license; **release HOLD**, see `docs/COMMERCIAL_API_POLICY.md`.

---

# 2026-11-05 21:49 KST — Final Windows customer-EXE live check

- [run #42029964305](https://github.com/hibi89/candle_scraper/actions/runs/42029964305), SHA `40c0afe32e4eecda64ada9021aad35a8d1cd96fd`, Windows Server 2022 Python 3.11.9, PyInstaller 6.16.0, **SUCCESS**.
- Offline unittest 127/127 PASS; independently launched all 3 customer ZIP EXEs, 3/3 PASS, no DB on startup.
- Actual customer ZIP program live API menu `[5]`: Upbit only 11 units PASS, Bithumb only 11 units PASS, Both edition Upbit 11 and Bithumb 11 PASS. Real public HTTPS first page and historical cursor page 2; read-only, temp folders only.
- Latest ZIP SHA256: Upbit `6985a6ae9c8ed094161db16863af7ce3d52cbc60862c85325efb27649db7e314`, Bithumb `5bd484fda1e6bfdd9be20527db4139bb958d2b7cdd3213c995df5dee390ae741`, Both `0e7ccc6850e67a36b2d6e71b6acc42611dd7ceb10026f8f51560f3737bb903f0`.
- CI Artifacts: Windows ZIP ID `13416505378` and EXE-live evidence ID `13416380913`, expire 2026-11-19 KST.
- **Sales HOLD**: Windows 10/11 customer deployment, prolonged all-KRW market live data/backfill, commercial API/data use rights NOT VERIFIED.

---

# Test evidence — updated 2026-11-05 21:40 KST

## Windows build and actual ZIP runtime — PASS
- GitHub Actions [#42027942187](https://github.com/hibi89/candle_scraper/actions/runs/42027942187), commit `f39932db1c5253c38fc8e0521e419da0920237fa`, **SUCCESS**.
- Windows Server 2022 / Python 3.11.9 / pinned PyInstaller 6.16.0; `python -m compileall -q .` PASS; `unittest discover` **127/127 PASS, 0 FAIL**.
- `build_windows.bat` five stages PASS; independently launch 3 EXEs and 3 unzipped customer ZIPs, no DB created on startup.
- ZIP SHA256 (Upbit/Bithumb/Both): `bdea04ada699c1926b6e3990804fa896298c5392b2fa6e5298c541e0e6d72e4c` / `77c0bbab861d0eed1118ee033fb6e0932972b1632e817aa336780f0e7d62cbb2` / `8212f954d708041fa64584c27dff4e3f61aff86a4175e963fd9ce273381c5154`.
- Artifact ID `13414129062` (private, 14-day expiry); ZIP not yet a commercial release.

## Live Upbit/Bithumb public API and disposable DB — PASS
- [GitHub Actions #42028865266](https://github.com/hibi89/candle_scraper/actions/runs/42028865266), commit `5a503c9f214e11ae77ebfb264478bef3b4cafa00`, **SUCCESS**.
- Upbit KRW markets observed: **300**. Bithumb KRW markets observed: **488**. Market lists only; not all symbols harvested.
- For each exchange: KRW-BTC 11 types (month/week/day/240/60/30/15/10/5/3/1), first+second page validation, bounded 11-day-candle initial collection, update, temporary SQLite PK uniqueness and UTF-8 BOM CSV all PASS.
- Only public HTTPS endpoints; no API credentials, private endpoints, trades, customer DB, raw market-data artifact, or full 10,000-candle live extraction.
- Temporary Windows SQLite handle cleanup fixed with `contextlib.closing`; first smoke job failed at file cleanup despite all data checks PASS, final job passed.
- Evidence artifact ID `13415620777` (private, 14-day expiry).

## Still NOT VERIFIED
- Consumer Windows 10/11 actual environment/Defender/SmartScreen; all-symbol 10k full historical collection on both live exchanges; prolonged operation / rate-limit recovery against real providers; commercial data-use terms. Sales RELEASE HOLD.

---

## Historical offline-only evidence (superseded test scope)


- Repeated in this environment from the v1.6.1 source: `python -W error::ResourceWarning -m unittest discover -p 'test_*.py' -q` → **127 tests, 0 failures, 0 errors**; process exit status 0.
- Python compiler: `python -m compileall -q .` → PASS in prior v1.6.1 package test; repeat during GitHub import check.
- Runtime: Linux Python 3.13.5 (not Windows); tests include local mock HTTP server for exchange-shaped pages. Any fabricated test server response is **not** live exchange evidence.
- Coverage previously recorded by tests: 206 candle pagination with 200/page, KST/UTC validation, malformed pages and symbols rejected, atomic SQLite/PK schema checks, 5 concurrent tasks DB init, separate exchange DBs, 10,000 initial plus 3 incremental, 400 before interruption + 9,600 resumed, menu, simulated package ZIP integrity.
- **NOT RUN:** Windows 10/11 native one-file EXEs and the actual customer ZIP executable launch; authentic exchange HTTPS full collection; continuous operation; antivirus/signed installer inspection; deployment (not applicable).
- Release gate remains HOLD. The 85% figure is project owner estimate rather than a measured code coverage percentage.

This report records test execution and does **not** assert real-exchange success from local mocks.
