# Uruchom ten skrypt jako Administrator (PPM -> "Uruchom jako administrator")
$python = (Get-Command python -ErrorAction Stop).Source
$projectDir = "C:\Users\48519\Documents\Monika\Szkolenia inne\Vibecoding\Project"
$script = "$projectDir\data_refresh.py"

$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "`"$script`"" `
    -WorkingDirectory $projectDir

$trigger = New-ScheduledTaskTrigger -Daily -At "10:00"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName "MyPrint - Codzienny import faktur" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Pobiera faktury sprzedazy z MyPrint i aktualizuje baze dashboardu" `
    -RunLevel Highest `
    -Force

Write-Host "Zadanie zostalo zaplanowane - codziennie o 10:00" -ForegroundColor Green
