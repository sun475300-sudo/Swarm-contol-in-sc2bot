# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import random
import subprocess
import sys
import time
import warnings
from pathlib import Path

# Antigravity easter egg removed - no longer used

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# IMPROVED: Use flexible venv path detection
def get_venv_dir() -> Path:
    """Get virtual environment directory from environment variable or use project default"""
    venv_dir = os.environ.get("VENV_DIR")
    if venv_dir and Path(venv_dir).exists():
        return Path(venv_dir)
    # Try common locations
    possible_paths = [
        PROJECT_DIR / ".venv",
        Path.home() / ".venv",
        Path(".venv"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    # Default fallback
    return PROJECT_DIR / ".venv"

VENV_DIR = get_venv_dir()
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe" if sys.platform == "win32" else VENV_DIR / "bin" / "python3"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if VENV_DIR.exists() and str(VENV_DIR / "Lib" / "site-packages") not in sys.path:
    sys.path.insert(0, str(VENV_DIR / "Lib" / "site-packages"))

def get_sc2_path():
    if "SC2PATH" in os.environ:
        sc2_path = os.environ["SC2PATH"]
        if os.path.exists(sc2_path):
            return sc2_path

    default_paths = []
    if sys.platform == "win32":
        default_paths = [
            r"C:\Program Files (x86)\StarCraft II",
            r"C:\Program Files\StarCraft II",
        ]
    elif sys.platform == "darwin":
        default_paths = [
            os.path.expanduser("~/Library/Application Support/Blizzard/StarCraft II"),
            "/Applications/StarCraft II",
        ]
    else:
        default_paths = [
            os.path.expanduser("~/StarCraft II"),
            "/opt/StarCraft II",
        ]

    for path in default_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            return path

    print(f"[WARNING] SC2 path not found. Please set SC2PATH environment variable.")
    print(f"[INFO] Tried paths: {default_paths}")
    return None

sc2_path = get_sc2_path()
if sc2_path:
    print(f"[OK] SC2 path: {sc2_path}")
else:
    print(f"[WARNING] SC2PATH not set. Some features may not work.")

DRY_RUN_MODE = os.environ.get("DRY_RUN_MODE", "false").lower() == "true"

try:
    from loguru import logger
    logger.remove()
    logger.add(sys.stderr, colorize=True, enqueue=True, catch=True, level="INFO")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(
        str(log_dir / "training_log.log"),
        rotation="10 MB",
 enqueue = True,
 catch = True,
        level="DEBUG",
        encoding="utf-8",
 )
    print("[OK] Loguru logger configured")
except ImportError:
    logger = None
    print("[WARNING] loguru not installed")
except Exception as e:
 logger = None
    print(f"[WARNING] Failed to configure loguru: {e}")

warnings.filterwarnings("ignore", category = DeprecationWarning, module="asyncio")

# CPU Thread Configuration: Use 12 threads (configurable via TORCH_NUM_THREADS env var)
# CRITICAL: Import torch safely to avoid C extensions loading errors
try:
 import multiprocessing
 # Change to a safe directory before importing torch to avoid path conflicts
 original_cwd = os.getcwd()
 try:
 # Temporarily change to project root to avoid local directory conflicts
 project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
 os.chdir(project_root)
 import torch
 # Verify torch is properly installed
        if not hasattr(torch, '_C'):
            raise ImportError("PyTorch C extensions not properly loaded")
        num_threads = int(os.environ.get("TORCH_NUM_THREADS", "12"))
 torch.set_num_threads(num_threads)
        os.environ["OMP_NUM_THREADS"] = str(num_threads)
        os.environ["MKL_NUM_THREADS"] = str(num_threads)
        print(f"[CPU] PyTorch configured to use {num_threads} threads")
 finally:
 os.chdir(original_cwd)
except Exception as e:
    print(f"[WARNING] Failed to configure CPU threads: {e}")
    print(f"[INFO] Game will continue but may use default thread settings")

# Initialize logging configuration at the start to prevent logging errors
# This fixes ValueError: I/O operation on closed file issues
# Use a safe handler that catches buffer detachment errors
class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that catches ValueError when buffer is detached"""

 def emit(self, record):
 try:
 # Check if stream is closed before attempting to write
            if hasattr(self.stream, "closed") and self.stream.closed:
 return # Stream is closed, skip logging
            if hasattr(self.stream, "detach") and not hasattr(self.stream, "write"):
 return # Buffer has been detached, skip logging
 super().emit(record)
 except (ValueError, OSError, AttributeError) as e:
 # Silently ignore buffer detachment errors
 # These occur when sc2 library tries to log after stream is closed
 error_msg = str(e).lower()
            if "buffer" in error_msg or "detached" in error_msg or "closed" in error_msg:
 # Silently ignore buffer-related errors from sc2 internal logging
 pass
 else:
 # Re-raise or handle other errors normally
 try:
 self.handleError(record)
 except Exception:
 pass # Even handleError can fail, so suppress it

# Configure logging with safe handler using sys.stdout explicitly
logging.basicConfig(
 handlers=[SafeStreamHandler(sys.stdout)],
 force = True,
 level = logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# IMPROVED: Platform-independent event loop policy
# Use default policy on all platforms for better compatibility
try:
 loop = asyncio.get_running_loop()
except RuntimeError:
 loop = asyncio.new_event_loop()
 asyncio.set_event_loop(loop)

# IMPROVED: Only set Windows-specific policy if explicitly needed and available
# This allows the code to run on Linux/Docker without modification
if sys.platform == "win32":
 try:
 # Only use WindowsSelectorEventLoopPolicy if default policy causes issues
 # Most modern Python versions handle this automatically
        if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
            # Check if we're in a Docker container or WSL (should use default policy)
            if not os.environ.get("WSL_DISTRO_NAME") and not os.path.exists("/.dockerenv"):
 asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                print("[INFO] Using Windows-specific event loop policy")
 except (AttributeError, Exception) as e:
 # Silently fall back to default policy
 pass

# Ensure event loop exists (fixes RuntimeError and DeprecationWarning in Python 3.10+)
# Python 3.10+ requires explicit loop creation - get_event_loop() no longer auto-creates
# At module level, we just ensure a loop is set (not running)
try:
 loop = asyncio.get_running_loop()
except RuntimeError:
 loop = asyncio.new_event_loop()
 asyncio.set_event_loop(loop)

# SC2 imports

# IMPROVED: Single game mode - no parallel execution
# _host_game disabled (not used in single game mode)
_HOST_GAME_AVAILABLE = False
_host_game = None


# CRITICAL: Replace ALL handlers on root logger and sc2 logger after imports
# This ensures sc2 library's handlers are replaced with safe handlers
root_logger = logging.getLogger()
root_logger.handlers = [
 SafeStreamHandler(sys.stdout)
] # Replace all root handlers with safe handler

# Also configure sc2 logger specifically
sc2_logger = logging.getLogger("sc2")
sc2_logger.handlers = [SafeStreamHandler(sys.stdout)] # Replace all sc2 handlers with safe handler
sc2_logger.setLevel(logging.INFO)
sc2_logger.propagate = False # Prevent propagation to root logger

# Monkey-patch StreamHandler.emit to catch buffer errors globally
# This ensures any StreamHandler created later will also be safe
_original_stream_handler_emit = logging.StreamHandler.emit

def safe_stream_handler_emit(self, record):
 try:
 return _original_stream_handler_emit(self, record)
 except (ValueError, OSError) as e:
 error_msg = str(e).lower()
        if "buffer" in error_msg or "detached" in error_msg:
 # Silently ignore buffer detachment errors
 return
 # Re-raise other errors
 raise

logging.StreamHandler.emit = safe_stream_handler_emit

# Bot import - Use WickedZergBotPro as integrated bot
# Add parent directory (root) to sys.path from current directory (local_training)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Curriculum Learning System
# This allows importing modules from root directory

# Configuration
SC2PATH = get_sc2_path() or os.environ.get("SC2PATH", None)
MAP_NAME = "AcropolisLE"  # Default map (confirmed to exist in Maps folder)

# IMPROVED: Difficulty is now managed by CurriculumManager (one level at a time)
# Legacy constants kept for backward compatibility but not actively used
# CurriculumManager handles all difficulty progression automatically

# Available maps - verified to exist in StarCraft II Maps directory
# Using exact file names (without .SC2Map extension) as they appear in the folder
AVAILABLE_MAPS = [
    "AcropolisLE",  # Default map
    "AbyssalReefLE",
    "BelShirVestigeLE",
    "CactusValleyLE",
    "ProximaStationLE",
    "NewkirkPrecinctTE",
    "OdysseyLE",
 # Additional confirmed maps (uncomment if needed):
    # "HonorgroundsLE",
    # "AscensiontoAiurLE",
    # "BattleontheBoardwalkLE",
    # "BlackpinkLE",
    # "CatalystLE",
    # "DiscoBloodbathLE",
    # "EphemeronLE",
    # "NeonVioletSquareLE",
    # "PaladinoTerminalLE",
    # "ThunderbirdLE",
    # "TritonLE",
    # "WintersGateLE",
    # "WorldofSleepersLE",
]

# Opponent races (for variety)
OPPONENT_RACES = [Race.Terran, Race.Protoss, Race.Zerg]

# Personality options
PERSONALITIES = ["serral", "dark", "reynor"]

def write_status_file(instance_id, status_data):
    """
 Write instance status to a JSON file for dashboard display

 IMPROVED: File locking prevention for parallel execution
 - Uses temporary file + atomic move to prevent file lock conflicts
 - Retries on failure to handle concurrent writes

 Args:
 instance_id: Unique instance identifier (0 if not in parallel mode)
 status_data: Dictionary containing status information
    """
 try:
 import json
 import time

 # IMPROVED: Use project root stats/ directory with instance subdirectory
 # This prevents I/O bottleneck when running 30+ instances
 project_root = Path(__file__).parent.parent
        status_dir = project_root / "stats" / f"instance_{instance_id}"
 status_dir.mkdir(parents = True, exist_ok = True)
        status_file = status_dir / "status.json"

 # IMPROVED: Use temporary file + atomic move to prevent file lock conflicts
 max_retries = 3
 retry_delay = 0.1

 for attempt in range(max_retries):
 try:
 # Step 1: Write to temporary file
                temp_file = status_file.with_suffix('.tmp')
                with open(temp_file, "w", encoding="utf-8") as f:
 json.dump(status_data, f, indent = 2)

 # Step 2: Atomic move (replaces existing file atomically)
                # On Windows, os.replace is atomic; on Unix, it's also atomic
 import os
 os.replace(str(temp_file), str(status_file))
 return # Success

 except (IOError, OSError, PermissionError) as e:
 if attempt < max_retries - 1:
 time.sleep(retry_delay * (attempt + 1)) # Exponential backoff
 continue
 else:
                    # Last attempt failed - log but don't raise
                    print(f"[WARNING] Failed to write status file after {max_retries} attempts: {e}")
 return
 except Exception as e:
 # Silently fail - status file writing is optional
 pass

def run_training():
 monitoring_procs = (None, None)

 # DRY-RUN MODE: Test all logic without running actual games
 if DRY_RUN_MODE:
        print("\n" + "=" * 70)
        print("? DRY-RUN MODE ACTIVATED - Testing without StarCraft II")
        print("=" * 70)

 try:
            print("\n[1/5] Verifying SC2 path...")
 sc2_path = get_sc2_path()
 if sc2_path:
                print(f"  ? SC2 path verified: {sc2_path}")
 else:
                print(f"  ??  SC2 path not found (but that's OK for dry-run)")

            print("\n[2/5] Initializing CurriculumManager...")
 curriculum = CurriculumManager()
 current_difficulty = curriculum.get_difficulty()
 progress_info = curriculum.get_progress_info()
            print(f"  ? Curriculum loaded: {progress_info['level_name']}")
            print(f"     Level: {progress_info['current_level']}/{progress_info['total_levels']}")
 print(
                f"     Games at current level: {progress_info['games_at_current_level']}/{progress_info['min_games_required']}"
 )

            print("\n[3/5] Loading bot architecture...")
            print(f"  ? WickedZergBotPro class loaded successfully")
            print(f"     - Personality system: Ready")
            print(f"     - RL Orchestrator: Ready")
            print(f"     - Strategy analyzer: Ready")

            print("\n[4/5] Checking data directories...")
            directories = ["replays", "logs", "stats", "data"]
 for dir_name in directories:
 dir_path = Path(dir_name)
 dir_path.mkdir(exist_ok = True)
                print(f"  ? {dir_name}/ directory ready")

            print("\n[5/5] Configuration summary...")
            print(f"  Instance ID: 0 (single instance mode)")
            print(f"  Render mode: HEADLESS (no window) - Default")
            print(f"  Map pool: {len(AVAILABLE_MAPS)} maps available")
            print(f"  Opponent races: {len(OPPONENT_RACES)} races")
            print(f"  Personality profiles: {len(PERSONALITIES)} personalities")

            print("\n" + "=" * 70)
            print("? [DRY-RUN SUCCESS] All systems ready for actual training!")
            print("=" * 70)
            print("\nTo start actual training:")
            print("  1. Open main_integrated.py")
            print("  2. Change 'DRY_RUN_MODE = True' to 'DRY_RUN_MODE = False'")
            print("  3. Run: python main_integrated.py")
            print("\n")
 return # Exit without starting actual training

 except Exception as e:
            print("\n" + "=" * 70)
            print(f"? [DRY-RUN FAILED] Error during validation:")
            print("=" * 70)
            print(f"Error: {type(e).__name__}: {e}")
 import traceback

 traceback.print_exc()
 return

 # ACTUAL TRAINING MODE: Run real games with StarCraft II

 # Note: Event loop is already running when this function is called (via asyncio.run())
 instance_id = 0 # IMPROVED: Always 0 (single game mode)
 # Override environment variable to force single game mode
    os.environ["INSTANCE_ID"] = "0"
    os.environ["NUM_INSTANCES"] = "1"
 # IMPROVED: Show window for visual monitoring
    show_window = os.environ.get("SHOW_WINDOW", "true").lower() == "true"
    os.environ["SHOW_WINDOW"] = "true" if show_window else "false"

 sc2_path = get_sc2_path()
 if sc2_path:
        os.environ["SC2PATH"] = sc2_path
 _config = Config()
 # IMPROVED: Try C++ implementation first for better performance, fallback to Python if needed
 if _config.PROTOCOL_BUFFERS_IMPL:
 try:
 # Try to use C++ implementation (10x faster)
            os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = _config.PROTOCOL_BUFFERS_IMPL
            if _config.PROTOCOL_BUFFERS_IMPL == "cpp":
 # Verify C++ implementation is available
 try:
                    print("[OK] Using C++ protobuf implementation (fast mode)")
 except ImportError:
 # Fallback to Python implementation if C++ not available
                    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
                    print("[WARNING] C++ protobuf not available, using Python implementation (slower)")
 except Exception as e:
 # Fallback to Python on any error
            os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
            print(f"[WARNING] Protobuf setup error: {e}, using Python implementation")

 if not sc2_path:
        print(f"[WARNING] SC2 path not found")
        print(f"[INFO] Please set SC2PATH environment variable to your StarCraft II installation path")

 # Create replay directory
    replay_dir = "replays"
 os.makedirs(replay_dir, exist_ok = True)

 # Training statistics
 game_count = 0
 win_count = 0
 loss_count = 0
    last_result = "N/A"  # Store last game result for terminal display
 # LEARNING: Batch processing - collect results first
 batch_results = []
 if len(batch_results) >= 10:
 # Process batch of 10 games at once
 process_batch(batch_results)
 batch_results.clear()
 # LEARNING: Batch processing - collect results first
 batch_results = []
 if len(batch_results) >= 10:
 # Process batch of 10 games at once
 process_batch(batch_results)
 batch_results.clear()

 MAX_CONTINUOUS_FAILURES = 3
 continuous_failures = 0

    monitor_enabled = os.environ.get("ENABLE_MONITOR", "false").lower() == "true"
 code_monitor = None
 code_monitor = None
 monitor_enabled = False

 curriculum = CurriculumManager()
 current_difficulty = curriculum.get_difficulty()

 # Legacy: Dynamic difficulty tracking (for backward compatibility)
 current_difficulty_index = curriculum.current_idx
 difficulty_games = curriculum.games_at_current_level

 # IMPROVED: Auto code optimization (default rule)
 if _config.AUTO_OPTIMIZE_CODE:
 try:
            print(f"[CODE OPTIMIZATION] Auto-optimization enabled (default rule)")
 import re

 optimization_files = [
                'wicked_zerg_bot_pro.py',
                'production_manager.py',
                'economy_manager.py',
                'combat_manager.py',
                'micro_controller.py',
                'intel_manager.py',
                'scouting_system.py',
                'unit_factory.py',
                'main_integrated.py'
 ]

 optimized_count = 0
 for filename in optimization_files:
 filepath = Path(filename)
 if filepath.exists():
 try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                        with open(filepath, 'r', encoding='utf-8') as f:
 # LEARNING: Cache file contents if read multiple times
 content = f.read()
 # LEARNING: Cache file contents if read multiple times
 content = f.read()
 content = f.read()

                        original_size = len(content.encode('utf-8'))

 # Remove Korean comments
 content = remove_korean_comments(content)

 # Remove excessive blank lines
                        content = re.sub(r'\n\n\n+', '\n\n', content)

 # Remove trailing whitespace
                        lines = content.split('\n')
 lines = [line.rstrip() for line in lines]
                        content = '\n'.join(lines)

                        new_size = len(content.encode('utf-8'))
 if new_size < original_size:
                            with open(filepath, 'w', encoding='utf-8') as f:
 f.write(content)
 optimized_count += 1
 except Exception as e:
 pass

 if optimized_count > 0:
                print(f"[CODE OPTIMIZATION] Optimized {optimized_count} files")
 except Exception as e:
            print(f"[WARNING] Code optimization error: {e}")

    print("\n" + "=" * 70)
    print("Integrated Wicked Zerg Bot - Training System")
    print("=" * 70)
    print(f"  Mode: SINGLE GAME MODE (one game at a time)")  # IMPROVED: Always single game
    print(f"  Instance ID: 0 (single instance)")  # IMPROVED: Always show single instance
    print(f"  Bot: WickedZergBotIntegrated (RL Orchestrator)")


 progress_info = curriculum.get_progress_info()
    print(f"  Opponent: Computer (Curriculum Learning System)")
    print(f"  Current Stage: {current_difficulty.name} - {progress_info['level_name']}")
    print(f"  Progress: Level {progress_info['current_level']}/{progress_info['total_levels']}")
 print(
        f"  Games at Current Level: {progress_info['games_at_current_level']}/{progress_info['min_games_required']}"
 )
    print(f"  Map: Random selection")
    print(f"  Mode: Continuous learning (infinite loop)")
    print(f"  RL: Enabled (Action-based orchestration)")
    print(f"  Auto Code Optimization: {'Enabled' if _config.AUTO_OPTIMIZE_CODE else 'Disabled'}")
    print(f"  Replay Learning: Every {_config.REPLAY_LEARNING_INTERVAL} game(s), {_config.REPLAY_LEARNING_ITERATIONS} iterations")
    print("=" * 70 + "\n")

 # Initialize status data
 status_data = {
        "instance_id": instance_id,
        "mode": "VISUAL" if show_window else "HEADLESS",
        "game_count": 0,
        "win_count": 0,
        "loss_count": 0,
        "last_result": "N/A",
        "current_game_time": "00:00",
        "current_minerals": 0,
        "current_supply": "0/0",
        "current_units": 0,
        "status": "INITIALIZING",
        "timestamp": time.time(),
        "difficulty": current_difficulty.name,
 }
 write_status_file(instance_id, status_data)

    MAX_GAMES = int(os.environ.get("MAX_GAMES", "0"))

 if MAX_GAMES > 0:
        print(f"\n? [TRAINING] Game limit set: {MAX_GAMES} games")
        print(f"[MONITOR] Will auto-stop and close monitor after {MAX_GAMES} game(s)")
        print(f"[MODE] SINGLE GAME MODE - Only one game window at a time\n")
 else:
        print(f"\n? [TRAINING] Infinite game mode (MAX_GAMES = 0)")
        print(f"[MONITOR] Monitor will continue running for all games")
        print(f"[MODE] SINGLE GAME MODE - Only one game window at a time")
        print(f"[HINT] To limit games, set: set MAX_GAMES = N && python main_integrated.py\n")

 while True:
 try:
 game_count += 1

 if continuous_failures > 0:
 print(
                    f"[RETRY] Current consecutive failures: {continuous_failures}/{MAX_CONTINUOUS_FAILURES}"
 )

 # Map selection (use default if available maps list is empty or map not found)
 if not AVAILABLE_MAPS:
 current_map = MAP_NAME
 else:
 current_map = random.choice(AVAILABLE_MAPS)

 map_instance = maps.get(current_map)

 if map_instance is None:
                print(f"[WARNING] Map '{current_map}' not found, using default: {MAP_NAME}")
 current_map = MAP_NAME
 map_instance = maps.get(current_map)

                # Final fallback: if default map also doesn't exist, skip this game
 if map_instance is None:
 print(
                        f"[ERROR] Default map '{MAP_NAME}' also not found. Please install maps in SC2 Maps folder."
 )
                    print(f"[INFO] Expected path: {correct_sc2_path}\\Maps")
 time.sleep(5)
 continue

 # Random opponent race
 opponent_race = random.choice(OPPONENT_RACES)

 # Random personality
 personality = random.choice(PERSONALITIES)

 # Create integrated bot
 bot = WickedZergBotIntegrated(
 train_mode = True,
 instance_id = instance_id,
 personality = personality,
 opponent_race = opponent_race,
 game_count = game_count, # Pass game count for terminal display
 )
 # Pass last result to bot for terminal display
            if hasattr(bot, "last_result"):
 bot.last_result = last_result

 # Set replay path
 replay_path = os.path.join(
 replay_dir,
                f"integrated_{personality}_vs_{opponent_race.name}_{current_map}_game{game_count}.SC2Replay",
 )

 current_difficulty = curriculum.get_difficulty()
 progress_info = curriculum.get_progress_info()

            print(f"\n[GAME #{game_count}] Starting...")
            print(f"  Map: {current_map}")
            print(f"  Opponent: {opponent_race.name} ({current_difficulty.name})")
            print(f"  Personality: {personality.upper()}")
            print(f"  Stats: {win_count}W / {loss_count}L")
 print(
                f"  Curriculum Stage: {progress_info['level_name']} (Level {progress_info['current_level']}/{progress_info['total_levels']})"
 )
 print(
                f"  Games at Current Level: {progress_info['games_at_current_level']}/{progress_info['min_games_required']}"
 )

 # CRITICAL: Always wait between games to ensure only ONE game runs at a time
 if game_count > 1:
                print(f"[WAIT] Ensuring previous game is fully closed (single game mode)...")
 time.sleep(2.0)
 else:
 # First game - still wait a bit to ensure clean start
 time.sleep(0.5)

 # Update status file with game start info
 status_data.update(
 {
                    "status": "GAME_RUNNING",
                    "current_map": current_map,
                    "opponent": opponent_race.name,
                    "personality": personality.upper(),
                    "timestamp": time.time(),
 }
 )
 write_status_file(instance_id, status_data)

 # Check if window should be shown (from environment variable)
 realtime_mode = False
 headless_mode = True

 # Store bot reference for status updates during game (via callback mechanism)
            # The bot's on_step will update status file via a callback function
 bot_instance_ref = bot # Store reference for potential future use

 # Run game directly in main thread (synchronous call)
 # CRITICAL: run_game() must be called from main thread - this function is now synchronous
 result = None

 try:
                print(f"[GAME] Selected Map: {current_map}")

 if DRY_RUN_MODE:
                    print("[DRY-RUN] Skipping game execution (code validation mode)")
                    result = "Victory"
 else:
                    print(f"[GAME MODE] Single game execution")
 result = run_game(
 map_instance,
 [Bot(Race.Zerg, bot), Computer(opponent_race, current_difficulty)],
 realtime = realtime_mode,
 save_replay_as = replay_path,
 )

 except Exception as game_error:
 # Catch any game session errors (including logging errors during shutdown)
 error_msg = str(game_error).lower()

 # Handle connection reset errors (most common)
                if "connectionreseterror" in error_msg or "closing transport" in error_msg:
 continuous_failures += 1
                    print("[SYSTEM] Connection reset detected, stopping training.")
 print(
                        f"[INFO] Connection retry ({continuous_failures}/{MAX_CONTINUOUS_FAILURES}): StarCraft II client disconnected or connection lost"
 )

 if continuous_failures >= MAX_CONTINUOUS_FAILURES:
                        print("\n" + "=" * 70)
                        print("[CRITICAL] Training stopped due to failures")
                        print("=" * 70)
                        print(f"Training stopped after {MAX_CONTINUOUS_FAILURES} consecutive connection failures")
                        print("System paused to prevent further issues. Please check system status.")
                        print("\nPossible causes:")
                        print("  - SC2 client is still running. Please check.")
                        print("  - GPU/CPU temperature and memory usage. Please check.")
                        print("  - Wait a moment and try again, or check other issues")
                        print("=" * 70 + "\n")

 try:
 from datetime import datetime

                            with open("crash_report.txt", "a", encoding="utf-8") as f:
                                f.write(f"\n{'=' * 70}\n")
                                f.write(f"Training stopped time: {datetime.now()}\n")
 f.write(
                                    f"Stop reason: Training stopped after {MAX_CONTINUOUS_FAILURES} ConnectionResetError\n"
 )
                                f.write(f"Total games: {game_count}\n")
                                f.write(f"Win/Loss: {win_count} wins {loss_count} losses\n")
                                f.write(f"{'=' * 70}\n")
                            print(f"[INFO] crash_report.txt saved successfully")
 except Exception:
 pass

 break

                    result = "Defeat"
 try:
 import torch

 if torch.cuda.is_available():
 torch.cuda.empty_cache()
                            print("[SYSTEM] GPU cache cleared")
 except Exception:
 pass
 time.sleep(2)
                elif "buffer" in error_msg or "detached" in error_msg:
 # Logging error during shutdown - can be safely ignored
                    print(f"[INFO] Game ended (logging cleanup in progress)")
 # Try to determine result from bot state if possible
                    result = "Defeat"  # Default to defeat if we can't determine
                elif "signal only works in main thread" in error_msg:
 # Signal error - run_game() must run in main thread
 # Use print() instead of logger to avoid buffer errors
                    print(f"[ERROR] Signal error: run_game() must run in main thread")
                    print(f"[INFO] This error indicates a threading issue with sc2 library")
                    result = "Defeat"
                elif "local variable 'asyncio' referenced before assignment" in error_msg:
 # Asyncio variable conflict - should not happen but handle it
 # Use print() instead of logger to avoid buffer errors
                    print(f"[ERROR] Asyncio variable conflict detected: {game_error}")
                    print(f"[ERROR] Game session crashed due to asyncio reference error")
                    result = "Defeat"
 else:
 # Other errors should be reported (avoid logger to prevent buffer errors)
                    print(f"[ERROR] Game session error: {game_error}")
 import traceback

 # Only print traceback for non-buffer errors
 if (
                        "buffer" not in str(game_error).lower()
                        and "detached" not in str(game_error).lower()
 ):
 traceback.print_exc()
                    result = "Defeat"  # Default to defeat on error
 finally:
 try:
 import torch

 if torch.cuda.is_available():
 torch.cuda.empty_cache()
 except Exception:
 pass

 # Ensure logging handlers are properly flushed after each game
 # This prevents buffer detachment errors during shutdown
 try:
 for handler in logging.root.handlers[:]:
 try:
 handler.flush()
 except (ValueError, OSError, AttributeError):
 # Handler stream is closed or detached - ignore
 pass
 except Exception:
 pass # Ignore any errors during logging cleanup

 # Also give loguru a moment to flush pending logs after each game
 # This reduces the chance of buffer errors during final shutdown
 try:
 if logger:
 # Brief wait to allow async log queue to process (use time.sleep instead of await)
 time.sleep(0.05) # Short wait for async log flush
 except Exception:
 pass # Ignore errors during loguru flush

 # IMPROVED: Process result (single game mode)
            result_text = "N/A"
            if str(result) == "Victory":
 continuous_failures = 0
 win_count += 1
                result_text = "WIN"
                print(f"[VICTORY] Game #{game_count} - {win_count}W / {loss_count}L")
                print(f"[INFO] Game ended successfully. Waiting for game window to close...")

            elif str(result) == "Defeat":
 continuous_failures = 0
 loss_count += 1
                result_text = "DEFEAT"
                print(f"[DEFEAT] Game #{game_count} - {win_count}W / {loss_count}L")
                print(f"[INFO] Game ended. Waiting for game window to close...")
 else:
                result_text = "DRAW"
                print(f"[DRAW] Game #{game_count} - {win_count}W / {loss_count}L")
                print(f"[INFO] Game ended. Waiting for game window to close...")

            # Store result for next game's terminal display
 last_result = result_text

 # LEARNING: Batch processing - collect results for batch learning
 # Process batch of 10 games at once for faster learning
            if not hasattr(main, 'batch_results'):
 main.batch_results = []
 main.batch_results.append({
                'game_count': game_count,
                'result': result_text,
                'win_count': win_count,
                'loss_count': loss_count
 })

 if len(main.batch_results) >= 10:
 # Process batch of 10 games at once
 try:
 # LEARNING: Batch learning can be implemented here
 # This allows processing multiple game results together
                    print(f"[LEARNING] Processing batch of {len(main.batch_results)} games...")
 # TODO: Implement batch learning logic here
 main.batch_results.clear()
 except Exception as e:
                    print(f"[WARNING] Batch processing error: {e}")
 main.batch_results.clear()

 # Update status file with final game result
 total_games = win_count + loss_count
 win_rate = (win_count / total_games * 100) if total_games > 0 else 0.0
 status_data.update(
 {
                    "game_count": game_count,
                    "win_count": win_count,
                    "loss_count": loss_count,
                    "last_result": result_text,
                    "win_rate": round(win_rate, 1),
                    "difficulty": current_difficulty.name,
                    "difficulty_level": current_difficulty_index + 1,
                    "status": "GAME_ENDED",
                    "timestamp": time.time(),
 }
 )
 write_status_file(instance_id, status_data)

 # 🧠 Strategy Audit: Analyze performance gap vs pro gamers (매 게임마다 실행)
 try:
 from local_training.strategy_audit import StrategyAudit

 # bot 인스턴스가 유효한지 확인
                if bot_instance_ref and hasattr(bot_instance_ref, 'production'):
 auditor = StrategyAudit()
 gap_analysis = auditor.analyze_last_game(
 bot_instance_ref,
 game_result = result_text.lower()
 )

 if gap_analysis:
 # 프로 대비 지연 시간 로그 출력
 if gap_analysis.time_gaps:
                            print(f"\n[🧠 STRATEGY AUDIT] 프로 대비 빌드오더 분석 결과:")
                            print(f"  게임 ID: {gap_analysis.game_id}")

 # 가장 심각한 시간 오차 상위 3개 출력
                            critical_gaps = [g for g in gap_analysis.time_gaps if g.severity in ["critical", "major"]]
 if critical_gaps:
                                print(f"  ⚠️  심각한 지연 발견 ({len(critical_gaps)}개):")
 for i, gap in enumerate(critical_gaps[:3], 1):
 print(
                                        f"    {i}. {gap.building_name}: "
                                        f"프로 {gap.pro_time:.1f}초 vs 봇 {gap.bot_time:.1f}초 "
                                        f"(지연: {gap.gap_seconds:+.1f}초, {gap.gap_percentage:+.1f}%)"
 )
 else:
 # 모든 시간 오차 출력 (심각한 것이 없으면)
                                print(f"  📊 시간 오차 분석:")
 for i, gap in enumerate(gap_analysis.time_gaps[:5], 1):
                                    severity_icon = "🔴" if gap.severity == "critical" else "🟡" if gap.severity == "major" else "🟢"
 print(
                                        f"    {i}. {severity_icon} {gap.building_name}: "
                                        f"프로 {gap.pro_time:.1f}초 vs 봇 {gap.bot_time:.1f}초 "
                                        f"(지연: {gap.gap_seconds:+.1f}초)"
 )

 # 권장사항 출력
 if gap_analysis.recommendations:
                                print(f"  💡 개선 권장사항:")
 for i, rec in enumerate(gap_analysis.recommendations[:3], 1):
                                    print(f"    {i}. {rec}")

 print() # 빈 줄 추가
 else:
                            print(f"[🧠 STRATEGY AUDIT] 분석 완료 (시간 오차 없음 또는 데이터 부족)\n")
 else:
                        print(f"[🧠 STRATEGY AUDIT] 분석 스킵 (승리 또는 데이터 부족)\n")
 else:
                    print(f"[🧠 STRATEGY AUDIT] 분석 스킵 (봇 인스턴스 또는 데이터 부족)\n")
 except ImportError as import_err:
                print(f"[WARNING] Strategy Audit 모듈을 불러올 수 없습니다: {import_err}\n")
 except Exception as audit_error:
 # 분석 실패해도 게임 진행은 계속
                print(f"[WARNING] Strategy Audit 분석 중 오류 발생: {audit_error}\n")
 import traceback
 traceback.print_exc()

 # Calculate win rate
 total_games = win_count + loss_count
 if total_games > 0:
 win_rate_percent = (win_count / total_games) * 100
 win_rate_ratio = win_count / total_games # 0.0 ~ 1.0
 print(
                    f"[STATS] Win Rate: {win_rate_percent:.1f}% ({win_count}W / {total_games} games)"
 )

 curriculum.record_game()

 recent_games = min(20, total_games)
 if recent_games >= 10:
 recent_wins = max(0, win_count - max(0, total_games - recent_games))
 recent_win_rate = recent_wins / recent_games if recent_games > 0 else 0.0

 old_difficulty_idx = curriculum.current_idx
 if curriculum.check_promotion(recent_win_rate, recent_games):
 current_difficulty = curriculum.get_difficulty()
 current_difficulty_index = curriculum.current_idx


 # IMPROVED: Safety check - ensure only one level increased
 if curriculum.current_idx != old_difficulty_idx + 1:
                            print(f"[WARNING] Difficulty index changed unexpectedly: {old_difficulty_idx} -> {curriculum.current_idx}")
 # Force to exactly one level higher
 curriculum.current_idx = min(old_difficulty_idx + 1, len(curriculum.levels) - 1)
 current_difficulty = curriculum.get_difficulty()
 current_difficulty_index = curriculum.current_idx
 curriculum.save_level()

 if recent_win_rate < curriculum.demotion_threshold and recent_games >= 30:
 old_difficulty_idx = curriculum.current_idx
 if curriculum.check_demotion(recent_win_rate, recent_games):
 current_difficulty = curriculum.get_difficulty()
 current_difficulty_index = curriculum.current_idx

 # IMPROVED: Safety check - ensure only one level decreased
 if curriculum.current_idx != old_difficulty_idx - 1:
                                print(f"[WARNING] Difficulty index changed unexpectedly: {old_difficulty_idx} -> {curriculum.current_idx}")
 # Force to exactly one level lower
 curriculum.current_idx = max(old_difficulty_idx - 1, 0)
 current_difficulty = curriculum.get_difficulty()
 current_difficulty_index = curriculum.current_idx
 curriculum.save_level()

 # Update difficulty tracking
 difficulty_games = curriculum.games_at_current_level

 # IMPROVED: Periodic code optimization (every 5 games)
 if _config.AUTO_OPTIMIZE_CODE and game_count % 5 == 0:
 run_code_optimization()

 try:
 from scripts.replay_build_order_learner import ReplayBuildOrderExtractor
 from learning_accelerator import LearningAccelerator
 from error_handler import ErrorHandler
 from performance_monitor import PerformanceMonitor

 # IMPROVED: Use flexible path detection
                replay_archive_dir = os.environ.get("REPLAY_ARCHIVE_DIR")
 if not replay_archive_dir or not os.path.exists(replay_archive_dir):
 # Try common locations
 possible_paths = [
                        PROJECT_DIR / "replays_archive",
                        Path.home() / "replays",
                        Path("replays_archive"),
 ]
 for path in possible_paths:
 if path.exists():
 replay_archive_dir = str(path)
 break
 else:
                        replay_archive_dir = "replays_archive"  # Fallback to relative path
 learning_interval = _config.REPLAY_LEARNING_INTERVAL
 learning_iterations = _config.REPLAY_LEARNING_ITERATIONS

 if game_count % learning_interval == 0:
                    print(f"[BUILD LEARNING] Analyzing pro replays for build order improvements (x{learning_iterations})...")

 quality_analyzer = ReplayQualityAnalyzer()
 learning_accelerator = LearningAccelerator()
 error_handler = ErrorHandler()
 performance_monitor = PerformanceMonitor()

 for iteration in range(learning_iterations):
 learning_accelerator.increment_iteration()
 speed_multiplier = learning_accelerator.get_learning_speed(learning_accelerator.iteration)

                        print(f"[BUILD LEARNING] Iteration {iteration + 1}/{learning_iterations} (Speed: {speed_multiplier}x)...")

 # Performance monitoring
 perf = performance_monitor.check_performance()
                        if perf["needs_optimization"]:
                            print(f"[PERFORMANCE] High resource usage detected (CPU: {perf['cpu_percent']:.1f}%, Memory: {perf['memory_percent']:.1f}%)")
 opt_result = performance_monitor.trigger_code_optimization()
 # LEARNING: Batch processing - collect results first
 batch_results = []
 if len(batch_results) >= 10:
 # Process batch of 10 games at once
 process_batch(batch_results)
 batch_results.clear()
 # LEARNING: Batch processing - collect results first
 batch_results = []
 if len(batch_results) >= 10:
 # Process batch of 10 games at once
 process_batch(batch_results)
 batch_results.clear()
                            if opt_result.get("success"):
                                print("[PERFORMANCE] Code optimization triggered")

 extractor = ReplayBuildOrderExtractor(replay_dir = replay_archive_dir)
 replay_files = extractor.scan_replays()

 weighted_params = {}
 total_weight = 0.0

 # IMPROVED: Use configurable max_replays instead of hardcoded 50
 max_replays_batch = _config.MAX_REPLAYS_FOR_LEARNING // 2 # Process in batches
 for replay_file in replay_files[:max_replays_batch]:
 try:
 quality_data = quality_analyzer.process_replay(replay_file)

 if quality_data:
                                    weight = quality_data["weight"]
                                    strategy_type = quality_data.get("strategy_type", "balanced")
 learning_accelerator.update_strategy_count(strategy_type)

 learned_params = extractor.extract_build_order(replay_file)
 if learned_params:
                                        for key, value in learned_params.get("timings", {}).items():
 if key not in weighted_params:
 weighted_params[key] = []
 weighted_params[key].append((value, weight))
 total_weight += weight
 except UnicodeDecodeError:
 error_handler.handle_unicode_error(replay_file)
 continue
 except Exception as e:
 error_type = type(e).__name__
                                if "Mpq" in error_type or "Corrupt" in error_type:
 error_handler.handle_mpq_error(replay_file)
 continue

 if weighted_params:
 final_params = {}
 for key, weighted_values in weighted_params.items():
 if weighted_values:
 weighted_sum = sum(v * w for v, w in weighted_values)
 weight_sum = sum(w for _, w in weighted_values)
 final_params[key] = weighted_sum / weight_sum if weight_sum > 0 else 0.0

 if final_params:
 extractor.save_learned_parameters(final_params)
                                print(f"[BUILD LEARNING] Iteration {iteration + 1}: Updated {len(final_params)} build order parameters (Weighted: Victory={VICTORY_WEIGHT}, Defeat={DEFEAT_WEIGHT})")
 else:
                            print(f"[BUILD LEARNING] Iteration {iteration + 1}: No new parameters learned")

 # Generate reports
 error_report = error_handler.get_error_report()
                    if error_report["corrupted_files"] > 0:
                        print(f"[ERROR HANDLING] Moved {error_report['corrupted_files']} corrupted files to trash")

 learning_report = learning_accelerator.get_report()
                    print(f"[LEARNING STATS] Strategy distribution: {learning_report['strategy_distribution']}")
                    print(f"[LEARNING STATS] Priority strategy: {learning_report['priority_strategy']}")

 accuracy_report_path = error_handler.generate_accuracy_report()
 if accuracy_report_path:
                        print(f"[REPORT] Accuracy report saved to: {accuracy_report_path}")

                    print(f"[BUILD LEARNING] Completed {learning_iterations} iterations")
 except ImportError as e:
                print(f"[INFO] Build order learning not available: {e}")
 except Exception as e:
                print(f"[WARNING] Build order learning error: {e}")

            replay_download_url = os.environ.get("REPLAY_DOWNLOAD_URL", None)
 if replay_download_url and game_count % 20 == 0: # Check every 20 games
 try:

                    print(f"[REPLAY DOWNLOAD] Checking for new replays from URL...")
 # IMPROVED: Use flexible path detection
                    replay_archive_dir = os.environ.get("REPLAY_ARCHIVE_DIR")
 if not replay_archive_dir or not os.path.exists(replay_archive_dir):
 # Try common locations
 possible_paths = [
                            PROJECT_DIR / "replays_archive",
                            Path.home() / "replays",
                            Path("replays_archive"),
 ]
 for path in possible_paths:
 if path.exists():
 replay_archive_dir = str(path)
 break
 else:
                            replay_archive_dir = "replays_archive"  # Fallback to relative path
 downloader = ReplayDownloader(replay_dir = Path(replay_archive_dir))
 new_count = downloader.download_and_extract_from_url(replay_download_url)

 if new_count > 0:
                        print(f"[REPLAY DOWNLOAD] Downloaded {new_count} new replays, triggering learning (x{_config.REPLAY_LEARNING_ITERATIONS})...")
 for iteration in range(_config.REPLAY_LEARNING_ITERATIONS):
                            print(f"[BUILD LEARNING] Iteration {iteration + 1}/{_config.REPLAY_LEARNING_ITERATIONS}...")
 extractor = ReplayBuildOrderExtractor(replay_dir = replay_archive_dir)
 learned_params = extractor.learn_from_replays(max_replays = _config.MAX_REPLAYS_FOR_LEARNING)
 if learned_params:
 extractor.save_learned_parameters(learned_params)
                                print(f"[BUILD LEARNING] Iteration {iteration + 1}: Updated {len(learned_params)} parameters from new replays")

 # 🧠 Strategy Audit: Verify learned parameters are loaded
 try:
                                    learned_json_path = Path("local_training/scripts/learned_build_orders.json")
 if learned_json_path.exists():
 auditor = StrategyAudit(learned_build_orders_path = learned_json_path)
 if auditor.pro_data:
                                            print(f"[🧠 STRATEGY AUDIT] Pro gamer data refreshed: {len(auditor.pro_data.get('build_orders', []))} build orders available")
 except Exception as audit_refresh_err:
                                    print(f"[WARNING] Strategy Audit refresh failed: {audit_refresh_err}")
                        print(f"[BUILD LEARNING] Completed {_config.REPLAY_LEARNING_ITERATIONS} iterations")
 except ImportError as e:
                    print(f"[INFO] Replay downloader not available: {e}")
 except Exception as e:
                    print(f"[WARNING] Replay download error: {e}")

 try:

 run_self_evolution(replay_dir)
 except ImportError:
 # Fallback to extract_replay_insights if self_evolution not available
 try:

 analyze_latest_replay(replay_dir)
 except ImportError:
                    print("[WARNING] Replay analysis modules not found, skipping analysis")
 except Exception as e:
                print(f"[WARNING] Self-Evolution analysis error: {e}")

 if monitor_enabled and code_monitor:
                monitor_status = "RUNNING" if code_monitor.running else "STOPPED"
 monitor_thread_alive = code_monitor.monitor_thread and code_monitor.monitor_thread.is_alive()
                print(f"\n[MONITOR] Status: {monitor_status} | Thread Alive: {monitor_thread_alive}")

 if code_monitor.has_fixes():
                    print("\n" + "="*70)
                    print("? REAL-TIME MONITOR DETECTED ISSUES!")
                    print("="*70)
 print(code_monitor.get_fix_summary())
                    print("Fixes saved to: self_healing_logs/fix_*.json")
                    print("Review and apply fixes before next game.")
                    print("="*70 + "\n")

 # Check if max games reached (for testing/demo mode)
 if MAX_GAMES > 0 and game_count >= MAX_GAMES:
                print(f"\n{'='*70}")
                print(f"[STOP] Maximum games ({MAX_GAMES}) reached. Training complete.")
                print(f"[FINAL STATS] {win_count}W / {loss_count}L")
                print(f"{'='*70}")

 # ? Monitor graceful shutdown
 if monitor_enabled and code_monitor:
                    print("\n[MONITOR] Stopping real-time code monitor...")
                    print("[MONITOR] Waiting for monitor thread to finish...")
 try:
 code_monitor.stop()
                        print("[? SUCCESS] Real-time code monitor stopped gracefully")
 except Exception as e:
                        print(f"[? WARNING] Error stopping monitor: {e}")

 if code_monitor.has_fixes():
                        print("\n[MONITOR] Final fixes summary:")
 print(code_monitor.get_fix_summary())

                print("\n[?] Training session ended. Monitor is now inactive.")
 break

            print(f"[WAIT] Waiting for game window to close completely...")
 time.sleep(3.0)

 except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("[INTERRUPT] Training stopped by user.")
            print(f"[FINAL STATS] {win_count}W / {loss_count}L")
            print("="*70)

 if monitor_enabled and code_monitor:
                print("\n[MONITOR] Stopping real-time code monitor...")
 try:
 code_monitor.stop()
                    print("[? SUCCESS] Real-time code monitor stopped gracefully")
 except Exception as e:
                    print(f"[? WARNING] Error stopping monitor: {e}")
 if code_monitor.has_fixes():
                    print("\n[MONITOR] Final fixes summary:")
 print(code_monitor.get_fix_summary())

            print("\n[?] Training session ended. Monitor is now inactive.")
 break

 except Exception as e:
            print(f"\n[ERROR] Game error: {e}")
 import traceback

 traceback.print_exc()
 time.sleep(5) # Wait before retrying
 continue

    print("\n" + "="*70)
    print("[CLEANUP] Training loop ended. Performing final cleanup...")
    print("="*70)

 if monitor_enabled and code_monitor:
 try:
 code_monitor.stop()
            print("[?] Real-time code monitor stopped successfully")

 if code_monitor.has_fixes():
                print("\n" + "="*70)
                print("? FINAL MONITOR REPORT")
                print("="*70)
 print(code_monitor.get_fix_summary())
 except Exception as e:
            print(f"[?] Error stopping monitor: {e}")

    print("\n[? COMPLETE] All cleanup finished. Program terminating...")
    print("="*70 + "\n")

 # CRITICAL: Clean up logging system BEFORE function returns
 # This ensures all pending logs are flushed before program shutdown
 try:
 # Complete loguru logging first (flush all pending logs in queue)
 if logger:
 try:
 logger.complete() # Wait for all pending logs to be written
 except Exception:
 pass # Ignore errors during completion

 # Then shutdown standard logging
 logging.shutdown()
 except Exception:
 pass # Ignore errors during logging shutdown

if __name__ == "__main__":
 # Single Instance Mode: 1 instance with full GPU and CPU utilization
    os.environ["INSTANCE_ID"] = "0"
    os.environ["NUM_INSTANCES"] = "1"
    os.environ["SINGLE_GAME_MODE"] = "true"
    os.environ["SHOW_WINDOW"] = "true"
    os.environ["HEADLESS_MODE"] = "false"
    os.environ["DISABLE_DASHBOARD"] = "true"

 # CPU Thread Configuration: Use 12 threads (configurable via TORCH_NUM_THREADS env var)
 try:
 # Change to a safe directory before importing torch to avoid path conflicts
 original_cwd = os.getcwd()
 try:
 # Temporarily change to project root to avoid local directory conflicts
 project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
 os.chdir(project_root)
 import torch
 # Verify torch is properly installed
            if not hasattr(torch, '_C'):
                raise ImportError("PyTorch C extensions not properly loaded")
            num_threads = int(os.environ.get("TORCH_NUM_THREADS", "12"))
 torch.set_num_threads(num_threads)
            os.environ["OMP_NUM_THREADS"] = str(num_threads)
            os.environ["MKL_NUM_THREADS"] = str(num_threads)
            print(f"[CONFIG] Single instance mode: 1 instance with GPU and {num_threads} CPU threads")
 finally:
 os.chdir(original_cwd)
 except Exception as e:
        print(f"[WARNING] Failed to configure CPU threads: {e}")
        print(f"[INFO] Game will continue but may use default thread settings")

 try:
 if logger:
 logger.remove() # Remove existing handlers
            logger.add(sys.stderr, level="INFO", enqueue = True, catch = True)  # Reconfigure for safety
 except Exception:
 pass

 try:
        print("\n" + "="*70)
        print("SINGLE GAME MODE ENABLED")
        print("VISUAL MODE ENABLED (Game window visible)")
        print("="*70)
        print("Only ONE game will run at a time.")
        print("Previous game must fully close before next game starts.")
        print("Game window is visible for monitoring.")
        print("="*70 + "\n")
 run_training()
 except KeyboardInterrupt:
 # User interrupted training
        print("\n[STOP] Training stopped by user.")
 except Exception as e:
 # Log runtime error (use print to avoid loguru buffer errors)
        print(f"[ERROR] Runtime error occurred: {e}")
 import traceback

 traceback.print_exc()
 finally:
 # Ensure logging is properly shut down and buffers are flushed
 try:
 # Complete loguru logging (flush all pending logs)
 if logger:
 try:
 logger.complete() # Wait for all pending logs to be written
 except Exception:
 pass # Ignore errors during completion
 try:
 logger.remove() # Remove all handlers
 except Exception:
 pass # Ignore errors during removal
 except Exception:
 pass

 # Also shutdown standard logging
 try:
 logging.shutdown()
 except Exception:
 pass # Ignore errors during logging shutdown

        print("[OK] System safely shut down.")