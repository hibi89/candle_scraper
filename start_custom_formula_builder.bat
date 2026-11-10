@echo off
setlocal
cd /d "%~dp0"
py -3 custom_formula_builder.py --interactive
if errorlevel 1 (
  echo.
  echo Formula builder stopped or Python 3.11+ unavailable.
)
pause
