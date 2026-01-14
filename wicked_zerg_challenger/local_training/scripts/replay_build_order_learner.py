# -*- coding: utf-8 -*-

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import statistics

try:
    import sc2reader
    SC2READER_AVAILABLE = True
except ImportError:
    SC2READER_AVAILABLE = False
    print("[WARNING] sc2reader not installed. Install with: pip install sc2reader")

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


# Pro player names to filter (Zerg players)
PRO_ZERG_PLAYERS = {
    "serral", "reynor", "dark", "solar", "rogue", "soo", "shin",
    "byun", "maru", "oliveira", "scarlett", "spirit", "firefly",
    "kelazhur", "elazer", "nerchio", "snute", "lambo", "stephano"
}


class ReplayBuildOrderExtractor:
    def __init__(self, replay_dir: str = None):
        # IMPROVED: Use environment variable or flexible path detection
        # Priority 1: D:\replays\replays (all Zerg pro gamer replays)
        if replay_dir is None:
            replay_dir = os.environ.get("REPLAY_ARCHIVE_DIR")
            if not replay_dir or not os.path.exists(replay_dir):
                # Try common locations (priority: D:\replays\replays)
                possible_paths = [
                    Path("D:/replays/replays"),  # All Zerg pro gamer replays (highest priority)
                    Path(__file__).parent.parent / "replays_archive",
                    Path.home() / "replays" / "replays",
                    Path.home() / "replays",
                    Path("replays_archive"),
                ]
                for path in possible_paths:
                    if path.exists():
                        replay_dir = str(path)
                        break
                else:
                    replay_dir = "D:/replays/replays"  # Default to Zerg pro gamer replays directory
        self.replay_dir = Path(replay_dir)
        self.build_orders: List[Dict] = []
        self.timing_stats: Dict[str, List[float]] = defaultdict(list)

        # IMPROVED: Ensure replay directory exists
        self.replay_dir.mkdir(parents=True, exist_ok=True)

    def scan_replays(self) -> List[Path]:
        """Scan replay directory for valid replay files"""
        if not self.replay_dir.exists():
            logger.warning(f"Replay directory not found: {self.replay_dir}")
            return []

        replay_files = list(self.replay_dir.glob("*.SC2Replay"))
        logger.info(f"Found {len(replay_files)} replay files in {self.replay_dir}")
        return replay_files

    def extract_build_order(self, replay_path: Path, phase_focus: Optional[Dict] = None) -> Optional[Dict]:
        """Extract build order from a single replay file"""
        if not SC2READER_AVAILABLE:
            logger.error("sc2reader not available. Cannot extract build orders.")
            return None

        try:
            replay = sc2reader.load_replay(str(replay_path), load_map=True)

            # IMPROVED: Strict Zerg player validation using sc2reader metadata
            # Always use play_race attribute from replay metadata (most reliable)
            zerg_player = None
            pro_zerg_player = None

            # IMPROVED: First pass - find Zerg players by race (strict validation)
            for player in replay.players:
                # CRITICAL: Always check play_race attribute (most reliable)
                if hasattr(player, 'play_race'):
                    player_race = str(player.play_race).lower()
                    if player_race == "zerg":
                        player_name_lower = (player.name or "").lower()
                        # Prioritize pro players
                        if any(pro_name in player_name_lower for pro_name in PRO_ZERG_PLAYERS):
                            pro_zerg_player = player
                            break
                        elif not zerg_player:
                            zerg_player = player

            # IMPROVED: Second pass - if no Zerg found by race, check alternative methods
            if not zerg_player and not pro_zerg_player:
                # Fallback: Check if any player has Zerg-related indicators
                # But this should be rare - most replays have proper race metadata
                for player in replay.players:
                    if hasattr(player, 'name'):
                        player_name_lower = (player.name or "").lower()
                        # Only use name-based detection if race metadata is missing
                        if not hasattr(player, 'play_race') or player.play_race is None:
                            if any(zerg_keyword in player_name_lower for zerg_keyword in ["zerg", "z", "zv"]):
                                logger.warning(f"Using name-based Zerg detection for {replay_path.name} (race metadata missing)")
                                zerg_player = player
                                break

            # Prefer pro player if found
            zerg_player = pro_zerg_player if pro_zerg_player else zerg_player

            # IMPROVED: Final validation - ensure we have a valid Zerg player
            if not zerg_player:
                logger.debug(f"No Zerg player found in {replay_path.name} (strict validation)")
                return None

            # IMPROVED: Double-check race attribute (safety check)
            if hasattr(zerg_player, 'play_race'):
                final_race = str(zerg_player.play_race).lower()
                if final_race != "zerg":
                    logger.warning(f"Player {zerg_player.name} race mismatch: {final_race} (expected Zerg) in {replay_path.name}")
                    return None

            # IMPROVED: Extract build order events with better tracking
            build_order = {
                "replay_file": replay_path.name,
                "player_name": zerg_player.name,
                "map_name": replay.map_name if hasattr(replay, 'map_name') else "Unknown",
                "game_length": replay.game_length.seconds if hasattr(replay, 'game_length') else 0,
                "timings": {}
            }

            # IMPROVED: Track structure/unit creation events
            # Map SC2 unit type names to our parameter names
            unit_to_parameter = {
                "Hatchery": "natural_expansion_supply",
                "Extractor": "gas_supply",
                "SpawningPool": "spawning_pool_supply",
                "RoachWarren": "roach_warren_supply",
                "HydraliskDen": "hydralisk_den_supply",
                "Lair": "lair_supply",
                "Hive": "hive_supply",
            }

            # IMPROVED: Extract from tracker events (more reliable than game events)
            # CRITICAL: Track supply history to filter out cancellations and unit losses
            supply_history: Dict[float, int] = {}  # time -> supply
            unit_creation_events: List[Tuple[str, float, int]] = []  # (unit_name, time, supply)

            if hasattr(replay, 'tracker_events'):
                for event in replay.tracker_events:
                    try:
                        if hasattr(event, 'player') and event.player == zerg_player:
                            # Track supply history for cancellation/loss detection
                            if hasattr(event, 'second') and hasattr(event, 'food_used'):
                                supply_history[event.second] = event.food_used

                            # Track unit born events (structures being created)
                            if hasattr(event, 'unit') and hasattr(event, 'second'):
                                unit = event.unit
                                if hasattr(unit, 'name'):
                                    unit_name = unit.name
                                    if unit_name in unit_to_parameter:
                                        param_name = unit_to_parameter[unit_name]
                                        # Get supply at time of event
                                        supply = self._get_supply_at_time(replay, zerg_player, event.second)
                                        if supply > 0:
                                            unit_creation_events.append((param_name, event.second, supply))
                    except Exception:
                        continue

            # CRITICAL: Filter out cancellations and unit losses
            # Check if supply decreases significantly after unit creation (indicates cancellation/loss)
            for param_name, creation_time, creation_supply in unit_creation_events:
                if param_name not in build_order["timings"]:
                    # Check supply changes in the next 10 seconds
                    is_valid = True
                    check_times = [t for t in supply_history.keys() if creation_time <= t <= creation_time + 10.0]
                    if check_times:
                        max_supply_after = max(supply_history[t] for t in check_times)
                        supply_decrease = creation_supply - max_supply_after

                        # If supply decreases by more than 5, likely a cancellation or unit loss
                        # (5 supply = 1 worker or small unit loss)
                        if supply_decrease > 5:
                            logger.debug(f"Filtered {param_name} at {creation_time}s: supply decreased by {supply_decrease} (likely cancellation/loss)")
                            is_valid = False

                    if is_valid:
                        build_order["timings"][param_name] = {
                            "supply": creation_supply,
                            "time": creation_time
                        }

            # IMPROVED: Also try to extract from game events as fallback
            for event in replay.events:
                try:
                    if hasattr(event, 'player') and event.player == zerg_player:
                        # Track structure creation
                        if hasattr(event, 'unit_type_name'):
                            unit_name = event.unit_type_name
                            if unit_name in unit_to_parameter:
                                param_name = unit_to_parameter[unit_name]
                                if param_name not in build_order["timings"]:
                                    # Get supply at time of event
                                    supply = self._get_supply_at_time(replay, zerg_player, event.second)
                                    if supply > 0:
                                        build_order["timings"][param_name] = {
                                            "supply": supply,
                                            "time": event.second
                                        }
                except Exception:
                    continue

            return build_order if build_order["timings"] else None

        except Exception as e:
            logger.error(f"Error extracting build order from {replay_path.name}: {e}")
            return None

    def _get_supply_at_time(self, replay, player, time_seconds: float) -> int:
        """Get player supply at a specific time"""
        try:
            # IMPROVED: Try multiple methods to get supply
            # Method 1: Tracker events (most reliable)
            if hasattr(replay, 'tracker_events'):
                closest_supply = None
                closest_time_diff = float('inf')

                for event in replay.tracker_events:
                    try:
                        if hasattr(event, 'player') and event.player == player:
                            if hasattr(event, 'second') and hasattr(event, 'food_used'):
                                time_diff = abs(event.second - time_seconds)
                                if time_diff < closest_time_diff:
                                    closest_time_diff = time_diff
                                    closest_supply = event.food_used
                    except Exception:
                        continue

                if closest_supply is not None and closest_time_diff < 5.0:  # Within 5 seconds
                    return closest_supply

            # Method 2: Try to estimate from units (fallback)
            # Count units and estimate supply
            try:
                if hasattr(replay, 'tracker_events'):
                    supply_estimate = 0
                    for event in replay.tracker_events:
                        if hasattr(event, 'player') and event.player == player:
                            if hasattr(event, 'second') and abs(event.second - time_seconds) < 2.0:
                                if hasattr(event, 'unit') and hasattr(event.unit, 'supply_cost'):
                                    supply_estimate += event.unit.supply_cost
                    if supply_estimate > 0:
                        return supply_estimate
            except Exception:
                pass

            return 0
        except Exception:
            return 0

    def _extract_strategies(
        self,
        replay_path: Path,
        build_order: Dict,
        phase_focus: Dict,
        strategy_db
    ) -> List[Dict[str, Any]]:
        """
        Extract strategies from replay based on learning phase

        Returns:
            List of extracted strategies
        """
        strategies = []

        try:
            from scripts.strategy_database import StrategyType, MatchupType

            replay = sc2reader.load_replay(str(replay_path), load_map=True)

            # Determine matchup
            zerg_player = None
            opponent = None
            matchup = MatchupType.ZVT  # Default

            for player in replay.players:
                if hasattr(player, 'play_race'):
                    race = str(player.play_race).lower()
                    if race == "zerg":
                        zerg_player = player
                    else:
                        opponent = player

            if opponent and hasattr(opponent, 'play_race'):
                opp_race = str(opponent.play_race).lower()
                if opp_race == "terran":
                    matchup = MatchupType.ZVT
                elif opp_race == "protoss":
                    matchup = MatchupType.ZVP
                elif opp_race == "zerg":
                    matchup = MatchupType.ZVZ

            phase = phase_focus.get("phase", "unknown")
            focus_areas = phase_focus.get("focus", [])

            # Extract strategies based on phase
            if phase == "early_game":
                # Extract build order strategies
                if "build_order" in focus_areas and build_order.get("timings"):
                    strategy_id = strategy_db.add_strategy(
                        StrategyType.BUILD_ORDER,
                        matchup,
                        timing=0.0,
                        description=f"Opening build order: {build_order.get('player_name', 'Unknown')}",
                        extracted_from=replay_path.name,
                        details={"timings": build_order.get("timings", {})}
                    )
                    strategies.append({
                        "strategy_id": strategy_id,
                        "type": "build_order",
                        "timing": 0.0,
                        "description": f"Opening build order"
                    })

            elif phase == "mid_game":
                # Extract micro control and multitasking strategies
                if "micro_control" in focus_areas or "multitasking" in focus_areas:
                    # Look for drop timings, engagements
                    for event in replay.events:
                        if hasattr(event, 'player') and event.player == zerg_player:
                            if hasattr(event, 'name') and 'Drop' in str(event.name):
                                timing = getattr(event, 'second', 0)
                                strategy_id = strategy_db.add_strategy(
                                    StrategyType.DROP_TIMING,
                                    matchup,
                                    timing=timing,
                                    description=f"Drop timing at {timing}s",
                                    extracted_from=replay_path.name
                                )
                                strategies.append({
                                    "strategy_id": strategy_id,
                                    "type": "drop_timing",
                                    "timing": timing,
                                    "description": f"Drop timing at {timing}s"
                                })
                                break

            elif phase == "late_game":
                # Extract macro and spell unit strategies
                if "spell_units" in focus_areas:
                    # Look for spell unit usage (Vipers, Infestors, etc.)
                    for event in replay.events:
                        if hasattr(event, 'player') and event.player == zerg_player:
                            if hasattr(event, 'unit_type_name'):
                                unit_name = str(event.unit_type_name).lower()
                                if any(spell_unit in unit_name for spell_unit in ["viper", "infestor", "swarmhost"]):
                                    timing = getattr(event, 'second', 0)
                                    strategy_id = strategy_db.add_strategy(
                                        StrategyType.MICRO_CONTROL,
                                        matchup,
                                        timing=timing,
                                        description=f"Spell unit usage: {unit_name}",
                                        extracted_from=replay_path.name
                                    )
                                    strategies.append({
                                        "strategy_id": strategy_id,
                                        "type": "spell_unit",
                                        "timing": timing,
                                        "description": f"Spell unit: {unit_name}"
                                    })
                                    break

        except Exception as e:
            logger.warning(f"Failed to extract strategies from {replay_path.name}: {e}")

        return strategies

    def learn_from_replays(self, max_replays: int = 100) -> Dict[str, float]:
        """
        Learn optimal build order timings from replays

        IMPROVED: Integrates with learning tracker and phase-based focused learning
        - Iterations 1-2: Early game (build order focus)
        - Iterations 3-4: Mid game (unit composition, skirmishes)
        - Iteration 5+: Late game (macro, spell units)
        """
        # IMPROVED: Use learning tracker to get replays that need training
        try:
            import sys
            from pathlib import Path
            script_dir = Path(__file__).parent
            if str(script_dir) not in sys.path:
                sys.path.insert(0, str(script_dir))
            from replay_learning_manager import ReplayLearningTracker
            from learning_logger import LearningLogger
            from strategy_database import StrategyDatabase, StrategyType, MatchupType

            # CRITICAL: Completed replays go to D:\replays\replays\completed
            completed_dir = Path("D:/replays/replays/completed")
            completed_dir.mkdir(parents=True, exist_ok=True)
            tracking_file = self.replay_dir / ".learning_tracking.json"
            tracker = ReplayLearningTracker(tracking_file, min_iterations=5)

            # Setup learning logger
            log_file = self.replay_dir / "learning_log.txt"
            learning_logger = LearningLogger(log_file)

            # Setup strategy database
            strategy_db_path = self.replay_dir / "strategy_db.json"
            strategy_db = StrategyDatabase(strategy_db_path)

            # Get replays that need training (not yet completed)
            replay_files = tracker.get_replays_for_training(self.replay_dir, completed_dir)

            if not replay_files:
                logger.warning("No replay files found that need training. All replays may be completed.")
                return {}

            # Limit number of replays to process
            replay_files = replay_files[:max_replays]

        except ImportError as e:
            logger.warning(f"Advanced learning modules not available: {e}")
            # Fallback: Use simple scan
            replay_files = self.scan_replays()
            if not replay_files:
                logger.warning("No replay files found. Cannot learn build orders.")
                return {}
            replay_files = replay_files[:max_replays]
            tracker = None
            learning_logger = None
            strategy_db = None

        logger.info(f"Processing {len(replay_files)} replays...")

        # CRITICAL: Load crash handler to prevent infinite retry loops
        crash_handler = None
        try:
            from scripts.replay_crash_handler import ReplayCrashHandler
            crash_log_file = self.replay_dir / "crash_log.json"
            crash_handler = ReplayCrashHandler(crash_log_file, max_crashes=3)
            # Recover stale sessions (mark as crashed if > 30 minutes old)
            # CRITICAL: Reduced to 30 minutes to clear stale sessions much faster
            # If a session is older than 30 minutes, it's likely a crashed/stuck process
            # This prevents "Already being learned" false positives
            crash_handler.recover_stale_sessions(max_age_seconds=1800)  # 30 minutes
        except ImportError:
            logger.warning("replay_crash_handler not available - crash recovery disabled")

        extracted_count = 0
        for replay_path in replay_files:
            # CRITICAL: Check if replay is marked as bad (repeated crashes)
            if crash_handler and crash_handler.is_bad_replay(replay_path):
                crash_count = crash_handler.get_crash_count(replay_path)
                logger.warning(f"[BAD REPLAY] {replay_path.name} - Skipping (crashed {crash_count} times)")
                continue

            # CRITICAL: Check if replay is already in progress (prevent duplicate processing)
            # FORCE MODE: Completely disabled to force replay analysis
            # The is_in_progress check is disabled - all replays will be processed
            # NOTE: Stale session auto-clearing in is_in_progress() is still active but this check is bypassed
            # DISABLED FOR FORCE MODE - DO NOT ENABLE
            # if crash_handler and crash_handler.is_in_progress(replay_path):
            #     logger.info(f"[IN PROGRESS] {replay_path.name} - Already being learned, skipping")
            #     continue

            # CRITICAL: Get current learning count BEFORE processing
            current_count = 0
            if tracker:
                current_count = tracker.get_learning_count(replay_path)
                # FORCE MODE: Temporarily disabled to force replay analysis
                # Skip if already completed (5+ iterations) - DISABLED FOR FORCE MODE
                # if tracker.is_completed(replay_path):
                #     logger.info(f"[SKIP] {replay_path.name} - Already completed ({current_count} iterations)")
                #     continue
                iteration = current_count + 1
                phase_info = tracker.get_phase_focus(iteration)
            else:
                iteration = 1
                phase_info = {"phase": "unknown", "focus": [], "weights": {}}

            # CRITICAL: Mark learning start to prevent duplicate processing
            if crash_handler:
                crash_handler.mark_learning_start(replay_path)

            try:
                # Extract build order with phase-specific focus
                build_order = self.extract_build_order(replay_path, phase_focus=phase_info)

                if build_order:
                    self.build_orders.append(build_order)
                    extracted_count += 1

                    # Extract strategies based on phase
                    strategies_extracted = []
                    if strategy_db and learning_logger:
                        strategies_extracted = self._extract_strategies(
                            replay_path, build_order, phase_info, strategy_db
                        )

                    # CRITICAL: Mark replay as trained (increment learning count)
                    # This is a hard requirement - MUST be called after each learning iteration
                    if tracker:
                        new_count = tracker.increment_learning_count(replay_path)
                        logger.info(f"  [LEARNING COUNT] {replay_path.name}: {current_count} → {new_count}/{tracker.min_iterations} iterations (Phase: {phase_info['phase']})")

                        # CRITICAL: Also update learning_status.json for hard requirement enforcement
                        try:
                            from scripts.learning_status_manager import LearningStatusManager
                            status_file = self.replay_dir / "learning_status.json"
                            status_manager = LearningStatusManager(status_file, min_iterations=5)
                            status_count = status_manager.increment_learning_count(replay_path)
                            logger.info(f"  [STATUS TRACKER] {replay_path.name}: {status_count}/{status_manager.min_iterations} iterations")
                        except ImportError:
                            pass  # learning_status_manager not available

                        # Log learning completion
                        if learning_logger:
                            learning_logger.log_learning_completion(
                                replay_path, new_count, phase_info["phase"],
                                strategies_extracted, phase_info
                            )

                        # CRITICAL: Only move to completed folder if 5+ iterations (hard requirement)
                        if tracker.is_completed(replay_path):
                            if tracker.move_completed_replay(replay_path, completed_dir):
                                logger.info(f"  [COMPLETED] Moved {replay_path.name} to completed folder ({new_count} iterations)")
                        else:
                            logger.info(f"  [IN PROGRESS] {replay_path.name} needs {tracker.min_iterations - new_count} more iterations")

                    # CRITICAL: Mark learning complete (successful)
                    if crash_handler:
                        crash_handler.mark_learning_complete(replay_path)

            except Exception as e:
                # CRITICAL: Mark as crashed on exception
                if crash_handler:
                    crash_count = crash_handler.mark_crash(replay_path)
                    logger.error(f"[CRASH] {replay_path.name} - Learning failed (crash count: {crash_count}): {e}")
                else:
                    logger.error(f"[ERROR] {replay_path.name} - Learning failed: {e}")
                continue

                # Collect timing statistics
                for param_name, timing_data in build_order["timings"].items():
                    if "supply" in timing_data:
                        self.timing_stats[param_name].append(timing_data["supply"])

        logger.info(f"Extracted build orders from {extracted_count} replays")

        # Calculate learned parameters (median supply timings)
        learned_params = {}
        for param_name, supply_values in self.timing_stats.items():
            if supply_values:
                # Use median for robustness against outliers
                median_supply = statistics.median(supply_values)
                learned_params[param_name] = int(round(median_supply))
                logger.info(f"Learned {param_name}: {median_supply:.1f} supply (from {len(supply_values)} samples)")

        return learned_params

    def save_learned_parameters(self, learned_params: Dict[str, float], output_file: str = None):
        """
        Save learned parameters to JSON file

        Output path: D:\replays\archive\training_YYYYMMDD_HHMMSS\learned_build_orders.json
        """
        from datetime import datetime

        # Create training output directory with timestamp
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_dir = Path("D:/replays/archive") / f"training_{timestamp}"
            archive_dir.mkdir(parents=True, exist_ok=True)
            output_path = archive_dir / "learned_build_orders.json"
        else:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "learned_parameters": learned_params,
            "source_replays": len(self.build_orders),
            "replay_directory": str(self.replay_dir),
            "build_orders": self.build_orders[:10]  # Save first 10 for reference
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved learned parameters to {output_path}")
        print(f"[SAVE] Training results saved to: {output_path}")
        return output_path


