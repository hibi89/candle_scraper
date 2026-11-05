## v1.1 — 신호 당시 고정 BB 상단 재도달 필터 (2026-11-06)

`future_retouch_review.py`: 업로드된 기존 357건 `results.csv`의 각 신호 `bb_upper`를 기준가로 사용(기본값). 신호봉 다음부터 high >= 기준가를 찾는다. 첫 터치 시각/경과분/봉 개수 기록. 골든크로스 수식/신호 목록 및 원본 SQLite는 수정하지 않는다. 이전 SMA280은 `--price-field sma280` 옵션. 실제 고객 DB 미검증. 자세한 내용은 `docs/BBUPPER_RETOUCH_v1.1.md`.

---

## 오프라인 결과 뷰어 (2026-11-06)

긴 결과 CSV를 직접 읽기 어려우면 `CandlePatternResultsViewer.html` 더블클릭 → **CSV 파일 선택** → 기존 `results.csv` 또는 `pattern_matches.csv` 지정. 다시 검색할 필요 없음. 브라우저 안에서만 읽으며 종목/분봉/거래소/날짜 필터, 검출 건수, 정렬, 60건씩 보기, 각 사건의 EMA/SMA/BB 자세히 보기, 필터 CSV 저장 기능 제공. 원본 CSV/SQLite 불변.

`node test_report_viewer.mjs` 오프라인 파서/정적 검사 9개 PASS. 실제 Windows 브라우저 실행은 검증되지 않았으며 제품 EXE 완성으로 간주하지 않음.

---

## v1.0 대화형 종목 선택·검색 옵션 — 2026-11-06

- Windows Python 설치 환경에서는 ZIP 압축 해제 후 `start_pattern_analyzer.bat` 더블클릭, 또는 `py pattern_analyzer.py --interactive` 실행.
- DB 전체 종목(기본) / 복수 특정 종목(`BTC,ETH` 또는 `KRW-BTC,KRW-ETH`) / 키워드로 DB 내 종목 목록 검색.
- 선택 분봉: `all` 또는 `1,3,5,10,15,30,60,240` 중 복수; 종목·분봉별 최근 N개 발생 신호만 검색(`--last N`), 기본 `--last 0` 전체 누적.
- 선택한 최근 N개 구간만 결과 판정하지만 SMA/EMA 시드는 전체 과거 이력부터 계산하므로 계산에 읽는 봉 수는 N보다 많을 수 있음.
- 실행 중 전체 처리율(%)·시장/분봉·완료 캔들·검출 건수·ETA 출력. CSV 기존 파일은 명시적 `--overwrite` 외 보존, 원본 DB는 항상 읽기 전용.
- CLI도 지원: `py pattern_analyzer.py --db "DB_PATH" --markets BTC,ETH --units 240 --last 10000 --output results.csv`. `--list-markets`는 DB 종목 열람.
- 성능: 볼린저 상단 표준편차는 고정 배열/골든크로스가 발생한 후보 봉에서만 계산. 추가 시계열 보관 메모리는 O(560). 실제 3GB DB 속도는 아직 미검증.
- 테스트: Python3.13.5 오프라인 23/23 PASS. Python3.11 Windows 실기기·무설치 EXE·실데이터·상용 출시 미검증.
- 상용형과 구분: 이것은 **Python 실행판 v1.0**, Windows EXE나 CSV/JSON/Excel/Parquet 멀티포맷 판매 완성판이 아님.

# 캔들 패턴 분석기 v0.1 — 구현 기준 (2026-11-05 KST)

## 제품 경계
- 이 브랜치의 `pattern_analyzer.py`는 **오프라인 분석기**다. 기존 `collector.py`, `menu.py` 및 고객의 SQLite 원본은 변경하지 않는다.
- 고객 제공 SQLite는 `file:...?...mode=ro`와 `PRAGMA query_only=ON`으로 읽는다. 거래소 API를 호출하지 않는다. 결과 CSV는 **별도의 경로**에 생성한다.
- 현재 실제로 동작하는 입력은 기존 수집기 스키마 `candles(market,unit,utc,kst,close,...)`를 가진 SQLite이다. CSV/JSON/Excel/Parquet 입력과 Windows EXE는 **후속 개발 항목**이며 구현 완료로 표현하지 않는다.

