param(
    [string]$RepoRoot = "C:\Users\HG\Documents\Contexthub-Apps",
    [string]$HubRoot = "C:\Users\HG\Documents\Contexthub",
    [switch]$SkipBackup
)

$ErrorActionPreference = "Stop"

$source = Join-Path $RepoRoot "dev-tools\Runtimes\Shared"
$target = Join-Path $HubRoot "Runtimes\Shared"

if (-not (Test-Path $source)) {
    throw "Source shared runtime not found: $source"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null

if (-not $SkipBackup -and (Test-Path $target)) {
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $backup = Join-Path $HubRoot "Runtimes\Shared_backup_$timestamp"
    Write-Host "Creating backup: $backup"
    Copy-Item -LiteralPath $target -Destination $backup -Recurse -Force
}

Write-Host "Syncing shared runtime"
Write-Host "Source: $source"
Write-Host "Target: $target"

robocopy $source $target /MIR /XD __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
$code = $LASTEXITCODE
if ($code -gt 7) {
    throw "robocopy failed with exit code $code"
}

Write-Host "Shared runtime mirrored."
