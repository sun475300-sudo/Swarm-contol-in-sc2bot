@echo off
REM Wrapper to run the Python runtime check script and open the generated log
python "%~dp0runtime_check.py" %*
if %ERRORLEVEL% EQU 0 (
    echo Runtime check OK
) else (
    echo Runtime check found issues (exit code %ERRORLEVEL%). Check logs in ..\logs\runtime_check_*.log
)
pause
