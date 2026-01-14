@echo off
REM Zerg AI Training Pipeline - All in One Launcher
REM Choose training option: Real Replays, Test, or AI Practice

REM CRITICAL: Ensure script runs from project root regardless of current directory
cd /d "%~dp0.."

setlocal enabledelayedexpansion

echo.
echo ================================
echo Zerg AI Training Pipeline
echo ================================
echo.

echo Choose training option:
echo.
echo [1] Download and train with real replays (RECOMMENDED)
echo [2] Quick test with sample data
echo [3] Train against built-in AI
echo [4] Extract replays from downloaded ZIPs
echo [5] View monitoring dashboard
echo [0] Exit
echo.

set /p choice="Enter your choice (0-5): "

if "%choice%"=="1" (
    echo.
    echo Starting Option 1: Real Replay Training
    echo.
    echo Step 1: Download replays from:
    echo   - GSL: https://www.afreecatv.com/user/gsl
    echo   - ESL: https://pro.eslgaming.com/starcraft/
    echo   - SC2: https://www.sc2replaystats.com/
    echo.
    echo Step 2: Save ZIP files to: C:\Users\sun47\Downloads\
    echo.
    pause
    echo.
    echo Step 3: Extracting replays...
    cd /d "%~dp0..\tools"
    python replay_lifecycle_manager.py --extract
    echo.
    echo Step 4: Starting training...
    cd /d "%~dp0.."
    python tools\integrated_pipeline.py --epochs 5
    goto end
)

if "%choice%"=="2" (
    echo.
    echo Starting Option 2: Test Mode Training
    cd /d "%~dp0..\local_training"
    python scripts\\integrated_pipeline.py --test-mode --epochs 1
    goto end
)

if "%choice%"=="3" (
    echo.
    echo Starting Option 3: AI Practice Training
    cd /d "%~dp0.."
    python main_integrated.py --quick-test --epochs 1
    goto end
)

if "%choice%"=="4" (
    echo.
    echo Extracting replays from downloaded ZIPs...
    cd /d "%~dp0..\tools"
    python replay_lifecycle_manager.py --extract
    goto end
)

if "%choice%"=="5" (
    echo.
    echo Starting monitoring dashboard...
    cd /d "%~dp0..\monitoring"
    call start_mobile_monitoring.bat
    goto end
)

if "%choice%"=="0" (
    echo Goodbye!
    goto end
)

echo Invalid choice!

:end
pause
