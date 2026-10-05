@echo off
echo ========================================
echo   CivicFlow Comprehensive Test Suite    
echo ========================================

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo.
echo [1/3] Running Phase 1 Foundation Verification...
python test_phase1.py
if errorlevel 1 goto failed

echo.
echo [2/3] Running Phase 2 Database Schema & Migrations...
python test_phase2.py
if errorlevel 1 goto failed

echo.
echo [3/4] Running Phase 3 Authentication & RBAC Verification...
python test_phase3.py
if errorlevel 1 goto failed

echo.
echo [4/5] Running Phase 4 Citizen Intake & Media Upload Verification...
python test_phase4.py
if errorlevel 1 goto failed

echo.
echo [5/6] Running Phase 5 Gemini AI Multimodal Verification...
python test_phase5.py
if errorlevel 1 goto failed

echo.
echo [6/8] Running Phase 6 Geographic Verification & Maps...
python test_phase6.py
if errorlevel 1 goto failed

echo.
echo [7/8] Running Phase 7 AI Draft + Human Review Verification...
python test_phase7.py
if errorlevel 1 goto failed

echo.
echo [8/9] Running Phase 8 Citizen Final Submission Pipeline...
python test_phase8.py
if errorlevel 1 goto failed

echo.
echo [9/10] Running Phase 9 Municipal Administrator Adjudication...
python test_phase9.py
if errorlevel 1 goto failed

echo.
echo [10/11] Running Phase 10 Citizen In-App Notification Engine...
python test_phase10.py
if errorlevel 1 goto failed

echo.
echo [11/12] Running Phase 11 Security, Audit & Hardening Suite...
python test_phase11.py
if errorlevel 1 goto failed

echo.
echo [12/12] Running Phase 12 Final Product Readiness & Demo Suite...
python test_phase12.py
if errorlevel 1 goto failed

echo.
echo ========================================
echo ALL PHASE TESTS PASSED SUCCESSFULLY! (Phases 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
echo ========================================

exit /b 0


:failed
echo.
echo ========================================
echo TEST FAILURES DETECTED!
echo ========================================
exit /b 1
