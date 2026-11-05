# HANDOFF — Coin Candle Collector v1.6.1 (2026-11-05 21:12 KST)

1. **목표/요구/기술:** 크몽 Windows 무설치 콘솔 EXE 단독 업비트/빗썸/통합 3종. KRW 전 종목, 월·주·일·240/60/30/15/10/5/3/1분봉 11종. 최초 최대 10,000 완료봉/이후 무제한 증분. 메뉴 선택, SQLite 분리, CSV. Python 3.11+ 표준 라이브러리 + PyInstaller. 상품 오픈가 단일형 4만/통합 6만원.
2. **완료/변경/설계 근거:** v1.4 원본 복구 이후 v1.5 데이터 정합성(시장코드/UTC-KST/페이지 순서), DB 초기화 동시성 방지 적용. v1.6.1에서는 DB PK preflight 추가·고객 ZIP 독립 실행 검증 빌드 단계 추가·한국어 메뉴·10000봉 대량 및 복구 회귀 확보. 기존 DB/ZIP 원본 건드리지 않음.
3. **테스트/수:** `python -W error::ResourceWarning -m unittest discover -p 'test_*.py' -q`, `python -m compileall -q .` **127/127 PASS, 0 FAIL**. 로컬 HTTP Upbit/Bithumb 206봉 페이지 이동, 11봉, CSV, 최대 10000봉, 증분 10003, 400개 저장 후 이어받기, 유사 DB 방어, 고객 ZIP 모의 정적 검증. 실제 Windows EXE/거래소 HTTPS/장기 운용 NOT_RUN.
4. **완료/진행/대기/차단:** 소스/오프라인 회귀 완료, 전체 판매 완성률 **추정 85%**, RELEASE HOLD. 실 EXE·실거래소 검증 전 판매 불가.
5. **오류/시도/대안:** 빗썸 과거 v1.3 UTC `to`/`is_details` 잘못됨→v1.4 KST `to`/`isDetails` 수정. v1.5 PK 미검사·ZIP 런타임 확인 없음→v1.6.1 보강. 컨테이너 양 거래소 도메인 DNS 해석 오류 확인. DNS 동일 환경 무의미한 재시도 금지; 외부 Windows 환경 검사 권장.
6. **저장소/브랜치/SHA/주요 경로:** 사용자가 생성한 비공개 저장소 `https://github.com/hibi89/candle_scraper`, 기본 브랜치 `main`. v1.6.1 소스 28개 파일 GitHub 최초 반영 및 원격 확인 완료. **소스 기준 커밋 SHA `b9a1483a790c642704abd492493c50e038ad7344`**. 이 후 문서 인수인계 갱신으로 `main` HEAD는 달라질 수 있으므로 항상 GitHub에서 현재 HEAD를 조회할 것. 원본 소스 ZIP `coin_candle_collector_dev_v1.6.1_ci_ready.zip`(Library), 추출된 파일은 GitHub 루트에 배치. 주요 `collector.py`, `menu.py`, `build_windows.bat`, `verify_windows_exes.py`, `verify_customer_packages.py`, `make_customer_packages.py`, `test_v16_*.py`.
7. **배포/실행 환경:** Vercel 미적용. 개발 Linux Python 3.13.5; Windows 고객 PyInstaller `build_windows.bat` → 3개 독립 EXE/고객 ZIP. Windows 실제 빌드·실행은 미검증.
8. **원본/백업/인증:** v1.4 원본 SHA256 `75483844759fbaf539f4f3dd33b88064b188b3e277c43ad9b23dccb77acc2d03`; v1.5 복구 ZIP과 v1.4 별도 Library 보존. 사용자 로컬 `E:\업비트 캔들긁어오기\upbit_candles.sqlite3` 및 기존 수집기는 손대지 않음. 계정/API Key 불필요, 기밀 파일 없음. v1.6.1 원본 ZIP SHA256 `a913ac56674dc3d712b134e56dc11b78ae1e48d5e716a11e6d408d8a82eedf50`. GitHub 원본 소스 SHA256는 `SOURCE_MANIFEST.json` 기준. GitHub 커밋 작성자/커미터 계정 `hibi89` 일치 확인.
9. **다음 작업/완료 기준/승인:** (1) Windows 10+ 독립 폴더에 개발 ZIP 압축 해제, PyInstaller 설치 권한 확인 (2) `build_windows.bat` 실행 5/5 PASS (3) 메뉴 [5] 두 거래소 11봉·페이지 2차 조회 확인 (4) 새 임시 DB 실제 최초/갱신/CSV/중단/재시작·3개 ZIP 고객 독립 실행 (5) 정책·판매 문구 확인 (6) RELEASE. GitHub 저장소는 사용자가 직접 생성했고 소스 업로드를 승인함. GitHub Actions 실행에 따른 비용·환경 설치는 실행 전 확인하고 Windows 검증을 별도로 승인받을 것.
10. **시점/검증범위/커밋:** 2026-11-05 21:12 KST; 이 컨테이너의 Python 단위·모의 네트워크·ZIP 정적 검사 및 Python CLI 종료만 검증. Windows/실거래소/Production 미검증. GitHub 소스 커밋 `b9a1483a790c642704abd492493c50e038ad7344` 원격 main 및 트리 확인 PASS; 문서 후속 커밋을 포함한 현재 HEAD는 별도 조회할 것. 다음 채팅은 이 문서→STATUS→AGENTS→REQUIREMENTS→코드 순서.

