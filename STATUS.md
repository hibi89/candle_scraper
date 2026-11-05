# STATUS — Coin Candle Collector v1.6.1

갱신: 2026-11-05 21:12 KST

## 현재 판정
- **최종 판매 완성률 추정 85%** (기준 v1.5 복구본 83% 대비 +2%p). 검증된 기능·출시 준비의 보수적 추정치이며 판매 가능 판정 아님.
- **판매 HOLD**: 실제 업비트/빗썸 HTTPS 종단 간 수집 및 Windows 10+ 실 EXE 3종 실행 검증 미실시.
- 최신 소스 보존: `coin_candle_collector_dev_v1.6.1_ci_ready.zip`. 기존 v1.4, v1.5 복구본은 덮어쓰지 않음.

## 이번 검증된 변경
1. 기존 SQLite `candles`/`collection_state`의 컬럼뿐 아니라 PK 순서를 검사해, 유사 스키마 DB 사용 시 중복 방지 실패 예방. 불일치 파일 수정 금지 검증.
2. 고객 ZIP을 만든 뒤 실제 Windows에서 ZIP별 별도 임시 폴더에 압축 해제→각 EXE 시작/종료→DB 미생성 및 판형 확인을 빌드 마지막 단계에 추가. Linux에서는 ZIP CRC/내용/EXE 해시 검증을 모의 테스트.
3. 업비트·빗썸·통합형 CLI 숫자 메뉴 한국어화. 기존 EXE 검증용 영어 식별 문자열 보존.
4. 10,000개 수집 상한·10,003개 증분 저장·400개 저장 후 중단/9,600개 복구의 전량 중복 없는 결과를 로컬 모의 API로 확인.

## 증거
- Python 3.13.5 Linux `python -W error::ResourceWarning -m unittest discover -p 'test_*.py' -q`: **127 PASS / 0 FAIL**.
- `python -m compileall -q .`: PASS.
- 3개 Python 에디션 메뉴 출현 및 종료: PASS (EXE 아닌 소스).
- Windows EXE/PyInstaller 실빌드: NOT_RUN (Linux). 고객 ZIP 독립 EXE 실제 재실행: NOT_RUN (Windows 필요).
- 업비트/빗썸 실제 API: DNS name resolution 오류; 외부 런타임 데이터 수신 불가. 공식 API 문서의 파라미터만 대조.
- GitHub 전용 저장소: `hibi89/candle_scraper` (private), `main` 소스 커밋 `b9a1483a790c642704abd492493c50e038ad7344` 업로드/원격 검증 PASS. 후속 문서 커밋 후 최종 HEAD 재확인 필요. Vercel 비대상. 

## 다음 필수 검증
- Windows PC 새 폴더에서 `build_windows.bat` (PyInstaller 별도 설치 승인·준비 필요). 테스트/3 EXE/해시 검증/3 ZIP 생성/ZIP 독립 실행 5단계 모두 PASS.
- 해당 PC에서 먼저 메뉴 [5] 양 거래소 11개 봉 실 API 점검, 별도 새 DB에서 최초·증분·중단/이어받기 소량 E2E.
- 거래소별 데이터 이용정책과 판매용 설명 문구 최종 확인 후 RELEASE 판정.

## GitHub Windows CI 준비 (실행 미검증)
- `.github/workflows/windows-build.yml`: 수동 실행(`workflow_dispatch`)만 지원. Windows 2022·Python 3.11에서 PyInstaller→5단계 빌드·검증→비공개 Actions artifact 업로드를 계획. GitHub 저장소 연결과 소스 업로드는 완료. Windows workflow는 아직 실행하지 않았으므로 미검증.
- `build_windows.bat`: CI 환경에서 Python 명령 분리 및 `pause` 우회. 기존 사용자 Windows의 `py` 실행 경로 유지.
- 진행률은 85% 유지. CI 준비 코드는 실제 Windows 성공 이전에 추가 진척으로 산정하지 않음.

## GitHub 초기 백업 및 인수인계
- 사용자가 `hibi89/candle_scraper` 저장소를 생성하고 소스·개발 이력·인수인계 업로드를 지시함. 기존 저장소는 초기 점검 시 비공개·빈 `main` 상태였음.
- 가져오는 소스는 Library의 검증된 v1.6.1 ZIP 내용과 일치. CI 루트 워크플로 포함. 원본 ZIP·Windows EXE·고객 DB는 GitHub에 포함하지 않음.
- 원격 `main` SHA `b9a1483a790c642704abd492493c50e038ad7344` 확인, `HANDOFF.md`에 소스 기준 SHA 기록함. 후속 문서 커밋과 구분하며 현재 HEAD는 실시간 조회.
- 이번 초기 GitHub 보존 작업 자체는 전체 판매 완성률에 추가 반영하지 않음(**85% 추정, HOLD**).

## GitHub 반영 확인 (2026-11-05 21:12 KST)
- **소스 커밋:** `b9a1483a790c642704abd492493c50e038ad7344` (main) / 28개 소스·문서 파일 원격 확인. 인증 연결 `hibi89` Author/Committer 확인.
- **실행 검증:** 이 환경에서 Python offline unittest 127/127 PASS, compileall PASS, source manifest 파일 SHA256 27/27 MATCH.
- **미검증:** Windows EXE 실빌드와 고객 ZIP 독립 실행, Upbit/Bithumb 실제 HTTPS, GitHub Actions 수동 CI.
- **후속 문서 커밋:** HANDOFF/STATUS/SOURCE_MANIFEST 갱신만 포함. 코드는 `b9a1483a790c642704abd492493c50e038ad7344`와 동일.

## 범위 분리
- 이전 대화의 공통 패턴 검색 설계는 `docs/FUTURE_PATTERN_SEARCH.md`에 미래 계획으로만 기록. 실행 엔진/수식 해석은 미구현이며 현 85% 추정률에 포함하지 않음.
