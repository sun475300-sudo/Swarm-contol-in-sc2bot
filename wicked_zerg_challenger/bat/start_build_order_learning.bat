@echo off
chcp 65001 > nul
REM 빌드오더 학습 시작 배치 스크립트

echo ======================================================================
echo Build Order Learning - 빌드오더 학습 시작
echo ======================================================================
echo.

REM CRITICAL: Change to scripts directory
cd /d "%~dp0\..\local_training\scripts"
set PYTHONPATH=%CD%\..\..

echo [INFO] Current directory: %CD%
echo [INFO] Starting build order learning from replays...
echo.
echo [NOTE] This will process replays from D:\replays\replays
echo [NOTE] Each replay will be analyzed for build orders
echo [NOTE] Learned parameters will be saved to learned_build_orders.json
echo.

REM Check if sc2reader is installed
python -c "import sc2reader" 2>nul
if errorlevel 1 (
    echo [WARNING] sc2reader not found. Installing...
    pip install sc2reader
    echo.
)

python replay_build_order_learner.py

echo.
echo ======================================================================
echo Build Order Learning Complete
echo ======================================================================
echo [INFO] Results saved to learned_build_orders.json
echo.

pause
