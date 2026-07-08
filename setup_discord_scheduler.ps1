# Uruchom jako Administrator (PPM -> "Uruchom jako administrator")
# Przed uruchomieniem podmien TWOJ_URL_WEBHOOKA ponizej

$webhookUrl  = "TWOJ_URL_WEBHOOKA"   # <-- wklej tutaj URL z Discorda (nie commituj tego pliku!)
$python      = (Get-Command python -ErrorAction Stop).Source
$projectDir  = "C:\Users\48519\Documents\Monika\Szkolenia inne\Vibecoding\Project"
$script      = "$projectDir\discord_notify.py"

$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "`"$script`"" `
    -WorkingDirectory $projectDir

# Uruchom o 10:30 (30 min po pobraniu danych o 10:00)
$trigger = New-ScheduledTaskTrigger -Daily -At "10:30"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Przekaz URL jako zmienna srodowiskowa do procesu
$env_block = [System.Collections.Generic.Dictionary[string,string]]::new()
$env_block["DISCORD_WEBHOOK_URL"] = $webhookUrl

Register-ScheduledTask `
    -TaskName "MyPrint - Discord Sales Notify" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Wysyla dzienna sprzedaz per klient na Discord po imporcie MyPrint" `
    -RunLevel Highest `
    -Force

# Ustaw zmienna srodowiskowa DISCORD_WEBHOOK_URL trwale dla konta
[System.Environment]::SetEnvironmentVariable(
    "DISCORD_WEBHOOK_URL", $webhookUrl, "User"
)

Write-Host "Gotowe! Powiadomienia beda wysylane codziennie o 10:30" -ForegroundColor Green
Write-Host "Przetestuj recznie: python `"$script`"" -ForegroundColor Cyan
