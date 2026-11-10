> **2026-11-11 KST — 코인 분석기 P4 수식↔결과 무결성 영수증 개발:** 기존 P3 `coin_report.py`와 중복되는 HTML 생성은 중단하고 정본 P1/P2 규칙-CSV 행 교차검증 `coin_evidence_receipt.py` 신규 추가. 소스 CSV SHA256·원문 JSON SHA256·각 컴파일 규칙 SHA256 및 매치 수 기록, 변경 후 `--verify` 재검증, 기존 영수증/원본 불변. 실제 Linux Python3.13.5 합성 SQLite P1 15 + P2 14 + P3 생성기 7 + P4 10 = **46/46 PASS**, P4 compileall PASS, P4 소스 blob `cf9850f5`/테스트 blob `8449fa43` 일치. 기존 P3 원본 전체 통합·Windows3.11/실 E: 3.6GB DB/차트·EXE/권리 **NOT RUN**. 최종상품 잠정 **50% 유지**, 목표 70%, RELEASE HOLD. collector/main·고객 DB·중복 PR #1·배포·과금 불변. [P4 문서](docs/COIN_FORMULA_EVIDENCE_P4_20261111.md).

> **2026-11-11 KST — 코인 패턴 P3 고객 수식 생성 메뉴:** `feature/candle-pattern-analyzer`에 기존 P1 규칙과 P2 배치를 그대로 활용하는 `custom_formula_builder.py`·7개 테스트·Windows BAT(미검증) 추가. SMA/EMA GC, BB상단 돌파/하단 복귀, 종가 임계값 5개 템플릿의 안전 JSON 생성(기존 파일 덮어쓰기 금지), 선택적 CLI/인터랙티브 실행. Linux Python3.13.5 **P1+P2+P3 총 36/36 PASS, 0 FAIL**, compileall PASS; 첫 실행에서 단순 기본 임계값 오류 1건 수정 후 재검증. 정확 소스 SHA builder `57b95144`, tests `8798d994`. 실제 Windows BAT/Python3.11·실 고객 DB/실 차트·기존 전체회귀·EXE/상업권 미검증. **최종상품 50% 유지(70% 미달), RELEASE HOLD**, main/collector·DBVORA·원본 DB/Production 미변경. [P3 기술기록](docs/CUSTOM_FORMULA_BUILDER_P3_20261111.md).

> **2026-11-11 KST — 코인 패턴 분석기 P2 단일 JSON DSL 통합 배치:** `feature/candle-pattern-analyzer`에 기존 P1 JSON 규칙을 그대로 재사용하는 `custom_formula_batch.py` (1~16 수식/1~8 SQLite 동시 분석, SQL 1회 순회, CSV 동일 컬럼/규칙 SHA256/진행률) 및 `test_custom_formula_batch.py` 추가. 고객 규칙의 잘못된 연산자·지표·필드 자료형으로 발생하던 P1 TypeError **3건 재현 후 ValueError로 안전 종료**하도록 최소 수정. 로컬 Linux Python3.13.5 **P1+P2 29/29 PASS, 0 FAIL**, compileall PASS, 합성 4개 마켓 8만 봉×16 수식 3.2초/5,056건/SQLite SHA256 불변. 원격 Git blob은 P1 `8b98d125`, P2 `97c6bef5`, 신규 테스트 `452159c6`; 전체 원본 브랜치 회귀/Windows Python3.11·3.6GB 사용자 DB/차트/EXE **미검증**. 다른 실험용 batch PR #1은 미병합·독립 유지. **최종 상품화 추정 50% 유지(70% 목표 미달), 판매 RELEASE HOLD**, collector `main`·DBVORA·고객 DB·계정/과금/Production 변경 없음. [P2 설명](docs/CUSTOM_FORMULA_BATCH_P2_20261111.md).

> **2026-11-11 KST — 코인 패턴 분석기 고객별 JSON 수식 P1 개발 / 50% 유지:** 기존 하드코딩 EMA·이중 BB 스캐너와 수집기 `main` 변경 없이 `feature/candle-pattern-analyzer`에 `custom_formula_scanner.py`(blob `8a6a858a58348717498e190eea3f1ff86132d375`), `test_custom_formula_scanner.py`(blob `75974dd5c656e74b1295f803216384d95d24220c`), [사용·제약 문서](docs/CUSTOM_FORMULA_SCANNER_20261111.md) 추가. 한정 JSON 조건(지표 SMA/EMA/BB, 비교, 골든·데드크로스, 논리합/곱·NOT)을 허용목록으로 처리하고 원본 SQLite read-only, KST/UTC, 필터, UTF-8 BOM CSV, 규칙 SHA256 및 출력 실패 원자 보존 지원. 로컬 Linux Python3.13 합성 SQLite E2E/보안·회귀 **15/15 PASS, 0 FAIL**, compileall PASS. 실제 Github 소스·테스트 blob은 로컬 파일의 마지막 개행만 제외한 Git blob과 일치. 기존 저장소 **전체 테스트·Windows10/11·실 약3.6GB DB·EXE·실차트/성능/계약 미검증**, Actions 강제 실행 없음. 따라서 최종 **상품화 추정률 50% 유지**, 70% 미달·RELEASE HOLD. DBVORA/해총 타 상품/고객 원본/유료 API/수집기 `main` 불변. 상세 [신규 P1 문서](docs/CUSTOM_FORMULA_SCANNER_20261111.md).

# 2026-11-06 — BB(4,4,Open) 원본 신호 재사용 + SMA4(Close) 목표 재검증

