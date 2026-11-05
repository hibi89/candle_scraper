# STATUS — Coin Candle Collector v1.6.1 (commercial Windows editions)

최신 확인: **2026-11-05 21:49 KST**

## 판정
- **추가 통합 검증:** Windows 고객 EXE 3종에서 실제 업비트·빗썸 공개 API 메뉴 실행까지 통과. 세부 검증 SHA와 최신 ZIP 해시 및 아티팩트는 바로 아래 최신 추가 검증 기록 참조.
- **판매 완성률 추정 94%** (이전 85% → **+9%p**). 이는 기능·빌드·실 API 게이트 진척을 반영한 보수적 프로젝트 추정치이며 테스트 커버리지 수치가 아니다.
- **RELEASE HOLD 유지.** Windows Server 2022 CI와 두 거래소 소량 실 API 검증은 통과했지만, 고객용 Windows 10/11 PC 직접 실행·장기/전종목 대용량 실수집·API 이용약관 최종 검토는 미검증이다.
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
