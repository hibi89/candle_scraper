# Archive provenance and recovery (read only)

Prepared 2026-11-05 21:04 KST. Original archives are retained OUTSIDE GitHub; they are not commit inputs for subsequent modifications unless a new version is explicitly chosen.

| Archive | SHA-256 | Verified source |
| --- | --- | --- |
| v1.4 original | `75483844759fbaf539f4f3dd33b88064b188b3e277c43ad9b23dccb77acc2d03` | Earlier attachment/Library |
| v1.5 recovered | `c81f136404e0a54c874e931342799d0c7aa313fe561331c78cca2185be7c6dd0` | Library |
| v1.6 verified source | `e422bf00fc2e3294a8de387a39d4b02279f500383063baf1e14a26b4768c7a63` | Library |
| v1.6.1 CI-ready source | `a913ac56674dc3d712b134e56dc11b78ae1e48d5e716a11e6d408d8a82eedf50` | `/coin_candle_collector_dev_v1.6.1_ci_ready.zip` in ChatGPT Library |

The tracked code and documentation originate from exact contents of the v1.6.1 ZIP. GitHub includes editable source rather than a second copy of the archive. Never commit customer datasets, `.sqlite3`, produced binaries, keys, tokens, or user-private filesystem contents.

**Recovery:** Clone `https://github.com/hibi89/candle_scraper` at its verified branch/SHA. Read `HANDOFF.md` then `STATUS.md`, `AGENTS.md`, `REQUIREMENTS.md`. Run offline tests. Check original development ZIP in Library only if reconstructing pre-Git history. Do not overwrite a user's existing Upbit DB.
