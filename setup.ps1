$ErrorActionPreference = "Stop"

$target = Join-Path $HOME ".pi\agent"
node (Join-Path $PSScriptRoot "scripts\install-harness.mjs") $target
node (Join-Path $target "scripts\install-packages.mjs") (Join-Path $target "settings.json")
npm --prefix $target test

Write-Host "Setup complete. Restart Pi to load the current harness."
