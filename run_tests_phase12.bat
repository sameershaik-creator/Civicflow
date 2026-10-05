@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON_EXE=venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo ========================================
echo    Running CivicFlow Phase 12 Tests     
echo ========================================
echo Using interpreter: %PYTHON_EXE%

"%PYTHON_EXE%" -m pip install -q -r backend\requirements.txt
"%PYTHON_EXE%" test_phase12.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Phase 12 tests failed with exit code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo [SUCCESS] Phase 12 tests completed successfully!
exit /b 0
