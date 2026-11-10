# 2026-11-11 KST — 코인 패턴 분석기 P2 통합 인수인계

1. 목표/설계: 크몽 코인 맞춤식 50→70% 목표, P1 JSON DSL 단일 계약을 보존하면서 16규칙 1회 SQL 스캔. 독립 batch DSL의 중복 유지비용 때문에 P1 evaluator 재사용 선택, PR #1 실험용 격리 미병합.
2. 구현: custom_formula_batch.py 신규, test_custom_formula_batch.py 신규, P1 잘못된 JSON typed operator/indicator/field 3건 안전 오류 수정, rules 예제, 진행률·규칙별 카운트·동일 CSV·SHA256.
3. 테스트: Linux Python3.13.5 P1 15 + P2 14 = 29 PASS/0 FAIL/0 SKIP; strict ResourceWarning; compileall PASS. 합성 SQLite 8만 봉×16규칙·4종목 3.2초/5056 신호/DB 해시 불변. Git blobs P1 8b98d125 / P2 97c6bef5 / tests 452159c6 exact; 이 결과는 Windows·고객 DB 대체 불가.
4. 상태: 상품 추정 50% 그대로, 70% 미달, RELEASE HOLD. 기능 초안은 자체 검증됐지만 고객 납품/기존 전체 회귀 미완.
5. 오류/대안: P1 malformed JSON unhashable list→TypeError 3건 재현 후 수정해 29/29 PASS. Local private clone DNS 제한; 반복하지 말고 GitHub blob 검증 또는 허가된 체크아웃. Windows 3.6GB DB 접근/Actions 비용확인 불가.
6. 저장소/브랜치/SHA: private hibi89/candle_scraper@feature/candle-pattern-analyzer, 본 커밋의 SHA는 원격 갱신 후 재조회. 경로 custom_formula_scanner.py / custom_formula_batch.py / test_custom_formula_batch.py / docs/CUSTOM_FORMULA_BATCH_P2_20261111.md. PR #1 draft 별도.
7. 실행/배포: python custom_formula_batch.py --db PATH --rules JSON --output CSV --progress; full env Python3.11+ 예정. Vercel/Production 미적용, 실 Windows/EXE 미검증.
8. 원본·백업·인증: 기존 git history 및 main/collector, 사용자 E: SQLite/WAL/SHM 및 과거 CSV/ZIP 불변. 실 고객 원본 사용/외부전송·계정/권한/유료 CI 없음. git revert 복구.
9. 다음: 전체 브랜치 old P1/BB/retouch/collector 테스트 실행, Windows3.11·실 데이터 read-only 스트레스/차트·CSV viewer·고객 규칙 작성 UX, EXE 패키지/상업권 확인 후 70% 검토. Draft PR #1은 비교 후 중복 해소 전 무단 병합 금지.
10. 갱신: 2026-11-11 KST, 로컬 합성 테스트만 실행; SHA/HEAD와 원격 파일 재확인 후 문서 기준 확정. 상세 docs/CUSTOM_FORMULA_BATCH_P2_20261111.md.

---

# 2026-11-11 KST — Coin Pattern Custom Formula P1 인수인계

1. **목표/요구/기술:** 크몽 50→70% 목표 중 사용자별 맞춤 수식이 핵심. collector 원본이 아닌 별도 Python3.11+ 오프라인 JSON DSL/SQLite 읽기 전용 검색기 추가. DBVORA는 다른 작업 담당이므로 본 회차 범위에서 제외.
2. **구현/설계:** 임의 Python import 방식(유연하나 임의 코드실행 위험)을 거부하고 허용목록 JSON 규칙을 채택. 필드(open/high/low/close/volume/trade_value), SMA/EMA/BB, 조건 비교, cross_up/down, all/any/not, 제한된 중첩/기간/출력건수. 원본 읽기 전용, 중복 파일 금지/명시적 덮어쓰기, CSV 원자 출력, 규칙 SHA256. 기존 고정 패턴과 Collector 무변경.
3. **테스트/검증:** Linux Python3.13 local `python -W error -m unittest -v test_custom_formula_scanner.py` **15 PASS/0 FAIL**, `python -m compileall -q custom_formula_scanner.py test_custom_formula_scanner.py` PASS; 임시 SQLite E2E, 데이터 해시/CSV 실패 보호, JSON 보안, CLI 검증. GitHub 정확 Git blob code `8a6a858a58348717498e190eea3f1ff86132d375`, tests `75974dd5c656e74b1295f803216384d95d24220c` 로컬 마지막 개행 제거 후 일치 확인. 기존 전 테스트/실 Windows/실 3.6GB DB/차트·EXE 미실행.
4. **상태:** P1 소스·테스트·설명 GitHub 반영 완료, 전체 최종상품 추정 **50% (70% 미달)**, RELEASE HOLD. 15 합성 테스트 성공만으로 진행률 상승 인정하지 않음.
5. **실패/차단/대안:** customer E: 원본 DB·Windows10/11 접근 불가, full private checkout/container DNS 제한(과거 확인)으로 원본 전체 검증 불가. 실제 신호 수/성능/수익률 추정 금지. 대안은 본 소스 기반 로컬 또는 허가된 Windows CI/실기기 테스트(비용 발생 여부 승인 선행), 기존 고정식 테스트와 함께 회귀 실행.
6. **저장소/브랜치/SHA/경로:** `hibi89/candle_scraper@feature/candle-pattern-analyzer`, source commit `e713891692750b40c6feac0152b9c4274e63d552`, test `3e712c23f1019840eb07d140ef1b74d8bd3de7bb`, doc `875836c6893a1e14e49f5d6e1ad06f9d3ff8e226`. 핵심 `custom_formula_scanner.py`, `test_custom_formula_scanner.py`, `docs/CUSTOM_FORMULA_SCANNER_20261111.md`. 이 인수인계 커밋 후 최신 SHA 재확인.
7. **실행/배포:** `python custom_formula_scanner.py --db PATH --rule rule.json --output matches.csv` / test `python -W error -m unittest -v test_custom_formula_scanner.py`. Python3.11+ 예정, Vercel/Production/EXE 미적용.
8. **원본/백업/보안:** 사용자 로컬 E: SQLite/WAL/SHM·기존 결과 CSV 변경 금지, 고객 DB/거래 데이터 GitHub 미전송. source만 private feature branch; `main` 미변경. 코드 문제 시 Git revert 가능. 동시 WAL writer 실험 미검증.
9. **다음 단계/완료 기준:** 전체 브랜치 체크아웃에서 신규 15 + 기존 패턴/이중BB + 전체 수집기 회귀, Windows10/11 실제 사용자 DB 읽기 전용 스캔·차트/성능 확인, 고객 수식 GUI·배포 EXE·라이선스 확인. 그 후 증거 기준으로 최종 상품화 70% 재평가.
10. **기준 일시/정확성:** 2026-11-11 KST, 로컬 합성 Python과 원격 Git blob 확인, GitHub Actions/전체 원본/실기기/고객 데이터 미검증. 이후 HEAD 확인이 기준.

---

# 2026-11-06 KST — SMA4(Close) 목표 재검증 인수인계 (신규 코드 GitHub 미반영)

