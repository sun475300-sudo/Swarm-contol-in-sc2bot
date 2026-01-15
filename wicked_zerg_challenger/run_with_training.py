# -*- coding: utf-8 -*-
"""
Run bot with neural network training enabled.

This script starts a game and trains the neural network model in real-time.
Model will be saved to: local_training/models/zerg_net_model.pt
"""

import sys
import os
from pathlib import Path

# SC2 path auto-setup function
def _ensure_sc2_path():
    """
    Set SC2PATH environment variable - search via Windows Registry or common paths
    """
    # Skip Windows-specific discovery on non-Windows hosts (AI Arena runs on Linux)
    if sys.platform != "win32":
        return

    if "SC2PATH" in os.environ:
        sc2_path = os.environ["SC2PATH"]
        versions_dir = os.path.join(sc2_path, "Versions")
        if os.path.exists(versions_dir):
            return

    # 1. Find StarCraft II installation path via Windows Registry
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Blizzard Entertainment\StarCraft II")
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)

        if os.path.exists(install_path):
            os.environ["SC2PATH"] = install_path
            print(f"[SC2] Found via Registry: {install_path}")
            return
    except Exception:
        pass

    # 2. Search common installation paths
    common_paths = [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]

    for path in common_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            print(f"[SC2] Found at common path: {path}")
            return

    print("[WARNING] SC2 installation not found automatically")

# Setup SC2 path before sc2 import
_ensure_sc2_path()

# Bot class import
sys.path.append(str(Path(__file__).parent))
from wicked_zerg_bot_pro import WickedZergBotPro
from sc2.data import Race, Difficulty  # type: ignore
from sc2.main import run_game  # type: ignore
from sc2.player import Bot, Computer  # type: ignore
from sc2 import maps  # type: ignore

def create_bot_with_training():
    """
    Create bot instance with neural network training enabled.
    Model will be saved to: local_training/models/zerg_net_model.pt
    """
    # CRITICAL: Set train_mode=True to enable neural network training
    bot_instance = WickedZergBotPro(train_mode=True)
    return Bot(Race.Zerg, bot_instance)

