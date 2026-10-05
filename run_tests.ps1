# CivicFlow Master Test Runner (PowerShell)
$ErrorActionPreference = "Continue"

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $scriptDir -or -not (Test-Path "$scriptDir\test_phase1.py")) {
    $scriptDir = (Get-Item .).FullName
    if (Test-Path "$scriptDir\..\test_phase1.py") {
        $scriptDir = (Get-Item "$scriptDir\..").FullName
    }
}
Set-Location $scriptDir

$venvPython = Join-Path $scriptDir "venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   CivicFlow Comprehensive Test Suite   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Using interpreter: $pythonExe`n" -ForegroundColor Cyan

Write-Host ">>> Ensuring runtime uploads directory is pristine (zero test residual)..." -ForegroundColor Gray
if (Test-Path "$scriptDir\tests\clean_uploads.py") {
    & $pythonExe "$scriptDir\tests\clean_uploads.py" | Out-Null
}

Write-Host ">>> Running Phase 1 Foundation Verification..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase1.py"
$p1Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 2 Database Schema & Migrations..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase2.py"
$p2Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 3 Authentication & RBAC Verification..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase3.py"
$p3Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 4 Citizen Intake & Media Upload Verification..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase4.py"
$p4Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 5 Gemini AI Multimodal Verification..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase5.py"
$p5Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 6 Geographic Verification & Maps..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase6.py"
$p6Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 7 AI Draft + Human Review Verification..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase7.py"
$p7Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 8 Citizen Final Submission Pipeline..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase8.py"
$p8Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 9 Municipal Administrator Adjudication..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase9.py"
$p9Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 10 Citizen In-App Notification Engine..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase10.py"
$p10Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 11 Security, Audit & Hardening Suite..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase11.py"
$p11Exit = $LASTEXITCODE

Write-Host "`n>>> Running Phase 12 Final Product Readiness & Demo Suite..." -ForegroundColor Yellow
& $pythonExe "$scriptDir\test_phase12.py"
$p12Exit = $LASTEXITCODE

Write-Host "`n========================================" -ForegroundColor Cyan
if (Test-Path "$scriptDir\tests\clean_uploads.py") {
    & $pythonExe "$scriptDir\tests\clean_uploads.py" | Out-Null
}
if ($p1Exit -eq 0 -and $p2Exit -eq 0 -and $p3Exit -eq 0 -and $p4Exit -eq 0 -and $p5Exit -eq 0 -and $p6Exit -eq 0 -and $p7Exit -eq 0 -and $p8Exit -eq 0 -and $p9Exit -eq 0 -and $p10Exit -eq 0 -and $p11Exit -eq 0 -and $p12Exit -eq 0) {
    Write-Host "ALL PHASE TESTS PASSED SUCCESSFULLY! (Phases 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, and 12)" -ForegroundColor Green
    exit 0
} else {
    Write-Host "TEST FAILURES DETECTED (P1: $p1Exit, P2: $p2Exit, P3: $p3Exit, P4: $p4Exit, P5: $p5Exit, P6: $p6Exit, P7: $p7Exit, P8: $p8Exit, P9: $p9Exit, P10: $p10Exit, P11: $p11Exit, P12: $p12Exit)" -ForegroundColor Red
    exit 1
}


