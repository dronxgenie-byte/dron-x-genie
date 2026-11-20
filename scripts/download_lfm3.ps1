<#
.SYNOPSIS
    Скачивает модель LFM3-1.7B (GGUF) для локального запуска через llama.cpp / LM Studio.
    Запускается автоматически при первом старте, если модели нет и есть интернет.
.DESCRIPTION
    1. Проверяет наличие модели в %LOCALAPPDATA%\Zhorik\models\
    2. Если нет — качает с Hugging Face (LiquidAI/LFM3-1.7B-GGUF)
    3. Сохраняет в models/ и создаёт .model_ready флаг
.NOTES
    Версия: 0.1.0
    Требует: PowerShell 5.1+, интернет
#>

param(
    [string]$ModelName = "LFM3-1.7B-Q4_K_M.gguf",
    [string]$ModelRepo = "LiquidAI/LFM3-1.7B-GGUF",
    [string]$DownloadUrl = "https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF/resolve/main/LFM3-1.7B-Q4_K_M.gguf",
    [int]$ExpectedSizeMB = 1024  # ~1 GB для Q4_K_M
)

$ErrorActionPreference = "Stop"

$SCRIPT_DIR   = $PSScriptRoot
$PROJECT_ROOT = Split-Path $SCRIPT_DIR -Parent
$MODELS_DIR   = Join-Path $PROJECT_ROOT "models"
$MODEL_PATH   = Join-Path $MODELS_DIR $ModelName
$FLAG_PATH    = Join-Path $MODELS_DIR ".model_ready"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] [$Level] $Message"
}

# --- 1. Check if model already exists ---
if (Test-Path $MODEL_PATH) {
    $size = (Get-Item $MODEL_PATH).Length / 1MB
    if ($size -ge ($ExpectedSizeMB * 0.9)) {
        Write-Log "Модель уже существует: $MODEL_PATH ($([math]::Round($size, 1)) MB)"
        if (-not (Test-Path $FLAG_PATH)) {
            New-Item -ItemType File -Path $FLAG_PATH -Force | Out-Null
        }
        exit 0
    } else {
        Write-Log "Файл модели повреждён/неполный ($([math]::Round($size, 1)) MB), перекачиваем..." "WARN"
        Remove-Item $MODEL_PATH -Force
    }
}

# --- 2. Create models directory ---
if (-not (Test-Path $MODELS_DIR)) {
    New-Item -ItemType Directory -Path $MODELS_DIR -Force | Out-Null
}

# --- 3. Check internet ---
Write-Log "Проверка интернета..."
try {
    $test = Invoke-WebRequest -Uri "https://huggingface.co" -TimeoutSec 5 -UseBasicParsing
    if ($test.StatusCode -ne 200) { throw "No internet" }
} catch {
    Write-Log "Интернет недоступен. Модель не может быть загружена автоматически." "ERROR"
    Write-Log "См. docs/OFFLINE_SETUP.md для ручной установки модели." "ERROR"
    exit 1
}

# --- 4. Download with progress ---
Write-Log "Скачивание модели $ModelName из $ModelRepo..."
Write-Log "Размер: ~$ExpectedSizeMB MB. Это может занять несколько минут."

try {
    $wc = New-Object System.Net.WebClient
    $wc.Proxy = [System.Net.WebRequest]::DefaultWebProxy
    $wc.Proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials

    $startTime = Get-Date
    $lastPercent = -1

    Register-ObjectEvent -InputObject $wc -EventName DownloadProgressChanged -Action {
        $e = $Event.SourceEventArgs
        $percent = [math]::Floor($e.ProgressPercentage)
        if ($percent % 10 -eq 0 -and $percent -ne $Global:lastPercent) {
            $elapsed = (Get-Date) - $Global:startTime
            $speed = if ($elapsed.TotalSeconds -gt 0) { "{0:N1} MB/s" -f ($e.BytesReceived / 1MB / $elapsed.TotalSeconds) } else { "..." }
            Write-Host "  Прогресс: $percent% | $speed"
            $Global:lastPercent = $percent
        }
    } | Out-Null

    $wc.DownloadFileTaskAsync($DownloadUrl, $MODEL_PATH).Wait()

    Unregister-Event -SourceIdentifier "DownloadProgressChanged" -Force -ErrorAction SilentlyContinue

    # Verify
    $size = (Get-Item $MODEL_PATH).Length / 1MB
    if ($size -lt ($ExpectedSizeMB * 0.9)) {
        throw "Downloaded file too small: $([math]::Round($size, 1)) MB"
    }

    Write-Log "Модель успешно загружена: $MODEL_PATH ($([math]::Round($size, 1)) MB)"

    # Create flag
    New-Item -ItemType File -Path $FLAG_PATH -Force | Out-Null
    Write-Log "Флаг готовности создан: $FLAG_PATH"

} catch {
    Write-Log "Ошибка загрузки: $($_.Exception.Message)" "ERROR"
    if (Test-Path $MODEL_PATH) { Remove-Item $MODEL_PATH -Force }
    exit 1
}

Write-Log "Готово. Модель доступна для LM Studio / llama.cpp."
exit 0