@echo off
REM Cree un raccourci P.R.O.S.P.E.R sur le Bureau.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"
pause
