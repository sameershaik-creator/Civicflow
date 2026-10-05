@echo off
setlocal
cd /d "%~dp0"

set PYTHON_CMD=python
if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0venv\Scripts\python.exe"
)

echo ========================================
echo    Running CivicFlow Phase 9 Tests
echo ========================================
echo Using interpreter: %PYTHON_CMD%

"%PYTHON_CMD%" -m pip install -q -r "%~dp0backend\requirements.txt"
"%PYTHON_CMD%" "%~dp0test_phase9.py"
endlocal
