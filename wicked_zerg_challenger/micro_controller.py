# -*- coding: utf-8 -*-
"""
Micro Controller - Boids-based movement with safe fallbacks.
"""

import math
from typing import Iterable, List, Optional, Tuple

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:  # Fallbacks for tooling environments
    UnitTypeId = None
    AbilityId = None
    Point2 = None

from combat.boids_swarm_control import BoidsSwarmController
from combat.targeting import select_target


class PotentialFieldController:
    """Simple repulsion model with air/ground weighting."""

    def __init__(
        self,
        enemy_weight: float = 1.0,
        terrain_weight: float = 1.0,
        structure_weight: float = 1.4,
    ):
        self.enemy_weight = enemy_weight
        self.terrain_weight = terrain_weight
        self.structure_weight = structure_weight
        self.enemy_radius = 6.0
        self.structure_radius = 8.0
        self.terrain_radius = 3.0

    def get_repulsion_vector(
        self,
        unit,
        enemy_units: Iterable,
        terrain_points: Optional[List] = None,
        structure_units: Optional[List] = None,
    ) -> Tuple[float, float]:
        if not Point2:
            return 0.0, 0.0

        terrain_points = terrain_points or []
        is_flying = getattr(unit, "is_flying", False)
        terrain_weight = 0.0 if is_flying else self.terrain_weight

        repulsion_x = 0.0
        repulsion_y = 0.0

        for enemy in enemy_units or []:
            try:
                dist = unit.distance_to(enemy)
            except Exception:
                continue
            if dist <= 0 or dist > self.enemy_radius:
                continue
            strength = (self.enemy_radius - dist) / self.enemy_radius
            dx = unit.position.x - enemy.position.x
            dy = unit.position.y - enemy.position.y
            repulsion_x += (dx / (dist + 0.1)) * strength * self.enemy_weight
            repulsion_y += (dy / (dist + 0.1)) * strength * self.enemy_weight

        for structure in structure_units or []:
            try:
                dist = unit.distance_to(structure)
            except Exception:
                continue
            if dist <= 0 or dist > self.structure_radius:
                continue
            strength = (self.structure_radius - dist) / self.structure_radius
            dx = unit.position.x - structure.position.x
            dy = unit.position.y - structure.position.y
            repulsion_x += (dx / (dist + 0.1)) * strength * self.structure_weight
            repulsion_y += (dy / (dist + 0.1)) * strength * self.structure_weight

        if terrain_weight > 0.0:
            for point in terrain_points:
                try:
                    terrain_pos = getattr(point, "position", point)
                    dist = unit.position.distance_to(terrain_pos)
                except Exception:
                    continue
                if dist <= 0 or dist > self.terrain_radius:
                    continue
                strength = (self.terrain_radius - dist) / self.terrain_radius
                dx = unit.position.x - terrain_pos.x
                dy = unit.position.y - terrain_pos.y
                repulsion_x += (dx / (dist + 0.1)) * strength * terrain_weight
                repulsion_y += (dy / (dist + 0.1)) * strength * terrain_weight

        return repulsion_x, repulsion_y


class ChokePointDetector:
    """Detects chokepoints and narrow passages on the map."""

    def __init__(self, bot):
        self.bot = bot
        self.chokepoints = []
        self.chokepoint_cache_frame = -1
        self.chokepoint_radius = 6.0
        self.narrow_passage_threshold = 4.0

    def update_chokepoints(self, iteration: int) -> None:
        """Update chokepoint cache periodically."""
        if iteration - self.chokepoint_cache_frame < 100:
            return

        self.chokepoint_cache_frame = iteration
        self.chokepoints = []

        # Get map ramps and chokepoints
        if hasattr(self.bot, "game_info"):
            game_info = self.bot.game_info
            if hasattr(game_info, "map_ramps"):
                for ramp in game_info.map_ramps:
                    if hasattr(ramp, "top_center"):
                        self.chokepoints.append(ramp.top_center)
                    if hasattr(ramp, "bottom_center"):
                        self.chokepoints.append(ramp.bottom_center)

    def is_in_chokepoint(self, position) -> bool:
        """Check if position is near a chokepoint."""
        if not self.chokepoints or not position:
            return False

        for choke in self.chokepoints:
            try:
                if position.distance_to(choke) < self.chokepoint_radius:
                    return True
            except Exception:
                continue
        return False

    def get_cohesion_modifier(self, position) -> float:
        """
        Return cohesion weight modifier based on terrain.
        Lower cohesion in chokepoints to prevent traffic jams.
        """
        if self.is_in_chokepoint(position):
            return 0.25  # Reduce cohesion to 25% in chokepoints
        return 1.0