## 사용자 정의 첫 번째 규칙
각 종목·각 분봉은 독립적인 시간순 캔들 시계열로 계산한다. 마지막 데이터는 기존 수집기가 저장한 완료봉이라는 전제다.

1. 직전 확정봉: `SMA280 <= SMA560`.
2. 현재 확정봉: `SMA280 > SMA560` (SMA280의 신규 골든크로스).
3. 현재 선 배열, 위에서 아래로: `EMA560 (보라) > EMA280 (노랑) > SMA280 (분홍) > SMA560 (파랑)`.
4. 현재 교차 위치는 볼린저밴드 상단보다 높다. 구현은 **엄격하게 `SMA560 > BBupper`**, 즉 두 SMA 모두 볼린저밴드 상단 위로 정의한다.
5. `BBupper = SMA(close,20) + 2 * population_stddev(close,20)`. EMA 재귀 계수 `2/(period+1)`, 최초 캔들 종가를 EMA 초기값으로 사용한다. 동일 타임스탬프 확정봉 종가로 평가하며 미래 데이터는 보지 않는다.

시세가 누락된 시간 구간에도 수집된 봉의 **행 순서대로** 이동평균 기간을 적용한다. 차트 플랫폼의 누락봉 처리·EMA 시드가 다르면 시각적 표시와 소폭 달라질 수 있으므로 실제 차트 대조는 미검증이다.

## 범위·성능
- 기본: 업비트 등 입력 DB에서 존재하는 **모든 KRW 종목**, **8종 분봉(1,3,5,10,15,30,60,240)**, **전체 누적 캔들**.
- `--last 1000`, `--last 10000`, `--last 30000` 등은 **종목·시간봉별 최신 N개 봉의 신호만 결과로 출력**한다. `--last 0`은 전 이력을 검색한다.
- EMA/SMA의 계산 오차를 방지하려고 `--last N`을 써도 시계열의 처음부터 계산한다. 따라서 `candles_processed`는 N보다 클 수 있다. 별도 캔들 보관 상한은 없다.
- 순차/스트리밍 분석으로 각 종목·봉별 지표 메모리는 O(560), 계산 시간은 전체 처리봉 수에 비례한다.
- 과거 최초 560봉은 SMA560을 계산할 수 없고, 최초 교차 판정에는 그 다음 봉까지 필요하다.
- 출력: UTF-8 BOM CSV. 거래소, 종목, 분봉, UTC/KST, 종가, SMA/EMA 4개, BB 상단, 직전·현재 SMA 차이.
- 기존 결과 CSV는 `--overwrite` 없이는 교체하지 않는다. 실패 시 임시 CSV 삭제, 정상 종료 후 원자 교체한다.

## 사용 (Python 3.11+)
전체 누적 데이터/8종 분봉:

```powershell
py pattern_analyzer.py --db "E:\업비트 캔들긁어오기\upbit_candles.sqlite3" --output "pattern_matches.csv"
```

최근 10,000봉 신호만, 1·3·5분봉:

```powershell
py pattern_analyzer.py --db "E:\업비트 캔들긁어오기\upbit_candles.sqlite3" --last 10000 --units 1,3,5 --output "recent_matches.csv"
```

다중 DB는 `--db`를 반복한다. `--markets KRW-BTC,KRW-ETH`로 대상 축소 가능하다.

## 테스트/미검증
- 로컬 Python 오프라인 단위시험 11개 성공: 교차·배열·볼린저 조건, 지표 560봉 준비, 전체/최신 N개, 마켓/분봉 필터, DB SHA256 불변, CSV BOM/원자 저장, 파일 보호, CLI.
- 실제 사용자 DB 전체 검색, 실차트 1:1 대조, Windows EXE, 판매/배포 법적 허가: **미검증/미구현**.
- 업비트·빗썸 수집기 배포는 별도 문서의 **RELEASE HOLD** 유지. 유료 오프라인 분석기와 무료 수집기를 섞어 판매 허가를 추정하지 않는다.
