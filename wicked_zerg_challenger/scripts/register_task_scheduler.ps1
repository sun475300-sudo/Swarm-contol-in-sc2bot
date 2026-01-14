# ===================================================
# Register Auto Git Push to Windows Task Scheduler
# ===================================================
# Run this script with Administrator privileges

Param(
    [int]$IntervalMinutes = 5
)

$ErrorActionPreference = "Stop"

# Configuration
$TaskName = "WickedZergAutoGitPush"
$ProjectRoot = "D:\wicked_zerg_challenger"
$ScriptPath = Join-Path $ProjectRoot "tools\auto_git_push.py"
$LogPath = Join-Path $ProjectRoot "tools\auto_git_push.log"

# Detect Python executable
if (Test-Path (Join-Path $ProjectRoot ".venv\Scripts\python.exe")) {
    $PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
} else {
    $PythonExe = "python"
}

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "Auto Git Push Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Task Name: $TaskName" -ForegroundColor Yellow
Write-Host "Python: $PythonExe" -ForegroundColor Yellow
Write-Host "Script: $ScriptPath" -ForegroundColor Yellow
Write-Host "Interval: $IntervalMinutes minutes" -ForegroundColor Yellow
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Remove existing task if present
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create task action
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "-u `"$ScriptPath`"" `
    -WorkingDirectory $ProjectRoot

# Create trigger (run at startup + repeat every X minutes)
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Trigger.Repetition = New-ScheduledTaskRepetition -Interval (New-TimeSpan -Minutes $IntervalMinutes) -Duration ([System.TimeSpan]::MaxValue)

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Get current user
$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Limited

# Register task
Write-Host "Registering task..." -ForegroundColor Green
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Automatically commit and push Git changes for Wicked Zerg Challenger project every $IntervalMinutes minutes"

Write-Host ""
Write-Host "SUCCESS: Task registered successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "The task will:" -ForegroundColor Cyan
Write-Host "  - Start automatically at system boot" -ForegroundColor White
Write-Host "  - Repeat every $IntervalMinutes minutes" -ForegroundColor White
Write-Host "  - Run even on battery power" -ForegroundColor White
Write-Host "  - Restart automatically on failure" -ForegroundColor White
Write-Host ""
Write-Host "Verify task:" -ForegroundColor Yellow
Write-Host "  taskschd.msc" -ForegroundColor White
Write-Host "  or" -ForegroundColor White
Write-Host "  Get-ScheduledTask -TaskName $TaskName | Format-List *" -ForegroundColor White
Write-Host ""
Write-Host "Start task immediately:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName $TaskName" -ForegroundColor White
Write-Host ""
Write-Host "Remove task:" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false" -ForegroundColor White
Write-Host ""
