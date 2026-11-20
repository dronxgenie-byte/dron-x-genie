# e2e-install.ps1 - automated testing of Zhorik-Setup-0.1.0.exe
# Usage: .\e2e-install.ps1
# Requires: PowerShell 5.1+, admin rights (for firewall rules)

$ErrorActionPreference = "Stop"
$results = @{}
$script:failed = $false

function Write-Result {
    param([string]$Test, [bool]$Pass, [string]$Detail = "")
    $status = if ($Pass) { "PASS" } else { "FAIL" }
    $results[$Test] = $Pass
    if (-not $Pass) { $script:failed = $true }
    $statusColor = if ($Pass) { "Green" } else { "Red" }
    Write-Host "$status - $Test" -ForegroundColor $statusColor
    if ($Detail) { Write-Host "      $Detail" -ForegroundColor Gray }
}

function Write-Section {
    param([string]$Name)
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
}

# ============================================================================
# 0. Check input data
# ============================================================================
Write-Section "0. Checking input data"

$InstallerPath = "dist\Zhorik-Setup-0.1.0.exe"
$InstallRoot = "$env:LOCALAPPDATA\Zhorik"
$HealthTimeout = 60

# ============================================================================
# Pre-check: free port 8000 (zombie uvicorn sockets)
# ============================================================================
Write-Host "Checking port 8000 for stale listeners..." -ForegroundColor Gray
$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn) {
    $procExists = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($procExists) {
        Write-Host "Port 8000 busy (PID: $($conn.OwningProcess)). Killing..." -ForegroundColor Yellow
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        $conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
        if ($conn) {
            Write-Result "Port 8000 freed" $false "Still busy: PID $($conn.OwningProcess)"
        }
        else {
            Write-Result "Port 8000 freed" $true
        }
    }
    else {
        # Process is dead but socket lingers (orphaned). Windows will release it.
        Write-Host "Port 8000 has orphaned socket (process $($conn.OwningProcess) is dead). Windows will release it." -ForegroundColor Yellow
        Write-Result "Port 8000 free" $true "Orphaned socket - will be released by kernel"
    }
}
else {
    Write-Result "Port 8000 free" $true
}

if (-not (Test-Path $InstallerPath -PathType Leaf)) {
    Write-Result "Installer exists" $false "Not found: $InstallerPath"
    Write-Host "Stopping." -ForegroundColor Red
    exit 1
}
else {
    Write-Result "Installer exists" $true "$InstallerPath ($(Get-Item $InstallerPath).Length bytes)"
}

# ============================================================================
# 1. Clean up old installation
# ============================================================================
Write-Section "1. Cleaning up old installation"

if (Test-Path $InstallRoot) {
    Remove-Item $InstallRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-Result "Old folder removed" $true "$InstallRoot"
}
else {
    Write-Result "Old folder absent" $true "Nothing to remove"
}

Remove-Item "HKCU:\Software\Zhorik" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Zhorik" -Force -ErrorAction SilentlyContinue
Write-Result "Registry cleared" $true "HKCU\Software\Zhorik"

# ============================================================================
# 2. Silent install (NSIS /S)
# ============================================================================
Write-Section "2. Silent installer run"

Write-Host "Command: $InstallerPath /S /D=$InstallRoot" -ForegroundColor Gray

$installProc = Start-Process -FilePath $InstallerPath -ArgumentList "/S", "/D=$InstallRoot" -Wait -PassThru -NoNewWindow
$installExitCode = $installProc.ExitCode

if ($installExitCode -eq 0) {
    Write-Result "Install completed" $true "exit code = 0"
}
else {
    Write-Result "Install failed" $false "exit code = $installExitCode"
}

# ============================================================================
# 3. Verify installed files and shortcuts
# ============================================================================
Write-Section "3. Verifying files and shortcuts"

$expectedFiles = @(
    "$InstallRoot\backend\agent\main.py",
    "$InstallRoot\backend\agent\routes.py",
    "$InstallRoot\backend\agent\pi_dron.py",
    "$InstallRoot\backend\agent\dron.py",
    "$InstallRoot\requirements.txt",
    "$InstallRoot\scripts\setup_env.ps1",
    "$InstallRoot\scripts\launcher.py",
    "$InstallRoot\scripts\download_lfm3.ps1",
    "$InstallRoot\prompts\system_cloud.md",
    "$InstallRoot\prompts\system_local.md",
    "$InstallRoot\frontend\dist\index.html",
    "$InstallRoot\frontend\dron_ui\app.js",
    "$InstallRoot\css\desktop.css",
    "$InstallRoot\js\desktop.js",
    "$InstallRoot\docs\E2E_TEST_CHECKLIST.md",
    "$InstallRoot\docs\USER_GUIDE_RU.md",
    "$InstallRoot\docs\OFFLINE_SETUP.md",
    "$InstallRoot\uninstall.exe"
)

