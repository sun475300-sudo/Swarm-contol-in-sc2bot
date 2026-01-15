@echo off
REM Neural Network Model Training - Continuous Training Mode
REM 게임 실행하여 신경망 모델 생성 시작 (연속 실행 모드)

REM CRITICAL: Ensure script runs from project root regardless of current directory
cd /d "%~dp0.."

chcp 65001 > nul
setlocal

echo.
echo ================================
echo NEURAL NETWORK MODEL TRAINING (CONTINUOUS)
echo ================================
echo.
echo This will start continuous StarCraft II games and train the neural network model.
echo Model will be saved to: local_training/models/zerg_net_model.pt
echo.
echo Games will run continuously without stopping.
echo Press Ctrl+C to stop training.
echo.

REM Check if StarCraft II is available
python -c "import sys; sys.path.insert(0, 'wicked_zerg_challenger'); from sc2 import run_game, maps, Race, Difficulty; print('[OK] StarCraft II API available')" 2>nul || (
    echo [WARNING] StarCraft II API may not be available
    echo [INFO] Continuing anyway...
)

echo.
echo [INFO] Training Configuration:
echo   - 15-dimensional state vector (Self 5 + Enemy 10)
echo   - REINFORCE algorithm for policy learning
echo   - Model auto-saves after each game
echo   - Training enabled: train_mode=True
echo   - Continuous training: Games run continuously
echo   - Build order improvements: Natural expansion, gas, spawning pool
echo.

echo [INFO] Starting continuous training...
echo [INFO] Game windows will open - you can watch the training in real-time!
echo [INFO] Press Ctrl+C to stop training
echo.

cd wicked_zerg_challenger

REM Clear Python cache to ensure latest code is used
echo [INFO] Clearing Python cache...
if exist __pycache__ (
    rmdir /s /q __pycache__
    echo [OK] Python cache cleared
)
del /q *.pyc 2>nul
echo.

REM Check if --LadderServer flag is provided
set LADDER_MODE=0
if "%1"=="--LadderServer" set LADDER_MODE=1

if %LADDER_MODE%==1 (
    echo [INFO] Connecting to AI Arena server...
    echo [INFO] Training will run on ladder server
    python run_with_training.py --LadderServer
) else (
    echo [INFO] Running local training (no server connection)
    echo [INFO] To connect to server, run: start_model_training.bat --LadderServer
    echo.
    REM Run training script (will loop continuously)
    python run_with_training.py
)

echo.
echo ================================
echo TRAINING STOPPED
echo ================================
echo.
echo Model saved to: local_training/models/zerg_net_model.pt
echo You can now use this trained model in future games!
echo.

pause
endlocal