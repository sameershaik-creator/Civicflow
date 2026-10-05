# Convenience proxy to run backend from frontend folder
$rootScript = Join-Path (Split-Path -Parent $PSScriptRoot) "run_backend.ps1"
& "$rootScript"
