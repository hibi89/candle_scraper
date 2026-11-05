# 후속 볼린저밴드 상단 미재도달 검사 v1.1 — 2026-11-06

## 변경점
- 골든크로스 발생 조건 및 기존 `results.csv` 원본 357개 신호는 그대로 둔다. 신호 **발생 봉 당시** `bb_upper` 값을 신호별로 고정하여 후속 가격 도달 여부를 판정한다.
- 현재 기본값: `--price-field bb_upper`. 이전 v1.0 기본 SMA280은 이제 명시적인 `--price-field sma280`로만 사용한다. `sma560`, `close` 비교도 선택 가능하다.
- 시그널 봉 본인은 제외한다. **이후 고가(high) >= 고정 BB 상단**인 첫 봉을 재도달로 처리한다. low > 기준가인 갭상승도 재도달로 처리한다.
- 재도달 첫 봉의 UTC/KST, 고가/저가/시가/종가, 경과 분/시간, 경과 봉 개수, 갭 여부를 저장한다.
- `01_untouched.csv`, `02_retouch_backtest.csv`, `03_unresolved.csv`, `04_all_classified.csv`, `report.html`, `summary.json` 생성. 새 `reference_field` 출력 열에 사용한 기준을 명시한다.
- 첫 신호봉 자체 이후의 관측 봉이 없으면 '미재도달'이 아니라 '보류'로 분류. 마지막 수집 이후 미래는 모른다.

## 설계 및 제약
반복적으로 357건마다 SQLite를 조회하는 대안보다 종목·분봉별로 한 번씩 정렬 조회하면서 후속 high와 보류 신호를 비교하는 방식을 채택했다. 기존 패턴 수식 재계산, API 호출, 3GB DB 복사, 외부 통신을 하지 않는다.
`mode=ro` SQLite 읽기 전용 연결 및 `query_only`, 기존 원본 CSV 불변, 출력 새 폴더만 생성. 엄격한 WAL/SHM 불변이 필요하면 동작 중 수집기를 정지하고 정적 DB 사본으로 확인한다.

## 실행
`results.csv` 파일을 프로그램 옆에 두고 Python 3.11+에서 Windows `start_future_retouch_review.bat`를 실행한다. 기본 DB 경로는 `E:\업비트 캔들긁어오기\upbit_candles.sqlite3`.

```powershell
py -3 future_retouch_review.py --db "E:\업비트 캔들긁어오기\upbit_candles.sqlite3" --signals results.csv
py -3 future_retouch_review.py --price-field sma280
python -m unittest -q test_future_retouch_review.py
```

파일의 기본 `bb_upper`가 **신호봉 당시 볼린저 상단**임을 유의한다. 신호 후 이동하는 BB 라인에 도달했는지를 검사하지 않는다. 이전 v1.0 `report.html`은 v1.1 결과로 간주할 수 없다.

## 검증·출시 판정
컨테이너 Python3.13.5 합성 DB 회귀 18/18 PASS, Python compileall PASS, HTML JS `node --check` PASS, 실제 업로드 `results.csv` 357개 파싱 및 `bb_upper` 양수 확인, ZIP CRC PASS 및 사용자 원본 CSV SHA256 일치. 실제 3.63GB E: SQLite / Windows 실기기 / 차트 수동 교차검증 **미검증**. EXE 미제작, 출시 RELEASE HOLD.

패키지: `CandleGoldenCross_BBUpper_FutureRetouch_v1.1.zip`, SHA256 `8fb27b6bb106138de8bb2ee4acd7eb6b4e3155a9f8b398fbf60f28316736e7e9`, 40,712 bytes. 357건 `results.csv`는 사용자 대화 ZIP에만 포함하며 GitHub에는 올리지 않는다.
