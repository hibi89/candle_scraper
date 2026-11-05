# -*- coding: utf-8 -*-
"""Create edition-specific customer ZIPs *after* Windows EXE verification."""
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent
DIST=ROOT/'dist'
OUTPUT=ROOT/'customer_packages'
PRODUCTS={
  'upbit':'업비트',
  'bithumb':'빗썸',
  'both':'업비트 + 빗썸',
}


def guide(name):
    return f'''코인 캔들 수집기 | {name}\n\n1. ZIP 파일을 문서 폴더 같은 쓰기 가능한 위치에 압축 해제합니다.\n2. 함께 제공된 CoinCollector_*.exe를 더블클릭합니다.\n3. [5] API 연결 확인 → [1] 최초 데이터 수집 → 이후 [2] 최신 캔들 업데이트 순서로 실행합니다.\n4. [3] CSV 내보내기, [6] SQLite 저장 현황 확인을 사용할 수 있습니다.\n5. 시간봉은 전체(A) 또는 번호 여러 개(예: 1,4,11)를 선택합니다.\n6. SQLite DB는 EXE와 같은 폴더에 생성됩니다. 저장 폴더 쓰기 권한이 필요합니다.\n7. 최초 다운로드는 종목별/시간봉별 10,000개 이하의 완료된 캔들을 대상으로 하며,\n   거래 이력이 짧거나 빈 기간이 있는 경우 실제 개수는 적습니다.\n8. 중단 시 재실행 후 [1]을 선택하면 이미 저장한 캔들부터 이어갑니다.\n9. 동일한 데이터베이스에 수집기를 2개 동시에 실행하지 마세요.\n10. 데이터 복사·백업은 프로그램을 완전히 종료한 뒤 실시하세요.\n\n주의: 이 프로그램은 시장 데이터 조회 전용이며 자동매매 프로그램이 아닙니다.\n미서명 Windows 실행 파일은 보안 경고가 표시될 수 있습니다.\n'''


def verify_products():
    """Reject missing or changed EXEs, even if someone invokes packaging alone."""
    manifest_path = DIST / 'exe_verification.json'
    if not manifest_path.is_file():
        raise RuntimeError('No verified Windows EXE manifest; run verify_windows_exes.py first')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('platform') != 'Windows' or manifest.get('schema_version') != 1:
        raise RuntimeError('Invalid Windows EXE verification manifest')
    if set(manifest.get('products', {})) != set(PRODUCTS):
        raise RuntimeError('Windows EXE verification manifest is incomplete')
    paths = {k: DIST / f'CoinCollector_{k}.exe' for k in PRODUCTS}
    for edition, exe in paths.items():
        entry = manifest['products'][edition]
        if not exe.is_file() or entry.get('filename') != exe.name:
            raise RuntimeError(f'Windows EXE missing after verification: {exe.name}')
        if entry.get('size') != exe.stat().st_size or entry.get('sha256') != sha256(exe.read_bytes()).hexdigest():
            raise RuntimeError(f'Windows EXE changed since verification: {exe.name}')
    return paths


def main():
    paths = verify_products()
    OUTPUT.mkdir(exist_ok=True)
    for edition, exe in paths.items():
        destination=OUTPUT/f'CoinCollector_{edition}_customer.zip'
        with ZipFile(destination,'w',ZIP_DEFLATED,compresslevel=6) as z:
            z.write(exe,exe.name)
            z.writestr('사용설명서.txt', ('\ufeff'+guide(PRODUCTS[edition])).encode('utf-8'))
        print(f'PACKAGE {edition}: {destination.name} sha256={sha256(destination.read_bytes()).hexdigest()}')


if __name__=='__main__': main()
