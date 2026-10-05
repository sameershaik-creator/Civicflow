# CivicFlow Frontend Runner (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting CivicFlow Frontend Client   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Resolve project root and frontend directories reliably
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $scriptDir -or -not (Test-Path "$scriptDir\frontend")) {
    $scriptDir = (Get-Item .).FullName
    if (Test-Path "$scriptDir\..\frontend") {
        $scriptDir = (Get-Item "$scriptDir\..").FullName
    }
}
$feDir = Join-Path $scriptDir "frontend"
Set-Location $feDir

if (-not (Test-Path "$feDir\node_modules")) {
    Write-Host "[1/2] Installing frontend dependencies (npm install)..." -ForegroundColor Yellow
    npm install
}

Write-Host "[2/2] Launching Vite development server..." -ForegroundColor Green
Write-Host "Frontend running at http://localhost:5173" -ForegroundColor Green
npm run dev
