@echo off
:: Run register_cleanup_scheduler.ps1 with Administrator privileges
title Register Cleanup Scheduler (Admin Mode)
color 0B

echo.
echo ====================================================
echo    Starting PowerShell as Administrator...
echo ====================================================
echo.
echo This will register the daily cleanup task.
echo.

powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', '%~dp0register_cleanup_scheduler.ps1'"

echo.
echo Administrator PowerShell window should open now.
echo Close this window after the task is registered.
echo.
pause