class BoidsController:
    """Boids-based micro control with safe fallback spacing."""

    def __init__(self, bot):
        self.bot = bot
        self.swarm_controller = BoidsSwarmController()
        self.potential_field = PotentialFieldController()
        self.chokepoint_detector = ChokePointDetector(bot)
        self.last_update = 0
        self.update_interval = 8
        self.move_scale = 2.5
        self.concave_weight = 0.6
        self.concave_spread_angle = 0.8
        self.concave_range_buffer = 0.8

        self.last_burrow_update = 0
        self.burrow_check_interval = 16
        self.burrow_health_threshold = 0.35
        self.unburrow_health_threshold = 0.7
        self.splash_avoid_radius = 10.0
        self.splash_repulsion_ground = 3.5
        self.splash_repulsion_air = 10.0
        self.splash_separation_min = 5.0
        self.splash_separation_max = 10.0

        self.combat_unit_types = set()
        self.ranged_unit_types = set()
        self.burrow_unit_types = set()
        self.splash_threat_types = set()
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
            }
            self.ranged_unit_types = {
                UnitTypeId.ROACH,
                UnitTypeId.RAVAGER,
                UnitTypeId.HYDRALISK,
                UnitTypeId.LURKER,
            }
            self.burrow_unit_types = {
                UnitTypeId.ROACH,
                UnitTypeId.LURKER,
                UnitTypeId.BANELING,
            }
            self.splash_threat_types = {
                UnitTypeId.SIEGETANK,
                UnitTypeId.SIEGETANKSIEGED,
                UnitTypeId.HIGHTEMPLAR,
                UnitTypeId.BANELING,
                UnitTypeId.BANELINGBURROWED,
                UnitTypeId.DISRUPTOR,
            }

    async def on_step(self, iteration: int) -> None:
        if iteration - self.last_update < self.update_interval:
            return
        self.last_update = iteration

        # Update chokepoint cache
        self.chokepoint_detector.update_chokepoints(iteration)

        units = self._get_combat_units()
        if not units:
            return

        enemy_units = getattr(self.bot, "enemy_units", [])

        try:
            skip_units = set()
            if iteration - self.last_burrow_update >= self.burrow_check_interval:
                self.last_burrow_update = iteration
                skip_units = await self._handle_burrow(units, enemy_units)

            await self._apply_boids(units, enemy_units, skip_units=skip_units)
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Boids micro error: {e}")
            await self._fallback_spread(units, enemy_units)

    def _get_combat_units(self):
        if not UnitTypeId or not hasattr(self.bot, "units"):
            return []
        units = self.bot.units
        if hasattr(units, "filter"):
            return units.filter(lambda u: u.type_id in self.combat_unit_types)
        return [u for u in units if u.type_id in self.combat_unit_types]

    async def _apply_boids(self, units, enemy_units, skip_units=None) -> None:
        if not Point2:
            return
        skip_units = skip_units or set()

        actions = []
        enemy_center = self._get_enemy_center(enemy_units)
        enemy_structures = getattr(self.bot, "enemy_structures", [])
        splash_threats = self._get_splash_threats(enemy_units)
        for unit in units:
            if unit.tag in skip_units:
                continue

            neighbors = self._nearby_units(units, unit, 6.0)
            target = select_target(unit, enemy_units, max_range=12.0)
            target_pos = target.position if target else None
            separation_multiplier = self._get_splash_separation_multiplier(
                unit, splash_threats
            )

            # Get cohesion modifier based on chokepoint presence
            cohesion_multiplier = self.chokepoint_detector.get_cohesion_modifier(
                unit.position
            )

            vx, vy = self.swarm_controller.calculate_swarm_velocity(
                unit,
                neighbors,
                target=target_pos,
                enemy_units=enemy_units,
                separation_multiplier=separation_multiplier,
                cohesion_multiplier=cohesion_multiplier,
            )

            terrain_points = getattr(self.bot, "structures", [])
            rep_x, rep_y = self.potential_field.get_repulsion_vector(
                unit,
                enemy_units,
                terrain_points=terrain_points,
                structure_units=enemy_structures,
            )
            splash_x, splash_y = self._calculate_splash_repulsion(unit, splash_threats)
            rep_x += splash_x
            rep_y += splash_y

            if (
                splash_threats
                and getattr(unit, "is_flying", False)
                and UnitTypeId
                and unit.type_id == UnitTypeId.MUTALISK
            ):
                sep_x, sep_y = self._neighbor_separation(unit, neighbors)
                rep_x += sep_x * self.splash_repulsion_air
                rep_y += sep_y * self.splash_repulsion_air
            move_offset = Point2(
                ((vx + rep_x) * self.move_scale, (vy + rep_y) * self.move_scale)
            )
            move_target = unit.position + move_offset

            concave_target = self._get_concave_target(unit, enemy_center or target_pos)
            if concave_target:
                move_target = self._blend_positions(
                    move_target, concave_target, self.concave_weight
                )

            if (
                target
                and hasattr(unit, "distance_to")
                and unit.distance_to(target) <= 4
            ):
                actions.append(unit.attack(target))
            else:
                actions.append(unit.move(move_target))

        await self._do_actions(actions)

    async def _fallback_spread(self, units, enemy_units) -> None:
        """Fallback movement that preserves spacing when boids fail."""
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

    def _nearby_units(self, units, unit, radius: float):
        if hasattr(units, "closer_than"):
            try:
                return units.closer_than(radius, unit.position)
            except Exception:
                pass
        return [u for u in units if u.tag != unit.tag and unit.distance_to(u) <= radius]

    def _get_enemy_center(self, enemy_units):
        if not Point2 or not enemy_units:
            return None
        try:
            return self._centroid(enemy_units)
        except Exception:
            return None

    def _get_splash_threats(self, enemy_units):
        if not UnitTypeId or not enemy_units:
            return []
        return [enemy for enemy in enemy_units if enemy.type_id in self.splash_threat_types]

    def _get_splash_separation_multiplier(self, unit, splash_threats) -> float:
        if not splash_threats:
            return 1.0
        nearest = None
        for threat in splash_threats:
            try:
                dist = unit.distance_to(threat)
            except Exception:
                continue
            if nearest is None or dist < nearest:
                nearest = dist

        if nearest is None or nearest > self.splash_avoid_radius:
            return 1.0

        ratio = max(0.0, 1.0 - (nearest / self.splash_avoid_radius))
        return min(
            self.splash_separation_max,
            self.splash_separation_min
            + ratio * (self.splash_separation_max - self.splash_separation_min),
        )

    def _calculate_splash_repulsion(self, unit, splash_threats) -> Tuple[float, float]:
        if not splash_threats:
            return 0.0, 0.0

        repulsion_x = 0.0
        repulsion_y = 0.0
        weight = (
            self.splash_repulsion_air
            if getattr(unit, "is_flying", False)
            else self.splash_repulsion_ground
        )

        for threat in splash_threats:
            try:
                dist = unit.distance_to(threat)
            except Exception:
                continue
            if dist <= 0 or dist > self.splash_avoid_radius:
                continue

            strength = (self.splash_avoid_radius - dist) / self.splash_avoid_radius
            dx = unit.position.x - threat.position.x
            dy = unit.position.y - threat.position.y
            repulsion_x += (dx / (dist + 0.1)) * strength * weight
            repulsion_y += (dy / (dist + 0.1)) * strength * weight

        return repulsion_x, repulsion_y

    def _neighbor_separation(self, unit, neighbors) -> Tuple[float, float]:
        sep_x = 0.0
        sep_y = 0.0
        count = 0
        for neighbor in neighbors:
            if neighbor.tag == unit.tag:
                continue
            try:
                dist = unit.distance_to(neighbor)
            except Exception:
                continue
            if dist <= 0 or dist > self.splash_avoid_radius:
                continue
            dx = unit.position.x - neighbor.position.x
            dy = unit.position.y - neighbor.position.y
            sep_x += dx / (dist * dist + 0.1)
            sep_y += dy / (dist * dist + 0.1)
            count += 1
        if count == 0:
            return 0.0, 0.0
        sep_x /= count
        sep_y /= count
        length = math.hypot(sep_x, sep_y)
        if length == 0:
            return 0.0, 0.0
        return sep_x / length, sep_y / length

    def _get_concave_target(self, unit, enemy_center):
        if not Point2 or not enemy_center:
            return None
        if not UnitTypeId or unit.type_id not in self.ranged_unit_types:
            return None
        if getattr(unit, "is_flying", False):
            return None

        range_value = getattr(unit, "ground_range", 5.0)
        desired_range = max(4.0, range_value + self.concave_range_buffer)

        dx = unit.position.x - enemy_center.x
        dy = unit.position.y - enemy_center.y
        length = math.hypot(dx, dy)
        if length == 0:
            dx, dy = 1.0, 0.0
            length = 1.0

        nx = dx / length
        ny = dy / length
        angle = self._get_tag_offset(unit.tag)
        rx, ry = self._rotate(nx, ny, angle)

        return Point2(
            (enemy_center.x + rx * desired_range, enemy_center.y + ry * desired_range)
        )

    def _get_tag_offset(self, tag: int) -> float:
        bucket = (tag % 7) - 3  # -3..3
        return (bucket / 3.0) * self.concave_spread_angle

    @staticmethod
    def _rotate(x: float, y: float, angle: float) -> Tuple[float, float]:
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return x * cos_a - y * sin_a, x * sin_a + y * cos_a

    @staticmethod
    def _blend_positions(base, target, weight: float):
        if not Point2:
            return base
        return Point2(
            (
                base.x + (target.x - base.x) * weight,
                base.y + (target.y - base.y) * weight,
            )
        )

    async def _handle_burrow(self, units, enemy_units) -> set:
        if not AbilityId or not UnitTypeId:
            return set()

        actions = []
        skip_units = set()
        for unit in units:
            if unit.type_id not in self.burrow_unit_types:
                continue

            health_ratio = self._health_ratio(unit)
            enemy_nearby = self._enemy_within(enemy_units, unit, 8.0)

            is_burrowed = getattr(unit, "is_burrowed", False)
            down_ability, up_ability = self._get_burrow_abilities(unit.type_id)

            if is_burrowed:
                if unit.type_id == UnitTypeId.BANELING and self._enemy_within(
                    enemy_units, unit, 2.5
                ):
                    if up_ability:
                        actions.append(unit(up_ability))
                        skip_units.add(unit.tag)
                    continue
                if health_ratio >= self.unburrow_health_threshold or not enemy_nearby:
                    if up_ability:
                        actions.append(unit(up_ability))
                        skip_units.add(unit.tag)
                else:
                    skip_units.add(unit.tag)
                continue

            if unit.type_id == UnitTypeId.BANELING:
                if enemy_nearby and getattr(unit, "is_idle", True) and down_ability:
                    actions.append(unit(down_ability))
                    skip_units.add(unit.tag)
                    continue

            if (
                enemy_nearby
                and health_ratio <= self.burrow_health_threshold
                and down_ability
            ):
                actions.append(unit(down_ability))
                skip_units.add(unit.tag)

        await self._do_actions(actions)
        return skip_units

    @staticmethod
    def _health_ratio(unit) -> float:
        health = getattr(unit, "health", 0)
        health_max = getattr(unit, "health_max", 0)
        if not health_max:
            return 1.0
        return max(0.0, min(1.0, health / health_max))

    @staticmethod
    def _enemy_within(enemy_units, unit, radius: float) -> bool:
        if not enemy_units:
            return False
        try:
            for enemy in enemy_units:
                if unit.distance_to(enemy) <= radius:
                    return True
        except Exception:
            return False
        return False

    @staticmethod
    def _get_burrow_abilities(unit_type):
        down_map = {
            "ROACH": "BURROWDOWN_ROACH",
            "LURKER": "BURROWDOWN_LURKER",
            "BANELING": "BURROWDOWN_BANELING",
        }
        up_map = {
            "ROACH": "BURROWUP_ROACH",
            "LURKER": "BURROWUP_LURKER",
            "BANELING": "BURROWUP_BANELING",
        }

        unit_name = getattr(unit_type, "name", "")
        down_name = down_map.get(unit_name, "BURROWDOWN")
        up_name = up_map.get(unit_name, "BURROWUP")

        down_ability = getattr(AbilityId, down_name, None)
        up_ability = getattr(AbilityId, up_name, None)
        return down_ability, up_ability

    @staticmethod
    def _centroid(units) -> Point2:
        if not units:
            return Point2((0, 0))
        total_x = sum(u.position.x for u in units)
        total_y = sum(u.position.y for u in units)
        return Point2((total_x / len(units), total_y / len(units)))

    async def _do_actions(self, actions: List) -> None:
        if not actions:
            return
        if hasattr(self.bot, "do_actions"):
            await self.bot.do_actions(actions)
        else:
            for action in actions:
                await self.bot.do(action)