def main():
    """
    Main entry point for bot execution with training enabled.
    IMPROVED: Continuous training mode - games will run continuously without stopping.
    """
    import time
    import random
    
    print("\n" + "=" * 70)
    print("? NEURAL NETWORK TRAINING MODE (CONTINUOUS)")
    print("=" * 70)
    print()
    print("? Training Configuration:")
    print("   ? 15-dimensional state vector (Self 5 + Enemy 10)")
    print("   ? REINFORCE algorithm for policy learning")
    print("   ? Model auto-saves after each game")
    print("   ? Continuous training: Games run continuously without stopping")
    print("   ? Build order comparison with pro gamer baseline")
    print("   ? Auto-update learned parameters on victory")
    print()
    print("? Model save location: local_training/models/zerg_net_model.pt")
    print("? Build order data: local_training/scripts/learned_build_orders.json")
    print()
    print("??  Press Ctrl+C to stop training")
    print("=" * 70)
    print()

    # 1. Run on AI Arena server (when --LadderServer flag is present)
    if "--LadderServer" in sys.argv:
        from sc2.main import run_ladder_game  # type: ignore
        print("\n[STEP 2] ? Connecting to AI Arena Server...")
        print("=" * 70)
        bot = create_bot_with_training()
        print("[OK] Bot created with training enabled")
        print("[INFO] Joining Ladder Game...")
        run_ladder_game(bot)
        return

    # 2. Run on local machine for continuous training
    print("\n[STEP 2] ? Initializing Continuous Training Loop...")
    print("=" * 70)
    
    # Initialize Training Session Manager
    try:
        from tools.training_session_manager import TrainingSessionManager
        session_manager = TrainingSessionManager()
        print("[OK] Training session manager initialized")
    except ImportError as e:
        print(f"[WARNING] Training session manager not available: {e}")
        session_manager = None
    
    game_count = 0
    max_consecutive_failures = 5
    consecutive_failures = 0
    
    # Available maps
    available_maps = ["AbyssalReefLE", "BelShirVestigeLE", "CactusValleyLE", "HonorgroundsLE", "ProximaStationLE"]
    opponent_races = [Race.Terran, Race.Protoss, Race.Zerg]
    # IMPROVED: Use only available Difficulty values (Elite doesn't exist, VeryHard is the highest)
    difficulties = [Difficulty.Hard, Difficulty.VeryHard]
    
    print(f"[INFO] Available maps: {len(available_maps)} maps")
    print(f"[INFO] Available opponent races: {len(opponent_races)} races")
    print(f"[INFO] Available difficulties: {len(difficulties)} levels")
    print()
    print("[OK] Continuous training loop initialized")
    print("[INFO] Game windows will open - you can watch the games in real-time!")
    print("[INFO] Neural network is learning from your gameplay...")
    print("=" * 70)
    print()
    
    while True:
        try:
            game_count += 1
            
            if consecutive_failures > 0:
                print(f"\n??  [RETRY] Current consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
                if consecutive_failures >= max_consecutive_failures:
                    print(f"? [ERROR] Too many consecutive failures ({consecutive_failures}). Stopping training.")
                    break
            
            # [STEP 3] Select random map, opponent race, and adaptive difficulty
            print(f"\n{'='*70}")
            print(f"? [STEP 3] GAME #{game_count} - Random Selection")
            print("=" * 70)
            
            map_name = random.choice(available_maps)
            opponent_race = random.choice(opponent_races)
            
            # IMPROVED: Use adaptive difficulty from session manager
            if session_manager:
                recommended_difficulty_str = session_manager.get_adaptive_difficulty()
                # Convert string to Difficulty enum
                if recommended_difficulty_str == "VeryHard":
                    difficulty = Difficulty.VeryHard
                else:
                    difficulty = Difficulty.Hard
                print(f"[ADAPTIVE] Recommended difficulty: {recommended_difficulty_str} "
                      f"(based on {session_manager.session_stats.win_rate:.1f}% win rate)")
            else:
                difficulty = random.choice(difficulties)
            
            print(f"[SELECTED] Map: {map_name}")
            print(f"[SELECTED] Opponent Race: {opponent_race.name}")
            print(f"[SELECTED] Difficulty: {difficulty.name}")
            print()
            print("[INFO] Starting game...")
            print("=" * 70)
            print()
            
            # Create new bot instance for each game
            bot = create_bot_with_training()
            # bot is already a Bot instance, so we can set attributes on the underlying AI
            if hasattr(bot, 'ai') and bot.ai:
                bot.ai.game_count = game_count  # Track game count
            
            # Run game with error handling
            try:
                map_instance = maps.get(map_name)
                if map_instance is None:
                    print(f"[WARNING] Map '{map_name}' not found, using default: AbyssalReefLE")
                    map_name = "AbyssalReefLE"
                    map_instance = maps.get(map_name)
                
                if map_instance is None:
                    print(f"[ERROR] Default map not found. Skipping this game.")
                    consecutive_failures += 1
                    time.sleep(5)
                    continue
                
                # CRITICAL: bot is already a Bot instance from create_bot_with_training()
                # DO NOT wrap it again with Bot() - it will cause AssertionError
                # bot = Bot(Race.Zerg, bot)  # ? WRONG - causes error
                # bot is already a Bot instance, use it directly
                run_game(
                    map_instance,
                    [
                        bot,  # ? CORRECT: Use bot directly (already a Bot instance)
                        Computer(opponent_race, difficulty)
                    ],
                    realtime=False  # False = fast speed, True = real-time speed
                )
                
                # Game completed successfully
                consecutive_failures = 0
                if session_manager:
                    session_manager.reset_error_count()
                
                # IMPROVED: Get game result from bot (if available)
                game_result_str = "Unknown"
                game_time = 0.0
                build_order_score = None
                loss_reason = None
                parameters_updated = 0
                
                if hasattr(bot, 'ai') and bot.ai:
                    # Try to get game result from bot
                    if hasattr(bot.ai, 'last_result'):
                        game_result_str = str(bot.ai.last_result)
                    if hasattr(bot.ai, 'time'):
                        game_time = float(bot.ai.time)
                
                # Record game result in session manager
                if session_manager:
                    session_manager.record_game_result(
                        game_id=game_count,
                        map_name=map_name,
                        opponent_race=opponent_race.name,
                        difficulty=difficulty.name,
                        result=game_result_str,
                        game_time=game_time,
                        build_order_score=build_order_score,
                        loss_reason=loss_reason,
                        parameters_updated=parameters_updated
                    )
                
                print(f"\n{'='*70}")
                print(f"? [GAME #{game_count}] COMPLETED SUCCESSFULLY")
                print("=" * 70)
                print("[INFO] Neural network model saved")
                print("[INFO] Build order comparison analysis will be displayed above")
                print()
                print("[NEXT] Automatically starting next game in 3 seconds...")
                print("=" * 70)
                time.sleep(3)
                
            except KeyboardInterrupt:
                print("\n[STOP] Training stopped by user.")
                break
            except Exception as game_error:
                consecutive_failures += 1
                
                # IMPROVED: Record error in session manager
                if session_manager:
                    error_type = type(game_error).__name__
                    error_message = str(game_error)
                    session_manager.record_error(error_type, error_message)
                
                print(f"\n[ERROR] Game #{game_count} failed: {game_error}")
                print(f"[RETRY] Will retry after 5 seconds...")
                import traceback
                traceback.print_exc()
                time.sleep(5)
                continue
                
        except KeyboardInterrupt:
            print("\n[STOP] Training stopped by user.")
            break
        except Exception as e:
            consecutive_failures += 1
            
            # IMPROVED: Record error in session manager
            if session_manager:
                error_type = type(e).__name__
                error_message = str(e)
                session_manager.record_error(error_type, error_message)
            
            print(f"\n[ERROR] Unexpected error in training loop: {e}")
            print(f"[RETRY] Will retry after 5 seconds...")
            import traceback
            traceback.print_exc()
            time.sleep(5)
            continue
    
    # IMPROVED: Print final training summary
    print()
    print("=" * 70)
    print("TRAINING STOPPED")
    print("=" * 70)
    print(f"Total games completed: {game_count}")
    print("Model saved to: local_training/models/zerg_net_model.pt")
    print("You can now use this trained model in future games!")
    
    if session_manager:
        print(session_manager.get_training_summary())
    
    print("=" * 70)

if __name__ == "__main__":
    main()