- 사용자 요청: 기존 BB20(2,Close)·BB4(4,Open) 하단 이탈과 BB20 복귀 시점은 **불변**. 매도 목표가만 복귀 당시 최근 4개 **종가 평균**으로 변경하고 **복귀 다음 봉부터** high>=고정 목표가를 추적.
- 로컬 단독 도구 `recheck_close_target.py` + ASCII BAT + 합성 테스트 + README를 `DualBB_CloseTarget_Recheck_v1.1.zip`으로 생성. SHA256 `8bc1556e1d65f628b2f73124df0fa8ec325c23e7c29b824c369e9cf14e157e17` (11,052 bytes). GitHub에는 **신규 소스 미반영**, 대화 첨부가 실행 원본임.
- 원본 `04_all_recovery_signals.csv`의 기존 복귀 신호를 그대로 사용하며 SQLite(읽기 전용)에서 SMA4(Close)를 계산하므로 원래 이탈 탐색을 다시 하지 않음. 기존 CSV·SQLite 덮어쓰기 없음. 전 종목·분봉의 후속 OHLC는 다시 순회해야 함.
- 검증: 독립 Python 합성 17/17 PASS / 컴파일 PASS / 기존 Open 패턴 스캐너의 **합성 출력 CSV**와 새 재검증기 end-to-end PASS / ZIP CRC PASS. 사용자 실 DB 20,987,007개 및 Windows BAT **미검증**. 실제 100% 주장 불가.
- 주요 출력: 도달/미도달/후속봉 없음/전체 CSV, `05_target_at_or_below_entry.csv`(목표가가 진입 종가 이하), summary.json, report.html. 기존 복귀봉 고가는 미래 정보이므로 **다음 봉부터** 검사.
- 고객 화면 기준 과거 Open 목표 222,408 신호/219,184 도달/3,219 미도달/5 후속봉 없음은 종전 결과이고, Close 목표 재검증 결과가 **아님**.
- 로컬 사용자 DB: `E:\\업비트 캔들긁어오기\\upbit_candles.sqlite3`; 기존 신호 CSV: `Downloads/DualBollinger_BreakoutReentry_Scanner_v1.0/dual_bb_results_*/04_all_recovery_signals.csv`. 이 경로의 원본 파일과 WAL/SHM 수정·삭제 금지.
- GitHub `main` 원본, 기존 듀얼 BB 도구를 변경하지 않음. 다음 우선순위: 사용자의 실제 결과 수치/반례 확인 → 로컬 소스·테스트를 비공개 feature 브랜치에 별도로 보존·재검증 → 상용 출시 판단 보류.

---

# 2026-11-06 — 신규 이중 볼린저밴드 신호 전수 검색기 v1.0

- 독립 `dual_bollinger_scanner.py`: 기존 `results.csv`를 재활용하지 않고 수집된 전체 SQLite OHLC를 읽기 전용 스캔. 모든 KRW 종목/1,3,5,10,15,30,60,240분봉 기본 검색; 선택 종목/분봉 CLI 지원.
- 이탈: 신호 봉 close < BB(20,2,close) lower AND close < BB(4,4,open) lower. 이탈 뒤 **첫** close > BB20 lower 복귀봉 확정(연속 이탈은 단일 에피소드). 매도 목표를 복귀봉 당시 BB4(4,4,open) middle=SMA4(open)로 **고정**. 복귀봉 포함 이후 high>=fixed target이면 REACHED(갭상승 low>target 포함), 나머지 NOT_REACHED_AS_OF_DATA_END, 마지막 봉에 복귀한 미관측 NO_FUTURE_CANDLES로 구별. 이 조건은 원래 골든크로스와 무관함.
- 신규 `start_dual_bb_scanner.bat`, `test_dual_bollinger_scanner.py`, `docs/DUAL_BOLLINGER_README.txt`, `docs/DUAL_BOLLINGER.md`. GitHub 소스 blob은 ZIP 안의 원본 byte와 git SHA 일치 검증. 기존 `pattern_analyzer.py`와 수집기 `main` 미변경.
- 검증: Python3.13.5 합성 SQLite unittest **24/24 PASS**, Python compileall PASS, 진짜 SQL 스키마 합성 E2E/CSV UTF-8 BOM/로컬 HTML 생성/DB SHA256 보존 PASS, Node22 HTML JavaScript `--check` PASS, ZIP CRC PASS. Windows10/11 실제 3GB 사용자 DB 및 실차트 일치 **NOT_RUN**. 실행 결과 수치/성공률 주장 금지.
- 사용자 다운로드 ZIP `DualBollinger_BreakoutReentry_Scanner_v1.0.zip` 15,184 bytes SHA256 `179422a16d01a3541e65106f992a4f269143ad21db19f396adffa5a2555c131d` (Python/테스트/BAT/README 4파일). DB/실제 검색 결과 파일 ZIP/GitHub 미포함. 원본 E: DB/WAL/SHM 보존; read-only/PRAGMA query_only. WAL 동시 접근 시 SQLite 측면 파일의 완전한 byte 불변성은 별도 정적 DB 백업으로 보장해야 함.
- 출력: `01_not_reached.csv`, `02_reached_first_touch.csv`, `03_no_future_candles.csv`, `04_all_recovery_signals.csv`, `summary.json`, `report.html`. 모두 새 timestamp 폴더에 생성하며 기존 결과 덮어쓰기 없음.
- Vercel/Production 해당없음, Windows exe 아직 미구현. 출시 HOLD. 실제 사용자 DB에서 검증 전 실사용 완료로 판정 금지.

---

# 2026-11-06 — BB상단 기준 후속 미재도달 판정 v1.1 (기능 소스 GitHub 반영)

- 골든크로스 패턴 검출 수식 불변. 기존 추출 357개 결과를 재사용. 향후 재도달의 기준가를 신호 당시 고정 `bb_upper`로 변경(기존 v1.0 SMA280 기본과 구별). BB 미래값 추종 없음.
- 오프라인 구현 `future_retouch_review.py`, 테스트 `test_future_retouch_review.py`, Windows Python 실행 BAT를 이 브랜치에 추가. 원본 `main` 수집기와 3GB DB·WAL·SHM 및 원본 CSV 불변.
- 검증: Python3.13.5 합성 18/18 PASS, compileall PASS, HTML JavaScript `node --check` PASS, 실제 사용자 357개 CSV 파싱/BB 양수 및 SHA 일치 PASS, ZIP CRC PASS. **E: 실 DB/Windows/EXE 미검증**. 실제 357건 분류 개수 확인 불가. RELEASE HOLD.
- 사용법과 새 CSV `reference_field`는 `docs/BBUPPER_RETOUCH_v1.1.md` 참조. 기존 2026-11-06 v1.0 기록 중 'GitHub 신기능 소스 미반영'은 당시 상태이며 이번 v1.1 소스 반영으로 해소.
- ZIP v1.1: SHA256 `8fb27b6bb106138de8bb2ee4acd7eb6b4e3155a9f8b398fbf60f28316736e7e9`. 다음: 실제 사용자 DB 후속 OHLC/AXS 240분봉 비교 → Windows 실행 → 출시 검토. 현재 GitHub 기준은 본 변경이 포함된 `feature/candle-pattern-analyzer` 최신 HEAD.

