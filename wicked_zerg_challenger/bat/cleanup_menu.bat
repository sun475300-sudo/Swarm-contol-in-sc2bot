@echo off
chcp 65001 > nul
title Project Cleanup System
color 0B

echo.
echo ====================================================
echo    Wicked Zerg Project Cleanup System
echo ====================================================
echo.
echo [1] Test Run (Dry-Run) - Preview changes only
echo [2] Cleanup Project - Execute cleanup
echo [3] Classify Drive Files (D: Drive only)
echo [4] Full Cleanup + Classification
echo [5] Schedule Auto-Cleanup (Task Scheduler)
echo [6] View Last Report
echo [0] Exit
echo.
echo ====================================================
echo.

set /p choice="Select option: "

if "%choice%"=="1" goto dryrun
if "%choice%"=="2" goto cleanup
if "%choice%"=="3" goto classify
if "%choice%"=="4" goto full
if "%choice%"=="5" goto schedule
if "%choice%"=="6" goto report
if "%choice%"=="0" goto end

echo Invalid choice!
timeout /t 2 > nul
goto menu

:dryrun
echo.
echo [DRY-RUN MODE] Preview only...
python tools\cleanup_and_organize.py --dry-run
pause
goto end

:cleanup
echo.
echo Running project cleanup...
python tools\cleanup_and_organize.py --keep-logs 2
echo.
echo Cleanup complete!
pause
goto end

:classify
echo.
echo Classifying D: drive files...
echo This may take a while...
python tools\auto_classify_drive.py --drives D: --depth 3
echo.
echo Classification complete!
pause
goto end

:full
echo.
echo Running FULL cleanup + classification...
echo.
echo Step 1/2: Project cleanup...
python tools\cleanup_and_organize.py --keep-logs 2
echo.
echo Step 2/2: Drive classification...
python tools\auto_classify_drive.py --drives D: --depth 2
echo.
echo All operations complete!
pause
goto end

:schedule
echo.
echo ====================================================
echo    Task Scheduler Registration
echo ====================================================
echo.
echo NOTE: Administrator privileges required!
echo.
echo Opening PowerShell as Administrator...
echo.
powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', '%~dp0register_cleanup_scheduler.ps1'"
echo.
echo Check the administrator PowerShell window that opened.
echo.
pause
goto end

:report
echo.
echo Latest cleanup report:
echo.
dir /b /o-d data\cleanup_report_*.json 2>nul | findstr /r ".*" >nul
if errorlevel 1 (
    echo No reports found.
) else (
    for /f %%i in ('dir /b /o-d data\cleanup_report_*.json') do (
        echo Report: %%i
        type data\%%i
        goto :report_done
    )
)
:report_done
pause
goto end

:end
echo.
echo Thank you for using Project Cleanup System!
timeout /t 2 > nul
exit /b
