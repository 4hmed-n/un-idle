@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=src\un_idle;%PYTHONPATH%"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m main %*
) else (
    python -m main %*
)
endlocal
