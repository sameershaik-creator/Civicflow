# CivicFlow Phase 8 Test Runner (PowerShell)
$ErrorActionPreference = "Stop"

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $scriptDir -or -not (Test-Path "$scriptDir\test_phase8.py")) {
    $scriptDir = (Get-Item .).FullName
    if (Test-Path "$scriptDir\..\test_phase8.py") {
        $scriptDir = (Get-Item "$scriptDir\..").FullName
    }
}
Set-Location $scriptDir

$venvPython = Join-Path $scriptDir "venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Running CivicFlow Phase 8 Tests      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Using interpreter: $pythonExe" -ForegroundColor Cyan

& $pythonExe -m pip install -q -r "$scriptDir\backend\requirements.txt"
& $pythonExe "$scriptDir\test_phase8.py"
