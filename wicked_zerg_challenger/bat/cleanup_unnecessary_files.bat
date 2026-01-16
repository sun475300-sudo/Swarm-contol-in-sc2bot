@echo off
chcp 65001 > nul
REM 불필요한 파일 제거 배치 스크립트

echo ======================================================================
echo Cleanup Unnecessary Files - 불필요한 파일 제거
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
echo [INFO] Starting cleanup...
echo.

REM Run cleanup scripts
echo [STEP 1] Cleaning up redundant documentation...
if exist "tools\cleanup_unnecessary_files_auto.py" (
    python tools\cleanup_unnecessary_files_auto.py
)

echo.
echo [STEP 2] Cleaning up Korean documentation...
if exist "tools\cleanup_korean_docs.py" (
    python tools\cleanup_korean_docs.py
)

echo.
echo [STEP 3] Comprehensive cleanup...
if exist "tools\comprehensive_cleanup.py" (
    python tools\comprehensive_cleanup.py
)

echo.
echo ======================================================================
echo Cleanup Complete
echo ======================================================================
echo.

pause
