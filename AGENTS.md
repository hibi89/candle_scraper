> **[KMONG_WORK_TARGET_GATE_20261112 | 사용자 최신 확정 | 필수 작업 규칙]** 이 저장소에서 크몽 상품·육성 후보를 작업하는 모든 AI 담당자는 새 채팅·`ㄱ` 시작 시 이 문구를 읽고 적용한다.
> - 실제 개발/수정/테스트 착수 즉시 [해총 크몽 최종완성률·후보 상태표](https://github.com/hibi89/hackathon-command-center-2026/blob/kmong-productization/docs/audits/KMONG_16_CURRENT_20261111.md)의 **해당 상품명 옆에 `**[작업중]**`을 표시하고 GitHub 커밋**한다. 확정 단계 목표(예: 95%)와 검증 기준을 제품 STATUS/HANDOFF에 남긴다.
> - **목표 완성률 달성 전에는 [작업중]을 삭제하지 않는다.** 일시중단·종료·보류·다른 제품 전환·담당 채팅 변경도 삭제 사유가 아니다. 예전 '전환·중단 시 삭제' 지시는 폐기한다.
> - **검증된 목표치에 도달한 뒤에만** 기능 SHA·PASS/FAIL/SKIP·미검증을 기록하고 자기 표시를 제거·커밋한다. 목표 하향/변경으로 표식 제거 시 사용자 명시 승인 필요. 다른 담당자 표시·기존 수치·RELEASE HOLD 보존.
> - 표식은 목표 미달 상태를 의미하며 **실시간 실행 증명은 아니다**. 허브 최신 HEAD 확인 후 안전하게 반영, 실패 시 `KMONG_HUB_SYNC_PENDING` 기록. 자동 동기화 없음. 크몽 외 작업에는 표시 불필요.

# AGENTS — Coin Candle Collector (repo-wide)

- Canonical editable source: **private** `hibi89/candle_scraper`, `main`; use commit SHA to identify a tested version. Legacy v1.4/v1.5/v1.6/v1.6.1 ZIPs are preserved in ChatGPT Library; do not overwrite.
- Next session document order: `HANDOFF.md` → `STATUS.md` → `AGENTS.md` → `REQUIREMENTS.md` → actual source. If docs differ from code/test/CI, verified source behavior wins and discrepancy must be documented.
- Product: commercial Windows 10+ console EXE in three editions (Upbit, Bithumb, both); first 10k complete candles per market/timeframe, unlimited incremental, SQLite, CSV, selected 11 timeframes, restart/resume.
- Preserve all legacy users' files. Never touch or migrate local `E:\업비트 캔들긁어오기\upbit_candles.sqlite3` or concurrent active collectors without separate approval and backups. Keep credentials, binaries, market data, customer DB and logs outside Git.
- Before modifying code, review trigger / collection API rate limits, UTC-KST `to` pagination, market list parameter compatibility, duplicate request / crash recovery, initial vs incremental persistence, and failure modes. Compare at least two viable designs for major changes; choose low-cost, maintainable option.
- Modification flow: inspect latest HEAD → smallest safe change → offline unit and mock HTTP integration tests → commit source/docs → inspect CI and actual SHA. Do not claim Windows EXE, real exchange or sales-ready based only on offline tests.
- GitHub Actions workflows support **manual** runs and **narrow push triggers**: Windows build on `.github/workflows/windows-build.yml`, `collector.py`, `test_v17_retry_safety.py`, `verify_customer_packages.py` changes; bounded live API on its own workflow edits. Use conservative runner minutes; avoid gratuitous rebuilds. Do not run billable jobs beyond authorized quotas, publish releases, change repository privacy or branch protection without clear user approval. No uncontrolled live API scraping.
- Update `STATUS.md` and `HANDOFF.md` after substantial work, with test commands/counts and verified vs unverified; avoid empty commits. Always identify branch/HEAD and package provenance. Release remains HOLD until `docs/RELEASE_CHECKLIST.md` gates pass.
