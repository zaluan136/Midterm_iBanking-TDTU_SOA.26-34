@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_demo.py %*
    exit /b
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3 run_demo.py %*
    exit /b
)
python run_demo.py %*
