@echo off
echo ========================================
echo    Starting CivicFlow Backend Server    
echo ========================================

cd /d "%~dp0"

if not exist "venv" (
    echo [1/4] Creating Python virtual environment in .\venv...
    python -m venv venv
)

echo [2/4] Activating virtual environment and installing requirements...
call venv\Scripts\activate.bat
pip install -r backend\requirements.txt

cd backend
echo [3/4] Running database migrations (alembic upgrade head)...
alembic upgrade head

echo [4/4] Launching FastAPI backend server...
echo Server listening at http://127.0.0.1:8000
echo Health check at http://127.0.0.1:8000/health
echo Database check at http://127.0.0.1:8000/health/db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
