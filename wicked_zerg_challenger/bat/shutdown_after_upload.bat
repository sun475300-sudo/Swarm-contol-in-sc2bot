@echo off
chcp 65001 > nul
REM 깃허브 업로드 확인 후 컴퓨터 종료 스크립트

echo ======================================================================
echo 깃허브 업로드 확인 및 컴퓨터 종료
echo ======================================================================
echo.

REM 깃허브 상태 확인
echo [1/4] 깃허브 상태 확인 중...
cd /d "%~dp0\.."
git status --short
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Git 상태 확인 실패
)

echo.
echo [2/4] 최근 커밋 확인...
git log --oneline -3

echo.
echo [3/4] 프로세스 정리 중...
REM Python 프로세스 종료 (선택적 - 안전하게)
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

REM SC2 프로세스 종료
taskkill /F /IM SC2_x64.exe /T 2>nul
timeout /t 2 /nobreak >nul

REM 기타 개발 도구 프로세스 종료
taskkill /F /IM code.exe /T 2>nul
taskkill /F /IM cursor.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo.
echo [4/4] 컴퓨터 종료 준비...
echo.
echo 10초 후 컴퓨터가 종료됩니다.
echo 취소하려면 Ctrl+C를 누르세요.
echo.
timeout /t 10 /nobreak

REM 컴퓨터 종료 (1분 후)
shutdown /s /t 60 /c "깃허브 업로드 완료. 1분 후 컴퓨터가 종료됩니다."

echo.
echo ======================================================================
echo 컴퓨터가 1분 후 종료됩니다.
echo 취소하려면: shutdown /a
echo ======================================================================
pause
