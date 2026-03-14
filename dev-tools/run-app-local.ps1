param(
    [Parameter(Mandatory = $true)]
    [string]$Category,

    [Parameter(Mandatory = $true)]
    [string]$App,

    [string]$TargetPath,

    [switch]$Headless,

    [string]$RepoRoot = "C:\Users\HG\Documents\Contexthub-Apps",

    [string]$HubRoot = "C:\Users\HG\Documents\Contexthub",

    [string]$SharedRoot,

    [string]$PythonExe = "python",

    [string]$OutputRoot
)

$ErrorActionPreference = "Stop"

$appRoot = Join-Path $RepoRoot $Category
$appDir = Join-Path $appRoot $App
$mainPy = Join-Path $appDir "main.py"
$localSharedRoot = Join-Path $RepoRoot "dev-tools\runtime\Shared"
$fallbackSharedRoot = Join-Path $HubRoot "Runtimes\Shared"

if (-not $SharedRoot) {
    if (Test-Path $localSharedRoot) {
        $SharedRoot = $localSharedRoot
    }
    else {
        $SharedRoot = $fallbackSharedRoot
    }
}

$sharedRoot = $SharedRoot
$sharedPackageRoot = Join-Path $sharedRoot "contexthub"

if (-not (Test-Path $mainPy)) {
    throw "App entry point not found: $mainPy"
}

if (-not (Test-Path $sharedRoot)) {
    throw "Shared runtime not found: $sharedRoot"
}

if (-not (Test-Path $sharedPackageRoot)) {
    throw "Shared contexthub package not found: $sharedPackageRoot"
}

$manifestPath = Join-Path $appDir "manifest.json"
if (-not (Test-Path $manifestPath)) {
    throw "manifest.json not found: $manifestPath"
}

$manifest = Get-Content $manifestPath | ConvertFrom-Json

$env:PYTHONPATH = $sharedRoot
$env:CTX_SHARED_ROOT = $sharedPackageRoot
$env:CTX_APP_ROOT = $appDir

if ($Headless) {
    $env:CTX_HEADLESS = "1"
} else {
    Remove-Item Env:CTX_HEADLESS -ErrorAction SilentlyContinue
}

if ($OutputRoot) {
    $env:CTX_OUTPUT_ROOT = $OutputRoot
} else {
    Remove-Item Env:CTX_OUTPUT_ROOT -ErrorAction SilentlyContinue
}

$args = @($mainPy)
if ($TargetPath) {
    $args += $TargetPath
}

Write-Host "Running $Category/$App"
Write-Host "Python: $PythonExe"
Write-Host "Shared runtime: $sharedRoot"
Write-Host "Mode: $($manifest.execution.mode)"
Write-Host "Headless: $($Headless.IsPresent)"
if ($TargetPath) {
    Write-Host "Target: $TargetPath"
}

& $PythonExe @args
$exitCode = $LASTEXITCODE
if ($null -ne $exitCode -and $exitCode -ne 0) {
    exit $exitCode
}
