@echo off
REM Fix replay learning issues: Clear cache, upgrade NumPy, clear crash log

echo ======================================================================
echo  FIXING REPLAY LEARNING ISSUES
echo ======================================================================
echo.

echo [1/4] Clearing Python cache...
for /d /r "local_training" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
echo   [OK] Python cache cleared

echo.
echo [2/4] Upgrading NumPy...
pip install "numpy>=2.0.0" --upgrade
if %ERRORLEVEL% EQU 0 (
    echo   [OK] NumPy upgraded
) else (
    echo   [WARNING] NumPy upgrade failed - check manually
)

echo.
echo [3/4] Clearing crash_log.json in_progress entries...
python -c "import json; from pathlib import Path; p = Path('D:/replays/replays/crash_log.json'); d = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'in_progress': {}, 'crash_count': {}, 'bad_replays': []}; old_count = len(d.get('in_progress', {})); d['in_progress'] = {}; p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf-8') if p.exists() else None; print(f'  Cleared {old_count} in_progress entries')" 2>nul || echo   [WARNING] Failed to clear crash_log.json

echo.
echo [4/4] Verifying cleanup...
python tools\check_crash_log.py 2>nul || echo   [WARNING] check_crash_log.py may not be available

echo.
echo ======================================================================
echo  FIX COMPLETE
echo ======================================================================
echo.
echo Next step: Run bat\start_replay_learning.bat
echo.
pause
