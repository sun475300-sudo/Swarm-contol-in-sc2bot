@echo off
REM Clear learning state files to force replay analysis
REM This script deletes learning status and stats files to reset the learning state

echo ======================================================================
echo  CLEARING LEARNING STATE FILES
echo ======================================================================
echo.
echo This will delete:
echo   1. learning_status.json (if exists)
echo   2. All .json files in stats/ directory
echo   3. crash_log.json in_progress entries (keeps crash counts)
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo [1/4] Checking for learning_status.json...
if exist "D:\replays\replays\learning_status.json" (
    del /q "D:\replays\replays\learning_status.json"
    echo   Deleted: D:\replays\replays\learning_status.json
) else (
    echo   Not found: D:\replays\replays\learning_status.json (may not exist)
)

if exist "local_training\scripts\learning_status.json" (
    del /q "local_training\scripts\learning_status.json"
    echo   Deleted: local_training\scripts\learning_status.json
) else (
    echo   Not found: local_training\scripts\learning_status.json (may not exist)
)

if exist "local_training\learning_status.json" (
    del /q "local_training\learning_status.json"
    echo   Deleted: local_training\learning_status.json
) else (
    echo   Not found: local_training\learning_status.json (may not exist)
)

echo.
echo [2/4] Clearing stats/*.json files...
if exist "stats\*.json" (
    del /q "stats\*.json"
    echo   Deleted all .json files in stats/ directory
) else (
    echo   No .json files found in stats/ directory
)

echo.
echo [3/4] Clearing stale crash_log.json entries...
python -c "import json; from pathlib import Path; p = Path('D:/replays/replays/crash_log.json'); d = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'in_progress': {}, 'crash_count': {}, 'bad_replays': []}; old_count = len(d.get('in_progress', {})); d['in_progress'] = {}; p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf-8') if p.exists() else None; print(f'  Cleared {old_count} in_progress entries from crash_log.json')" 2>nul || echo   Note: crash_log.json may not exist or Python may not be available

echo.
echo [4/4] Verifying cleanup...
python tools\check_crash_log.py 2>nul || echo   Note: check_crash_log.py may not be available

echo.
echo ======================================================================
echo  STATE CLEARED - Ready for replay analysis
echo ======================================================================
echo.
echo Next step: Run bat\start_replay_learning.bat
echo.
pause
