@echo off
REM 훈련 종료 후 자동 커밋 스크립트
REM Auto Commit After Training

REM CRITICAL: Ensure script runs from project root regardless of current directory
cd /d "%~dp0.."

echo.
echo ================================
echo AUTO COMMIT AFTER TRAINING
echo ================================
echo.

echo [INFO] Running auto commit script...
python tools\auto_commit_after_training.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Auto commit completed successfully
) else (
    echo.
    echo [WARNING] Auto commit failed - check output above
    echo [INFO] You may need to commit manually:
    echo   git add -A
    echo   git commit -m "Training completed"
    echo   git push origin main
)

echo.
pause
