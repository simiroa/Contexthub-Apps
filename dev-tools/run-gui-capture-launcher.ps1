param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $PSScriptRoot "gui_capture_launcher.py"

if (-not (Test-Path $scriptPath)) {
    throw "GUI launcher not found: $scriptPath"
}

function Test-PythonHasPySide6 {
    param([string]$Exe)

    if ([string]::IsNullOrWhiteSpace($Exe)) {
        return $false
    }

    try {
        & $Exe -c "import PySide6" *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $candidates = @(
        "python",
        "C:\Users\HG\Documents\HG_context_v2\ContextUp\tools\python\python.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-PythonHasPySide6 -Exe $candidate) {
            $PythonExe = $candidate
            break
        }
    }
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    throw "No Python interpreter with PySide6 was found."
}

Write-Host "Using Python: $PythonExe"
& $PythonExe $scriptPath
