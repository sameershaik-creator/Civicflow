# CivicFlow Phase 12 Backend Trampoline (PowerShell)
$ErrorActionPreference = "Stop"
$rootDir = (Get-Item "$PSScriptRoot\..").FullName
Set-Location $rootDir
& "$rootDir\run_tests_phase12.ps1"
