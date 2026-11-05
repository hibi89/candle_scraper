# 코인 캔들 수집기 — v1.6.1 (비공개 GitHub 소스 저장소)

**상태: 판매 보류(HOLD), 완성률 추정 94%.** Windows Server 2022 GitHub Actions에서 3종 EXE 빌드/실행 및 고객 ZIP 3종 독립 실행 3/3 PASS. 업비트·빗썸 각각 KRW-BTC 실 API 11봉·2페이지 및 임시 DB 소량 수집/증분/CSV PASS. **실제 고객 ZIP 3종의 EXE 내 메뉴 [5]도 업비트/빗썸 실 API 연결 PASS** (Windows Server 2022). 단, 소비자 Windows 10/11 실행·장기/전종목 수집·약관 검증은 남아 있습니다. GitHub 소스 ZIP 자체는 EXE가 아닙니다.

## 최신 고객 ZIP 검증 (2026-11-05 21:49 KST)

[Windows Actions run #42029964305](https://github.com/hibi89/candle_scraper/actions/runs/42029964305)에서 **3종 실제 고객 EXE 실행·실거래소 메뉴 [5]·ZIP 독립 실행 전부 PASS**. 정확한 실행 소스 SHA `40c0afe32e4eecda64ada9021aad35a8d1cd96fd`. 고객 ZIP 해시: 업비트 `6985a6ae9c8ed094161db16863af7ce3d52cbc60862c85325efb27649db7e314`, 빗썸 `5bd484fda1e6bfdd9be20527db4139bb958d2b7cdd3213c995df5dee390ae741`, 통합 `0e7ccc6850e67a36b2d6e71b6acc42611dd7ceb10026f8f51560f3737bb903f0`. CI 아티팩트 만료 2026-11-19. 일반 소비자 Windows10/11, 전체 종목 장시간 실수집, 시장정보 상용 이용약관 검토 전까지 **판매 HOLD**.

> **판매/라이선스 차단 (2026-11-05):** 업비트 Open API 현행 제6조 제3항은 해당 API 사용 프로그램의 유상 양도·배포·이용 허락을 제한합니다. 업비트 단독·통합 EXE는 별도 서면 허락 없이는 판매하지 않습니다. 빗썸 단독도 상용 배포 조건 확인 전 판매하지 않습니다. 상세 근거: [docs/COMMERCIAL_API_POLICY.md](docs/COMMERCIAL_API_POLICY.md). 기술 검증 성공과 판매 허용은 별개입니다.

## 주요 기능

- 업비트 / 빗썸 독립 SQLite (`upbit_candles.sqlite3`, `bithumb_candles.sqlite3`).
- 월봉 → 주봉 → 일봉 → 240 → 60 → 30 → 15 → 10 → 5 → 3 → 1분봉 순서. 원하는 시간봉만 다중 선택 가능.
- 종목·시간봉별 최초 최대 10,000개 **완료된** 캔들 수집. 이후 증분 갱신은 10,000개 초과 누적.
- 5개 종목 병렬 요청, 공유 요청 간격 제한, SQLite 중복 방지 및 중단 후 이어받기.
- 메뉴에서 최초 수집/이어받기, 증분 갱신, CSV 출력, 폴더 열기, 읽기 전용 API 점검, DB 현황 조회.
- **v1.4:** 빗썸 `to` KST 변환과 마켓 조회 `isDetails` 파라미터 적용. API 점검은 첫 페이지뿐 아니라 과거 페이지 탐색도 확인.

- **v1.5:** 검증된 캔들 날짜의 UTC/KST 일치 여부, 정확한 종목, 과거 페이지 정렬/중복, 잘못된 DB 스키마를 검사하며, 초기 DB 5개 작업 동시 생성 경쟁을 예방합니다.
- **v1.5:** 실제 Windows에서 EXE 3개 시작/종료 검증 시 SHA256 해시 매니페스트를 남기고, 검증된 EXE만 고객용 ZIP으로 제작합니다.
- **v1.6.1:** 기존 DB의 기본키·중복 방지 계약을 쓰기 전에 확인합니다. 컬럼 이름만 같은 오래된/외부 DB는 읽지 않고 그대로 보존합니다.
- **v1.6.1:** 고객용 ZIP 3종을 별도 임시 폴더에 해제해 각각 독립 실행·정상 종료 확인 후에만 빌드 성공으로 판정합니다.
- **v1.6.1:** 숫자 메뉴는 한국어로 표시합니다. 10,000개 최초 수집/이후 10,003개 누적/중단 후 9,600개 복구를 두 거래소 요청 형식의 로컬 시뮬레이터로 검증했습니다.

## Windows에서 개발용 실행

Python 3.11 이상이 설치된 Windows에서 `start.bat`을 실행하거나:

```bat
py entry_upbit.py
py entry_bithumb.py
py entry_both.py
```

거래소 API 키와 SQLite 별도 설치는 필요 없습니다. 프로그램의 DB 파일 저장 경로는 실행 파일/소스 폴더이며 **쓰기 가능한 폴더**에서 실행해야 합니다.

실행 중인 기존 `upbit_collect_fast.py`와 **같은 SQLite 파일에 동시 수집하지 마세요.** 기존 수집 완료 후 프로그램을 닫고 DB와 WAL 체크포인트/백업 상태를 확인한 다음 데이터를 이전하는 것이 안전합니다. 이 소스 ZIP은 기존 사용자 DB를 포함하거나 수정하지 않습니다.

## Windows EXE 빌드 및 검증 (Windows Server 2022 CI 통과, 일반 소비자 PC 미검증)

1. Windows 개발 PC에 Python 3.11+ 및 PyInstaller가 필요합니다. 설치가 필요한 경우 별도 승인·관리 하에 `py -m pip install pyinstaller` 사용.
2. `build_windows.bat` 실행: 자동 테스트 → EXE 3개 빌드 → 3개 EXE 시작·종료 점검 및 검증 해시 기록 → 상품별 ZIP 제작.
3. 빌드 5단계에서 `verify_customer_packages.py`가 3개 고객 ZIP을 각각 새 폴더에 풀어 EXE 재실행·정상 종료를 추가 검증합니다. 성공하면 `customer_packages/`에 3개 상품군 ZIP이 생성됩니다. 각 ZIP에는 선택한 EXE와 사용설명서만 들어갑니다.
4. 실제 Windows에서 읽기 전용 메뉴 `[5] API 점검` → **새 임시 폴더/새 DB**에서 소량 실수집·증분 갱신·CSV·재시작을 시험해야 합니다.
5. 사용자가 실제 사용하는 보안 설정/백신에서 실행 경고와 권한 오류를 확인하세요. 미서명 EXE는 보안 경고가 발생할 수 있습니다.

`build_windows.bat`은 PyInstaller를 자동 설치하지 않습니다. 검증에 실패하면 고객용 ZIP 제작을 진행하지 않습니다.

## 검증

```bat
py -m unittest discover -p "test_*.py" -q
py -m compileall -q .
```

Linux Python 3.13.5 테스트 환경에서 Python 단위·동시성·로컬 HTTP API·고객 ZIP 모의 검사·10,000개 대량 수집/복구 **127/127 PASS**. 로컬 HTTP 서버는 실제 urllib 통신을 사용하지만 **거래소 서버가 아닙니다**. 외부 HTTPS 연결은 테스트 환경의 DNS 제한으로 실패했으므로 실 API 성공은 미검증입니다.

공식 참조:
- 빗썸 캔들 `to` KST: https://apidocs.bithumb.com/reference/%EB%B6%84minute-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
- 빗썸 마켓 `isDetails`: https://apidocs.bithumb.com/reference/%EA%B1%B0%EB%9E%98-%EB%8C%80%EC%83%81-%EB%AA%A9%EB%A1%9D-%EC%A1%B0%ED%9A%8C
- 업비트 일봉 `to`: https://docs.upbit.com/kr/reference/list-candles-days

**상용화 전:** 거래소별 API 정책, 데이터 활용·재배포 조건, 실제 데이터 일치 여부를 별도로 확인해야 합니다. 수집된 시세는 투자 수익을 보장하지 않습니다.

## GitHub Windows CI 빌드 검증 (2026-11-05 완료)

비공개 `main`의 `.github/workflows/windows-build.yml`로 Windows Server 2022 / Python 3.11.9 / PyInstaller 6.16.0 실제 빌드를 완료했습니다. [성공 run #42027942187](https://github.com/hibi89/candle_scraper/actions/runs/42027942187)에서 내부 고객 ZIP 3종과 SHA256 증거를 내려받을 수 있습니다(14일 후 만료). 별도 [실 API run #42028865266](https://github.com/hibi89/candle_scraper/actions/runs/42028865266)도 통과했고, `live_api_probe.py`는 고객 데이터베이스와 무관한 일회성 임시 DB만 사용합니다. 두 실행의 정확한 SHA와 범위는 STATUS.md에 있습니다. **판매 HOLD 유지.**

## 프로젝트 관리 및 백업

- GitHub 단일 기준: `hibi89/candle_scraper` 비공개 `main` (소스·테스트·설정·문서만).
- 재개 전 `HANDOFF.md` → `STATUS.md` → `AGENTS.md` → `REQUIREMENTS.md` 순으로 읽고 실제 HEAD SHA 확인.
- 과거 버전별 원본 개발 ZIP은 ChatGPT Library 보존, 해시 및 경로는 `docs/ARCHIVE_PROVENANCE.md`.
- `docs/RELEASE_CHECKLIST.md`를 충족하기 전에는 판매 보류. CI는 수동 실행이며 비용과 상태 확인 없이 자동으로 돌리지 않습니다.
