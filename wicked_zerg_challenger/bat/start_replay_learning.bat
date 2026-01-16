@echo off
chcp 65001 > nul
REM 리플레이 학습 시작 배치 스크립트

echo ======================================================================
echo Replay Learning - 리플레이 학습 시작
echo ======================================================================
echo.

REM CRITICAL: Change to scripts directory
cd /d "%~dp0\..\local_training\scripts"
set PYTHONPATH=%CD%\..\..

echo [INFO] Current directory: %CD%
echo [INFO] Starting replay learning...
echo.
echo [NOTE] This will process replays from D:\replays\replays
echo [NOTE] Each replay will be analyzed 5 times for comprehensive learning
echo [NOTE] Progress will be shown in real-time
echo.

python replay_build_order_learner.py

echo.
echo ======================================================================
echo Replay Learning Complete
echo ======================================================================
echo.

pause
