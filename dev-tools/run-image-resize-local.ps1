param(
    [string]$TargetPath,
    [switch]$Headless,
    [string]$RepoRoot = "C:\Users\HG\Documents\Contexthub-Apps",
    [string]$HubRoot = "C:\Users\HG\Documents\Contexthub",
    [string]$PythonExe = "python"
)

$scriptPath = Join-Path $RepoRoot "dev-tools\run-app-local.ps1"

if (-not (Test-Path $scriptPath)) {
    throw "Missing launcher: $scriptPath"
}

$params = @{
    Category = "image"
    App = "image_resizer"
    RepoRoot = $RepoRoot
    HubRoot = $HubRoot
    PythonExe = $PythonExe
}

if ($TargetPath) {
    $params.TargetPath = $TargetPath
}

if ($Headless) {
    $params.Headless = $true
}

& $scriptPath @params
