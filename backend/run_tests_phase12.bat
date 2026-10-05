@echo off
setlocal
cd /d "%~dp0\.."
call run_tests_phase12.bat
exit /b %ERRORLEVEL%
