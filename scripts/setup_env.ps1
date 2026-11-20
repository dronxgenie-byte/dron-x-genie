<#
.SYNOPSIS
    Setup environment for DRON X GENIE: create .venv, install dependencies.
.DESCRIPTION
    1. Checks/creates .venv in project root.
    2. Installs dependencies from requirements.txt via .venv pip.
    All paths are relative - script is portable.
#>
$ErrorActionPreference = "Stop"

$SCRIPT_DIR   = $PSScriptRoot
$PROJECT_ROOT = Split-Path $SCRIPT_DIR -Parent
$VENV_DIR     = Join-Path $PROJECT_ROOT ".venv"
$VENV_PYTHON  = Join-Path (Join-Path $VENV_DIR "Scripts") "python.exe"
$REQUIREMENTS = Join-Path $PROJECT_ROOT "requirements-core.txt"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "DRON X GENIE - environment setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------
# Step 1: Check and create .venv
# ---------------------------------------------------------------
Write-Host "[1/2] Checking and creating virtual environment .venv..." -ForegroundColor Yellow
if (-not (Test-Path $VENV_PYTHON)) {
    python -m venv "$VENV_DIR" 2>&1 | Write-Host
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-Host "ERROR: failed to create .venv" -ForegroundColor Red
        exit 1
    }
    Write-Host "Created: $VENV_DIR" -ForegroundColor Green
} else {
    Write-Host "[1/2] .venv already exists." -ForegroundColor Green
}

# ---------------------------------------------------------------
# Step 2: Install dependencies via .venv python
# ---------------------------------------------------------------
Write-Host "[2/2] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
$installCmd = '"' + $VENV_PYTHON + '" -m pip install --no-deps --timeout 120 --retries 3 --no-input -r "' + $REQUIREMENTS + '"'
$installOutput = & { $ErrorActionPreference = "Continue"; cmd /c $installCmd 2>&1 }
$installExitCode = $LASTEXITCODE
$installOutput | Write-Host
if ($installExitCode -ne 0) {
    if (Test-Path $VENV_PYTHON) {
        Write-Host "WARNING: dependency install failed (likely offline), but .venv exists — continuing with installed packages." -ForegroundColor Yellow
    } else {
        Write-Host "ERROR: failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}
Write-Host "Dependencies installed." -ForegroundColor Green

# Optional ML dependencies
$mlReqs = Join-Path $PROJECT_ROOT "requirements-ml.txt"
if (Test-Path $mlReqs) {
    Write-Host "[Optional] Installing ML dependencies..." -ForegroundColor Yellow
    $mlCmd = '"' + $VENV_PYTHON + '" -m pip install --no-deps --timeout 120 --retries 3 --no-input -r "' + $mlReqs + '"'
    $mlOutput = & { $ErrorActionPreference = "Continue"; cmd /c $mlCmd 2>&1 }
    $mlExitCode = $LASTEXITCODE
    $mlOutput | Write-Host
    if ($mlExitCode -ne 0) {
        Write-Host "WARNING: optional ML dependencies failed to install." -ForegroundColor Yellow
    }
}
