$ErrorActionPreference = "Stop"

$TOOL_NAME   = "ngrok"
$LOCAL_PORT  = 5173
$NGROK_EXE   = Join-Path (Get-Location).Path "tools\ngrok.exe"
$LOG_FILE    = Join-Path $env:TEMP 'dronxgenie-ngrok.log'
$ERR_FILE    = Join-Path $env:TEMP 'dronxgenie-ngrok.err'
$PID_FILE    = Join-Path $env:TEMP 'dronxgenie-ngrok.pid'
$PIN_FILE    = Join-Path $env:TEMP 'dronxgenie-ngrok.pin'

# Генерируем случайный 6-значный PIN при каждом запуске
$PIN = (100000..999999 | Get-Random)

Write-Host 'DRON X GENIE - ngrok tunnel'
Write-Host ''

# Проверка наличия ngrok.exe
if (-not (Test-Path $NGROK_EXE)) {
    Write-Host 'ERROR: ngrok.exe не найден в tools\ngrok.exe' -ForegroundColor Red
    exit 1
}

# Проверка: не запущен ли уже ngrok на этом порту
if (Test-Path $PID_FILE) {
    $oldPid = Get-Content $PID_FILE -ErrorAction SilentlyContinue
    if ($oldPid) {
        try {
            $proc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
            if ($proc -and $proc.ProcessName -eq 'ngrok') {
                Write-Host ("ngrok уже запущен (PID " + $oldPid + "). Повторный запуск не требуется.") -ForegroundColor Yellow
                if (Test-Path $PIN_FILE) {
                    $oldPin = Get-Content $PIN_FILE -ErrorAction SilentlyContinue
                    Write-Host ("PIN: " + $oldPin) -ForegroundColor Cyan
                }
                exit 0
            }
        } catch { }
        Remove-Item $PID_FILE -Force -ErrorAction SilentlyContinue
    }
}

# Сохраняем PIN во временный файл (не в постоянное хранилище)
Set-Content -Path $PIN_FILE -Value $PIN.ToString()

Write-Host ('PIN доступа к кабине: ' + $PIN) -ForegroundColor Cyan
Write-Host ('PIN действителен только для этой сессии туннеля.') -ForegroundColor Gray
Write-Host ''

# Остановка предыдущего процесса ngrok если есть
Get-Process -Name 'ngrok' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Запуск ngrok
Write-Host ('Запуск ngrok на порту ' + $LOCAL_PORT + '...') -ForegroundColor Yellow
$process = Start-Process -FilePath $NGROK_EXE -ArgumentList ('http', $LOCAL_PORT.ToString()) -PassThru -WindowStyle Hidden -RedirectStandardOutput $LOG_FILE -RedirectStandardError $ERR_FILE
Set-Content -Path $PID_FILE -Value $process.Id
Write-Host ('ngrok запущен (PID ' + $process.Id + '). Лог: ' + $LOG_FILE) -ForegroundColor Green

# Ожидание публичного URL через локальный API ngrok (http://127.0.0.1:4040/api/tunnels)
Write-Host 'Ожидание публичного URL от ngrok...' -ForegroundColor Yellow
$publicUrl = $null
$apiBase = "http://127.0.0.1:4040"
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $tunnels = Invoke-RestMethod -Uri "$apiBase/api/tunnels" -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($tunnels -and $tunnels.tunnels) {
            foreach ($tunnel in $tunnels.tunnels) {
                if ($tunnel.proto -eq 'https') {
                    $publicUrl = $tunnel.public_url
                    break
                }
            }
        }
        if ($publicUrl) { break }
    } catch { }
}

# Результат — URL и PIN выводятся только на экран, не пишутся в постоянные файлы
Write-Host ''
if ($publicUrl) {
    Write-Host 'ТУННЕЛЬ АКТИВЕН' -ForegroundColor Green
    Write-Host ('Кабина доступна по адресу: ' + $publicUrl) -ForegroundColor Green
    Write-Host ('PIN для доступа: ' + $PIN) -ForegroundColor Cyan
    Write-Host ('Лог ngrok: ' + $LOG_FILE) -ForegroundColor Gray
} else {
    Write-Host 'ngrok запущен, но публичный URL не получен.' -ForegroundColor Yellow
    Write-Host 'Проверьте лог: ' + $LOG_FILE -ForegroundColor Yellow
    Write-Host 'Проверьте ошибки: ' + $ERR_FILE -ForegroundColor Yellow
}

Write-Host ''
if (Test-Path $PID_FILE) {
    $tunnelPid = Get-Content $PID_FILE -ErrorAction SilentlyContinue
    if ($tunnelPid) {
        Write-Host ('Для остановки: Stop-Process -Id ' + $tunnelPid) -ForegroundColor Gray
        Write-Host ('Удалить PIN-файл: Remove-Item ' + $PIN_FILE) -ForegroundColor Gray
    }
}
