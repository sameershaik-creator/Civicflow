# Convenience proxy to run all tests from backend folder
$rootScript = Join-Path (Split-Path -Parent $PSScriptRoot) "run_tests.ps1"
& "$rootScript"