1. **목표·확정 수식:** 기존 설정 BB(20,2,Close) 하단 AND BB(4,4,Open) 하단 동시 이탈 → 이후 최초 BB20 하단 위 종가 복귀까지는 **그대로 유지**. 복귀봉 시점 SMA4(Close) 고정 후 복귀 **다음 봉부터** high>=목표가인지 검사. 실전 봉내 선후관계/미래 참조 방지.
2. **완료·결정:** 기존 전수 검색 산출물 `04_all_recovery_signals.csv`의 222,408개 복귀 신호를 다시 활용하는 전용 `recheck_close_target.py` 제작. 3GB DB에서 추가로 SMA4(Close)와 미래 OHLC만 종목/분봉별 1회 순회, 원래 BB 하단 조건 재계산 불필요. 모든 원본 입력 별개 결과 폴더로 보존. 목표가<=진입종가를 수익 목표 부적격으로 별도 기록.
3. **테스트:** `python -m unittest -q test_recheck_close_target.py` 17/17 PASS, `compileall` PASS. 기존 Open 스캐너에서 만든 독립 합성 CSV와 새 도구의 end-to-end 통합 PASS; old=UNREACHED/new=REACHED 합성 사례 입증. ZIP CRC PASS. Windows 사용자 환경/실 20,987,007개 DB/최종 도달률은 **NOT_RUN**.
4. **상태:** 로컬 ZIP 다운로드 가능, 실제 데이터 실행 대기, 출시 HOLD. 100% 가설 근거 없음. 합성 반례 존재.
5. **오류·시도·대안:** 초기에 유닛테스트 1/17은 누락 데이터 오류메시지 정규식 기대 차이로 실패 → 기대식 정정 후 17/17 PASS. 실제 3.63GB DB는 사용자 E: 로컬에만 있어 여기서 평가 불가; 사용자 PC 도구 실행 또는 승인 후 원본 데이터 전달 필요. 도달 시각/봉 수는 캔들 데이터의 정밀도 한계.
6. **저장소/브랜치/SHA:** private `hibi89/candle_scraper`, `feature/candle-pattern-analyzer`. 이 회차 시작 HEAD `14b0820b83f77e69bc988aa421ff52e6bd60014b`. 기존 스캐너/collector/main 수정 없음. 신규 도구 소스는 로컬 ZIP만 존재하며 **GitHub에 아직 미반영**. ZIP SHA256 `8bc1556e1d65f628b2f73124df0fa8ec325c23e7c29b824c369e9cf14e157e17`.
7. **배포/실행:** Windows Python3.11+ ZIP 추출→`start_close_target_recheck.bat`. E: 기본 DB 경로, 이전 `dual_bb_results_*/04_all_recovery_signals.csv` 자동 탐색, 필요시 CSV 경로 붙여넣기. 결과는 `close_target_recheck_*/report.html`; Vercel 미적용, EXE 아님.
8. **원본/보안:** 원본 E: SQLite/WAL/SHM과 이전 CSV는 변경 금지. DB `mode=ro` 및 `PRAGMA query_only=ON`; HTTP 없음. 분석 결과는 로컬에만 생성, GitHub에 사용자 시장 데이터 업로드하지 않음. WAL/SHM 자체의 바이트 불변은 실기기 검증 없음.
9. **다음 우선순위:** 사용자 재검증 실행 후 `summary.json`과 `01_close_target_unreached.csv` 수집/검증 → 해당 로컬 코드·테스트를 feature 브랜치에 보관 → 100% 미달 사례의 저장 누락/실제 반례 구분 → 실전 손익 유효성 검증.
10. **갱신 기준:** 2026-11-06 KST, 오프라인 합성 테스트·실행 ZIP 검증. 기준 GitHub HEAD는 이 문서 변경 커밋 직전 `14b0820b83f77e69bc988aa421ff52e6bd60014b`, 최종 문서 HEAD는 원격 브랜치 재확인. 사용자 실제 분석 수치 미확정.

---

# 2026-11-06 KST — 이중 BB(20,2 Close / 4,4 Open) 검색기 인수인계

1. **목표·용도·확정 수식:** 신규 검색기. 최초 close가 BB20 close 하단 AND BB4 open 하단보다 작은 봉을 setup. 이후 첫 close>BB20 하단 복귀봉에서 BB4 open 중간선=SMA4(open) 고정. 복귀봉 자체부터 이후 high>=고정값인 봉 발견 시 REACHED, low>고정값인 갭상승도 포함. 연속 setup은 최초 한 건으로 묶음. BB4 하단 재복귀는 요구하지 않음. 이전 SMA280 골든크로스 패턴과 독립.
2. **완료·결정 근거:** 종목·분봉별 SQLite 오름차순 1회 SQL 조회+20 close/4 open rolling windows+최소힙으로 각 고정목표가 첫 터치 판정. 개별 신호마다 전체 과거·미래 SQL 반복보다 중복 IO 작고, 골든크로스 기존 코드를 변경하는 것보다 회귀 위험 낮음. 기본 전체 KRW·8종 분봉, CLI 시장 선택. Python 3.11+ 표준 라이브러리/로컬 HTML+CSV. 테스트 소스와 ZIP 원본 Git Blob SHA 일치.
3. **테스트·미검증:** `python -m unittest -q test_dual_bollinger_scanner.py` **24 PASS/0 FAIL**, compileall PASS. 합성 DB end-to-end/CSV, SHA256 DB 보존 PASS; Node22 HTML JS 구문 검사 PASS; ZIP CRC PASS. 실제 사용자 3GB E: DB·Windows 실행·차트 비교·시간 측정 NOT_RUN. 실질 승률/실전 익절 체결 불명.
4. **상태/중단:** 구현+오프라인 검증 완료, 실 DB/Windows 검증 대기. 상품 RELEASE HOLD. 복귀봉 high가 목표가 이상인 경우 포함하지만 그 고가는 복귀 종가 확정 전일 수 있어 실거래 체결 근거로 사용할 수 없음.
5. **오류·시도·대안:** 외부 API/실 DB 접근 없음. 구형 ZIP의 SMA280/BB 상단 재도달 로직은 이 신패턴에 부적절하므로 재사용하지 않음. 저장된 봉 사이의 미거래/수집 공백은 별도 `pair_data_gaps`로 기록. SQLite WAL 파일 엄격 불변 필요 시 수집기 종료 후 백업본 분석. 수집기 동시에 실행한 실제 DB는 미검증.
6. **저장소·브랜치·주요 경로:** private `hibi89/candle_scraper`, `feature/candle-pattern-analyzer`; 새로운 `dual_bollinger_scanner.py`, `test_dual_bollinger_scanner.py`, `start_dual_bb_scanner.bat`, `docs/DUAL_BOLLINGER.md`, `docs/DUAL_BOLLINGER_README.txt`. HEAD SHA는 이 커밋 직후 원격으로 확인. `main`/기존 수집기 변경 없음.
7. **배포·실행:** Vercel/Production 미적용. 고객 ZIP을 새 폴더에 풀고 `start_dual_bb_scanner.bat` 더블클릭; 기본 DB `E:\업비트 캔들긁어오기\upbit_candles.sqlite3`. 결과는 `dual_bb_results_...`의 `report.html`과 CSV 4종. EXE 아님, Python 3.11+ 필요.
8. **원본·백업·보안:** 사용자 3GB SQLite/CSV를 GitHub로 보내지 않음. SQLite `mode=ro`, `PRAGMA query_only=ON`; 결과 timestamp 폴더는 원본 외부 별도 생성. 기존 ZIP/기존 신호 CSV 보존. 비밀·토큰 없음. ZIP SHA256 `179422a16d01a3541e65106f992a4f269143ad21db19f396adffa5a2555c131d`.
9. **다음 작업·완료기준:** 고객 3GB 실 DB에서 BAT→전체 스캔→`summary.json`의 수량→실차트와 다수 신호에서 BB 하단 계산/고정 목표가/최초 터치→Windows 실제 보고서 브라우저 확인→성능 개선/상용 여부 승인. 확인 전 성공률 100% 주장 불가.
10. **갱신 시점·증거:** 2026-11-06 KST. 로컬 Python 24/24+합성 DB+HTML JS+ZIP 검증 완료; 실 DB/Windows/Production 범위 미검증. 이 인수인계 문서와 상태 문서는 함께 갱신했으며 원격 확인 SHA가 유효 기준.

---

# 2026-11-06 — BB상단 재도달 판정 v1.1 인수인계

1. **목표/요구/기술:** 기존 골든크로스 탐색 수식 그대로, CSV의 각 신호봉 당시 볼린저 상단(`bb_upper`)을 고정해 이후 최초 high >= 기준가 재도달 여부로 필터링. Python 3.11+ 표준 라이브러리/SQLite read-only/HTML 정적 보고서.
2. **완료/근거:** 이전 v1.0 SMA280 기본→v1.1 bb_upper 기본, `--price-field sma280|sma560|close` 비교 옵션 유지. 여러 신호를 (market,unit)별 정렬 스트림+최소힙으로 단일 조회해 반복 DB 조회보다 적게 읽음. 갭상승 포함, 신호봉 제외, 미재도달/첫재도달/보류 CSV + 시각/경과 시간/봉 수/고저가/보고서.
3. **테스트:** `python -W error -m unittest -q test_future_retouch_review.py` 18 PASS/0 FAIL, Python compileall PASS, JS `node --check` PASS, 사용자 원본 신호 CSV 357건 BB 양수 확인, ZIP CRC 및 입력 SHA256 일치 PASS. 실 3.63GB DB/Windows 10/11/차트 교차 검증 NOT_RUN.
4. **상태:** 기능 구현과 합성 검증 완료. 사용자 실제 357건 결과 판정 미검증. Windows EXE/상업 배포 미완. 출시 HOLD.
5. **오류/시도/대안:** 이전 v1.0 기본 SMA280 때문에 연구 대상이 달라짐. 이번 수정은 신호식이 아닌 기준가만 변경. 새 보고서는 재실행해야 함; 이전 보고서 숫자 재사용 금지. 실 DB가 없으므로 터치 숫자 임의 생성 금지.
6. **저장소/브랜치/SHA:** private `hibi89/candle_scraper`, `feature/candle-pattern-analyzer`, 업데이트 이전 HEAD `436620733979cafadd5f56111486adc42fd0c754`. 최종 SHA는 GitHub branch HEAD에서 확인. 새 소스 `future_retouch_review.py` blob `b1eda1355c12110aecfb6b85f96e0a04fdcc70a6`, 테스트 `7f3b99c5d1a62b623ee80a1cd726f30ff7f61900`, BAT; `main` 비변경.
7. **배포/환경:** Vercel 미적용. 사용자 Windows에서 Python3.11+ 및 ZIP 해제 후 BAT 실행, DB 기본 `E:\업비트 캔들긁어오기\upbit_candles.sqlite3`. 유저 결과 `report.html`. GitHub CI는 기존 설정의 제한된 트리거에 따르며 Windows 검증을 대신하지 않음.
8. **원본/보안:** 원본 DB/WAL/SHM과 신호 CSV의 수정·이동 금지. SQLite mode=ro/query_only; 실 DB는 미접근. 357개 시장신호 CSV는 대화 ZIP에만 포함, GitHub 업로드 금지. 기존 ZIP 유지.
9. **다음 우선순위:** 고객 DB에서 동일 v1.1 ZIP 실행 → AXS 240m 등 신호 원본 차트와 수동 대조 → 실제 Windows 이용성/에러/성능 확인 → EXE → 출시 승인. 동시 수집기 WAL/SHM 변경에 주의.
10. **갱신 기준:** 2026-11-06 KST, 로컬 소스+18 합성테스트+실 신호 CSV+ZIP 검증. GitHub 본 커밋 기준, 실 DB/브라우저/EXE는 미검증.

