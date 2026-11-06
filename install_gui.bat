@echo off
REM Installe les dependances de l interface graphique (PyQt6, google-genai...).
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo Creation de l environnement virtuel...
    python -m venv venv
    if errorlevel 1 ( echo Echec : Python 3.12+ est requis. & pause & exit /b 1 )
)
echo Installation des dependances...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements-gui.txt
if errorlevel 1 ( echo Echec de l installation. & pause & exit /b 1 )
echo.
echo Termine. Lancez Prosper_GUI.bat ou creez un raccourci avec create_shortcut.bat
pause