---

# 2026-11-06 — 후속 고가 재도달 검사 (로컬 산출물, GitHub 소스 미반영)

- 사용자 업로드 `results.csv` **357신호 / 210종목 / 8종 분봉 / 326 종목·분봉 조합** 정상 파싱, 중복 0. 해당 CSV만으로는 이후 고가·저가를 판정할 수 없음.
- **로컬 임시 개발판 준비:** `future_retouch_review.py`, `start_future_retouch_review.bat`, `README_사용방법.txt`, 기존 `results.csv`를 묶은 `CandleGoldenCross_FutureRetouch_v1.0.zip` (SHA256 `d24a75eec903a89e1144fdd9fc8c18c48d5e98debc2399860d0fe498e37960db`, 36884 bytes). 임시 대화 첨부; GitHub source는 아직 **미반영**. 재개 시 ZIP 첨부 필요.
- 로컬 Python3.13.5 합성 SQLite **15/15 PASS** / Node22 HTML 스크립트 구문 PASS / 기존 CSV 357건 parse PASS / ZIP CRC 및 포함 CSV 해시 일치 PASS. 사용자 Windows10/11·3.63GB 실 SQLite·실차트 **NOT_RUN**.
- 기준가 옵션 `--price-field sma280`(기본, 교차선), `sma560`, `close`; 357신호 모두 close와 sma280이 다름. 신호봉 자체 제외, **이후 high >= 기준가** 최초를 감지하며 low>기준가인 갭상승/봉 전체 초과 포함. 한 번 도달한 사건은 `02_retouch_backtest.csv`(최초 시각·경과 분·봉 수·OHLC), 관찰 후 미도달 `01_untouched.csv`, 보류 `03_unresolved.csv`, 전체 `04_all_classified.csv`, 로컬 HTML `report.html`.
- 원본 DB mode=ro/PRAGMA query_only; 수식 재계산/거래소 HTTP 호출 없음. 입력/기존 CSV 덮어쓰기 없음. SQLite WAL/SHM 엄격한 바이트 불변 보장을 위해서는 별도 정적 사본 필요.
- **다음:** ZIP의 Python 파일과 15개 테스트를 GitHub 이 브랜치에 원문 그대로 추가 → 원본 SQLite 4시간봉·전분봉 검증 → Windows EXE 및 실차트 검증. `main` 변경 금지, 상품 RELEASE HOLD 유지.

---

# 2026-11-06 — 검색 결과 가독성 개선

- 신규 `CandlePatternResultsViewer.html`: 기존 `results.csv`를 다시 검색하지 않고 파일 선택/드롭으로 로컬 읽기. 검출 개수·종목/분봉·최근 시각, 종목별 빈도, 필터·정렬·60건 페이지, 지표 상세·수식 조건, 필터 결과를 새 CSV로 저장.
- 신규 `test_report_viewer.mjs`: Node 오프라인 CSV 스트리밍/유니코드·인용·오류/정적 검사(컨테이너 9/9 PASS). 설치 프로그램/외부 API/CDN 불필요.
- 브라우저 실제 클릭 자동검증: 파일 URL과 로컬서버 URL 모두 실행환경 `ERR_BLOCKED_BY_ADMINISTRATOR`로 **미검증**. 실제 Windows/고객 CSV, 대용량 SQLite 검색, 최종 EXE도 **미검증/미완성**.
- 기존 수집기 `main` 및 SQLite, 원본 CSV 불변. 판매 RELEASE HOLD 유지. 인수인계 기준 SHA 최신화는 커밋 직후 원격 확인.

---

# 분석기 브랜치 최신 상태 — 2026-11-06 00:26 KST

**작동 확인 범위: Python 인터랙티브 메뉴형 검색기 v1.0 / Windows 무설치 EXE는 아직 미구현 / 사용자 실 DB는 미검증.**

- 완료: `pattern_analyzer.py`에 전체/선택/복수 KRW 종목(예: BTC,ETH), 종목 검색, 8종 분봉 다중 선택, 종목·분봉별 전체 또는 최근 N개 구간의 발생 신호 검색, 수집기 SQLite의 읽기 전용 연결, 원자적 CSV, 진행률(%)/처리 건수/검출 건수/ETA, CLI 옵션 유지. `start_pattern_analyzer.bat` 더블클릭 메뉴 시작(Python 설치 필요).
- 성능 개선: SMA280↑SMA560 + EMA 배열의 교차 후보에서만 BB20 표준편차 평가. 합성 종가 10만 개 반복 계산 내부 비교 0.43초(전봉 BB) 대비 0.13초(BB 생략) 관찰. 실제 3GB SQLite 전체 검색 속도와 차트 일치 여부는 미측정.
- 검색 규칙: 직전 `SMA280<=SMA560`, 현재 `SMA280>SMA560`, `EMA560>EMA280>SMA280>SMA560>BBupper(20,2)`. 빈 신호도 헤더 CSV 출력.
- 검증: 로컬 Python 3.13.5 `python -m unittest -q test_pattern_analyzer.py` **23/23 PASS**, `python -m compileall -q pattern_analyzer.py test_pattern_analyzer.py` PASS; 합성 12,345봉 전체 계산/최근 1,000봉 결과 필터, 실제 합성 교차 1건, 선택 복수 종목/CLI/메뉴, 한글·특수문자 경로, 원본 DB SHA256 불변, 출력 CSV 보호·원자성 통과. 거래소 실데이터·Windows 10/11/EXE NOT_RUN.
- GitHub: private `hibi89/candle_scraper`, `feature/candle-pattern-analyzer`; 원본 `main` 소스 SHA `1f976770db4797bcaa846ed32962e306318971ca`, 현재 코드·테스트/런처의 Git Blob SHA는 각각 `cb41a4935e3b890e26f30b479804e14d628ef16c`, `e52c206224b1c241fde0d4b5d4dd2ddaf72873dd`, `a8d5e8710c22fe3a6be34a7aa58a4b598704f4be`. 최종 문서 HEAD는 커밋 후 재조회.
- 다운로드 ZIP: `CandlePatternScanner_v1.0_Python.zip` sha256 `5545bf03fcb317b29a0ba36b61bd210cfe7f40fd29f74f10ef7e3d95be687ffe`; 3개 파일, ZIP CRC PASS. GitHub에는 패키지 바이너리·시장 데이터·로컬 고객 DB 미업로드.
- 원본/출시: 수집기 `collector.py`와 `menu.py` 변경 없음; 사용자 로컬 `E:\\업비트 캔들긁어오기\\upbit_candles.sqlite3` 미접근, 재수집 없음, 외부 API 호출 없음. 기존 수집기 판매 RELEASE HOLD 유지. 분석기 실고객 배포도 EXE/실 DB/계약 검증 전 보류.
- 잔여: 실제 사용자 DB에서 전/선택 종목 검색, Windows10/11 실행과 표시, 정확한 차트 재현, 무설치 EXE 제작·검증, 일반 파일 포맷 어댑터. 사용자 승인 없는 원본/권한/개인자료 변경 없음. Vercel/Production 미적용.
- 설계 대안: 기존 CLI만 유지(수정 소량, 실사용 난도 높음) vs CLI+안전한 대화형 메뉴(표준 라이브러리, 유지보수 용이). 후자 선택, 동적 고객 Python 코드 실행 및 외부 GUI 의존성 배제.

