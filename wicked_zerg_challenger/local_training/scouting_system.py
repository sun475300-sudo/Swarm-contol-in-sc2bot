# -*- coding: utf-8 -*-
"""
================================================================================
                    Scouting System (scouting_system.py)
================================================================================
Unified scouting system that manages dynamic build order transitions and
heatmap-based predictive scouting.

Core Features:
    1. Initial scouting (Overlord/Zergling)
    2. Event-based scouting (Idle time/Tech scan)
    3. Heatmap-based predictive scouting (Grid-based area management)
    4. Enemy composition analysis and threat assessment
    5. Dynamic build order transition triggers
================================================================================
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

from config import THREAT_BUILDINGS, Config, EnemyRace, GamePhase


@dataclass
class GridCell:
    """Grid cell data"""

    position: Point2  # Cell center coordinates
    last_visited: float = 0.0  # Last visit time
    threat_level: int = 0  # Threat level (0-10)
    is_expansion: bool = False  # Expansion point flag
    is_enemy_base: bool = False  # Enemy base flag
    priority: int = 0  # Scouting priority


class ScoutingSystem:
    """
    Unified scouting system

    Integrated scouting management system combining ScoutManager and HeatmapScout functionality.
    """

    # Heatmap settings
    GRID_SIZE = 20.0  # Grid size (game units)
    STALE_TIME = 60.0  # Time considered stale (seconds)
    CRITICAL_TIME = 90.0  # Time requiring urgent scouting (seconds)

    # Priority weights
    PRIORITY_EXPANSION = 10  # Expansion point
    PRIORITY_ENEMY_BASE = 8  # Enemy base area
    PRIORITY_STALE = 5  # Stale area
    PRIORITY_NORMAL = 1  # Normal area

    def __init__(self, bot: BotAI):
        """
        Args:
            bot: Main bot instance
        """
        self.bot = bot
        self.config = Config()

        # Scouting status
        self.scout_sent: bool = False
        self.overlord_scout_sent: bool = False

        # Enemy information
        self.enemy_race: EnemyRace = EnemyRace.UNKNOWN
        self.enemy_buildings_seen: Set[UnitTypeId] = set()
        self.enemy_units_seen: Set[UnitTypeId] = set()

        # Opponent tech information (for custom unit composition)
        self.enemy_tech_detected: dict = {
            "air_tech": False,  # Air tech (Starport/Stargate)
            "mech_tech": False,  # Mechanic tech (Factory/Robotics Facility)
            "bio_tech": False,  # Bio tech (Barracks/Gateway multiple)
            "detected_time": 0.0,  # Tech detection time
        }

        # Enemy unit composition (for counter-based production)
        self.enemy_composition = {
            "marines": 0,
            "tanks": 0,
            "stalkers": 0,
            "voidrays": 0,
            "zealots": 0,
            "immortals": 0,
            "colossi": 0,
        }

        # Time tracking (for predictive scouting)
        self.last_enemy_seen_time: float = 0.0
        self.last_scout_time: float = 0.0

        # Threat assessment
        self.threat_level: int = 0
        self.enemy_rushing: bool = False
        self.enemy_expanding: bool = False
        self.enemy_has_air: bool = False
        self.enemy_has_cloak: bool = False

        # Scouting locations
        self.scout_targets: List[Point2] = []
        self.current_scout_index: int = 0

        # Heatmap grid system
        self.grid: Dict[Tuple[int, int], GridCell] = {}
        self.map_width: int = 0
        self.map_height: int = 0
        self.grid_cols: int = 0
        self.grid_rows: int = 0
        self.expansion_locations: List[Point2] = []
        self.scout_assignments: Dict[int, Point2] = {}  # unit_tag -> target
        self.total_cells: int = 0
        self.visited_cells: int = 0
        self.heatmap_initialized: bool = False

    def initialize(self):
        """Initialize - Set scout locations and initialize heatmap"""
        b = self.bot

        # Scout targets initialization
        try:
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                enemy_main = b.enemy_start_locations[0]
                self.scout_targets.append(enemy_main)

                try:
                    expansion_locations_list = list(b.expansion_locations.keys())
                    enemy_natural = (
                        expansion_locations_list[1]
                        if len(expansion_locations_list) > 1
                        else enemy_main
                    )
                    self.scout_targets.append(enemy_natural)
                except Exception:
                    self.scout_targets.append(enemy_main)
        except Exception as e:
            print(f"[WARNING] Failed to set enemy scout targets: {e}")

        try:
            self.scout_targets.append(b.game_info.map_center)
        except Exception:

            self.scout_targets.append(Point2((0, 0)))

        # Heatmap initialization
        self._initialize_heatmap()

    def _initialize_heatmap(self):
        """Initialize heatmap grid"""
        b = self.bot

        if self.heatmap_initialized:
            return

        try:
            self.map_width = int(b.game_info.map_size.width)
            self.map_height = int(b.game_info.map_size.height)

            self.grid_cols = int(self.map_width / self.GRID_SIZE) + 1
            self.grid_rows = int(self.map_height / self.GRID_SIZE) + 1

            for col in range(self.grid_cols):
                for row in range(self.grid_rows):
                    x = col * self.GRID_SIZE + self.GRID_SIZE / 2
                    y = row * self.GRID_SIZE + self.GRID_SIZE / 2

                    if x < self.map_width and y < self.map_height:
                        position = Point2((x, y))

                        if b.in_pathing_grid(position):
                            self.grid[(col, row)] = GridCell(position=position)

            self.total_cells = len(self.grid)

            self._mark_expansion_locations()
            self._mark_enemy_base_area()

            self.heatmap_initialized = True
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 200 == 0:
                print(
                    f"?? Heatmap initialized: {self.grid_cols}x{self.grid_rows} grid, {self.total_cells} cells"
                )
        except Exception as e:
            if getattr(b, "iteration", 0) % 200 == 0:
                print(f"[WARNING] Failed to initialize heatmap: {e}")

    def _mark_expansion_locations(self):
        """Mark expansion locations"""
        b = self.bot

        try:
            expansion_locations_list = list(b.expansion_locations.keys())
            for exp_loc in expansion_locations_list:
                self.expansion_locations.append(exp_loc)

                cell_key = self._position_to_grid(exp_loc)
                if cell_key in self.grid:
                    self.grid[cell_key].is_expansion = True
                    self.grid[cell_key].priority += self.PRIORITY_EXPANSION
        except Exception:
            pass

    def _mark_enemy_base_area(self):
        """Mark enemy base area"""
        b = self.bot

        try:
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                enemy_main = b.enemy_start_locations[0]

                for key, cell in self.grid.items():
                    if cell.position.distance_to(enemy_main) < 40:
                        cell.is_enemy_base = True
                        cell.priority += self.PRIORITY_ENEMY_BASE
        except Exception:
            pass

    def _position_to_grid(self, position: Point2) -> Tuple[int, int]:
        """Convert coordinates to grid key"""
        col = int(position.x / self.GRID_SIZE)
        row = int(position.y / self.GRID_SIZE)
        return (col, row)

    async def update(self, context: dict) -> GamePhase:
        """
        Main scouting management loop called every frame

        Args:
            context: Shared data between managers

        Returns:
            GamePhase: Recommended game phase
        """
        b = self.bot

        # Heatmap update (every 8 frames for performance)
        current_iteration = getattr(b, "iteration", 0)
        if current_iteration % 8 == 0:
            self._update_heatmap()

        # 1. Enemy unit/building detection
        self._detect_enemy()

        # 2. Intelligent early scouting (Context-aware scouting within 20 seconds)
        if b.time < 20.0 and current_iteration < 450:
            await self._fast_scouting_20_seconds()

        # 3. Initial scouting (start within 2 seconds)
        if b.supply_used >= self.config.INITIAL_SCOUT_SUPPLY or b.time >= 2:
            await self._send_initial_scout()

        # 4. Overlord scouting
        await self._manage_overlord_scout()

        # 5. Predictive scouting (idle time scouting + heatmap-based)
        await self._predictive_scouting()

        # 6. Threat assessment
        self._evaluate_threat()

        # 7. Context update
        self._update_context(context)

        # 8. Return recommended game phase
        return self._recommend_game_phase()

    def _update_heatmap(self):
        """Update heatmap"""
        b = self.bot

        if not self.heatmap_initialized:
            return

        self.visited_cells = 0

        for key, cell in self.grid.items():
            if b.is_visible(cell.position):
                cell.last_visited = b.time
                self.visited_cells += 1

        # Recalculate priority
        for key, cell in self.grid.items():
            priority = 0

            if cell.is_expansion:
                priority += self.PRIORITY_EXPANSION

            if cell.is_enemy_base:
                priority += self.PRIORITY_ENEMY_BASE

            time_since_visit = b.time - cell.last_visited
            if time_since_visit > self.CRITICAL_TIME:
                priority += self.PRIORITY_STALE * 2
            elif time_since_visit > self.STALE_TIME:
                priority += self.PRIORITY_STALE

            cell.priority = priority

        # Remove dead units from scout_assignments
        # Performance optimization: Use IntelManager cache (check overlords only)
        intel = getattr(b, "intel", None)
        if intel and intel.cached_overlords is not None:
            # Create set of cached overlord tags (fast lookup)
            alive_overlord_tags = {u.tag for u in intel.cached_overlords if hasattr(u, "tag")}
        else:
            # Fallback: 吏곸젒 ?묎렐
            alive_overlord_tags = {u.tag for u in b.units(UnitTypeId.OVERLORD) if hasattr(u, "tag")}

        # Remove dead units from scout_assignments
        dead_tags = [tag for tag in self.scout_assignments if tag not in alive_overlord_tags]
        for tag in dead_tags:
            del self.scout_assignments[tag]

    def get_next_scout_target(self) -> Optional[Point2]:
        """
        Return next scout target location based on heatmap

        Returns:
            Point2: Scout target location, or None if not available
        """
        b = self.bot

        if not self.heatmap_initialized:
            return None

        sorted_cells = sorted(
            self.grid.values(),
            key=lambda c: (c.priority, b.time - c.last_visited),
            reverse=True,
        )

        assigned_positions = set(self.scout_assignments.values())

        for cell in sorted_cells:
            if cell.position not in assigned_positions:
                if b.time - cell.last_visited > self.STALE_TIME:
                    return cell.position

        return None

    # Enemy unit/building detection (ScoutManager logic)
    def _detect_enemy(self):
        """Detect enemy units and buildings (including opponent strategy recording)"""
        b = self.bot

        self.enemy_composition = {
            "marines": 0,
            "tanks": 0,
            "stalkers": 0,
            "voidrays": 0,
            "zealots": 0,
            "immortals": 0,
            "colossi": 0,
        }

        enemy_units = getattr(b, "enemy_units", [])
        if enemy_units:
            self.last_enemy_seen_time = b.time

            for enemy in enemy_units:
                self.enemy_units_seen.add(enemy.type_id)

                if self.enemy_race == EnemyRace.UNKNOWN:
                    self._identify_enemy_race(enemy.type_id)

                if enemy.is_flying:
                    self.enemy_has_air = True

                if enemy.type_id in [
                    UnitTypeId.DARKTEMPLAR,
                    UnitTypeId.BANSHEE,
                    UnitTypeId.GHOST,
                    UnitTypeId.LURKER,
                ]:
                    self.enemy_has_cloak = True

                if enemy.type_id == UnitTypeId.MARINE:
                    self.enemy_composition["marines"] += 1
                elif enemy.type_id in {
                    UnitTypeId.SIEGETANK,
                    UnitTypeId.SIEGETANKSIEGED,
                }:
                    self.enemy_composition["tanks"] += 1
                elif enemy.type_id == UnitTypeId.STALKER:
                    self.enemy_composition["stalkers"] += 1
                elif enemy.type_id == UnitTypeId.VOIDRAY:
                    self.enemy_composition["voidrays"] += 1
                elif enemy.type_id == UnitTypeId.ZEALOT:
                    self.enemy_composition["zealots"] += 1
                elif enemy.type_id == UnitTypeId.IMMORTAL:
                    self.enemy_composition["immortals"] += 1
                elif enemy.type_id == UnitTypeId.COLOSSUS:
                    self.enemy_composition["colossi"] += 1

        enemy_structures = getattr(b, "enemy_structures", [])
        if enemy_structures:
            self.last_enemy_seen_time = b.time

            for building in enemy_structures:
                if building.type_id not in self.enemy_buildings_seen:
                    self.enemy_buildings_seen.add(building.type_id)

                    if self.enemy_race == EnemyRace.UNKNOWN:
                        self._identify_enemy_race(building.type_id)

                    if building.type_id in [UnitTypeId.STARGATE, UnitTypeId.STARPORT]:
                        self.enemy_has_air = True
                        self.enemy_tech_detected["air_tech"] = True
                        self.enemy_tech_detected["detected_time"] = b.time
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            print(
                                f"[SCOUT] [{int(b.time)}s] ?? AIR TECH DETECTED: {building.type_id.name} - Switch to Hydralisk/Queen!"
                            )

                    elif building.type_id in [
                        UnitTypeId.FACTORY,
                        UnitTypeId.ROBOTICSFACILITY,
                    ]:
                        self.enemy_tech_detected["mech_tech"] = True
                        self.enemy_tech_detected["detected_time"] = b.time
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            print(
                                f"[SCOUT] [{int(b.time)}s] ?? MECH TECH DETECTED: {building.type_id.name} - Switch to Ravager/Roach!"
                            )

                    elif building.type_id in [UnitTypeId.BARRACKS, UnitTypeId.GATEWAY]:
                        barracks_count = sum(
                            1 for s in enemy_structures if s.type_id == UnitTypeId.BARRACKS
                        )
                        gateway_count = sum(
                            1 for s in enemy_structures if s.type_id == UnitTypeId.GATEWAY
                        )
                        if barracks_count + gateway_count >= 2:
                            self.enemy_tech_detected["bio_tech"] = True
                            self.enemy_tech_detected["detected_time"] = b.time
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[SCOUT] [{int(b.time)}s] ?? BIO TECH DETECTED: {barracks_count} Barracks + {gateway_count} Gateway - Switch to Baneling/Zergling!"
                                )

                    try:
                        opponent_tracker = getattr(b, "strategy_analyzer", None)
                        if opponent_tracker:
                            strategy = self._infer_strategy_from_building(building.type_id)
                            if strategy:
                                opponent_tracker.record_opponent_strategy(strategy)
                    except Exception:
                        pass

    def _infer_strategy_from_building(self, building_type: UnitTypeId) -> str:
        """Infer opponent strategy from building type"""
        if building_type == UnitTypeId.BARRACKS:
            return "bio"
        elif building_type == UnitTypeId.FACTORY:
            return "mech"
        elif building_type == UnitTypeId.STARPORT:
            return "air"
        elif building_type == UnitTypeId.BUNKER:
            return "rush"
        elif building_type == UnitTypeId.STARGATE:
            return "air"
        elif building_type == UnitTypeId.ROBOTICSFACILITY:
            return "robo"
        elif building_type == UnitTypeId.DARKSHRINE:
            return "rush"
        elif building_type == UnitTypeId.SPAWNINGPOOL:
            return "rush"
        elif building_type == UnitTypeId.ROACHWARREN:
            return "roach"
        elif building_type == UnitTypeId.BANELINGNEST:
            return "baneling"

        return ""

    def _identify_enemy_race(self, unit_type: UnitTypeId):
        """Identify enemy race"""
        terran_units = {
            UnitTypeId.SCV,
            UnitTypeId.MARINE,
            UnitTypeId.COMMANDCENTER,
            UnitTypeId.BARRACKS,
            UnitTypeId.FACTORY,
            UnitTypeId.STARPORT,
        }
        protoss_units = {
            UnitTypeId.PROBE,
            UnitTypeId.ZEALOT,
            UnitTypeId.NEXUS,
            UnitTypeId.GATEWAY,
            UnitTypeId.PYLON,
            UnitTypeId.FORGE,
        }
        zerg_units = {
            UnitTypeId.DRONE,
            UnitTypeId.ZERGLING,
            UnitTypeId.HATCHERY,
            UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.ROACHWARREN,
        }

        if unit_type in terran_units:
            self.enemy_race = EnemyRace.TERRAN
            print(f"[TARGET] [{int(self.bot.time)}s] Enemy race detected: Terran")
        elif unit_type in protoss_units:
            self.enemy_race = EnemyRace.PROTOSS
            print(f"[TARGET] [{int(self.bot.time)}s] Enemy race detected: Protoss")
        elif unit_type in zerg_units:
            self.enemy_race = EnemyRace.ZERG
            print(f"[TARGET] [{int(self.bot.time)}s] Enemy race detected: Zerg")

    # Scouting execution methods (ScoutManager logic)
    async def _fast_scouting_20_seconds(self):
        """Fast scouting logic within 20 seconds"""
        b = self.bot

        if self.scout_sent and self.overlord_scout_sent:
            return

        if not b.enemy_start_locations or len(b.enemy_start_locations) == 0:
            return

        enemy_start = b.enemy_start_locations[0]

        if not self.overlord_scout_sent:
            # Performance optimization: Use IntelManager cache
            intel = getattr(b, "intel", None)
            if intel and intel.cached_overlords is not None:
                overlords = list(intel.cached_overlords) if intel.cached_overlords.exists else []
            else:
                overlords = [u for u in b.units(UnitTypeId.OVERLORD)]
            if overlords:
                scout_overlord = overlords[0]
                if scout_overlord.is_idle or (
                    not scout_overlord.orders or len(scout_overlord.orders) == 0
                ):
                    try:
                        scout_overlord.move(enemy_start)
                        self.overlord_scout_sent = True
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            print(
                                f"[FAST SCOUT] [{int(b.time)}s] Overlord fast scouting to enemy base (20s priority)"
                            )
                        return
                    except Exception:
                        pass

        if not self.scout_sent:
            # Performance optimization: Use IntelManager cache
            intel = getattr(b, "intel", None)
            if intel and intel.cached_zerglings is not None:
                zerglings = [u for u in intel.cached_zerglings if u.is_idle]
            else:
                zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_idle]
            if zerglings:
                scout = zerglings[0]
                try:
                    scout.move(enemy_start)
                    self.scout_sent = True
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(
                            f"[FAST SCOUT] [{int(b.time)}s] Zergling fast scouting to enemy base (20s priority)"
                        )
                    return
                except Exception:
                    pass

        if not self.scout_sent:
            # Performance optimization: Use IntelManager cache
            intel = getattr(b, "intel", None)
            if intel and intel.cached_workers is not None:
                workers = list(intel.cached_workers) if intel.cached_workers.exists else []
            else:
                workers = [w for w in b.workers]
            if workers and len(workers) >= 6:
                scout_drone = workers[0]
                try:
                    scout_drone.move(enemy_start)
                    self.scout_sent = True
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(
                            f"[FAST SCOUT] [{int(b.time)}s] Drone fast scouting to enemy base (20s priority, risky)"
                        )
                except Exception:
                    pass

    async def _send_initial_scout(self):
        """Initial Zergling scouting"""
        b = self.bot

        if self.scout_sent:
            return

        if b.time >= 2 and not self.scout_sent:
            needs_scouting = True
            if hasattr(self, "enemy_race") and self.enemy_race:
                needs_scouting = b.time < 30.0

            if needs_scouting:
                # Performance optimization: Use IntelManager cache
                intel = getattr(b, "intel", None)
                if intel and intel.cached_zerglings is not None:
                    zerglings = [u for u in intel.cached_zerglings if u.is_idle]
                else:
                    zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_idle]
                if zerglings and self.scout_targets:
                    scout = zerglings[0]
                    target = self.scout_targets[0]
                    scout.move(target)
                    self.scout_sent = True
                    self.last_scout_time = b.time
                    return

            # Performance optimization: Use IntelManager cache
            intel = getattr(b, "intel", None)
            if intel and intel.cached_overlords is not None:
                overlords = list(intel.cached_overlords) if intel.cached_overlords.exists else []
            else:
                overlords = [u for u in b.units(UnitTypeId.OVERLORD)]
            if overlords and self.scout_targets:
                scout_overlord = overlords[0]
                if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    enemy_start = b.enemy_start_locations[0]
                    scout_overlord.move(enemy_start)
                    self.scout_sent = True
                    self.last_scout_time = b.time
                    return

        if b.supply_used >= self.config.INITIAL_SCOUT_SUPPLY:
            # Performance optimization: Use IntelManager cache
            intel = getattr(b, "intel", None)
            if intel and intel.cached_zerglings is not None:
                zerglings = [u for u in intel.cached_zerglings if u.is_idle]
            else:
                zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_idle]
            if zerglings and self.scout_targets:
                scout = zerglings[0]
                target = self.scout_targets[0]
                scout.move(target)
                self.scout_sent = True
                self.last_scout_time = b.time

    async def _manage_overlord_scout(self):
        """Manage overlord scouting"""
        b = self.bot

        overlords = [u for u in b.units(UnitTypeId.OVERLORD)]
        if not overlords:
            return

        if (not self.overlord_scout_sent and overlords and len(self.scout_targets) > 0) or (
            b.time >= 2 and not self.overlord_scout_sent
        ):
            scout_overlord = overlords[0]

            try:
                if hasattr(b, "enemy_units"):
                    nearby_enemies = [
                        u for u in b.enemy_units if u.distance_to(scout_overlord) < 10
                    ]
                else:
                    nearby_enemies = []
            except (AttributeError, TypeError):
                nearby_enemies = []

            if nearby_enemies:
                if b.townhalls.exists:
                    townhalls = [th for th in b.townhalls]
                    if townhalls:
                        retreat_pos = townhalls[0].position
                        scout_overlord.move(retreat_pos)
                    else:
                        scout_overlord.move(b.start_location)
                else:
                    scout_overlord.move(b.start_location)
            else:
                if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    enemy_start = b.enemy_start_locations[0]
                    scout_overlord.move(enemy_start)

                    try:
                        map_center = b.game_info.map_center
                        enemy_structures = getattr(b, "enemy_structures", [])
                        proxy_buildings = [
                            UnitTypeId.BARRACKS,
                            UnitTypeId.FACTORY,
                            UnitTypeId.GATEWAY,
                            UnitTypeId.BARRACKSFLYING,
                            UnitTypeId.FACTORYFLYING,
                        ]

                        for building in enemy_structures:
                            if building.type_id in proxy_buildings:
                                building_to_center = building.position.distance_to(map_center)
                                building_to_enemy_start = building.position.distance_to(enemy_start)

                                if building_to_center < building_to_enemy_start:
                                    self.enemy_rushing = True
                                    print(
                                        f"[SCOUT] [{int(b.time)}s] ?? PROXY BUILDING DETECTED: {building.type_id.name}!"
                                    )

                            if building.type_id not in self.enemy_buildings_seen:
                                self.enemy_buildings_seen.add(building.type_id)
                                if building.type_id == UnitTypeId.STARGATE:
                                    self.enemy_has_air = True
                                    print(
                                        f"[SCOUT] [{int(b.time)}s] Detected Stargate - enemy going air!"
                                    )
                                elif building.type_id == UnitTypeId.STARPORT:
                                    self.enemy_has_air = True
                                    print(
                                        f"[SCOUT] [{int(b.time)}s] Detected Starport - enemy going air!"
                                    )
                    except Exception:
                        pass
                self.overlord_scout_sent = True

        if len(overlords) >= 2:
            second_overlord = overlords[1]
            if second_overlord.is_idle:
                if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    enemy_start = b.enemy_start_locations[0]
                    watch_pos = enemy_start.towards(b.game_info.map_center, 20)
                    second_overlord.move(watch_pos)

        if len(overlords) >= 3:
            for i, overlord in enumerate(overlords[1:3]):
                if overlord.is_idle:
                    enemy_start = (
                        b.enemy_start_locations[0]
                        if b.enemy_start_locations
                        else b.game_info.map_center
                    )
                    watch_points = [
                        b.game_info.map_center,
                        enemy_start.towards(b.game_info.map_center, 30),
                    ]
                    if i < len(watch_points):
                        overlord.move(watch_points[i])

    async def _predictive_scouting(self):
        """Predictive scouting (idle time scouting + heatmap-based)"""
        b = self.bot

        # Idle time scouting
        if b.time - self.last_enemy_seen_time > 60:
            overlords = [u for u in b.units(UnitTypeId.OVERLORD) if u.is_idle]
            if overlords:
                if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    expansion_locations_list = list(b.expansion_locations.keys())
                    enemy_expansions = sorted(
                        expansion_locations_list,
                        key=lambda x: x.distance_to(b.enemy_start_locations[0]),
                    )
                    if len(enemy_expansions) > 1 and overlords:
                        target = enemy_expansions[1]
                        if overlords:
                            overlords[0].move(target)
                        print(
                            f"[SCOUT] [{int(b.time)}s] Idle time scouting - Checking enemy expansion"
                        )
                        self.last_enemy_seen_time = b.time

        # Heatmap-based scouting
        if self.heatmap_initialized:
            target = self.get_next_scout_target()
            if target:
                overlords = [u for u in b.units(UnitTypeId.OVERLORD) if u.is_idle]
                for overlord in overlords:
                    if overlord.tag not in self.scout_assignments:
                        overlord.move(target)
                        self.scout_assignments[overlord.tag] = target
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 200 == 0:
                            print(
                                f"[SCOUT] [{int(b.time)}s] Overlord heatmap scouting started ??{target}"
                            )
                        break

    # Threat assessment and game phase recommendation
    def _evaluate_threat(self):
        """Threat assessment - Enemy composition analysis"""
        b = self.bot

        self.threat_level = 0

        for building_type in self.enemy_buildings_seen:
            self.threat_level += THREAT_BUILDINGS.get(building_type, 0)

        self._detect_rush()
        self._detect_expansion()

    def _detect_rush(self):
        """Detect rush"""
        b = self.bot

        if b.time < 180:
            try:
                if hasattr(b, "enemy_units"):
                    enemy_near_base = [
                        u
                        for u in b.enemy_units
                        if u.distance_to(b.start_location) < self.config.RUSH_DETECTION_DISTANCE
                    ]
                else:
                    enemy_near_base = []
            except (AttributeError, TypeError):
                enemy_near_base = []
            if len(enemy_near_base) >= 5:
                self.enemy_rushing = True
                print(f"[RUSH] [{int(b.time)}s] Rush detected! Enemy units: {len(enemy_near_base)}")

        barracks_count = sum(
            1 for bt in self.enemy_buildings_seen if bt in [UnitTypeId.BARRACKS, UnitTypeId.GATEWAY]
        )
        if barracks_count >= 3:
            self.enemy_rushing = True

    def _detect_expansion(self):
        """Detect enemy expansion"""
        b = self.bot

        base_types = {
            UnitTypeId.COMMANDCENTER,
            UnitTypeId.NEXUS,
            UnitTypeId.HATCHERY,
            UnitTypeId.ORBITALCOMMAND,
            UnitTypeId.PLANETARYFORTRESS,
            UnitTypeId.LAIR,
            UnitTypeId.HIVE,
        }
        try:
            if hasattr(b, "enemy_structures"):
                enemy_bases = [s for s in b.enemy_structures if s.type_id in base_types]
            else:
                enemy_bases = []
        except (AttributeError, TypeError):
            enemy_bases = []

        if len(enemy_bases) >= 2:
            self.enemy_expanding = True

    def _update_context(self, context: dict):
        """Update Blackboard context"""
        context["enemy_race"] = self.enemy_race
        context["enemy_rushing"] = self.enemy_rushing
        context["enemy_expanding"] = self.enemy_expanding
        context["enemy_has_air"] = self.enemy_has_air
        context["enemy_has_cloak"] = self.enemy_has_cloak
        context["threat_level"] = self.threat_level
        context["last_enemy_seen"] = self.last_enemy_seen_time

    def _recommend_game_phase(self) -> GamePhase:
        """Recommend game phase based on scouting information"""
        b = self.bot

        if self.enemy_rushing:
            return GamePhase.DEFENSE

        if self.enemy_expanding and b.supply_army >= 30:
            print(f"[TARGET] [{int(b.time)}s] Enemy expansion detected! Attack timing")
            return GamePhase.ATTACK

        if self.threat_level >= 10:
            return GamePhase.DEFENSE
        elif self.threat_level >= 5:
            return GamePhase.TECH

        if b.time < self.config.EARLY_GAME_TIME:
            return GamePhase.OPENING
        elif b.time < self.config.MID_GAME_TIME:
            return GamePhase.ECONOMY
        else:
            return GamePhase.TECH

    def get_scout_status(self) -> dict:
        """Return current scouting status"""
        enemy_race_str = "UNKNOWN"
        if hasattr(self.enemy_race, "name"):
            enemy_race_str = self.enemy_race.name
        else:
            enemy_race_str = str(self.enemy_race)
        return {
            "enemy_race": enemy_race_str,
            "enemy_rushing": self.enemy_rushing,
            "enemy_expanding": self.enemy_expanding,
            "enemy_has_air": self.enemy_has_air,
            "enemy_has_cloak": self.enemy_has_cloak,
            "threat_level": self.threat_level,
            "buildings_seen": len(self.enemy_buildings_seen),
            "last_seen": f"{self.last_enemy_seen_time:.0f}s",
        }

    # Heatmap utility methods
    def get_coverage_percent(self) -> float:
        """Return map exploration percentage"""
        if self.total_cells == 0:
            return 0.0
        return (self.visited_cells / self.total_cells) * 100

    def get_stale_cell_count(self) -> int:
        """Return count of stale cells"""
        b = self.bot
        count = 0
        for cell in self.grid.values():
            if b.time - cell.last_visited > self.STALE_TIME:
                count += 1
        return count
