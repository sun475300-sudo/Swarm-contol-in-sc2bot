@echo off
REM NumPy 버전 불일치 해결 스크립트
REM Fix NumPy version mismatch for Python 3.10

echo.
echo ================================
echo NUMPY VERSION FIX
echo ================================
echo.

cd /d D:\wicked_zerg_challenger

echo [STEP 1] Activating virtual environment...
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found!
    echo [INFO] Please create virtual environment first: python -m venv .venv
    pause
    exit /b 1
)

echo [STEP 2] Checking Python version...
python --version

echo [STEP 3] Uninstalling NumPy...
pip uninstall numpy -y

echo [STEP 4] Clearing pip cache...
pip cache purge

echo [STEP 5] Reinstalling NumPy (Python 3.10 compatible)...
pip install "numpy>=1.20.0,<2.0.0" --no-cache-dir

if errorlevel 1 (
    echo [ERROR] NumPy installation failed!
    pause
    exit /b 1
)

echo [STEP 6] Verifying installation...
python -c "import numpy; print(f'NumPy {numpy.__version__} - OK')"

if errorlevel 1 (
    echo [ERROR] NumPy import test failed!
    pause
    exit /b 1
)

echo.
echo ================================
echo NUMPY FIX COMPLETE
echo ================================
echo.
echo [INFO] You can now run: bat\start_game_training.bat
echo.

pause