---

# 분석기 브랜치 현행 상태 — 2026-11-05 KST

- **적용 범위:** `feature/candle-pattern-analyzer` 전용 신규 코드. 기존 `main` 수집기/고객 SQLite는 변경 없음. 사용자 제공 기준 SHA `1f976770db4797bcaa846ed32962e306318971ca`에서 시작.
- **완료:** `pattern_analyzer.py`에 SQLite `mode=ro`/`query_only`, 8개 분봉 전체·최근 N개 신호 탐색, EMA280/560·SMA280/560·BB(20,2), SMA280↗SMA560 신규 교차 및 `EMA560>EMA280>SMA280>SMA560>BBupper` 판정, CSV 원자 저장. `--last 0` 전체 무제한, 양수 N은 종목/분봉별 최근 N개 신호 표시(이동평균 계산은 전체 이전 이력 활용). 복수 SQLite `--db` 지원.
- **테스트:** 작성자의 임시 로컬 Python 3.13.5 환경에서 `python -m unittest -q test_pattern_analyzer.py` **12/12 PASS**, 실제 합성가격 873봉의 조건 발생 1건과 마지막 100봉 제외 0건, 기존 DB 해시 불변, BOM/원자 출력, 파일 보호, 잘못된 데이터 취소. GitHub 동일 SHA의 Windows Actions/EXE 및 실제 사용자의 10,000+봉 DB 전체 검색 **NOT_RUN**.
- **기능 코드 기준 GitHub 커밋:** `ab5d904701fe78a273978ca81bcd6622e4dcb7ad` (그 이전 분석기 파일 생성 `a6d9084`, 테스트 `0f04aa3`, 규칙 문서 `82a340d`). 문서 커밋 후 최종 HEAD 재조회 필요.
- **원본 보호:** 수집기와 시장 원본·고객 데이터 접근/변경 없음; synthetic 임시 DB만 사용, 결과 CSV는 별도 경로. `docs/PATTERN_ANALYZER.md`가 현재 규칙과 사용법 기준.
- **진행/제약:** 분석기 MVP의 Python 코드·오프라인 시험 완료. Windows EXE/전종목 실운용/차트 1:1 비교/CSV·JSON·Excel·Parquet 입력 어댑터/판매조건은 **미완료/미검증**. 기존 수집기 기술 추정 99% 및 **판매 HOLD**와 혼동 금지. 현재 분석기 완성률 정량 수치는 미산정.
- **Vercel/Production:** 미적용(로컬 오프라인 Python 도구). GitHub Actions 자동 Windows 빌드는 이 신규 분석기 파일에 대해 구성/실행하지 않음.
- **다음:** 실제 10,000+봉 로컬 DB를 읽기 전용으로 스캔해 사건 개수·시간·차트 대조, 이후 Windows 전용 분석기 EXE·UI, 멀티포맷 어댑터 및 상업용 정책 검토. 사용자가 요구한 옵션은 커맨드라인 `--last`로 우선 지원.

---

# STATUS — Coin Candle Collector v1.6.1 (commercial Windows editions)

최신 확인: **2026-11-05 22:50 KST**

## 2026-11-05 22:50 KST — latest Windows 147/147, SQLite rollback/handle lifecycle verified

