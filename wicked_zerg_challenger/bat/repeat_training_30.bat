@echo off
REM Repeat integrated_pipeline.py 30 times
REM Training rounds with automatic archiving

REM CRITICAL: Ensure script runs from project root regardless of current directory
cd /d "%~dp0.."

cd /d "%~dp0.."

echo.
echo ================================================================================
echo STARTING 30-ROUND TRAINING CYCLE
echo ================================================================================
echo Start time: %date% %time%
echo.

for /L %%i in (1,1,30) do (
    echo.
    echo ================================================================================
    echo TRAINING ROUND %%i / 30
    echo ================================================================================
    echo Time: %date% %time%
    echo.
    
    python tools\integrated_pipeline.py
    
    if errorlevel 1 (
        echo ERROR: Training round %%i failed!
        echo Stopping cycle...
        pause
        exit /b 1
    )
    
    echo Round %%i completed successfully
    echo.
)

echo.
echo ================================================================================
echo ALL 30 TRAINING ROUNDS COMPLETED!
echo ================================================================================
echo End time: %date% %time%
echo Results saved to: D:\backup\replay_archive\training_*
echo.

pause
