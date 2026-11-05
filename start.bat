@echo off
chcp 65001 >nul
cd /d "%~dp0"
py menu.py
if errorlevel 1 pause
