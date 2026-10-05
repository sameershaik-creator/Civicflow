# Convenience proxy to run tests from frontend folder
$rootScript = Join-Path (Split-Path -Parent $PSScriptRoot) "run_tests.ps1"
& "$rootScript"
