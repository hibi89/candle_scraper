@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%~dp0future_retouch_review.py" %*
) else (
  python "%~dp0future_retouch_review.py" %*
)
echo.
echo Check the output folder and report.html. Press any key to close.
pause >nul
