# -*- coding: utf-8 -*-
"""
Micro Controller - Boids-based movement orchestrator with modular components.

This module serves as the main orchestrator for unit micro-control,
integrating separate modules for:
- Potential field repulsion (potential_fields.py)
- Terrain analysis (terrain_analysis.py)
- Threat response (threat_response.py)
- Formation tactics (formation_tactics.py)
- Boids swarm control (boids_swarm_control.py)
"""

from typing import List, Set

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    UnitTypeId = None
    Point2 = None

# Import modular components
from combat.boids_swarm_control import BoidsSwarmController
from combat.potential_fields import PotentialFieldController
from combat.terrain_analysis import ChokePointDetector
from combat.threat_response import SplashThreatHandler
from combat.formation_tactics import ConcaveFormationController, BurrowController
from combat.targeting import select_target
from combat.stutter_step_kiting import StutterStepKiting


class BoidsController:
    """
    Boids-based micro control orchestrator with modular components.

    Coordinates multiple sub-systems for intelligent unit movement:
    - Boids swarm algorithm for natural movement
    - Potential field avoidance for collision prevention
    - Terrain-aware cohesion adjustments
    - Splash threat response
    - Concave formation generation
    - Burrow ability management
    - K-D Tree / Spatial Grid for O(N log N) proximity queries
    """

    def __init__(self, bot, use_kd_tree: bool = False):
        """
        Initialize the micro controller with all sub-components.

        Args:
            bot: The main bot instance
            use_kd_tree: True for K-D Tree (sparse), False for Spatial Grid (dense)
        """
        self.bot = bot

        # Initialize sub-controllers
        self.swarm_controller = BoidsSwarmController()
        self.potential_field = PotentialFieldController()
        self.chokepoint_detector = ChokePointDetector(bot)
        self.splash_handler = SplashThreatHandler()
        self.formation_controller = ConcaveFormationController()
        self.burrow_controller = BurrowController()
        self.stutter_step = StutterStepKiting(bot)  # ★ NEW: Stutter-Step Kiting ★

        # Update timing - increased interval for performance
        self.last_update = 0
        # Update timing - increased interval for performance
        self.last_update = 0
        self.default_interval = 12
        self.focus_interval = 3  # Combat focus mode (4x faster)
        self.update_interval = self.default_interval
        self.focus_mode_active = False
        self.focus_mode_end_frame = 0

        # Movement configuration
        self.move_scale = 2.5

        # Performance: limit units processed per frame
        self.max_units_per_frame = 30

        # Spatial optimization settings
        self.use_kd_tree = use_kd_tree
        self._spatial_index = None
        self._spatial_available = False
        self._last_spatial_build = 0
        self._spatial_build_interval = 4  # Rebuild every 4 frames

        # Try to import spatial utilities
        try:
            from utils.kd_tree import KDTree, build_unit_kdtree
            from utils.spatial_partition import SpatialGrid, build_unit_grid

            self._KDTree = KDTree
            self._build_unit_kdtree = build_unit_kdtree
            self._SpatialGrid = SpatialGrid
            self._build_unit_grid = build_unit_grid
            self._spatial_available = True
        except ImportError:
            self._spatial_available = False

        # Combat unit types for filtering
        self.combat_unit_types: Set = set()
        if UnitTypeId:
            self.combat_unit_types = {
                UnitTypeId.ZERGLING,
                UnitTypeId.BANELING,
                UnitTypeId.ROACH,
                UnitTypeId.RAVAGER,
                UnitTypeId.HYDRALISK,
                UnitTypeId.MUTALISK,
                UnitTypeId.CORRUPTOR,
                UnitTypeId.ULTRALISK,
                UnitTypeId.LURKER,
                UnitTypeId.BROODLORD,
                UnitTypeId.INFESTOR,
                UnitTypeId.VIPER,
                UnitTypeId.SWARMHOSTMP,
            }


    def set_focus_mode(self, active: bool, duration: int = 44) -> None:
        """
        Set High-Performance Focus Mode for combat.
        
        Args:
            active: Enable/Disable focus mode
            duration: Duration in frames (default ~2s)
        """
        if active:
            self.focus_mode_active = True
            self.update_interval = self.focus_interval
            if hasattr(self.bot, "iteration"):
                 self.focus_mode_end_frame = self.bot.iteration + duration
        else:
            self.focus_mode_active = False
            self.update_interval = self.default_interval

    async def on_step(self, iteration: int) -> None:
        """
        Main update loop - called each game frame.

        Args:
            iteration: Current game iteration/frame
        """
        # Auto-disable focus mode
        if self.focus_mode_active and iteration > self.focus_mode_end_frame:
            self.set_focus_mode(False)

        # Global update rate limiter (use dynamic interval)
        if iteration - self.last_update < self.update_interval:
            return
            
        self.last_update = iteration

        # Update terrain cache (less frequent)
        if iteration % 4 == 0:
            self.chokepoint_detector.update_chokepoints(iteration)

        # Get combat units
        units = self._get_combat_units()
        if not units:
            return

        # Build spatial index for optimized proximity queries
        self._build_spatial_index(units, iteration)

        enemy_units = getattr(self.bot, "enemy_units", [])
        
        # ★ NEW: Priority-based Unit Selection ★
        # 1. Identify high-priority units (near enemies or in danger)
        high_priority_units = []
        low_priority_units = []
        
        # Quick check for combat status
        if enemy_units:
            # Spatial query would be better here, but requires building it first
            # We'll use a simple heuristic: if bad guys exist, check proximity
            # Optimization: check distance to nearest enemy center? No, too risky.
            
            # Use spatial index if available
            if self._spatial_index and self._spatial_available:
                # Find units near any enemy
                pass # Complex to query for all enemies efficiently
            
            # Fallback: simple proximity check (optimized)
            for unit in units:
                # If unit was attacked recently or is attacking -> High Priority
                if (unit.is_attacking or unit.weapon_cooldown > 0 or 
                    (hasattr(unit, "shield_health_percentage") and unit.shield_health_percentage < 1.0)):
                    high_priority_units.append(unit)
                    continue
                    
                # Check proximity to closest enemy (expensive O(N*M)) -> Optimize?
                # Rely on cached "closest_enemy_dist" if available, or just check briefly
                # Here we assume units in combat set a flag or we check a subset

                # Simple optimization: Randomly promote some units if list is empty
                # For now, let's treat ALL units as candidates, but simple filter
                # Check if any enemy is in range (safer than target_in_range with Units collection)
                try:
                    in_range = any(unit.distance_to(e) <= unit.ground_range + 3 for e in enemy_units if hasattr(unit, 'ground_range'))
                    if in_range:
                        high_priority_units.append(unit)
                    else:
                        low_priority_units.append(unit)
                except:
                    low_priority_units.append(unit)
        else:
            low_priority_units = list(units)

        # 2. Staggered processing for low priority units
        # Process 1/4 of low priority units each update
        rollover_idx = (iteration // 2) % 4
        chunk_size = len(low_priority_units) // 4 + 1
        start_idx = rollover_idx * chunk_size
        end_idx = start_idx + chunk_size
        active_low_priority = low_priority_units[start_idx:end_idx]
        
        # Combine lists
        active_units = high_priority_units + active_low_priority
        
        # Limit total processing (increased from 30 -> 80)
        # Combat units take precedence
        self.max_units_per_frame = 80
        if len(active_units) > self.max_units_per_frame:
             # Keep all high priority, trim low priority
             if len(high_priority_units) >= self.max_units_per_frame:
                 active_units = high_priority_units[:self.max_units_per_frame]
             else:
                 remaining_slots = self.max_units_per_frame - len(high_priority_units)
                 active_units = high_priority_units + active_low_priority[:remaining_slots]

        try:
            # Handle burrow abilities
            skip_units = await self.burrow_controller.handle_burrow(
                active_units, enemy_units, iteration, self._do_actions, bot=self.bot
            )

            # ★★★ NEW: Stutter-Step Kiting for Hydra/Roach ★★★
            kiting_handled = set()
            if enemy_units:
                for unit in active_units:
                    if unit.tag in skip_units:
                        continue

                    # 카이팅 가능 유닛은 Stutter-Step으로 처리
                    if self.stutter_step.should_kite(unit):
                        target = enemy_units.closest_to(unit.position) if enemy_units else None
                        if self.stutter_step.execute_kiting(unit, target, enemy_units):
                            kiting_handled.add(unit.tag)

            # Cleanup dead units from kiting tracker
            alive_tags = {u.tag for u in active_units}
            self.stutter_step.cleanup_dead_units(alive_tags)

            # Combine skip sets
            skip_units = skip_units.union(kiting_handled)

            # Apply main boids movement (for units not handled by kiting)
            await self._apply_boids(active_units, enemy_units, skip_units=skip_units)

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Boids micro error: {e}")
            await self._fallback_spread(active_units, enemy_units)

    def _get_combat_units(self):
        """Filter and return combat-capable units."""
        if not UnitTypeId or not hasattr(self.bot, "units"):
            return []
        units = self.bot.units
        if hasattr(units, "filter"):
            return units.filter(lambda u: u.type_id in self.combat_unit_types)
        return [u for u in units if u.type_id in self.combat_unit_types]

    async def _apply_boids(
        self, units, enemy_units, skip_units: Set[int] = None
    ) -> None:
        """
        Apply Boids algorithm with all integrated components.

        Args:
            units: Friendly combat units (already filtered for this frame)
            enemy_units: Enemy units
            skip_units: Set of unit tags to skip (e.g., burrowing units)
        """
        if not Point2:
            return
        skip_units = skip_units or set()

        actions = []
        enemy_center = self._get_enemy_center(enemy_units)
        enemy_structures = getattr(self.bot, "enemy_structures", [])
        splash_threats = self.splash_handler.get_splash_threats(enemy_units)

        # Optimization: Pre-calculate map center for simple fallback
        # map_center = self.bot.game_info.map_center

        for unit in units:
            if unit.tag in skip_units:
                continue

            # Get nearby friendly units for flocking
            neighbors = self._nearby_units(self.bot.units, unit, 6.0) # Query against ALL units for cohesion

            # Select target enemy
            target = select_target(unit, enemy_units, max_range=14.0)
            target_pos = target.position if target else None

            # Calculate splash-based separation multiplier
            separation_multiplier = self.splash_handler.get_separation_multiplier(
                unit, splash_threats
            )

            # Get terrain-based cohesion modifier
            cohesion_multiplier = self.chokepoint_detector.get_cohesion_modifier(
                unit.position
            )

            # Calculate base Boids velocity
            vx, vy = self.swarm_controller.calculate_swarm_velocity(
                unit,
                neighbors,
                target=target_pos,
                enemy_units=enemy_units,
                separation_multiplier=separation_multiplier,
                cohesion_multiplier=cohesion_multiplier,
            )

            # Calculate potential field repulsion
            terrain_points = getattr(self.bot, "structures", [])
            rep_x, rep_y = self.potential_field.get_repulsion_vector(
                unit,
                enemy_units,
                terrain_points=terrain_points,
                structure_units=enemy_structures,
            )

            # Add splash threat repulsion
            splash_x, splash_y = self.splash_handler.calculate_repulsion(
                unit, splash_threats
            )
            rep_x += splash_x
            rep_y += splash_y

            # Extra separation for flying units (mutalisks) near splash threats
            if (
                splash_threats
                and getattr(unit, "is_flying", False)
                and UnitTypeId
                and unit.type_id == UnitTypeId.MUTALISK
            ):
                sep_x, sep_y = self.splash_handler.calculate_neighbor_separation(
                    unit, neighbors
                )
                rep_x += sep_x * self.splash_handler.repulsion_air
                rep_y += sep_y * self.splash_handler.repulsion_air

            # Calculate final movement target
            move_offset = Point2(
                ((vx + rep_x) * self.move_scale, (vy + rep_y) * self.move_scale)
            )
            move_target = unit.position + move_offset

            # Blend with concave formation for ranged units
            concave_target = self.formation_controller.get_concave_target(
                unit, enemy_center or target_pos
            )
            if concave_target:
                move_target = self.formation_controller.blend_positions(
                    move_target,
                    concave_target,
                    self.formation_controller.concave_weight,
                )

            # Execute attack or move command
            # Attack if close and weapon ready, otherwise move
            if (
                target
                and hasattr(unit, "distance_to")
                and unit.distance_to(target) <= (unit.ground_range + 1.0) # Attack range buffer
                and unit.weapon_cooldown == 0
            ):
                actions.append(unit.attack(target))
            else:
                actions.append(unit.move(move_target))

        await self._do_actions(actions)

    async def _fallback_spread(self, units, enemy_units) -> None:
        """
        Fallback movement that preserves spacing when boids fail.

        Uses simple center-avoidance to spread units apart.
        """
        if not Point2:
            return

        actions = []
        for unit in units:
            neighbors = self._nearby_units(units, unit, 3.0)
            if neighbors:
                center = self._centroid(neighbors)
                dx = unit.position.x - center.x
                dy = unit.position.y - center.y
                move_target = unit.position + Point2((dx * 0.8, dy * 0.8))
                actions.append(unit.move(move_target))
                continue

            target = select_target(unit, enemy_units, max_range=12.0)
            if target:
                actions.append(unit.attack(target))

        await self._do_actions(actions)

    def _build_spatial_index(self, units, iteration: int) -> None:
        """
        Build spatial index for fast proximity queries.

        Args:
            units: Units to index
            iteration: Current iteration for caching
        """
        if not self._spatial_available:
            return

        # Only rebuild periodically
        if iteration - self._last_spatial_build < self._spatial_build_interval:
            return

        self._last_spatial_build = iteration

        try:
            if self.use_kd_tree:
                self._spatial_index = self._build_unit_kdtree(units)
            else:
                self._spatial_index = self._build_unit_grid(units, cell_size=6.0)
        except Exception:
            self._spatial_index = None

    def _nearby_units(self, units, unit, radius: float):
        """
        Get units within given radius using spatial optimization.

        Uses K-D Tree or Spatial Grid if available for O(log N) or O(1) queries
        instead of O(N) brute force.

        Args:
            units: All units to search
            unit: Center unit
            radius: Search radius

        Returns:
            List of nearby units
        """
        # Try spatial index first (O(log N) or O(1))
        if self._spatial_index and self._spatial_available:
            try:
                pos = (unit.position.x, unit.position.y)
                results = self._spatial_index.query_radius(pos, radius, exclude_data=unit)
                # results: List of ((x, y), unit, distance)
                return [r[1] for r in results if r[1].tag != unit.tag]
            except Exception:
                pass  # Fall through to standard methods

        # Try SC2 built-in method (faster than manual iteration)
        if hasattr(units, "closer_than"):
            try:
                return units.closer_than(radius, unit.position)
            except Exception:
                pass

        # Fallback: brute force O(N)
        return [
            u for u in units if u.tag != unit.tag and unit.distance_to(u) <= radius
        ]

    def _get_enemy_center(self, enemy_units):
        """Calculate centroid of enemy units."""
        if not Point2 or not enemy_units:
            return None
        try:
            return self._centroid(enemy_units)
        except Exception:
            return None

    @staticmethod
    def _centroid(units):
        """Calculate center of mass for a group of units."""
        if not units or not Point2:
            return Point2((0, 0))
        total_x = sum(u.position.x for u in units)
        total_y = sum(u.position.y for u in units)
        return Point2((total_x / len(units), total_y / len(units)))

    async def _do_actions(self, actions: List) -> None:
        """Execute a batch of unit actions."""
        if not actions:
            return
        if hasattr(self.bot, "do_actions"):
            result = self.bot.do_actions(actions)
            if hasattr(result, "__await__"):
                await result
        else:
            for action in actions:
                result = self.bot.do(action)
                if hasattr(result, "__await__"):
                    await result


# Backward compatibility aliases
PotentialFieldController = PotentialFieldController
ChokePointDetector = ChokePointDetector
