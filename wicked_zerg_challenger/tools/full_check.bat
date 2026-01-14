@echo off
chcp 65001 >nul
echo 전체 코드 품질 점검 시작...
echo.

python tools\code_quality_check.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 점검 실패!
    pause
    exit /b 1
)
echo.
echo 점검 완료!
pause
