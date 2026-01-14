@echo off
REM 리플레이 학습 시작 스크립트
REM Replay Build Order Learning System

REM CRITICAL: Ensure script runs from project root regardless of current directory
cd /d "%~dp0.."

echo.
echo ================================
echo REPLAY BUILD ORDER LEARNING
echo ================================
echo.

cd /d "%~dp0..\local_training\scripts"

echo [STEP 1] Checking replay directory...
if not exist "D:\replays\replays" (
    echo [WARNING] Replay directory not found: D:\replays\replays
    echo [INFO] Creating directory...
    mkdir "D:\replays\replays" 2>nul
)

echo [STEP 2] Starting replay build order learning...
set AUTO_COMMIT_AFTER_TRAINING=true
python replay_build_order_learner.py

echo.
echo [STEP 3] Auto committing changes to GitHub...
cd /d "%~dp0.."
python tools\auto_commit_after_training.py

echo.
echo ================================
echo REPLAY LEARNING COMPLETE
echo ================================
echo.

pause
