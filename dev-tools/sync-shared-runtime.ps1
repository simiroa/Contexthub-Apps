param(
    [string]$RepoRoot = "C:\Users\HG\Documents\Contexthub-Apps",
    [string]$HubRoot = "C:\Users\HG\Documents\Contexthub"
)

$ErrorActionPreference = "Stop"

$source = Join-Path $HubRoot "Runtimes\Shared"
$target = Join-Path $RepoRoot "dev-tools\runtime\Shared"

if (-not (Test-Path $source)) {
    throw "Source shared runtime not found: $source"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null

Write-Host "Syncing shared runtime"
Write-Host "Source: $source"
Write-Host "Target: $target"

robocopy $source $target /E /NFL /NDL /NJH /NJS /NP | Out-Null
$code = $LASTEXITCODE
if ($code -gt 7) {
    throw "robocopy failed with exit code $code"
}

Write-Host "Shared runtime synced."
