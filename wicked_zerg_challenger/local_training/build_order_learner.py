#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Order Learner and Executor

This module provides:
1. BuildOrderLearner: Loads and manages build orders from JSON files
2. BuildOrderExecutor: Executes build orders in-game with adaptive logic
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from dataclasses import dataclass

try:
    SC2_AVAILABLE = True
except ImportError:
    SC2_AVAILABLE = False
 # Fallback for testing without SC2
class UnitTypeId:
    pass
 SPAWNINGPOOL = None
 EXTRACTOR = None
 HATCHERY = None
 OVERLORD = None
 QUEEN = None
 ZERGLING = None
 ROACHWARREN = None
 BANELINGNEST = None
 EVOLUTIONCHAMBER = None
 LAIR = None
 SPIRE = None
 INFESTATIONPIT = None
 ULTRALISKCAVERN = None
 LURKERDENMP = None
 HYDRALISKDEN = None
 GREATERSPIRE = None
 HIVE = None


@dataclass
class BuildOrderStep:
    """Single build order step"""
 supply: int
 time_seconds: int
 action: str
 minerals: Optional[int] = None
 gas: Optional[int] = None
 notes: Optional[str] = None


@dataclass
class BuildOrder:
    """Complete build order"""
 name: str
 race: str
 vs_race: str
 steps: List[BuildOrderStep]
 player_name: Optional[str] = None
    source: str = "unknown"
 tags: List[str] = None

def __post_init__(self):
    if self.tags is None:
        pass
    self.tags = []


class BuildOrderLearner:
    """
 Loads and manages build orders from JSON files

 Features:
 - Loads build orders from data directory
 - Filters by matchup (ZvT, ZvP, ZvZ)
 - Filters by strategy tags (aggressive, economic, standard)
 - Provides build order selection based on criteria
    """

def __init__(self, data_dir: str = "data/build_orders"):
    """
 Args:
 data_dir: Directory containing build order JSON files
     """
 self.data_dir = Path(data_dir)
 self.build_orders: List[BuildOrder] = []
 self._load_build_orders()

def _load_build_orders(self):
    """Load all build orders from JSON files"""
 if not self.data_dir.exists():
     print(f"[BUILD ORDER LEARNER] Data directory not found: {self.data_dir}")
 return

     json_files = list(self.data_dir.glob("*.json"))
     json_files = [f for f in json_files if not f.name.startswith("collection_summary")]

 for json_file in json_files:
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         with open(json_file, 'r', encoding='utf-8') as f:
 data = json.load(f)

 # Handle both list and single dict formats
 if isinstance(data, list):
     builds = data
 elif isinstance(data, dict):
     builds = [data]
 else:
     pass
 continue

 for build_data in builds:
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         build = self._parse_build_order(build_data)
 if build:
     self.build_orders.append(build)
 except Exception as e:
     print(f"[BUILD ORDER LEARNER] Error parsing build in {json_file.name}: {e}")
 continue

 except Exception as e:
     print(f"[BUILD ORDER LEARNER] Error loading {json_file.name}: {e}")
 continue

     print(f"[BUILD ORDER LEARNER] Loaded {len(self.build_orders)} build orders")

