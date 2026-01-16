@echo off
chcp 65001 > nul
REM 불필요한 파일 정리 배치 스크립트

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 불필요한 파일 정리
echo ======================================================================
echo.

REM 확인 요청
echo [주의] 이 작업은 파일을 삭제합니다.
echo.
set /p CONFIRM="계속하시겠습니까? (yes/no): "
if /i not "%CONFIRM%"=="yes" (
    echo 작업이 취소되었습니다.
    pause
    exit /b 0
)

echo.
echo 백업 파일(.bak) 삭제 중...
for /r %%f in (*.bak) do (
    echo   삭제: %%f
    del /f /q "%%f"
)

echo.
echo 캐시 파일(.pyc, .pyo) 삭제 중...
for /r %%f in (*.pyc *.pyo) do (
    echo   삭제: %%f
    del /f /q "%%f"
)

echo.
echo __pycache__ 디렉토리 삭제 중...
for /d /r %%d in (__pycache__) do (
    echo   삭제: %%d
    rd /s /q "%%d"
)

echo.
echo ======================================================================
echo 불필요한 파일 정리 완료!
echo ======================================================================
echo.
pause
