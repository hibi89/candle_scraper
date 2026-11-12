@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_RUN=py"
if defined CI set "PYTHON_RUN=python"
echo [1/6] Running offline tests...
%PYTHON_RUN% -m unittest discover -p "test_*.py" -q
if errorlevel 1 goto fail
%PYTHON_RUN% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo PyInstaller missing. Install it manually first: py -m pip install pyinstaller
  goto fail
)
echo [2/6] Building Windows executables...
for %%E in (upbit bithumb both) do (
  %PYTHON_RUN% -m PyInstaller --noconfirm --clean --onefile --console --name CoinCollector_%%E --distpath dist --workpath build --specpath build entry_%%E.py
  if errorlevel 1 goto fail
)
echo [3/6] Checking executable startup and exit...
%PYTHON_RUN% verify_windows_exes.py
if errorlevel 1 goto fail
echo [4/6] Preparing edition-specific customer ZIPs...
%PYTHON_RUN% make_customer_packages.py
if errorlevel 1 goto fail
echo [5/6] Executing EXEs from independent customer ZIP extracts...
%PYTHON_RUN% verify_customer_packages.py
if errorlevel 1 goto fail
echo [6/6] Read-only audit of ZIP byte integrity and unchanged Korean guide...
%PYTHON_RUN% audit_customer_packages.py
if errorlevel 1 goto fail
echo PASS candidate only. Do not distribute without exchange licenses and owner release approval.
if not defined CI pause
exit /b 0
:fail
echo FAILED. Do not distribute this build.
if not defined CI pause
exit /b 1