def _parse_build_order(self, data: Dict) -> Optional[BuildOrder]:
    """Parse build order from dictionary"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     # Parse steps
 steps = []
     for step_data in data.get("steps", []):
         pass
     step = BuildOrderStep(
     supply = step_data.get("supply", 0),
     time_seconds = step_data.get("time_seconds", 0),
     action = step_data.get("action", ""),
     minerals = step_data.get("minerals"),
     gas = step_data.get("gas"),
     notes = step_data.get("notes")
 )
 steps.append(step)

 build = BuildOrder(
     name = data.get("name", "Unknown Build"),
     race = data.get("race", "Z"),
     vs_race = data.get("vs_race", "T"),
 steps = steps,
     player_name = data.get("player_name"),
     source = data.get("source", "unknown"),
     tags = data.get("tags", [])
 )

 return build
 except Exception as e:
     print(f"[BUILD ORDER LEARNER] Error parsing build: {e}")
 return None

def get_build_orders(self, matchup: Optional[str] = None,
 strategy: Optional[str] = None,
 player_name: Optional[str] = None) -> List[BuildOrder]:
     """
 Get build orders matching criteria

 Args:
     matchup: Matchup filter (e.g., "ZvT", "ZvP", "ZvZ")
     strategy: Strategy filter (e.g., "aggressive", "economic", "standard")
 player_name: Player name filter

 Returns:
 List of matching build orders
     """
 matches = self.build_orders

 # Filter by matchup
 if matchup:
     matchup_upper = matchup.upper()
 matches = [b for b in matches
     if f"{b.race}v{b.vs_race}".upper() == matchup_upper]

 # Filter by strategy (tags)
 if strategy:
     strategy_lower = strategy.lower()
 matches = [b for b in matches
 if strategy_lower in [t.lower() for t in b.tags] or
     strategy_lower == "standard" and not b.tags]

 # Filter by player name
 if player_name:
     matches = [b for b in matches
 if b.player_name and player_name.lower() in b.player_name.lower()]

 return matches

def get_best_build(self, matchup: str, strategy: str = "standard") -> Optional[BuildOrder]:
    """
 Get the best build order for a matchup and strategy

 Args:
     matchup: Matchup (e.g., "ZvT", "ZvP", "ZvZ")
     strategy: Strategy preference (default: "standard")

 Returns:
 Best matching build order, or None if none found
     """
 builds = self.get_build_orders(matchup = matchup, strategy = strategy)

 if not builds:
     # Fallback to any build for this matchup
 builds = self.get_build_orders(matchup = matchup)

 if not builds:
     return None

 # Prefer builds with more steps (more complete)
 builds.sort(key = lambda b: len(b.steps), reverse = True)

 # Prefer pro player builds
 pro_builds = [b for b in builds if b.player_name]
 if pro_builds:
     return pro_builds[0]

 return builds[0]


class BuildOrderExecutor:
    """
 Executes build orders in-game with adaptive logic

 Features:
 - Supply/time-based trigger checking
 - Resource availability validation
 - Tech requirement checking
 - Fallback logic for impossible steps
 - Progress tracking
    """

 # Action name to UnitTypeId mapping
 ACTION_MAP: Dict[str, Any] = {
     "spawning pool": UnitTypeId.SPAWNINGPOOL,
     "pool": UnitTypeId.SPAWNINGPOOL,
     "extractor": UnitTypeId.EXTRACTOR,
     "gas": UnitTypeId.EXTRACTOR,
     "hatchery": UnitTypeId.HATCHERY,
     "hatch": UnitTypeId.HATCHERY,
     "overlord": UnitTypeId.OVERLORD,
     "queen": UnitTypeId.QUEEN,
     "zergling": UnitTypeId.ZERGLING,
     "ling": UnitTypeId.ZERGLING,
     "roach warren": UnitTypeId.ROACHWARREN,
     "roach": UnitTypeId.ROACHWARREN,
     "baneling nest": UnitTypeId.BANELINGNEST,
     "bane nest": UnitTypeId.BANELINGNEST,
     "evolution chamber": UnitTypeId.EVOLUTIONCHAMBER,
     "evo": UnitTypeId.EVOLUTIONCHAMBER,
     "lair": UnitTypeId.LAIR,
     "spire": UnitTypeId.SPIRE,
     "infestation pit": UnitTypeId.INFESTATIONPIT,
     "infestation": UnitTypeId.INFESTATIONPIT,
     "ultralisk cavern": UnitTypeId.ULTRALISKCAVERN,
     "ultra cavern": UnitTypeId.ULTRALISKCAVERN,
     "lurker den": UnitTypeId.LURKERDENMP,
     "lurker": UnitTypeId.LURKERDENMP,
     "hydralisk den": UnitTypeId.HYDRALISKDEN,
     "hydra den": UnitTypeId.HYDRALISKDEN,
     "greater spire": UnitTypeId.GREATERSPIRE,
     "hive": UnitTypeId.HIVE,
 }

def __init__(self, bot, learner: BuildOrderLearner):
    """
 Args:
 bot: SC2 BotAI instance
 learner: BuildOrderLearner instance
     """
 self.bot = bot
 self.learner = learner
 self.current_build: Optional[BuildOrder] = None
 self.current_step_index: int = 0
 self.completed_steps: set = set()
 self.execution_log: List[str] = []

def set_build_order(self, matchup: str, strategy: str = "standard",
 map_size: Optional[str] = None, player_name: Optional[str] = None):
     """
 Set the current build order to execute

 Args:
     matchup: Matchup (e.g., "ZvT", "ZvP", "ZvZ")
     strategy: Strategy preference (default: "standard")
 map_size: Map size filter (optional)
 player_name: Player name filter (optional)
     """
 build = self.learner.get_best_build(matchup, strategy)

 if not build and player_name:
     builds = self.learner.get_build_orders(matchup = matchup, player_name = player_name)
 if builds:
     build = builds[0]

 if not build:
     print(f"[BUILD EXECUTOR] No build order found for {matchup} ({strategy})")
 self.current_build = None
 self.current_step_index = 0
 return

 self.current_build = build
 self.current_step_index = 0
 self.completed_steps = set()
 self.execution_log = []

     print(f"[BUILD EXECUTOR] Set build: {build.name} ({matchup}, {strategy})")
     print(f"[BUILD EXECUTOR] Total steps: {len(build.steps)}")

 async def execute_current_build(self):
     """
 Execute the current step of the build order

 This should be called in on_step() during early game (first 4 minutes)
     """
 if not self.current_build:
     return

 if self.current_step_index >= len(self.current_build.steps):
     # Build order complete
 return

 step = self.current_build.steps[self.current_step_index]

 # Check if step should be executed
 if self._should_execute_step(step):
     success = await self._execute_step(step)

 if success:
     self.completed_steps.add(self.current_step_index)
 self.current_step_index += 1
     self.execution_log.append(f"Completed: {step.action} at supply {step.supply}")
 else:
     # Skip this step if it's impossible, but continue with next
     self.execution_log.append(f"Skipped: {step.action} (impossible)")
 self.current_step_index += 1

def _should_execute_step(self, step: BuildOrderStep) -> bool:
    """Check if step should be executed based on supply/time"""
 current_supply = self.bot.supply_used
 current_time = self.bot.time

 # Check supply trigger (allow 1 supply tolerance)
 supply_ready = current_supply >= (step.supply - 1)

 # Check time trigger (allow 5 second tolerance)
 time_ready = current_time >= (step.time_seconds - 5)

 # Execute if either condition is met
 return supply_ready or time_ready

 async def _execute_step(self, step: BuildOrderStep) -> bool:
     """Execute a single build order step"""
 action_lower = step.action.lower()

     # Parse unit count if present (e.g., "Zergling x6")
 unit_count = 1
     count_match = re.search(r'x(\d+)', action_lower)
 if count_match:
     unit_count = int(count_match.group(1))
     action_lower = re.sub(r'\s*x\d+', '', action_lower).strip()

 # Get UnitTypeId from action name
 unit_type = self._get_unit_type_from_action(action_lower)

 if not unit_type:
     # Unknown action - try to parse manually
 return await self._try_parse_action(step.action)

 # Check if already built/pending
 if self._is_already_built(unit_type):
     return True # Already done

 # Check resources
 if not self._has_resources(step, unit_type):
     return False # Not enough resources

 # Check tech requirements
 if not self._has_tech_requirements(unit_type):
     return False # Missing tech

 # Execute the build
 return await self._build_unit_or_structure(unit_type, unit_count)

def _get_unit_type_from_action(self, action: str) -> Optional[Any]:
    """Get UnitTypeId from action name"""
 action = action.strip().lower()

 # Direct match
 if action in self.ACTION_MAP:
     return self.ACTION_MAP[action]

 # Partial match
 for key, unit_id in self.ACTION_MAP.items():
     if key in action or action in key:
         return unit_id

 return None

def _is_already_built(self, unit_type: Any) -> bool:
    """Check if unit/structure is already built or pending"""
 if not SC2_AVAILABLE:
     return False

 # Check existing structures
 if self.bot.structures(unit_type).exists:
     return True

 # Check pending
     if hasattr(self.bot, 'already_pending'):
         pass
     if self.bot.already_pending(unit_type) > 0:
         pass
     return True

 return False

def _has_resources(self, step: BuildOrderStep, unit_type: Any) -> bool:
    """Check if bot has enough resources"""
 if not SC2_AVAILABLE:
     return True # Assume available for testing

 # Use step minerals/gas if provided
 required_minerals = step.minerals
 required_gas = step.gas

 # Fallback to game cost if not specified
 if required_minerals is None or required_gas is None:
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         # Try to get cost from game data
 cost = self.bot.game_data.units[unit_type.value].cost
 if required_minerals is None:
     required_minerals = cost.minerals
 if required_gas is None:
     required_gas = cost.vespene
 except (AttributeError, KeyError, TypeError):
     # Fallback to default costs if unable to get from game data
 if required_minerals is None:
     required_minerals = 50 # Default
 if required_gas is None:
     required_gas = 0 # Default

 return (self.bot.minerals >= required_minerals and
 self.bot.vespene >= required_gas)

def _has_tech_requirements(self, unit_type: Any) -> bool:
    """Check if tech requirements are met"""
 if not SC2_AVAILABLE:
     return True # Assume available for testing

 # Basic tech requirements for Zerg
 tech_map = {
 UnitTypeId.LAIR: UnitTypeId.HATCHERY,
 UnitTypeId.HIVE: UnitTypeId.LAIR,
 UnitTypeId.SPIRE: UnitTypeId.LAIR,
 UnitTypeId.GREATERSPIRE: UnitTypeId.SPIRE,
 UnitTypeId.ROACHWARREN: UnitTypeId.SPAWNINGPOOL,
 UnitTypeId.BANELINGNEST: UnitTypeId.SPAWNINGPOOL,
 UnitTypeId.HYDRALISKDEN: UnitTypeId.LAIR,
 UnitTypeId.LURKERDENMP: UnitTypeId.HYDRALISKDEN,
 UnitTypeId.INFESTATIONPIT: UnitTypeId.LAIR,
 UnitTypeId.ULTRALISKCAVERN: UnitTypeId.HIVE,
 }

 required = tech_map.get(unit_type)
 if required:
     return self.bot.structures(required).ready.exists

 return True

 async def _build_unit_or_structure(self, unit_type: Any, count: int = 1) -> bool:
     """Build a unit or structure"""
 if not SC2_AVAILABLE:
     return False

 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     # Structures
 if unit_type in [UnitTypeId.SPAWNINGPOOL, UnitTypeId.EXTRACTOR,
 UnitTypeId.ROACHWARREN, UnitTypeId.BANELINGNEST,
 UnitTypeId.EVOLUTIONCHAMBER, UnitTypeId.SPIRE,
 UnitTypeId.INFESTATIONPIT, UnitTypeId.ULTRALISKCAVERN,
 UnitTypeId.LURKERDENMP, UnitTypeId.HYDRALISKDEN]:
 # Find a worker to build
 workers = self.bot.workers.idle
 if not workers:
     workers = self.bot.workers

 if workers:
     worker = workers[0]
 # Get build location (simplified - use main base)
 if self.bot.townhalls:
     location = self.bot.townhalls[0].position
 await self.bot.build(unit_type, near = location)
 return True

 # Units from larva
 elif unit_type in [UnitTypeId.ZERGLING, UnitTypeId.OVERLORD]:
     larvae = self.bot.larva
 if larvae:
     for _ in range(min(count, len(larvae))):
         if larvae:
             await self.bot.train(unit_type, larvae[0])
 return True

 # Queen (from hatchery)
 elif unit_type == UnitTypeId.QUEEN:
     hatcheries = self.bot.townhalls.ready
 for hatchery in hatcheries:
     if not hatchery.has_buff(AbilityId.QUEENSPAWNLARVATIMER):
         await self.bot.train(UnitTypeId.QUEEN, hatchery)
 return True

 # Morphs (Lair, Hive, Greater Spire)
 elif unit_type in [UnitTypeId.LAIR, UnitTypeId.HIVE, UnitTypeId.GREATERSPIRE]:
     if unit_type == UnitTypeId.LAIR:
         hatcheries = self.bot.townhalls.ready
 if hatcheries:
     await hatcheries[0].morph(UnitTypeId.LAIR)
 return True
 elif unit_type == UnitTypeId.HIVE:
     lairs = self.bot.townhalls(UnitTypeId.LAIR).ready
 if lairs:
     await lairs[0].morph(UnitTypeId.HIVE)
 return True
 elif unit_type == UnitTypeId.GREATERSPIRE:
     spires = self.bot.structures(UnitTypeId.SPIRE).ready
 if spires:
     await spires[0].morph(UnitTypeId.GREATERSPIRE)
 return True

 except Exception as e:
     print(f"[BUILD EXECUTOR] Error executing {unit_type}: {e}")
 return False

 return False

 async def _try_parse_action(self, action: str) -> bool:
     """Try to parse and execute an unknown action"""
 # This is a fallback for actions not in the standard map
 # Could be extended to handle custom actions
     print(f"[BUILD EXECUTOR] Unknown action: {action}")
 return False

def get_progress_status(self) -> str:
    """Get current build order progress status"""
 if not self.current_build:
     return "No build order set"

 total_steps = len(self.current_build.steps)
 completed = len(self.completed_steps)
 progress_pct = (completed / total_steps * 100) if total_steps > 0 else 0

 if self.current_step_index < total_steps:
     current_step = self.current_build.steps[self.current_step_index]
     return (f"{self.current_build.name}: {completed}/{total_steps} steps "
     f"({progress_pct:.1f}%) - Next: {current_step.action} at supply {current_step.supply}")
 else:
     return f"{self.current_build.name}: Complete ({completed}/{total_steps} steps)"

def is_complete(self) -> bool:
    """Check if build order is complete"""
 if not self.current_build:
     return True

 return self.current_step_index >= len(self.current_build.steps)
