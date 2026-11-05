@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Dual Bollinger Pattern Scanner - Read Only
set "DB=E:\업비트 캔들긁어오기\upbit_candles.sqlite3"
echo [DUAL BB SCANNER] 20,2 Close lower + 4,4 Open lower - ^> 20 lower recovery
echo Database: %DB%
echo The source SQLite will be opened READ ONLY. No result.csv is required.
echo.
if not exist "%DB%" (
  echo Default DB not found. Enter full path to your candle SQLite:
  set /p "DB=DB path: "
)
if not exist "%DB%" (
  echo ERROR: SQLite DB path not found.
  pause
  exit /b 2
)
py -3 --version >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0dual_bollinger_scanner.py" --db "%DB%" --output-dir "%~dp0" --markets all --units all
) else (
  python "%~dp0dual_bollinger_scanner.py" --db "%DB%" --output-dir "%~dp0" --markets all --units all
)
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" echo ERROR: Exit status %EXIT_CODE%
echo Press any key to exit. Results in dual_bb_results_YYYYMMDD_HHMMSS.
pause >nul
exit /b %EXIT_CODE%
