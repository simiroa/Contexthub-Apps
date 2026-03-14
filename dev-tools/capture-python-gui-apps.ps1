param(
    [string]$RepoRoot = "C:\Users\HG\Documents\Contexthub-Apps",
    [string]$HubRoot = "C:\Users\HG\Documents\Contexthub",
    [string]$SharedRoot,
    [string]$OutputRoot = "Diagnostics\\gui_captures",
    [string[]]$Categories = @("image", "ai", "ai_light", "document", "utilities", "video"),
    [string[]]$OnlyApps = @(),
    [int]$WaitSeconds = 20,
    [int]$CooldownSeconds = 2,
    [string]$PythonExe = "python",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$appsRoot = $RepoRoot
$outputPath = Join-Path $RepoRoot $OutputRoot
$logPath = Join-Path $RepoRoot "Diagnostics\\gui_capture_log.md"
$runTmpRoot = Join-Path $RepoRoot "Diagnostics\\gui_runs"

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

if (-not (Test-Path $SharedRoot)) {
    throw "Shared runtime not found: $SharedRoot"
}

if ($Clean) {
    Remove-Item -Recurse -Force $outputPath -ErrorAction SilentlyContinue
    Remove-Item -Force $logPath -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $runTmpRoot -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
New-Item -ItemType Directory -Force -Path $runTmpRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Write-Log {
    param([string]$Message)
    Add-Content -Path $logPath -Value $Message
}

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win32Capture {
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT {
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
  }

  [DllImport("user32.dll")]
  public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

  [DllImport("user32.dll")]
  public static extern bool SetForegroundWindow(IntPtr hWnd);

  [DllImport("user32.dll")]
  public static extern bool IsWindowVisible(IntPtr hWnd);

  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

  [DllImport("user32.dll")]
  public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

  [DllImport("user32.dll")]
  public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

  [DllImport("user32.dll")]
  public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

  [DllImport("user32.dll")]
  public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);

  [DllImport("dwmapi.dll")]
  public static extern int DwmGetWindowAttribute(IntPtr hwnd, int dwAttribute, out RECT pvAttribute, int cbAttribute);

  public static bool TryGetWindowBounds(IntPtr hWnd, out RECT rect) {
    rect = new RECT();
    if (DwmGetWindowAttribute(hWnd, 9, out rect, Marshal.SizeOf(typeof(RECT))) == 0) {
      return true;
    }
    return GetWindowRect(hWnd, out rect);
  }

  public static IntPtr FindWindowForProcess(int pid) {
    IntPtr found = IntPtr.Zero;
    int bestArea = 0;
    EnumWindows((hWnd, lParam) => {
      uint windowPid;
      GetWindowThreadProcessId(hWnd, out windowPid);
      if (windowPid == pid && IsWindowVisible(hWnd)) {
        RECT rect;
        if (TryGetWindowBounds(hWnd, out rect)) {
          int width = rect.Right - rect.Left;
          int height = rect.Bottom - rect.Top;
          int area = width * height;
          if (width > 0 && height > 0 && area > bestArea) {
            bestArea = area;
            found = hWnd;
          }
        }
      }
      return true;
    }, IntPtr.Zero);
    return found;
  }
}
"@

function Wait-ForWindowHandle {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$TimeoutSeconds
    )

    function Get-DescendantPids {
        param([int]$RootPid)
        $all = New-Object System.Collections.Generic.HashSet[int]
        $queue = New-Object System.Collections.Generic.Queue[int]
        $queue.Enqueue($RootPid)
        [void]$all.Add($RootPid)
        while ($queue.Count -gt 0) {
            $currentPid = $queue.Dequeue()
            try {
                $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$currentPid" -ErrorAction SilentlyContinue
            } catch {
                $children = @()
            }
            foreach ($child in $children) {
                $cpid = [int]$child.ProcessId
                if ($all.Add($cpid)) {
                    $queue.Enqueue($cpid)
                }
            }
        }
        return $all
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) { return $null }
        $Process.Refresh()
        $pids = Get-DescendantPids -RootPid $Process.Id
        foreach ($candidatePid in $pids) {
            $handle = [Win32Capture]::FindWindowForProcess($candidatePid)
            if ($handle -and $handle -ne [IntPtr]::Zero) {
                return @{ Process = $Process; WindowPid = $candidatePid; Handle = $handle }
            }
        }
        Start-Sleep -Milliseconds 150
    }
    return $null
}

function Save-WindowScreenshot {
    param(
        [IntPtr]$Handle,
        [string]$Path
    )

    $rect = New-Object Win32Capture+RECT
    if (-not [Win32Capture]::TryGetWindowBounds($Handle, [ref]$rect)) {
        throw "Failed to get window bounds"
    }

    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    if ($width -le 0 -or $height -le 0) {
        throw "Invalid window bounds"
    }

    [Win32Capture]::ShowWindow($Handle, 9) | Out-Null
    [Win32Capture]::SetForegroundWindow($Handle) | Out-Null
    Start-Sleep -Milliseconds 250

    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $hdc = $graphics.GetHdc()
    try {
        $ok = [Win32Capture]::PrintWindow($Handle, $hdc, 0)
        if (-not $ok) {
            $graphics.ReleaseHdc($hdc)
            $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size($width, $height)))
        }
    }
    finally {
        try { $graphics.ReleaseHdc($hdc) } catch {}
        $graphics.Dispose()
    }

    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
}

