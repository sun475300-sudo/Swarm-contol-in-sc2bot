@echo off
chcp 65001 > nul
REM 로컬 트레이닝 시작 배치 스크립트

echo ======================================================================
echo Local Training - 로컬 트레이닝 시작
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo [INFO] Current directory: %CD%
echo [INFO] Starting local training with integrated system...
echo.
echo [NOTE] Training Configuration:
echo    - Single instance mode (1 game at a time)
echo    - Visual mode (game window visible)
echo    - Local monitoring server will start automatically
echo    - Neural network training enabled
echo.

REM Set environment variables
set INSTANCE_ID=0
set NUM_INSTANCES=1
set SINGLE_GAME_MODE=true
set SHOW_WINDOW=true
set HEADLESS_MODE=false
set DISABLE_DASHBOARD=false
set TORCH_NUM_THREADS=12

REM Optional: Set max games (0 = infinite)
if "%MAX_GAMES%"=="" set MAX_GAMES=0

echo [INFO] Environment variables set:
echo    - INSTANCE_ID=%INSTANCE_ID%
echo    - NUM_INSTANCES=%NUM_INSTANCES%
echo    - SINGLE_GAME_MODE=%SINGLE_GAME_MODE%
echo    - SHOW_WINDOW=%SHOW_WINDOW%
echo    - MAX_GAMES=%MAX_GAMES%
echo.

REM Check if SC2PATH is set
if "%SC2PATH%"=="" (
    echo [WARNING] SC2PATH not set. Will attempt to auto-detect...
) else (
    echo [INFO] SC2PATH: %SC2PATH%
)

echo.
echo [INFO] Starting training...
echo.

REM Start training with integrated system
REM Option 1: Use integrated training system (main_integrated.py)
REM Option 2: Use run_with_training.py (with monitoring server integration)
REM 
REM Note: main_integrated.py has some indentation issues that need fixing
REM For now, using run_with_training.py which includes monitoring server

REM Option 1: Integrated system (may need indentation fixes)
REM python local_training/main_integrated.py

REM Option 2: Training with monitoring (recommended)
python run_with_training.py

echo.
echo ======================================================================
echo Training Session Ended
echo ======================================================================
echo.

pause
