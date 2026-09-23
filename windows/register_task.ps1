# Registers run_mt4_export.bat as a recurring Windows Task Scheduler
# task, so the MT4 dashboard always shows a fresh signal.
#
# Usage (PowerShell, run as the user who will run MT4 -- NOT as
# Administrator, unless MT4 itself also runs elevated):
#   cd C:\MaduOKU\windows
#   powershell -ExecutionPolicy Bypass -File .\register_task.ps1
#
# Edit $IntervalMinutes below to match how often you want signals
# refreshed (should be <= your smallest timeframe, e.g. 5 for M5).

$TaskName        = "MaduOKU_MT4_Export"
$ScriptPath      = Join-Path $PSScriptRoot "run_mt4_export.bat"
$IntervalMinutes = 5

$action  = New-ScheduledTaskAction -Execute $ScriptPath
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
             -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
             -RepetitionDuration ([TimeSpan]::MaxValue)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
              -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Exports MaduOKU reversal signals for the MT4 dashboard indicator" `
    -Force

Write-Host "Task '$TaskName' registered: runs $ScriptPath every $IntervalMinutes minute(s)."
Write-Host "Check status any time in Task Scheduler, or run: Get-ScheduledTaskInfo -TaskName '$TaskName'"
