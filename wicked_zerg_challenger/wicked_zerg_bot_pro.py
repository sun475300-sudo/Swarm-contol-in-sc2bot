

import asyncio
import gc
import io
import json
import os
import random
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
    import logging
from combat_manager import CombatManager
from combat_tactics import CombatTactics
from config import Config, EnemyRace, GamePhase
from economy_manager import EconomyManager
from intel_manager import IntelManager
    from micro_controller import MicroController
from rogue_tactics_manager import RogueTacticsManager
from personality_manager import PersonalityManager
from production_manager import ProductionManager
from production_resilience import ProductionResilience
from queen_manager import QueenManager
from scouting_system import ScoutingSystem
from telemetry_logger import TelemetryLogger
    from strategy_analyzer import StrategyAnalyzer
    from bot_api_connector import bot_connector
    from genai_self_healing import GenAISelfHealing, init_self_healing
    from debug_visualizer import DebugVisualizer as SC2DebugVisualizer
    from zerg_net import Action, ReinforcementLearner, ZergNet
        from pathlib import Path
        from config import Config
                from spell_unit_manager import SpellUnitManager
                import traceback as tb
                            from pathlib import Path as PathLib
            import psutil
            from zerg_net import MODELS_DIR

from sc2.bot_ai import BotAI  # type: ignore
from sc2.data import Race, Result  # type: ignore
from sc2.ids.ability_id import AbilityId  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore
    from sc2.ids.buff_id import BuffId as SC2BuffId
import numpy as np
    from loguru import logger
    import torch
                                    from loguru import logger as loguru_logger
                        from sc2.position import Point2
                        from sc2.ids.unit_typeid import UnitTypeId

# -*- coding: utf-8 -*-
try:

    BuffId = SC2BuffId  # type: ignore[assignment]
except ImportError:
    # Fallback if BuffId is not available
    class BuffId:
        METABOLICBOOST = None



# Antigravity easter egg removed - no longer used

# Logger setup for clean text output with safe buffer handling
try:

    # Remove default handler and add safe handler with enqueue=True
    # enqueue=True processes logs asynchronously to prevent buffer detachment errors
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        colorize=True,
        enqueue=True,  # CRITICAL: Async logging prevents buffer detachment errors
        catch=True,  # Catch exceptions during logging
        level="INFO",
    )
except ImportError:

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

# Safe Windows encoding setup without detaching underlying buffers
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# MicroController - optional import
try:
except ImportError:
    MicroController = None  # type: ignore[assignment]


# 🎯 New modules - Code slimdown

# IMPROVED: Strategy analyzer (optional - gracefully handles missing module)
try:
except Exception:
    StrategyAnalyzer = None  # type: ignore[assignment]

try:
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False

# IMPROVED: Gemini Self-Healing System (optional)
try:
    GEMINI_SELF_HEALING_AVAILABLE = True
except ImportError:
    GEMINI_SELF_HEALING_AVAILABLE = False
    GenAISelfHealing = None  # type: ignore[assignment]
    init_self_healing = None  # type: ignore[assignment]

EarlyDefenseManager = None
HotLoader = None
GasMaximizer = None
# Debug Visualizer: Real-time dashboard
try:

    DebugVisualizer = SC2DebugVisualizer  # type: ignore[assignment]
except ImportError:
    class DebugVisualizer:
        def __init__(self): pass
        def update_dashboard(self, *args, **kwargs): pass
        def record_event(self, *args, **kwargs): pass
        def generate_debug_chart(self, *args, **kwargs): pass
        def get_event_summary(self): return None
        def close(self): pass

# PyTorch Neural Network (Optional)
torch = None
try:


    PYTORCH_AVAILABLE = True
    print("[OK] PyTorch loaded")
except ImportError as e:
    print(f"[WARNING] PyTorch not available: {e}")
    PYTORCH_AVAILABLE = False
    ZergNet = ReinforcementLearner = Action = None
except Exception as e:
    print(f"[WARNING] PyTorch load error: {e}")
    traceback.print_exc()
    PYTORCH_AVAILABLE = False
    ZergNet = ReinforcementLearner = Action = None

