@echo off
REM 전체 프로젝트 한글 인코딩 문제 수정 배치 파일

echo.
echo ================================
echo 전체 파일 인코딩 수정
echo ================================
echo.

cd /d "%~dp0.."

echo [STEP 1] 프로젝트 루트로 이동...
cd /d "%~dp0.."

echo [STEP 2] 모든 Python 파일 검사 및 수정 중...
echo.

REM 주요 디렉토리의 Python 파일들 수정
for /r %%f in (*.py) do (
    python scripts\fix_encoding.py "%%f" 2>nul
)

echo.
echo [STEP 3] Syntax 검증 중...
python -m py_compile local_training\main_integrated.py 2>nul && echo OK: main_integrated.py || echo ERROR: main_integrated.py

echo.
echo ================================
echo 인코딩 수정 완료
echo ================================
echo.

pause
