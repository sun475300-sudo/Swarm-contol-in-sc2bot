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
from sc2.data import Race, Difficulty # type: ignore
from sc2.main import run_game # type: ignore
from sc2.player import Bot, Computer # type: ignore
from sc2 import maps # type: ignore

def create_bot_with_training():
    """
    Create bot instance with neural network training enabled.
    Model will be saved to: local_training/models/zerg_net_model.pt
    """
    # CRITICAL: Set train_mode = True to enable neural network training
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
        
        # Start Arena Monitoring Server
        arena_server_manager = None
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from monitoring.server_manager import start_arena_monitoring
            arena_server_manager = start_arena_monitoring(background=True)
            if arena_server_manager:
                print("[OK] Arena monitoring server started")
                print(f"     Server URL: {arena_server_manager.get_server_url()}")
                print(f"     Mobile/Web Access: Available")
            else:
                print("[WARNING] Failed to start arena monitoring server")
        except Exception as e:
            print(f"[WARNING] Arena monitoring server not available: {e}")
            print("[INFO] Continuing without monitoring server...")

        print("\n[STEP 2] ? Connecting to AI Arena Server...")
        print("=" * 70)
        bot = create_bot_with_training()
        print("[OK] Bot created with training enabled")
        print("[INFO] Joining Ladder Game...")
        try:
            run_ladder_game(bot)
        finally:
            # Stop arena server when done
            if arena_server_manager:
                arena_server_manager.stop_server()
        return

    # 2. Run on local machine for continuous training
    print("\n[STEP 2] ? Initializing Continuous Training Loop...")
    print("=" * 70)

    # Start Local Monitoring Server
    local_server_manager = None
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from monitoring.server_manager import start_local_monitoring
        local_server_manager = start_local_monitoring(background=True)
        if local_server_manager:
            print("[OK] Local monitoring server started")
            print(f"     Server URL: {local_server_manager.get_server_url()}")
            print(f"     Mobile/Web Access: Available")
            print(f"     Web UI: {local_server_manager.get_server_url()}/ui")
            print(f"     API Docs: {local_server_manager.get_server_url()}/docs")
        else:
            print("[WARNING] Failed to start local monitoring server")
    except Exception as e:
        print(f"[WARNING] Monitoring server not available: {e}")
        print("[INFO] Continuing without monitoring server...")

    # Initialize Training Session Manager
    try:
        from tools.training_session_manager import TrainingSessionManager
        session_manager = TrainingSessionManager()
        print("[OK] Training session manager initialized")
    except ImportError as e:
        print(f"[WARNING] Training session manager not available: {e}")
        session_manager = None

    # Initialize Background Parallel Learner
    background_learner = None
    try:
        from tools.background_parallel_learner import BackgroundParallelLearner
        background_learner = BackgroundParallelLearner(
            max_workers=2,  # 최대 2개의 병렬 워커
            enable_replay_analysis=True,
            enable_model_training=True
        )
        background_learner.start()
        print("[OK] Background parallel learner initialized and started")
        print("[INFO] Replay analysis and model training will run in background")
    except ImportError as e:
        print(f"[WARNING] Background parallel learner not available: {e}")
    except Exception as e:
        print(f"[WARNING] Failed to start background learner: {e}")

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
                # bot = Bot(Race.Zerg, bot) # WRONG - causes error
                # bot is already a Bot instance, use it directly
                run_game(
                    map_instance,
                    [
                        bot,  # CORRECT: Use bot directly (already a Bot instance)
                        Computer(opponent_race, difficulty)
                    ],
                    realtime=False  # False = fast speed, True = real-time speed
                )

                # Game completed successfully
                consecutive_failures = 0
                if session_manager:
                    session_manager.reset_error_count()

                # IMPROVED: Get game result from bot (wait for on_end to complete)
                # Wait a moment for on_end() to complete and store _training_result
                import time as time_module
                time_module.sleep(0.5)  # Small delay to ensure on_end() completes

                game_result_str = "Unknown"
                game_time = 0.0
                build_order_score = None
                loss_reason = None
                parameters_updated = 0

                if hasattr(bot, 'ai') and bot.ai:
                    # CRITICAL: Get training result from on_end() if available
                    if hasattr(bot.ai, '_training_result'):
                        result = bot.ai._training_result
                        game_result_str = result.get("game_result", "Unknown")
                        game_time = result.get("game_time", 0.0)
                        build_order_score = result.get("build_order_score")
                        loss_reason = result.get("loss_reason")
                        parameters_updated = result.get("parameters_updated", 0)
                        print(f"[INFO] Retrieved training result: {game_result_str}, "
                              f"Time: {game_time:.1f}s, Score: {build_order_score}, "
                              f"Params: {parameters_updated}")
                    else:
                        # Fallback: Try to get from bot attributes
                        if hasattr(bot.ai, 'last_result'):
                            game_result_str = str(bot.ai.last_result)
                        if hasattr(bot.ai, 'time'):
                            game_time = float(bot.ai.time)
                        print(f"[WARNING] _training_result not found, using fallback values")

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

                # IMPROVED: Longer wait time between games to ensure SC2 client fully closes
                wait_between_games = 10  # Increased from 3 to 10 seconds
                print(f"[NEXT] Automatically starting next game in {wait_between_games} seconds...")
                print(f"[INFO] Waiting for SC2 client to fully close before next game")
                print("=" * 70)

                # IMPROVED: Check if SC2 processes are still running before next game
                try:
                    import psutil
                    for _ in range(wait_between_games):
                        sc2_running = False
                        for proc in psutil.process_iter(['pid', 'name']):
                            try:
                                proc_name = proc.info['name'].lower()
                                if 'sc2' in proc_name or 'starcraft' in proc_name:
                                    sc2_running = True
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass

                        if not sc2_running:
                            # SC2 processes closed, can proceed
                            break

                        time.sleep(1)
                    else:
                        # Still waiting, proceed anyway
                        print(f"[WARNING] SC2 processes may still be running, but proceeding anyway")
                except ImportError:
                    # psutil not available, use simple sleep
                    time.sleep(wait_between_games)
                except Exception:
                    # Process check failed, use simple sleep
                    time.sleep(wait_between_games)

                # IMPROVED: Print background learning stats periodically
                if background_learner and game_count % 5 == 0:
                    stats = background_learner.get_stats()
                    print(f"\n{'='*70}")
                    print("? [BACKGROUND LEARNING] STATISTICS")
                    print("=" * 70)
                    print(f"Replays Analyzed: {stats['replays_analyzed']}")
                    print(f"Models Trained: {stats['models_trained']}")
                    print(f"Total Processing Time: {stats['total_processing_time']:.2f}s")
                    print(f"Active Workers: {stats['active_workers']}/{stats['max_workers']}")
                    print(f"Errors: {stats['errors']}")
                    print("=" * 70)
                    print()
            except Exception as game_error:
                consecutive_failures += 1

                # IMPROVED: Record error in session manager
                if session_manager:
                    error_type = type(game_error).__name__
                    error_message = str(game_error)
                    session_manager.record_error(error_type, error_message)

                # IMPROVED: Handle connection errors with longer wait time
                error_msg = str(game_error).lower()
                is_connection_error = (
                    "connection" in error_msg or
                    "connectionalreadyclosed" in error_msg or
                    "websocket" in error_msg or
                    "closing transport" in error_msg
                )

                if is_connection_error:
                    wait_time = 15  # Longer wait for connection errors
                    print(f"\n[ERROR] Game #{game_count} failed: Connection error")
                    print(f"[ERROR] StarCraft II client connection was closed unexpectedly")
                    print(f"[INFO] This usually happens when:")
                    print(f"   - Previous game session didn't fully close")
                    print(f"   - SC2 client crashed or was terminated")
                    print(f"   - Network/WebSocket connection was interrupted")
                    print(f"[RETRY] Waiting {wait_time} seconds for SC2 client to fully close...")
                    print(f"[INFO] Please ensure no SC2 game windows are still open")
                else:
                    wait_time = 10  # Standard wait for other errors
                    print(f"\n[ERROR] Game #{game_count} failed: {game_error}")
                    print(f"[RETRY] Will retry after {wait_time} seconds...")

                import traceback
                traceback.print_exc()
                time.sleep(wait_time)

                # IMPROVED: Try to check if SC2 processes are still running
                try:
                    import psutil
                    sc2_processes = []
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            proc_name = proc.info['name'].lower()
                            if 'sc2' in proc_name or 'starcraft' in proc_name:
                                sc2_processes.append(proc.info['pid'])
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    if sc2_processes:
                        print(f"[WARNING] Found {len(sc2_processes)} SC2 process(es) still running")
                        print(f"[INFO] Waiting additional 5 seconds for processes to close...")
                        time.sleep(5)
                except ImportError:
                    # psutil not available, skip process check
                    pass
                except Exception as proc_error:
                    # Process check failed, continue anyway
                    print(f"[WARNING] Could not check SC2 processes: {proc_error}")

                continue
        except KeyboardInterrupt:
            print("\n[STOP] Training stopped by user.")
            # Stop local monitoring server on interrupt
            if local_server_manager:
                print("[INFO] Stopping local monitoring server...")
                local_server_manager.stop_server()
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

    # IMPROVED: Stop background learner before exiting
    if background_learner:
        print("\n[INFO] Stopping background parallel learner...")
        background_learner.stop()
        stats = background_learner.get_stats()
        print(f"[BACKGROUND LEARNER] Final stats:")
        print(f"  - Replays Analyzed: {stats['replays_analyzed']}")
        print(f"  - Models Trained: {stats['models_trained']}")
        print(f"  - Total Processing Time: {stats['total_processing_time']:.2f}s")
        print(f"  - Errors: {stats['errors']}")

    # Stop local monitoring server
    if local_server_manager:
        print("\n[INFO] Stopping local monitoring server...")
        local_server_manager.stop_server()

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

 # ? NEW: Auto-extract and learn from training data after training ends
 if game_count > 0:
        print("\n" + "=" * 70)
        print("AUTO-EXTRACTING AND LEARNING FROM TRAINING DATA")
        print("=" * 70)
 try:
 # Import extractor module - add parent directory to path
 script_dir = Path(__file__).parent
 if str(script_dir) not in sys.path:
 sys.path.insert(0, str(script_dir))

 from tools.extract_and_train_from_training import TrainingDataExtractor
 from datetime import datetime

 extractor = TrainingDataExtractor()

 # Extract data
            print("\n[STEP 1] Extracting training data...")
 training_data = extractor.extract_training_stats()
 comparisons = extractor.extract_build_order_comparisons()
 session_stats = extractor.extract_session_stats()

 if training_data or comparisons:
 # Analyze data
                print("\n[STEP 2] Analyzing training data...")
 analysis = extractor.analyze_training_data(training_data)

 # Learn from data
                print("\n[STEP 3] Learning from training data...")
 learned_params = extractor.learn_from_training_data(
 training_data,
 comparisons,
 learning_rate = 0.1
 )

 # Save extracted data
                print("\n[STEP 4] Saving extracted data...")
 extractor.save_extracted_data(
 training_data,
 comparisons,
 analysis,
 learned_params
 )

 # Generate and print report
                print("\n[STEP 5] Generating report...")
 report = extractor.generate_report(analysis, learned_params)
                print("\n" + report)

 # Save report
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = extractor.output_dir / f"report_{timestamp}.txt"
                with open(report_file, 'w', encoding='utf-8') as f:
 f.write(report)
                print(f"\n[SAVED] Report: {report_file}")

                print("\n" + "=" * 70)
                print("EXTRACTION AND LEARNING COMPLETE")
                print("=" * 70)
 else:
                print("[INFO] No training data found to extract. Skipping extraction.")
 except Exception as e:
            print(f"\n[WARNING] Failed to extract and learn from training data: {e}")
            print("[INFO] You can manually run: python -m wicked_zerg_challenger.tools.extract_and_train_from_training")
 import traceback
 traceback.print_exc()

if __name__ == "__main__":
 main()