# 신규 이중 볼린저밴드 하단 이탈 → 복귀 → 고정 중앙선 도달 검색

## 사용자 확정 규칙
- 기준 BB A: `BB(20,2,Close)`, 20개 종가 SMA ± 표준편차(모집단 분산, ÷20) ×2.
- 기준 BB B: `BB(4,4,Open)`, 4개 시가 SMA ± 표준편차(모집단 분산, ÷4) ×4.
- **이탈 setup:** 캔들 종가 `close < A.lower` 그리고 `close < B.lower`.
- **복귀 recovery:** setup 이후 최초 `close > A.lower` 종가. B.lower의 재상향은 추가로 검사하지 않음.
- **매도 목표값:** recovery 캔들에서 계산한 `B.middle = SMA(open,4)` 값 하나를 고정. 이후 밴드가 변해도 목표값 불변.
- **재도달 touch:** recovery **당일 해당 캔들을 포함해** `high >= fixed B.middle`이면 도달로 기록. low>target인 갭상승도 도달. 실제 봉 내부 고가 발생 순서는 알 수 없음.
- **미재도달:** DB가 보유한 해당 종목·분봉의 마지막 봉까지 도달하지 않은 신호. 단, 복귀 자체가 마지막 봉이면 `NO_FUTURE_CANDLES`로 별도 구분.
- 연속 이탈은 하나의 setup episode, 최초 이탈봉 기록. 이후 첫 복귀에서 신호 하나 기록.
- ① 이탈/② 복귀 검색부터 전 종목 DB에 직접 적용; 이전 골든크로스 `results.csv`를 사용하지 않음.

## 설계 선택 및 비용
- 설계 A: 매 신호마다 별도 미래 SQL 검색 → 같은 거래쌍 반복 스캔, DB I/O 큼.
- **선택 B:** 거래쌍마다 시간순 1회 조회 → BB windows O(20+4), 목표가 최소힙을 통해 첫 도달 일괄 판정 → 중복 조회 최소, 표준 라이브러리만 이용, 정교한 예외·리포트 유지.
- 파일은 DB `mode=ro`/query_only, 고유 타임스탬프 폴더에 CSV 4종·HTML·summary.json. API 호출/비밀 저장/DB 수정 없음. 기존 원본의 WAL/SHM을 엄밀히 보존하려면 수집기 종료 후 DB 정적 사본 사용.

## 실행
`start_dual_bb_scanner.bat` 더블클릭 (Python3.11+).
`py -3 dual_bollinger_scanner.py --db "E:\업비트 캔들긁어오기\upbit_candles.sqlite3" --markets AXS,BTC --units 60,240`

## 출력 및 신뢰성
- `01_not_reached.csv`: 기준일 현재까지 미재도달.
- `02_reached_first_touch.csv`: 최초 도달봉 시각·OHLC·경과 봉 개수/분.
- `03_no_future_candles.csv`: 재진입 이후 관측 미래 봉이 없는 경우.
- `04_all_recovery_signals.csv`: 전체 기준/상태.
- `report.html`: 종목/분봉/상태 검색. 네트워크 없음.
- 복귀봉 자체에서 고가가 목표 이상인 경우 도달 판정하지만, 해당 고가가 **종가 확정 전에 발생했을 가능성**으로 인해 즉시 매매 익절 성공을 보장하지 않음.
- 누락봉·미거래 봉 가능성 때문에 100% 과거 관측치도 100% 미래 성과가 아님.

## 검증
Python3.13.5 오프라인 `python -m unittest -q test_dual_bollinger_scanner.py` 24 PASS; Python compileall PASS; 합성 SQLite/CSV/BOM/원본 SHA256 불변/HTML 스크립트 Node22 구문 PASS; ZIP CRC PASS. 사용자 3GB 원본·Windows·실차트 **NOT_RUN**.
ZIP `DualBollinger_BreakoutReentry_Scanner_v1.0.zip` 15,184 bytes SHA256 `179422a16d01a3541e65106f992a4f269143ad21db19f396adffa5a2555c131d`.
