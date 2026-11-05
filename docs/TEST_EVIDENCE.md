# Offline test evidence — 2026-11-05 21:04 KST

- Repeated in this environment from the v1.6.1 source: `python -W error::ResourceWarning -m unittest discover -p 'test_*.py' -q` → **127 tests, 0 failures, 0 errors**; process exit status 0.
- Python compiler: `python -m compileall -q .` → PASS in prior v1.6.1 package test; repeat during GitHub import check.
- Runtime: Linux Python 3.13.5 (not Windows); tests include local mock HTTP server for exchange-shaped pages. Any fabricated test server response is **not** live exchange evidence.
- Coverage previously recorded by tests: 206 candle pagination with 200/page, KST/UTC validation, malformed pages and symbols rejected, atomic SQLite/PK schema checks, 5 concurrent tasks DB init, separate exchange DBs, 10,000 initial plus 3 incremental, 400 before interruption + 9,600 resumed, menu, simulated package ZIP integrity.
- **NOT RUN:** Windows 10/11 native one-file EXEs and the actual customer ZIP executable launch; authentic exchange HTTPS full collection; continuous operation; antivirus/signed installer inspection; deployment (not applicable).
- Release gate remains HOLD. The 85% figure is project owner estimate rather than a measured code coverage percentage.

This report records test execution and does **not** assert real-exchange success from local mocks.
