@echo off
chcp 65001 > nul
REM 코드 스타일 통일화 배치 스크립트

echo ======================================================================
echo Code Style Unification - 코드 스타일 통일화
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo [INFO] Running code style unification...
echo [INFO] This will:
echo    - Normalize indentation to 4 spaces
echo    - Remove trailing whitespace
echo    - Ensure final newline
echo    - Fix import order (optional)
echo.

python tools/apply_code_style.py --all

echo.
echo ======================================================================
echo Code Style Unification Complete
echo ======================================================================
echo.

pause