def update_config_with_learned_params(learned_params: Dict[str, float]):
    """Update config.py with learned parameters"""
    config_path = Path(__file__).parent / "config.py"

    if not config_path.exists():
        logger.warning(f"config.py not found at {config_path}")
        return

    # Read current config
    with open(config_path, 'r', encoding='utf-8') as f:
        config_content = f.read()

    # Update get_learned_parameter function defaults
    # This is a simple approach - in production, you might want a more sophisticated update mechanism
    logger.info("Learned parameters (update config.py manually or use JSON file):")
    for param_name, value in learned_params.items():
        logger.info(f"  {param_name}: {value}")

    # Save to separate JSON file that get_learned_parameter can read
    # Also save to local_training for backward compatibility
    learned_json_path = Path(__file__).parent / "learned_build_orders.json"
    with open(learned_json_path, 'w', encoding='utf-8') as f:
        json.dump(learned_params, f, indent=2)

    logger.info(f"Saved learned parameters to {learned_json_path} (local copy for config.py)")
    logger.info("config.py will read from learned_build_orders.json automatically")


def main():
    """Main function to learn build orders from replays"""
    print("\n" + "="*70)
    print("REPLAY BUILD ORDER LEARNING SYSTEM")
    print("="*70)

    if not SC2READER_AVAILABLE:
        print("\n[ERROR] sc2reader not installed!")
        print("Install with: pip install sc2reader")
        return

    # IMPROVED: Use flexible path detection
    # Priority 1: D:\replays\replays (training source directory)
    # Priority 2: Environment variable
    # Priority 3: Common locations
    default_replay_dir = os.environ.get("REPLAY_ARCHIVE_DIR")
    if not default_replay_dir or not os.path.exists(default_replay_dir):
        # Try common locations (priority: training source directory)
        possible_paths = [
            Path("D:/replays/replays"),  # Training source directory (highest priority)
            Path(__file__).parent.parent / "replays_archive",
            Path.home() / "replays" / "replays",
            Path.home() / "replays",
            Path("replays_archive"),
        ]
        for path in possible_paths:
            if path.exists():
                default_replay_dir = str(path)
                break
        else:
            default_replay_dir = "D:/replays/replays"  # Default to training source directory

    extractor = ReplayBuildOrderExtractor(replay_dir=default_replay_dir)

    learned_params = extractor.learn_from_replays(max_replays=100)

    if not learned_params:
        print("\n[WARNING] No build orders extracted. Check replay directory.")
        return

    # Save learned parameters
    extractor.save_learned_parameters(learned_params)
    update_config_with_learned_params(learned_params)

    print("\n" + "="*70)
    print("LEARNING COMPLETE")
    print("="*70)
    print(f"Learned {len(learned_params)} parameters from {len(extractor.build_orders)} replays")
    print("\nLearned Parameters:")
    for param_name, value in learned_params.items():
        print(f"  {param_name}: {value}")
    print("\nThese parameters will be used by production_manager.py")
    print("="*70 + "\n")

    # Auto commit after training (if enabled)
    auto_commit_enabled = os.environ.get("AUTO_COMMIT_AFTER_TRAINING", "false").lower() == "true"
    if auto_commit_enabled:
        print("\n[INFO] Auto commit enabled - committing changes...")
        try:
            import subprocess
            script_path = Path(__file__).parent.parent / "tools" / "auto_commit_after_training.py"
            if script_path.exists():
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=str(Path(__file__).parent.parent),
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                if result.returncode == 0:
                    print("[OK] Auto commit completed successfully")
                else:
                    print(f"[WARNING] Auto commit failed: {result.stderr}")
            else:
                print(f"[WARNING] Auto commit script not found: {script_path}")
        except Exception as e:
            print(f"[WARNING] Auto commit error: {e}")


if __name__ == "__main__":
    main()
