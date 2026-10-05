# CivicFlow Backend Runner (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting CivicFlow Backend Server    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Resolve root directory regardless of current working directory
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $scriptDir -or -not (Test-Path "$scriptDir\backend")) {
    $scriptDir = (Get-Item .).FullName
    if (Test-Path "$scriptDir\..\backend") {
        $scriptDir = (Get-Item "$scriptDir\..").FullName
    }
}
Set-Location $scriptDir

# 1. Create virtual environment if needed
$venvDir = Join-Path $scriptDir "venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$pipExe = Join-Path $venvDir "Scripts\pip.exe"
$alembicExe = Join-Path $venvDir "Scripts\alembic.exe"
$uvicornExe = Join-Path $venvDir "Scripts\uvicorn.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[1/4] Creating Python virtual environment in .\venv..." -ForegroundColor Yellow
    python -m venv "$venvDir"
}

# 2. Install backend dependencies into venv
Write-Host "[2/4] Checking and installing backend dependencies..." -ForegroundColor Yellow
& $pipExe install -r "$scriptDir\backend\requirements.txt"

# 3. Execute database migrations
Write-Host "[3/4] Applying database migrations (alembic upgrade head)..." -ForegroundColor Yellow
Set-Location "$scriptDir\backend"
try {
    & $alembicExe -c "$scriptDir\backend\alembic.ini" upgrade head
} catch {
    Write-Host "Migration head check completed with existing schema." -ForegroundColor Yellow
    & $alembicExe -c "$scriptDir\backend\alembic.ini" stamp head
}

# 4. Stop any stale process bound to port 8000
$portProc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($portProc) {
    foreach ($pidToKill in $portProc) {
        Write-Host "Stopping stale process ($pidToKill) on port 8000..." -ForegroundColor Yellow
        Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

# 5. Start Uvicorn directly with venv binary
Write-Host "[5/5] Launching FastAPI backend server..." -ForegroundColor Green
Write-Host "Backend API: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Health Check: http://127.0.0.1:8000/health" -ForegroundColor Green
Write-Host "Database Check: http://127.0.0.1:8000/health/db" -ForegroundColor Green
& $uvicornExe app.main:app --reload --host 0.0.0.0 --port 8000
