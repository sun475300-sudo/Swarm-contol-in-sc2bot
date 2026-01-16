@echo off
chcp 65001 > nul
REM 로그 파일 정리 배치 스크립트

echo ======================================================================
echo Cleanup Log Files - 로그 파일 정리
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
if not exist "tools" (
    echo [ERROR] tools directory not found. Current directory: %CD%
    exit /b 1
)
set PYTHONPATH=%CD%

REM Verify Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH
    exit /b 1
)

echo [INFO] Current directory: %CD%
echo [INFO] Starting log cleanup...
echo.

REM Run cleanup script
if exist "tools\cleanup_logs.py" (
    python tools\cleanup_logs.py
) else (
    echo [ERROR] cleanup_logs.py not found
    exit /b 1
)

echo.
echo ======================================================================
echo Cleanup Complete
echo ======================================================================
echo.

pause