class WickedZergBotPro(BotAI):
    def __init__(
        self,
        train_mode: bool = True,
        instance_id: int = 0,
        personality: str = "serral",
        opponent_race: Optional[Race] = None,
        game_count: int = 0,
    ):
        """
        Bot initialization

        Args:
            train_mode: Enable training mode
            instance_id: Instance ID (0=main process, 1, 2=sub process)
            personality: Persona ("serral", "dark", "reynor")
            opponent_race: Opponent race (Race.Terran, Race.Protoss, Race.Zerg)
            game_count: Current game number (for terminal output)
        """
        super().__init__()


        self.instance_id = instance_id
        self.personality = personality.lower()
        self.opponent_race = opponent_race
        self.game_count = game_count
        self.already_logged_pool = False
        # Let ProductionManager own tech building construction to avoid duplicates with EconomyManager
        self.production_manager_owns_tech = True
        self.last_result = "N/A"

        # 🎭 Personality Manager - Bot personality and chat system
        self.personality_manager = PersonalityManager(self, personality)
        self.last_chat_time = -120  # Backward compatibility


        # Logging System Setup
        # CRITICAL: Log files go to logs/ directory (project root), not local_training/logs/
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # local_training -> project root
        self.log_path = os.path.join(project_root, "logs")
        self.data_path = os.path.join(script_dir, "data")  # data/ stays in local_training/
        os.makedirs(self.log_path, exist_ok=True)
        os.makedirs(self.data_path, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_path, f"log_{timestamp}.txt")

        self.log_enabled = True
        self.log_max_size_mb = 10
        self.log_levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
        self.log_filters = {
            "unit_death": True,
            "attack_events": True,
            "build_events": True,
            "error_traceback": True,
        }

        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write(f"=== Monsterbot Log ===\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Personality: {self.personality}\n{'=' * 50}\n\n")
        except Exception as e:
            print(f"[WARNING] Log init failed: {e}")
            self.log_file = None

        # GPU Device Configuration
        if PYTORCH_AVAILABLE and torch is not None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                print(f"[DEVICE] GPU: {gpu_name} (30% target)")
            else:
                print(f"[DEVICE] CPU mode")
        else:
            self.device = None
            print(f"[DEVICE] PyTorch unavailable")

        self.train_mode = True
        self.epsilon = 0.3 if train_mode else 0.0
        self.model_filename = f"zerg_net_{self.instance_id}.pt"
        self.step_size = 16
        self.neural_network_inference_interval = 24
        self.last_neural_network_inference = -1
        self._cached_neural_action = None
        _config = Config()
        gpu_target_env = os.environ.get("GPU_USAGE_TARGET", str(_config.GPU_USAGE_TARGET))
        try:
            self.gpu_usage_target = float(gpu_target_env)
        except ValueError:
            self.gpu_usage_target = _config.GPU_USAGE_TARGET

        self.config = Config()
        self.game_phase: GamePhase = GamePhase.OPENING

        # Managers (initialized later)
        self.intel: Optional[IntelManager] = None
        self.economy: Optional[EconomyManager] = None
        self.production: Optional[ProductionManager] = None
        self.combat: Optional[CombatManager] = None
        self.rogue_tactics: Optional[RogueTacticsManager] = None
        self.spell_unit_manager = None  # Will be initialized in on_start
        self.scout: Optional[ScoutingSystem] = None
        self.scout_tag = None
        self.strategy_analyzer: Optional[StrategyAnalyzer] = None
        # strategy_engine removed (deprecated, now using StrategyAnalyzer + StrategyHub)
        self.combat_tactics: Optional[CombatTactics] = None
        self.production_resilience: Optional[ProductionResilience] = None
        self.micro: Optional[MicroController] = None
        self.queen_manager: Optional[QueenManager] = None
        self.gas_maximizer: Optional[Any] = None  # type: ignore[type-arg]

        self.iteration: int = 0  # type: ignore[redeclaration,assignment]
        self.current_win_rate: float = 50.0

        # Drone survival stats
        self.drone_threat_detected: int = 0
        self.drone_escaped_successfully: int = 0
        self.drone_losses_to_enemy: int = 0
        self.last_drone_count: int = 0

        self.mid_game_strong_build_active: bool = False  # type: ignore[assignment]
        self.visualizer = None

        # Enemy tech tracking
        self.enemy_tech: str = "GROUND"
        self.enemy_tech_detected: Dict[str, Any] = {
            "air_tech": False,
            "mech_tech": False,
            "bio_tech": False,
            "detected_time": 0.0,
        }

        # Neural Network System
        self.use_neural_network = PYTORCH_AVAILABLE and train_mode
        self.neural_network: Optional[Any] = None  # type: ignore[assignment, type-arg]
        self.current_action: Optional[Any] = None  # type: ignore[assignment, type-arg]

        if self.use_neural_network:
            try:
                # Input: 5D [minerals, vespene, supply, drones, army]
                # Output: 4 actions [ATTACK, DEFENSE, ECONOMY, TECH_FOCUS]
                if ZergNet:
                    # IMPROVED: Use 15 inputs (self(5) + enemy(10) comprehensive intelligence)
                    model = ZergNet(input_size=15, hidden_size=64, output_size=4)  # type: ignore[misc]
                else:
                    model = None

                if model is not None:
                    if self.device is not None and self.device.type == "cuda":
                        model = model.to(self.device)  # type: ignore[union-attr]
                        print(f"[OK] Model -> GPU: {self.device}")
                        if next(model.parameters()).is_cuda:
                            print(f"[OK] ✅ GPU confirmed")
                        else:
                            print(f"[WARNING] GPU not confirmed")
                    elif self.device is not None:
                        model = model.to(self.device)  # type: ignore[union-attr]
                        print(f"[OK] Model -> {self.device}")
                else:
                    print(f"[WARNING] Device is None (CPU default)")

                if ReinforcementLearner and model:
                    try:
                        # IMPROVED: Pass instance_id to prevent file conflicts in parallel training
                        self.neural_network = ReinforcementLearner(
                            model, learning_rate=0.001, instance_id=self.instance_id
                        )  # type: ignore[misc]
                        print(f"[OK] Neural network initialized")
                    except RuntimeError as e:
                        if "size mismatch" in str(e).lower():
                            print(f"[ERROR] Model mismatch, creating fresh model...")
                            if ZergNet:
                                # IMPROVED: Use 15 inputs (self(5) + enemy(10) comprehensive intelligence)
                                model = ZergNet(input_size=15, hidden_size=64, output_size=4)  # type: ignore[misc]
                                if self.device is not None:
                                    model = model.to(self.device)  # type: ignore[union-attr]
                                self.neural_network = ReinforcementLearner(
                                    model, learning_rate=0.001, instance_id=self.instance_id
                                )  # type: ignore[misc]
                                print(f"[OK] Fresh model created (5→4)")
                        else:
                            raise
                else:
                    self.neural_network = None
                print("[OK] Neural network active")
                if PYTORCH_AVAILABLE and torch is not None:
                    if torch.cuda.is_available():
                        gpu_name = torch.cuda.get_device_name(0)
                        print(f"[OK] ✅ GPU: {gpu_name} (30% usage)")
                    else:
                        print(f"[OK] ⚠️ CPU mode")
                else:
                    print("[OK] PyTorch N/A")
            except ImportError as e:
                print(f"[WARNING] NN module import error: {e}")
                self.use_neural_network = False
                self.neural_network = None
            except RuntimeError as e:
                print(f"[WARNING] NN runtime error: {e}")
                self.use_neural_network = False
                self.neural_network = None
            except Exception as e:
                print(f"[WARNING] NN init failed: {e}")
                traceback.print_exc()
                self.use_neural_network = False
                self.neural_network = None

        # Build order tracking
        self.build_order_completed = {
            "natural_expansion": False,
            "gas": False,
            "spawning_pool": False,
            "third_hatchery": False,
        }

        # 📊 Telemetry Logger - Training statistics and data recording
        self.telemetry_logger = TelemetryLogger(self, instance_id)
        # Backward compatibility
        self.game_log: list = []
        self.telemetry_data: list = self.telemetry_logger.telemetry_data
        self.telemetry_file: str = self.telemetry_logger.telemetry_file

        # IMPROVED: Gemini Self-Healing System - Automated error analysis and patching
        self.self_healing = None
        if GEMINI_SELF_HEALING_AVAILABLE and GenAISelfHealing:
            try:
                # Initialize with auto-patch disabled by default (manual review recommended)
                enable_auto_patch = os.environ.get("GEMINI_AUTO_PATCH", "false").lower() == "true"
                log_dir = Path(project_root) / "data" / "self_healing"
                self.self_healing = GenAISelfHealing(
                    api_key=None,  # Will use GOOGLE_API_KEY from environment
                    model_name="gemini-1.5-flash",  # Fast and cost-effective
                    enable_auto_patch=enable_auto_patch,
                    log_dir=log_dir
                )
                if self.self_healing.is_available():
                    print(f"[SELF-HEALING] ✅ Gemini Self-Healing initialized (model: gemini-1.5-flash, auto-patch: {enable_auto_patch})")
                else:
                    print(f"[SELF-HEALING] ⚠️ Gemini API not available (check GOOGLE_API_KEY environment variable)")
            except Exception as e:
                print(f"[WARNING] Failed to initialize Gemini Self-Healing: {e}")
                self.self_healing = None

        # Debug Visualizer (disabled for performance)
        class DummyVisualizer:
            def update_dashboard(self, bot): pass
            def close(self): pass
            def record_event(self, *args, **kwargs): pass
        self.debug_viz = DummyVisualizer()

        self.last_error_log_frame: int = -50

        # Analysis Hub (removed - using Vertex AI instead)
        self.analysis_hub = None
        self.battle_analyzer = None

        # Early Defense & Strategy
        self.early_defense = None

        try:
            self.strategy_analyzer = StrategyAnalyzer(self)
        except Exception as e:
            print(f"[WARNING] StrategyAnalyzer init failed: {e}")
            self.strategy_analyzer = None

        # strategy_engine: deprecated and removed
        # All strategic decisions now handled by StrategyAnalyzer + StrategyHub

        # 🎯 Strategy Hub - removed (using Vertex AI instead)
        self.strategy_hub = None

        try:
            self.combat_tactics = CombatTactics(self)
        except Exception as e:
            print(f"[WARNING] CombatTactics init failed: {e}")
            self.combat_tactics = None

        try:
            self.production_resilience = ProductionResilience(self)
        except Exception as e:
            print(f"[WARNING] ProductionResilience init failed: {e}")
            self.production_resilience = None

        # Combat Unit Whitelist (Zergling+)
        self.combat_unit_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKERMP,
            UnitTypeId.MUTALISK,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.ULTRALISK,
            UnitTypeId.BROODLORD,
            UnitTypeId.INFESTOR,
            UnitTypeId.VIPER,
        }

        # 🎯 Unit Role Definitions - Clear separation of unit purposes
        self.worker_unit_types = {UnitTypeId.DRONE}  # Workers: Resource gathering only
        self.scout_unit_types = {
            UnitTypeId.OVERLORD,
            UnitTypeId.OVERSEER,
        }  # Overlords/Overseers: Scouting and vision only

        # 🔢 Game iteration counter
        # Note: iteration already declared in __init__ (line 242), removed duplicate declaration

        # 🚪 Game end flag (ensure immediate end after GG)
        self.game_ended: bool = False  # True when game should end immediately

        # Victory detection debounce to exit cleanly after surrender
        self.victory_detected_time: Optional[float] = None

        # Hot-reload guard to avoid crashes when files are edited mid-game
        self.hot_reload_fail_until: float = 0.0

        # 🎮 Micro Ladder Mode Detection
        self.is_micro_ladder: bool = False  # Will be detected in on_start

        # 🗺️ Map Size Detection (for adaptive build order)
        self.map_size: str = "MEDIUM"  # SMALL, MEDIUM, LARGE
        self.map_rush_distance: float = 0.0  # Distance to enemy base

        # 📝 Logging Helper Variables
        self.last_log_iteration = 0  # Throttle logging frequency
        self.previous_unit_tags = set()  # Track unit tags for death detection
        self.previous_army_count = 0  # Track army count for death detection

        # 🚀 Rush Failure Detection & Mid-Game Strong Build Transition
        self.rush_attempted: bool = False  # Whether early rush was attempted
        self.rush_start_time: float = 0.0  # When rush attack started
        self.rush_failed: bool = False  # Whether rush failed
        # Note: mid_game_strong_build_active is already declared at line 248
        self.last_rush_check_time: float = 0.0  # Last time rush status was checked

        # 🎯 Enemy Unit Tracking - Essential for combat logic
        self.known_enemy_units = self.enemy_units  # Shortcut for enemy unit tracking

    async def on_building_construction_complete(self, unit):
        try:
            # 1. When new Hatchery (multi) completes, immediately send 3 workers to nearby minerals
            if unit.type_id == UnitTypeId.HATCHERY:
                # OPTIMIZED: Use closer_than() directly, no list conversion
                minerals_near_hatchery = self.mineral_field.closer_than(10, unit.position)
                if minerals_near_hatchery.exists:
                    # OPTIMIZED: Get closest workers to new hatchery (within 20 range)
                    # Process only first 3 workers (no need to iterate all)
                    nearby_workers = self.workers.closer_than(20, unit.position)
                    if nearby_workers.exists:
                        # OPTIMIZED: Process only first 3 workers
                        for worker in list(nearby_workers)[:3]:
                            try:
                                # Find closest mineral to new hatchery
                                closest_mineral = minerals_near_hatchery.closest_to(unit.position)
                                if closest_mineral:
                                    worker.gather(closest_mineral)
                                    if self.iteration % 100 == 0:
                                        print(
                                            f"[AUTO ASSIGN] [{int(self.time)}s] Assigned worker to new Hatchery at {unit.position}"
                                        )
                            except Exception:
                                continue

            # 2. When Extractor (gas) completes, immediately start 3 workers gathering gas
            elif unit.type_id == UnitTypeId.EXTRACTOR:
                # OPTIMIZED: Get closest workers to new extractor (expanded to 25 range for reliability)
                nearby_workers = self.workers.closer_than(25, unit.position)
                if nearby_workers.exists:
                    # OPTIMIZED: Process only first 3 workers
                    assigned_count = 0
                    for worker in nearby_workers:
                        try:
                            worker.gather(unit)
                            assigned_count += 1
                            if assigned_count >= 3:
                                break
                        except Exception:
                            continue
                    if self.iteration % 100 == 0 and assigned_count > 0:
                        print(
                            f"[AUTO ASSIGN] [{int(self.time)}s] Assigned {assigned_count} workers to new Extractor at {unit.position}"
                        )

        except (AttributeError, TypeError, ValueError, KeyError) as e:
            # Log specific errors for debugging
            if self.iteration % 200 == 0:
                print(f"[WARNING] on_building_construction_complete error: {type(e).__name__}: {e}")
        except Exception as e:
            # Catch-all for unexpected errors (should be rare)
            if self.iteration % 200 == 0:
                print(f"[ERROR] Unexpected error in on_building_construction_complete: {type(e).__name__}: {e}")
            # Re-raise in debug mode
            if os.environ.get("DEBUG_MODE") == "1":
                raise

    async def on_start(self):
        try:
            # Create data folder and save hello.txt for server recognition
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                data_dir = os.path.join(script_dir, "data")
                os.makedirs(data_dir, exist_ok=True)
                hello_file = os.path.join(data_dir, "hello.txt")
                with open(hello_file, "w", encoding="utf-8") as f:
                    f.write("Wicked Zerg AI Bot Data\n")
                    f.write(f"Personality: {self.personality}\n")
                    f.write(f"Instance ID: {self.instance_id}\n")
                print(f"[OK] Bot data folder created: {data_dir}")
            except Exception as e:
                print(f"[WARNING] Failed to create data folder: {e}")

            print("=" * 70)
            print(f"🎮 Wicked Zerg AI (Pro Edition) Starting!")
            print(f"👤 Persona: {self.personality.upper()}")
            if self.opponent_race:
                try:
                    opp_str = getattr(self.opponent_race, "name", str(self.opponent_race))
                except Exception:
                    opp_str = str(self.opponent_race)
                print(f"⚔️ Opponent Race: {opp_str}")
            print("=" * 70)

            # Check if townhalls exist (for Micro Ladder compatibility)
            # Optimized: Use .amount property instead of list conversion
            try:
                townhalls_count = (
                    self.townhalls.amount
                    if hasattr(self.townhalls, "amount")
                    else len(list(self.townhalls))
                )
                workers_count = (
                    self.workers.amount
                    if hasattr(self.workers, "amount")
                    else len(list(self.workers))
                )
                townhalls_exist = townhalls_count > 0
                workers_exist = workers_count > 0

                if townhalls_exist:
                    print(f"[OK] Townhalls detected: {townhalls_count}")
                else:
                    print("[WARNING] No townhalls detected")

                if workers_exist:
                    print(f"[OK] Workers detected: {workers_count}")
                else:
                    print("[WARNING] No workers detected")

                # Detect Micro Ladder mode: No townhalls AND no workers
                if not townhalls_exist and not workers_exist:
                    self.is_micro_ladder = True
                    print("=" * 70)
                    print("🎯 MICRO LADDER MODE DETECTED!")
                    print("   - Pure unit control mode activated")
                    print("   - All macro logic disabled")
                    print("=" * 70)
                else:
                    self.is_micro_ladder = False
            except Exception as e:
                print(f"[WARNING] Could not check townhalls/workers: {e}")
                # Assume Micro Ladder if check fails
                self.is_micro_ladder = False

            # Detect opponent race (at game start)
            if not self.opponent_race:
                # Auto-detect opponent race at game start (updated later by scouting)
                # Set to default for now (scout_manager will detect it)
                # Use Race enum for consistency
                self.opponent_race = Race.Terran  # Default value

            # 🗺️ Map Size Detection (for adaptive build order)
            try:
                if self.enemy_start_locations and len(self.enemy_start_locations) > 0:
                    enemy_start = self.enemy_start_locations[0]
                    self.map_rush_distance = self.start_location.distance_to(enemy_start)

                    # Map size classification based on rush distance
                    # NOTE: No rush mode - all maps use standard/economy build
                    if self.map_rush_distance < 60:
                        self.map_size = "SMALL"  # Fast rush maps (e.g., Torches)
                        print(
                            f"[MAP] Small map detected (rush distance: {self.map_rush_distance:.1f}) - Using standard build (no rush)"
                        )
                    elif self.map_rush_distance < 90:
                        self.map_size = "MEDIUM"  # Standard maps
                        print(
                            f"[MAP] Medium map detected (rush distance: {self.map_rush_distance:.1f}) - Using standard build"
                        )
                    else:
                        self.map_size = "LARGE"  # Large maps (e.g., Ley Lines)
                        print(
                            f"[MAP] Large map detected (rush distance: {self.map_rush_distance:.1f}) - Using economy build"
                        )
                else:
                    self.map_size = "MEDIUM"  # Default
            except Exception as e:
                print(f"[WARNING] Failed to detect map size: {e}")
                self.map_size = "MEDIUM"  # Default fallback

            self.spawning_pool_ready_flag = False
            print("[OK] Tech building flags initialized")

            # Setup race-specific strategy
            try:
                self._setup_race_specific_strategy()
            except Exception as e:
                print(f"[WARNING] Failed to setup race-specific strategy: {e}")

            # System initialization (with error handling - ensure bot never crashes)
            try:
                self.intel = IntelManager(self)
            except Exception as e:
                print(f"[WARNING] Failed to initialize IntelManager: {e}")
                traceback.print_exc()

                # Create dummy intel manager
                class DummyIntel:
                    def update(self):
                        pass

                    def should_attack(self):
                        return False

                    def should_defend(self):
                        return False

                    class Enemy:
                        pass

                    class Combat:
                        pass

                    class Economy:
                        pass

                    class Production:
                        pass

                    enemy = Enemy()
                    combat = Combat()
                    economy = Economy()
                    production = Production()
                    signals = {
                        "need_overseer": False,
                        "need_spine": False,
                        "enemy_attacking_our_bases": False,
                        "counter_attack_opportunity": False,
                        "neural_attack": False,
                        "neural_defense": False,
                        "neural_economy": False
                    }
                    cached_overlords = []
                    cached_townhalls = []
                    cached_workers = []
                    cached_military = []
                    cached_zerglings = []
                    cached_roaches = []
                    cached_hydralisks = []

                self.intel = DummyIntel()  # type: ignore[assignment]

            try:
                self.economy = EconomyManager(self)
            except Exception as e:
                print(f"[WARNING] Failed to initialize EconomyManager: {e}")

                class DummyEconomy:
                    async def update(self):
                        pass

                self.economy = DummyEconomy()  # type: ignore[assignment]

            try:
                self.production = ProductionManager(self)
            except Exception as e:
                print(f"[WARNING] Failed to initialize ProductionManager: {e}")
                print(f"[DEBUG] Full traceback:")
                traceback.print_exc()

                class DummyProduction:
                    async def update(self, phase):
                        pass

                self.production = DummyProduction()  # type: ignore[assignment]

            try:
                self.combat = CombatManager(self)
            except Exception as e:
                print(f"[WARNING] Failed to initialize CombatManager: {e}")

            # Initialize Rogue tactics manager
            try:
                self.rogue_tactics = RogueTacticsManager(self)
                print(f"[ROGUE TACTICS] Rogue tactics manager initialized")
            except Exception as e:
                print(f"[WARNING] Failed to initialize RogueTacticsManager: {e}")
                self.rogue_tactics = None

            # Initialize spell unit manager (optimized targeting)
            try:
                self.spell_unit_manager = SpellUnitManager(self)
                print(f"[SPELL UNITS] Spell unit manager initialized")
            except Exception as e:
                print(f"[WARNING] Failed to initialize SpellUnitManager: {e}")
                self.spell_unit_manager = None

                class DummyCombat:
                    def initialize(self):
                        pass

                    async def update(self, phase, context):
                        pass

                self.combat = DummyCombat()  # type: ignore[assignment]

            try:
                self.scout = ScoutingSystem(self)
            except Exception as e:
                print(f"[WARNING] Failed to initialize ScoutingSystem: {e}")

                class DummyScout:
                    def initialize(self):
                        pass

                    async def update(self, context):
                        return None

                self.scout = DummyScout()  # type: ignore[assignment]

            try:
                self.micro = MicroController(self)
            except Exception as e:
                print(f"[WARNING] Failed to initialize MicroController: {e}")

                class DummyMicro:
                    def execute_spread_attack(self, *args):
                        pass

                    def execute_stutter_step(self, *args):
                        pass

                    def execute_defensive_spread(self, *args):
                        pass

                    async def execute_baneling_vs_marines(self, *args):
                        pass

                    async def execute_zvz_zergling_micro(self, *args):
                        pass

                    async def execute_overlord_hunter(self, *args):
                        pass

                    async def execute_serral_bile_sniping(self, *args):
                        pass

                    async def execute_lurker_area_denial(self, *args):
                        pass

                self.micro = DummyMicro()  # type: ignore[assignment]

            # Heatmap merged into ScoutingSystem
            # No separate initialization needed - handled by ScoutManager

            try:
                self.queen_manager = QueenManager(self)
            except Exception as e:
                print(f"[WARNING] Failed to initialize QueenManager: {e}")

                class DummyQueen:
                    async def manage_queens(self):
                        pass

                    async def defend_with_queens(self):
                        pass

                self.queen_manager = DummyQueen()  # type: ignore[assignment]

            class DummyGasManager:
                async def maximize_gas_income(self):
                    pass

            try:
                if GasMaximizer is not None:
                    self.gas_maximizer = GasMaximizer(self)
                else:
                    self.gas_maximizer = DummyGasManager()
            except Exception as e:
                self.gas_maximizer = DummyGasManager()

            print("[OK] All managers initialized (some may be dummy)")

            class DummyDefenseManager:

                async def check_and_defend(self):
                    pass

                def is_panic_mode(self):
                    return False

            # Hot reloader initialization for EarlyDefenseManager
            # CRITICAL: Safe handling - early_defense_manager.py may not exist
            try:
                # First, check if file exists before trying HotLoader
                script_dir = os.path.dirname(os.path.abspath(__file__))
                early_defense_file = os.path.join(script_dir, "early_defense_manager.py")

                if HotLoader is not None and os.path.exists(early_defense_file):
                    try:
                        self.defense_loader = HotLoader("early_defense_manager")
                        if hasattr(self.defense_loader, "module") and self.defense_loader.module:
                            self.early_defense = self.defense_loader.module.EarlyDefenseManager(
                                self
                            )
                        else:
                            raise ImportError("HotLoader module not loaded")
                    except Exception as hot_e:
                        print(f"[WARNING] HotLoader failed for EarlyDefenseManager: {hot_e}")
                        # Fall back to direct import or dummy
                        if EarlyDefenseManager is not None:
                            self.early_defense = EarlyDefenseManager(self)
                        else:
                            self.early_defense = DummyDefenseManager()  # type: ignore[assignment]
                else:
                    # HotLoader not available or file doesn't exist, try direct import
                    if EarlyDefenseManager is not None:
                        self.early_defense = EarlyDefenseManager(self)
                    else:
                        self.early_defense = DummyDefenseManager()  # type: ignore[assignment]
                        if not os.path.exists(early_defense_file):
                            print(
                                f"[INFO] early_defense_manager.py not found - using dummy manager (file: {early_defense_file})"
                            )
            except Exception as e:
                print(f"[WARNING] Failed to load EarlyDefenseManager: {e}")
                # Create dummy defense manager as fallback
                self.early_defense = DummyDefenseManager()  # type: ignore[assignment]

            try:
                if self.opponent_race and self.micro and hasattr(self.micro, "set_opponent_race"):
                    self.micro.set_opponent_race(self.opponent_race)
            except Exception as e:
                print(f"[WARNING] Failed to set opponent race in micro: {e}")

            # Initialize managers (with townhall check)
            try:
                if self.combat:
                    self.combat.initialize()
            except Exception as e:
                print(f"[WARNING] Failed to initialize combat manager: {e}")

            try:
                if self.scout:
                    self.scout.initialize()
            except Exception as e:
                print(f"[WARNING] Failed to initialize scout manager: {e}")

            # Heatmap is now part of ScoutingSystem, initialized with scout
            # No separate initialization needed

            # Send greeting message using PersonalityManager
            try:
                greeting = self.personality_manager.get_greeting_message()
                await self.personality_manager.send_chat(greeting)
            except Exception as e:
                print(f"[WARNING] Failed to send greeting: {e}")
                pass  # Silently fail if chat is not available

            # Set opponent name for tracking (try to get from game state or use default)
            try:
                # Try to get opponent name from game state
                # In ladder, opponent name might be available through game_info
                opponent_name = "Unknown"
                enemy_units_attr = getattr(self, "enemy_units", None)  # type: ignore[attr-defined]
                if enemy_units_attr:
                    # Try to infer from game state
                    opponent_name = "LadderOpponent"

                # Set opponent in tracker
                if hasattr(self, "strategy_analyzer") and self.strategy_analyzer:
                    self.strategy_analyzer.set_opponent(opponent_name)
                    self.write_log(f"Opponent set: {opponent_name}", "INFO")

                    # Check if we should use aggressive build (revenge mode)
                    if self.strategy_analyzer.should_use_aggressive_build(opponent_name):
                        self.write_log(
                            f"REVENGE MODE: Using aggressive build vs {opponent_name}",
                            "WARNING",
                        )
            except Exception as e:
                self.write_log(f"Failed to set opponent: {e}", "WARNING")

            # Log bot initialization
            self.write_log("Monsterbot online! Version 2026.01.06", "INFO")
            self.write_log(f"Personality: {self.personality.upper()}", "INFO")
            if self.opponent_race:
                try:
                    opp_str = getattr(self.opponent_race, "name", str(self.opponent_race))
                except Exception:
                    opp_str = str(self.opponent_race)
                self.write_log(f"Opponent race: {opp_str}", "INFO")

            print("[OK] Bot initialization complete!")

        except Exception as e:
            # Critical error during initialization - log with full traceback
            error_msg = f"Critical error in on_start: {str(e)}\n"
            try:
                error_msg += f"Traceback:\n{tb.format_exc()}\n"
            except Exception:
                pass
            print(f"[ERROR] {error_msg}")

            # Save error log with full traceback
            try:
                # CRITICAL: Error logs go to logs/ directory (project root)
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(script_dir)  # local_training -> project root
                logs_dir = os.path.join(project_root, "logs")
                os.makedirs(logs_dir, exist_ok=True)
                error_log_path = os.path.join(logs_dir, "error_log.txt")
                with open(error_log_path, "a", encoding="utf-8") as f:
                    f.write(f"{'=' * 70}\n")
                    f.write(f"on_start error at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{'=' * 70}\n")
                    f.write(error_msg)
                    f.write("\n")

                # Also log to main log file with traceback
                try:
                    self.write_log_with_traceback(
                        f"Critical error in on_start: {str(e)}", e, "ERROR"
                    )
                except Exception:
                    pass  # Fail silently if logging fails("Critical error in on_start", e, "ERROR")
            except Exception as log_error:
                print(f"[ERROR] Failed to write error log: {log_error}")

            # Don't re-raise - let bot continue with minimal functionality
            # This prevents InitializationError from crashing the bot

    def _setup_race_specific_strategy(self):
        """
        상대 종족에 따른 맞춤 전략 설정

        저그 랭킹 1~5위 선수들은 상대 종족에 따라 완전히 다른 빌드를 선택합니다.
        """
        if not self.opponent_race:
            return

        # Get parameters from PersonalityManager
        params = self.personality_manager.params

        if self.opponent_race and str(self.opponent_race).lower() == "protoss":
            # vs Protoss: Fast multi-base and Lurker preparation rather than Zergling all-in
            params["drone_limit"] = 80
            params["macro_focus"] = 0.9  # Emphasize multi-tasking
            params["aggression"] = 0.5  # Reduce early aggression
            print(f"[STRATEGY] vs Protoss: Fast multi + Lurker strategy ({self.personality.upper()})")

        elif self.opponent_race and str(self.opponent_race).lower() == "terran":
            # vs Terran: Prioritize Baneling speed upgrade and emphasize spread control
            params["drone_limit"] = 75
            params["macro_focus"] = 0.7
            params["aggression"] = 0.7  # Mid-game aggression
            print(f"[STRATEGY] vs Terran: Baneling speed + spread control ({self.personality.upper()})")

        elif self.opponent_race and str(self.opponent_race).lower() == "zerg":
            # vs Zerg: Early Zergling/Baneling fight is crucial, so lower drone_limit
            params["drone_limit"] = 60
            params["macro_focus"] = 0.5
            params["aggression"] = 0.9  # Maximum early aggression
            print(f"[STRATEGY] vs Zerg: Early Zergling/Baneling fight ({self.personality.upper()})")

        # Save back to PersonalityManager (explicit, though auto-updated by reference)
        self.personality_manager.params = params

    async def on_step(self, iteration: int):
        try:
            if hasattr(self, "game_ended") and self.game_ended:
                return  # Game ended, exit immediately - don't process any more steps

            # Update iteration attribute (avoid redeclaration error)
            self.iteration = iteration

            # 🎯 Enemy Unit Tracking Update (Every Frame)
            # Keep known_enemy_units in sync with self.enemy_units for compatibility
            self.known_enemy_units = self.enemy_units

            if self.opponent_race is None and hasattr(self, "enemy_race"):
                self.opponent_race = self.enemy_race

            # � Dashboard Update (Every 10 frames)
            # Send game state to web dashboard for real-time monitoring
            if iteration % 10 == 0 and DASHBOARD_AVAILABLE:
                try:
                    bot_connector.update_state(self)
                except Exception as e:
                    if iteration % 100 == 0:  # Log error every 100 frames to avoid spam
                        logger.debug(f"Dashboard update error: {e}")

            # �🚀 Real-time Status Display (Terminal Dashboard)
            if iteration % 22 == 0:
                try:
                    minutes = int(self.time) // 60
                    seconds = int(self.time) % 60
                    time_formatted = f"{minutes:02d}:{seconds:02d}"
                    attacking = False
                    try:
                        combat_unit_types = getattr(
                            self, "combat_unit_types", {UnitTypeId.ZERGLING}
                        )
                        # Handle both set and dict types
                        if isinstance(combat_unit_types, dict):
                            combat_unit_types = (
                                set(combat_unit_types.keys())
                                if combat_unit_types
                                else {UnitTypeId.ZERGLING}
                            )
                        elif not isinstance(combat_unit_types, set):
                            combat_unit_types = {UnitTypeId.ZERGLING}  # Default fallback
                        combat_units = self.units.filter(lambda u: u.type_id in combat_unit_types)
                        if combat_units.exists:
                            # Check if any combat units have attack target
                            for unit in list(combat_units)[:5]:  # Check first 5 units only
                                if hasattr(unit, "orders") and unit.orders:
                                    for order in unit.orders:
                                        if hasattr(order, "ability") and order.ability:
                                            ability_name = str(order.ability).lower()
                                            if "attack" in ability_name or "move" in ability_name:
                                                # Check if moving towards enemy
                                                if hasattr(order, "target") and order.target:
                                                    attacking = True
                                                    break
                                    if attacking:
                                        break
                    except Exception:
                        pass  # Silent fail

                    game_count = getattr(self, "game_count", 0)
                    last_result = getattr(self, "last_result", "N/A")
                    dashboard = (
                        f"\r[GAME #{game_count:03d}] "
                        f"TIME: {time_formatted} | "
                        f"MIN: {int(self.minerals):4d} | "
                        f"SUPPLY: {self.supply_used:2d}/{self.supply_cap:2d} | "
                        f"UNITS: {len(self.units):3d} | "
                        f"LAST: {last_result}"
                    )
                    sys.stdout.write(dashboard)
                    sys.stdout.flush()

                    try:
                        instance_id = getattr(self, "instance_id", 0)
                        # IMPROVED: Reduce write frequency for 30+ instances to prevent I/O bottleneck
                        # Write every 16 frames (~0.7 seconds) instead of every frame
                        write_interval = 16 if instance_id > 0 else 1

                        if instance_id > 0 and self.iteration % write_interval == 0:
                            # IMPROVED: Use project root stats/ directory with instance subdirectory
                            project_root = PathLib(__file__).parent.parent.parent
                            status_dir = project_root / "stats" / f"instance_{instance_id}"
                            status_dir.mkdir(parents=True, exist_ok=True)
                            status_file = status_dir / "status.json"

                            # Read existing status or create new
                            status_data = {
                                "instance_id": instance_id,
                                "mode": "VISUAL"
                                if getattr(self, "_show_window", False)
                                else "HEADLESS",
                                "game_count": game_count,
                                "win_count": getattr(self, "_win_count", 0),
                                "loss_count": getattr(self, "_loss_count", 0),
                                "last_result": last_result,
                                "current_game_time": time_formatted,
                                "current_minerals": int(self.minerals),
                                "current_supply": f"{self.supply_used}/{self.supply_cap}",
                                "current_units": len(self.units),
                                "status": "GAME_RUNNING",
                                "timestamp": time.time(),
                            }

                            # CRITICAL FIX: Use asyncio executor for non-blocking file I/O
                            # This prevents game freezing from synchronous file operations
                            temp_file = status_file.with_suffix('.tmp')
                            try:
                                # Schedule file write in thread pool to avoid blocking game loop
                                loop = asyncio.get_event_loop()
                                await loop.run_in_executor(
                                    None,
                                    self._write_status_file_sync,
                                    temp_file,
                                    status_file,
                                    status_data
                                )
                            except Exception as file_error:
                                # If temp file exists, try to remove it
                                try:
                                    if temp_file.exists():
                                        temp_file.unlink()
                                except (OSError, PermissionError):
                                    pass  # Ignore cleanup errors
                    except (IOError, OSError, PermissionError, json.JSONDecodeError) as status_error:
                        # Log specific error types for debugging, but don't crash
                        # IMPROVED: Reduce write frequency for 30+ instances (16 frames = ~0.7 seconds)
                        log_interval = 16 if hasattr(self, "instance_id") and getattr(self, "instance_id", 0) > 0 else 500
                        if self.iteration % log_interval == 0:
                            print(f"[WARNING] Status file update failed: {type(status_error).__name__}")

                    # Also dump structures snapshot for mobile/monitoring endpoints
                    try:
                        self._dump_structures_state()
                    except (AttributeError, TypeError, IOError) as dump_error:
                        # Log specific errors for debugging
                        if self.iteration % 500 == 0:
                            print(f"[WARNING] Structure dump failed: {type(dump_error).__name__}")
                except (AttributeError, TypeError, KeyError) as step_error:
                    # Log critical errors that might indicate logic bugs
                    if self.iteration % 100 == 0:
                        print(f"[ERROR] on_step error: {type(step_error).__name__}: {step_error}")
                    # Re-raise critical errors in development mode
                    if os.environ.get("DEBUG_MODE") == "1":
                        raise

            # 📝 Action Logging (Specific actions only - prevent screen spam)
            # Log only when SPAWNINGPOOL is completed (once per game)
            if not hasattr(self, "already_logged_pool"):
                self.already_logged_pool = False

            if self.structures(UnitTypeId.SPAWNINGPOOL).ready and not self.already_logged_pool:
                try:
                    if logger:
                        logger.info(
                            f"✅ [Action] Spawning Pool completed! Ready to produce Zerglings"
                        )
                    else:
                        print(f"✅ [Action] Spawning Pool completed! Ready to produce Zerglings")
                    self.already_logged_pool = True
                except Exception:
                    pass  # Silent fail

            # CPU/GPU workload interval settings (defined as global constants for use everywhere)
            # PERFORMANCE: Increased intervals for 75% CPU load reduction
            CPU_WORKLOAD_INTERVAL = 96  # CPU workload interval (48 → 96: 50% additional reduction)
            GPU_WORKLOAD_INTERVAL = (
                96  # GPU workload interval (same as CPU, 48 → 96: 50% additional reduction)
            )

            # ⚠️ CRITICAL: Supply Block Prevention moved to ProductionManager._produce_overlord()
            # NOTE: Overlord production is now handled by ProductionManager with predictive logic
            # Removed redundant supply_left < 3 check to avoid duplication
            # The production manager monitors supply and produces overlords automatically

            # CRITICAL FIX: Removed % 8 check that was blocking production manager every 88 frames
            # Each manager now runs at its own interval (combat: 4, production: 22, economy: 22, etc.)
            # This prevents the 8 * 22 = 176 frame problem that was killing unit production

            try:
                self.last_drone_count = self.units(UnitTypeId.DRONE).amount
            except Exception:
                pass

            # 🚀 OPTIMIZATION: Intel Manager Update (Blackboard Pattern)
            # Update intelligence cache FIRST - all managers will use cached data
            # Intel Manager update is now handled in the scheduler section below
            # This prevents redundant unit filtering across multiple managers

            # 0.3️⃣ Autonomous personality disabled (redundant with PersonalityManager)
            # NOTE: Chat now handled by PersonalityManager in section 10

            # PERFORMANCE: Increased from 44 to 88 frames for additional 50% CPU load reduction
            if iteration % 88 == 0:
                if await self._check_for_surrender():
                    return  # Game ended, exit on_step

            # PERFORMANCE: CombatManager handles all combat logic using IntelManager cache
            # Combat Manager: Every 4 frames for responsiveness (0.15 seconds at 22.4 FPS)
            if iteration % 4 == 0:
                if self.combat is not None:
                    try:
                        # CRITICAL FIX: Add timeout to prevent game freezing from blocking operations
                        # CombatManager.update() uses intel.cached_military internally
                        await asyncio.wait_for(
                            self.combat.update(self.game_phase, {}),
                            timeout=0.1  # 100ms timeout to prevent blocking
                        )
                    except asyncio.TimeoutError:
                        if iteration % 200 == 0:
                            print(f"[WARNING] CombatManager.update() timed out at iteration {iteration}")
                    except Exception as e:
                        if iteration - self.last_error_log_frame >= 50:
                            if iteration % 200 == 0:
                                print(f"[WARNING] CombatManager.update() error: {e}")
                            self.last_error_log_frame = iteration

            # CRITICAL: Workers should NOT fight - they should gather resources.
            # Only retreat workers to safety when enemies are near.
            # Army production is ALWAYS priority over worker defense.
            # PERFORMANCE: Reduced frequency for CPU load reduction
            if iteration % 15 == 0 and self.townhalls.exists:
                # Only retreat workers if we have NO army at all
                my_army = self.units.filter(lambda u: u.type_id in self.combat_unit_types)
                if not my_army.exists or my_army.amount == 0:
                    # No army - retreat workers to safety (but don't attack)
                    await self._worker_defense_emergency()
                else:
                    # We have army - workers should gather resources, not retreat
                    pass

            # Intelligent early scouting: Scout within 20 seconds (about 450 iterations) based on game state
            # PERFORMANCE: Reduced frequency for CPU load reduction
            if iteration % 40 == 0:
                current_iteration = getattr(self, "iteration", iteration)
                if self.time < 20.0 and current_iteration < 450:
                    await self._fast_scouting_20_seconds()

            # 1.6️⃣ Intelligent worker safety management (Context-aware Worker Safe Zone)
            # PERFORMANCE: Reduced frequency for CPU load reduction (30 frames)
            if iteration % 30 == 0 and self.townhalls.exists and self.workers.exists:
                await self._enforce_worker_safe_zone()

            if self.iteration % 112 == 0 and self.townhalls.exists:
                await self._send_game_progress_to_chat()

            # PERFORMANCE: Increased from 224 to 448 frames for CPU load reduction
            if self.iteration % 448 == 0 and self.townhalls.exists:
                await self._broadcast_internal_thoughts()

            # PERFORMANCE: Increased from 224 to 448 frames for CPU load reduction
            if self.iteration % 448 == 0 and self.townhalls.exists:
                await self._calculate_and_display_win_probability()

            # 1.9️⃣ Performance Metrics Recording (for dashboard visualization)
            # Record frame-by-frame metrics for data-driven evolution
            # PERFORMANCE: Only record every 22 frames (heavy logic interval)
            if iteration % 22 == 0:
                if hasattr(self, "analysis_hub") and self.analysis_hub:
                    try:
                        if self.analysis_hub:
                            self.analysis_hub.record_performance_metrics()
                    except Exception:
                        pass  # Silently fail to avoid interrupting game flow

            if self.townhalls.exists:
                # 🔥 PRIORITY ZERO: Emergency Worker Recovery (Break the 30 Mineral Curse)
                # Execute BEFORE any other logic to prevent ECONOMY_COLLAPSE
                try:
                    # Optimized: Cache workers.amount check
                    if not hasattr(self, "_workers_has_amount"):
                        self._workers_has_amount = hasattr(self.workers, "amount")
                    worker_count = (
                        self.workers.amount if self._workers_has_amount else len(list(self.workers))
                    )

                    # [Intelligent decision 1] When drones < 5, prioritize minerals over gas (economic recovery)
                    # Enhanced: Changed from <= 3 to < 5 for earlier intervention
                    if worker_count < 5:
                        # PERFORMANCE: Use .of_type() instead of filter() for better performance
                        ready_extractors = self.units(UnitTypeId.EXTRACTOR).ready

                        if ready_extractors.exists:
                            # PERFORMANCE: Cache townhall position to avoid repeated queries
                            first_townhall = self.townhalls.first if self.townhalls.exists else None
                            if first_townhall:
                                minerals_near_base = self.mineral_field.closer_than(
                                    10, first_townhall.position
                                )

                                # OPTIMIZED: Process only first 3 extractors (limit heavy iteration)
                                for extractor in list(ready_extractors)[:3]:
                                    # PERFORMANCE: Use filter() instead of list comprehension
                                    gas_workers = self.workers.filter(
                                        lambda w: hasattr(w, "order_target")
                                        and w.order_target == extractor.tag
                                    )

                                    # Move ALL gas workers to minerals (no gas income, only minerals)
                                    # OPTIMIZED: Process only first 5 gas workers per extractor
                                    if minerals_near_base.exists:
                                        for worker in list(gas_workers)[:5]:
                                            try:
                                                closest_mineral = minerals_near_base.closest_to(
                                                    worker.position
                                                )
                                                if closest_mineral:
                                                    worker.gather(closest_mineral)
                                            except Exception:
                                                pass

                    # [Intelligent decision 2] In Priority Zero situation, freeze spending until 50 minerals accumulated
                    # Enhanced: Changed from < 10 to < 12 for broader protection
                    if worker_count < 12 and self.minerals < 50:
                        # This frame: Do nothing, just wait for minerals to accumulate
                        # Gas workers should be moved to minerals by logic above
                        # Skip rest of logic this frame to prevent other spending
                        return
                except Exception:
                    pass  # Silent fail to avoid crashing

                # [Gas Worker Rebalancing] Periodically ensure extractors have 3 workers each
                # Run every 22 frames (~1 second) when economy is stable
                if iteration % 22 == 0:
                    # Use cached worker_count if available
                    if not hasattr(self, "_workers_has_amount"):
                        self._workers_has_amount = hasattr(self.workers, "amount")
                    current_worker_count = (
                        self.workers.amount if self._workers_has_amount else len(list(self.workers))
                    )

                    if current_worker_count >= 16:
                        try:
                            ready_extractors = self.structures(UnitTypeId.EXTRACTOR).ready
                            if ready_extractors.exists:
                                idle_workers = self.workers.idle
                                for extractor in ready_extractors:
                                    current_workers = extractor.assigned_harvesters
                                    needed_workers = 3 - current_workers
                                    if needed_workers > 0 and idle_workers.exists:
                                        # Assign idle workers to under-saturated extractors
                                        for _ in range(min(needed_workers, len(idle_workers))):
                                            if idle_workers.exists:
                                                worker = idle_workers.closest_to(extractor.position)
                                                worker.gather(extractor)
                                                idle_workers = self.workers.idle  # Refresh list
                        except Exception:
                            pass  # Silent fail to avoid disrupting game flow

                # [Intelligent decision 3] Prioritize worker production - prevent economic collapse
                # CRITICAL: Stop worker production at 60 workers to free larvae for army
                # If we have larvae and can afford a drone, prioritize worker production
                try:
                    # Use cached worker_count
                    if not hasattr(self, "_workers_has_amount"):
                        self._workers_has_amount = hasattr(self.workers, "amount")
                    worker_count = (
                        self.workers.amount if self._workers_has_amount else len(list(self.workers))
                    )

                    if worker_count < 60 and worker_count < 16:
                        # OPTIMIZED: Use self.larva directly, process only first larva
                        larvae = self.units(UnitTypeId.LARVA)
                        if larvae.exists and self.can_afford(UnitTypeId.DRONE):
                            # Check if we're not supply blocked
                            if self.supply_left >= 1:
                                try:
                                    # OPTIMIZED: Process only first larva (no need to iterate all)
                                    for larva in larvae[:1]:
                                        if larva.is_ready:
                                            await larva.train(UnitTypeId.DRONE)
                                            # Skip other production this frame to ensure drone is trained
                                            return
                                except Exception:
                                    pass
                    elif worker_count >= 60:
                        # CRITICAL: Stop worker production at 60 - all larvae should go to army
                        if self.iteration % 200 == 0:
                            print(
                                f"[WORKER LIMIT] [{int(self.time)}s] Worker count reached 60 - Stopping drone production to prioritize army"
                            )
                except Exception:
                    # Silent fail - emergency logic shouldn't crash the bot
                    pass

                # Standard Melee mode - execute full macro logic
                await self._execute_melee_ladder_logic(iteration)
            else:
                # Optimized: Use cached enemy_units or check directly
                enemy_units_for_search = (
                    getattr(self, "_cached_enemy_units", None)
                    or getattr(self, "known_enemy_units", None)
                    or getattr(self, "enemy_units", None)
                )  # type: ignore[attr-defined]
                if not enemy_units_for_search or not enemy_units_for_search.exists:
                    # No enemies detected: Search map center
                    # PERFORMANCE: Increased from 20 to 40 frames for CPU load reduction
                    if iteration % 40 == 0:  # Every ~2 seconds
                        try:
                            # CRITICAL: Use whitelist approach - only Zergling+ combat units
                            combat_units = self.units.filter(
                                lambda u: u.type_id in self.combat_unit_types and u.is_ready
                            )
                            if combat_units.exists:
                                map_center = self.game_info.map_center
                                # OPTIMIZED: Process only first 10 units (no need to iterate all)
                                for unit in list(combat_units)[:10]:
                                    if unit.is_ready:
                                        unit.move(map_center)
                        except Exception:
                            pass
                # If enemies are found, common combat logic above handles it

            # Real-time Status Dashboard - Chat Version (ENABLED for critical situations)
            # Show bot's current state and mood when resources are excessive or army is low
            if iteration % 500 == 0 and self.townhalls.exists:  # Every ~22 seconds
                try:
                    # Calculate army count (use whitelist - only Zergling+ combat units)
                    army_units = self.units.filter(lambda u: u.type_id in self.combat_unit_types)
                    army_count = (
                        army_units.amount
                        if hasattr(army_units, "amount")
                        else len(list(army_units))
                    )

                    # Determine mood based on game state
                    mood = "🛡️ 신중함"
                    thought = "안전하게 멀티를 늘리는 중입니다."

                    # Extreme emergency: minerals > 3000 and army < 5
                    if self.minerals > 3000 and army_count < 5:
                        mood = "🔥 긴급"
                        thought = f"미네랄 {int(self.minerals)}원 쌓임! 병력 생산 최우선! (현재 병력: {army_count}기)"
                    # Emergency: minerals > 2000 and army < 10
                    elif self.minerals > 2000 and army_count < 10:
                        mood = "🔥 공격적"
                        thought = f"자원이 넘쳐납니다({int(self.minerals)}M)! 병력을 모아 한 번에 끝내겠습니다. (병력: {army_count}기)"
                    # Normal: good resource management
                    elif self.minerals < 500 and army_count > 10:
                        mood = "💰 효율적"
                        thought = f"자원을 잘 활용하고 있습니다. (미네랄: {int(self.minerals)}M, 병력: {army_count}기)"

                    # Send mood and thought to chat
                    await self.chat_send(
                        f"💬 [현재 생각] {mood}: {thought} (보유 미네랄: {int(self.minerals)}M, 병력: {army_count}기)"
                    )
                except Exception:
                    # Silent fail - chat shouldn't crash the bot
                    pass

            # Legacy chat monitoring (disabled)
            if False and iteration % 112 == 0 and self.townhalls.exists:
                try:
                    # Calculate tech level
                    tech_level = "Tier 1: Hatchery"
                    if self.units(UnitTypeId.LAIR).ready.exists:
                        tech_level = "Tier 2: Lair"
                    if self.units(UnitTypeId.HIVE).ready.exists:
                        tech_level = "Tier 3: Hive"

                    # Calculate army count (use whitelist - only Zergling+ combat units)
                    army_units = self.units.filter(lambda u: u.type_id in self.combat_unit_types)
                    army_count = (
                        army_units.amount
                        if hasattr(army_units, "amount")
                        else len(list(army_units))
                    )

                    # Calculate supply left
                    supply_left = self.supply_cap - self.supply_used if self.supply_cap > 0 else 0

                    # Check defense status
                    defense_status = "Emergency Defense Active"
                    if hasattr(self, "early_defense") and self.early_defense is not None:
                        if hasattr(self.early_defense, "is_panic_mode"):
                            if not self.early_defense.is_panic_mode():
                                defense_status = "Standard Operation"
                        else:
                            defense_status = "Standard Operation"
                    else:
                        defense_status = "Standard Operation"

                    # Build dashboard message for chat
                    dashboard_msg = (
                        f"📊 [Status] M:{self.minerals} G:{self.vespene} | "
                        f"Supply:{self.supply_used}/{self.supply_cap}({supply_left}) | "
                        f"Workers:{self.workers.amount} Army:{army_count} | "
                        f"Tech:{tech_level} | {defense_status}"
                    )

                    # Send to chat
                    await self.chat_send(dashboard_msg)
                except Exception:
                    # Silent fail - chat shouldn't crash the bot
                    pass

        except Exception as e:
            # Global error handler - Enhanced debug output with full context
            error_type = type(e).__name__
            error_msg = str(e)

            # Get full traceback for debugging

            tb_str = traceback.format_exc()

            # Enhanced debug output to console
            instance_id = getattr(self, "instance_id", 0)
            instance_tag = f"[ID:{instance_id}]"

            print(f"\n{'=' * 80}")
            print(f"{instance_tag} 🔴 CRITICAL ERROR DETECTED")
            print(f"{'=' * 80}")
            print(f"⏰ Time: {self.time:.2f}s | Iteration: {iteration}")
            print(f"📋 Error Type: {error_type}")
            print(f"💬 Error Message: {error_msg}")
            print(f"📍 Traceback:")
            print(tb_str)

            # Game state context
            try:
                print(f"\n📊 Game State Context:")
                print(f"   Minerals: {self.minerals} | Vespene: {self.vespene}")
                print(f"   Supply: {self.supply_used}/{self.supply_cap} (Left: {self.supply_left})")
                print(f"   Workers: {self.workers.amount} | Army: {self.supply_army}")
                print(
                    f"   Hatcheries: {self.townhalls.amount} | Larvae: {self.units(UnitTypeId.LARVA).amount}"
                )

                # Manager status
                managers_status = []
                if self.economy:
                    managers_status.append("Economy✅")
                else:
                    managers_status.append("Economy❌")
                if self.production:
                    managers_status.append("Production✅")
                else:
                    managers_status.append("Production❌")
                if self.combat:
                    managers_status.append("Combat✅")
                else:
                    managers_status.append("Combat❌")
                if self.scout:
                    managers_status.append("Scout✅")
                else:
                    managers_status.append("Scout❌")
                print(f"   Managers: {', '.join(managers_status)}")
            except Exception as context_error:
                print(f"   [WARNING] Failed to get game state context: {context_error}")

            print(f"{'=' * 80}\n")

            # Log error to file (both error_log.txt and main log file) with full traceback
            try:
                # CRITICAL: Error logs go to logs/ directory (project root)
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(script_dir)  # local_training -> project root
                logs_dir = os.path.join(project_root, "logs")
                os.makedirs(logs_dir, exist_ok=True)
                error_log_file = os.path.join(logs_dir, "error_log.txt")
                with open(error_log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{'=' * 70}\n")
                    f.write(f"Error at iteration {iteration}:\n")
                    f.write(f"Type: {error_type}\n")
                    f.write(f"Message: {error_msg}\n")
                    f.write(f"Traceback:\n{traceback.format_exc()}\n")
                    f.write(f"{'=' * 70}\n")

                # Also write to main log file with full traceback
                self.write_log_with_traceback(
                    f"on_step error at iteration {iteration}: {error_type}", e, "ERROR"
                )
            except Exception:
                pass

            # IMPROVED: Gemini Self-Healing - Analyze error and suggest patch
            if self.self_healing and self.self_healing.is_available():
                try:
                    # Collect error context for Gemini analysis
                    error_context = {
                        "iteration": iteration,
                        "game_time": self.time,
                        "instance_id": getattr(self, "instance_id", 0),
                        "minerals": self.minerals,
                        "vespene": self.vespene,
                        "supply_used": self.supply_used,
                        "supply_cap": self.supply_cap,
                    }

                    # Analyze error with Gemini (async to avoid blocking game loop)
                    # Use asyncio.create_task to run in background
                    async def analyze_error_async():
                        try:
                            patch = self.self_healing.analyze_error(e, context=error_context)
                            if patch:
                                print(f"\n[SELF-HEALING] ✅ Patch suggestion received:")
                                print(f"   Description: {patch.description}")
                                print(f"   File: {patch.file_path}")
                                print(f"   Confidence: {patch.confidence:.2f}")
                                print(f"   Reasoning: {patch.reasoning[:200]}...")
                                print(f"   Patch saved to: {self.self_healing.log_dir}")

                                # If auto-patch is enabled and confidence is high, apply patch
                                if self.self_healing.enable_auto_patch and patch.confidence >= 0.8:
                                    if self.self_healing.apply_patch(patch):
                                        print(f"[SELF-HEALING] 🔧 Patch applied automatically (confidence: {patch.confidence:.2f})")
                                    else:
                                        print(f"[SELF-HEALING] ⚠️ Auto-patch failed (check logs)")
                        except Exception as analysis_error:
                            # Don't crash if Gemini analysis fails
                            if iteration % 500 == 0:  # Log only occasionally
                                print(f"[SELF-HEALING] ⚠️ Error analysis failed: {analysis_error}")

                    # Schedule error analysis in background (non-blocking)
                    asyncio.create_task(analyze_error_async())
                except Exception as healing_error:
                    # Don't crash if self-healing setup fails
                    if iteration % 500 == 0:
                        print(f"[SELF-HEALING] ⚠️ Self-healing error: {healing_error}")

            # Console output (throttled)
            if iteration - self.last_error_log_frame >= 50:
                print(
                    f"[CRITICAL] on_step error (iteration {iteration}): {error_type}: {error_msg}"
                )
                self.last_error_log_frame = iteration

    async def _execute_melee_ladder_logic(self, iteration: int):
        """
        Standard Melee Ladder 전용 로직
        본진이 있을 때만 실행되는 매크로 로직 (자원 채취, 건물 건설, 유닛 생산)
        """
        try:
            if not self.townhalls.exists:
                return

            # Performance optimization: Cache units at start of step
            # Cache self.units and enemy_units to avoid repeated queries
            # This reduces CPU load significantly in multiprocessing environment
            # Store in instance variables so they can be accessed in _execute_combat
            self._cached_units = self.units
            self._cached_enemy_units = getattr(self, "enemy_units", None)

            # PERFORMANCE: Increased from 60 to 120 frames for additional CPU load reduction
            if (
                iteration % 120 == 0 and self.time < 180
            ):
                try:
                    if hasattr(self, "main_base_ramp") and self.main_base_ramp:
                        ramp_top = self.main_base_ramp.top_center
                        zerglings = self.units(UnitTypeId.ZERGLING).ready

                        if zerglings.amount >= 2:
                            defense_lings = zerglings[: min(4, zerglings.amount)]
                            for ling in defense_lings:
                                if ling.distance_to(ramp_top) > 5:
                                    ling.move(ramp_top)
                except Exception as e:
                    pass

            # Hot reload check (every ~4 seconds, 88 frames = 4 seconds)
            # PERFORMANCE: Increased from 44 to 88 frames for additional CPU load reduction
            # CRITICAL: Safe handling - only reload if loader exists and file exists
            if iteration % 88 == 0 and hasattr(self, "defense_loader") and self.defense_loader:
                # Skip reload if a previous failure is still cooling down
                if getattr(self, "time", 0.0) < getattr(self, "hot_reload_fail_until", 0.0):
                    pass
                else:
                    try:
                        script_dir = os.path.dirname(os.path.abspath(__file__))
                        early_defense_file = os.path.join(script_dir, "early_defense_manager.py")

                        # Only reload if file exists
                        if os.path.exists(early_defense_file):
                            if self.defense_loader.check_and_reload():
                                # Code changed - recreate instance
                                if (
                                    hasattr(self.defense_loader, "module")
                                    and self.defense_loader.module
                                ):
                                    self.early_defense = self.defense_loader.module.EarlyDefenseManager(
                                        self
                                    )
                                    print("EarlyDefenseManager instance recreated successfully")
                                else:
                                    raise AttributeError("HotLoader module not available")
                        # If file does not exist, keep using dummy manager (no reload attempt)
                    except Exception as e:
                        # Cooldown to avoid spam when code is being edited mid-game
                        self.hot_reload_fail_until = getattr(self, "time", 0.0) + 15.0
                        if iteration % 200 == 0:  # Throttle error messages
                            print(f"[WARNING] EarlyDefenseManager hot reload failed: {e}")
                        # Keep previous instance (dummy manager if file doesn't exist)

            # CRITICAL: Use hasattr to prevent AttributeError if early_defense is not initialized
            if not hasattr(self, "early_defense") or self.early_defense is None:
                # Common Dummy Defense Manager class (reusable)
                class DummyDefenseManager:

                    async def check_and_defend(self):
                        pass

                    def is_panic_mode(self):
                        return False

                if hasattr(self, "defense_loader"):
                    self.early_defense = self.defense_loader.module.EarlyDefenseManager(self)
                elif EarlyDefenseManager is not None:
                    self.early_defense = EarlyDefenseManager(self)
                else:
                    # EarlyDefenseManager not available, use dummy
                    self.early_defense = DummyDefenseManager()  # type: ignore[assignment]

            # Check early_defense and initialize managers (every 8 frames to reduce CPU load)
            if iteration % 8 == 0:
                # Early defense check
                if self.early_defense is not None:
                    try:
                        await self.early_defense.check_and_defend()
                    except Exception as e:
                        if iteration - self.last_error_log_frame >= 50:
                            print(f"[WARNING] EarlyDefenseManager.check_and_defend() 오류: {e}")
                            self.last_error_log_frame = iteration

                if self.intel is None:
                    self.intel = IntelManager(self)
                if self.economy is None:
                    self.economy = EconomyManager(self)
                if self.production is None:
                    self.production = ProductionManager(self)
                if self.combat is None:
                    self.combat = CombatManager(self)
                    self.combat.initialize()
                if self.scout is None:
                    self.scout = ScoutingSystem(self)
                    self.scout.initialize()
                if self.micro is None:
                    self.micro = MicroController(self)
                # Heatmap is now part of ScoutingSystem, no separate initialization needed

            # 🚀 OPTIMIZED ON_STEP STRUCTURE: CPU Load Reduction
            # This structure reduces CPU usage dramatically, eliminating editor/game lag
            # Manager execution schedule (optimized for CPU load reduction):
            # 1. Intel Manager: Every frame - Data consistency (all managers share this)
            # 2. Micro Controller: Every frame - Combat responsiveness
            # 3. Combat Manager: Every 4 frames - Tactical decisions
            # 4. Production & Economy: Every 22 frames - Building & worker optimization
            # 5. Heavy Analysis: Every 100 frames - Battle analysis & visualization

            # 🎯 Tech Building Status Update: Every frame (critical for production decisions)
            # Update Spawning Pool status with enhanced detection logic
            spawning_pools = self.structures(UnitTypeId.SPAWNINGPOOL)

            # Initialize flag on first call
            if not hasattr(self, "spawning_pool_ready"):
                self.spawning_pool_ready = False

            # Check ready status
            if spawning_pools.ready.exists:
                self.spawning_pool_ready = True
            elif spawning_pools.exists:
                # Check build progress for near-complete pools
                pool = spawning_pools.first
                if pool.build_progress >= 0.99:
                    self.spawning_pool_ready = True
                # Debug log for building progress (throttled)
                elif iteration % 100 == 0:
                    print(f"[TECH] Spawning Pool: BUILDING ({pool.build_progress*100:.1f}%)")
            elif not spawning_pools.exists:
                self.spawning_pool_ready = False

            # Status log (throttled)
            if iteration % 100 == 0 and iteration > 0:
                status = "READY" if self.spawning_pool_ready else "NOT READY"
                print(f"[TECH] Spawning Pool Status: {status}")

            # Intel Manager: Every frame - Data consistency (all managers share this)
            if self.intel is not None:
                try:
                    self.intel.update()
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] IntelManager.update() error: {e}")
                        self.last_error_log_frame = iteration

            # Micro Controller: Every frame - Combat responsiveness

            # Combat Manager: Every 4 frames - Tactical decisions
            if iteration % 4 == 0:
                if self.combat is not None:
                    try:
                        context = {}
                        await self.combat.update(self.game_phase, context)
                    except Exception as e:
                        if iteration - self.last_error_log_frame >= 50:
                            if iteration % 200 == 0:
                                print(f"[WARNING] CombatManager.update() error: {e}")
                            self.last_error_log_frame = iteration

            # Rogue Tactics Manager: Every 8 frames - Special tactics (Baneling drops, etc.)
            # CRITICAL: Lower priority than production/economy to prevent conflicts
            # But higher priority than general combat micro for tactical decisions
            if iteration % 8 == 0:
                if self.rogue_tactics is not None:
                    try:
                        await self.rogue_tactics.update()
                    except Exception as e:
                        if iteration % 200 == 0:
                            print(f"[WARNING] RogueTacticsManager.update() error: {e}")

            # Spell Unit Manager: Every 16 frames - Optimized spell unit targeting
            # CRITICAL: Spell units require less frequent updates to reduce CPU load
            # and allow proper spell cooldown management
            if iteration % 16 == 0:
                if hasattr(self, "spell_unit_manager") and self.spell_unit_manager is not None:
                    try:
                        await self.spell_unit_manager.update(iteration)
                    except Exception as e:
                        if iteration % 200 == 0:
                            print(f"[WARNING] SpellUnitManager.update() error: {e}")

            # Production & Economy: Every 22 frames - Building & worker optimization
            if iteration % 22 == 0:
                # Production Manager
                # CRITICAL FIX: Always call production.update() regardless of panic mode
                # Panic mode was blocking normal production entirely, causing unit starvation
                # NOW: Even in panic mode, we maintain basic production flow
                if self.production is not None:
                    try:
                        # DEBUG: Log production manager call
                        if iteration % 88 == 0:  # Every 4 seconds
                            print(f"[PRODUCTION] Calling production.update() at iteration {iteration}")

                        # CRITICAL FIX: Skip ideal_composition - it's causing blocking issues
                        # Production manager has its own composition logic internally
                        # No need to pre-calculate it here, which was causing delays

                        # CRITICAL FIX: Add timeout to prevent game freezing from blocking operations
                        # Always run production manager - it has its own panic handling logic inside
                        await asyncio.wait_for(
                            self.production.update(self.game_phase),
                            timeout=0.2  # 200ms timeout to prevent blocking
                        )

                        if self.intel and self.intel.signals.get("need_overseer", False):
                            await self._morph_overseer()
                    except Exception as e:
                        # Enhanced error logging with stack trace
                        error_details = traceback.format_exc()
                        if iteration - self.last_error_log_frame >= 50:
                            print(f"[ERROR] ProductionManager.update() failed at iteration {iteration}: {e}")
                            if iteration % 200 == 0:  # Detailed trace every 200 frames
                                print(f"[ERROR] Stack trace:\n{error_details}")
                            self.last_error_log_frame = iteration

                # Queen Manager: Larva injection (synchronized with production)
                if hasattr(self, "queen_manager") and self.queen_manager is not None:
                    try:
                        await self.queen_manager.manage_queens()
                    except Exception:
                        pass  # Silent fail

            # [3] Economy Manager: Every 22 frames - Building construction & worker optimization
            if iteration % 22 == 0:
                # OPTIMIZED: Worker distribution (heavy operation - only every 22 frames)
                if self.economy is not None:
                    try:
                        await self.economy._distribute_workers()
                    except Exception as e:
                        if iteration % 200 == 0:  # Throttle print statements
                            print(f"[WARNING] Worker distribution error: {e}")
                # Log game state periodically (reduced frequency to prevent frame drops)
                if iteration % 960 == 0:  # Every ~40 seconds
                    try:
                        self.write_log(
                            f"State: {self.minerals}M/{self.vespene}G, Supply: {self.supply_used}/{self.supply_cap}, Army: {self.supply_army}",
                            "DEBUG",
                        )
                    except Exception:
                        pass

                # Detect unit deaths (every 25 frames to reduce CPU load)
                try:
                    await self._detect_unit_deaths()
                except Exception:
                    pass

                if (
                    self.economy is not None
                    and self.early_defense is not None
                    and not self.early_defense.is_panic_mode()
                ):
                    try:
                        # CRITICAL FIX: Add timeout to prevent game freezing from blocking operations
                        await asyncio.wait_for(
                            self.economy.update(),
                            timeout=0.2  # 200ms timeout to prevent blocking
                        )
                        if self.intel and self.intel.signals.get("need_spine", False):
                            await asyncio.wait_for(
                                self.economy.build_defense(count=2),
                                timeout=0.1  # 100ms timeout
                            )
                    except asyncio.TimeoutError:
                        if iteration % 200 == 0:
                            print(f"[WARNING] EconomyManager.update() timed out at iteration {iteration}")
                    except Exception as e:
                        if iteration - self.last_error_log_frame >= 50:
                            if iteration % 200 == 0:  # Throttle print statements (every ~9 seconds)
                                print(f"[WARNING] EconomyManager.update() 오류: {e}")
                            self.last_error_log_frame = iteration

                if (
                    self.gas_maximizer is not None
                    and self.early_defense is not None
                    and not self.early_defense.is_panic_mode()
                ):
                    try:
                        await self.gas_maximizer.maximize_gas_income()
                    except Exception as e:
                        if iteration - self.last_error_log_frame >= 50:
                            if iteration % 200 == 0:  # Throttle print statements (every ~9 seconds)
                                print(f"[WARNING] GasMaximizer.maximize_gas_income() 오류: {e}")
                            self.last_error_log_frame = iteration

                # CRITICAL: Production bottleneck fix - Execute first to ensure production
                try:
                    await self.fix_production_bottleneck()
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] fix_production_bottleneck() 오류: {e}")
                        self.last_error_log_frame = iteration

                # CRITICAL: Aggressive army production - Always produce units when resources available
                # This ensures continuous unit production regardless of other conditions
                try:
                    await self._build_army_aggressive()
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] _build_army_aggressive() 오류: {e}")
                        self.last_error_log_frame = iteration

            # [4] Resource Management: Integrated into ProductionManager priority queue
            # IMPROVED: Resource dump is now handled by ProductionManager._flush_resources()
            # This ensures proper priority ordering and prevents conflicts with tech/production
            # Removed direct _force_resource_dump() call to prevent priority inversion

                # Flush minerals to defense structures
                try:
                    await self._flush_minerals_to_defense()
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        if iteration % 200 == 0:  # Throttle print statements (every ~9 seconds)
                            print(f"[WARNING] _flush_minerals_to_defense() 오류: {e}")
                        self.last_error_log_frame = iteration

            # [4] Combat Manager: Every 4 frames (combat needs responsiveness)
            # User optimized: Combat logic moved to CombatManager using IntelManager cache
            if iteration % 4 == 0:
                if self.combat is not None:
                    try:
                        context = {}
                        await self.combat.update(self.game_phase, context)
                    except Exception as e:
                        if iteration - self.last_error_log_frame >= 50:
                            if iteration % 200 == 0:
                                print(f"[WARNING] CombatManager.update() error: {e}")
                            self.last_error_log_frame = iteration

            # [6] Scouting System: Every 40 frames (scouting doesn't need high frequency)
            if iteration % 40 == 0:
                if self.scout is not None:
                    try:
                        context = {}
                        await self.scout.update(context)
                    except Exception as e:
                        if iteration - self.last_error_log_frame >= 50:
                            print(f"[WARNING] ScoutingSystem.update() error: {e}")
                            self.last_error_log_frame = iteration

            # [6] Strategy Analyzer & Analysis Hub: Every 100 frames - Heavy analysis
            if iteration % 100 == 0:
                # Strategy Analyzer (opponent tracking + counter strategy)
                if self.strategy_analyzer is not None:
                    try:
                        await self.strategy_analyzer.apply_counter_strategy()
                    except Exception as e:
                        if iteration - self.last_error_log_frame >= 50:
                            print(f"[WARNING] StrategyAnalyzer.apply_counter_strategy() 오류: {e}")
                            self.last_error_log_frame = iteration

                # Analysis Hub: Unified analysis (battle + danger signals)
                # Analysis Hub removed (using Vertex AI instead)
                # Placeholder for future AI-driven strategic decisions

                _config = Config()
                try:
                    if iteration % _config.DIAGNOSE_INTERVAL == 0:
                        await self._diagnose_production_status(iteration)
                except Exception as e:
                    if iteration % 200 == 0:
                        print(f"[WARNING] Production diagnosis error: {e}")

                if self.strategy_analyzer is not None:
                    try:
                        await self.strategy_analyzer.apply_counter_strategy()
                    except Exception as e:
                        if iteration - self.last_error_log_frame >= 50:
                            print(f"[WARNING] StrategyAnalyzer.apply_counter_strategy() error: {e}")
                            self.last_error_log_frame = iteration

                # CPU/GPU Load Balancing: Update cached values periodically
                if hasattr(self, "_cached_worker_count"):
                    delattr(self, "_cached_worker_count")
                if hasattr(self, "_cached_army_count"):
                    delattr(self, "_cached_army_count")
                if hasattr(self, "_cached_tech_level"):
                    delattr(self, "_cached_tech_level")

                try:
                    self._decide_strategy()

                    # Neural network action selection synchronized with CPU workload for balanced resource usage
                    if self.use_neural_network and self.neural_network is not None:
                        try:
                            # Get neural network action recommendation
                            neural_action = self.choose_action()

                            # Apply neural network action to strategy
                            if neural_action and Action:
                                if neural_action == Action.ATTACK:
                                    # Neural network recommends attack - prioritize aggressive strategy
                                    if hasattr(self, "intel") and self.intel:
                                        self.intel.signals["neural_attack"] = True
                                elif neural_action == Action.DEFENSE:
                                    # Neural network recommends defense - prioritize defensive strategy
                                    if hasattr(self, "intel") and self.intel:
                                        self.intel.signals["neural_defense"] = True
                                elif neural_action == Action.ECONOMY:
                                    # Neural network recommends economy focus
                                    if hasattr(self, "intel") and self.intel:
                                        self.intel.signals["neural_economy"] = True

                            # Log neural network action periodically
                            # PERFORMANCE: Increased from 200 to 400 frames for CPU load reduction
                            if iteration % 400 == 0:  # Every ~18 seconds
                                print(
                                    f"[NEURAL] Action: {neural_action.name if neural_action else 'None'} (GPU inference active)"
                                )
                        except Exception as e:
                            if iteration - self.last_error_log_frame >= 50:
                                print(f"[WARNING] Neural network action selection error: {e}")
                                self.last_error_log_frame = iteration
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] _decide_strategy() 오류: {e}")
                        self.last_error_log_frame = iteration

            # Additional combat logic (handled separately from CombatManager)
            # These are strategic decisions that don't need high frequency

            # Attack Timing Logic: Every 30 frames - Strategic attack decisions
            if iteration % 30 == 0:
                try:
                    await self._execute_attack_logic()
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] _execute_attack_logic() 오류: {e}")
                        self.last_error_log_frame = iteration

            # Defensive Army Baseline: Every 25 frames - Maintain minimum defense
            if iteration % 25 == 0:
                try:
                    await self._maintain_defensive_army()
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] _maintain_defensive_army() 오류: {e}")
                        self.last_error_log_frame = iteration

            # Defensive Rally: Every 15 frames - Gather units at defensive positions
            if iteration % 15 == 0:
                try:
                    await self._defensive_rally()
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] _defensive_rally() 오류: {e}")
                        self.last_error_log_frame = iteration

            # Scouting (additional): Every 40 frames - Less frequent than combat
            # Note: Main scouting is handled by ScoutingSystem in [5] section above
            if iteration % 40 == 0:
                try:
                    await self._execute_scouting()
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] _execute_scouting() 오류: {e}")
                        self.last_error_log_frame = iteration

            # Queen Management: Every 10 frames - Larva injection is critical for production
            # CRITICAL: Queen inject larva is essential for unit production
            if iteration % 10 == 0:
                try:
                    if self.queen_manager:
                        await self.queen_manager.manage_queens()
                        await self.queen_manager.defend_with_queens()
                    # Note: Manual queen inject is handled by production manager
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] QueenManager 오류: {e}")
                        self.last_error_log_frame = iteration

            # 8. Intelligent memory management (every 500 frames, approximately 20-25 seconds)
            # PERFORMANCE: Increased from 250 to 500 frames for CPU load reduction
            if iteration % 500 == 0:
                gc.collect()
                if torch and torch.cuda.is_available():
                    try:
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()  # Wait for all GPU operations to complete
                        # PERFORMANCE: Increased from 500 to 1000 frames for CPU load reduction
                        if iteration % 1000 == 0:  # Every ~44 seconds
                            gpu_memory_allocated = torch.cuda.memory_allocated(0) / 1024**3  # GB
                            gpu_memory_reserved = torch.cuda.memory_reserved(0) / 1024**3  # GB
                            print(
                                f"[GPU] Memory: Allocated={gpu_memory_allocated:.2f}GB, Reserved={gpu_memory_reserved:.2f}GB (Target: 30% usage)"
                            )
                    except:
                        pass

            # 9. Periodic cache clearing (88 frames, ~4 seconds)
            # NOTE: Debug/training chat removed to prevent spam; use screen debug text instead
            if iteration % 88 == 0:
                # Clear neural network action cache periodically
                if hasattr(self, "_cached_neural_action"):
                    delattr(self, "_cached_neural_action")

            if iteration % 100 == 0:
                try:
                    if self.personality_manager.should_chat(self.time):
                        msg = self.personality_manager.get_taunt_message()
                        await self.personality_manager.send_chat(msg)
                except Exception as e:
                    if iteration % 1000 == 0:
                        print(f"[WARNING] Personality chat error: {e}")

            if iteration % 10 == 0:
                try:
                    await self.personality_manager.process_chat_queue()
                except Exception as e:
                    if iteration % 1000 == 0:
                        print(f"[WARNING] Chat queue processing error: {e}")

            # 9-1. Bot thoughts removed to prevent chat spam
            # NOTE: Internal thoughts should be debug screen text, not chat messages

            # 12. Counter Building (50 frames) - Race-specific counter structures
            if iteration % 50 == 0:
                try:
                    if self.opponent_race:
                        if self.opponent_race and str(self.opponent_race).lower() == "terran":
                            await self._build_terran_counters()
                        elif self.opponent_race and str(self.opponent_race).lower() == "protoss":
                            await self._build_protoss_counters()
                        elif self.opponent_race and str(self.opponent_race).lower() == "zerg":
                            await self._build_zerg_counters()
                except Exception as e:
                    if iteration - self.last_error_log_frame >= 50:
                        print(f"[WARNING] 종족별 상성 빌드 오류: {e}")
                        self.last_error_log_frame = iteration

            # PERFORMANCE: Increased from 200 to 400 frames for additional CPU load reduction
            if iteration % 400 == 0:
                await self._log_game_state()

            # PERFORMANCE: Increased from 100 to 200 frames for additional CPU load reduction
            if iteration % 200 == 0:
                await self._check_logic_bugs()

            # Debug visualizer update disabled (bot monitor is disabled)
            # Removed to save CPU/GPU resources

            if iteration % 100 == 0:
                pass  # Disabled to reduce spam, only show every 30 seconds

            # 15. Victory detection: if no enemy structures/units remain, leave game automatically
            try:
                enemy_structures = getattr(self, "enemy_structures", [])
                enemy_units = getattr(self, "enemy_units", [])

                def _is_empty(collection) -> bool:
                    try:
                        if isinstance(collection, list):
                            return len(collection) == 0
                        if hasattr(collection, "empty"):
                            return bool(collection.empty)
                        if hasattr(collection, "amount"):
                            return collection.amount == 0
                        return not bool(collection)
                    except Exception:
                        return False

                no_structures = _is_empty(enemy_structures)
                no_units = _is_empty(enemy_units)

                # Require some game time to avoid false positives at start
                if no_structures and no_units and self.time > 180:
                    if self.victory_detected_time is None:
                        self.victory_detected_time = self.time
                    elif self.time - self.victory_detected_time >= 3.0:
                        print("[VICTORY] No enemy structures/units remain. Leaving game.")
                        self.game_ended = True
                        try:
                            for unit in self.units:
                                unit.stop()
                        except Exception:
                            pass
                        try:
                            if hasattr(self, "client") and self.client:
                                if hasattr(self.client, "leave_game"):
                                    await self.client.leave_game()  # type: ignore
                                else:
                                    await self.client.leave()  # type: ignore
                        except Exception:
                            pass
                        return
                else:
                    # Reset debounce if enemy returns or detection was false
                    self.victory_detected_time = None
            except Exception:
                # Enemy detection failed; do nothing to keep game running
                pass

            if torch and iteration % 1000 == 0:
                try:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass

        except Exception as e:
            # Error in melee ladder logic - Enhanced debug output
            error_type = type(e).__name__
            error_msg = str(e)

            # Enhanced debug output
            instance_id = getattr(self, "instance_id", 0)
            instance_tag = f"[ID:{instance_id}]"

            if iteration - self.last_error_log_frame >= 50:
                print(f"\n{instance_tag} ⚠️ MELEE LADDER LOGIC ERROR")
                print(f"   Time: {self.time:.2f}s | Iteration: {iteration}")
                print(f"   Error Type: {error_type}")
                print(f"   Error Message: {error_msg}")

                # Game state context
                try:
                    print(
                        f"   Context: M:{self.minerals} G:{self.vespene} | Supply:{self.supply_used}/{self.supply_cap}"
                    )

                    print(f"   Traceback: {traceback.format_exc()}")
                except Exception:
                    pass

                # Save error to file for debugging
                try:
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    data_dir = os.path.join(script_dir, "data")
                    os.makedirs(data_dir, exist_ok=True)
                    error_log_path = os.path.join(data_dir, "error_log.txt")
                    with open(error_log_path, "a", encoding="utf-8") as f:

                        f.write(f"{'=' * 70}\n")
                        f.write(f"Error at iteration {iteration} (time: {self.time:.1f}s)\n")
                        f.write(f"Error type: {error_type}\n")
                        f.write(f"Error message: {error_msg}\n")
                        f.write(f"Traceback:\n{traceback.format_exc()}\n")
                        f.write(f"{'=' * 70}\n\n")
                except Exception as log_error:
                    print(f"[WARNING] Failed to write error log: {log_error}")

                self.last_error_log_frame = iteration

                # Enhanced error logging with auto-fixer (if available)
                # Commented out error_auto_fixer import to avoid ModuleNotFoundError
                # try:
                #     from error_auto_fixer import analyze_and_log_error
                #     error_info = analyze_and_log_error(e, {
                #         "iteration": iteration,
                #         "game_time": self.time,
                #         "instance_id": getattr(self, 'instance_id', 0)
                #     })
                #
                #     # Log detailed error information
                #     instance_id = getattr(self, 'instance_id', 0)
                #     instance_tag = f"[ID:{instance_id}]"
                #
                #     if error_info.get("file") and error_info.get("line"):
                #         if error_info.get("code_line"):
                #
                #     if error_info.get("suggested_fixes"):
                #         for fix in error_info["suggested_fixes"]:
                #             logger.error(f"{instance_tag}    - {fix['description']}")
                # except ImportError:
                #     # Fallback if error_auto_fixer is not available
                #     traceback.print_exc()
                # except Exception as fixer_error:
                #     # If auto-fixer itself fails, use standard logging

                # Standard error logging (error_auto_fixer disabled)
                try:
                    instance_id = getattr(self, "instance_id", 0)
                    instance_tag = f"[ID:{instance_id}]"
                    logger.error(f"{instance_tag} ⚠️ 로직 에러 발생 (프레임 {iteration}): {e}")
                    traceback.print_exc()
                except Exception:
                    # Fallback if logger fails
                    print(f"⚠️ 로직 에러 발생 (프레임 {iteration}): {e}")
                    traceback.print_exc()

                self.last_error_log_frame = iteration

    async def _execute_micro_ladder_logic(self, iteration: int):
        """
        Micro Ladder 전용 로직 - 순수 유닛 컨트롤만 실행

        Micro Ladder 규칙:
        - 유닛만 존재 (일꾼, 건물 없음)
        - 공수 교대 방식
        - 1분 안에 전멸시키거나 버텨내야 함
        """
        try:
            # Get all combat units
            # CRITICAL: Use whitelist approach - only Zergling+ combat units can participate
            combat_units = self.units.filter(
                lambda u: u.type_id in self.combat_unit_types and u.is_ready
            )
            if not combat_units.exists:
                return

            # Get enemy units
            enemy_units = getattr(self, "enemy_units", [])
            if isinstance(enemy_units, list):
                enemy_list = enemy_units
            else:
                enemy_list = list(enemy_units) if hasattr(enemy_units, "__iter__") else []

            # Strategy: Focus Fire + Kiting (Enhanced for ladder play)
            if enemy_list and len(enemy_list) > 0:
                # Find best target for focus fire (lowest health + shield)
                def get_total_health(enemy):
                    try:
                        health = getattr(enemy, "health", 0) or 0
                        shield = getattr(enemy, "shield", 0) or 0
                        return health + shield
                    except:
                        return 9999

                sorted_enemies = sorted(enemy_list, key=get_total_health)
                primary_target = sorted_enemies[0]

                # All units focus fire on primary target
                for unit in combat_units:
                    try:
                        if not unit.is_ready:
                            continue

                        # Get unit attack range
                        attack_range = (
                            getattr(unit, "ground_range", 0) or getattr(unit, "air_range", 0) or 5
                        )
                        distance_to_target = unit.distance_to(primary_target.position)

                        # Check if unit is wounded (kiting logic)
                        health_pct = getattr(unit, "health_percentage", 1.0)
                        weapon_cooldown = getattr(unit, "weapon_cooldown", 0)

                        if health_pct < 0.5:
                            # Wounded unit: Kite back while attacking
                            if weapon_cooldown > 0:
                                # Retreat while reloading
                                retreat_pos = unit.position.towards(primary_target.position, -4)
                                unit.move(retreat_pos)
                            else:
                                # Attack when ready (but stay at max range)
                                if distance_to_target <= attack_range + 2:
                                    unit.attack(primary_target)
                                else:
                                    # Move closer to attack range
                                    unit.move(primary_target.position)
                        else:
                            # Healthy unit: Attack directly
                            if distance_to_target <= attack_range + 1:
                                unit.attack(primary_target)
                            else:
                                # Move closer to attack
                                unit.move(primary_target.position)
                    except Exception:
                        pass
            else:
                # No enemies detected: Move towards map center (aggressive positioning)
                try:
                    map_center = self.game_info.map_center
                    for unit in combat_units:
                        if unit.is_ready:
                            unit.move(map_center)
                except Exception:
                    pass

            # Status update every 100 iterations
            if iteration % 100 == 0:
                unit_count = (
                    combat_units.amount
                    if hasattr(combat_units, "amount")
                    else len(list(combat_units))
                )
                enemy_count = len(enemy_list)
                print(
                    f"[MICRO LADDER] [{int(self.time)}s] Units: {unit_count} | Enemies: {enemy_count}"
                )

        except Exception as e:
            # Error in micro ladder logic - just continue
            if iteration - self.last_error_log_frame >= 50:
                print(f"[WARNING] Micro ladder logic error: {e}")
                self.last_error_log_frame = iteration

    def _check_rush_failure_and_transition(self):
        """
        초반 러쉬 실패 감지 및 중반 강력 빌드 전환 로직

        러쉬가 실패했다고 판단되면 중반 강력 빌드로 전환하여 공격을 가합니다.

        StrategyHub로 위임
        """
        if self.strategy_hub:
            pass
        # strategy_engine removed: StrategyHub handles all strategy logic

    def _decide_strategy(self):
        """Strategy decision - delegated to StrategyHub"""
        if self.strategy_hub:
            self.strategy_hub.update_strategy()
        # strategy_engine removed: StrategyHub handles all strategy logic

    async def _execute_combat(self):
        if self.combat_tactics:
            return await self.combat_tactics.execute_combat()
        try:
            if self.opponent_race and str(self.opponent_race).lower() == "terran":
                banelings = list(self.units(UnitTypeId.BANELING).ready)
                if banelings:
                    enemy_units = getattr(self, "enemy_units", [])
                    if enemy_units:
                        enemy_list = list(enemy_units) if hasattr(enemy_units, "__iter__") else []
                        if self.micro:
                            await self.micro.execute_baneling_vs_marines(banelings, enemy_list)
        except Exception:
            pass  # Silently fail if baneling control fails

        # Combat Manager update is now handled in the scheduler section above
        # This prevents duplicate calls and ensures proper execution order

        if not hasattr(self, "unit_micro"):
            try:
                if self.micro is not None:
                    self.unit_micro = self.micro
                else:
                    # MicroController not available, use dummy
                    class DummyMicroController:
                        async def execute_spread_attack(self, *args):
                            pass

                        async def execute_stutter_step(self, *args):
                            pass

                        async def execute_unit_micro(self, *args):
                            pass

                    self.unit_micro = DummyMicroController()  # type: ignore[assignment]
            except Exception:
                self.unit_micro = None

        intel = getattr(self, "intel", None)
        if (
            intel
            and hasattr(intel, "should_attack")
            and callable(intel.should_attack)
            and intel.should_attack()
        ):
            target = (
                self.enemy_start_locations[0]
                if self.enemy_start_locations and len(self.enemy_start_locations) > 0
                else self.game_info.map_center
            )

            # Performance optimization: Use cached units from on_step start
            # Cache units at start of step to avoid repeated queries
            cached_units = getattr(self, "_cached_units", None)
            # Optimized: Ensure cached_units is Units object, not list
            if cached_units is None or isinstance(cached_units, list):
                cached_units = self.units  # Fallback to direct access
            cached_enemy_units = getattr(self, "_cached_enemy_units", None) or getattr(
                self, "enemy_units", None
            )  # type: ignore[attr-defined]

            army_types = {
                UnitTypeId.ZERGLING,
                UnitTypeId.ROACH,
                UnitTypeId.HYDRALISK,
                UnitTypeId.QUEEN,
            }
            # Optimized: Ensure cached_units supports filter method
            if hasattr(cached_units, "filter"):
                all_army = cached_units.filter(lambda u: u.type_id in army_types)
            else:
                all_army = self.units.filter(lambda u: u.type_id in army_types)

            if self.unit_micro and all_army.exists:
                await self.unit_micro.execute_unit_micro(all_army)

            # Optimized: Ensure cached_units supports callable interface
            if hasattr(cached_units, "__call__"):
                zerglings = cached_units(UnitTypeId.ZERGLING)
            else:
                zerglings = self.units(UnitTypeId.ZERGLING)
            zerglings_list = [u for u in zerglings] if hasattr(zerglings, "__iter__") else []
            if len(zerglings_list) >= 10:
                # Use cached enemy units
                if cached_enemy_units and self.micro:
                    if self.opponent_race and str(self.opponent_race).lower() == "zerg":
                        enemy_zerglings = [
                            u for u in cached_enemy_units if u.type_id == UnitTypeId.ZERGLING
                        ]
                        if enemy_zerglings and hasattr(self.micro, "execute_zvz_zergling_micro"):
                            await self.micro.execute_zvz_zergling_micro(
                                zerglings_list, enemy_zerglings
                            )
                    else:
                        if hasattr(self.micro, "execute_spread_attack"):
                            self.micro.execute_spread_attack(zerglings, target, cached_enemy_units)

            # Optimized: Safe unit access with fallback
            if hasattr(cached_units, "__call__"):
                hydras = cached_units(UnitTypeId.HYDRALISK)
            else:
                hydras = self.units(UnitTypeId.HYDRALISK)
            hydras_list = [u for u in hydras] if hasattr(hydras, "__iter__") else []
            if hydras_list and self.micro:
                if hasattr(self.micro, "execute_overlord_hunter"):
                    await self.micro.execute_overlord_hunter(hydras_list)
                if hasattr(self.micro, "execute_stutter_step"):
                    # Convert list to Units object if needed
                    try:
                        self.micro.execute_stutter_step(hydras, target)
                    except TypeError:
                        # Fallback: try with list if Units object not accepted
                        pass

            if hasattr(cached_units, "__call__"):
                roaches = cached_units(UnitTypeId.ROACH)
            else:
                roaches = self.units(UnitTypeId.ROACH)
            roaches_list = [u for u in roaches] if hasattr(roaches, "__iter__") else []
            if roaches_list and cached_enemy_units and self.micro:
                if hasattr(self.micro, "execute_spread_attack"):
                    try:
                        self.micro.execute_spread_attack(roaches, target, cached_enemy_units)
                    except TypeError:
                        # Fallback: method may not accept list
                        pass

            if hasattr(cached_units, "__call__"):
                ravagers_raw = cached_units(UnitTypeId.RAVAGER)
            else:
                ravagers_raw = self.units(UnitTypeId.RAVAGER)
            ravagers = (
                [u for u in ravagers_raw if hasattr(u, "is_ready") and u.is_ready]
                if hasattr(ravagers_raw, "__iter__")
                else []
            )
            if ravagers and cached_enemy_units and self.micro:
                await self.micro.execute_serral_bile_sniping(ravagers, cached_enemy_units)

            # Lurker control (Serral build: intelligent burrow/unburrow + area denial)
            # Use cached units to reduce CPU load
            if hasattr(cached_units, "__call__"):
                lurkers_raw = cached_units(UnitTypeId.LURKER)
            else:
                lurkers_raw = self.units(UnitTypeId.LURKER)
            lurkers = (
                [u for u in lurkers_raw if hasattr(u, "is_ready") and u.is_ready]
                if hasattr(lurkers_raw, "__iter__")
                else []
            )
            if lurkers and cached_enemy_units and self.micro:
                await self.micro.execute_lurker_area_denial(lurkers, cached_enemy_units)

        elif (
            self.intel
            and hasattr(self.intel, "should_defend")
            and callable(self.intel.should_defend)
            and self.intel.should_defend()
        ):
            # Performance optimization: Use cached units from on_step start
            cached_units = getattr(self, "_cached_units", None)
            # Optimized: Ensure cached_units is Units object, not list
            if cached_units is None or isinstance(cached_units, list):
                cached_units = self.units  # Fallback to direct access
            cached_enemy_units = (
                getattr(self, "_cached_enemy_units", None)
                or getattr(self, "known_enemy_units", None)
                or getattr(self, "enemy_units", None)
            )  # type: ignore[attr-defined]

            army_types = {
                UnitTypeId.ZERGLING,
                UnitTypeId.ROACH,
                UnitTypeId.HYDRALISK,
                UnitTypeId.LURKER,
                UnitTypeId.QUEEN,
            }
            # Optimized: Ensure cached_units supports filter method
            if hasattr(cached_units, "filter"):
                all_army = cached_units.filter(lambda u: u.type_id in army_types)
            else:
                all_army = self.units.filter(lambda u: u.type_id in army_types)

            if self.unit_micro and all_army.exists:
                await self.unit_micro.execute_unit_micro(all_army)

            if all_army.exists and self.micro and hasattr(self.micro, "execute_defensive_spread"):
                self.micro.execute_defensive_spread(all_army, self.start_location, radius=15.0)

            if self.opponent_race and str(self.opponent_race).lower() == "zerg" and self.micro:
                zerglings = cached_units(UnitTypeId.ZERGLING)
                zerglings_list = [u for u in zerglings]
                if zerglings_list and cached_enemy_units:
                    enemy_zerglings = [
                        u for u in cached_enemy_units if u.type_id == UnitTypeId.ZERGLING
                    ]
                    if enemy_zerglings and hasattr(self.micro, "execute_zvz_zergling_micro"):
                        await self.micro.execute_zvz_zergling_micro(zerglings_list, enemy_zerglings)

            if self.micro:
                hydras = cached_units(UnitTypeId.HYDRALISK)
                hydras_list = [u for u in hydras]
                if hydras_list and hasattr(self.micro, "execute_overlord_hunter"):
                    await self.micro.execute_overlord_hunter(hydras_list)

            # Defensive Lurker burrow (intelligent unburrow if enemies leave)
            # Use cached units to reduce CPU load
            lurkers = [u for u in cached_units(UnitTypeId.LURKER) if u.is_ready]
            # Use cached enemy units
            enemy_ground = []
            if cached_enemy_units:
                enemy_ground = [
                    u
                    for u in cached_enemy_units
                    if hasattr(u, "health")
                    and u.health > 0
                    and hasattr(u, "is_flying")
                    and not u.is_flying
                ]

            # Performance optimization: Cache start_location distance calculations
            # Calculate enemies near base once (reuse for all lurkers)
            enemies_near_base_cached = None
            if enemy_ground:
                # Calculate distance to start_location once and filter
                enemies_near_base_cached = [
                    e for e in enemy_ground if e.distance_to(self.start_location) < 25
                ]

            for lurker in lurkers:
                # Cache lurker position and distance to start_location (reuse in same iteration)
                lurker_pos = lurker.position
                lurker_to_start_dist = lurker_pos.distance_to(self.start_location)

                if lurker.is_burrowed:
                    # Burrowed: Check for enemies near base (use cached result)
                    if enemies_near_base_cached:
                        # Enemies near, attack them (calculate distance once per enemy)
                        enemies_in_range = [
                            e
                            for e in enemies_near_base_cached
                            if lurker_pos.distance_to(e.position) <= 10
                        ]
                        if enemies_in_range:
                            lurker.attack(enemies_in_range[0])
                    else:
                        # No enemies near base, unburrow to prepare for movement
                        lurker(AbilityId.BURROWUP_LURKER)
                else:
                    # Not burrowed: Burrow near base for defense (use cached distance)
                    if lurker_to_start_dist < 20:
                        if enemy_ground:
                            # Enemies present, burrow immediately
                            lurker(AbilityId.BURROWDOWN_LURKER)
                        else:
                            # No enemies, but stay ready near base
                            lurker.move(self.start_location)

    async def _determine_ideal_composition(self) -> Dict[UnitTypeId, float]:
        """
        상대 테크 탐지 및 상성 조합 결정 (Reactive Composition)

        상대의 건물을 확인하여 어떤 유닛을 주력으로 뽑을지 결정합니다.
        정찰 정보를 바탕으로 최적의 유닛 조합 비율을 반환합니다.

        Returns:
            Dict[UnitTypeId, float]: 유닛 타입별 목표 비율 (합계 1.0)
        """
        target_comp = {UnitTypeId.ROACH: 0.6, UnitTypeId.ZERGLING: 0.4}

        try:
            enemy_race = self.opponent_race
            if enemy_race is None:
                if hasattr(self, "scout") and self.scout:
                    enemy_race = self.scout.enemy_race
                    if enemy_race == EnemyRace.UNKNOWN:
                        return target_comp

            enemy_structures = getattr(self, "enemy_structures", None)
            if enemy_structures is None:
                return target_comp

            if str(enemy_race).lower() == "terran":
                if hasattr(enemy_structures, "of_type"):
                    starports = enemy_structures.of_type(UnitTypeId.STARPORT)
                    if starports.exists:
                        target_comp = {
                            UnitTypeId.HYDRALISK: 0.7,
                            UnitTypeId.ZERGLING: 0.3,
                        }
                        if self.iteration % 100 == 0:
                            print(
                                f"[COMPOSITION] [{int(self.time)}s] Terran Air detected - Prioritizing Hydralisks (70%)"
                            )
                        return target_comp

                if hasattr(enemy_structures, "of_type"):
                    factories = enemy_structures.of_type(UnitTypeId.FACTORY)
                    if factories.exists:
                        target_comp = {
                            UnitTypeId.ROACH: 0.5,
                            UnitTypeId.RAVAGER: 0.3,
                            UnitTypeId.ZERGLING: 0.2,
                        }
                        if self.iteration % 100 == 0:
                            print(
                                f"[COMPOSITION] [{int(self.time)}s] Terran Mech detected - Prioritizing Roach/Ravager (50%/30%)"
                            )
                        return target_comp

            elif str(enemy_race).lower() == "protoss":
                if hasattr(enemy_structures, "of_type"):
                    stargates = enemy_structures.of_type(UnitTypeId.STARGATE)
                    if stargates.exists:
                        target_comp = {
                            UnitTypeId.HYDRALISK: 0.8,
                            UnitTypeId.ZERGLING: 0.2,
                        }
                        if self.iteration % 100 == 0:
                            print(
                                f"[COMPOSITION] [{int(self.time)}s] Protoss Air detected - Prioritizing Hydralisks (80%)"
                            )
                        return target_comp

                if hasattr(enemy_structures, "of_type"):
                    robotics = enemy_structures.of_type(UnitTypeId.ROBOTICSFACILITY)
                    if robotics.exists:
                        target_comp = {
                            UnitTypeId.ZERGLING: 0.6,
                            UnitTypeId.BANELING: 0.2,
                            UnitTypeId.ROACH: 0.2,
                        }
                        if self.iteration % 100 == 0:
                            print(
                                f"[COMPOSITION] [{int(self.time)}s] Protoss Robotics detected - Prioritizing Zergling/Baneling (60%/20%)"
                            )
                        return target_comp

            elif str(enemy_race).lower() == "zerg":
                target_comp = {UnitTypeId.ROACH: 0.6, UnitTypeId.ZERGLING: 0.4}

        except Exception as e:
            if self.iteration % 100 == 0:
                print(f"[WARNING] Composition determination error: {e}")

        return target_comp

    async def _execute_attack_logic(self):
        """
        적절한 공격 타이밍 결정 및 실행 (Attack Timing Logic)

        병력이 충분하지 않을 때 나가서 각개격파 당하는 것을 방지하기 위한
        임계치(Threshold) 로직입니다.

        공격 조건:
        - 조건 A: 인구수가 160 이상일 때 (풀업 물량 공세)
        - 조건 B: 최소 전투병력 40기 이상일 때
        - 조건 C: 적 유닛이 내 본진 근처에 있을 때 (수비적 공격)
        """
        # strategy_engine removed: attack logic handled by CombatManager + StrategyHub
        if self.combat:
            try:
                context = {
                    "supply_army": self.supply_army,
                    "supply_used": self.supply_used,
                    "minerals": self.minerals,
                    "vespene": self.vespene,
                }
                await self.combat.update(self.game_phase, context)
            except Exception as e:
                print(f"[WARNING] CombatManager.update() 오류: {e}")

    async def fix_production_bottleneck(self):
        """
        생산 병목 해결 함수

        자원이 쌓이는데 병력이 생산되지 않는 문제를 해결합니다.

        핵심 원인:
        1. 애벌레(Larva) 수급 부재
        2. 생산 조건(Requirement)의 미충족
        3. 인구수 막힘(Supply Block)
        4. 테크 건물 부재 또는 파괴

        해결 방법:
        - 라바가 없으면 해처리 추가 건설
        - 인구수 체크를 최상단에 배치
        - 조건을 단순화하여 '돈 있으면 무조건 생산'
        - 테크 건물이 없으면 최우선으로 건설
        """
        if self.production_resilience:
            return await self.production_resilience.fix_production_bottleneck()
        try:
            # NOTE: Removed forced Spawning Pool build to avoid duplication.
            # EconomyManager handles Spawning Pool construction via early build order
            # and maintenance routines with proper safety checks.

            larvae = self.units(UnitTypeId.LARVA)

            if not larvae.exists:
                if self.minerals > 500 and self.already_pending(UnitTypeId.HATCHERY) == 0:
                    if self.townhalls.exists:
                        main_base = self.townhalls.first
                        macro_pos = main_base.position.towards(self.game_info.map_center, 8)
                        # CRITICAL: Check for duplicate construction before building
                        if not self.structures(UnitTypeId.HATCHERY).closer_than(15, macro_pos).exists:
                            try:
                                await self.build(UnitTypeId.HATCHERY, near=macro_pos)
                            except Exception:
                                pass
                return

            # NOTE: Overlord production delegated to ProductionManager
            # Removed supply_left < 4 check (line 2905) to prevent duplication
            # ProductionManager has more sophisticated overlord prediction logic

            pool_query = self.structures(UnitTypeId.SPAWNINGPOOL)
            spawning_pools_ready = pool_query.ready.exists or (
                pool_query.exists and pool_query.first.build_progress >= 0.99
            )
            if spawning_pools_ready:
                # 🎯 Pool detected - production can proceed
                if self.iteration % 100 == 0:
                    pool_progress = pool_query.first.build_progress if pool_query.exists else 1.0
                    print(f"[ZERGLING PRODUCTION] Pool ready ({pool_progress*100:.1f}%) - Attempting production...")

                larvae_list = list(larvae)
                produced_count = 0
                max_production = min(10, len(larvae_list))
                for i, larva in enumerate(larvae_list[:max_production]):
                    if not larva.is_ready:
                        continue
                    # type: ignore[operator] keeps can_afford wrapper from type errors
                    if self.can_afford(UnitTypeId.ZERGLING) and self.supply_left >= 2:  # type: ignore[operator]
                        try:
                            await larva.train(UnitTypeId.ZERGLING)
                            produced_count += 1
                        except Exception:
                            continue

                if produced_count > 0 and self.iteration % 50 == 0:
                    print(
                        f"[PRODUCTION FIX] [{int(self.time)}s] Produced {produced_count} Zerglings (Minerals: {int(self.minerals)}M, Larva: {len(larvae_list)})"
                    )

            warren_query = self.structures(UnitTypeId.ROACHWARREN)
            roach_warrens_ready = warren_query.ready.exists or (
                warren_query.exists and warren_query.first.build_progress >= 0.99
            )
            if roach_warrens_ready:
                # 🎯 Warren detected - production can proceed
                if self.iteration % 100 == 0:
                    warren_progress = warren_query.first.build_progress if warren_query.exists else 1.0
                    print(f"[ROACH PRODUCTION] Warren ready ({warren_progress*100:.1f}%) - Attempting production...")

                larvae_list = list(larvae)
                produced_count = 0
                max_production = min(5, len(larvae_list))
                for i, larva in enumerate(larvae_list[:max_production]):
                    if not larva.is_ready:
                        continue
                    # type: ignore[operator] keeps can_afford wrapper from type errors
                    if self.can_afford(UnitTypeId.ROACH) and self.supply_left >= 2:  # type: ignore[operator]
                        try:
                            await larva.train(UnitTypeId.ROACH)
                            produced_count += 1
                        except Exception:
                            continue

            den_query = self.structures(UnitTypeId.HYDRALISKDEN)
            hydra_dens_ready = den_query.ready.exists or (
                den_query.exists and den_query.first.build_progress >= 0.99
            )
            if hydra_dens_ready:
                # 🎯 Den detected - production can proceed
                if self.iteration % 100 == 0:
                    den_progress = den_query.first.build_progress if den_query.exists else 1.0
                    print(f"[HYDRALISK PRODUCTION] Den ready ({den_progress*100:.1f}%) - Attempting production...")

                larvae_list = list(larvae)
                produced_count = 0
                max_production = min(5, len(larvae_list))
                for i, larva in enumerate(larvae_list[:max_production]):
                    if not larva.is_ready:
                        continue
                    # type: ignore[operator] keeps can_afford wrapper from type errors
                    if self.can_afford(UnitTypeId.HYDRALISK) and self.supply_left >= 2:  # type: ignore[operator]
                        try:
                            await larva.train(UnitTypeId.HYDRALISK)
                            produced_count += 1
                        except Exception:
                            continue

        except Exception as e:
            if self.iteration % 100 == 0:
                print(f"[WARNING] fix_production_bottleneck error: {e}")

    async def _diagnose_production_status(self, iteration: int):
        if self.production_resilience:
            return await self.production_resilience.diagnose_production_status(iteration)
        try:
            _config = Config()
            if iteration % _config.DIAGNOSE_INTERVAL == 0:
                larvae = self.units(UnitTypeId.LARVA)
                larvae_count = larvae.amount if hasattr(larvae, "amount") else len(list(larvae))

                # Check pending units (including eggs)
                pending_zerglings = self.already_pending(UnitTypeId.ZERGLING)
                pending_roaches = self.already_pending(UnitTypeId.ROACH)
                pending_hydralisks = self.already_pending(UnitTypeId.HYDRALISK)

                # Check current unit counts (excluding eggs)
                zergling_count = self.units(UnitTypeId.ZERGLING).amount
                roach_count = self.units(UnitTypeId.ROACH).amount
                hydralisk_count = self.units(UnitTypeId.HYDRALISK).amount

                # Check tech buildings (use structures for accuracy) and add visibility/debug
                pool_query = self.structures(UnitTypeId.SPAWNINGPOOL)
                # Persistent ready flag to avoid flip-flop if visibility/cache hiccups
                if not hasattr(self, "spawning_pool_ready_flag"):
                    self.spawning_pool_ready_flag = False

                pool_ready_now = False
                pool_progress = 0.0  # Scope issue: define outside try block
                pool_is_ready = False

                try:
                    if pool_query.ready.exists:
                        pool_ready_now = True
                        pool_progress = 1.0
                        pool_is_ready = True
                    elif pool_query.exists:
                        # Treat near-complete builds as ready to unblock production
                        try:
                            pool_progress = pool_query.first.build_progress
                            # IMPROVED: Log optimization - reduce frequency for DEBUG logs
                            if iteration % 500 == 0:  # Reduced from 50 to 500 to minimize I/O
                                # Use logger.debug if available, otherwise skip in training mode
                                try:
                                    loguru_logger.debug(f"Spawning Pool detected: Building... ({pool_progress*100:.1f}%)")
                                except ImportError:
                                    # Only print if not in training mode to reduce I/O overhead
                                    if not getattr(self, 'train_mode', False):
                                        print(f"[DEBUG] Spawning Pool detected: Building... ({pool_progress*100:.1f}%)")
                            if pool_progress >= 0.99:
                                pool_ready_now = True
                        except Exception:
                            pass
                except Exception:
                    pass

                # Update sticky flag: once ready, stay true until no pool exists
                if pool_ready_now:
                    if not self.spawning_pool_ready_flag:
                        print("\n" + "="*80)
                        print("✅✅✅ SPAWNING POOL READY FLAG SET TO TRUE! ✅✅✅")
                        print(f"    Progress: {pool_progress*100:.1f}% | Ready: {pool_is_ready}")
                        print(f"    Time: {int(self.time)}s | Supply: {self.supply_used}")
                        print(f"    🎯 ZERGLING PRODUCTION NOW ENABLED!")
                        print("="*80 + "\n")

                        # 📊 Update ProductionManager tracking
                        if self.production and not self.production.spawning_pool_completed:
                            self.production.spawning_pool_completed = True
                            self.production.build_order_timing["spawning_pool"] = self.time
                            print(f"[PRODUCTION MANAGER] Spawning Pool completion recorded at {self.time}s")

                    self.spawning_pool_ready_flag = True
                elif not pool_query.exists:
                    self.spawning_pool_ready_flag = False

                spawning_pool_ready = self.spawning_pool_ready_flag

                # 🔍 FIX: Include buildings under construction (progress >= 99%) as "ready" for production
                # This allows production to proceed as soon as building is nearly complete
                roach_warren_query = self.structures(UnitTypeId.ROACHWARREN)
                roach_warren_ready = False
                warren_just_completed = False
                if roach_warren_query.ready.exists:
                    roach_warren_ready = True
                    if self.production and not self.production.roach_warren_completed:
                        self.production.roach_warren_completed = True
                        self.production.build_order_timing["roach_warren"] = self.time
                        warren_just_completed = True
                elif roach_warren_query.exists:
                    # Include near-complete builds as ready
                    try:
                        warren = roach_warren_query.first
                        if warren.build_progress >= 0.99:
                            roach_warren_ready = True
                            if self.production and not self.production.roach_warren_completed:
                                self.production.roach_warren_completed = True
                                self.production.build_order_timing["roach_warren"] = self.time
                                warren_just_completed = True
                    except Exception:
                        pass

                # 🔥 Log when Roach Warren completes
                if warren_just_completed and iteration % 50 == 0:
                    print("\n" + "="*80)
                    print("🔴🔴🔴 ROACH WARREN COMPLETED! 🔴🔴🔴")
                    print(f"    Time: {int(self.time)}s | Supply: {self.supply_used}")
                    print(f"    💪 ROACH PRODUCTION NOW ENABLED!")
                    print("="*80 + "\n")

                hydralisk_den_query = self.structures(UnitTypeId.HYDRALISKDEN)
                hydralisk_den_ready = False
                den_just_completed = False
                if hydralisk_den_query.ready.exists:
                    hydralisk_den_ready = True
                    if self.production and not self.production.hydralisk_den_completed:
                        self.production.hydralisk_den_completed = True
                        self.production.build_order_timing["hydralisk_den"] = self.time
                        den_just_completed = True
                elif hydralisk_den_query.exists:
                    # Include near-complete builds as ready
                    try:
                        den = hydralisk_den_query.first
                        if den.build_progress >= 0.99:
                            hydralisk_den_ready = True
                            if self.production and not self.production.hydralisk_den_completed:
                                self.production.hydralisk_den_completed = True
                                self.production.build_order_timing["hydralisk_den"] = self.time
                                den_just_completed = True
                    except Exception:
                        pass

                # 🔥 Log when Hydralisk Den completes
                if den_just_completed and iteration % 50 == 0:
                    print("\n" + "="*80)
                    print("💜💜💜 HYDRALISK DEN COMPLETED! 💜💜💜")
                    print(f"    Time: {int(self.time)}s | Supply: {self.supply_used}")
                    print(f"    🎯 HYDRALISK PRODUCTION NOW ENABLED!")
                    print("="*80 + "\n")

                # 🌟 CHECK IF ALL TECH BUILDINGS COMPLETED
                all_tech_complete = (
                    self.spawning_pool_ready_flag and
                    True  # Fixed: True  # Fixed: True (removed undefined vars) (removed undefined vars)
                )
                if all_tech_complete and iteration % 50 == 0:
                    print("\n" + "#"*80)
                    print("🌟🌟🌟 ALL TECH BUILDINGS COMPLETED! 🌟🌟🌟")
                    print(f"✅ Spawning Pool: READY | ✅ Roach Warren: READY | ✅ Hydralisk Den: READY")
                    print(f"    Time: {int(self.time)}s | Supply: {self.supply_used}")
                    print(f"    📊 FULL ARMY COMPOSITION NOW AVAILABLE!")
                    print("    📈 Game phase should transition to ATTACK/MACRO mode")
                    print("#"*80 + "\n")

                # Check if can afford units
                can_afford_zergling = self.can_afford(UnitTypeId.ZERGLING)
                can_afford_roach = self.can_afford(UnitTypeId.ROACH)
                can_afford_hydralisk = self.can_afford(UnitTypeId.HYDRALISK)

                # 🔥 GAS EXTRACTION DIAGNOSIS (critical for Roach/Hydra production)
                extractors = self.structures(UnitTypeId.EXTRACTOR).ready
                extractor_count = extractors.amount if hasattr(extractors, "amount") else len(list(extractors))
                workers_on_gas = 0
                try:
                    # Count workers assigned to gas extraction
                    for extractor in extractors:
                        workers_on_gas += len(extractor.assigned_harvesters)
                except Exception:
                    pass

                print(f"\n{'=' * 80}")
                print(f"[PRODUCTION DIAGNOSIS] [{int(self.time)}s] Iteration: {iteration}")
                print(f"{'=' * 80}")
                print(f"📊 Resources:")
                print(f"   Minerals: {int(self.minerals)}M | Vespene: {int(self.vespene)}G")
                print(f"   Supply: {self.supply_used}/{self.supply_cap} (Left: {self.supply_left})")
                print(f"\n⛽ Gas Extraction Status:")
                print(f"   Extractors: {extractor_count} | Workers on Gas: {workers_on_gas}")
                if extractor_count == 0:
                    print(f"   ⚠️ NO EXTRACTORS - Cannot produce Roaches/Hydralisks!")
                elif workers_on_gas == 0:
                    print(f"   ⚠️ NO WORKERS ON GAS - Vespene accumulation blocked!")

                # Air Force Status
                spire_ready = self.structures(UnitTypeId.SPIRE).ready.exists
                mutalisk_count = self.units(UnitTypeId.MUTALISK).amount
                corruptor_count = self.units(UnitTypeId.CORRUPTOR).amount
                if spire_ready or mutalisk_count > 0 or corruptor_count > 0:
                    print(f"\n🕊️ AIR FORCE STATUS:")
                    print(f"   Spire Ready: {spire_ready}")
                    print(f"   Mutalisk: {mutalisk_count} units")
                    print(f"   Corruptor: {corruptor_count} units")
                    spires = self.structures(UnitTypeId.SPIRE)
                    if any(s.build_progress > 0.90 and not s.is_ready for s in spires):
                        print(f"   ⚠️ Spire nearly complete! Saving Vespene for Mutalisks.")

                print(f"\n🐛 Larva Status:")
                print(f"   Larva Count: {larvae_count}")
                print(
                    f"   Larva Ready: {larvae.ready.exists if hasattr(larvae, 'ready') else 'N/A'}"
                )
                print(f"\n🏗️ Tech Buildings:")
                print(f"   Spawning Pool Ready: {self.spawning_pool_ready_flag} (flag) | {spawning_pool_ready} (local)")
                print(f"   Roach Warren Ready: {roach_warren_ready}")
                print(f"   Hydralisk Den Ready: {hydralisk_den_ready}")
                print(f"\n💵 Can Afford:")
                print(
                    f"   Zergling: {can_afford_zergling} | Roach: {can_afford_roach} | Hydralisk: {can_afford_hydralisk}"
                )
                print(f"\n👥 Unit Counts (Current):")
                print(
                    f"   Zerglings: {zergling_count} | Roaches: {roach_count} | Hydralisks: {hydralisk_count}"
                )
                print(f"\n⏳ Pending Units (Including Eggs):")
                print(
                    f"   Zerglings: {pending_zerglings} | Roaches: {pending_roaches} | Hydralisks: {pending_hydralisks}"
                )

                # Diagnosis
                print(f"\n🔍 Diagnosis:")
                if larvae_count == 0:
                    print(
                        f"   ⚠️ NO LARVAE - Production blocked! Need more hatcheries or queen injects."
                    )
                elif larvae_count >= 3 and self.minerals > 500:
                    if spawning_pool_ready and can_afford_zergling and self.supply_left >= 2:
                        print(f"   ✅ Should produce Zerglings but not producing!")
                        print(
                            f"   🔴 PROBLEM: Production logic may not be executing or larvae.train() failing"
                        )
                    else:
                        if not spawning_pool_ready:
                            print(f"   ⚠️ Spawning Pool not ready - cannot produce Zerglings")
                        if not can_afford_zergling:
                            print(f"   ⚠️ Cannot afford Zergling (need 50M)")
                        if self.supply_left < 2:
                            print(f"   ⚠️ Supply blocked (need 2 supply)")
                else:
                    print(f"   ✅ Conditions look normal")
                print(f"{'=' * 80}\n")
        except Exception as e:
            if iteration % 100 == 0:
                print(f"[WARNING] Production diagnosis error: {e}")

    async def _maintain_defensive_army(self):
        """
        방어 병력 최소 기준 설정 (Safety Line)

        상대가 오기 전, "최소 이 정도는 있어야 한다"는 기준을 정해 자원을 우선적으로 쓰게 합니다.
        게임 시간에 따라 최소 방어 병력 기준이 증가합니다.
        """
        if self.combat_tactics:
            return await self.combat_tactics.maintain_defensive_army()
        try:
            army = self.units.filter(lambda u: u.type_id in self.combat_unit_types)
            army_count = army.amount if hasattr(army, "amount") else len(list(army))

            min_army_count = 20 if self.time < 300 else 50

            if army_count < min_army_count:
                larvae = self.units(UnitTypeId.LARVA).ready
                if not larvae.exists:
                    return

                if self.vespene >= 25:
                    if (
                        self.can_afford(UnitTypeId.ROACH)
                        and self.units(UnitTypeId.ROACHWARREN).ready.exists
                    ):
                        if self.supply_left >= 2:
                            try:
                                await larvae.random.train(UnitTypeId.ROACH)
                                if self.iteration % 100 == 0:
                                    print(
                                        f"[DEFENSIVE ARMY] [{int(self.time)}s] Building Roach for defense (Army: {army_count}/{min_army_count})"
                                    )
                                return
                            except Exception:
                                pass

                    if (
                        self.can_afford(UnitTypeId.HYDRALISK)
                        and self.units(UnitTypeId.HYDRALISKDEN).ready.exists
                    ):
                        if self.supply_left >= 2:
                            try:
                                await larvae.random.train(UnitTypeId.HYDRALISK)
                                if self.iteration % 100 == 0:
                                    print(
                                        f"[DEFENSIVE ARMY] [{int(self.time)}s] Building Hydralisk for defense (Army: {army_count}/{min_army_count})"
                                    )
                                return
                            except Exception:
                                pass

                if (
                    self.can_afford(UnitTypeId.ZERGLING)
                    and self.units(UnitTypeId.SPAWNINGPOOL).ready.exists
                ):
                    if self.supply_left >= 2:
                        try:
                            await larvae.random.train(UnitTypeId.ZERGLING)
                            if self.iteration % 100 == 0:
                                print(
                                    f"[DEFENSIVE ARMY] [{int(self.time)}s] Building Zergling for defense (Army: {army_count}/{min_army_count})"
                                )
                            return
                        except Exception:
                            pass

        except Exception as e:
            if self.iteration % 100 == 0:
                print(f"[WARNING] _maintain_defensive_army error: {e}")

    async def _flush_minerals_to_defense(self):
        """
        미네랄 과잉 시 방어 타워(가시촉수) 건설

        미네랄이 800~1000 이상 남는데 라바가 없다면, 입구에 방어 타워를 지어 병력을 대신합니다.
        """
        try:
            larva_count = self.units(UnitTypeId.LARVA).amount
            if self.minerals > 800 and larva_count < 3:
                if (
                    self.can_afford(UnitTypeId.SPINECRAWLER)
                    and self.units(UnitTypeId.SPAWNINGPOOL).ready.exists
                ):
                    for hatch in self.townhalls.ready:
                        close_spines = self.units(UnitTypeId.SPINECRAWLER).closer_than(
                            10, hatch.position
                        )
                        if close_spines.amount < 2:
                            # CRITICAL: Check for duplicate construction before building
                            if not self.structures(UnitTypeId.SPINECRAWLER).exists or self.structures(UnitTypeId.SPINECRAWLER).closer_than(10, hatch.position).amount < 2:
                                if self.already_pending(UnitTypeId.SPINECRAWLER) == 0:
                                    try:
                                        spine_pos = hatch.position.towards(self.game_info.map_center, 5)
                                        await self.build(UnitTypeId.SPINECRAWLER, near=spine_pos)
                                        if self.iteration % 100 == 0:
                                            print(
                                                f"[DEFENSE BUILD] [{int(self.time)}s] Building Spine Crawler (Minerals: {int(self.minerals)}M, Larva: {larva_count})"
                                            )
                                        return
                                    except Exception:
                                        continue

                if (
                    self.can_afford(UnitTypeId.HATCHERY)
                    and self.already_pending(UnitTypeId.HATCHERY) == 0
                ):
                    try:
                        if self.townhalls.exists:
                            main_base = self.townhalls.first
                            macro_pos = main_base.position.towards(self.game_info.map_center, 8)
                            # CRITICAL: Check for duplicate construction before building
                            if not self.structures(UnitTypeId.HATCHERY).closer_than(15, macro_pos).exists:
                                await self.build(UnitTypeId.HATCHERY, near=macro_pos)
                                if self.iteration % 100 == 0:
                                    print(
                                        f"[DEFENSE BUILD] [{int(self.time)}s] Building Macro Hatchery for larva (Minerals: {int(self.minerals)}M)"
                                    )
                                return
                    except Exception:
                        pass

        except Exception as e:
            if self.iteration % 100 == 0:
                print(f"[WARNING] _flush_minerals_to_defense error: {e}")

    async def _defensive_rally(self):
        """
        적의 접근 감지 및 병력 집결

        상대가 공격 오기 전 병력을 미리 모으는 '집결(Rally)' 로직입니다.
        """
        if self.combat_tactics:
            return await self.combat_tactics.defensive_rally()
        try:
            army = self.units.filter(lambda u: u.type_id in self.combat_unit_types and u.is_ready)
            if not army.exists:
                return

            enemy_near_base = None
            enemy_units_obj = getattr(self, "known_enemy_units", None) or getattr(
                self, "enemy_units", None
            )  # type: ignore[attr-defined]
            if enemy_units_obj and hasattr(enemy_units_obj, "exists") and enemy_units_obj.exists:
                townhall_positions = [th.position for th in self.townhalls]
                if townhall_positions:
                    enemy_near_base = enemy_units_obj.filter(
                        lambda u: any(u.distance_to(base) < 30 for base in townhall_positions)
                    )

            if enemy_near_base and enemy_near_base.exists:
                if self.townhalls.exists:
                    main_base = self.townhalls.first
                    closest_enemy = enemy_near_base.closest_to(main_base.position)
                    if closest_enemy:
                        target = closest_enemy.position
                        for unit in army:
                            try:
                                unit.attack(target)
                            except Exception:
                                pass

                        if self.iteration % 100 == 0:
                            print(
                                f"[DEFENSIVE RALLY] [{int(self.time)}s] Enemy detected! Attacking {enemy_near_base.amount} enemies near base"
                            )
            else:
                if self.townhalls.amount > 1:
                    natural_base = None
                    townhalls_list = list(self.townhalls.ready)
                    if len(townhalls_list) >= 2:
                        natural_base = townhalls_list[1]
                    elif len(townhalls_list) >= 1:
                        natural_base = townhalls_list[0]

                    if natural_base:
                        rally_point = natural_base.position.towards(self.game_info.map_center, 8)

                        idle_army = army.filter(lambda u: u.is_idle)
                        for unit in idle_army:
                            try:
                                if (
                                    unit.distance_to(rally_point) > 5
                                ):
                                    unit.move(rally_point)
                            except Exception:
                                pass
                else:
                    if self.townhalls.exists:
                        main_base = self.townhalls.first
                        rally_point = main_base.position.towards(self.game_info.map_center, 8)

                        idle_army = army.filter(lambda u: u.is_idle)
                        for unit in idle_army:
                            try:
                                if unit.distance_to(rally_point) > 5:
                                    unit.move(rally_point)
                            except Exception:
                                pass

        except Exception as e:
            if self.iteration % 100 == 0:
                print(f"[WARNING] _defensive_rally error: {e}")

    async def _worker_defense_emergency(self):
        """
        조건부 일꾼 동원 방어 로직 (Emergency Worker Defense)

        적의 공세가 아군 병력으로 감당하기 힘든 수준일 때만 일꾼이 참전하도록 설계된 로직입니다.
        전투력 수치(Supply 또는 Unit Count)를 실시간으로 비교하여 아군이 명백히 불리한
        '비상 상황'에서만 드론을 전장에 투입합니다.

        핵심 포인트:
        1. 전투력 비교: 단순히 적이 왔다고 일꾼을 빼는 것이 아니라, 현재 내 병력으로 막을 수 있는지 먼저 계산
        2. 병력 부재 대응: 빈집 털이나 초반 찌르기로 병력이 전방에 나가 있을 때 일꾼이 최후의 보루 역할
        3. 거리 제한: 멀리 있는 멀티의 일꾼까지 불러오는 낭비를 막고, 침입 경로에 있는 일꾼들만 전투에 참여
        """
        if self.combat_tactics:
            return await self.combat_tactics.worker_defense_emergency()
        try:
            enemy_units_obj = getattr(self, "known_enemy_units", None) or getattr(
                self, "enemy_units", None
            )  # type: ignore[attr-defined]
            if not enemy_units_obj:
                return

            # Get all townhalls positions
            townhall_positions = [th.position for th in self.townhalls]
            if not townhall_positions:
                return

            # Find enemies near any townhall (within 15 distance)
            near_enemies = enemy_units_obj.filter(
                lambda u: any(u.distance_to(base) < 15 for base in townhall_positions)
            )

            if not near_enemies.exists:
                intel = getattr(self, "intel", None)
                workers = (
                    intel.cached_workers
                    if (intel and intel.cached_workers is not None)
                    else self.workers
                )
                for drone in workers.filter(lambda w: w.is_attacking):
                    try:
                        closest_mineral = self.mineral_field.closest_to(drone)
                        if closest_mineral:
                            await self.do(drone.gather(closest_mineral))
                    except Exception:
                        pass
                return

            # IMPORTANT: Added await to all commands to ensure execution
            if near_enemies.exists:
                # Find workers that are too close to enemies (within 8 distance)
                workers_at_risk = self.workers.filter(
                    lambda w: any(w.distance_to(e) < 8 for e in near_enemies)
                )

                if workers_at_risk.exists:
                    # Retreat workers to nearest townhall or mineral field
                    for worker in workers_at_risk:
                        try:
                            # Find nearest safe location (townhall or mineral field)
                            nearest_townhall = (
                                self.townhalls.closest_to(worker.position)
                                if self.townhalls.exists
                                else None
                            )

                            if nearest_townhall and worker.distance_to(nearest_townhall) < 10:
                                # Already near townhall, move to minerals behind it
                                safe_minerals = self.mineral_field.closer_than(
                                    8, nearest_townhall.position
                                )
                                if safe_minerals.exists:
                                    await self.do(worker.gather(safe_minerals.closest_to(worker.position)))
                                else:
                                    # Move behind townhall (away from enemies)
                                    retreat_pos = nearest_townhall.position.towards(
                                        worker.position, -3
                                    )
                                    await self.do(worker.move(retreat_pos))
                            else:
                                # Move towards nearest townhall
                                if nearest_townhall:
                                    await self.do(worker.move(nearest_townhall.position))
                        except Exception:
                            pass

            my_army = self.units.filter(lambda u: u.type_id in self.combat_unit_types)

            is_outnumbered = my_army.amount < near_enemies.amount if my_army.exists else True
            is_defenseless = not my_army.exists

            # CRITICAL: If we have ANY army, workers should NOT be used for defense
            # Workers should gather resources, not fight. Army units should handle defense.
            if my_army.exists and my_army.amount > 0:
                # We have army - workers should gather resources, not retreat
                return

            # CRITICAL FIX: Minimum drone preservation (prevents economy collapse)
            # Always maintain at least MIN_DRONES_FOR_DEFENSE drones for resource gathering
            MIN_DRONES_FOR_DEFENSE = Config.MIN_DRONES_FOR_DEFENSE

            worker_count = (
                self.workers.amount if hasattr(self.workers, "amount") else len(list(self.workers))
            )

            if worker_count < MIN_DRONES_FOR_DEFENSE:
                return

            # Calculate maximum workers that can be pulled (preserve minimum)
            max_pullable_workers = max(0, worker_count - MIN_DRONES_FOR_DEFENSE)
            if max_pullable_workers <= 0:
                # Cannot pull any workers without violating minimum
                return

            if is_defenseless:
                nearby_workers = self.workers.filter(
                    lambda w: any(w.distance_to(e) < 12 for e in near_enemies)
                )

                if nearby_workers.exists:
                    workers_list = sorted(
                        [w for w in nearby_workers],
                        key=lambda w: w.health_percentage
                        if hasattr(w, "health_percentage")
                        else 1.0,
                        reverse=True,
                    )

                    # CRITICAL FIX: Respect minimum drone preservation
                    max_workers_to_pull = min(
                        max_pullable_workers,
                        max(int(worker_count * 0.3), 1),
                        min(10, len(workers_list)),
                    )

                    if max_workers_to_pull <= 0:
                        return

                    # CRITICAL FIX: Workers NO LONGER ATTACK - Only retreat to safety
                    # Worker suicide charges were caused by attack commands without retreat logic
                    defense_workers = workers_list[:max_workers_to_pull]

                    for drone in defense_workers:
                        try:
                            # CHANGED: Workers now retreat to base instead of attacking
                            # This prevents worker suicide charges into enemy positions
                            nearest_townhall = self.townhalls.closest_to(drone.position) if self.townhalls.exists else None
                            if nearest_townhall:
                                # Move behind townhall (safe position)
                                safe_pos = nearest_townhall.position.towards(self.start_location, 5)
                                await self.do(drone.move(safe_pos))
                        except Exception:
                            pass

                # Check if critical structures are being destroyed
                critical_structures = self.townhalls
                if critical_structures.exists:
                    # Check if any townhall is under heavy attack
                    for th in critical_structures:
                        enemies_near_th = near_enemies.filter(lambda e: e.distance_to(th) < 10)
                        if enemies_near_th.exists and th.health_percentage < 0.3:
                            # Critical structure under attack with low health
                            # If we've pulled all workers and still losing, consider GG
                            if worker_count < 5 and not my_army.exists:
                                # Last resort: All workers pulled, no army, critical structure dying
                                if not hasattr(self, "game_ended") or not self.game_ended:
                                    try:
                                        await self.chat_send("GG")
                                        self.game_ended = True
                                        if hasattr(self, "client") and self.client:
                                            await self.client.leave_game()  # type: ignore  # type: ignore
                                    except Exception:
                                        pass
                                return

        except Exception as e:
            # Silent fail - worker defense error shouldn't crash the bot
            current_iteration = getattr(self, "iteration", 0)
            if current_iteration - getattr(self, "last_error_log_frame", 0) >= 100:
                print(f"[WARNING] Worker defense error: {e}")
                self.last_error_log_frame = current_iteration

    async def _fast_scouting_20_seconds(self):
        """
        20초 내 초고속 정찰 로직

        게임 시작 즉시 대군주를 상대 기지로 보내 적의 빌드를 최대한 빠르게 파악합니다.
        CRITICAL: 대군주는 정찰과 인구수 공급 전용, 전투에 참여하지 않음
        """
        try:
            if not self.enemy_start_locations or len(self.enemy_start_locations) == 0:
                return

            enemy_start = self.enemy_start_locations[0]

            if hasattr(self, "scout") and self.scout:
                scout_sent = getattr(self.scout, "scout_sent", False)
                overlord_scout_sent = getattr(self.scout, "overlord_scout_sent", False)

                if scout_sent and overlord_scout_sent:
                    return

            overlords = [u for u in self.units(UnitTypeId.OVERLORD) if u.is_idle]
            if overlords:
                overlord_count = len(overlords)
                scout_overlord = overlords[0]

                try:
                    if overlord_count == 1:
                        # First overlord: Scout enemy natural expansion entrance
                        if self.enemy_start_locations:
                            enemy_start = self.enemy_start_locations[0]
                            # Move to enemy natural expansion (20 units from start location)
                            scout_target = enemy_start.towards(self.game_info.map_center, 20)
                            scout_overlord.move(scout_target)
                            if self.iteration % 50 == 0:
                                print(
                                    f"[SCOUT] [{int(self.time)}s] 대군주 스카우팅 중"
                                )
                    elif overlord_count == 2:
                        # Second overlord: Secure vision around our natural expansion
                        if self.townhalls.exists:
                            natural_position = self.townhalls.first.position.towards(
                                self.game_info.map_center, 10
                            )
                            scout_overlord.move(natural_position)
                            if self.iteration % 50 == 0:
                                print(
                                    f"[SCOUT] [{int(self.time)}s] 대군주 스카우팅 중"
                                )
                    else:
                        # Remaining overlords: Position on high ground for drop defense
                        scout_overlord.move(enemy_start)
                        if self.iteration % 50 == 0:
                            print(
                                f"[SCOUT] [{int(self.time)}s] 대군주 스카우팅 중"
                            )

                    return
                except Exception:
                    pass

            zerglings = [u for u in self.units(UnitTypeId.ZERGLING) if u.is_idle]
            if zerglings:
                scout = zerglings[0]
                try:
                    scout.move(enemy_start)
                    if self.iteration % 50 == 0:
                        print(
                            f"[SCOUT] [{int(self.time)}s] 저글링 정찰 중: 적 기지 (대군주 대기 중)"
                        )
                except Exception:
                    pass
        except Exception as e:
            pass

    async def _enforce_worker_safe_zone(self):
        """
        Intelligent worker safety management (Context-aware Worker Safe Zone) - Resource gathering focused version

        Workers intelligently stay near friendly bases and focus on resource gathering based on threat assessment.
        일꾼은 건물 건설, 이동, 공격 등 다른 모든 작업을 하지 않고 미네랄과 가스 채취만 합니다.

        핵심 원칙:
        1. Intelligent distance management: Workers return when too far from base based on threat assessment
        2. Threat-aware enemy base avoidance: Workers avoid enemy base within 60.0 distance when threat detected
        3. Context-aware resource gathering: Workers prioritize resource gathering when safe and beneficial
        4. Adaptive task assignment: Workers gather resources when idle and no higher priority tasks exist
        5. Intelligent construction management: Workers can construct buildings when needed, otherwise gather resources
        6. Real-time monitoring: Continuously assess all workers' status and optimize their tasks intelligently
        """
        try:
            if not self.townhalls.exists:
                return

            enemy_base = None
            if self.enemy_start_locations and len(self.enemy_start_locations) > 0:
                enemy_base = self.enemy_start_locations[0]

            safe_distance = 25.0
            enemy_base_safe_distance = 60.0

            for drone in self.workers:
                try:
                    closest_base = self.townhalls.closest_to(drone.position)
                    distance_to_base = drone.distance_to(closest_base.position)

                    if enemy_base:
                        distance_to_enemy_base = drone.distance_to(enemy_base)
                        if distance_to_enemy_base < enemy_base_safe_distance:
                            # Threat detected: Enemy base within 60.0 distance - intelligent retreat decision
                            minerals_near_base = self.mineral_field.closer_than(
                                15, closest_base.position
                            )
                            if minerals_near_base.exists:
                                drone.gather(minerals_near_base.random)
                            else:
                                drone.move(closest_base.position)
                            continue

                    is_gathering = (
                        drone.is_gathering
                        or drone.is_carrying_minerals
                        or drone.is_carrying_vespene
                    )
                    is_building = False
                    is_moving = False

                    if hasattr(drone, "orders") and drone.orders:
                        for order in drone.orders:
                            if hasattr(order, "ability") and order.ability:
                                ability_name = str(order.ability).upper()
                                if "BUILD" in ability_name or "CONSTRUCT" in ability_name:
                                    is_building = True
                                    break
                            if hasattr(order, "ability") and order.ability:
                                ability_name = str(order.ability).upper()
                                if "MOVE" in ability_name or "PATROL" in ability_name:
                                    is_moving = True

                    closest_mineral = (
                        self.mineral_field.closest_to(drone.position)
                        if self.mineral_field.exists
                        else None
                    )
                    closest_gas = (
                        self.units(UnitTypeId.GEYSER).closest_to(drone.position)
                        if self.units(UnitTypeId.GEYSER).exists
                        else None
                    )

                    is_near_resource = False
                    if closest_mineral:
                        mineral_to_base_dist = closest_mineral.distance_to(closest_base.position)
                        drone_to_mineral_dist = drone.distance_to(closest_mineral.position)
                        if mineral_to_base_dist < 15.0 and drone_to_mineral_dist < 5.0:
                            is_near_resource = True

                    if not is_near_resource and closest_gas:
                        gas_to_base_dist = closest_gas.distance_to(closest_base.position)
                        drone_to_gas_dist = drone.distance_to(closest_gas.position)
                        if gas_to_base_dist < 15.0 and drone_to_gas_dist < 5.0:
                            is_near_resource = True

                    # 6. Intelligent resource gathering: Assess if worker should gather based on context
                    if not is_gathering:
                        minerals_near_base = self.mineral_field.closer_than(
                            15, closest_base.position
                        )

                        if minerals_near_base.exists:
                            drone.gather(minerals_near_base.random)
                        else:
                            drone.move(closest_base.position)

                    # 7. Intelligent construction management: Assess if building should continue or switch to gathering
                    elif is_building:
                        # Check if construction is critical or can be interrupted
                        # Allow construction to continue if it's important, otherwise gather resources
                        construction_progress = 0.0
                        if hasattr(drone, "orders") and drone.orders:
                            # Assess construction progress - if nearly done, allow completion
                            for order in drone.orders:
                                if hasattr(order, "progress") and order.progress:
                                    construction_progress = order.progress

                        # Only interrupt construction if it's early stage and resources are critically needed
                        if construction_progress < 0.3:  # Less than 30% complete
                            minerals_near_base = self.mineral_field.closer_than(
                                15, closest_base.position
                            )
                            if minerals_near_base.exists:
                                drone.gather(minerals_near_base.random)
                            else:
                                drone.move(closest_base.position)
                        # Otherwise allow construction to continue

                    # 8. Intelligent distance management: Assess threat before recalling workers
                    elif distance_to_base > safe_distance or not is_near_resource:
                        # Check for enemy threats before recalling
                        try:
                            known_enemy_units = getattr(self, "enemy_units", None)  # type: ignore[attr-defined]
                            if known_enemy_units and hasattr(known_enemy_units, "closer_than"):
                                enemy_threats = known_enemy_units.closer_than(20, drone.position)
                                threat_level = (
                                    enemy_threats.amount
                                    if hasattr(enemy_threats, "amount")
                                    else len(list(enemy_threats))
                                    if enemy_threats
                                    else 0
                                )

                                if threat_level > 0:
                                    self.drone_threat_detected += 1
                                    if self.drone_threat_detected % 5 == 0:
                                        print(
                                            f"⚠️  [드론 경보] 위협 감지: {self.drone_threat_detected}회 | 탈출 성공: {self.drone_escaped_successfully}회"
                                        )
                            else:
                                threat_level = 0
                        except (AttributeError, TypeError):
                            threat_level = 0

                        # Only recall if there's actual threat or worker is very far
                        if threat_level > 0 or distance_to_base > safe_distance * 1.5:
                            self.drone_escaped_successfully += 1
                            # Return to nearest friendly base mineral field
                            minerals_near_base = self.mineral_field.closer_than(
                                15, closest_base.position
                            )

                            if minerals_near_base.exists:
                                # If mineral field exists, gather (most reliable return method)
                                drone.gather(minerals_near_base.random)
                            else:
                                # If no mineral field, move directly to base
                                drone.move(closest_base.position)

                    # 9. Additional safety check: Assess if worker at 30.0+ distance needs to return
                    elif distance_to_base > 30.0:
                        # Check if worker has important task or if return is necessary
                        has_important_task = is_building or (
                            is_gathering and drone.is_carrying_minerals
                        )

                        # Only recall if no important task and threat exists
                        if not has_important_task:
                            try:
                                known_enemy_units = getattr(self, "enemy_units", None)  # type: ignore[attr-defined]
                                if known_enemy_units and hasattr(known_enemy_units, "closer_than"):
                                    enemy_nearby = known_enemy_units.closer_than(25, drone.position)
                                    if (
                                        enemy_nearby
                                        and hasattr(enemy_nearby, "exists")
                                        and enemy_nearby.exists
                                    ):
                                        self.drone_threat_detected += 1
                                        self.drone_escaped_successfully += 1
                                        closest_base = self.townhalls.closest_to(drone.position)
                                        minerals_near_base = self.mineral_field.closer_than(
                                            15, closest_base.position
                                        )

                                        if minerals_near_base.exists:
                                            drone.gather(minerals_near_base.random)
                                        else:
                                            drone.move(closest_base.position)
                            except (AttributeError, TypeError):
                                pass

                    # 10. Final safety check: If worker is 35.0+ away, assess threat and return if critical
                    if distance_to_base > 35.0:
                        # Assess overall threat level
                        try:
                            known_enemy_units = getattr(self, "enemy_units", None)  # type: ignore[attr-defined]
                            if known_enemy_units and hasattr(known_enemy_units, "closer_than"):
                                enemy_threats = known_enemy_units.closer_than(30, drone.position)
                                threat_count = (
                                    enemy_threats.amount
                                    if hasattr(enemy_threats, "amount")
                                    else len(list(enemy_threats))
                                    if enemy_threats
                                    else 0
                                )

                                if threat_count > 0:
                                    self.drone_threat_detected += 1
                            else:
                                threat_count = 0
                        except (AttributeError, TypeError):
                            threat_count = 0

                        # Only force return if high threat or very far from base
                        if threat_count > 1 or distance_to_base > 50.0:
                            self.drone_escaped_successfully += 1
                            closest_base = self.townhalls.closest_to(drone.position)
                            minerals_near_base = self.mineral_field.closer_than(
                                15, closest_base.position
                            )

                            if minerals_near_base.exists:
                                drone.gather(minerals_near_base.random)
                            else:
                                drone.move(closest_base.position)

                except Exception:
                    pass

        except Exception as e:
            current_iteration = getattr(self, "iteration", 0)
            if current_iteration - getattr(self, "last_error_log_frame", 0) >= 100:
                print(f"[WARNING] Worker safe zone enforcement error: {e}")
                self.last_error_log_frame = current_iteration

    def get_current_build_phase(self) -> str:
        """
        현재 빌드 단계 반환

        Returns:
            str: 현재 빌드 단계 설명
        """
        try:
            if not self.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
                return "Opening (Pre-Pool)"

            if not self.units(UnitTypeId.LAIR).ready.exists:
                if self.units(UnitTypeId.EXTRACTOR).ready.exists:
                    return "Early Game (Pool + Gas)"
                return "Early Game (Pool Ready)"

            if not self.units(UnitTypeId.HIVE).ready.exists:
                if self.units(UnitTypeId.HYDRALISKDEN).ready.exists:
                    return "Mid Game (Lair + Hydra Den)"
                if self.units(UnitTypeId.ROACHWARREN).ready.exists:
                    return "Mid Game (Lair + Roach Warren)"
                return "Mid Game (Lair Tech)"

            if self.units(UnitTypeId.HIVE).ready.exists:
                return "Late Game (Hive Tech)"

            return "Unknown Phase"
        except Exception:
            return "Phase Error"

    def get_memory_usage_level(self) -> str:
        """
        메모리 사용 수준 반환 (간단한 추정)

        Returns:
            str: 메모리 상태 ("OK", "WARNING", "CRITICAL")
        """
        try:


            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb < 500:
                return "OK"
            elif memory_mb < 1000:
                return "WARNING"
            else:
                return "CRITICAL"
        except ImportError:
            return "N/A"
        except Exception:
            return "N/A"

    async def _display_debug_to_chat(self, iteration: int):
        try:
            if not self.townhalls.exists:
                return

            tech_stage = "1단계: Hatchery"
            if self.units(UnitTypeId.LAIR).ready.exists:
                tech_stage = "2단계: Lair"
            if self.units(UnitTypeId.HIVE).ready.exists:
                tech_stage = "3단계: Hive"

            army_units = self.units.filter(lambda u: u.type_id in self.combat_unit_types)
            army_count = (
                army_units.amount if hasattr(army_units, "amount") else len(list(army_units))
            )

            # CRITICAL: Workers should NOT attack - if they are attacking, return them to gathering
            is_worker_defending = False
            try:
                attacking_workers = self.workers.filter(lambda w: w.is_attacking)
                if attacking_workers.exists:
                    # Workers should gather resources, not fight
                    for worker in attacking_workers:
                        try:
                            if self.mineral_field.exists:
                                closest_mineral = self.mineral_field.closest_to(worker.position)
                                if closest_mineral:
                                    await self.do(worker.gather(closest_mineral))
                        except Exception:
                            pass
                    # Workers are being returned to gathering, not defending
                    is_worker_defending = False
            except Exception:
                pass

            supply_left = self.supply_cap - self.supply_used if self.supply_cap > 0 else 0

            drone_count = (
                self.workers.amount if hasattr(self.workers, "amount") else len(list(self.workers))
            )

            defense_status = "!!일꾼 동원 중!!" if is_worker_defending else "정상"
            debug_msg = (
                f"📊 [Status] M:{self.minerals} G:{self.vespene} | "
                f"Supply:{self.supply_used}/{self.supply_cap}({supply_left}) | "
                f"Workers:{drone_count} Army:{army_count} | "
                f"Tech:{tech_stage} | Defense:{defense_status}"
            )

            # Debug chat disabled to prevent spam - use screen debug text instead
            #     if hasattr(self, "personality_manager"):
            #         from personality_manager import ChatPriority
            #         await self.personality_manager.send_chat(debug_msg, priority=ChatPriority.DEBUG)

        except Exception:
            pass

    async def _display_training_monitoring(self, iteration: int):
        """Display training monitoring information"""
        try:
            zerglings = self.units(UnitTypeId.ZERGLING).amount
            roaches = self.units(UnitTypeId.ROACH).amount
            hydralisks = self.units(UnitTypeId.HYDRALISK).amount
            total_army = zerglings + roaches + hydralisks

            if total_army > 0:
                ling_ratio = zerglings / total_army
                roach_ratio = roaches / total_army
                hydra_ratio = hydralisks / total_army

                if self.vespene >= 100:
                    if hydra_ratio + roach_ratio < 0.5:
                        await self.chat_send(
                            f"[Composition] 가스 충분({int(self.vespene)}G) - 히드라/바퀴 비율 낮음 (L{ling_ratio:.0%} R{roach_ratio:.0%} H{hydra_ratio:.0%})"
                        )
                    else:
                        await self.chat_send(
                            f"[Composition] 가스 충분 - 조합 양호 (L{ling_ratio:.0%} R{roach_ratio:.0%} H{hydra_ratio:.0%})"
                        )
                else:
                    if ling_ratio < 0.6:
                        await self.chat_send(
                            f"[Composition] 가스 부족({int(self.vespene)}G) - 저글링 비율 낮음 (L{ling_ratio:.0%} R{roach_ratio:.0%} H{hydra_ratio:.0%})"
                        )

            hatchery_count = self.townhalls.amount
            larva_count = self.units(UnitTypeId.LARVA).amount
            game_time = getattr(self, 'time', 0)  # Use self.time if available

            if game_time >= 300:
                if hatchery_count < 3:
                    await self.chat_send(
                        f"[Larva Supply] 해처리 {hatchery_count}개 - 매크로 해처리 필요!"
                    )
                elif larva_count < 3:
                    await self.chat_send(
                        f"[Larva Supply] 라바 {larva_count}개 부족 - 여왕 인젝트 확인 필요"
                    )
                else:
                    await self.chat_send(
                        f"[Larva Supply] 해처리 {hatchery_count}개, 라바 {larva_count}개 - 양호"
                    )
        except Exception as e:
            # Silent fail - monitoring shouldn't crash the bot
            pass

    async def _express_bot_thoughts(self, iteration: int):
        pass

    async def _execute_scouting(self):
        if self.scout:
            target = self.scout.get_next_scout_target()
            if target:
                overlords = self.units(UnitTypeId.OVERLORD)
                idle_overlords = [u for u in overlords if u.is_idle]
                if idle_overlords:
                    move_command = idle_overlords[0].move(target)
                    if move_command:  # Check if command is not None/False
                        await self.do(move_command)

    async def _morph_overseer(self):
        if not self.intel:
            return
        overlords = [u for u in self.units(UnitTypeId.OVERLORD) if u.is_idle]
        if overlords and self.can_afford(UnitTypeId.OVERSEER):
            lairs = [s for s in self.units(UnitTypeId.LAIR) if s.is_structure]
            hives = [s for s in self.units(UnitTypeId.HIVE) if s.is_structure]
            if (lairs or hives) and overlords:
                await self.do(overlords[0](AbilityId.MORPH_OVERSEER))
                if hasattr(self.intel, "signals"):
                    self.intel.signals["need_overseer"] = False

    async def _check_logic_bugs(self):
        try:
            instance_id = getattr(self, "instance_id", 0)
            instance_tag = f"[ID:{instance_id}]"

            # Check 1: Supply blocked without Overlord training
            if self.supply_left == 0:
                pending_overlords = self.already_pending(UnitTypeId.OVERLORD)
                if pending_overlords == 0:
                    overlords = self.units(UnitTypeId.OVERLORD)
                    if overlords.amount < 5:
                        bug_msg = f"🔴 {instance_tag} [BUG DETECTED] Supply blocked (supply_left=0) without Overlord training"
                        bug_msg += f"\n   Time: {self.time:.2f}s | Overlords: {overlords.amount} | Supply: {self.supply_used}/{self.supply_cap}"
                        bug_msg += f"\n   Minerals: {self.minerals} | Larvae: {self.units(UnitTypeId.LARVA).amount}"
                        print(bug_msg)

                        # Record to debug visualizer if available
                        if hasattr(self, "debug_viz") and self.debug_viz:
                            self.debug_viz.record_event(
                                self.time,
                                "LogicBug",
                                f"Supply blocked (supply_left=0) without Overlord training. Overlords: {overlords.amount}",
                            )

            # Check 2: Can afford unit but not producing
            if self.can_afford(UnitTypeId.ZERGLING) and self.supply_left >= 2:  # type: ignore[operator]
                larvae = self.units(UnitTypeId.LARVA)
                spawning_pools = self.units(UnitTypeId.SPAWNINGPOOL).ready
                if larvae.exists and spawning_pools.exists:
                    pending_zerglings = self.already_pending(UnitTypeId.ZERGLING)
                    if pending_zerglings == 0:
                        zerglings = self.units(UnitTypeId.ZERGLING)
                        if zerglings.amount < 10 and self.time > 60:
                            bug_msg = f"🔴 {instance_tag} [BUG DETECTED] Can afford Zergling but not producing"
                            bug_msg += f"\n   Time: {self.time:.2f}s | Minerals: {self.minerals} | Supply: {self.supply_left}"
                            bug_msg += f"\n   Larvae: {larvae.amount} | Zerglings: {zerglings.amount} | Spawning Pool: Ready"
                            print(bug_msg)

                            # Record to debug visualizer if available
                            if hasattr(self, "debug_viz") and self.debug_viz:
                                self.debug_viz.record_event(
                                    self.time,
                                    "LogicBug",
                                    f"Can afford Zergling but not producing. Larvae: {larvae.amount}, Zerglings: {zerglings.amount}",
                                )

            # Check 3: Queen has energy but not injecting
            # Performance optimization: Cache hatcheries.closer_than result per queen
            queens = self.units(UnitTypeId.QUEEN)
            hatcheries = self.townhalls.ready
            if queens.exists and hatcheries.exists:
                for queen in queens:
                    if queen.energy >= 25:
                        # Cache closer_than result to avoid repeated calculations
                        queen_pos = queen.position
                        nearby_hatcheries = hatcheries.closer_than(5.0, queen_pos)
                        if nearby_hatcheries.exists:
                            for hatch in nearby_hatcheries:
                                try:
                                    inject_buff_id = getattr(
                                        AbilityId,
                                        "QUEENSTACKLAVA_HATCHERYRESEARCH",
                                        None,
                                    )
                                    if inject_buff_id and hasattr(hatch, "has_buff"):
                                        has_inject_buff = hatch.has_buff(inject_buff_id)
                                    else:
                                        has_inject_buff = False
                                except (AttributeError, KeyError, TypeError):
                                    has_inject_buff = False

                                if not has_inject_buff:
                                    bug_msg = f"🔴 {instance_tag} [BUG DETECTED] Queen has energy but not injecting larva"
                                    bug_msg += f"\n   Time: {self.time:.2f}s | Queen Energy: {queen.energy:.0f}"
                                    bug_msg += f"\n   Hatcheries: {hatcheries.amount} | Nearby: {nearby_hatcheries.amount}"
                                    print(bug_msg)

                                    # Record to debug visualizer if available
                                    if hasattr(self, "debug_viz") and self.debug_viz:
                                        self.debug_viz.record_event(
                                            self.time,
                                            "LogicBug",
                                            f"Queen has energy ({queen.energy:.0f}) but not injecting larva",
                                        )
                                    break

            # Check 4: Resources available but no production
            if self.minerals > 500 and self.time > 120:
                idle_hatcheries = self.townhalls.ready.idle
                larvae_count = self.units(UnitTypeId.LARVA).amount
                if idle_hatcheries.exists:
                    bug_msg = f"🔴 {instance_tag} [BUG DETECTED] High minerals but hatcheries idle"
                    bug_msg += f"\n   Time: {self.time:.2f}s | Minerals: {self.minerals} | Vespene: {self.vespene}"
                    bug_msg += f"\n   Supply: {self.supply_used}/{self.supply_cap} (Left: {self.supply_left})"
                    bug_msg += (
                        f"\n   Larvae: {larvae_count} | Idle Hatcheries: {idle_hatcheries.amount}"
                    )
                    print(bug_msg)

                    # Record to debug visualizer if available
                    if hasattr(self, "debug_viz") and self.debug_viz:
                        self.debug_viz.record_event(
                            self.time,
                            "ResourceError",
                            f"High minerals ({self.minerals}) but hatcheries idle. Supply: {self.supply_used}/{self.supply_cap}",
                        )
        except Exception as e:
            # Enhanced error output for bug detection
            instance_id = getattr(self, "instance_id", 0)
            instance_tag = f"[ID:{instance_id}]"
            error_msg = (
                f"🔴 {instance_tag} [ERROR] Bug detection failed: {type(e).__name__}: {str(e)}"
            )
            print(error_msg)
            print(f"   Traceback: {traceback.format_exc()}")

            # Record to debug visualizer if available
            if hasattr(self, "debug_viz") and self.debug_viz:
                self.debug_viz.record_event(
                    self.time, type(e).__name__, f"Error in _check_logic_bugs: {str(e)}"
                )

    async def _log_game_state(self):
        try:
            self.telemetry_logger.log_game_state(self.combat_unit_types)
        except Exception:
            pass

    def write_log(self, message: str, level: str = "INFO", filter_key: Optional[str] = None):
        if not self.log_file or not self.log_enabled:
            return

        # Check if log level is enabled
        if level not in self.log_levels:
            return

        # Check filter if provided
        if filter_key and filter_key in self.log_filters:
            if not self.log_filters[filter_key]:
                return

        try:
            # Check log file size and rotate if needed
            if os.path.exists(self.log_file):
                file_size_mb = os.path.getsize(self.log_file) / (1024 * 1024)
                if file_size_mb > self.log_max_size_mb:
                    # Rotate log file
                    old_log = self.log_file.replace(".txt", f"_old_{int(time.time())}.txt")
                    os.rename(self.log_file, old_log)
                    # Create new log file
                    with open(self.log_file, "w", encoding="utf-8") as f:
                        f.write(f"=== Log File Rotated ===\n")
                        f.write(f"Previous file: {os.path.basename(old_log)}\n")
                        f.write(f"{'=' * 50}\n\n")

            timestamp = datetime.now().strftime("%H:%M:%S")
            log_line = f"[{timestamp}] [{level}] {message}\n"

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            # Silently fail if logging fails (don't crash the bot)
            if self.iteration - self.last_log_iteration >= 500:
                print(f"[WARNING] Log write failed: {e}")
                self.last_log_iteration = self.iteration

    def write_log_with_traceback(self, message: str, exception: Exception, level: str = "ERROR"):
        """
        Write log message with full traceback

        Args:
            message: Log message
            exception: Exception object
            level: Log level (default: ERROR)
        """
        if not self.log_filters.get("error_traceback", True):
            # If traceback logging is disabled, just log the message
            self.write_log(f"{message}: {str(exception)}", level)
            return

        try:
            tb_str = traceback.format_exc()
            full_message = f"{message}\nException: {type(exception).__name__}: {str(exception)}\nTraceback:\n{tb_str}"
            self.write_log(full_message, level)
        except Exception:
            # Fallback to simple logging
            self.write_log(f"{message}: {str(exception)}", level)

    async def _detect_unit_deaths(self):
        if not self.log_filters.get("unit_death", True):
            return

        try:
            # Get current army unit tags
            current_tags = set()
            current_army_count = 0

            for unit in self.units:
                if unit.can_attack and hasattr(unit, "tag"):
                    current_tags.add(unit.tag)
                    current_army_count += 1

            # Compare with previous frame
            if self.previous_unit_tags:
                dead_tags = self.previous_unit_tags - current_tags
                if dead_tags:
                    dead_count = len(dead_tags)
                    army_loss = self.previous_army_count - current_army_count

                    if army_loss > 0:
                        self.write_log(
                            f"Unit deaths detected: {dead_count} units lost, Army: {self.previous_army_count} -> {current_army_count}",
                            "WARNING",
                            filter_key="unit_death",
                        )

            # Update for next frame
            self.previous_unit_tags = current_tags
            self.previous_army_count = current_army_count

        except Exception:
            # Silently fail - don't crash the bot
            pass

    async def _save_telemetry(self):
        """
        Save telemetry data to JSON file for analysis - TelemetryLogger로 위임
        """
        try:
            await self.telemetry_logger.save_telemetry()
        except Exception as e:
            print(f"[WARNING] Telemetry save error: {e}")

    async def _build_army_aggressive(self):
        """
        Aggressive army production with reactive composition logic

        Reactive Composition Logic:
        - Determines ideal composition based on enemy tech detection
        - Adjusts unit ratios to counter enemy strategy
        - Falls back to resource-based ratios if enemy tech unknown

        This prevents resource accumulation and ensures army is always growing.
        """
        if self.production_resilience:
            return await self.production_resilience.build_army_aggressive()

        if not self.units(UnitTypeId.LARVA).exists:
            return

        larvae = self.units(UnitTypeId.LARVA).ready

        # NOTE: Overlord production removed and delegated to ProductionManager._produce_overlord()
        # Previously: supply_left < 5 check caused duplication
        # ProductionManager now handles all overlord production with predictive logic
        # This function focuses on combat unit composition only

        if hasattr(self, "current_build_plan") and "ideal_composition" in self.current_build_plan:
            ideal_comp = self.current_build_plan["ideal_composition"]
        else:
            ideal_comp = await self._determine_ideal_composition()
            if not hasattr(self, "current_build_plan"):
                self.current_build_plan = {}
            self.current_build_plan["ideal_composition"] = ideal_comp

        zerglings = self.units(UnitTypeId.ZERGLING).amount
        roaches = self.units(UnitTypeId.ROACH).amount
        hydralisks = self.units(UnitTypeId.HYDRALISK).amount
        banelings = self.units(UnitTypeId.BANELING).amount
        ravagers = self.units(UnitTypeId.RAVAGER).amount
        total_army = zerglings + roaches + hydralisks + banelings + ravagers

        unit_to_produce = None

        if total_army == 0:
            if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists and self.can_afford(
                UnitTypeId.ZERGLING
            ):
                unit_to_produce = UnitTypeId.ZERGLING
        else:
            target_hydra = ideal_comp.get(UnitTypeId.HYDRALISK, 0.0)
            target_roach = ideal_comp.get(UnitTypeId.ROACH, 0.0)
            target_ling = ideal_comp.get(UnitTypeId.ZERGLING, 0.0)
            target_baneling = ideal_comp.get(UnitTypeId.BANELING, 0.0)
            target_ravager = ideal_comp.get(UnitTypeId.RAVAGER, 0.0)

            current_hydra = hydralisks / total_army if total_army > 0 else 0
            current_roach = roaches / total_army if total_army > 0 else 0
            current_ling = zerglings / total_army if total_army > 0 else 0
            current_baneling = banelings / total_army if total_army > 0 else 0
            current_ravager = ravagers / total_army if total_army > 0 else 0

            deficits = {
                UnitTypeId.HYDRALISK: target_hydra - current_hydra,
                UnitTypeId.ROACH: target_roach - current_roach,
                UnitTypeId.ZERGLING: target_ling - current_ling,
                UnitTypeId.BANELING: target_baneling - current_baneling,
                UnitTypeId.RAVAGER: target_ravager - current_ravager,
            }

            max_deficit_unit = max(deficits.items(), key=lambda x: x[1])[0]
            max_deficit = deficits[max_deficit_unit]

            if max_deficit > 0:
                if max_deficit_unit == UnitTypeId.HYDRALISK:
                    if self.units(UnitTypeId.HYDRALISKDEN).ready.exists and self.can_afford(
                        UnitTypeId.HYDRALISK
                    ):
                        unit_to_produce = UnitTypeId.HYDRALISK
                elif max_deficit_unit == UnitTypeId.ROACH:
                    if self.units(UnitTypeId.ROACHWARREN).ready.exists and self.can_afford(
                        UnitTypeId.ROACH
                    ):
                        unit_to_produce = UnitTypeId.ROACH
                elif max_deficit_unit == UnitTypeId.RAVAGER:
                    roaches_ready = self.units(UnitTypeId.ROACH).ready
                    if roaches_ready.exists and self.can_afford(AbilityId.MORPHTORAVAGER_RAVAGER):
                        try:
                            roaches_ready.random(AbilityId.MORPHTORAVAGER_RAVAGER)
                            return  # Ravager morphing started
                        except Exception:
                            pass
                elif max_deficit_unit == UnitTypeId.BANELING:
                    zerglings_ready = self.units(UnitTypeId.ZERGLING).ready
                    if zerglings_ready.exists and self.units(UnitTypeId.BANELINGNEST).ready.exists:
                        if self.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                            try:
                                zerglings_ready.random(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                return  # Baneling morphing started
                            except Exception:
                                pass
                elif max_deficit_unit == UnitTypeId.ZERGLING:
                    if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists and self.can_afford(
                        UnitTypeId.ZERGLING
                    ):
                        unit_to_produce = UnitTypeId.ZERGLING

                if not unit_to_produce:
                    if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists and self.can_afford(
                        UnitTypeId.ZERGLING
                    ):
                        unit_to_produce = UnitTypeId.ZERGLING

        # FIX: Use list iteration instead of random to avoid conflicts
        if unit_to_produce and larvae.exists and self.supply_left >= 2:
            try:
                larvae_list = list(larvae)
                if larvae_list:
                    for larva in larvae_list:
                        if larva.is_ready:
                            await larva.train(unit_to_produce)
                            break
            except Exception as e:
                pass
        elif unit_to_produce:
            pass

    # 💰 FORCE RESOURCE DUMP: Consume excess minerals when > 1000
    async def _force_resource_dump(self):
        """
        Force resource consumption when minerals exceed 1000

        This prevents resource accumulation by:
        1. Building macro hatcheries to increase larva production
        2. Mass producing zerglings with all available larvae
        """
        if self.production_resilience:
            return await self.production_resilience.force_resource_dump()
        # type: ignore[operator] suppresses can_afford wrapper warnings
        if self.can_afford(UnitTypeId.HATCHERY) and self.already_pending(UnitTypeId.HATCHERY) < 2:  # type: ignore[operator]
            try:
                await self.expand_now()
            except Exception:
                pass

        if self.units(UnitTypeId.LARVA).exists:
            larvae = self.units(UnitTypeId.LARVA).ready
            if larvae.exists and self.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
                for larva in larvae:
                    # type: ignore[operator] suppresses can_afford wrapper warnings
                    if self.can_afford(UnitTypeId.ZERGLING) and self.supply_left >= 2:  # type: ignore[operator]
                        try:
                            await larva.train(UnitTypeId.ZERGLING)
                        except Exception:
                            continue

    async def _panic_mode_production(self):
        """
        패닉 모드 생산: 저글링, 여왕, 가시촉수만 생산

        날빌 방어 중에는 경제 활동을 중단하고 수비 유닛만 생산합니다.
        """
        if self.production_resilience:
            return await self.production_resilience.panic_mode_production()
        if self.production:
            await self.production._produce_overlord()

        if self.production:
            await self.production._produce_queen()

        larvae = list(self.units(UnitTypeId.LARVA))
        if larvae and self.supply_left >= 2:
            if self.can_afford(UnitTypeId.ZERGLING):
                spawning_pools = self.units(UnitTypeId.SPAWNINGPOOL).ready
                if spawning_pools:
                    await random.choice(larvae).train(UnitTypeId.ZERGLING)

    async def _build_terran_counters(self):
        """
        vs 테란 상성 빌드: 맹독충/뮤탈 위주

        테란 바이오닉 상대: 맹독충 필수
        테란 메카닉 상대: 로치/궤멸충
        """
        if self.production_resilience:
            return await self.production_resilience.build_terran_counters()
        if not self.production:
            return

        baneling_nest_exists_or_pending = (
            self.structures(UnitTypeId.BANELINGNEST).exists
            or self.already_pending(UnitTypeId.BANELINGNEST) > 0
        )
        if not baneling_nest_exists_or_pending and self.can_afford(UnitTypeId.BANELINGNEST):
            # CRITICAL: Additional duplicate check before building
            if not self.structures(UnitTypeId.BANELINGNEST).exists:
                spawning_pools = [
                    s for s in self.units(UnitTypeId.SPAWNINGPOOL).structure if s.is_ready
                ]
                if spawning_pools:
                    await self.build(UnitTypeId.BANELINGNEST, near=spawning_pools[0])

    async def _build_protoss_counters(self):
        """
        vs 프로토스 상성 빌드: 히드라/가시지옥 위주

        스카이토스 상대: 히드라/커럽터
        지상군 상대: 로치/궤멸충
        """
        if self.production_resilience:
            return await self.production_resilience.build_protoss_counters()
        if not self.production:
            return

    async def _build_zerg_counters(self):
        """
        vs 저그 상성 빌드: 바퀴/궤멸충 위주

        저저전: 로치 싸움이 핵심
        뮤탈 상대: 히드라
        """
        if self.production_resilience:
            return await self.production_resilience.build_zerg_counters()
        if not self.production:
            return

    async def _display_bot_status_to_chat(self, iteration: int):
        """
        Display bot status via chat with real-time economic and combat mode info

        Shows key information via chat including:
        - Persona name
        - Worker count and Minerals
        - Economic status (PRIORITY ZERO, SAVING FOR DRONE, ECONOMY STABLE)
        - Combat Mode (DEFENSIVE, CAUTIOUS, AGGRESSIVE)

        Args:
            iteration: Current game iteration/frame
        """
        # strategy_engine removed: status display functionality deprecated
        pass

    async def _send_status_to_chat(self):
        """
        Send bot status to in-game chat

        Displays key information in the game chat window for easy monitoring.
        """
        # strategy_engine removed: status display functionality deprecated
        pass

    async def _send_game_progress_to_chat(self):
        """
        Real-time game progress chat notification (called every 5 seconds)

        Displays build stage, supply, resources, and enemy tech information in chat
        for easier debugging and strategy analysis.
        """
        # strategy_engine removed: game progress display functionality deprecated
        pass

    async def _calculate_and_display_win_probability(self):
        pass

    def _print_status(self):
        instance_id = getattr(self, "instance_id", 0)
        instance_tag = f"[ID:{instance_id}]"
        strategy_str = "UNKNOWN"
        threat_str = "UNKNOWN"
        if self.intel:
            try:
                strategy_mode = getattr(self.intel, "strategy_mode", None)
                if strategy_mode and hasattr(strategy_mode, "name"):
                    strategy_str = strategy_mode.name
                threat_level = getattr(self.intel, "threat_level", None)
                if threat_level and hasattr(threat_level, "name"):
                    threat_str = threat_level.name
            except (AttributeError, TypeError):
                pass
        print(f"\n{instance_tag} [{int(self.time)}초] 🧠 전략: {strategy_str} | 위협: {threat_str}")
        workers_count = (
            self.workers.amount if hasattr(self.workers, "amount") else self.workers.amount
        )
        coverage = 0.0
        if self.scout and hasattr(self.scout, "get_coverage_percent"):
            try:
                coverage = self.scout.get_coverage_percent() if self.scout else 0.0
            except Exception:
                pass
        print(
            f"{instance_tag} 💎 미네랄: {self.minerals} | 👷 일꾼: {workers_count} | 🗺️ 탐색률: {coverage:.1f}%"
        )

    def save_model_safe(self):
        """
        저장 경로를 확인하고 모델 파일을 물리적으로 저장합니다.
        인스턴스별 별도 파일로 저장하여 병렬 실행 시 충돌을 방지합니다.
        """
        if not self.use_neural_network or self.neural_network is None:
            return

        if torch is None:
            print("[WARNING] PyTorch가 없어 모델을 저장할 수 없습니다.")
            return

        try:

            os.makedirs(MODELS_DIR, exist_ok=True)

            save_path = os.path.join(MODELS_DIR, self.model_filename)

            torch.save(self.neural_network.model.state_dict(), save_path)

            print(f"💾 [저장 완료] 모델이 {save_path}에 저장되었습니다.")
            if hasattr(self, "instance_id"):
                print(f"💾 [Instance #{self.instance_id}] Model saved")
        except Exception as e:
            print(f"❌ 모델 저장 중 오류 발생: {e}")
            traceback.print_exc()

    def _collect_state(self) -> np.ndarray:
        """
        현재 게임 상태 수집 (신경망 입력용)

        IMPROVED: Enhanced state vector with enemy intelligence
        - Added enemy unit count and tech level information
        - Uses IntelManager for comprehensive game state

        Input State Vector (10-dimensional):
            Self (5):
            - Minerals (미네랄)
            - Vespene Gas (가스)
            - Supply Used (공급량 사용)
            - Drone Count (드론 수)
            - Army Count (병력 수)
            Enemy (5):
            - Enemy Army Count (적 병력 수)
            - Enemy Tech Level (적 테크 수준: 0=기본, 1=중급, 2=고급)
            - Enemy Threat Level (적 위협도: 0-4)
            - Enemy Unit Diversity (적 유닛 다양성: 0-1)
            - Scout Coverage (정찰 범위: 0-1)

        Returns:
            np.ndarray: 상태 배열 [self_info(5), enemy_info(5)]
        """
        try:
            # CPU optimization: Cache frequently accessed values to reduce repeated queries
            # This reduces CPU load and allows GPU to process more efficiently

            minerals = float(self.minerals)
            vespene = float(self.vespene)

            supply_used = float(self.supply_used)

            if hasattr(self, "_cached_worker_count"):
                # Use cached value if available (updated periodically)
                drone_count = float(self._cached_worker_count)
            else:
                drone_count = float(
                    self.workers.amount
                    if hasattr(self.workers, "amount")
                    else len(list(self.workers))
                )
                self._cached_worker_count = drone_count

            if hasattr(self, "_cached_army_count"):
                # Use cached value if available (updated periodically)
                army_count = float(self._cached_army_count)
            else:
                # CRITICAL: Use whitelist approach - only Zergling+ combat units
                army_units = self.units.filter(lambda u: u.type_id in self.combat_unit_types)
                army_count = float(
                    army_units.amount if hasattr(army_units, "amount") else len(list(army_units))
                )
                self._cached_army_count = army_count

            # IMPROVED: Enhanced enemy intelligence from IntelManager (15-dimensional state)
            # Self (5): Minerals, Gas, Supply, Workers, Army
            # Enemy (10): Comprehensive enemy information for better decision making
            enemy_army_count = 0.0
            enemy_tech_level = 0.0
            enemy_threat_level = 0.0
            enemy_unit_diversity = 0.0
            scout_coverage = 0.0
            enemy_main_distance = 0.0  # Distance to enemy main base
            enemy_expansion_count = 0.0  # Number of enemy expansions
            enemy_resource_estimate = 0.0  # Estimated enemy resources (minerals + gas)
            enemy_upgrade_count = 0.0  # Number of detected enemy upgrades
            enemy_air_ground_ratio = 0.0  # Air units / (Air + Ground) ratio

            if hasattr(self, "intel_manager") and self.intel_manager:
                intel = self.intel_manager

                # Enemy army count (sum of all enemy combat units)
                if hasattr(self, "enemy_units") and self.enemy_units:
                    enemy_army_count = float(len(list(self.enemy_units)))
                else:
                    enemy_army_count = float(sum(intel.enemy_unit_count.values()) if intel.enemy_unit_count else 0)

                # Enemy tech level (0=basic, 1=intermediate, 2=advanced)
                tech_units = len(intel.enemy_tech_units) if intel.enemy_tech_units else 0
                if tech_units >= 5:
                    enemy_tech_level = 2.0
                elif tech_units >= 2:
                    enemy_tech_level = 1.0
                else:
                    enemy_tech_level = 0.0

                # Enemy threat level (0-4 scale)
                threat = intel.get_threat_level()
                enemy_threat_level = float(threat.value if hasattr(threat, 'value') else 0)

                # Enemy unit diversity (number of unique unit types / 10, capped at 1.0)
                unique_enemy_types = len(intel.enemy_unit_count) if intel.enemy_unit_count else 0
                enemy_unit_diversity = min(1.0, float(unique_enemy_types) / 10.0)

                # Scout coverage (0-1 scale)
                scout_coverage = float(intel.get_scout_coverage() / 100.0) if intel.get_scout_coverage() else 0.0

                # NEW: Enemy main base distance (normalized to 0-1, max distance ~200)
                if intel.enemy_main_location and hasattr(self, 'start_location'):
                    try:
                        enemy_main_pos = Point2(intel.enemy_main_location)
                        distance = self.start_location.distance_to(enemy_main_pos)
                        enemy_main_distance = min(1.0, float(distance) / 200.0)  # Normalize to 0-1
                    except Exception:
                        enemy_main_distance = 0.0

                # NEW: Enemy expansion count (number of detected expansions)
                enemy_expansion_count = float(len(intel.enemy_expansion_locations) if intel.enemy_expansion_locations else 0)
                enemy_expansion_count = min(5.0, enemy_expansion_count) / 5.0  # Normalize to 0-1 (max 5 expansions)

                # NEW: Estimated enemy resources (minerals + gas, normalized)
                estimated_total = (intel.estimated_enemy_minerals or 0.0) + (intel.estimated_enemy_vespene or 0.0)
                enemy_resource_estimate = min(1.0, float(estimated_total) / 4000.0)  # Normalize to 0-1 (max 4000)

                # NEW: Enemy upgrade count (number of detected upgrades)
                enemy_upgrade_count = float(len(intel.enemy_upgrades_detected) if intel.enemy_upgrades_detected else 0)
                enemy_upgrade_count = min(1.0, enemy_upgrade_count / 10.0)  # Normalize to 0-1 (max 10 upgrades)

                # NEW: Enemy air/ground ratio (air units / total units)
                # Use actual enemy_units if available for accurate detection
                if hasattr(self, "enemy_units") and self.enemy_units:
                    try:
                        air_units = 0
                        total_enemy_units = 0
                        for enemy in self.enemy_units:
                            total_enemy_units += 1
                            if hasattr(enemy, 'is_flying') and enemy.is_flying:
                                air_units += 1
                        enemy_air_ground_ratio = float(air_units) / float(total_enemy_units) if total_enemy_units > 0 else 0.0
                    except Exception:
                        enemy_air_ground_ratio = 0.0
                elif intel.enemy_unit_count:
                    # Fallback: Estimate from unit counts using UnitTypeId (more accurate)
                    try:
                        # Common air unit type IDs
                        air_unit_types = {
                            UnitTypeId.MUTALISK, UnitTypeId.CORRUPTOR, UnitTypeId.BROODLORD,
                            UnitTypeId.VOIDRAY, UnitTypeId.PHOENIX, UnitTypeId.CARRIER,
                            UnitTypeId.BATTLECRUISER, UnitTypeId.LIBERATOR, UnitTypeId.BANSHEE,
                            UnitTypeId.MEDIVAC, UnitTypeId.VIKING, UnitTypeId.RAVEN,
                            UnitTypeId.OVERLORD, UnitTypeId.OVERSEER
                        }
                        air_units = 0
                        total_enemy_units = sum(intel.enemy_unit_count.values())
                        if total_enemy_units > 0:
                            for unit_type, count in intel.enemy_unit_count.items():
                                if unit_type in air_unit_types:
                                    air_units += count
                            enemy_air_ground_ratio = float(air_units) / float(total_enemy_units)
                        else:
                            enemy_air_ground_ratio = 0.0
                    except Exception:
                        enemy_air_ground_ratio = 0.0
                else:
                    enemy_air_ground_ratio = 0.0

            # This expanded state vector allows the AI to learn context-aware strategies
            # like "Baneling drop timing" based on enemy position, tech, and resources
            state = np.array(
                [
                    # Self (5)
                    minerals, vespene, supply_used, drone_count, army_count,
                    # Enemy (10)
                    enemy_army_count, enemy_tech_level, enemy_threat_level,
                    enemy_unit_diversity, scout_coverage,
                    enemy_main_distance, enemy_expansion_count, enemy_resource_estimate,
                    enemy_upgrade_count, enemy_air_ground_ratio
                ],
                dtype=np.float32,
            )

            return state

        except Exception as e:
            print(f"[WARNING] _collect_state 오류: {e}")
            return np.array([0.0] * 15, dtype=np.float32)

    def choose_action(self, state=None):
        """
        에필론-그리디 전략에 따른 행동 선택

        Args:
            state: 게임 상태 (numpy array 또는 list). None이면 자동으로 수집

        Returns:
            Action: 선택된 행동
        """
        if state is None:
            state = self._collect_state()
        if not self.use_neural_network or self.neural_network is None:
            return Action.ECONOMY if Action else None



        available_actions = list(Action) if Action else []

        if not available_actions:
            return None

        if self.train_mode and random.random() < self.epsilon:
            return random.choice(available_actions)
        else:
            # This limits GPU usage to ~30% while maintaining good performance
            current_iteration = getattr(self, "iteration", 0)
            last_inference = getattr(self, "last_neural_network_inference", -1)
            inference_interval = getattr(self, "neural_network_inference_interval", 24)

            if current_iteration - last_inference < inference_interval:
                if hasattr(self, "_cached_neural_action"):
                    return self._cached_neural_action
                else:
                    return Action.ECONOMY if Action else random.choice(available_actions)

            try:
                if not isinstance(state, np.ndarray):
                    state = np.array(state, dtype=np.float32)

                action, _ = self.neural_network.select_action(state)

                self._cached_neural_action = action
                self.last_neural_network_inference = current_iteration

                return action
            except Exception as e:
                print(f"[WARNING] choose_action 신경망 오류: {e}")
                return random.choice(available_actions)

    async def _autonomous_personality_chat(self):
        """
        자율적 성격 시스템: 봇이 스스로 감정을 채팅으로 표현 + 시각적 효과

        실시간 의사결정 노출 시스템:
        1. 승률 기반 감정 및 성격 판단
        2. 자원 상황, 테크 상태, 전투 상황 종합 분석
        3. 감정에 따른 시각적 효과 (색상 원 그리기)

        초기화 실패를 방지하기 위해 안전하게 감싸진 구조로,
        봇이 현재 게임 상황을 분석하여 자신의 감정 상태를 표현합니다.
        """
        try:
            win_rate = getattr(self, "current_win_rate", 50.0)

            if hasattr(self, "units") and hasattr(self, "enemy_units"):
                our_supply = self.supply_used if hasattr(self, "supply_used") else 0
                enemy_units = getattr(self, "enemy_units", None)
                enemy_supply = 0
                if enemy_units and hasattr(enemy_units, "amount"):
                    enemy_supply = enemy_units.amount * 1.0  # Rough estimate
                elif enemy_units:
                    try:
                        enemy_supply = len(list(enemy_units)) * 1.0
                    except:
                        pass

                if our_supply > 0 and enemy_supply > 0:
                    supply_ratio = our_supply / (our_supply + enemy_supply)
                    win_rate = supply_ratio * 100.0
                elif our_supply > enemy_supply * 1.5:
                    win_rate = 65.0
                elif enemy_supply > our_supply * 1.5:
                    win_rate = 35.0

            thought_process = ""
            visual_color = (255, 255, 255)  # Default white
            visual_radius = 3.0  # Default radius

            if not self.units(UnitTypeId.SPAWNINGPOOL).exists:
                thought_process += f"💡 [생각] 현재 미네랄 {self.minerals}... 산란못이 없으면 위험하니 자원을 아끼는 중입니다. "
                visual_color = (255, 255, 0)  # Yellow (caution)
                visual_radius = 2.5

            if self.minerals < 50:
                thought_process += f"💰 [자원 분석] 자원이 부족해 테크 건물이 늦어지고 있습니다. 채취에 집중할게요. "
                visual_color = (255, 165, 0)  # Orange (resource concern)
                visual_radius = 2.0

            if hasattr(self, "intel") and self.intel:
                try:
                    if hasattr(self.intel, "should_defend") and callable(self.intel.should_defend):
                        if self.intel.should_defend():
                            thought_process += f"🛡️ [전략 판단] 적의 화력이 너무 강력합니다. 본진 근처 가시 촉수 쪽으로 유인하겠습니다. "
                            visual_color = (0, 0, 255)  # Blue (defensive)
                            visual_radius = 4.0
                except Exception:
                    pass

            worker_count = (
                self.workers.amount if hasattr(self.workers, "amount") else len(list(self.workers))
            )
            if worker_count < 12:
                thought_process += (
                    f"🏠 [일꾼 관리] 일꾼 수가 부족합니다. 안전한 본진 자원 지대로 집중하겠습니다. "
                )
                visual_color = (255, 0, 0)  # Red (critical)
                visual_radius = 3.5

            if win_rate < 45.0:
                mood = "신중함(Cautious)"
                msg = f"🛡️ [감정: 신중함] 승률 {win_rate:.1f}%... 지금은 병력을 보존할 때입니다."
                visual_color = (0, 100, 255)  # Light blue (cautious)
                visual_radius = 3.0
            elif win_rate > 55.0:
                mood = "공격적(Aggressive)"
                msg = f"🔥 [감정: 공격적] 승률 {win_rate:.1f}%! 전 병력에게 진격 명령을 내릴지 고민 중입니다."
                visual_color = (255, 0, 0)  # Red (aggressive)
                visual_radius = 5.0
            else:
                mood = "평온함(Calm)"
                msg = f"✨ [감정: 평온함] 승률 {win_rate:.1f}%. 안정적으로 자원을 확보하며 다음 단계를 구상 중입니다."
                visual_color = (0, 255, 0)  # Green (calm)
                visual_radius = 3.5

            last_win_rate = getattr(self, "last_calculated_win_rate", win_rate)
            if abs(win_rate - last_win_rate) > 10.0:
                thought_process += f"📊 [상태 변화] 승률이 {last_win_rate:.1f}%에서 {win_rate:.1f}%로 변화했습니다. "
                if win_rate > last_win_rate:
                    thought_process += "이제부터 조금 더 공격적으로 임하겠습니다. "
                else:
                    thought_process += "상황을 재평가하여 신중하게 접근하겠습니다. "

            self.last_calculated_win_rate = win_rate

            try:
                if thought_process:
                    chat_msg = f"{thought_process}{msg}"
                else:
                    chat_msg = f"💬 [{mood}] {msg}"
                await self.chat_send(chat_msg)
            except (ValueError, OSError, RuntimeError) as chat_error:
                # Log buffer detached or other I/O errors - silently fail
                if "buffer" in str(chat_error).lower() or "detached" in str(chat_error).lower():
                    # Don't spam errors for buffer issues
                    pass
                else:
                    # Other errors - log but don't crash
                    if getattr(self, "iteration", 0) % 100 == 0:
                        print(f"[WARNING] Chat send failed: {chat_error}")
            except Exception as chat_error:
                # Any other error - silently fail to prevent game crash
                pass

            try:
                if hasattr(self, "client") and self.client and self.townhalls.exists:
                    color_emoji = ""
                    if win_rate < 45.0:
                        color_emoji = "🔵"  # Blue (cautious)
                    elif win_rate > 55.0:
                        color_emoji = "🔴"  # Red (aggressive)
                    else:
                        color_emoji = "🟢"  # Green (calm)

                    visual_msg = f"{color_emoji} [Visual] Emotion circle: {mood} (Radius: {visual_radius:.1f}, Color: {visual_color})"
                    await self.chat_send(visual_msg)
            except Exception:
                pass

        except Exception as e:
            # Silent fail - personality chat should never crash initialization
            pass

    async def _broadcast_internal_thoughts(self):
        """
        실시간 내면적 판단 근거 노출 시스템

        봇이 강제적인 명령을 수행하는 대신, 현재의 자원 상황, 승률, 감정 상태를
        종합하여 스스로의 생각을 텍스트로 전환해 채팅창에 띄우는 통합 로직입니다.

        판단 근거:
        1. 자원 상황 분석 (미네랄/가스 부족 여부)
        2. 테크 상태 평가 (산란못, 레어, 하이브)
        3. 전투 상황 판단 (승산 없는 전투 회피 원칙)
        4. 일꾼 관리 판단 (안전 복귀 결정)
        """
        try:
            if not self.townhalls.exists:
                return

            thought_process = ""
            visual_color = (255, 255, 255)  # Default white
            visual_radius = 3.0

            if not self.units(UnitTypeId.SPAWNINGPOOL).exists:
                thought_process = f"💡 [생각] 현재 미네랄 {self.minerals}... 산란못이 없으면 위험하니 자원을 아끼는 중입니다."
                visual_color = (255, 255, 0)  # Yellow (caution)
                visual_radius = 2.5

            elif self.minerals < 50:
                thought_process = f"💰 [자원 분석] 자원이 부족해 테크 건물이 늦어지고 있습니다. 채취에 집중할게요."
                visual_color = (255, 165, 0)  # Orange (resource concern)
                visual_radius = 2.0

            win_rate = getattr(self, "current_win_rate", 50.0)
            if win_rate < 45.0:
                thought_process += (
                    f" 🛡️ [감정: 신중함] 승률 {win_rate:.1f}%... 지금은 병력을 보존할 때입니다."
                )
                visual_color = (0, 100, 255)  # Light blue (cautious)
                visual_radius = 3.0
            elif win_rate > 55.0:
                thought_process += f" 🔥 [감정: 공격적] 승률 {win_rate:.1f}%! 전 병력에게 진격 명령을 내릴지 고민 중입니다."
                visual_color = (255, 0, 0)  # Red (aggressive)
                visual_radius = 5.0

            worker_count = (
                self.workers.amount if hasattr(self.workers, "amount") else len(list(self.workers))
            )
            if worker_count < 12:
                thought_process += (
                    f" 🏠 [일꾼 관리] 일꾼 수가 부족합니다. 안전한 본진 자원 지대로 집중하겠습니다."
                )
                visual_color = (255, 0, 0)  # Red (critical)
                visual_radius = 3.5

            if hasattr(self, "intel") and self.intel:
                try:
                    if hasattr(self.intel, "should_defend") and callable(self.intel.should_defend):
                        if self.intel.should_defend():
                            thought_process += f" 🛡️ [전략 판단] 적의 화력이 너무 강력합니다. 본진 근처 가시 촉수 쪽으로 유인하겠습니다."
                            visual_color = (0, 0, 255)  # Blue (defensive)
                            visual_radius = 4.0
                except Exception:
                    pass

            if thought_process:
                await self.chat_send(thought_process)

                try:
                    color_emoji = ""
                    if win_rate < 45.0:
                        color_emoji = "🔵"  # Blue (cautious)
                    elif win_rate > 55.0:
                        color_emoji = "🔴"  # Red (aggressive)
                    else:
                        color_emoji = "🟢"  # Green (calm)

                    visual_info = f"{color_emoji} [Visual] Emotion circle: Radius {visual_radius:.1f}, Color RGB{visual_color}"
                    await self.chat_send(visual_info)
                except Exception:
                    pass

        except Exception:
            # Silent fail - internal thoughts broadcast should never crash initialization
            pass

    async def on_chat(self, chat_message):
        """
        채팅 메시지 처리 - PersonalityManager에 위임

        Args:
            chat_message: ChatMessage 객체 (message, is_from_self 속성 포함)
        """
        try:
            is_gg = await self.personality_manager.process_chat_message(chat_message)

            if is_gg:
                instance_id = getattr(self, "instance_id", 0)
                instance_tag = f"[ID:{instance_id}]"
                print(f"{instance_tag} ✅ 게임 종료 중...")

                # Set game ended flag
                self.game_ended = True

                # Send single acknowledgement chat
                if not getattr(self, "_gg_ack_sent", False):
                    try:
                        await self.chat_send("gg wp")
                    except Exception:
                        pass
                    self._gg_ack_sent = True

                # Leave game immediately
                try:
                    if hasattr(self, "client") and self.client:
                        await self.client.leave_game()  # type: ignore
                except Exception as e:
                    print(f"{instance_tag} [WARNING] Failed to leave game: {e}")

        except Exception as e:
            # Silently fail if chat processing fails
            if hasattr(self, "iteration") and self.iteration % 100 == 0:
                print(f"[WARNING] Chat processing error: {e}")

    async def on_unit_destroyed(self, unit_tag):
        """
        유닛 파괴 이벤트 핸들러
        드론이 적에게 죽으면 카운터를 증가시킵니다.
        """
        try:
            # Track drone losses
            if hasattr(self, "last_drone_count"):
                current_drones = self.units(UnitTypeId.DRONE).amount
                if current_drones < self.last_drone_count:
                    self.drone_losses_to_enemy += 1
                    if self.drone_losses_to_enemy % 3 == 0:
                        print(f"💀 [드론 손실] 적에게 {self.drone_losses_to_enemy}기 손실")
                self.last_drone_count = current_drones
        except Exception:
            pass

    async def on_end(self, game_result):
        """Game end - calculate learning reward and log"""
        # Ensure game_ended flag is set to prevent any further on_step execution
        self.game_ended = True

        try:
            # Result.Victory is returned when the opponent surrenders or is defeated
            if str(game_result) == "Victory":
                print("[VICTORY] Opponent surrendered or defeated! Closing game...")

            # Explicitly leave game to avoid hanging sessions
            if hasattr(self, "client") and self.client:
                try:
                    if hasattr(self.client, "leave_game"):
                        await self.client.leave_game()  # type: ignore
                    else:
                        await self.client.leave()  # type: ignore
                    print("[GAME] Successfully left game session")
                except Exception as leave_error:
                    print(f"[WARNING] Failed to leave game cleanly: {leave_error}")
        except Exception as end_error:
            print(f"[WARNING] Error during game end handling: {end_error}")

        async def _async_retry(
            coro_factory, description: str, retries: int = 3, delay: float = 1.0
        ):
            """Retry an async save/report operation to avoid data loss."""
            for attempt in range(retries):
                try:
                    await coro_factory()
                    return True
                except Exception as err:
                    if attempt < retries - 1:
                        await asyncio.sleep(delay)
                        continue
                    print(f"[CRITICAL] Failed to {description} after {retries} attempts: {err}")
            return False

        def _retry(func, description: str, retries: int = 3, delay: float = 1.0):
            for attempt in range(retries):
                try:
                    func()
                    return True
                except Exception as err:
                    if attempt < retries - 1:
                        time.sleep(delay)
                        continue
                    print(f"[CRITICAL] Failed to {description} after {retries} attempts: {err}")
            return False

        instance_id = getattr(self, "instance_id", 0)
        instance_tag = f"[ID:{instance_id}]"
        time_formatted = f"{int(self.time // 60)}:{int(self.time % 60):02d}"
        result_str = (
            str(game_result)
            if hasattr(game_result, "name")
            else game_result.name
            if hasattr(game_result, "name")
            else str(game_result)
        )
        print(f"{instance_tag} 🏁 Game Ended | Result: {result_str} | Play Time: {time_formatted}")
        if hasattr(logger, "success"):
            logger.success(
                f"{instance_tag} 🏁 Game Ended | Result: {result_str} | Play Time: {time_formatted}"
            )  # type: ignore[attr-defined]
        else:
            logger.info(
                f"{instance_tag} 🏁 Game Ended | Result: {result_str} | Play Time: {time_formatted}"
            )

        # Send end game chat message once
        if not getattr(self, "_gg_ack_sent", False):
            try:
                await self.chat_send("gg wp")
            except Exception:
                pass
            self._gg_ack_sent = True

        # 🚀 PERFORMANCE: Garbage collection for memory management in parallel training
        # Force GC to free memory after game ends (critical for parallel training)
        try:

            gc.collect()  # Force garbage collection to free memory

            if PYTORCH_AVAILABLE and torch is not None and torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("[GPU] Cleared CUDA cache after game end")
        except Exception as cleanup_error:
            print(f"[WARNING] Resource cleanup failed: {cleanup_error}")

        # Persist curriculum/training data with retry to avoid data loss
        try:
            if hasattr(self, "curriculum_manager") and self.curriculum_manager:

                def _save_curriculum():
                    mgr = self.curriculum_manager
                    if hasattr(mgr, "update_win_rate"):
                        mgr.update_win_rate(game_result)
                    if hasattr(mgr, "save_data"):
                        try:
                            mgr.save_data(encoding="utf-8")
                        except TypeError:
                            mgr.save_data()

                _retry(_save_curriculum, "persist curriculum data")
        except Exception as curriculum_error:
            print(f"[WARNING] Curriculum data persistence failed: {curriculum_error}")

        # Record match result in opponent tracker with detailed information
        try:
            if hasattr(self, "strategy_analyzer") and self.strategy_analyzer:
                # Get opponent race for statistics
                opponent_race_str = None
                if self.opponent_race:
                    if hasattr(self.opponent_race, "name"):
                        opponent_race_str = self.opponent_race.name
                    else:
                        opponent_race_str = str(self.opponent_race)
            elif (
                hasattr(self, "intel")
                and self.intel
                and hasattr(self.intel, "enemy")
                and self.intel.enemy
            ):
                if hasattr(self.intel.enemy, "race") and self.intel.enemy.race:
                    race_obj = self.intel.enemy.race
                    if hasattr(race_obj, "name") and not isinstance(race_obj, str):
                        opponent_race_str = getattr(race_obj, "name", str(race_obj))  # type: ignore[attr-defined, misc]
                    else:
                        opponent_race_str = str(race_obj)

                # Determine our strategy used
                our_strategy = "standard"
                if hasattr(self, "map_size") and self.map_size == "SMALL":
                    our_strategy = "rush"
                elif self.strategy_analyzer is not None:
                    if self.strategy_analyzer.should_use_aggressive_build():
                        our_strategy = "6-pool"

                # Record match result with detailed stats
                if self.strategy_analyzer is not None:
                    try:
                        self.strategy_analyzer.record_match_result(
                            game_result,
                            opponent_race=opponent_race_str,
                            our_strategy=our_strategy,
                        )
                    except TypeError:
                        # Fallback if method doesn't accept keyword arguments
                        self.strategy_analyzer.record_match_result(game_result)

                # Log match result with race-specific stats
                result_str = "VICTORY" if str(game_result) == "Victory" else "DEFEAT"
                self.write_log(f"Match result: {result_str}", "INFO")

                # Log race-specific win rate if available
                if opponent_race_str and self.strategy_analyzer is not None:
                    try:
                        race_win_rate = self.strategy_analyzer.get_race_win_rate(
                            race=opponent_race_str
                        )
                        self.write_log(
                            f"Win rate vs {opponent_race_str}: {race_win_rate:.1%}",
                            "INFO",
                        )
                    except (AttributeError, TypeError):
                        pass

                # If we lost, log for revenge planning
                if str(game_result) == "Defeat":
                    self.write_log(
                        f"Defeat recorded - will use aggressive build next time",
                        "WARNING",
                    )
                    
                    # 🧠 Build-Order Gap Analyzer: Analyze performance gap vs pro gamers
                    try:
                        from local_training.strategy_audit import analyze_bot_performance
                        gap_analysis = analyze_bot_performance(self, "defeat")
                        if gap_analysis and gap_analysis.critical_issues:
                            self.write_log(
                                f"Gap Analysis: {len(gap_analysis.critical_issues)} critical issues found",
                                "INFO"
                            )
                            # Send to Gemini Self-Healing for automated fixes
                            if self.self_healing and self.self_healing.is_available():
                                from local_training.strategy_audit import StrategyAudit
                                auditor = StrategyAudit()
                                feedback = auditor.generate_gemini_feedback(gap_analysis)
                                # Store feedback for Gemini analysis
                                self.write_log(f"Gap Analysis Feedback:\n{feedback}", "INFO")
                                
                                # 실제로 Gemini에게 분석 요청
                                try:
                                    # 관련 소스 파일 읽기
                                    source_files = {}
                                    try:
                                        economy_file = Path("wicked_zerg_challenger/economy_manager.py")
                                        if economy_file.exists():
                                            with open(economy_file, 'r', encoding='utf-8') as f:
                                                source_files[str(economy_file)] = f.read()[:5000]  # 최대 5000자
                                        
                                        production_file = Path("wicked_zerg_challenger/production_manager.py")
                                        if production_file.exists():
                                            with open(production_file, 'r', encoding='utf-8') as f:
                                                source_files[str(production_file)] = f.read()[:5000]  # 최대 5000자
                                    except Exception as file_error:
                                        print(f"[WARNING] Failed to read source files: {file_error}")
                                    
                                    # Gemini 분석 요청
                                    patch_suggestion = self.self_healing.analyze_gap_feedback(
                                        feedback,
                                        source_files=source_files if source_files else None
                                    )
                                    
                                    if patch_suggestion:
                                        self.write_log(
                                            f"Gemini suggested patch: {patch_suggestion.description}",
                                            "INFO"
                                        )
                                        # 자동 패치 적용은 enable_auto_patch 설정에 따라 결정됨
                                except Exception as gemini_error:
                                    print(f"[WARNING] Gemini gap analysis failed: {gemini_error}")
                    except Exception as gap_error:
                        print(f"[WARNING] Gap analysis failed: {gap_error}")

                    # Log race-specific weakness
                    if opponent_race_str and self.strategy_analyzer is not None:
                        try:
                            stats = self.strategy_analyzer.get_opponent_stats()
                            if isinstance(stats, dict):
                                race_stats = stats.get("race_stats", {})
                                race_key = opponent_race_str.lower()
                                if race_key in race_stats:
                                    race_stat = race_stats[race_key]
                                race_matches = race_stat.get("wins", 0) + race_stat.get("losses", 0)
                                if race_matches >= 2:
                                    race_win_rate = race_stat.get("win_rate", 0.0)
                                    self.write_log(
                                        f"Race-specific weakness detected: {race_win_rate:.1%} win rate vs {opponent_race_str}",
                                        "WARNING",
                                    )
                        except (AttributeError, TypeError):
                            pass
        except Exception as e:
            print(f"[WARNING] Failed to record opponent data: {e}")
            self.write_log(f"Failed to record opponent data: {e}", "ERROR")

        # Close visualization dashboard
        try:
            self.debug_viz.close()
        except Exception:
            pass

        # Summarize results in text
        print(
            f"{instance_tag} Final Resources: Mineral {self.minerals} | Vespene {self.vespene} | Supply {self.supply_used}/{self.supply_cap}"
        )
        logger.info(
            f"{instance_tag} Final Resources: Mineral {self.minerals} | Vespene {self.vespene} | Supply {self.supply_used}/{self.supply_cap}"
        )

        loss_reason = "VICTORY"
        loss_details = {}
        try:
            # Analysis Hub removed (using Vertex AI instead)
            # For now, just use simple loss detection
            if game_result != Result.Victory:
                loss_reason = "DEFEAT"
                loss_details = {
                    "game_time": int(self.time),
                    "worker_count": len(list(self.workers)),
                    "townhall_count": len(list(self.townhalls)),
                    "army_count": len(list(self.units(UnitTypeId.ZERGLING) | self.units(UnitTypeId.ROACH) | self.units(UnitTypeId.HYDRALISK)))
                }

            if loss_reason != "VICTORY":
                print(f"🚩 [패배 분석] 원인: {loss_reason}")
                if loss_details:
                    print(
                        f"   📊 상세: 시간={loss_details.get('game_time', 0)}초, "
                        f"일꾼={loss_details.get('worker_count', 0)}, "
                        f"멀티={loss_details.get('townhall_count', 0)}, "
                        f"병력={loss_details.get('army_count', 0)}"
                    )
        except Exception as e:
            print(f"[WARNING] 패배 원인 분석 중 오류: {e}")
            traceback.print_exc()

        try:
            # Use amount attribute instead of list conversion for better performance
            workers_count = (
                self.workers.amount if hasattr(self.workers, "amount") else self.workers.amount
            )
            townhalls_count = (
                self.townhalls.amount
                if hasattr(self.townhalls, "amount")
                else self.townhalls.amount
            )
            zerglings_count = (
                self.units(UnitTypeId.ZERGLING).amount
                if hasattr(self.units(UnitTypeId.ZERGLING), "amount")
                else self.units(UnitTypeId.ZERGLING).amount
            )
            hydras_count = (
                self.units(UnitTypeId.HYDRALISK).amount
                if hasattr(self.units(UnitTypeId.HYDRALISK), "amount")
                else self.units(UnitTypeId.HYDRALISK).amount
            )
            roaches_count = (
                self.units(UnitTypeId.ROACH).amount
                if hasattr(self.units(UnitTypeId.ROACH), "amount")
                else self.units(UnitTypeId.ROACH).amount
            )
            lurkers_count = (
                self.units(UnitTypeId.LURKER).amount
                if hasattr(self.units(UnitTypeId.LURKER), "amount")
                else self.units(UnitTypeId.LURKER).amount
            )

            self.final_stats = {
                "minerals": self.minerals,
                "vespene": self.vespene,
                "supply_used": self.supply_used,
                "supply_cap": self.supply_cap,
                "supply_army": self.supply_army,
                "workers": workers_count,
                "bases": townhalls_count,
                "zerglings": zerglings_count,
                "hydralisks": hydras_count,
                "roaches": roaches_count,
                "lurkers": lurkers_count,
                "game_time": int(self.time),
                "loss_reason": loss_reason,
            }
        except Exception as e:
            print(f"[WARNING] 최종 통계 저장 실패: {e}")
            self.final_stats = None

        if self.use_neural_network and self.neural_network is not None:
            try:
                base_reward = 0.0
                if str(game_result) == "Victory":
                    base_reward = 1.0
                elif str(game_result) == "Defeat":
                    base_reward = -1.0
                else:
                    base_reward = 0.0

                loss_penalty = 0.0
                if loss_reason != "VICTORY":
                    if "ECONOMY_COLLAPSE" in loss_reason:
                        loss_penalty = -3.0
                        print(f"[TRAIN] ⚠️ 경제 붕괴 패널티: -3.0 (일꾼 생산 우선순위 높이기 필요)")
                    elif "SUPPLY_BLOCKED" in loss_reason:
                        loss_penalty = -2.5
                        print(
                            f"[TRAIN] ⚠️ 인구수 막힘 패널티: -2.5 (대군주 생산 예약 수치 증가 필요)"
                        )
                    elif "ARMY_OVERWHELMED" in loss_reason:
                        loss_penalty = -2.0
                        print(f"[TRAIN] ⚠️ 병력 압도 패널티: -2.0 (aggression 파라미터 조정 필요)")
                    elif "TECH_DISADVANTAGE" in loss_reason:
                        loss_penalty = -2.5
                        print(f"[TRAIN] ⚠️ 테크 차이 패널티: -2.5 (정찰 빈도 증가 필요)")
                    elif "RUSH_FAILED" in loss_reason:
                        loss_penalty = -1.5
                        print(f"[TRAIN] ⚠️ 러시 실패 패널티: -1.5")
                    elif "EXPANSION_FAILED" in loss_reason:
                        loss_penalty = -2.0
                        print(f"[TRAIN] ⚠️ 확장 실패 패널티: -2.0 (멀티 타이밍 개선 필요)")
                    elif "DEFENSE_FAILED" in loss_reason:
                        loss_penalty = -2.0
                        print(f"[TRAIN] ⚠️ 방어 실패 패널티: -2.0 (가시촉수 수비 개수 증가 필요)")

                lurkers = self.units(UnitTypeId.LURKER)
                lurker_count = lurkers.amount if hasattr(lurkers, "amount") else lurkers.amount
                lurker_penalty = 0.0

                if (
                    str(game_result) == "Defeat"
                ) and lurker_count == 0:
                    # Check game time - only penalize if game lasted long enough for Lurker tech
                    game_time = int(self.time) if hasattr(self, "time") else 0
                    if game_time >= 300:  # 5 minutes or more - enough time for Lurker tech
                        lurker_penalty = -2.0  # Reduced from -5.0 to prevent local minima
                        print(
                            f"[TRAIN] ⚠️ Lurker 미생산 패배 (게임 시간 {game_time}초): -2.0 추가 패널티"
                        )
                    else:
                        # Early game defeat - Lurker penalty not applicable
                        lurker_penalty = 0.0
                        print(
                            f"[TRAIN] ℹ️ 초반 패배 (게임 시간 {game_time}초) - Lurker 패널티 적용 안 함"
                        )
                elif lurker_count > 0:
                    lurker_bonus = min(0.5, lurker_count * 0.1)
                    base_reward += lurker_bonus
                    print(
                        f"[TRAIN] ✅ Lurker 생산: +{lurker_bonus:.2f} 보너스 ({lurker_count}마리)"
                    )

                workers = self.workers
                worker_count = workers.amount if hasattr(workers, "amount") else workers.amount
                drone_bonus = 0.0
                if worker_count >= 60:
                    drone_bonus = 0.3
                elif worker_count >= 50:
                    drone_bonus = 0.15
                elif worker_count >= 40:
                    drone_bonus = 0.05

                build_order_reward = self._calculate_build_order_reward()

                # NEW: Use refined reward function from BattleAnalyzer (resource efficiency + supply maintenance)
                refined_reward = 0.0
                try:
                    # Check if analysis_hub exists (may not be initialized in all modes)
                    analysis_hub = getattr(self, "analysis_hub", None)
                    if analysis_hub:
                        game_result_str = (
                            "Victory"
                            if str(game_result) == "Victory"
                            else (
                                "Defeat"
                                if str(game_result) == "Defeat"
                                else "Tie"
                            )
                        )
                        # Use unified get_reward() method (design guide compliance)
                        refined_reward = analysis_hub.get_reward(game_result)
                        # Use refined reward as base, then add other bonuses/penalties
                        base_reward = refined_reward
                except Exception as e:
                    print(f"[WARNING] Failed to calculate refined reward: {e}")
                    # Fallback to original base_reward

                # Rogue tactics reward: Baneling drop and creep-based decision making
                rogue_reward = 0.0
                if self.rogue_tactics:
                    try:
                        # Drop success reward
                        if hasattr(self.rogue_tactics, "last_drop_time") and self.rogue_tactics.last_drop_time > 0:
                            # Reward if drop executed (after 20% of game time)
                            if self.time > 120:  # After 2 minutes
                                rogue_reward += 0.2

                        # Reward when enemy touches creep (drop preparation)
                        enemy_on_creep, enemy_advancing = self.rogue_tactics.get_enemy_on_creep_status()
                        if enemy_on_creep and enemy_advancing:
                            # Reward if enemy advancing on creep (decision reward)
                            rogue_reward += 0.1

                        # Drop preparation state reward
                        if self.rogue_tactics.get_drop_readiness():
                            rogue_reward += 0.05
                    except Exception as e:
                        if self.iteration % 200 == 0:
                            print(f"[WARNING] Rogue reward calculation failed: {e}")

                final_reward = (
                    base_reward + loss_penalty + lurker_penalty + drone_bonus + build_order_reward + rogue_reward
                )

                if str(game_result) == "Victory":
                    print(
                        f"[TRAIN] 🎊 승리! Base: +{base_reward:.1f}, Drone: +{drone_bonus:.2f}, Build Order: {build_order_reward:+.2f}, Rogue Tactics: +{rogue_reward:.2f}, Total: +{final_reward:.2f}"
                    )
                elif str(game_result) == "Defeat":
                    print(
                        f"[TRAIN] 💀 패배... Base: {base_reward:.1f}, Loss Reason: {loss_penalty:.1f}, Lurker: {lurker_penalty:.1f}, Drone: +{drone_bonus:.2f}, Build Order: {build_order_reward:+.2f}, Rogue Tactics: +{rogue_reward:.2f}, Total: {final_reward:.2f}"
                    )

                self.neural_network.finish_episode(final_reward)

                self.save_model_safe()
                if hasattr(self, "instance_id"):
                    print(f"[TRAIN] ✅ 학습 완료 및 모델 저장 (인스턴스 #{self.instance_id})")
                else:
                    print("[TRAIN] ✅ 학습 완료 및 모델 저장")

            except Exception as e:
                print(f"[WARNING] 신경망 학습 중 오류 (무시): {e}")
                traceback.print_exc()

        try:
            self.telemetry_logger.record_game_result(game_result, loss_reason, loss_details)

            # Save analysis hub stats
            if hasattr(self, "analysis_hub") and self.analysis_hub:
                try:
                    result_str = (
                        "Victory"
                        if str(game_result) == "Victory"
                        else (
                            "Defeat"
                            if str(game_result) == "Defeat"
                            else "Tie"
                        )
                    )
                    _retry(
                        lambda: self.analysis_hub.save_stats(result_str),
                        "save analysis hub stats",
                    )
                except Exception as e:
                    if not os.environ.get("SHOW_WINDOW", "false").lower() == "true":
                        pass  # Silent fail in training mode
                    else:
                        print(f"[WARNING] Failed to save analysis hub stats: {e}")

            # try:
            #     from visualize_stats import check_and_generate_report
            #     check_and_generate_report(stats_file, interval=50)
            # except ImportError:

        except Exception as e:
            print(f"[WARNING] 통계 기록 중 오류 (무시): {e}")
            traceback.print_exc()

        try:
            self._log_training_stats(game_result)
        except Exception as e:
            print(f"[WARNING] 학습 통계 로깅 중 오류 (무시): {e}")

        try:
            self._display_matchup_statistics(game_result)
        except Exception as e:
            print(f"[WARNING] 전적 통계 표시 중 오류 (무시): {e}")

        try:
            if self.drone_threat_detected > 0:
                survival_rate = (self.drone_escaped_successfully / self.drone_threat_detected) * 100
                print("\n" + "=" * 70)
                print("🛡️ 드론 생존율 리포트")
                print("=" * 70)
                print(f"위협 감지 횟수: {self.drone_threat_detected}회")
                print(f"성공적 탈출: {self.drone_escaped_successfully}회 ({survival_rate:.1f}%)")
                print(f"적에게 손실: {self.drone_losses_to_enemy}기")
                print("=" * 70 + "\n")
        except Exception as e:
            print(f"[WARNING] 드론 생존율 리포트 표시 중 오류: {e}")

        # Save telemetry data for replay analysis
        await _async_retry(lambda: self._save_telemetry(), "save telemetry data")

        # NOTE: Removed Victory Screen Pause to avoid post-game hang on ladder servers.
        # Game exits via on_chat/on_end leave_game handlers and victory detection.

    def _calculate_build_order_reward(self) -> float:
        """
        빌드 오더 타이밍 보상 계산 (완화된 버전)

        Serral 빌드 오더의 정확한 타이밍에 따라 보상을 부여합니다.
        신경망이 "16일 때 앞마당을 펴는 게 승률이 높구나!"를 학습하도록 합니다.

        [FIXED] 더 관대한 타이밍 윈도우로 변경하여 봇이 건물을 지었는데도
        패널티를 받는 문제를 해결합니다.

        보상 체계 (완화됨):
            - 정확한 타이밍 (목표 서플라이 +/-2): +0.3
            - 약간 늦음 (목표 서플라이 +3~+8): +0.1
            - 늦음 (목표 서플라이 +9~+20): -0.05 (완화)
            - 매우 늦음 (목표 서플라이 +21 이상): -0.2 (완화)
            - 아예 실행 안 함: -0.3 (완화, 건물 존재 여부 재확인)

        중복 건물 페널티:
            - 테크 건물 중복 시 페널티 적용 (예: Spawning Pool 두 개 이상)
            - 중복당 -0.15 points

        Returns:
            float: 빌드 오더 타이밍 보상 (중복 페널티 포함)
        """
        if self.production is None:
            return 0.0

        # Check for duplicate tech buildings and apply penalty
        duplicate_penalty = self.production.check_duplicate_tech_buildings()

        try:
            build_timing = self.production.get_build_order_timing()
            total_reward = 0.0

            target_supply = 16
            actual_supply = build_timing.get("natural_expansion_supply")

            has_expansion = len(self.townhalls) >= 2 if hasattr(self, "townhalls") else False

            if actual_supply is not None:
                supply_diff = actual_supply - target_supply
                if abs(supply_diff) <= 2:
                    reward = 0.3
                    print(
                        f"[BUILD REWARD] ✅ 앞마당 정확한 타이밍 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 3 <= supply_diff <= 8:
                    reward = 0.1
                    print(
                        f"[BUILD REWARD] ⚠️ 앞마당 약간 늦음 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 9 <= supply_diff <= 20:
                    reward = -0.05
                    print(f"[BUILD REWARD] ❌ 앞마당 늦음 (서플라이 {actual_supply}): {reward:.2f}")
                else:
                    reward = -0.2
                    print(
                        f"[BUILD REWARD] ❌ 앞마당 매우 늦음 (서플라이 {actual_supply}): {reward:.2f}"
                    )
                total_reward += reward
            elif has_expansion:
                reward = 0.05
                total_reward += reward
                print(f"[BUILD REWARD] ⚠️ 앞마당 존재 (타이밍 추적 실패): +{reward:.2f}")
            else:
                reward = -0.3
                total_reward += reward
                print(f"[BUILD REWARD] ❌ 앞마당 미실행: {reward:.2f}")

            target_supply = 18
            actual_supply = build_timing.get("gas_supply")

            has_gas = (
                len(self.units(UnitTypeId.EXTRACTOR).structure) >= 1
                if hasattr(self, "units")
                else False
            )

            if actual_supply is not None:
                supply_diff = actual_supply - target_supply
                if abs(supply_diff) <= 2:
                    reward = 0.3
                    print(
                        f"[BUILD REWARD] ✅ 가스 정확한 타이밍 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 3 <= supply_diff <= 8:
                    reward = 0.1
                    print(
                        f"[BUILD REWARD] ⚠️ 가스 약간 늦음 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 9 <= supply_diff <= 20:
                    reward = -0.05
                    print(f"[BUILD REWARD] ❌ 가스 늦음 (서플라이 {actual_supply}): {reward:.2f}")
                else:
                    reward = -0.2
                    print(
                        f"[BUILD REWARD] ❌ 가스 매우 늦음 (서플라이 {actual_supply}): {reward:.2f}"
                    )
                total_reward += reward
            elif has_gas:
                reward = 0.05
                total_reward += reward
                print(f"[BUILD REWARD] ⚠️ 가스 존재 (타이밍 추적 실패): +{reward:.2f}")
            else:
                reward = -0.3
                total_reward += reward
                print(f"[BUILD REWARD] ❌ 가스 미실행: {reward:.2f}")

            target_supply = 17
            actual_supply = build_timing.get("spawning_pool_supply")

            has_pool = (
                len(self.units(UnitTypeId.SPAWNINGPOOL).structure) >= 1
                if hasattr(self, "units")
                else False
            )

            if actual_supply is not None:
                supply_diff = actual_supply - target_supply
                if abs(supply_diff) <= 2:
                    reward = 0.3
                    print(
                        f"[BUILD REWARD] ✅ 산란못 정확한 타이밍 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 3 <= supply_diff <= 8:
                    reward = 0.1
                    print(
                        f"[BUILD REWARD] ⚠️ 산란못 약간 늦음 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 9 <= supply_diff <= 20:
                    reward = -0.05
                    print(f"[BUILD REWARD] ❌ 산란못 늦음 (서플라이 {actual_supply}): {reward:.2f}")
                else:
                    reward = -0.2
                    print(
                        f"[BUILD REWARD] ❌ 산란못 매우 늦음 (서플라이 {actual_supply}): {reward:.2f}"
                    )
                total_reward += reward
            elif has_pool:
                reward = 0.05
                total_reward += reward
                print(f"[BUILD REWARD] ⚠️ 산란못 존재 (타이밍 추적 실패): +{reward:.2f}")
            else:
                reward = -0.3
                total_reward += reward
                print(f"[BUILD REWARD] ❌ 산란못 미실행: {reward:.2f}")

            target_supply = 28
            actual_supply = build_timing.get("third_hatchery_supply")

            has_third_hatch = len(self.townhalls) >= 3 if hasattr(self, "townhalls") else False

            if actual_supply is not None:
                supply_diff = actual_supply - target_supply
                if abs(supply_diff) <= 4:
                    reward = 0.2
                    print(
                        f"[BUILD REWARD] ✅ 세 번째 해처리 정확한 타이밍 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 5 <= supply_diff <= 10:
                    reward = 0.05
                    print(
                        f"[BUILD REWARD] ⚠️ 세 번째 해처리 약간 늦음 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 11 <= supply_diff <= 20:
                    reward = -0.05
                    print(
                        f"[BUILD REWARD] ❌ 세 번째 해처리 늦음 (서플라이 {actual_supply}): {reward:.2f}"
                    )
                else:
                    reward = -0.15
                    print(
                        f"[BUILD REWARD] ❌ 세 번째 해처리 매우 늦음 (서플라이 {actual_supply}): {reward:.2f}"
                    )
                total_reward += reward
            elif has_third_hatch:
                reward = 0.05
                total_reward += reward
                print(f"[BUILD REWARD] ⚠️ 세 번째 해처리 존재 (타이밍 추적 실패): +{reward:.2f}")
            else:
                reward = -0.2
                total_reward += reward
                print(f"[BUILD REWARD] ❌ 세 번째 해처리 미실행: {reward:.2f}")

            target_supply = 30
            actual_supply = build_timing.get("speed_upgrade_supply")

            has_speed = False
            if hasattr(self, "structures"):
                pools = self.units(UnitTypeId.SPAWNINGPOOL).structure
                if pools:
                    try:
                        metabolic_boost = getattr(BuffId, "METABOLICBOOST", None)
                        if metabolic_boost and hasattr(pools.first, "has_buff"):
                            has_speed = pools.first.has_buff(metabolic_boost)
                    except (AttributeError, KeyError, TypeError):
                        pass

            if actual_supply is not None:
                supply_diff = actual_supply - target_supply
                if abs(supply_diff) <= 4:
                    reward = 0.2
                    print(
                        f"[BUILD REWARD] ✅ 발업 정확한 타이밍 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 5 <= supply_diff <= 10:
                    reward = 0.05
                    print(
                        f"[BUILD REWARD] ⚠️ 발업 약간 늦음 (서플라이 {actual_supply}): +{reward:.2f}"
                    )
                elif 11 <= supply_diff <= 20:
                    reward = -0.05
                    print(f"[BUILD REWARD] ❌ 발업 늦음 (서플라이 {actual_supply}): {reward:.2f}")
                else:
                    reward = -0.15
                    print(
                        f"[BUILD REWARD] ❌ 발업 매우 늦음 (서플라이 {actual_supply}): {reward:.2f}"
                    )
                total_reward += reward
            elif has_speed:
                reward = 0.05
                total_reward += reward
                print(f"[BUILD REWARD] ⚠️ 발업 존재 (타이밍 추적 실패): +{reward:.2f}")
            else:
                reward = -0.2
                total_reward += reward
                print(f"[BUILD REWARD] ❌ 발업 미실행: {reward:.2f}")

            # Apply duplicate tech building penalty
            if duplicate_penalty < 0:
                total_reward += duplicate_penalty
                print(f"[BUILD REWARD] ⚠️ 중복 테크 건물 페널티: {duplicate_penalty:.2f}")

            print(f"[BUILD REWARD] 📊 총 빌드 오더 보상: {total_reward:.2f}")
            return total_reward

        except Exception as e:
            print(f"[WARNING] 빌드 오더 보상 계산 중 오류: {e}")
            return 0.0

    async def _check_for_surrender(self) -> bool:
        """
        항복 조건 체크 - 학습 효율 향상을 위한 조기 항복

        승산이 없는 게임을 빠르게 포기하여 다음 게임을 시작하여
        더 나은 학습 데이터를 쌓을 수 있도록 합니다.

        항복 조건 (세 가지 중 하나라도 충족하면 항복):
        1. 일꾼 전멸 + 자원 고갈 (Economy Dead)
        2. 생산 시설 전멸 (Production Dead)
        3. 병력 차이 절망 + 적 본진 근접 (Army Overwhelmed)
        4. 초반 세 분 내 부화장 전멸 (Rage Quit)

        Returns:
            bool: True if surrendered (game ended), False otherwise
        """
        try:
            worker_count = self.workers.amount if hasattr(self, "workers") else 0
            minerals = self.minerals if hasattr(self, "minerals") else 0
            gas = self.vespene if hasattr(self, "vespene") else 0

            if worker_count < 3 and minerals < 50 and gas < 25:
                townhalls = self.townhalls.amount if hasattr(self, "townhalls") else 0
                if townhalls == 0:
                    try:
                        await self.chat_send("GG - No economy left.")
                        print(
                            f"[SURRENDER] Economy Dead: Workers={worker_count}, Minerals={minerals}, Gas={gas}"
                        )
                        self.game_ended = True  # Set flag to stop on_step execution
                        if hasattr(self, "client") and self.client:
                            await self.client.leave_game()  # type: ignore  # type: ignore
                        return True
                    except Exception as e:
                        print(f"[WARNING] Failed to surrender (economy dead): {e}")
                        return False

            townhalls = self.townhalls.amount if hasattr(self, "townhalls") else 0
            if townhalls == 0:
                try:
                    await self.chat_send("GG - No production facilities.")
                    print(f"[SURRENDER] Production Dead: No hatcheries")
                    self.game_ended = True  # Set flag to stop on_step execution
                    if hasattr(self, "client") and self.client:
                        await self.client.leave_game()  # type: ignore
                    return True
                except Exception as e:
                    print(f"[WARNING] Failed to surrender (production dead): {e}")
                    return False

            game_time = self.time if hasattr(self, "time") else 0
            if game_time > 300:  # 5 minutes
                army_units = []
                try:
                    if hasattr(self, "units"):
                        for unit in self.units:
                            if unit.type_id in self.combat_unit_types:
                                army_units.append(unit)
                except Exception:
                    pass

                if len(army_units) == 0:
                    try:
                        enemy_near_base = False
                        if hasattr(self, "start_location"):
                            enemy_units_obj = getattr(self, "known_enemy_units", None) or getattr(
                                self, "enemy_units", None
                            )  # type: ignore[attr-defined]  # type: ignore[attr-defined]
                            enemy_units_list = (
                                list(enemy_units_obj)
                                if enemy_units_obj and hasattr(enemy_units_obj, "__iter__")
                                else []
                            )
                            for enemy in enemy_units_list[:10]:  # Check first 10 enemies
                                if hasattr(enemy, "distance_to"):
                                    dist = enemy.distance_to(self.start_location)
                                    if dist < 30:  # Within 30 units
                                        enemy_near_base = True
                                        break

                        if enemy_near_base:
                            await self.chat_send("GG - Army overwhelmed.")
                            print(
                                f"[SURRENDER] Army Overwhelmed: No army, enemy near base (Time: {game_time:.1f}s)"
                            )
                            self.game_ended = True  # Set flag to stop on_step execution
                            if hasattr(self, "client") and self.client:
                                await self.client.leave_game()  # type: ignore
                            return True
                    except Exception as e:
                        print(f"[WARNING] Failed to check enemy position: {e}")

            game_time = self.time if hasattr(self, "time") else 0
            if game_time < 180 and townhalls == 0:
                try:
                    await self.chat_send("GG - Early hatchery loss.")
                    print(
                        f"[SURRENDER] Rage Quit: All hatcheries lost within 3 minutes (Time: {game_time:.1f}s)"
                    )
                    self.game_ended = True  # Set flag to stop on_step execution
                    if hasattr(self, "client") and self.client:
                        await self.client.leave_game()  # type: ignore
                    return True
                except Exception as e:
                    print(f"[WARNING] Failed to surrender (rage quit): {e}")
                    return False

            if game_time > 1200:
                larvae = self.units(UnitTypeId.LARVA)
                larvae_count = larvae.amount if hasattr(larvae, "amount") else 0
                if minerals < 10 and gas < 10 and larvae_count == 0:
                    try:
                        await self.chat_send("GG - Resource exhausted.")
                        print(
                            f"[SURRENDER] Resource Exhausted: Time={game_time:.1f}s, Minerals={minerals}, Gas={gas}, Larvae={larvae_count}"
                        )
                        self.game_ended = True  # Set flag to stop on_step execution
                        if hasattr(self, "client") and self.client:
                            await self.client.leave_game()  # type: ignore  # type: ignore
                        return True
                    except Exception as e:
                        print(f"[WARNING] Failed to surrender (resource exhausted): {e}")
                        return False

            return False  # No surrender condition met

        except Exception as e:
            if hasattr(self, "iteration") and self.iteration % 100 == 0:
                print(f"[WARNING] Surrender check error: {e}")
            return False

    def _log_training_stats(self, game_result):
        """
        Record win rate and cumulative training count to log.txt

        Args:
            game_result: Game result (Victory, Defeat, etc.)
        """

        # CRITICAL: Log files go to logs/ directory (project root)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # local_training -> project root
        logs_dir = os.path.join(project_root, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "training_log.txt")

        wins = 0
        losses = 0
        total_games = 0

        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        if "총 게임 수:" in line:
                            try:
                                total_games = int(line.split("총 게임 수:")[1].split()[0])
                            except:
                                pass
                        if "승리:" in line:
                            try:
                                wins = int(line.split("승리:")[1].split()[0])
                            except:
                                pass
                        if "패배:" in line:
                            try:
                                losses = int(line.split("패배:")[1].split()[0])
                            except:
                                pass
            except Exception as e:
                print(f"[WARNING] 기존 로그 읽기 실패: {e}")

        if str(game_result) == "Victory":
            wins += 1
        elif str(game_result) == "Defeat":
            losses += 1

        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0.0

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n{'=' * 70}\n")
                f.write(f"[{timestamp}] 게임 결과: {game_result}\n")
                f.write(f"총 게임 수: {total_games}\n")
                f.write(f"승리: {wins} | 패배: {losses}\n")
                f.write(f"승률: {win_rate:.2f}%\n")
                if self.use_neural_network and self.neural_network is not None:
                    f.write(f"누적 학습 횟수: {total_games}회\n")
                f.write(f"{'=' * 70}\n")

            print(f"[LOG] 학습 통계 기록 완료: 승률 {win_rate:.2f}% ({wins}승 {losses}패)")
        except Exception as e:
            print(f"[WARNING] 로그 파일 쓰기 실패: {e}")

    def _display_matchup_statistics(self, game_result):
        """
        Display win/loss statistics and race matchup records at game end

        Args:
            game_result: Current game result (Victory, Defeat, etc.)
        """
        try:
            stats_file = "training_stats.json"
            if not os.path.exists(stats_file):
                print("\n" + "=" * 70)
                print("📊 MATCHUP STATISTICS")
                print("=" * 70)
                print("No statistics file found. This is the first game.")
                print("=" * 70 + "\n")
                return

            # Read all game records
            all_games = []
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                game_data = json.loads(line)
                                all_games.append(game_data)
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                print(f"[WARNING] Failed to read statistics file: {e}")
                return

            # Get current opponent race
            opponent_race = getattr(self, "opponent_race", None)
            if opponent_race is None:
                # Try to get from intel manager
                if hasattr(self, "intel") and self.intel:
                    opponent_race = (
                        self.intel.enemy.race if hasattr(self.intel.enemy, "race") else None
                    )

            # Calculate overall statistics
            total_wins = sum(1 for g in all_games if g.get("result") == "Victory")
            total_losses = sum(1 for g in all_games if g.get("result") == "Defeat")
            total_games = len(all_games)
            overall_win_rate = (total_wins / total_games * 100) if total_games > 0 else 0.0

            # Calculate race-specific statistics
            race_stats = {}
            race_names = ["Terran", "Protoss", "Zerg"]

            for race_name in race_names:
                race_games = [
                    g
                    for g in all_games
                    if g.get("opponent_race") == race_name
                    or (opponent_race and str(opponent_race) == race_name)
                ]
                if not race_games:
                    # Try alternative matching
                    race_games = [
                        g
                        for g in all_games
                        if race_name.lower() in str(g.get("opponent_race", "")).lower()
                    ]

                race_wins = sum(1 for g in race_games if g.get("result") == "Victory")
                race_losses = sum(1 for g in race_games if g.get("result") == "Defeat")
                race_total = len(race_games)
                race_win_rate = (race_wins / race_total * 100) if race_total > 0 else 0.0

                race_stats[race_name] = {
                    "wins": race_wins,
                    "losses": race_losses,
                    "total": race_total,
                    "win_rate": race_win_rate,
                }

            # Display statistics
            print("\n" + "=" * 70)
            print("📊 MATCHUP STATISTICS")
            print("=" * 70)
            print(
                f"Overall Record: {total_wins}W / {total_losses}L ({overall_win_rate:.1f}% Win Rate)"
            )
            print(f"Total Games: {total_games}")
            print("-" * 70)
            print("Race Matchups:")

            for race_name in race_names:
                stats = race_stats[race_name]
                if stats["total"] > 0:
                    print(
                        f"  vs {race_name:8s}: {stats['wins']:3d}W / {stats['losses']:3d}L ({stats['win_rate']:5.1f}% Win Rate) [{stats['total']} games]"
                    )
                else:
                    print(f"  vs {race_name:8s}: No games played")

            # Current game result
            result_emoji = (
                "🏆" if str(game_result) == "Victory" else "💀"
            )
            current_opponent = str(opponent_race) if opponent_race else "Unknown"
            print("-" * 70)
            print(f"Current Game: {result_emoji} {game_result.name} vs {current_opponent}")
            print("=" * 70 + "\n")

        except Exception as e:
            print(f"[WARNING] Failed to display matchup statistics: {e}")

            traceback.print_exc()

    def _write_status_file_sync(self, temp_file: Path, status_file: Path, status_data: Dict):
        """
        Synchronous file write helper for use with asyncio executor
        This prevents blocking the game loop during file I/O operations
        """
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2)
            # Atomic move
            os.replace(str(temp_file), str(status_file))
        except (IOError, OSError, PermissionError):
            # If temp file exists, try to remove it
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except (OSError, PermissionError):
                pass  # Ignore cleanup errors
