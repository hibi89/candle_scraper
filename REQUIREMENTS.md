# REQUIREMENTS — 코인 캔들 수집기 (판매용)

## 확정 범위
- 업비트 단독형 / 빗썸 단독형 / 통합형: Windows EXE 각각 1개, ZIP 풀고 더블클릭
- 조작: 메뉴형 터미널; 최초 수집/이어받기, 신규 캔들 갱신, CSV 내보내기, 폴더 열기, 공개 API 진단, DB 확인, 종료
- 거래쌍: 각 거래소의 원화(KRW) 마켓 전체; 거래소별 SQLite DB 분리
- 봉: 월/주/일/240/60/30/15/10/5/3/1분, 선택적 다중 체크 및 긴 봉부터 우선 처리
- 최초: 종목/봉별 최대 10,000개 완료된 캔들; 새로 생긴 캔들은 이 제한 없이 증분 누적
- 동시 종목 처리: 5개 요청자; 거래소별 호출 속도 제한 및 오류 재시도
- 무결성: UTC/KST, OHLC, 유한 수치, 정확한 종목, 날짜 내림차순, 페이지 exclusive cursor 검증
- DB 데이터 일관성: 중복 키, 페이지별 원자 트랜잭션, 중단 후 이어받기, 다른 스키마 DB 보존
- CSV: BOM 포함 UTF-8, 원자 교체, 종목/봉별 분리
- 경험: 진행률, 예상 남은 시간, 실패 로그 표시
- 공개 가격(초기): 거래소 단독 40,000원, 통합 60,000원; 향후 통합 100,000원 계획

## 별도 제품
- 개인용 업비트 캔들 수집기의 봉은 1/3/5/10/15/30/60/240분만. 판매용 11종과 혼동하지 말 것.

## 판매 출시 차단 기준
- 실제 업비트·빗썸 11종 조회, 페이지 이동, 임시 DB 최초/증분 검증
- 실제 Windows 10+ 환경에서 3개 EXE 빌드·실행·종료, 실제 고객 ZIP 독립 실행 확인
- API 정책과 시장 데이터의 재배포/사용 제한에 맞는 고객 안내 확인

## Source-of-truth and handoff
- Canonical GitHub repository: `hibi89/candle_scraper` (private), branch `main`; commit SHA must be recorded in status reports.
- Original ZIP backups remain in ChatGPT Library; GitHub source, tests, schema expectations and docs must remain available independently.
- `docs/RELEASE_CHECKLIST.md` sets the objective sales gate; Windows and live HTTP are not automatically certified by local tests.
