@echo off
chcp 65001 > nul
REM SC2 AI Arena 대시보드 시작 배치 스크립트

echo ======================================================================
echo SC2 AI Arena 대시보드 시작
echo ======================================================================
echo.

REM CRITICAL: Change to monitoring directory
cd /d "%~dp0\..\monitoring"
set PYTHONPATH=%CD%\..

echo [INFO] 작업 디렉토리: %CD%
echo [INFO] Python 경로: %PYTHONPATH%
echo.

REM 환경 변수 설정 (기본값)
if "%ARENA_API_URL%"=="" set ARENA_API_URL=https://aiarena.net/api/v2
if "%ARENA_BOT_NAME%"=="" set ARENA_BOT_NAME=WickedZerg
if "%ARENA_DASHBOARD_ENABLED%"=="" set ARENA_DASHBOARD_ENABLED=1

echo [설정]
echo   ARENA_API_URL: %ARENA_API_URL%
echo   ARENA_BOT_NAME: %ARENA_BOT_NAME%
echo   ARENA_DASHBOARD_ENABLED: %ARENA_DASHBOARD_ENABLED%
echo.

echo [INFO] Arena 대시보드 시작 중...
echo [INFO] 포트: 8002
echo [INFO] API 문서: http://localhost:8002/docs
echo.

python arena_dashboard_api.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 대시보드 시작 실패
    echo.
    echo [해결 방법]
    echo   1. Python 패키지 설치: pip install fastapi uvicorn requests
    echo   2. 환경 변수 확인: ARENA_API_URL, ARENA_BOT_NAME
    echo   3. 포트 8002가 사용 중인지 확인
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Arena 대시보드가 종료되었습니다.
echo ======================================================================
pause