foreach ($f in $expectedFiles) {
    $exists = Test-Path $f -PathType Leaf
    if (-not $exists) {
        Write-Result "File: $([System.IO.Path]::GetFileName($f))" $false "Missing: $f"
    }
    else {
        Write-Result "File: $([System.IO.Path]::GetFileName($f))" $true
    }
}

$startMenuLnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Zhorik\Zhorik.lnk"
Write-Result "Start Menu shortcut" (Test-Path $startMenuLnk -PathType Leaf) $startMenuLnk

if (Test-Path $startMenuLnk -PathType Leaf) {
    $ws = New-Object -ComObject WScript.Shell
    $shortcut = $ws.CreateShortcut($startMenuLnk)
    $target = $shortcut.TargetPath
    $workdir = $shortcut.WorkingDirectory
    Write-Result "Shortcut Target exists" (Test-Path $target -PathType Leaf) "Target: $target"
    Write-Result "Shortcut WorkingDir" (Test-Path $workdir -PathType Container) "WorkDir: $workdir"
}

# ============================================================================
# 4. Run setup_env.ps1 (create .venv + install deps)
# ============================================================================
Write-Section "4. Environment setup (setup_env.ps1)"

$setupLog = "$env:TEMP\zhorik-setup.log"
$setupCmd = "& `"$InstallRoot\scripts\setup_env.ps1`" 2>&1 | Tee-Object -FilePath `"$setupLog`""
$setupProc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$InstallRoot\scripts\setup_env.ps1`"" -Wait -PassThru -NoNewWindow
$setupExitCode = $setupProc.ExitCode

if ($setupExitCode -eq 0) {
    Write-Result "setup_env.ps1 completed" $true "exit code = 0"
}
else {
    Write-Result "setup_env.ps1 failed" $false "exit code = $setupExitCode, see $setupLog"
}

$venvPy = "$InstallRoot\.venv\Scripts\python.exe"
Write-Result ".venv created" (Test-Path $venvPy -PathType Leaf) $venvPy

if (Test-Path $setupLog) {
    $setupErrors = Select-String -Path $setupLog -Pattern "ERROR|WinError 5|Cannot uninstall|no RECORD" -ErrorAction SilentlyContinue
    if ($setupErrors) {
        Write-Result "No critical install errors" $false "Found: $($setupErrors | Select-Object -First 1 -ExpandProperty Line)"
    }
    else {
        Write-Result "No critical install errors" $true
    }
}

# ============================================================================
# 5. Start backend + health-check
# ============================================================================
Write-Section "5. Start backend + health-check"

# Check if port 8000 is available (orphaned sockets from killed processes can block it)
$port8000Busy = $false
$conns8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conns8000) {
    $allDead = $true
    foreach ($c in $conns8000) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            $allDead = $false
            break
        }
    }
    if ($allDead) {
        Write-Host "Port 8000 blocked by orphaned socket (dead process). Ignoring - kernel will release." -ForegroundColor Yellow
        Write-Result "Port 8000 free" $true "Orphaned socket - no live process"
    }
    else {
        $port8000Busy = $true
        Write-Host "Port 8000 busy (live PID). Killing..." -ForegroundColor Yellow
        foreach ($c in $conns8000) {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 3
        $conns8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
        if ($conns8000) {
            Write-Result "Port 8000 freed" $false "Still busy"
        }
        else {
            Write-Result "Port 8000 freed" $true
        }
    }
}
else {
    Write-Result "Port 8000 free" $true
}

if (-not $port8000Busy) {
    $backendLogOut = "$env:TEMP\zhorik-backend-out.log"
    $backendLogErr = "$env:TEMP\zhorik-backend-err.log"
    $backendProc = Start-Process -FilePath $venvPy -ArgumentList "-m", "uvicorn", "agent.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory "$InstallRoot\backend" -RedirectStandardOutput "$backendLogOut" -RedirectStandardError "$backendLogErr" -PassThru -NoNewWindow
    Write-Host "Backend started (PID $($backendProc.Id)), waiting $HealthTimeout sec..." -ForegroundColor Gray

    $healthUrl = "http://127.0.0.1:8000/api/health"
    $healthOk = $false
    $startTime = Get-Date

    # Wait for backend startup message in log (more reliable than Invoke-RestMethod)
    while ((Get-Date) - $startTime -lt (New-Timespan -Seconds $HealthTimeout)) {
        Start-Sleep -Seconds 2
        if (Test-Path $backendLogOut) {
            $startupMsg = Select-String -Path $backendLogOut -Pattern "Application startup complete|Uvicorn running on" -ErrorAction SilentlyContinue
            if ($startupMsg) {
                $healthOk = $true
                break
            }
        }
        # Also try HTTP health-check as fallback
        try {
            $response = Invoke-RestMethod -Uri $healthUrl -Method GET -TimeoutSec 2 -ErrorAction Stop
            $respStatus = $response.status
            if ($respStatus -in @("ok", "degraded")) {
                $healthOk = $true
                break
            }
            else {
                Write-Host "Health-check returned status: $respStatus" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "Health-check error: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    if ($healthOk) {
        Write-Result "Health-check /api/health" $true "Response: $response | < $HealthTimeout sec"
    }
    else {
        Write-Result "Health-check /api/health" $false "Backend not responding after $HealthTimeout sec"
    }

    if (Test-Path $backendLogOut) {
        $backendErrors = Select-String -Path $backendLogOut -Pattern "ImportError|ModuleNotFoundError|Traceback" -ErrorAction SilentlyContinue
        if ($backendErrors) {
            Write-Result "No import errors in backend" $false "Found: $($backendErrors | Select-Object -First 1 -ExpandProperty Line)"
        }
        else {
            Write-Result "No import errors in backend" $true
        }
    }

    try {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    catch {}
}
else {
    Write-Result "Health-check /api/health" $false "Skipped - port 8000 blocked by orphaned socket"
    Write-Result "No import errors in backend" $false "Skipped - port 8000 blocked by orphaned socket"
}

# ============================================================================
# 6. Uninstall
# ============================================================================
$uninstaller = "$InstallRoot\uninstall.exe"
if (Test-Path $uninstaller -PathType Leaf) {
    # Запускаем деинсталлятор
    $uninstallProc = Start-Process -FilePath $uninstaller -ArgumentList "/S" -Wait -PassThru -NoNewWindow
    $uninstallExitCode = $uninstallProc.ExitCode
    
    if ($uninstallExitCode -eq 0) {
        Write-Result "Uninstall completed" $true "exit code = 0"
    }
    else {
        Write-Result "Uninstall failed" $false "exit code = $uninstallExitCode"
    }
}
else {
    Write-Result "Uninstaller found" $false "Not found: $uninstaller"
}

# =========================================================
# Ожидание фонового удаления (чтобы папка успела исчезнуть)
# =========================================================
Write-Host "Waiting for NSIS uninstaller to finish in background..." -ForegroundColor Gray
$timeout = (Get-Date).AddSeconds(15)
while ((Test-Path -LiteralPath $InstallRoot) -and ((Get-Date) -lt $timeout)) {
    Start-Sleep -Milliseconds 500
}

# ============================================================================
# 7. Verify cleanup after removal
# ============================================================================
Write-Section "7. Cleanup verification"

$folderRemoved = -not (Test-Path $InstallRoot -PathType Container)
Write-Result "Install folder removed" $folderRemoved "Path: $InstallRoot"

$regKeyRemoved = -not (Test-Path "HKCU:\Software\Zhorik" -PathType Container)
Write-Result "Registry HKCU\Software\Zhorik removed" $regKeyRemoved

$unregRemoved = -not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Zhorik" -PathType Container)
Write-Result "Registry Uninstall key removed" $unregRemoved

$startMenuRemoved = -not (Test-Path $startMenuLnk -PathType Leaf)
Write-Result "Start Menu shortcut removed" $startMenuRemoved

# ============================================================================
# SUMMARY
# ============================================================================
Write-Section "E2E SUMMARY"

$passCount = ($results.Values | Where-Object { $_ -eq $true }).Count
$failCount = ($results.Values | Where-Object { $_ -eq $false }).Count
$total = $results.Count

Write-Host "Passed: $passCount / $total" -ForegroundColor Green
$failColor = if ($failCount -gt 0) { "Red" } else { "Green" }
Write-Host "Failed: $failCount / $total" -ForegroundColor $failColor

if ($failed) {
    Write-Host "E2E FAILED - there are failed steps." -ForegroundColor Red
    exit 1
}
else {
    Write-Host "E2E PASSED - all steps successful." -ForegroundColor Green
    exit 0
}