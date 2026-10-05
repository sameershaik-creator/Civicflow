@echo off
echo ========================================
echo    Running CivicFlow Phase 2 Tests      
echo ========================================

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python test_phase2.py
