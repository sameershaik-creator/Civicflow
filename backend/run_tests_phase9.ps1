# CivicFlow Phase 9 Test Runner (PowerShell) - Backend Directory Trampoline
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$rootDir = (Get-Item "$scriptDir\..").FullName

& "$rootDir\run_tests_phase9.ps1"