function Get-AppsToTest {
    $results = @()
    foreach ($category in $Categories) {
        $catPath = Join-Path $appsRoot $category
        if (-not (Test-Path $catPath)) { continue }
        $manifests = Get-ChildItem -Path $catPath -Recurse -Filter manifest.json -File -ErrorAction SilentlyContinue
        foreach ($manifestFile in $manifests) {
            $appDir = Split-Path -Parent $manifestFile.FullName
            $appName = Split-Path -Leaf $appDir
            if ($OnlyApps.Count -gt 0 -and $OnlyApps -notcontains $appName -and $OnlyApps -notcontains "$category/$appName") {
                continue
            }
            $results += $manifestFile.FullName
        }
    }
    return $results
}

$manifests = Get-AppsToTest
foreach ($manifestPath in $manifests) {
    $proc = $null
    try {
        $manifest = Get-Content -Raw -Path $manifestPath | ConvertFrom-Json
        $appDir = Split-Path -Parent $manifestPath
        $appId = $manifest.id
        $category = $manifest.runtime.category

        if (-not $manifest.ui.enabled -or $manifest.execution.entry_point -notlike "*.py") {
            Write-Log "[$(Get-Date -Format s)] SKIP $category/$appId - not a python gui app"
            continue
        }

        $entryPath = Join-Path $appDir $manifest.execution.entry_point
        if (-not (Test-Path $entryPath)) {
            Write-Log "[$(Get-Date -Format s)] SKIP $category/$appId - missing entry point"
            continue
        }

        $stdoutDir = Join-Path $outputPath "logs"
        New-Item -ItemType Directory -Force -Path $stdoutDir | Out-Null
        $stdoutPath = Join-Path $stdoutDir "${category}_${appId}_stdout.log"
        $stderrPath = Join-Path $stdoutDir "${category}_${appId}_stderr.log"
        $tmpDir = Join-Path $runTmpRoot (Join-Path $category $appId)
        New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
        $imageDir = Join-Path $outputPath $category
        New-Item -ItemType Directory -Force -Path $imageDir | Out-Null
        $imagePath = Join-Path $imageDir "${appId}.png"

        $oldPythonPath = $env:PYTHONPATH
        $oldSharedRoot = $env:CTX_SHARED_ROOT
        $oldHeadless = $env:CTX_HEADLESS
        $oldCapture = $env:CTX_CAPTURE_MODE
        $oldOutput = $env:CTX_OUTPUT_ROOT
        $oldAppRoot = $env:CTX_APP_ROOT
        $oldTemp = $env:TEMP
        $oldTmp = $env:TMP

        $env:PYTHONPATH = $SharedRoot
        $env:CTX_SHARED_ROOT = (Join-Path $SharedRoot "contexthub")
        $env:CTX_HEADLESS = "1"
        $env:CTX_CAPTURE_MODE = "1"
        $env:CTX_OUTPUT_ROOT = $tmpDir
        $env:CTX_APP_ROOT = $appDir
        $env:TEMP = $tmpDir
        $env:TMP = $tmpDir

        $proc = Start-Process -FilePath $PythonExe -ArgumentList @($entryPath) -WorkingDirectory $appDir -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $windowInfo = Wait-ForWindowHandle -Process $proc -TimeoutSeconds $WaitSeconds

        if ($windowInfo) {
            Save-WindowScreenshot -Handle $windowInfo.Handle -Path $imagePath
            Write-Log "[$(Get-Date -Format s)] OK   $category/$appId -> $imagePath (window pid: $($windowInfo.WindowPid))"
        }
        else {
            Write-Log "[$(Get-Date -Format s)] WARN $category/$appId - no window detected within ${WaitSeconds}s"
        }
    }
    catch {
        Write-Log "[$(Get-Date -Format s)] FAIL $manifestPath - $($_.Exception.Message)"
    }
    finally {
        if ($CooldownSeconds -gt 0) {
            Start-Sleep -Seconds $CooldownSeconds
        }

        if ($proc) {
            try {
                $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($proc.Id)"
                foreach ($child in $children) {
                    Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
                }
            } catch {}
            if (-not $proc.HasExited) {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }

        $env:PYTHONPATH = $oldPythonPath
        $env:CTX_SHARED_ROOT = $oldSharedRoot
        $env:CTX_HEADLESS = $oldHeadless
        $env:CTX_CAPTURE_MODE = $oldCapture
        $env:CTX_OUTPUT_ROOT = $oldOutput
        $env:CTX_APP_ROOT = $oldAppRoot
        $env:TEMP = $oldTemp
        $env:TMP = $oldTmp
    }
}
