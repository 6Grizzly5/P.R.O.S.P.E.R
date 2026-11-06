@echo off
REM Lance P.R.O.S.P.E.R en mode terminal (CLI).
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" run_cli.py
) else (
    python run_cli.py
)
pause
