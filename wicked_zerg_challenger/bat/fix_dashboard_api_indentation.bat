@echo off
chcp 65001 > nul
REM dashboard_api.py 들여쓰기 수정 스크립트

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo dashboard_api.py 들여쓰기 수정
echo ======================================================================
echo.

REM Python 스크립트로 들여쓰기 자동 수정
python -c "import re; content = open('monitoring/dashboard_api.py', 'r', encoding='utf-8', errors='replace').read(); lines = content.splitlines(); fixed = []; indent_level = 0; for line in lines: stripped = line.lstrip(); if stripped: indent = len(line) - len(stripped); if stripped.startswith(('def ', 'class ', 'async def ')): indent_level = indent // 4; fixed.append(' ' * (indent_level * 4) + stripped); elif stripped.startswith(('if ', 'elif ', 'else:', 'try:', 'except ', 'finally:', 'for ', 'while ', 'with ')): indent_level = indent // 4; fixed.append(' ' * (indent_level * 4) + stripped); elif stripped.startswith('return') or stripped.startswith('raise') or stripped.startswith('break') or stripped.startswith('continue'): fixed.append(' ' * (indent_level * 4) + stripped); else: fixed.append(' ' * (indent_level * 4) + stripped); else: fixed.append(''); open('monitoring/dashboard_api.py', 'w', encoding='utf-8').write('\n'.join(fixed))"

if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] 들여쓰기 자동 수정 실패 - 수동 수정 필요
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 들여쓰기 수정 완료!
echo.
echo 다음 명령으로 문법 확인:
echo   python -m py_compile monitoring/dashboard_api.py
echo.
pause