---

# 2026-11-06 — 후속 재도달 판정 기능 인수인계 (소스 GitHub 미반영)

1. **목표·확정 요구:** 이미 추출한 357개 패턴 신호에서 신호 이후 저장된 캔들의 high가 골든크로스 기준가 이상인 적이 없던 건만 남기고, 한 번이라도 넘은 건의 최초 도달 봉/경과 시간을 백테스트 기록. Python 표준 라이브러리 + 기존 SQLite mode=ro + 오프라인 HTML.
2. **설계·기능:** 개별 SQL 반복보다 market/unit별 한 번의 정렬 조회+보류 이벤트 최소힙을 선택. 기준가 `sma280` 기본/옵션 `sma560|close` (357개 모두 종가와 SMA280 값 상이). 신호봉 자체 제외, 고가 `>=`, 저가가 기준가 초과인 봉도 재도달. 미도달/재도달/데이터 보류 분리. 결과 CSV 4종+HTML+JSON.
3. **테스트:** 로컬 Python3.13.5 유닛 15/15 PASS, Node22 HTML JS 문법 PASS, 업로드한 실제 `results.csv` 357건 파싱 PASS, ZIP CRC/CSV 해시 일치 PASS. 사용자 실제 E: SQLite/Windows 10/11/실차트·상업 배포 NOT_RUN.
4. **상태:** 다운로드용 ZIP 제작 완료(대화 첨부), 실제 DB 검증 미실시. **GitHub에는 로컬 Python 소스·테스트가 아직 업로드되지 않음.** 따라서 GitHub 브랜치의 실행 코드만으로 해당 신기능 재현 불가. 제품 출시 HOLD.
5. **오류·대안:** GitHub 연결 도구는 파일 원본 경로 자체를 Git blob 업로드로 연결하는 기능을 제공하지 않아 현재 회차 소스 반영 미완료. ZIP의 source/test 파일을 확인해 후속 GitHub 전송해야 함. 없는 DB로 완료 숫자 생성 금지. 원본 DB/WAL/SHM 삭제/수정 금지.
6. **저장소/브랜치/SHA:** private `hibi89/candle_scraper` `feature/candle-pattern-analyzer`, 작업 시작 HEAD `89ce50b4a2ecd71d0d6aafb40ced81cc83ff145d`. 이번 STATUS/HANDOFF 문서만 추가 반영, 실제 코드 GitHub 미반영. `main` 불변.
7. **실행·환경:** ZIP `CandleGoldenCross_FutureRetouch_v1.0.zip` SHA256 `d24a75eec903a89e1144fdd9fc8c18c48d5e98debc2399860d0fe498e37960db`, 36884 bytes. 압축 해제/기존 E: 경로 DB/Windows Python3.11+, `start_future_retouch_review.bat` 실행. Vercel 미적용, EXE 아님.
8. **원본·백업·보안:** 사용자 `E:\\업비트 캔들긁어오기\\upbit_candles.sqlite3` 실제 원본은 접근하지 않음. 업로드된 357건 CSV만 ZIP에 포함(비공개 GitHub에 시장 데이터 업로드하지 않음). SQLite 로컬 읽기 전용; 별도 출력 폴더만 새로 생성.
9. **다음 우선순위·기준:** GitHub에 ZIP 내 원본 Python/테스트/launcher를 정확하게 반영하고 테스트 → 사용자 DB에서 최초 재도달 시간·갭상승·미도달 결과 확인 → 고객 Windows10 EXE 검증 → 인수인계 최종 동기화/출시 승인.
10. **갱신 기준:** 2026-11-06 KST, 검증은 합성 오프라인 15건·실 신호 CSV 파싱/ZIP CRC, 미래 OHLC는 미접근. 문서 기준 커밋은 원격 HEAD 재조회.

---

# 패턴 검색기 오프라인 결과 뷰어 인수인계 — 2026-11-06 KST

1. **목표/용도:** 이전 분석기의 검색 결과 CSV가 길어 읽기 어려워, 고객이 PC에서 오프라인 HTML로 요약/검색/선택하도록 독립 뷰어 추가. 기존 검색 수식/수집기 변경 없음.
2. **완료/설계:** `CandlePatternResultsViewer.html` (단일 정적 파일). Excel 필터(설치·조작 요구)와 비교해 별도 설치·계정 없는 Chrome/Edge 로컬 HTML 방식 선택. 요약 4종, 종목별 히스토그램, 종목/분봉/거래소/날짜 검색, 최신·과거 정렬, 60건 페이지, 상세 SMA/EMA/BB/조건 검사, 필터 결과 CSV 다운로드.
3. **검증:** 컨테이너 Node22 오프라인 CSV/정적 검사 9/9 PASS(5개 스트림 분할, 빈 파일, 비정상 열, 따옴표, 누락 열); `node test_report_viewer.mjs`. 고객 브라우저 UI 테스트는 실행정책 차단으로 NOT_RUN. 기존 Python 분석기 23 PASS는 이전 회차 기록.
4. **상태:** 새 HTML/파서 코드 정적 검증 완료. 실제 고객 `results.csv`·Windows10/11 실기기·3.63GB DB는 NOT_RUN. 분석기 EXE, 멀티포맷 입력 미완성. 제품 RELEASE HOLD 유지.
5. **오류/시도/대안:** 브라우저 자동화 file:// 및 localhost에서 `ERR_BLOCKED_BY_ADMINISTRATOR` 발생(정책 환경 문제, 제품 오류 여부 불명). 동일 방법 반복하지 말고 소비자 Chrome/Edge에서 파일 선택·상세·CSV 저장을 수동 검증.
6. **저장소/브랜치/SHA:** private `hibi89/candle_scraper`, `feature/candle-pattern-analyzer`; 이전 HEAD `dad206a3e4c0107fc09fc92f3fe2ef4e8648d56c`. 신규 HTML, Node 검사, 이 문서 및 STATUS/docs만 추가/변경. 최신 SHA는 변경 후 원격 확인. `main` 원본 보존.
7. **배포/환경:** 단일 HTML을 Windows에서 더블클릭하고 기존 검색 CSV 선택. 외부 연결이나 실행 파일 설치 없음. Vercel 미적용, Windows EXE는 별도 개발 대상.
8. **원본/보안/금지:** `E:\\업비트 캔들긁어오기\\upbit_candles.sqlite3`/WAL/SHM 및 CSV 내용 수정 없음. 외부 JS/HTTP/CDN 미사용, 텍스트는 DOM textContent로 삽입, 필터 CSV 내보내기만 별도 다운로드.
9. **다음 우선순위:** 실제 사용자 CSV 뷰어 결과/수식값 확인 → 특정 종목 240분봉 및 전종목 전8분봉 실검증 → Windows 무설치 분석기 EXE → 입력 포맷 확장 → 상용 이용범위/출시 승인.
10. **갱신 기준:** 2026-11-06 KST, 로컬 HTML 파싱 검사와 소스 확인 범위. 실제 브라우저/고객 PC 검증 없이 실사용 완성 주장 금지.

---

# 캔들 패턴 분석기 v1.0 최신 인수인계 — 2026-11-06 00:26 KST

