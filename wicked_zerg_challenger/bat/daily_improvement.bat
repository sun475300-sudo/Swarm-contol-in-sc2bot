@echo off
chcp 65001 > nul
REM 일일 개선 작업 자동화 스크립트
REM Windows 배치 파일에서 UTF-8 인코딩 사용

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
if not exist "tools" (
    echo [ERROR] tools directory not found. Current directory: %CD%
    exit /b 1
)
set PYTHONPATH=%CD%

echo ======================================================================
echo 일일 개선 작업 자동화
echo ======================================================================
echo 작업 시작 시간: %DATE% %TIME%
echo.

REM 1. 지속적인 개선 시스템 실행
echo [1/3] 지속적인 개선 시스템 실행 중...
if exist "tools\continuous_improvement_system.py" (
    python tools\continuous_improvement_system.py
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] 지속적인 개선 시스템 실행 중 오류 발생
    )
) else (
    echo [WARNING] tools\continuous_improvement_system.py not found
)

echo.

REM 2. 자동 에러 수정 도구 실행 (자동 에러 수정 도구 - 필요한 경우에만 실행)
echo [2/3] 자동 에러 수정 도구 실행 중...
if exist "tools\auto_error_fixer.py" (
    python tools\auto_error_fixer.py --all
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] 자동 에러 수정 도구 실행 중 오류 발생
    )
) else (
    echo [WARNING] tools\auto_error_fixer.py not found
)

echo.

REM 3. 코드 품질 개선 도구 실행
echo [3/3] 코드 품질 개선 도구 실행 중...
if exist "tools\code_quality_improver.py" (
    python tools\code_quality_improver.py --remove-unused --fix-style
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] 코드 품질 개선 도구 실행 중 오류 발생
    )
) else (
    echo [WARNING] tools\code_quality_improver.py not found
)

echo
echo ======================================================================
echo 일일 개선 작업 완료!
echo ======================================================================
echo.
echo 생성된 파일들:
echo   - CONTINUOUS_IMPROVEMENT_REPORT.md
echo   - logs/improvement_log.json
echo.

REM 로그 파일에 기록
if not exist "logs" mkdir logs
echo %DATE% %TIME% - Daily improvement completed >> logs\daily_improvement.log
