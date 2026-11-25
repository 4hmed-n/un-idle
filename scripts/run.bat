@echo off
setlocal
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m un_idle.main %*
) else (
    python -m un_idle.main %*
)
endlocal
