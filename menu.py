# -*- coding: utf-8 -*-
"""Interactive console front end; allowed editions are set by entrypoint."""
import os
import sys
from collector import ROOT, UNITS, run, export_csv, smoke_check, inspect_database

LABELS = {'upbit': 'Upbit', 'bithumb': 'Bithumb'}
UNIT_LABELS = {'month': '월봉', 'week': '주봉', 'day': '일봉'}

def choose_exchange(allowed):
    allowed = tuple(allowed)
    if len(allowed) == 1:
        print(f'거래소: {LABELS[allowed[0]]}')
        return list(allowed)
    print('\n[1] 업비트  [2] 빗썸  [3] 통합  [0] 돌아가기')
    return {'1':['upbit'],'2':['bithumb'],'3':['upbit','bithumb']}.get(input('거래소 선택: ').strip(),[])

def choose_units():
    """Enter all, comma-separated indices, or 0 to cancel."""
    print('\n시간봉 선택 (월봉부터 순서대로 수집):')
    for i, unit in enumerate(UNITS, 1):
        print(f'  [{i:>2}] {UNIT_LABELS.get(unit, str(unit) + '분봉')}')
    print('  [A] 전체  [0] 돌아가기')
    raw = input('번호 여러 개(예: 1,2,4) 또는 A 입력: ').strip().lower()
    if raw in ('a', 'all'): return UNITS
    if raw == '0' or not raw: return ()
    try:
        indices = [int(x.strip()) for x in raw.split(',')]
        if not indices or any(i < 1 or i > len(UNITS) for i in indices): raise ValueError
        return tuple(unit for i, unit in enumerate(UNITS, 1) if i in indices)
    except ValueError:
        print('잘못된 시간봉 번호입니다.')
        return ()

def main(allowed=('upbit','bithumb')):
    allowed = tuple(allowed)
    if not allowed or any(e not in LABELS for e in allowed):
        raise ValueError('Invalid edition configuration')
    while True:
        print('\n' + '='*48)
        print('  COIN CANDLE COLLECTOR | 코인 캔들 수집기')
        print('  Edition: ' + ' + '.join(LABELS[e] for e in allowed))
        print('  [1] 최초 수집 / 중단 지점 이어받기')
        print('  [2] 신규 완료 캔들 증분 갱신')
        print('  [3] CSV 내보내기')
        print('  [4] 데이터 폴더 열기')
        print('  [5] 거래소 API 연결 점검 (읽기 전용)')
        print('  [6] 데이터베이스 저장 현황 조회')
        print('  [0] 종료')
        print('='*48)
        choice = input('메뉴 번호: ').strip()
        if choice == '0': return
        if choice == '4':
            if sys.platform == 'win32': os.startfile(str(ROOT))
            else: print(ROOT)
            continue
        if choice not in ('1','2','3','5','6'):
            print('잘못된 메뉴 번호입니다.')
            continue
        exchanges = choose_exchange(allowed)
        if not exchanges: continue
        units = choose_units() if choice in ('1','2') else ()
        if choice in ('1','2') and not units: continue
        for exchange in exchanges:
            try:
                if choice == '5':
                    smoke_check(exchange)
                elif choice == '6':
                    info = inspect_database(exchange)
                    if not info['exists']:
                        print(f'아직 DB가 없습니다: {info["path"]}')
                    else:
                        print(f'데이터베이스: {info["path"]}')
                        print(f'종목: {info["markets"]}개, 종목-봉 조합: {info["pairs"]}개, 캔들: {info["candles"]:,}개')
                elif choice == '3':
                    n,folder = export_csv(exchange)
                    print(f'CSV {n}개 내보내기 완료: {folder}')
                else:
                    run(exchange,'initial' if choice == '1' else 'update', units=units)
            except Exception as exc:
                print(f'오류 {exchange}: {type(exc).__name__}: {exc}')
        input('\n메뉴로 돌아가려면 Enter...')

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: print('\n사용자가 중단했습니다.')