1. **목표·기술·확정 요구:** 수집기와 독립된 오프라인 맞춤식 검색기. 보라 EMA560 > 노랑 EMA280 > 분홍 SMA280 > 파랑 SMA560 > BB(20,2) 상단, SMA280이 SMA560을 이번 봉에서 골든크로스. KRW 전 종목·1/3/5/10/15/30/60/240분봉, DB 모든 누적 봉 또는 최근 N개 신호만. Python3.11+ 표준 라이브러리, SQLite 읽기 전용, CSV 출력.
2. **완료·설계·결정:** `pattern_analyzer.py`(CLI+인터랙티브), `start_pattern_analyzer.bat`(Windows 더블클릭, Python 필요), `test_pattern_analyzer.py` 회귀. 종목 전체/단일/복수 선택·검색 메뉴, 분봉 선택, N 자유 입력, 진행률/ETA, CSV 기존 파일 보존·원자 저장. 빠른 후보 필터에서만 BB 표준편차 계산. CLI 단독보다 메뉴 병행을 선택(유지보수·의존성 비용 낮음), 임의 고객 코드 실행 미도입.
3. **검증 명령·결과:** Python3.13.5 `python -m unittest -q test_pattern_analyzer.py`: **23 PASS, 0 FAIL/ERROR**. `python -m compileall -q pattern_analyzer.py test_pattern_analyzer.py` PASS. 합성 12,345봉, 실제 계산 합성 교차 1회, 전체/최근 1,000, 오류/중단/원자 파일, 한글 경로, 두 DB, 메뉴 정상. 사용자의 약 3.6GB 업비트 원본 검증 **NOT_RUN**, Windows10/11·EXE **NOT_RUN**.
4. **완료/진행/대기/차단:** Python 검색기 v1.0/테스트/더블클릭 BAT/설명서 ZIP 완료. 실제 데이터 진단, 상용 무설치 EXE, CSV/JSON/Excel/Parquet 입력은 미완료. 기존 거래소 수집기의 출시 **RELEASE HOLD**와 별도.
5. **오류·원인·재시도 금지·대안:** 종목 검증 시 예전 테스트는 미존재 종목 0건 결과를 기대했으나 새 설계는 명시적 오류 처리; 교차 후보 선별 때문에 목(mock) 신호 테스트를 갱신. 수정 후 23 PASS. 실제 PC 오류·성능은 아직 재현된 바 없으므로 단정 금지. 고객 대형 DB를 GitHub로 복사하지 말고 사용자 PC에서 읽기 전용으로 확인.
6. **저장소·브랜치·SHA·경로:** private `hibi89/candle_scraper`, `feature/candle-pattern-analyzer`, 초기/원본 main `1f976770db4797bcaa846ed32962e306318971ca`. 코드/테스트/BAT Git blob은 `cb41a4935e3b890e26f30b479804e14d628ef16c`, `e52c206224b1c241fde0d4b5d4dd2ddaf72873dd`, `a8d5e8710c22fe3a6be34a7aa58a4b598704f4be`; GitHub 문서 커밋 후 브랜치 HEAD 재조회. `docs/PATTERN_ANALYZER.md` 핵심 수식 명세.
7. **환경·Production/실행:** Python3.11+가 있으면 ZIP 해제 후 `start_pattern_analyzer.bat` 실행, 또는 `py pattern_analyzer.py --db "E:\\업비트 캔들긁어오기\\upbit_candles.sqlite3" --markets BTC,ETH --units 240 --last 10000 --output results.csv`. Windows EXE 아직 빌드하지 않음. Vercel 미적용, CI Windows 작업 없음.
8. **원본·백업·보안/변경금지:** 로컬 `E:\\업비트 캔들긁어오기\\upbit_candles.sqlite3`, 관련 -wal/-shm은 사용자 장비에만 두고 건드리지 않음. GitHub에는 소스·합성 테스트·문서만, 시세/키/실DB/EXE 없음. 실제 수집기 main 및 과거 ZIP 보존. 결과는 `.csv`에만 기록, 입력 DB `mode=ro`+`query_only`.
9. **다음 우선순위·완료 기준/승인:** (a) 사용자 로컬 DB 전체 검색 + 성능/ETA/출력 및 차트 시각 검증 (b) Windows 10/11 비관리자·한글 경로 검증 (c) PyInstaller 독립 EXE + 메뉴 빌드·실기기 점검, 필요 비용/권한 사전 확인 (d) 고객 CSV/JSON/Excel/Parquet 어댑터 (e) 상업적 라이선스 검증과 최종 사용자 RELEASE 승인. 구버전 실행 중에는 교체 파일 자동 적용되지 않음.
10. **갱신 기준·검증 범위:** 2026-11-06 00:26 KST. 로컬 합성 DB 오프라인 Python 23개 테스트·ZIP 무결성/소스 SHA 검증까지 완료. GitHub Actions/실제 업비트 DB/Windows EXE/실차트/판매 허가 검증 없음.

---

# 캔들 패턴 분석기 브랜치 인수인계 — 2026-11-05 KST (최우선)

1. **목표·확정 요구·기술:** 기존 수집기 독립 유료 오프라인 패턴 검색 도구(예정가 170,000원). 기존 업비트 SQLite의 모든 KRW 종목·1/3/5/10/15/30/60/240분봉·누적 전체 과거 10,000봉 이상에서 사용자 수식 검색, 종목/봉/시간/조건값 CSV. Python 3.11+ 표준 라이브러리. 선택 `--last N`, 0=전체, N=종목/분봉별 최신 N개 결과만 판단; 계산은 전체 이력 사용. SQLite 고정 스키마를 첫 입력으로 구현, 기타 CSV/JSON/Excel/Parquet는 향후 어댑터.
2. **완료 기능·근거:** `pattern_analyzer.py` 추가, 수집기/시장 DB 변경 없음. 조건은 직전 `SMA280<=SMA560`, 현재 `SMA280>SMA560`, 위치 `EMA560(보라)>EMA280(노랑)>SMA280(분홍)>SMA560(파랑)>BB20 upper`. Bollinger population std 2배, EMA 최초 종가 시드. `mode=ro`+`query_only`, 순차 O(560) 보조 메모리, 실패 시 결과 CSV 중간 산출물 제거, 기존 CSV 자동 덮어쓰기 금지. 설계: 외부 고객 수식을 Python 동적 실행하는 안보다 현재 정형 규칙 코어를 우선하여 임의 코드 실행을 배제.
3. **테스트 명령·증거·미검증:** 로컬 `python -m unittest -q test_pattern_analyzer.py`, Python 3.13.5, **12/12 PASS** (기본 지표, 인위적 실제 가격 추세 교차 1건, 최근 100개에서 0건, SQLite 읽기 전 원본 SHA256과 후 SHA256 동일, CSV BOM, 원자 처리/덮어쓰기 보호, 스키마 오류, CLI). 정확한 GitHub 원격 SHA의 Windows CI **NOT_RUN**. 실 업비트 사용자 DB 및 TradingView 비교 **NOT_RUN**.
4. **완료/진행/대기/차단:** Python MVP 구현·합성 시험 완료 / 고객 데이터 실검증·EXE 인터페이스 진행 대기 / 다른 파일 포맷 미구현 / 수집기 배포는 별도 유상 이용조건 검토 **RELEASE HOLD**. 분석기 전체 완성률은 근거 부족으로 미산정.
5. **실패·복구·원인/대안:** 분석기 테스트 코드 SQLite 연결 누수 경고를 `contextlib.closing`으로 제거; 테스트 12개 최종 PASS. 무작위 합성 가격에서 존재 가능한 교차 판정 신호를 확인하고 고정 시계열 회귀로 유지. 대량 실제 DB 검증 실패를 주장하지 않는다(시도하지 않음). 원본 손상 시나리오에는 `mode=ro`+출력 경로 분리+기존 파일 보호 적용.
6. **저장소·브랜치·SHA·주요 경로:** private `hibi89/candle_scraper`, `feature/candle-pattern-analyzer`, 초기 `1f976770db4797bcaa846ed32962e306318971ca`, 기능·테스트 소스 HEAD `ab5d904701fe78a273978ca81bcd6622e4dcb7ad`; 문서 업데이트 후 최종 SHA 확인. `pattern_analyzer.py`, `test_pattern_analyzer.py`, `docs/PATTERN_ANALYZER.md`.
7. **환경·Production·실행:** Windows 개발 예정, Python CLI `py pattern_analyzer.py --db "C:\\path\\upbit_candles.sqlite3" --last 0 --output matches.csv`. 기존 Windows EXE 빌드는 수집기용이며 분석기 EXE는 아직 없음. Vercel/웹 배포 미적용. 외부 유료 실행 없음.
8. **원본 위치·백업·인증·수정 금지:** 사용자 `E:\\업비트 캔들긁어오기\\upbit_candles.sqlite3` 로컬 원본은 접근하지 않음; GitHub에는 소스/문서/합성 테스트만. 다른 실 DB, API 키, EXE, CSV, 고객 데이터 업로드 금지. 기존 수집기 Legacy 원본은 Library 및 `main`에 보존. 분석기는 수집기 코드를 import하지 않음.
9. **다음 순서·완료 기준·승인:** (a) 사용자 DB 실제 전체 누적 데이터에서 읽기 전용 실행과 시간대/지표 실제 차트 대조 (b) 시간봉과 탐색 건수 선택 메뉴형 Windows EXE 독립 배포, 출력 검사 (c) CSV/JSON/Excel/Parquet 포맷 어댑터, 회귀 (d) 계약·상용 이용 및 사용자 출시 승인. 무단 수집기 API 연동·외부 발송 금지. 설계 변경/범위 축소 사전 승인.
10. **갱신시각·기준:** 2026-11-05 KST. 로컬 합성 데이터, 파이썬 12개 단위시험만 성공; GitHub Windows Actions/실 DB/실 EXE/거래소 라이선스 미검증. 이 문서 반영 커밋은 최종 브랜치 HEAD로 재확인.

