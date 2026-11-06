@echo off
REM Lance P.R.O.S.P.E.R en mode graphique (sans fenetre de terminal).
cd /d "%~dp0"
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" "run_gui.pyw"
) else (
    where pythonw >nul 2>nul
    if errorlevel 1 (
        echo Python introuvable. Lancez d abord install_gui.bat
        pause
        exit /b 1
    )
    start "" pythonw "run_gui.pyw"
)
