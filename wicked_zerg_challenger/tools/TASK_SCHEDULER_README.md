# Windows Task Scheduler Registration

## Quick Start

### Register Task (Administrator Required)
```powershell
# Run PowerShell as Administrator
cd D:\wicked_zerg_challenger\tools
.\register_task_scheduler.ps1

# Or with custom interval (default 5 minutes)
.\register_task_scheduler.ps1 -IntervalMinutes 10
```

### Unregister Task
```cmd
# Run as Administrator
tools\unregister_task_scheduler.bat
```

## What It Does

The task scheduler will:
- ? Start automatically at system boot
- ? Repeat every 5 minutes (customizable)
- ? Run even on battery power
- ? Restart automatically on failure (up to 3 times)
- ? Only run when network is available

## Manual Control

### Start Task Immediately
```powershell
Start-ScheduledTask -TaskName "WickedZergAutoGitPush"
```

### Stop Running Task
```powershell
Stop-ScheduledTask -TaskName "WickedZergAutoGitPush"
```

### Check Task Status
```powershell
Get-ScheduledTask -TaskName "WickedZergAutoGitPush" | Format-List *
```

### View Task in GUI
```cmd
taskschd.msc
```
Then search for "WickedZergAutoGitPush"

## Troubleshooting

### Task Not Running
1. Check task status: `Get-ScheduledTask -TaskName "WickedZergAutoGitPush"`
2. Check log file: `tools\auto_git_push.log`
3. Ensure network connection is available
4. Verify Python path is correct

### Disable Task (Without Unregistering)
```powershell
Disable-ScheduledTask -TaskName "WickedZergAutoGitPush"
```

### Re-enable Task
```powershell
Enable-ScheduledTask -TaskName "WickedZergAutoGitPush"
```

## Environment Variables

You can customize behavior by setting system environment variables:

```powershell
# Custom commit message prefix (default: "chore")
[System.Environment]::SetEnvironmentVariable("AUTO_PUSH_MESSAGE_PREFIX", "auto", "User")

# Custom push interval in seconds (default: 300)
[System.Environment]::SetEnvironmentVariable("AUTO_PUSH_INTERVAL_SEC", "600", "User")

# Custom remote name (default: "origin")
[System.Environment]::SetEnvironmentVariable("AUTO_PUSH_REMOTE", "origin", "User")
```

Restart the task after changing environment variables.
