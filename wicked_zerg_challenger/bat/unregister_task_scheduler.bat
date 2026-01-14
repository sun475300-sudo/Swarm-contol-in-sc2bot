@echo off
REM ===================================================
REM Unregister Auto Git Push from Task Scheduler
REM ===================================================
REM Run this script with Administrator privileges

echo =======================================
echo Unregister Auto Git Push Task
echo =======================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click and select 'Run as Administrator'
    pause
    exit /b 1
)

schtasks /Delete /TN "WickedZergAutoGitPush" /F

if %errorLevel% equ 0 (
    echo.
    echo SUCCESS: Task unregistered successfully!
) else (
    echo.
    echo WARNING: Task not found or already unregistered.
)

echo.
pause
