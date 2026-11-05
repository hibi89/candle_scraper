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
