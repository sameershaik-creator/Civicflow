# Convenience proxy to run Phase 2 tests from backend folder
$rootScript = Join-Path (Split-Path -Parent $PSScriptRoot) "run_tests_phase2.ps1"
& "$rootScript"