- **기술 완성률 추정 99% (직전 98% → +1%p)**. 강한 데이터 안전성 검증이 추가되었으나 실제 소비자 Windows10/11/SmartScreen·전종목 실운용은 미검증, 상업적 출시 **RELEASE HOLD 유지**.
- [Windows CI run #42038795999](https://github.com/hibi89/candle_scraper/actions/runs/42038795999) **SUCCESS**, exact tested **source SHA `9e0632890c5621f4756e9ca7328480d860b2b710`**, Windows Server 2022 / Python 3.11.9 / pinned PyInstaller 6.16.0.
- 오프라인 **147/147 테스트 PASS** (144→147; 추가 3개 SQLite 오류 주입): `insert_page`의 중간 트리거 실패 시 **해당 페이지 전체 명시적 rollback** 및 기존 완료 데이터 보존, 장애 해제 후 재시도 PASS; `db_open`의 DB 초기화 오류 및 키보드 인터럽트에서도 **SQLite 핸들 close** 보장.
- **고객용 Windows EXE 3/3** 시작/종료, 고객 ZIP 3/3 독립 압축해제 실행 PASS. 한글·공백 경로에서 메뉴 [6] 읽기 전용·DB 미생성 **3/3 PASS**. 실제 고객 EXE에서 업비트 단독/빗썸 단독/양사 통합 메뉴 [5] 공개 API 검사 모두 PASS.
- 최신 ZIP SHA256: upbit `a61393bf8dd058afc7aed44d73329b8accb24e7df53386f12316dfd754bd7e00`; bithumb `e5677ca43f26c9b24bb52bb663dc1602210ee6e8b5747086e7df6f047136cbbf`; both `b152e053408810f0e9873fe8c564f991fcb896973935c2b1d391afdf197f9ade`. GitHub Actions 내부 ZIP artifact ID `13419497818`, EXE 실 API evidence ID `13418954271`, 2026-11-19 22:48~22:49 KST 만료. **이전 ZIP의 해시와 혼동 금지**.
- CI artifact ZIP을 현재 작업 임시 저장소로 복사 후 ZIP CRC, 내부 EXE/사용설명서 2파일 구성, 고객 ZIP 3종 SHA256 일치 직접 확인. 바깥 artifact sha256 `11572559bf3dc092099dd47028a86455ea811c76027d47d1bbb3450486ebc5d1`. Windows 실행 검증의 근거는 **GitHub runner**이며 로컬 Linux 환경에서 Windows EXE를 실행했다고 주장하지 않음.
- 출시 체크리스트 오류 수정: `SOURCE_MANIFEST.json`은 **초기 import의 과거 SHA 스냅샷**이다. 현재 소스를 역사적 manifest와 비교하라는 잘못된 지시 제거; 확인은 현재 빌드 소스 SHA·CI 실행 SHA·`BUILD_EVIDENCE.txt`와 artifact 해시로 수행. 공식 [Upbit Open API 약관](https://www.upbit.com/open_api_agreement) 및 [제6조 3항 원문 안내](https://docs.upbit.com/kr/v1.5.9/changelog/%EC%95%88%EB%82%B4-open-api-%ED%82%A4-%EC%A0%95%EB%B3%B4-%EB%B3%B4%EC%95%88-%EC%A3%BC%EC%9D%98-%EC%95%88%EB%82%B4-%EB%B0%8F-%EC%9D%B4%EC%9A%A9%EC%95%BD%EA%B4%80-%EC%95%88%EB%82%B4-%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%A8-%EC%9C%A0%EC%83%81-%ED%8C%90%EB%A7%A4-%EB%B6%88%EA%B0%80) 근거 링크 보강.
- **남은 게이트:** 고객 PC 실제 Windows 10/11 비관리자·Defender/SmartScreen/쓰기권한 미검증, KRW 전 종목/11봉의 실제 장시간 전체 운용 미실시. **판매 HOLD:** Upbit API 사용 유료 EXE 판매/배포 제한; Bithumb 소프트웨어 유상 재판매 허가 미확인. 서면 허가 요청 초안은 미발송, 출시 승인 없음. 원본 개인 DB·Library ZIP 변경 없음.
- Vercel/Production URL: **미적용** (Windows 로컬 상품).

## 2026-11-05 22:30 KST — previous 144-case / multilingual consumer-path regression (historical)

- **전체 기술 완성도 추정 98% (직전 97% → +1%p).** 이는 기술적 검증 목표의 주관적 추정이며 판매 허가/출시 준비 100%를 뜻하지 않는다. **RELEASE HOLD 유지**.
- **현재 최신 Windows 검증:** [GitHub Actions #42035893214](https://github.com/hibi89/candle_scraper/actions/runs/42035893214), code SHA `75bdd6ea6d78887200b93f29fab9b389c3054e3f`, Windows Server 2022, Python 3.11.9 + PyInstaller 6.16.0, **SUCCESS**. unittest **144/144 PASS**, 전체 EXE 3/3 빌드·시작, 고객 ZIP 3/3 개별 압축 해제 및 실행 PASS.
- **추가 실제 Windows EXE 경로 검증:** 고객 ZIP 각각을 한글과 공백이 있는 임시 경로에 해제·실행하여 메뉴 `[6]` DB 조회: 업비트 1회, 빗썸 1회, 통합형 2회. 모두 **PASS**, 존재하지 않는 DB를 자동 생성하지 않음을 확인. 고객 Windows 10/11 자체 테스트나 SmartScreen/Defender 인증은 **미실시**.
- **실제 고객 ZIP의 live [5] 메뉴:** 업비트 단독, 빗썸 단독, 통합형 양 거래소 11종 실 API 점검 전부 PASS. 이 검증은 시세·고객 DB를 GitHub에 업로드하지 않음.
- **다종목/장애 회귀 강화:** 모의 거래소 REST 응답으로 5 KRW 종목 × 11 시간봉 × 2 거래소 = **110개의 조합**, 각 최초 206개/추가 1개·중복 0·CSV 행 수 207개 검증. 특정 한 종목 오류 시 **54/55 작업 보존**, 다음 `initial`에서 55/55로 회복 검증. 업비트 UTC `to`와 빗썸 KST `to` 각각 확인.
- **429/RateLimit:** 0~30초 내 단기 Retry-After 및 Retry-After 미제공 429도 5개 병렬 작업자 공통 RateGate가 차단하고 이후 복구. 앞선 30초 초과, 마지막 재시도 장기 429 보강도 유지.
- **이전 실패 처리:** [run #42035413941](https://github.com/hibi89/candle_scraper/actions/runs/42035413941)는 새 테스트의 SQLite 연결 미종료와 429 호출횟수 기대 오류로 FAILURE; 테스트 코드 수정 후 [#42035667647](https://github.com/hibi89/candle_scraper/actions/runs/42035667647) **144/144 SUCCESS**. 이후 Unicode 경로를 포함한 **최종 run #42035893214 SUCCESS**. 제품 장애/판매 불가의 원인으로 오기하지 않음.
- **현재 검증 ZIP 해시(SHA256):** Upbit `e308076d4e8dd85b829361cb5ee16d0b6710f56a92d9307788aa24d82f0664f3`; Bithumb `5bf396c39fbae5c3bdc82fab0bbecb0c11d098396e7739171fed74aec0079cd9`; Both `7b253ba2e058a42aa72a90d606efce1238cce6c7a15eb50907fe502842baf985`. GitHub Actions 고객 ZIP artifact ID `13418123592`·실 API evidence `13417524024`. **2026-11-19 22:29~22:30 KST 만료**.
- **로컬 ZIP 교차 검수:** 외부 GitHub Artifacts에서 받은 묶음 ZIP `candle_collector_latest_INTERNAL_75bdd6e.zip` 크기 29,715,882bytes/sha256 `46651307e7fad65502f2bb46e0d6ba29284afb5df09ddc310748e099ebfa68eb`, 내부 3개 ZIP 각 SHA256과 무결성 `ZipFile.testzip()==None` 직접 PASS. 고객 상품에 시장 CSV·DB 포함 없음.
- **최종 남은 차단:** Windows 10/11 **비관리자 사용자 실기기** + Defender/SmartScreen 직접 검사, 전 KRW·전 11봉 장시간 실제 수집은 미실시. **업비트 Open API 유상 배포 제한**, 빗썸 유상 EXE 배포 권한 미확정: 판매·공개·고객 전달 **금지**. 현행 제품 허가·제품 재설계·출시 모두 별도 사용자 승인 필요. `docs/COMMERCIAL_API_POLICY.md`와 미발송 `docs/LICENSING_REQUEST_DRAFTS.md` 참조.

## 2026-11-05 22:15 KST — historical 140-test release-safety improvement

- **기술 전체 완성률 추정 97% (이전 95% 대비 +2%p)**. 기능 테스트 통과와 고객 배포·판매 허가는 별개이며 **RELEASE HOLD**. 소비자 Windows10/11 실제 환경/SmartScreen, 전 KRW/11종 장시간 사용, API 상업적 라이선스는 차단/미검증.
- [Windows GitHub CI #42033704161](https://github.com/hibi89/candle_scraper/actions/runs/42033704161), source SHA `da582b1c4c6db6740c08d2ddce7788d8e658724d`, **completed SUCCESS**. Python 3.11.9, pinned PyInstaller 6.16.0.
- **140/140 unittest PASS** (127 baseline +13 HTTP retry/shared-provider gate safety tests). `python -m compileall -q .`, Windows EXE startup 3/3, independent customer ZIP extract/start/exit 3/3, all CI job steps SUCCESS.
- **실제 고객 EXE 메뉴 [5] 공개 API:** Upbit-only 11봉, Bithumb-only 11봉, Both edition 양 거래소 각 11봉 **PASS**. 기존 소량 2페이지 및 실 10,000봉 복구 검증([#42031303797](https://github.com/hibi89/candle_scraper/actions/runs/42031303797))도 보존. 라이브 API 점검은 원본 DB 미수정.
- 요청 제한 방어 수정: 서버 `Retry-After`를 HTTP 날짜·초·소수 초로 해석, 30초 초과 제한은 즉시 중단. **다섯 번째(최종) 재시도에서도 긴 쿨다운 공지 처리**하고, 동일 거래소의 다른 4개 워커 추가 요청도 공통 RateGate로 차단. 정상 API 처리 및 고객 세 판형 회귀 PASS.
- 최신 내부 ZIP의 SHA256(이전 SHA 산출물과 혼동 금지): Upbit `32cc7ee09682410bc0205c88b464bb1667d34eeb167f024215e90d0ea935885f`; Bithumb `bc22cab45bdd2579c4cc5cd06733dbf64441942de1f5911097e3d42ce0cb4f81`; Both `26a27c2c063579d0c39ee4f9b2669d36ec6a0583686d01127d6ec35ffa57e711`.
- 내부 ZIP 아티팩트 ID **13417935853**, 실제 EXE 실 API 감사 ID **13418225561**, 만료 **2026-11-19 22:13~22:14 KST**. GitHub Actions 임시 자산이지 고객 판매 릴리스·영구 백업이 아님.
- **상용 배포 금지 계속:** Upbit 현재 공개 약관 제6조 제3항 프로그램 유상 배포 제한; Bithumb은 데이터 제3자 양도 제한(과거 공식 약관)은 확인됐지만 현재 EXE 유통 허가 여부 미확인. `docs/COMMERCIAL_API_POLICY.md`, 미발송 문의 초안 `docs/LICENSING_REQUEST_DRAFTS.md`. 개발 이슈보다 **공식 서면 허가 또는 사용자 승인에 따른 제품 재설계**가 상용화의 선결 조건.
- GitHub 소스가 단일 기준, 기존 고객 SQLite 및 Library 원본 보존. **Vercel: 미적용.** 위 기능 CI 검증 SHA `da582b1c4c6db6740c08d2ddce7788d8e658724d`, 이후 문서 커밋으로 HEAD가 달라질 수 있으므로 재조회.

## 2026-11-05 21:59 KST — previous 10,000-candle proof (historical)
- **전체 기능·출시준비 기술 진척률 95% (직전 94% → +1%p)**: 업비트·빗썸의 1분봉 10,000개 실수집 및 중단/재개 기능 검증. 이 수치는 프로젝트 진행도 추정이며 전체 상품 판매 허가율을 뜻하지 않는다.
- CI: [run #42031303797](https://github.com/hibi89/candle_scraper/actions/runs/42031303797), **SUCCESS**, 검증 소스 SHA `f6ba8768dcd59e985354a11e4d98e7a7626d4e46`, GitHub Windows Server 2022 / Python 3.11, `public-api` 및 `live-history-10k` **2/2 jobs SUCCESS**.
- Upbit `KRW-BTC` 1분봉: 실제 첫 두 페이지 저장 **399개** → 3번째 페이지에서 **테스트용 예외 주입** → 프로세스 복구 시 정확히 **10,000개** 완성, 재실행 중복 0, 증분 후 10,000개, CSV 10,000행/UTF-8 BOM/SQLite integrity PASS. 캔들 API 요청 53회 (한도 70회).
- Bithumb `KRW-BTC` 1분봉: 실제 첫 두 페이지 저장 **399개** → 동일한 인위적 중단 → **10,000개 복구** → 증분 신규 1개, **총 10,001개** → CSV 10,001행/SQLite integrity/PK 중복 없음 PASS. 캔들 API 요청 53회 (한도 70회).
- 시험의 모든 SQLite·CSV는 Windows 러너 내 자동 삭제되는 임시 폴더만 사용, **사용자 DB 미접근·시장 원본 업로드 없음**. 내부 artifact `13415414502`는 **건수·결과만 기록**, 2026-11-19 **21:58 KST** 만료.
- Upbit/Bithumb 11개 시간봉·과거 페이지 및 고객 EXE 3종 API 메뉴 실검증은 기존 성공 [run #42029964305](https://github.com/hibi89/candle_scraper/actions/runs/42029964305) SHA `40c0afe32e4eecda64ada9021aad35a8d1cd96fd` 유지. 10,000 실수집 검증은 **각 거래소 KRW-BTC 1분봉 한 조합**에 한정하며, 전 KRW 종목·전 11봉 대량/장기 운용이나 고객 Windows10/11 네이티브 실행을 증명하지 않는다.
- **상업용 배포는 별도 계약상 차단**: Upbit Open API 현행 제6조 제3항이 유상 프로그램 배포·이용허락 금지, 제5조가 무단 영리 데이터 사용 제한. Bithumb 상업적 권한도 미확정. 근거 `docs/COMMERCIAL_API_POLICY.md`. **RELEASE HOLD (판매/제공 금지)**. 문서화가 허가 획득을 대신하지 않음.

## 이전 판정(현행 98%가 우선)

- **기술 완성률 97% (검증 범위 기준 과거 추정)**. 아래 95%, 94%, 92%는 과거 회차의 역사적 기록으로 최신 판정이 아님.
- **판매 준비 상태: 차단(HOLD)** — 업비트 유상 프로그램 배포 금지, 빗썸 유상 배포 권리 미확인, 고객 Windows 10/11 검증 미실시. 제품 발매·전송·결제 없음.

## 과거 판정 기록 (최신이 아님)
- **추가 통합 검증:** Windows 고객 EXE 3종에서 실제 업비트·빗썸 공개 API 메뉴 실행까지 통과. 세부 검증 SHA와 최신 ZIP 해시 및 아티팩트는 바로 아래 최신 추가 검증 기록 참조.
- **기술 완성률 추정 95%** (직전 94% → **+1%p**). 실거래소 대량·복구 기술진척을 반영한 추정치이며 테스트 커버리지나 상업적 판매 허가가 아니다.
- **RELEASE HOLD 유지.** 실거래소 10,000봉은 KRW-BTC/1분봉만 검증, 전 종목·장기 운영·고객용 Windows 10/11 미검증. 특히 Upbit 유상 프로그램 배포 제한과 Bithumb 허가 미확인 때문에 상업적 출시 차단.
- 기존 SQLite DB·레거시 ZIP·사용자 로컬 E: 경로 보존. 자동매매·API 키·인증·Vercel 사용 없음.

## 최종 추가 검증 — 실제 고객 EXE의 실거래소 연결 (2026-11-05 21:49 KST)
- [Windows CI run #42029964305](https://github.com/hibi89/candle_scraper/actions/runs/42029964305) **SUCCESS**, 검증 소스 SHA `40c0afe32e4eecda64ada9021aad35a8d1cd96fd`, Windows Server 2022·Python 3.11.9·PyInstaller 6.16.0.
- Windows Python compileall PASS, 오프라인 unittest **127/127 PASS**, EXE 3종 빌드·정상 종료 **3/3**, ZIP별 완전 독립 압축 해제·실행 **3/3**.
- **실제 배포될 세 개 ZIP의 EXE 자체**에서 메뉴 `[5]`를 호출하여 읽기 전용 실 API 검증: 업비트 단독 **11/11 봉 PASS**; 빗썸 단독 **11/11 PASS**; 통합형 업비트 **11/11 PASS** + 빗썸 **11/11 PASS**. 모두 실제 두 페이지 조회. 각 독립 작업 폴더에서 DB 미생성 확인.
- 사용자 데이터·기존 DB를 사용하거나 수정하지 않음. `verify_live_exes.py`를 통해 소량 API로만 검사했으며 전체 종목 수집/장기 운용 검증이 아님.
- 해당 Windows 실행의 **최신 고객 ZIP** SHA256: 업비트 `6985a6ae9c8ed094161db16863af7ce3d52cbc60862c85325efb27649db7e314`, 빗썸 `5bd484fda1e6bfdd9be20527db4139bb958d2b7cdd3213c995df5dee390ae741`, 통합형 `0e7ccc6850e67a36b2d6e71b6acc42611dd7ceb10026f8f51560f3737bb903f0`. 이전 f399 SHA의 ZIP 해시와 혼동하지 말 것.
- GitHub 내부 고객 ZIP 아티팩트 **13416505378**, EXE 실 API 감사 아티팩트 **13416380913**. 두 파일 모두 **2026-11-19 21:48~21:49 KST 만료**, 영구 배포 불가.
- 판매 완성률 **추정 94%**, 기존 85%에서 **+9%p**. 나머지 ~6% 주요 블로커: 일반 Windows 10/11·SmartScreen/보안 제품과 비관리자 계정, 양 거래소 전종목/10,000봉 장기 실수집·재시작, 거래소 공식 시장데이터 상업 활용 약관 최종 확인. **판매 RELEASE HOLD** 유지. 사용자의 최종 출시 승인 전 판매 불가.

## 이전 Windows EXE 빌드 기록 (보존)
- [GitHub Windows Actions run #42027942187](https://github.com/hibi89/candle_scraper/actions/runs/42027942187), **SUCCESS**, 소스 SHA `f39932db1c5253c38fc8e0521e419da0920237fa`.
- Windows Server 2022, Python 3.11.9, PyInstaller 6.16.0, Python 3.11 구문 검사 PASS.
- 오프라인 unittest **127/127 PASS, 0 FAIL**.
- `build_windows.bat` 5단계 PASS: EXE 3종 생성, 각각 부팅/정상 종료 3/3, 고객 ZIP 3종 구성, **각 ZIP을 별도 폴더에 해제해 EXE 실행 3/3 PASS**, 초기 DB 미생성 확인.
- 내부 보관 아티팩트 `CoinCollector-Windows-UNRELEASED-f39932db1c5253c38fc8e0521e419da0920237fa`, GitHub artifact ID `13414129062`, **2026-11-19 21:33 KST 만료**. 고객 배포 승인이 아님.
- 빌드 ZIP SHA256: `upbit=bdea04ada699c1926b6e3990804fa896298c5392b2fa6e5298c541e0e6d72e4c`; `bithumb=77c0bbab861d0eed1118ee033fb6e0932972b1632e817aa336780f0e7d62cbb2`; `both=8212f954d708041fa64584c27dff4e3f61aff86a4175e963fd9ce273381c5154`.

## 별도 Python 소스 실거래소 HTTPS 검사 (보존)
- [GitHub Live API Actions run #42028865266](https://github.com/hibi89/candle_scraper/actions/runs/42028865266), **SUCCESS**, 실검사 SHA `5a503c9f214e11ae77ebfb264478bef3b4cafa00`.
- **업비트 PASS:** 검사 당시 300개 KRW 마켓 목록 조회, KRW-BTC 11개 시간봉별 실응답·첫 페이지·과거 두 번째 페이지, 소량 일봉 최초 저장/증분/CSV BOM/PK 중복 검증 PASS.
- **빗썸 PASS:** 검사 당시 488개 KRW 마켓 목록 조회, 동일한 11시간봉·2페이지·소량 DB 최초/증분/CSV BOM/PK 중복 검증 PASS.
- `live_api_probe.py`는 대상 `KRW-BTC`, 하루 봉 최대 11개, 일회성 임시 SQLite와 CSV만 이용한다. **전체 KRW 마켓의 대규모 과거 수집 성공을 의미하지 않는다.** 원본 DB와 데이터 파일을 GitHub에 올리지 않음.
- 실검증 증거는 내부 artifact ID `13415620777`, **2026-11-19 21:39 KST 만료**.

## 수정한 오류와 검증 근거
- 첫 GitHub Actions 실행: YAML `pip` 한 줄의 `: ` 구문 오류 → 블록 scalar로 수정.
- 두 번째 실행: Python 3.11이 한국어 메뉴의 중첩 인용부호 f-string 파싱 실패 → `menu.py` 최소 수정.
- 세 번째 실행: 영문 Windows 러너 CP1252 한국어 출력 오류 → Windows UTF-8 stdout/stderr 처리 보완.
- 첫 실 API 검증: 양 거래소 실데이터 검사 자체 PASS이나 SQLite 점검용 연결이 Windows 임시 폴더 삭제를 막음 → `contextlib.closing`으로 수정; 최종 run PASS. 성공 검증 전 실패를 지우거나 덮어쓰지 않음.

## 출시 전 잔여 게이트
1. 실제 고객 Windows 10/11·백신·SmartScreen·비관리자 권한에서 ZIP 3종 독립 실행/폴더 쓰기 검증.
2. 양 거래소 전종목·11봉 대규모 및 10,000개 장기 수집, 네트워크 중단/재시작, 데이터 무결성 직접 검증. 10,000개/10,003개 등은 현재 오프라인 모의 127개 테스트에 포함.
3. 업비트·빗썸 최신 Open API 이용약관, 상업용 프로그램 공급과 시세 데이터 재배포 허용 범위를 별도로 확인. ZIP에는 수집된 시장 데이터나 개인 DB가 포함되지 않음.
4. 출시 전 최종 코드 SHA에 대해 빌드·실 API·보안·고객 ZIP을 같은 기준으로 재검토하고 **사용자 출시 승인** 필요.

## 저장소 / 보존
- 비공개 `hibi89/candle_scraper`, `main`; 최근 전체 Windows/EXE 실 API 검증 SHA `40c0afe32e4eecda64ada9021aad35a8d1cd96fd`. 이후 `.gitignore` 반영과 본 문서 커밋 때문에 최신 HEAD는 GitHub에서 직접 확인.
- `SOURCE_MANIFEST.json` 파일 해시 목록은 **초기 GitHub 반영 소스 SHA `b9a1483a790c642704abd492493c50e038ad7344`의 역사적 스냅샷**이지 현재 HEAD 전체 파일의 매니페스트가 아니다. 원본 ZIP SHA는 `docs/ARCHIVE_PROVENANCE.md` 참고.
- Vercel/Production URL: **미적용** (오프라인 Windows 상품).

## 2026-11-11 KST — P4 unified customer workflow + offline HTML; final-product estimate 65% PROVISIONAL
- **Canonical source:** current `hibi89/candle_scraper@feature/candle-pattern-analyzer` implementation SHA `33ed7ae00341016b8c6e42a43eb0f6d610e0b742`; 9 new P4 files (CLI, report, tests, BAT, JSON example, design note) with local Git blob SHA verification. P1 `custom_formula_scanner.py`, P2 `custom_formula_batch.py`, P3 `custom_formula_builder.py`, collector/main and earlier patterns are untouched.
- **Customer workflow:** `coin_analyzer.py --rule` calls canonical P1; `--rules` calls canonical P2; bounded `--max-matches`, --markets/--units/--last, --validate-only, explicit --overwrite; `coin_report.py` produces escaped static CSP HTML with per-rule/market/unit counts, capped preview and safe same-directory publication. Simple Python-installed BAT wrappers. No dynamic Python customer code, live exchange API, customer database write, or externally hosted UI.
- **Exact executed local P4 evidence:** Linux Python3.13.5 `test_coin_cli_dispatch.py` eight **mocked** CLI tests + `test_coin_report.py` thirteen actual synthetic CSV/HTML tests = **21/21 PASS**, 0 FAIL/SKIP, strict ResourceWarning. Chromium headless on a synthetic canonical CSV rendered the actual generated report: 1/1 PASS, KPI cards 4, injected image 0, console errors 0, external HTTP requests 0. Source Git SHA of all 9 new files matched local hash-object before push.
- **Other completed but DIFFERENT source runs:** canonical P1+P2+P3 36/36 PASS in previous separate run; draft standalone P0 batch 57/57 PASS and 100k-benchmark are NOT integrated into P4 and not additive to its same-SHA regression.
- **NOT RUN:** new `test_coin_analyzer.py` four true P1/P2/P4 full-source E2E tests, whole repo/collector regression, native Windows3.11 and browser, user ~3.6GB E: source data, chart parity, packaged EXE, exchange licensing. Draft PR #1 independent duplicate batch remains unmerged and is NOT canonical.
- **Final-product engineering estimate changed 50→65% provisional**: +5pp canonical P1/P2 multi-rule, +5pp P3 five-template builder, +5pp P4 single customer CLI/offline report. These are milestone judgement weights, not test coverage or release certification. Remaining to 70: **5pp**, contingent on same-SHA complete checkout P1/P2/P3/P4 4 E2E + legacy regression and smoke; no invented PASS. **RELEASE HOLD** even at 70; full Windows/real DB/package/license still beyond.
- Evidence: `docs/COIN_ANALYZER_P3_UNIFIED_20261111.md`. Do not reassign archive/collector license from technical tests.
