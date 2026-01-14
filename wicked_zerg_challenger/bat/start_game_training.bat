@echo off
REM 게임 학습 시작 스크립트
REM Game Training with Reinforcement Learning

REM CRITICAL: Ensure script runs from project root regardless of current directory
cd /d "%~dp0.."

echo.
echo ================================
echo GAME TRAINING - REINFORCEMENT LEARNING
echo ================================
echo.

cd /d "%~dp0..\local_training"

echo [STEP 1] Checking StarCraft II installation...
python -c "import sys; sys.path.insert(0, '.'); from sc2 import run_game, maps, Race, Difficulty, BotAI; print('[OK] StarCraft II API available')" 2>nul || (
    echo [WARNING] StarCraft II API may not be available
    echo [INFO] Continuing anyway...
)

echo.
echo [STEP 2] Starting game training...
echo [INFO] This will start StarCraft II and train the AI in real-time
echo [INFO] Training uses 15-dimensional state vector (Self 5 + Enemy 10)
echo [INFO] Rogue tactics (Baneling drops, Larva saving) are enabled
echo.

python main_integrated.py

echo.
echo ================================
echo GAME TRAINING COMPLETE
echo ================================
echo.

pause
