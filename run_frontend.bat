@echo off
echo ========================================
echo    Starting CivicFlow Frontend Client   
echo ========================================

cd /d "%~dp0\frontend"

if not exist "node_modules" (
    echo [1/2] Installing frontend dependencies...
    call npm install
)

echo [2/2] Launching Vite development server...
echo Frontend running at http://localhost:5173
call npm run dev