**v1.6.1 추가:** 기존 v1.6 원본은 유지하고, 사용자가 지정한 GitHub 비공개 저장소 루트에 이 패키지 파일을 배치했을 경우 `.github/workflows/windows-build.yml` 수동 Windows 2022 CI를 실행할 수 있게 준비. CI 미실행/미검증, 85% 유지. CI artifact 14일 후 만료되므로 영구 저장소로 간주 금지.

## 사용자 지정 GitHub 인수인계(추가)
- 프로젝트 단일 소스: `hibi89/candle_scraper`, 기본 `main`. 원본 ZIP 별도 Library 보존. v1.6.1 소스와 테스트를 GitHub **루트**에 반영했으므로 CI 경로 `.github/workflows/windows-build.yml`가 유효함.
- 신규 문서: `docs/ARCHIVE_PROVENANCE.md`, `docs/TEST_EVIDENCE.md`, `docs/RELEASE_CHECKLIST.md` 및 `.gitignore`. 개발 소스와 과거 원본 ZIP의 SHA-256 출처 확인.
- **반드시 다음 채팅에서 먼저** 원격 `main` SHA와 이 `HANDOFF.md`의 기준 SHA를 대조한 뒤 테스트·빌드·상용화로 넘어갈 것. **소스 기준 SHA `b9a1483a790c642704abd492493c50e038ad7344`**, 현재 문서 기준 HEAD SHA는 `main` 원격 조회로 확인. 문서 후속 커밋 이전 소스 내용과 HEAD를 혼동하지 말 것.

## GitHub 업로드 검증 — 2026-11-05 21:12 KST
- 사용자 지정 비공개 저장소 `hibi89/candle_scraper`, `main`, 최초 소스 SHA: `b9a1483a790c642704abd492493c50e038ad7344`. **28개 파일** 및 `.github/workflows/windows-build.yml` 원격 트리에서 확인, Git blob `collector.py`/`README.md`/`HANDOFF.md`/CI 파일이 로컬 Git 해시와 일치.
- GitHub connector로 원격 `main` HEAD가 해당 SHA를 가리킨 것을 확인. GitHub Author/Committer 매핑은 `hibi89` 확인.
- 후속 갱신은 인수인계/상태/소스 체크섬 문서만 변경하며 **기능 소스 및 테스트 동작에는 변화 없음**. 따라서 판매 완성률 85% 추정·판매 HOLD 유지.
- CI는 수동 트리거(`workflow_dispatch`)이며 **실행하지 않음**. `Ready` 같은 배포 상태와 혼동하지 말 것: Vercel 배포 자체가 비대상.
- 최초 빈 repo의 README 초기화 SHA `fe31ffbfee7e39732155fbbf0d90c04085249d45` → 본문 소스 전체 반영 SHA `b9a1483a790c642704abd492493c50e038ad7344` → 후속 문서 HEAD(원격 조회).
