param(
    [string]$Action = "status",
    [string]$Number = "",
    [string]$Text = ""
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

function Get-PhoneWindow {
    $proc = Get-Process PhoneExperienceHost -ErrorAction SilentlyContinue
    if (-not $proc) { return $null }
    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $cond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $proc.Id)
    $windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)
    $tabCond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::AutomationIdProperty, "CallingNodeAutomationId")
    foreach ($w in $windows) {
        if ($w.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $tabCond)) { return $w }
    }
    if ($windows.Count -gt 0) { return $windows[0] }
    return $null
}

function Ensure-Window {
    $win = Get-PhoneWindow
    if ($win) { return $win }
    $app = (Get-StartApps | Where-Object { $_.AppID -like "Microsoft.YourPhone*" } | Select-Object -First 1)
    if (-not $app) { return $null }
    Start-Process ("shell:appsFolder\" + $app.AppID)
    for ($i = 0; $i -lt 25; $i++) {
        Start-Sleep -Milliseconds 600
        $win = Get-PhoneWindow
        if ($win) { return $win }
    }
    return $null
}

function Find-ById($win, $id) {
    $c = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::AutomationIdProperty, $id)
    return $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $c)
}

function Find-ByName($win, $name) {
    $c = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty, $name)
    return $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $c)
}

function Get-Text($win, $id) {
    $el = Find-ById $win $id
    if ($el) { return $el.Current.Name }
    return ""
}

function Invoke-Element($el) {
    $p = $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
    $p.Invoke()
}

function Open-CallsTab($win) {
    $tab = Find-ById $win "CallingNodeAutomationId"
    if (-not $tab) { return $false }
    $p = $tab.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
    $p.Select()
    Start-Sleep -Milliseconds 1500
    return $true
}

function Get-Status([string]$state = "ok", [string]$errorText = "", [string]$device = "") {
    $win = Get-PhoneWindow
    if (-not $win) {
        return (@{ ok = $false; state = "closed"; error = "Окно «Связь с телефоном» не открыто"; device = "" } | ConvertTo-Json -Compress)
    }
    if (-not $device) { $device = Get-Text $win "PhoneNameTextBlock" }
    $win = $win
    $null = Open-CallsTab $win
    $dialerError = Get-Text $win "DialerPaneErrorTitle"
    $result = @{
        ok = [string]::IsNullOrEmpty($dialerError)
        state = if ($dialerError) { "dialer_error" } else { "ready" }
        device = $device
        error = $dialerError
        hint = if ($dialerError) { "На телефоне откройте «Связь с Windows» → разрешения для звонков, включите Bluetooth, затем «Повторить попытку»" } else { "" }
    }
    return ($result | ConvertTo-Json -Compress)
}

if ($Action -eq "status") {
    Write-Output (Get-Status)
    exit 0
}

if ($Action -eq "open") {
    $win = Ensure-Window
    if (-not $win) { Write-Output (@{ ok = $false; error = "Не удалось открыть Phone Link" } | ConvertTo-Json -Compress); exit 1 }
    Write-Output (Get-Status)
    exit 0
}

if ($Action -eq "call") {
    $win = Ensure-Window
    if (-not $win) { Write-Output (@{ ok = $false; error = "Не удалось открыть Phone Link" } | ConvertTo-Json -Compress); exit 1 }

    if (-not (Open-CallsTab $win)) {
        Write-Output (@{ ok = $false; error = "Вкладка «Вызовы» не найдена" } | ConvertTo-Json -Compress)
        exit 1
    }

    $dialerError = Get-Text $win "DialerPaneErrorTitle"
    if ($dialerError) {
        $retry = Find-ById $win "DialerPaneErrorActionButton"
        if ($retry) { try { Invoke-Element $retry } catch {} }
        Start-Sleep -Seconds 4
        $dialerError = Get-Text $win "DialerPaneErrorTitle"
    }
    if ($dialerError) {
        $msg = "Phone Link не может дозвониться: " + $dialerError +
            ". На телефоне откройте «Связь с Windows», разрешите звонки и включите Bluetooth."
        Write-Output (@{ ok = $false; error = $msg; state = "dialer_error" } | ConvertTo-Json -Compress)
        exit 2
    }

    $box = Find-ById $win "TextBox"
    if (-not $box) {
        Write-Output (@{ ok = $false; error = "Поле набора номера не найдено" } | ConvertTo-Json -Compress)
        exit 1
    }

    $value = $box.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
    $value.SetValue($Number)
    Start-Sleep -Milliseconds 1800

    $dialButton = $null
    foreach ($candidate in @("CallLogDialButton", "DialButton", "CallButton")) {
        $dialButton = Find-ById $win $candidate
        if ($dialButton) { break }
    }
    if (-not $dialButton) {
        $dialButton = Find-ByName $win "Звонок"
    }
    if (-not $dialButton) {
        Write-Output (@{ ok = $false; error = "Кнопка «Звонок» не найдена — номер введён в поиск, но набрать не удалось" } | ConvertTo-Json -Compress)
        exit 1
    }

    try {
        Invoke-Element $dialButton
        Start-Sleep -Seconds 3
        Write-Output (@{ ok = $true; state = "calling"; number = $Number; device = (Get-Text $win "PhoneNameTextBlock") } | ConvertTo-Json -Compress)
        exit 0
    } catch {
        Write-Output (@{ ok = $false; error = ("Не удалось нажать «Звонок»: " + $_.Exception.Message) } | ConvertTo-Json -Compress)
        exit 1
    }
}

Write-Output (@{ ok = $false; error = "Неизвестное действие: $Action" } | ConvertTo-Json -Compress)
exit 1
