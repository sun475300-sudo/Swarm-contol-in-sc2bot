@echo off
REM Force clear crash_log.json in_progress entries
REM This script directly clears the in_progress section to force replay analysis

echo ======================================================================
echo  FORCE CLEAR CRASH LOG - IN PROGRESS ENTRIES
echo ======================================================================
echo.
echo This will clear ALL in_progress entries from crash_log.json
echo This forces all replays to be analyzed immediately.
echo.
pause

echo.
echo [1/2] Clearing crash_log.json in_progress entries...
python -c "import json; from pathlib import Path; p = Path('D:/replays/replays/crash_log.json'); d = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'in_progress': {}, 'crash_count': {}, 'bad_replays': []}; old_count = len(d.get('in_progress', {})); d['in_progress'] = {}; p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf-8'); print(f'  Cleared {old_count} in_progress entries from crash_log.json')" 2>nul || (
    echo   [WARNING] Python script failed, trying manual edit...
    echo   Please manually edit D:\replays\replays\crash_log.json
    echo   Set "in_progress": {} in the file
)

echo.
echo [2/2] Verifying crash_log.json...
if exist "D:\replays\replays\crash_log.json" (
    python -c "import json; from pathlib import Path; p = Path('D:/replays/replays/crash_log.json'); d = json.loads(p.read_text(encoding='utf-8')); print(f'  in_progress entries: {len(d.get(\"in_progress\", {}))}'); print(f'  crash_count entries: {len(d.get(\"crash_count\", {}))}'); print(f'  bad_replays: {len(d.get(\"bad_replays\", []))}')" 2>nul || echo   [WARNING] Could not verify crash_log.json
) else (
    echo   [INFO] crash_log.json does not exist (will be created on first run)
)

echo.
echo ======================================================================
echo  CRASH LOG CLEARED - Ready for replay analysis
echo ======================================================================
echo.
echo Next step: Run bat\start_replay_learning.bat
echo.
pause
