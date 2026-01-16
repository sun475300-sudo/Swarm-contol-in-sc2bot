@echo off
chcp 65001 > nul
REM 리플레이 데이터 비교분석 시작 배치 스크립트

echo ======================================================================
echo Replay Data Comparison Analysis - 리플레이 데이터 비교분석 시작
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo [INFO] Current directory: %CD%
echo [INFO] Starting replay comparison analysis...
echo.
echo [NOTE] This will compare:
echo    - Pro gamer replays (D:\replays\replays)
echo    - Training replays (local training data)
echo    - Generate detailed comparison reports
echo.

python tools/compare_pro_vs_training_replays.py

echo.
echo ======================================================================
echo Replay Comparison Analysis Complete
echo ======================================================================
echo [INFO] Comparison reports saved to local_training/comparison_reports/
echo.

pause
