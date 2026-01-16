@echo off
chcp 65001 > nul
REM 통합 API 게이트웨이 시작 배치 스크립트

echo ======================================================================
echo Unified API Gateway - 통합 모니터링 게이트웨이
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo [INFO] Starting Unified API Gateway...
echo [INFO] Gateway will proxy requests to:
echo    - Local server (port 8001) - for local training
echo    - Arena server (port 8002) - for arena battles
echo.

python -m uvicorn monitoring.unified_api_gateway:app --host 0.0.0.0 --port 8000

pause
