@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 or newer is required. No files were changed.
  exit /b 2
)
py -3 coin_report.py %*
exit /b %ERRORLEVEL%
