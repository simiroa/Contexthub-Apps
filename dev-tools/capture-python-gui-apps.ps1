param(
    [string]$RepoRoot = "",
    [string]$HubRoot = "",
    [string]$SharedRoot,
    [string]$OutputRoot = "Diagnostics\\gui_captures",
    [string]$CaptureFixturesRoot = "Diagnostics\\generated\\gui_capture_inputs",
    [string[]]$Categories = @("3d", "ai", "ai_lite", "audio", "comfyui", "document", "image", "native", "utilities", "video"),
    [string[]]$OnlyApps = @(),
    [int]$WaitSeconds = 20,
    [int]$CooldownSeconds = 2,
    [int]$PaintWaitMilliseconds = 1200,
    [string]$PythonExe = "python",
    [switch]$DryRun,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
if (-not $HubRoot) {
    $repoParent = Split-Path -Parent $RepoRoot
    $candidateHubRoot = Join-Path $repoParent "Contexthub"
    if (Test-Path $candidateHubRoot) {
        $HubRoot = $candidateHubRoot
    }
}

$appsRoot = $RepoRoot
$outputPath = Join-Path $RepoRoot $OutputRoot
$fixturesPath = Join-Path $RepoRoot $CaptureFixturesRoot
$logPath = Join-Path $RepoRoot "Diagnostics\\gui_capture_log.md"
$runTmpRoot = Join-Path $RepoRoot "Diagnostics\\gui_runs"

$localSharedRoot = Join-Path $RepoRoot "dev-tools\runtime\Shared"
$fallbackSharedRoot = $null
if ($HubRoot) {
    $fallbackSharedRoot = Join-Path $HubRoot "Runtimes\Shared"
}
if (-not $SharedRoot) {
    if (Test-Path -LiteralPath $localSharedRoot) {
        $SharedRoot = $localSharedRoot
    }
    elseif ($fallbackSharedRoot -and (Test-Path -LiteralPath $fallbackSharedRoot)) {
        $SharedRoot = $fallbackSharedRoot
    }
}

if ([string]::IsNullOrWhiteSpace($SharedRoot) -or -not (Test-Path -LiteralPath $SharedRoot)) {
    throw "Shared runtime not found: $SharedRoot"
}

if ($Clean) {
    Remove-Item -Recurse -Force $outputPath -ErrorAction SilentlyContinue
    Remove-Item -Force $logPath -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $runTmpRoot -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
New-Item -ItemType Directory -Force -Path $fixturesPath | Out-Null
New-Item -ItemType Directory -Force -Path $runTmpRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null

# Default behavior keeps existing captures and overwrites files by app.
# When running full-category capture (OnlyApps omitted), clear only those category artifacts.
if ((-not $Clean) -and $OnlyApps.Count -eq 0) {
    $stdoutDir = Join-Path $outputPath "logs"
    foreach ($category in $Categories) {
        $categoryCaptureDir = Join-Path $outputPath $category
        Remove-Item -Recurse -Force $categoryCaptureDir -ErrorAction SilentlyContinue

        if (Test-Path $stdoutDir) {
            Get-ChildItem -Path $stdoutDir -Filter "${category}_*.log" -File -ErrorAction SilentlyContinue |
                Remove-Item -Force -ErrorAction SilentlyContinue
        }

        $categoryRunDir = Join-Path $runTmpRoot $category
        Remove-Item -Recurse -Force $categoryRunDir -ErrorAction SilentlyContinue
    }
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Write-Log {
    param([string]$Message)
    Add-Content -Path $logPath -Value $Message
}

function Get-UiFramework {
    param([object]$Manifest)

    try {
        if ($Manifest.ui -and $Manifest.ui.framework) {
            return [string]$Manifest.ui.framework
        }
    }
    catch {
    }

    return ""
}

function Get-UiTemplate {
    param([object]$Manifest)

    try {
        if ($Manifest.ui -and $Manifest.ui.template) {
            return [string]$Manifest.ui.template
        }
    }
    catch {
    }

    return ""
}

function Test-QtFramework {
    param([string]$Framework)

    if ([string]::IsNullOrWhiteSpace($Framework)) {
        return $false
    }

    $normalized = $Framework.Trim().ToLowerInvariant()
    return @("qt", "pyside6") -contains $normalized
}

function Resolve-UiTemplate {
    param(
        [object]$Manifest,
        [string]$Framework
    )

    $template = Get-UiTemplate -Manifest $Manifest
    if (-not [string]::IsNullOrWhiteSpace($template)) {
        return $template.Trim().ToLowerInvariant()
    }

    if (Test-QtFramework -Framework $Framework) {
        return "full"
    }

    return "unknown"
}

function Resolve-PythonForCategory {
    param([string]$Category)

    $envCategory = switch ($Category) {
        "ai_lite" { "ai_light" }
        "3d" { "ai" }
        default { $Category }
    }

    $categoryPython = Join-Path $HubRoot "Runtimes\Envs\$envCategory\Scripts\python.exe"
    if (Test-Path $categoryPython) {
        return $categoryPython
    }
    return $PythonExe
}

function Test-PythonImport {
    param(
        [string]$PythonPath,
        [string]$ModuleName
    )

    try {
        & $PythonPath -c "import $ModuleName" *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Resolve-PythonForManifest {
    param(
        [string]$Category,
        $Manifest
    )

    $candidate = Resolve-PythonForCategory -Category $Category
    $framework = ""
    try {
        $framework = [string]$Manifest.ui.framework
    }
    catch {
        $framework = ""
    }

    if ($framework -eq "qt") {
        if (Test-PythonImport -PythonPath $candidate -ModuleName "PySide6") {
            return $candidate
        }
        if (Test-PythonImport -PythonPath $PythonExe -ModuleName "PySide6") {
            return $PythonExe
        }
    }

    return $candidate
}

function Ensure-SampleVideoInput {
    param([string]$OutputPath)

    if (Test-Path $OutputPath) {
        return $OutputPath
    }

    $outputDir = Split-Path -Parent $OutputPath
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $ffmpegCmd = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if (-not $ffmpegCmd) {
        return $null
    }

    & $ffmpegCmd.Source -y -f lavfi -i "testsrc2=size=1280x720:rate=24" -f lavfi -i "sine=frequency=440:sample_rate=48000" -t 3 -c:v libx264 -pix_fmt yuv420p -c:a aac $OutputPath | Out-Null
    if (Test-Path $OutputPath) {
        return $OutputPath
    }
    return $null
}

function Ensure-SampleAudioInput {
    param([string]$OutputPath)

    if (Test-Path $OutputPath) {
        return $OutputPath
    }

    $outputDir = Split-Path -Parent $OutputPath
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $ffmpegCmd = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if (-not $ffmpegCmd) {
        return $null
    }

    & $ffmpegCmd.Source -y -f lavfi -i "sine=frequency=440:sample_rate=48000:duration=3" -c:a pcm_s16le $OutputPath | Out-Null
    if (Test-Path $OutputPath) {
        return $OutputPath
    }
    return $null
}

function Resolve-CaptureTargets {
    param(
        [string]$Category,
        [string]$AppId
    )

    $key = "$Category/$AppId"
    switch ($key) {
        "video/video_convert" {
            $sample = Ensure-SampleVideoInput -OutputPath (Join-Path $fixturesPath "video_convert_sample.mp4")
            if ($sample) {
                return @($sample)
            }
        }
        "video/remove_audio" {
            $sample = Ensure-SampleVideoInput -OutputPath (Join-Path $fixturesPath "remove_audio_sample.mp4")
            if ($sample) {
                return @($sample)
            }
        }
        "audio/normalize_volume" {
            $sample = Ensure-SampleAudioInput -OutputPath (Join-Path $fixturesPath "normalize_volume_sample.wav")
            if ($sample) {
                return @($sample)
            }
        }
    }
    return @()
}

function Get-LogExcerpt {
    param(
        [string]$Path,
        [int]$Tail = 20
    )

    if (-not (Test-Path $Path)) {
        return ""
    }

    try {
        $lines = Get-Content -Path $Path -Tail $Tail -ErrorAction SilentlyContinue
        return ($lines -join " | ")
    }
    catch {
        return ""
    }
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

  [StructLayout(LayoutKind.Sequential)]
  public struct POINT {
    public int X;
    public int Y;
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

  [DllImport("user32.dll", CharSet = CharSet.Unicode)]
  public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);

  [DllImport("user32.dll", CharSet = CharSet.Unicode)]
  public static extern int GetClassName(IntPtr hWnd, System.Text.StringBuilder text, int count);

  [DllImport("user32.dll")]
  public static extern bool GetClientRect(IntPtr hWnd, out RECT rect);

  [DllImport("user32.dll")]
  public static extern bool ClientToScreen(IntPtr hWnd, ref POINT point);

  [DllImport("user32.dll")]
  public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);

  [DllImport("user32.dll", SetLastError = true)]
  public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

  public static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
  public static readonly IntPtr HWND_NOTOPMOST = new IntPtr(-2);
  public const uint SWP_NOMOVE = 0x0002;
  public const uint SWP_NOSIZE = 0x0001;
  public const uint SWP_NOACTIVATE = 0x0010;

  [DllImport("dwmapi.dll")]
  public static extern int DwmGetWindowAttribute(IntPtr hwnd, int dwAttribute, out RECT pvAttribute, int cbAttribute);

  public static bool TryGetWindowBounds(IntPtr hWnd, out RECT rect) {
    rect = new RECT();
    if (DwmGetWindowAttribute(hWnd, 9, out rect, Marshal.SizeOf(typeof(RECT))) == 0) {
      return true;
    }
    return GetWindowRect(hWnd, out rect);
  }

  public static bool TryGetClientBounds(IntPtr hWnd, out RECT rect) {
    rect = new RECT();
    RECT clientRect;
    if (!GetClientRect(hWnd, out clientRect)) {
      return false;
    }
    POINT topLeft = new POINT { X = clientRect.Left, Y = clientRect.Top };
    POINT bottomRight = new POINT { X = clientRect.Right, Y = clientRect.Bottom };
    if (!ClientToScreen(hWnd, ref topLeft) || !ClientToScreen(hWnd, ref bottomRight)) {
      return false;
    }
    rect.Left = topLeft.X;
    rect.Top = topLeft.Y;
    rect.Right = bottomRight.X;
    rect.Bottom = bottomRight.Y;
    return true;
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

  public static string GetWindowTitle(IntPtr hWnd) {
    var sb = new System.Text.StringBuilder(512);
    GetWindowText(hWnd, sb, sb.Capacity);
    return sb.ToString();
  }

  public static string GetWindowClass(IntPtr hWnd) {
    var sb = new System.Text.StringBuilder(256);
    GetClassName(hWnd, sb, sb.Capacity);
    return sb.ToString();
  }
}
"@

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

function Wait-ForWindowHandle {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$TimeoutSeconds
    )

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

    [Win32Capture]::ShowWindow($Handle, 9) | Out-Null
    [Win32Capture]::SetForegroundWindow($Handle) | Out-Null
    Start-Sleep -Milliseconds 250

    [Win32Capture]::SetWindowPos($Handle, [Win32Capture]::HWND_TOPMOST, 0, 0, 0, 0, [Win32Capture]::SWP_NOMOVE -bor [Win32Capture]::SWP_NOSIZE) | Out-Null
    Start-Sleep -Milliseconds 120

    # Measure after restore/foreground so stale bounds don't produce shifted crops.
    $windowRect = New-Object Win32Capture+RECT
    if (-not [Win32Capture]::TryGetWindowBounds($Handle, [ref]$windowRect)) {
        throw "Failed to get window bounds"
    }
    $clientRect = New-Object Win32Capture+RECT
    $hasClient = [Win32Capture]::TryGetClientBounds($Handle, [ref]$clientRect)

    $windowWidth = $windowRect.Right - $windowRect.Left
    $windowHeight = $windowRect.Bottom - $windowRect.Top
    if ($windowWidth -le 0 -or $windowHeight -le 0) {
        throw "Invalid window frame bounds"
    }

    $captureLeft = $windowRect.Left
    $captureTop = $windowRect.Top
    $captureWidth = $windowWidth
    $captureHeight = $windowHeight

    if ($hasClient) {
        $clientWidth = $clientRect.Right - $clientRect.Left
        $clientHeight = $clientRect.Bottom - $clientRect.Top
        $clientInsideWindow =
            $clientRect.Left -ge $windowRect.Left -and
            $clientRect.Top -ge $windowRect.Top -and
            $clientRect.Right -le $windowRect.Right -and
            $clientRect.Bottom -le $windowRect.Bottom
        $clientLooksReasonable =
            $clientWidth -gt 0 -and
            $clientHeight -gt 0 -and
            $clientWidth -ge [Math]::Floor($windowWidth * 0.5) -and
            $clientHeight -ge [Math]::Floor($windowHeight * 0.5)
        if ($clientInsideWindow -and $clientLooksReasonable) {
            $captureLeft = $clientRect.Left
            $captureTop = $clientRect.Top
            $captureWidth = $clientWidth
            $captureHeight = $clientHeight
        }
    }

    # Clamp to virtual desktop to avoid invalid CopyFromScreen coordinates on multi-monitor setups.
    $virtual = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $left = [Math]::Max($captureLeft, $virtual.Left)
    $top = [Math]::Max($captureTop, $virtual.Top)
    $right = [Math]::Min($captureLeft + $captureWidth, $virtual.Right)
    $bottom = [Math]::Min($captureTop + $captureHeight, $virtual.Bottom)
    $width = $right - $left
    $height = $bottom - $top
    if ($width -le 0 -or $height -le 0) {
        throw "Invalid capture region after screen clamp"
    }

    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($left, $top, 0, 0, (New-Object System.Drawing.Size($width, $height)))
    }
    finally {
        $graphics.Dispose()
        [Win32Capture]::SetWindowPos($Handle, [Win32Capture]::HWND_NOTOPMOST, 0, 0, 0, 0, [Win32Capture]::SWP_NOMOVE -bor [Win32Capture]::SWP_NOSIZE -bor [Win32Capture]::SWP_NOACTIVATE) | Out-Null
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
$summaryGui = 0
$summaryQt = 0
$summaryNonQt = 0
$summaryDryRun = 0
foreach ($manifestPath in $manifests) {
    $proc = $null
    try {
        $manifest = Get-Content -Raw -Path $manifestPath | ConvertFrom-Json
        $appDir = Split-Path -Parent $manifestPath
        $appId = $manifest.id
        $category = $manifest.runtime.category
        $framework = Get-UiFramework -Manifest $manifest
        $isQtFramework = Test-QtFramework -Framework $framework
        $template = Resolve-UiTemplate -Manifest $manifest -Framework $framework

        if (-not $manifest.ui.enabled -or $manifest.execution.entry_point -notlike "*.py") {
            Write-Log "[$(Get-Date -Format s)] SKIP $category/$appId - not a python gui app"
            continue
        }

        $summaryGui++
        if ($isQtFramework) {
            $summaryQt++
        }
        else {
            $summaryNonQt++
        }

        $entryPath = Join-Path $appDir $manifest.execution.entry_point
        if (-not (Test-Path $entryPath)) {
            Write-Log "[$(Get-Date -Format s)] SKIP $category/$appId - missing entry point"
            continue
        }

        if ($DryRun) {
            $summaryDryRun++
            $dryRunLine = "[$(Get-Date -Format s)] DRYRUN $category/$appId | framework=$framework | qt_like=$isQtFramework | template=$template | entry=$entryPath | app_dir=$appDir"
            Write-Log $dryRunLine
            Write-Host $dryRunLine
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
        $captureTargets = Resolve-CaptureTargets -Category $category -AppId $appId
        if ($null -eq $captureTargets) {
            $captureTargets = @()
        }

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

        $resolvedPythonExe = Resolve-PythonForManifest -Category $category -Manifest $manifest
        $argumentList = @($entryPath) + $captureTargets
        Write-Log "[$(Get-Date -Format s)] START $category/$appId | python=$resolvedPythonExe | template=$template | entry=$entryPath | targets=$([string]::Join(';', @($captureTargets))) | stdout=$stdoutPath | stderr=$stderrPath | temp=$tmpDir"
        $proc = Start-Process -FilePath $resolvedPythonExe -ArgumentList $argumentList -WorkingDirectory $appDir -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $windowInfo = Wait-ForWindowHandle -Process $proc -TimeoutSeconds $WaitSeconds

        if ($windowInfo) {
            Start-Sleep -Milliseconds $PaintWaitMilliseconds
            $windowRect = New-Object Win32Capture+RECT
            [Win32Capture]::TryGetWindowBounds($windowInfo.Handle, [ref]$windowRect) | Out-Null
            $windowTitle = [Win32Capture]::GetWindowTitle($windowInfo.Handle)
            $windowClass = [Win32Capture]::GetWindowClass($windowInfo.Handle)
            Save-WindowScreenshot -Handle $windowInfo.Handle -Path $imagePath
            $stdoutTail = Get-LogExcerpt -Path $stdoutPath
            $stderrTail = Get-LogExcerpt -Path $stderrPath
            Write-Log "[$(Get-Date -Format s)] OK   $category/$appId | template=$template | image=$imagePath | window_pid=$($windowInfo.WindowPid) | title=$windowTitle | class=$windowClass | bounds=$($windowRect.Left),$($windowRect.Top),$($windowRect.Right),$($windowRect.Bottom) | stdout_tail=$stdoutTail | stderr_tail=$stderrTail"
        }
        else {
            $stdoutTail = Get-LogExcerpt -Path $stdoutPath
            $stderrTail = Get-LogExcerpt -Path $stderrPath
            $exitState = if ($proc.HasExited) { "exited:$($proc.ExitCode)" } else { "running" }
            Write-Log "[$(Get-Date -Format s)] WARN $category/$appId | template=$template | no window detected within ${WaitSeconds}s | proc=$exitState | stdout=$stdoutPath | stderr=$stderrPath | stdout_tail=$stdoutTail | stderr_tail=$stderrTail"
        }
    }
    catch {
        $stdoutTail = Get-LogExcerpt -Path $stdoutPath
        $stderrTail = Get-LogExcerpt -Path $stderrPath
        Write-Log "[$(Get-Date -Format s)] FAIL $manifestPath | template=$template | message=$($_.Exception.Message) | stdout=$stdoutPath | stderr=$stderrPath | stdout_tail=$stdoutTail | stderr_tail=$stderrTail"
    }
    finally {
        if ($CooldownSeconds -gt 0) {
            Start-Sleep -Seconds $CooldownSeconds
        }

        if ($proc) {
            try {
                $descendantPids = Get-DescendantPids -RootPid $proc.Id | Where-Object { $_ -ne $proc.Id }
                foreach ($childPid in ($descendantPids | Sort-Object -Descending)) {
                    Stop-Process -Id $childPid -Force -ErrorAction SilentlyContinue
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

if ($DryRun) {
    $summaryLine = "DRYRUN SUMMARY | gui_candidates=$summaryGui | qt_like=$summaryQt | non_qt_like=$summaryNonQt | dryrun_entries=$summaryDryRun"
    Write-Host $summaryLine
    Write-Log "[$(Get-Date -Format s)] $summaryLine"
}
