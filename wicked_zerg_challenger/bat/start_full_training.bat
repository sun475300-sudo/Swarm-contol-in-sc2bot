@echo off
REM 전체 학습 파이프라인 시작 스크립트
REM Full Training Pipeline: Replay Learning + Game Training

echo.
echo ================================
echo FULL TRAINING PIPELINE
echo ================================
echo.

setlocal enabledelayedexpansion

echo [STEP 1] Replay Extraction and Filtering...
cd /d "%~dp0..\tools"
python replay_lifecycle_manager.py --extract
if errorlevel 1 (
    echo [ERROR] Replay extraction failed!
    pause
    exit /b 1
)

echo.
echo [STEP 2] Replay Build Order Learning...
cd /d "%~dp0..\local_training\scripts"
python replay_build_order_learner.py
if errorlevel 1 (
    echo [ERROR] Replay learning failed!
    pause
    exit /b 1
)

echo.
echo [STEP 3] Game Training with Neural Network...
python main_integrated.py
if errorlevel 1 (
    echo [ERROR] Game training failed!
    pause
    exit /b 1
)

echo.
echo [STEP 4] Cleanup and Archive...
cd /d "%~dp0..\tools"
python replay_lifecycle_manager.py --cleanup

echo.
echo [STEP 5] Auto committing changes to GitHub...
cd /d "%~dp0.."
python tools\auto_commit_after_training.py

echo.
echo ================================
echo FULL TRAINING PIPELINE COMPLETE
echo ================================
echo.

pause
