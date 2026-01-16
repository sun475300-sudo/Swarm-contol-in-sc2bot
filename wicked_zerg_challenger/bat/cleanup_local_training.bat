@echo off
chcp 65001 > nul
REM 로컬 학습 폴더 정리 배치 스크립트

echo ======================================================================
echo Cleanup Local Training - 로컬 학습 폴더 정리
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo [INFO] Current directory: %CD%
echo [INFO] Starting cleanup of local_training folder...
echo.

REM Change to local_training directory
cd local_training

echo [STEP 1] Removing __pycache__ directories...
for /d /r %%d in (__pycache__) do @if exist "%%d" (
    echo   Removing: %%d
    rd /s /q "%%d" 2>nul
)

echo [STEP 2] Removing .pyc and .pyo files...
for /r %%f in (*.pyc *.pyo) do @if exist "%%f" (
    echo   Removing: %%f
    del /q "%%f" 2>nul
)

echo [STEP 3] Removing .bak files...
for /r %%f in (*.bak) do @if exist "%%f" (
    echo   Removing: %%f
    del /q "%%f" 2>nul
)

echo [STEP 4] Removing temporary files...
for /r %%f in (*.tmp *.temp *.swp *.swo *~) do @if exist "%%f" (
    echo   Removing: %%f
    del /q "%%f" 2>nul
)

echo.
echo ======================================================================
echo Cleanup Complete
echo ======================================================================
echo.

cd ..
pause