---

# HANDOFF 최신 검증 — 2026-11-05 22:50 KST

**기술 전체 완성률 추정 99% (직전 98% 대비 +1%p), 판매 RELEASE HOLD.** 기술 진척과 상업용 출시 허가는 별개의 게이트이다. 이 문서 아래의 98%, 97%, 95%는 역사적 기록이며 최신 판정이 아니다.

1. **목표·요구·기술:** Windows 로컬 무설치 EXE 3종(업비트/빗썸/통합), KRW 전 종목, 월/주/일/240/60/30/15/10/5/3/1분 11봉, 최초 각 10,000개 완료봉·이후 증분 무제한, 5워커, SQLite DB 거래소별 분리, CSV, 진행률/ETA, 오류로그, Python3.11 stdlib/PyInstaller. 기존 요구/원본 변경 없음.
2. **완료/결정/근거:** 페이지 일부 INSERT 중 예외 발생 시 `rollback()`해 기존 정상 데이터를 보존, 실패한 DB 열기/PRAGMA/WAL/DDL/초기 검증이나 KeyboardInterrupt 시 `close()`보장. 기본 SQLite 자동 정리에 의존하는 방식보다 실패 범위가 명시적인 최소 수정 선택. 기존 안전한 PK/커서/429 제한/다종목 매트릭스 보존. 신규 `test_v19_db_atomicity.py` 3개 회귀.
3. **테스트/증거:** [Windows CI #42038795999](https://github.com/hibi89/candle_scraper/actions/runs/42038795999) **SUCCESS**, 코드 검증 SHA `9e0632890c5621f4756e9ca7328480d860b2b710`, Windows Server2022 Python3.11.9 PyInstaller6.16.0, `python -m unittest discover -p 'test_*.py' -q`: **147/147 PASS**; 3/3 EXE 부팅, 3/3 고객 ZIP 독립 실행 및 한글 경로 3/3, 실제 EXE의 업비트·빗썸 각각 공개 API 검사 PASS. 과거 실제 BTC 10,000봉·중단/복구는 [#42031303797](https://github.com/hibi89/candle_scraper/actions/runs/42031303797). 고객 PC Windows10/11/SmartScreen·전종목 장시간 실제 운용 NOT_RUN.
4. **진행/차단:** 기능 검증 기준 기술 추정 **99%**; 추가 실제 PC·라이선스 별도. **유상 판매 HOLD**. 업비트 제6조 제3항 유료 프로그램 양도·배포/이용 허락 금지, 빗썸 유상 EXE 판매 라이선스 미확정, 서면 허가·사용자 출시 승인 없음.
5. **오류/시도/대안:** 과거 Windows f-string/CP1252/테스트 SQLite 연결 누락 등은 이후 성공 SHA로 해결. 이번 실패 주입 테스트에서 SQLite 데이터 트랜잭션 롤백·핸들 보존 문제를 명시적으로 보완하고 CI 147 PASS. 실패 SHA 반복·대량 API 재수집 불필요. 기술 이외 판매 제한은 버그가 아니라 이용약관 협의/제품 구조 변경 문제.
6. **저장소/브랜치/SHA/주요 경로:** private `hibi89/candle_scraper` `main`; **기능 통합 검증 SHA `9e0632890c5621f4756e9ca7328480d860b2b710`**, 그 후 별도 `docs/RELEASE_CHECKLIST.md`·`docs/COMMERCIAL_API_POLICY.md` 정정 커밋 `f1d5ccd5f197ea464d643453de3cb4a37b0bbb70`. 이 문서의 최종 HEAD는 다시 GitHub 조회. `collector.py`, `test_v19_db_atomicity.py`, `.github/workflows/windows-build.yml`, `docs/RELEASE_CHECKLIST.md`.
7. **Production/환경:** Vercel 미적용. Windows GitHub Actions run `42038795999`, Python3.11.9 PyInstaller6.16.0. 내부 고객 ZIP 3종 artifact ID `13419497818`, EXE 실 API 감사 artifact ID `13418954271`, 만료 2026-11-19 22:48~22:49 KST. ZIP SHA256: Upbit `a61393bf8dd058afc7aed44d73329b8accb24e7df53386f12316dfd754bd7e00`, Bithumb `e5677ca43f26c9b24bb52bb663dc1602210ee6e8b5747086e7df6f047136cbbf`, Both `b152e053408810f0e9873fe8c564f991fcb896973935c2b1d391afdf197f9ade`; 통합 artifact sha256 `11572559bf3dc092099dd47028a86455ea811c76027d47d1bbb3450486ebc5d1`. 테스트 전용/판매 미승인.
8. **원본/백업/인증·변경금지:** v1.4~v1.6.1 원본 ZIP은 Library에 별도 보존, v1.6.1 원본 ZIP SHA256 `a913ac56674dc3d712b134e56dc11b78ae1e48d5e716a11e6d408d8a82eedf50`. 사용자 `E:\업비트 캔들긁어오기\upbit_candles.sqlite3` 및 기존 로컬/시장 DB 절대 건드리지 않음. CI는 새 임시 DB/모의 데이터만 쓰며 GitHub에 고객 DB/CSV/비밀·EXE 없음. SOURCE_MANIFEST.json은 최초 스냅샷 기록만.
9. **다음 우선순위/완료 기준·승인:** 실고객 Windows10/11 비관리자·SmartScreen/Defender 확인, 전종목/11봉의 실제 장기 스트레스 검증(요청 제한/이용조건 고려), 업비트/빗썸 유료 EXE 유통 **서면 허가** 및 사용자 출시 최종 승인. 문의 초안 `docs/LICENSING_REQUEST_DRAFTS.md` 미발송. 허가 불가시 정식 라이선스 소스 또는 오프라인 CSV 상품으로 범위 전환 *사전 사용자 승인* 필요. 99% 진행을 판매 허용으로 해석 금지.
10. **갱신 시점/KST/증거/문서 SHA:** 2026-11-05 **22:50 KST**. GitHub CI SUCCESS #42038795999 정확한 소스 SHA `9e0632890c5621f4756e9ca7328480d860b2b710`; 별도 sandbox 다운로드 artifact 및 3개 ZIP CRC/SHA256 검수 PASS. Windows Server 2022에서 실제 EXE 실행 확인; 일반 사용자 Windows10/11 등 미검증. 본 HANDOFF 반영 문서 커밋은 main 원격 최신 HEAD로 재확인.

---

# HANDOFF 최신 — 2026-11-05 22:30 KST

**현재 기술 완성률 추정 98% (97% → +1%p), 유상 배포 RELEASE HOLD.** '98%'는 기술 품질의 프로젝트 추정이며 **판매 98% 허가**가 아니다. 아래 97%, 95% 등은 역사적 시점이다.

1. **목표·확정 요구·기술:** 기존 크몽 Windows 무설치 EXE 3종(Upbit/Bithumb/Both), KRW 전 종목, 11봉, 최초 10k 완료봉과 이후 무제한 증분, 선택적 시간봉, 5 병렬 워커, SQLite 별도 DB/CSV, 진행률/ETA. Python 3.11 stdlib/PyInstaller 6.16.0. 디자인/서비스 범위 변경 없음.
2. **완료·변경·설계:** 기존 140개 회귀·EXE 검증 보존. 새 공통 RateGate: **짧은/헤더 없는 429도 다른 4개 병렬 요청자가 일시 정지**; 30초 초과/최종 429 정책 보존. 신규 오프라인 데이터 매트릭스 5×11×2=110조합, 장애-재시도 54/55→55/55, 증분/CSV/중복. 추가 실제 EXE 한글·공백 경로 실행·DB 조회 메뉴 무쓰기 검증 3판형.
3. **테스트 명령·결과/범위:** `python -m unittest discover -p 'test_*.py' -q` **144/144 PASS**. `build_windows.bat` 5/5 단계 PASS, `python -m compileall -q .` PASS. 최신 [Windows Actions #42035893214](https://github.com/hibi89/candle_scraper/actions/runs/42035893214) source SHA `75bdd6ea6d78887200b93f29fab9b389c3054e3f`: EXE 3/3, 고객 ZIP 3/3, Unicode 경로 3/3, 실제 EXE 공개 API 검사 3개 판형 PASS. 이전 각 거래소 BTC 1분봉 실제 10k/중단/복구 CI [#42031303797](https://github.com/hibi89/candle_scraper/actions/runs/42031303797). 전 종목 장시간·소비자 Windows10/11 직접 검증 **미실시**.
4. **진행·대기·차단:** 전체 기술 완성률 **98%** (이전 97% 대비 +1%p). 고객 Windows10/11·SmartScreen/Defender 미확인. **유상 판매 HOLD**: Upbit API 사용 프로그램 유상 배포 금지 조항, Bithumb 유상 EXE 권리 미확인. 승인 전 고객에게 ZIP/시장 DB 제공 금지.
5. **오류/원인/시도/재시도:** 첫 신규 다종목 테스트 [#42035413941](https://github.com/hibi89/candle_scraper/actions/runs/42035413941) 실패 원인은 **테스트 코드** SQLite context-manager 비종료 `WinError32`, mock `block_for` 기대횟수 누락. `closing()`과 assertion 정정 후 [#42035667647](https://github.com/hibi89/candle_scraper/actions/runs/42035667647) SUCCESS, 후속 Unicode 최종 [#42035893214](https://github.com/hibi89/candle_scraper/actions/runs/42035893214) SUCCESS. 실패한 SHA 재실행/무의미한 API 대량 검사 불필요.
6. **GitHub·브랜치·SHA·경로:** 비공개 `hibi89/candle_scraper`, `main`; **최신 실제 빌드 검증 SHA `75bdd6ea6d78887200b93f29fab9b389c3054e3f`**. 본 HANDOFF 문서 커밋 후 현재 HEAD를 재확인. 주요 `collector.py`, `test_v17_retry_safety.py`, `test_v18_market_matrix.py`, `verify_customer_packages.py`, `build_windows.bat`, `.github/workflows/windows-build.yml`.
7. **Production·실행 환경:** Vercel 미적용; GitHub Windows Server 2022 Python3.11.9/PyInstaller6.16.0. 내부 고객 ZIP artifact **13418123592**/실 EXE API 감사 **13417524024**, 2026-11-19 22:29~22:30 KST 만료; 원본 외부 ZIP 29,715,882bytes SHA256 `46651307e7fad65502f2bb46e0d6ba29284afb5df09ddc310748e099ebfa68eb`. 개별 ZIP 해시는 STATUS 최신 섹션 참조. 판매 릴리스 아님.
8. **원본·백업·인증/수정금지:** 모든 v1.4~1.6.1 소스 ZIP Library/비공개 GitHub 보존, v1.6.1 원본 ZIP sha256 `a913ac56674dc3d712b134e56dc11b78ae1e48d5e716a11e6d408d8a82eedf50`. 사용자 `E:\업비트 캔들긁어오기\upbit_candles.sqlite3` 수정/동기화 금지, 비밀키·시장원본·고객 DB·EXE의 GitHub 원본 소스 내 반영 금지. CI는 임시 DB만 사용.
9. **다음 우선 작업·완료 기준·승인:** (a) 현행 판매 모델을 유지하려면 거래소 양사에 공식 유상 프로그램 라이선스 서면 허가 확인—미발송 문의 초안은 `docs/LICENSING_REQUEST_DRAFTS.md`, 사용자 승인 전 발송 금지 (b) 소비자 Windows10/11 비관리자 ZIP 실행·Defender/SmartScreen 증거 확보 (c) 필요 시 실제 전종목 실행은 사용자의 별도 동의와 API 정책/리소스 검토 후 한정 수행 (d) 허가 불가 시 사용자 승인 후 오프라인/정식 라이선스 데이터 소스 상품으로 전환 (e) 사용자 RELEASE 승인. 불허된 상태에서는 기술 100%여도 출시 금지.
10. **KST·검증 시점·문서 커밋:** 2026-11-05 **22:30 KST** 기준 GitHub Actions `42035893214` 완료 SUCCESS 및 로컬 다운로드된 GitHub artifacts 4개 ZIP 해시/압축 무결성 확인. 고객 PC/실 상용허가 미검증. 문서 기준 SHA는 갱신 후 remote HEAD 확인.

---

# HANDOFF 최신 — 2026-11-05 22:15 KST

**최신 확인된 기술 완성률 97% (전 회차 95% → +2%p) / 판매 RELEASE HOLD.** 아래 연혁의 95%,94% 등은 과거 시점 기록이다.

1. **목표·기술:** Windows 무설치 EXE 업비트/빗썸/통합 3종, KRW 11봉, 최초 10,000 완료봉+증분 무제한, 진행률·ETA, SQLite·CSV, 오프라인 Python3.11 stdlib/PyInstaller, 고객 ZIP. 크몽 유료 판매 모델은 법적 허가 전 중지.
2. **완료 기능·근거:** 원래 수집/중복·복구/CSV/실 API 기능 유지. HTTP `Retry-After` 초·HTTP-date 해석, 30초 초과 제한 즉시 중지, 최종 5번째 재시도까지 긴 쿨다운 감지, 같은 거래소 5개 작업자에 공통 쿨다운 적용. 두 거래소 별도 제한 유지. 오프라인 모의·실 Windows 회귀 통과.
3. **테스트/검증:** [CI #42033704161](https://github.com/hibi89/candle_scraper/actions/runs/42033704161) 소스 SHA **`da582b1c4c6db6740c08d2ddce7788d8e658724d`**, Windows 2022/Python3.11.9/PyInstaller6.16.0, **140/140 tests PASS**, compileall PASS, EXE 3/3 시작·종료, ZIP 3/3 독립 실행, 실제 고객 EXE 3판형 공개 API 11봉 점검 PASS. 별도 [10,000봉 실복구 CI #42031303797](https://github.com/hibi89/candle_scraper/actions/runs/42031303797) 두 거래소 각각 BTC 1분봉 10k·중단/복구/CSV PASS. 소비자 Windows10/11 및 전 KRW/전 봉 장기운영 NOT_RUN.
4. **상태:** 기술 완성률 **97%** (프로젝트 추정, 100% 실서비스 또는 법적 허가가 아님). **SALE HOLD**—업비트 API 연동 프로그램 유상 배포 제한 확인, 빗썸의 현행 유상 소프트웨어 재판매 허가 미확정. 사용자 라이선스 요청/제품 범위 변경 승인 없음.
5. **실패·원인·재시도:** 과거 YAML/f-string/Windows 콘솔 cp1252/SQLite 파일 핸들 수정 완료. 이번 회차는 서버 긴 `Retry-After`를 최대 30초로 잘라 재요청할 수 있는 API 정책 위험을 해결; 작업자 공유 cooldown 및 5번째 시도 누락 경로 보완. CI 두 차례 최신 성공, 실패 재시도 필요 없음. 무의미한 재빌드 금지.
6. **저장소·브랜치·SHA:** 비공개 `hibi89/candle_scraper`, `main`. **검증된 최신 기능 SHA `da582b1c4c6db6740c08d2ddce7788d8e658724d`**. 이 HANDOFF와 STATUS 변경 후 원격 HEAD 별도 확인. 주요 `collector.py`, `test_v17_retry_safety.py`, `.github/workflows/windows-build.yml`, `live_history_probe.py`, `docs/COMMERCIAL_API_POLICY.md`, `docs/LICENSING_REQUEST_DRAFTS.md`.
7. **배포/실행:** Vercel 미적용, Windows Server 2022 GitHub Actions 내부 검증만. CI #42033704161, 고객 ZIP artifact **13417935853**, Live EXE 감사 artifact **13418225561**, 2026-11-19 22:13~22:14 KST 만료. 최신 ZIP 해시: upbit `32cc7ee09682410bc0205c88b464bb1667d34eeb167f024215e90d0ea935885f`; bithumb `bc22cab45bdd2579c4cc5cd06733dbf64441942de1f5911097e3d42ce0cb4f81`; both `26a27c2c063579d0c39ee4f9b2669d36ec6a0583686d01127d6ec35ffa57e711`.
8. **원본·백업·인증 보존:** 레거시 v1.4~1.6.1 ZIP은 ChatGPT Library 별도, v1.6.1 ZIP SHA256 `a913ac56674dc3d712b134e56dc11b78ae1e48d5e716a11e6d408d8a82eedf50`, `E:\\업비트 캔들긁어오기\\upbit_candles.sqlite3` 및 고객 로컬 데이터 수정 금지. GitHub에 비밀/API Key/시장 데이터/EXE 미커밋. SOURCE_MANIFEST.json은 역사적 최초 업로드 스냅샷.
9. **다음 단계/승인:** (최우선) 업비트 유상 API 연동 프로그램 배포 특별 허가 가능 여부와 빗썸 상용 배포 조건을 **공식 서면 확인**. 외부 문의는 준비된 미발송 초안 기반 사용자 승인 후에만. 허가 불가 시 사용자 승인 후 정식 라이선스 데이터 공급자 교체 또는 API 비연동형 제품 전환. 이후 일반 Windows10/11 보안/쓰기권한·SmartScreen 직접 확인, 전 KRW 장기 수집과 재시작 회귀, 동일 출고 SHA 고객 ZIP 검증 후 출시 승인.
10. **갱신·증거·커밋:** 2026-11-05 **22:15 KST**. 이번 회차 GitHub Actions SUCCESS 로그/아티팩트 해시/빌드 원본 SHA 확인. 상용 라이선스, 고객 Windows10/11 미검증 명시. 문서 기준 GitHub 커밋은 별도 최신 HEAD로 확인.

---

# HANDOFF 최신 검증 — 2026-11-05 21:59 KST

**현재 기준: 기술 전체 완성률 추정 95% (직전 94% → +1%p), 판매 RELEASE HOLD.** 아래 94%, 92%, 85%는 과거 시점의 역사적 상태이며 우선 참조 금지.

1. **목표/기술:** 크몽 판매용 Windows 무설치 업비트/빗썸/통합 EXE 3종, 11봉, KRW 전 종목, 최초 10k 완료봉·증분 무제한, SQLite/CSV, Python 3.11+ 표준 라이브러리/PyInstaller. 변경 없이 원본 유지.
2. **완료/설계 근거:** 고객 EXE 3종 실제 실행·실 API 메뉴 이전 127/127 PASS. 이번 회차 신규 `live_history_probe.py`가 각 거래소 KRW-BTC 1분봉 10,000개 수집을 70회 이하 호출 제한으로 증명. 2페이지 399개 저장 후 예외 주입/재개, 중복·CSV·원자성·실제 증분 검증. 전체 전종목 수집 대신 단일 고유동성 시장에서 안전한 부하로 장기 페이지 분량 검증.
3. **테스트/검증/미검증:** [실거래소 대량 검증 run #42031303797](https://github.com/hibi89/candle_scraper/actions/runs/42031303797), SHA `f6ba8768dcd59e985354a11e4d98e7a7626d4e46`, Windows 2022 CI 2/2 jobs SUCCESS. **업비트** 399→10,000/증분 +0/CSV 10,000행/53 호출 PASS. **빗썸** 399→10,000/증분 +1/CSV 10,001행/53 호출 PASS. 정합성/PK/SQLite integrity PASS. 이전 EXE 3종 고객 ZIP 빌드·11종 실 API PASS [run #42029964305](https://github.com/hibi89/candle_scraper/actions/runs/42029964305), SHA `40c0afe32e4eecda64ada9021aad35a8d1cd96fd`. 고객 Windows10/11 환경·전 KRW/11봉 대량 장기운용은 미검증.
4. **진행/대기/차단:** 기술적 완성도 **95% (+1%p)**, 판매 HOLD. 핵심 **상업적 제약**: Upbit 현행 Open API 제6조 제3항 유상 배포 제한 및 제5조 무단 영리 이용 금지; Bithumb 영리 소프트웨어 판매 허가 미확인. 약관 근거 `docs/COMMERCIAL_API_POLICY.md`. 유상 판매/배포를 절대 성공 판정하지 않는다.
5. **오류·복구·재시도:** 이전 YAML/f-string/CP1252/SQLite 핸들 문제 해결하여 성공 기록. 이번 bounded history 검증 오류 0. 같은 SHA의 불필요한 반복 실행이나 API 대량 수집 금지. 정책 미확인 상태에서 신규 유료 판매 출시/게시 금지.
6. **저장소/브랜치/SHA:** 비공개 `hibi89/candle_scraper`, `main`; 기능 검증 `f6ba8768dcd59e985354a11e4d98e7a7626d4e46`, 이후 공식 정책 문서 추가 SHA `ca180529347cb4fda6755ea57ba6aa047c2957fb`; 이 HANDOFF 갱신은 별도 커밋이므로 **현재 HEAD는 GitHub에서 재조회**. 핵심 소스 `collector.py`, `live_history_probe.py`, `.github/workflows/live-api-smoke.yml`, `docs/COMMERCIAL_API_POLICY.md`.
7. **Production/환경:** Vercel 미적용. GitHub Windows 2022 Python 3.11.9; CI RUN `42031303797` 공개 실 API 인증 없음, 각 거래소 53회 제한 호출. 내부 건수만 담긴 증거 artifact ID `13415414502`, 2026-11-19 21:58 KST 만료; 영구 백업 아님. 고객 EXE/ZIP 기존 artifact `13416505378`, 11월 19일 만료.
8. **원본/백업/보안:** 이전 v1.4~v1.6.1 ZIP Library에 보존, v1.6.1 원본 SHA256 `a913ac56674dc3d712b134e56dc11b78ae1e48d5e716a11e6d408d8a82eedf50`. 사용자 `E:\\업비트 캔들긁어오기\\upbit_candles.sqlite3` 절대 수정하지 않음. 검증 데이터는 CI 임시 SQLite/CSV, GitHub에는 데이터·키·토큰 없음.
9. **다음 단계/승인:** (1) Upbit와 Bithumb의 유료 판매용 소프트웨어 연결·시세 사용 서면 허가 취득 여부 판단, 또는 사용자 승인 후 CSV 오프라인 제품/라이선스 공급자로 전환 (2) Windows10/11 실제 소비자 환경 EXE/권한·SmartScreen 검증 (3) 임시 데이터로 전종목·재시작·429회귀 (4) 동일 배포 SHA에서 회귀/고객 ZIP 해시 검증 후 사용자 출시 승인. 기술 검증만으로 HOLD 해제 금지.
10. **검증 시각/KST/범위/문서 기준:** 2026-11-05 **21:59 KST**. Windows 2022 GitHub Actions `42031303797` 소스 SHA `f6ba8768dcd59e985354a11e4d98e7a7626d4e46` 2/2 PASS 및 실 API 검증 로그 확인. 이 문서를 포함한 최종 main SHA는 문서 업데이트 직후 재조회. 사용자 로컬 Windows10/11, 법적 허가, 전 KRW 장시간 수집은 미검증/차단.

---

# HANDOFF 최신 확인 — 2026-11-05 21:49 KST (이 문서의 최우선 기록)

**한눈에 보는 최신 기준:**
- 목표/기술: Windows 무설치 코인 캔들 수집기 업비트/빗썸/통합 EXE 3종, Python 3.11 stdlib + PyInstaller.
- 완성/판정: 판매 완성률 추정 **94%** (이전 85% 대비 +9%p), **RELEASE HOLD**; 일반 고객 Windows 10/11 직접 실행, 장기 전체 종목 10,000봉 실수집, 데이터 이용조건 검토가 남음.
- Windows 2022 CI: [run #42029964305](https://github.com/hibi89/candle_scraper/actions/runs/42029964305) SUCCESS, 정확한 실행 SHA **`40c0afe32e4eecda64ada9021aad35a8d1cd96fd`**. Python 3.11.9, PyInstaller 6.16.0, unittest 127/127 PASS, EXE 3종 및 ZIP 3종 독립 실행 3/3 PASS.
- **실행 파일 자체 검증**: 최신 ZIP 3종을 별도 임시 폴더에 풀어 각 EXE 메뉴 `[5]` 공개 API 점검 수행. Upbit 전용 11봉 PASS; Bithumb 전용 11봉 PASS; 통합형 업비트·빗썸 각 11봉 PASS. 페이지 2차 응답 조회, DB 불생성, 오류 0.
- **실제 임시 DB 단위/증분 검증**: 이전 성공 [run #42028865266](https://github.com/hibi89/candle_scraper/actions/runs/42028865266) SHA `5a503c9f214e11ae77ebfb264478bef3b4cafa00`, 거래소별 KRW-BTC 11봉·2페이지·일봉 11개 이하 임시 SQLite 최초/갱신·CSV BOM 및 PK 무결성 PASS. 실수집은 KRW-BTC에 제한, **전 종목 검증 아님**.
- **고객 ZIP 최신 SHA256**: upbit `6985a6ae9c8ed094161db16863af7ce3d52cbc60862c85325efb27649db7e314`; bithumb `5bd484fda1e6bfdd9be20527db4139bb958d2b7cdd3213c995df5dee390ae741`; both `0e7ccc6850e67a36b2d6e71b6acc42611dd7ceb10026f8f51560f3737bb903f0`. 업로드 이전 ZIP과는 해시가 다름.
- GitHub 기록: 비공개 `hibi89/candle_scraper` 브랜치 `main`, 최신 기능 검증 SHA `40c0afe32e4eecda64ada9021aad35a8d1cd96fd`; 최신 `.gitignore` `197ed84544f4ec1c2a980253a46551d0f9ad374a`. **이 문서 반영 후 HEAD가 변경되므로 반드시 원격 main 재조회.** Author/Committer = `hibi89`. Vercel 배포 **미적용**.
- 내부 CI 산출물: 고객 ZIP 3종 artifact ID `13416505378`; 실행파일 live API evidence artifact ID `13416380913`, 각각 **2026-11-19 21:48~21:49 KST 만료**. 실제 파일은 Actions run의 Artifacts에서 받고, 공개 판매 릴리스가 아니다. 장기 보관 확인 없음.
- 보안·원본: 이전 v1.4/1.5/1.6/1.6.1 원본 ZIP은 Library, 고객 DB/CSV/.env/토큰/실시세는 GitHub 비반영. 사용자 `E:\업비트 캔들긁어오기\upbit_candles.sqlite3` 불변. `SOURCE_MANIFEST.json`의 파일별 해시는 최초 GitHub 스냅샷에만 대응.
- 실패 원인과 복구: YAML plain scalar, Python3.11 메뉴 f-string, Windows CP1252, 실검증 임시 SQLite 핸들 WinError 32 모두 소스/CI 최소 변경으로 해결 후 성공 런 검증. 과거 실패한 동일 SHA 반복 금지.
- 다음 우선순위·완료 조건: 고객 환경 Windows10/11 실제 ZIP 실행·SmartScreen/보안·폴더 권한 확인 → 전 종목 장기 실수집·증분·복구 정합성 표본 검증(새 DB만) → 거래소 별 이용조건/상용 EXE 설명 정책 검토 → 동일 배포 SHA에서 최종 회귀·해시 대조 → **사용자 출시 승인**. 완료 시 RELEASE HOLD 해제.
- 검증 시점: **2026-11-05 21:49 KST**, 확인 범위는 Windows Server 2022 CI 및 공개 Upbit/Bithumb API 실호출, 일반 고객 PC는 **미검증**. GitHub 인수인계 문서 기준 커밋은 문서 갱신 후 `main` HEAD로 확인한다.

---

# HANDOFF — Coin Candle Collector v1.6.1

## 최신 우선 인수인계 — 2026-11-05 21:40 KST
**아래 '이전 이력'에는 이전 시점의 85%/NOT_RUN 기록이 남아 있다. 최신 근거는 이 10항과 STATUS.md이다.**

1. **목표·요구·기술**: 크몽 판매용 Windows 무설치 EXE 3종(업비트/빗썸/통합), 메뉴형 최초 최대 10,000 완료봉·무제한 증분, 월/주/일/240/60/30/15/10/5/3/1분봉, 거래소별 SQLite, CSV, 재시작/이어받기. Python 3.11 stdlib + PyInstaller 6.16.0.
2. **완료·설계**: v1.6.1 수집기·무결성/중복키/복구·127 오프라인 테스트 보존. 이번 작업에서 Python 3.11 메뉴 파서/Windows CP1252 출력을 고치고, 의존 도구 버전 및 GitHub Actions 액션 SHA를 고정한 Windows 자동 빌드·고객 ZIP 해시 증거를 확보. 실 API용 별도 일회성 임시 DB 스크립트 추가.
3. **테스트·범위**: Windows Server 2022 Python 3.11.9 / PyInstaller 6.16.0, 127/127 PASS, `build_windows.bat` 5/5 PASS, EXE 시작/종료 3/3, 독립 고객 ZIP 3/3. Windows Actions [run #42027942187](https://github.com/hibi89/candle_scraper/actions/runs/42027942187) / SHA `f39932db1c5253c38fc8e0521e419da0920237fa`. 실제 KRW-BTC 업비트·빗썸 각각 11봉·2페이지·소량 최초/증분/CSV/SQLite PK 검증 PASS: [run #42028865266](https://github.com/hibi89/candle_scraper/actions/runs/42028865266) / SHA `5a503c9f214e11ae77ebfb264478bef3b4cafa00`. 전체 KRW 대량 수집과 일반 소비자 Windows 10/11 검증은 NOT_RUN.
4. **상태**: 전체 판매 완성률 **보수적 추정 92% (+7%p)**, **RELEASE HOLD**. GitHub 내부 ZIP 아티팩트 3종 생성 완료, 고객 배포 승인 아님. 실 API 2개 거래소 소량 실증 성공. Vercel은 미적용.
5. **오류·재시도 주의**: (a) Actions YAML plain scalar의 `: ` → 인용/블록으로 수정 (b) 3.11 동일 인용부호 f-string → 변수 분리 (c) CP1252 UnicodeEncodeError → UTF-8 출력 설정 (d) 실검증 임시 SQLite 핸들 WinError32 → `closing()` 수정. 각 성공 CI 로그로 해결 확인. 이미 실패한 SHA 재시도·무의미한 빈 커밋 금지.
6. **GitHub·경로**: 비공개 [hibi89/candle_scraper](https://github.com/hibi89/candle_scraper), `main`; 최종 기능 확인 SHA `5a503c9f214e11ae77ebfb264478bef3b4cafa00`, 후속 gitignore SHA `a682c4584f231b7a4db1904575b175acacef2cac`; 문서 반영 후 GitHub `main` HEAD를 다시 조회. 주요 `collector.py`, `menu.py`, `build_windows.bat`, `live_api_probe.py`, `.github/workflows/*.yml`, `verify_*exes.py`, `verify_customer_packages.py`, `make_customer_packages.py`.
7. **배포·환경**: `windows-2022` + Python 3.11.9/ PyInstaller 6.16.0. Windows 빌드 run `42027942187`, 고객 ZIP artifact ID `13414129062`; 실 API run `42028865266`, evidence ID `13415620777`. 둘 다 내부 비공개, **2026-11-19 KST 만료**, 영구 백업 아님. 서비스 URL·Vercel 미적용.
8. **원본·보안·복구**: v1.4/v1.5/v1.6/v1.6.1 ZIP은 Library에 별도 보관. v1.6.1 원본 ZIP SHA256 `a913ac56674dc3d712b134e56dc11b78ae1e48d5e716a11e6d408d8a82eedf50`. `E:\업비트 캔들긁어오기\upbit_candles.sqlite3` 등 고객 로컬 DB/비밀정보/시장 원데이터 수정·업로드 금지. GitHub가 복구 가능한 코드 기준이며 `SOURCE_MANIFEST.json`은 최초 업로드 SHA `b9a1483...`의 과거 스냅샷.
9. **다음 우선순위·승인**: (1) Windows10/11 고객 수준 3개 ZIP 직접 사용/보안 확인 (2) 양 거래소 장시간 전체 KRW/11봉 실제 최초·증분·재시작 데이터 대조 (3) 최신 데이터 이용정책·상업 배포 설명 검토 (4) 동일 출시 SHA의 회귀 및 사용자 RELEASE 승인. 유료 이용·권한/원본 변경/게시 전 추가 승인.
10. **검증 시각·문서 기준**: 2026-11-05 **21:40 KST**. Windows GitHub Actions 빌드 및 네트워크 검증 로그까지 직접 확인했으며 일반 Windows10/11 PC와 보안 백신은 미검증. 최신 문서 커밋의 SHA는 본 기록을 반영한 GitHub `main` HEAD로 확인; 원본 저장 기준은 위 SHA 및 RELEASE_CHECKLIST.md.

---

## 이전 인수인계 이력 (역사적 기록)
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

## 사용자 제공 이전 화면 설계(후속 범위) — 2026-11-05 21:16 KST
- 공통 검색 엔진은 업비트·빗썸 수집 DB를 **읽기 전용**으로 조회하고, 사용자별 패턴 수식과 통합 CSV 결과를 제공하는 향후 제품 구상임. **현재 v1.6.1 수집기에는 미구현**. 코드·DB를 임의 변경하지 말 것.
- 아키텍처/위험/대안 A·B는 `docs/FUTURE_PATTERN_SEARCH.md`. 우선 순위는 Windows EXE·실 API 검증으로 수집기 출시 HOLD 해제 후 결정.
