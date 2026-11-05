이중 볼린저밴드 신패턴 검색기 v1.0 (Python 3.11+ / Windows)

1. 이 폴더를 압축 해제합니다.
2. 기존 DB가 E:\업비트 캔들긁어오기\upbit_candles.sqlite3에 있으면
   start_dual_bb_scanner.bat 더블클릭만 하면 됩니다.
   해당 경로에 없으면 실행 중 경로를 입력합니다.
3. 3GB DB의 원화마켓 전체 1,3,5,10,15,30,60,240분봉을 직접 검색합니다.
   기존 results.csv는 필요하지 않습니다.
4. 새 dual_bb_results_... 폴더 안의 report.html을 Chrome/Edge에서 열어 확인합니다.

검색 규칙:
 - 20기간 종가/2배 표준편차 볼린저 하단 및 4기간 시가/4배 표준편차 하단 아래에서 종가가 마감한 첫 이탈봉을 기록.
 - 이후 처음으로 종가가 BB20 종가 하단 위에서 마감한 복귀봉을 찾음.
 - 복귀봉 당시 BB4(open) 중앙선 (4개 open SMA)을 매도 목표가로 고정.
 - 복귀봉 자체부터 이후 high>=고정 목표가면 재도달, 갭상승도 포함.
 - DB 마지막 봉까지 미도달이면 미도달 목록. 미래에 반드시 도달하지 않는다는 보장은 없음.
 - 이탈 구간에서 복수 연속 이탈봉은 하나의 에피소드로 취급하며 최초 이탈 시각을 남김.

생성 파일: 01_not_reached.csv / 02_reached_first_touch.csv /
03_no_future_candles.csv / 04_all_recovery_signals.csv / summary.json / report.html

다른 DB/종목/분봉만 실행할 경우(설치된 Python 명령행):
py -3 dual_bollinger_scanner.py --db "D:\my_candles.sqlite3" --markets AXS,BTC --units 240,60

안전: SQLite mode=ro, PRAGMA query_only=ON. API/네트워크 호출 없음, 원본 CSV/DB 덮어쓰기 없음.
진입: 복귀봉 종가 이후를 가정. 다만 복귀봉의 고가도 미도달 필터에 포함되어
'복귀봉 고가 터치'는 봉 내부 순서상 실제 매매 가능 익절임을 보장하지 않음.
데이터 중간 누락/공백이 있으면 마지막 저장된 봉까지의 관찰로 제한됨.
실제 사용자 3GB DB/Windows EXE 실행 및 차트 일치는 별도 검증 필요.

원본 보존 참고: mode=ro/query_only는 테이블 변경을 금지하지만, DB가 WAL로 실시간
열려 있을 경우 SQLite가 공유 메모리 측면 파일(-shm)을 건드릴 수 있습니다.
수집기 동시 실행 중 파일 단위의 완전한 불변성이 필수라면 수집기 종료 후
정상 백업본으로 분석하십시오. 실행기에 DB 백업/이동/삭제 기능은 없습니다.
