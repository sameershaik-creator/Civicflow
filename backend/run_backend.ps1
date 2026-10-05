# Convenience proxy to run backend launcher from backend folder
$rootScript = Join-Path (Split-Path -Parent $PSScriptRoot) "run_backend.ps1"
& "$rootScript"
