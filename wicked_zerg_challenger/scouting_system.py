#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
<<<<<<< Current (Your changes)
Scouting System - Overlord sensor network + scouting.
"""

from typing import Dict, List
from pathlib import Path
import json
import csv

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        OVERLORD = "OVERLORD"
        OVERSEER = "OVERSEER"
        ZERGLING = "ZERGLING"
        HATCHERY = "HATCHERY"
        LAIR = "LAIR"
        HIVE = "HIVE"
    class AbilityId:
        MORPH_OVERSEER = "MORPH_OVERSEER"
    Point2 = tuple


class ScoutingSystem:
    def __init__(self, bot):
        self.bot = bot
        self.intel_manager = None
        self.last_scout_update = 0
        self.last_overseer_morph = 0
        self.scout_assignments: Dict[int, Point2] = {}
        self.scout_zerglings: List[int] = []
        self.last_sensor_log = 0
        self.log_interval = 220
        self.sensor_csv_path = "logs/sensor_network.csv"
        self.sensor_json_path = "logs/sensor_network.json"

        params = getattr(self.bot, "scout_params", None)
        if isinstance(params, dict):
            self.log_interval = params.get("log_interval", self.log_interval)
            self.sensor_csv_path = params.get("sensor_csv_path", self.sensor_csv_path)
            self.sensor_json_path = params.get("sensor_json_path", self.sensor_json_path)

    async def on_step(self, iteration: int):
        try:
            if not self.intel_manager and hasattr(self.bot, "intel"):
                self.intel_manager = self.bot.intel

            if iteration - self.last_scout_update > 110:
                await self._update_overlord_network()
                await self._assign_ling_scouts()
                await self._maybe_morph_overseer()
                self.last_scout_update = iteration

            await self._move_scouts()
            self._log_sensor_snapshot(iteration)
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Scouting system error: {e}")

    async def _update_overlord_network(self):
        if not hasattr(self.bot, "units"):
            return
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        if not overlords.exists:
            return
        if not self.bot.enemy_start_locations or not self.bot.townhalls.exists:
            return

        enemy_start = self.bot.enemy_start_locations[0]
        our_base = self.bot.townhalls.first.position
        map_center = getattr(self.bot.game_info, "map_center", our_base)

        # Perimeter radar points
        perimeter = self._compute_perimeter_points(map_center, 0.55)
        drop_watch = self._compute_drop_watch_points(our_base, enemy_start)
        path_points = [our_base.towards(enemy_start, d) for d in (20.0, 35.0)]
        targets = perimeter[:4] + drop_watch + path_points

        for overlord, target in zip(overlords, targets):
            self.scout_assignments[overlord.tag] = target

    async def _assign_ling_scouts(self):
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if not zerglings.exists or not self.bot.enemy_start_locations:
            return
        active = [z for z in zerglings if z.tag in self.scout_zerglings]
        if len(active) >= 2:
            return
        available = [z for z in zerglings if z.tag not in self.scout_zerglings]
        for z in available[:2 - len(active)]:
            self.scout_zerglings.append(z.tag)
            self.scout_assignments[z.tag] = self.bot.enemy_start_locations[0]

    async def _maybe_morph_overseer(self):
        if self.bot.time < 240 or self.bot.vespene < 50:
            return
        if self.bot.structures(UnitTypeId.LAIR).exists or self.bot.structures(UnitTypeId.HIVE).exists:
            overlords = self.bot.units(UnitTypeId.OVERLORD)
            if overlords.exists and self.bot.time - self.last_overseer_morph > 60:
                target = overlords.closest_to(self.bot.townhalls.first.position)
                try:
                    await self.bot.do(target(AbilityId.MORPH_OVERSEER))
                    self.last_overseer_morph = self.bot.time
                except Exception:
                    pass

    async def _move_scouts(self):
        for unit_tag, target_pos in list(self.scout_assignments.items()):
            unit = self.bot.units.find_by_tag(unit_tag)
            if not unit:
                self.scout_assignments.pop(unit_tag, None)
                continue
            if unit.is_idle or unit.is_moving:
                try:
                    await self.bot.do(unit.move(target_pos))
                except Exception:
                    pass

    def _compute_perimeter_points(self, center: Point2, ratio: float) -> List[Point2]:
        if not hasattr(self.bot, "game_info"):
            return []
        map_size = getattr(self.bot.game_info, "map_size", None)
        if not map_size:
            return []
        max_x, max_y = map_size
        radius_x = max_x * ratio
        radius_y = max_y * ratio
        points = []
        for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            points.append(Point2((center.x + dx * radius_x * 0.5, center.y + dy * radius_y * 0.5)))
        return points

    def _compute_drop_watch_points(self, base: Point2, enemy_start: Point2) -> List[Point2]:
        back = base.towards(enemy_start, -12.0)
        base_side = base.towards(enemy_start, -8.0)
        side1 = Point2((base_side.x + 6.0, base_side.y))
        side2 = Point2((base_side.x - 6.0, base_side.y))
        return [back, side1, side2]

    def _log_sensor_snapshot(self, iteration: int) -> None:
        if iteration - self.last_sensor_log < self.log_interval:
            return
        self.last_sensor_log = iteration
        game_time = getattr(self.bot, "time", 0.0)
        game_id = getattr(self.bot, "game_id", None) or "unknown"

        rows = []
        for unit_tag, target in self.scout_assignments.items():
            unit = self.bot.units.find_by_tag(unit_tag)
            if not unit:
                continue
            rows.append(
                {
                    "time": f"{game_time:.2f}",
                    "iteration": iteration,
                    "game_id": game_id,
                    "unit_tag": unit_tag,
                    "unit_type": getattr(unit.type_id, "name", str(unit.type_id)),
                    "pos_x": getattr(unit.position, "x", 0.0),
                    "pos_y": getattr(unit.position, "y", 0.0),
                    "target_x": getattr(target, "x", 0.0),
                    "target_y": getattr(target, "y", 0.0),
                }
            )

        if rows:
            try:
                csv_path = Path(self.sensor_csv_path)
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                write_header = not csv_path.exists()
                with csv_path.open("a", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            "time",
                            "iteration",
                            "game_id",
                            "unit_tag",
                            "unit_type",
                            "pos_x",
                            "pos_y",
                            "target_x",
                            "target_y",
                        ],
                    )
                    if write_header:
                        writer.writeheader()
                    writer.writerows(rows)
            except Exception:
                pass

            try:
                json_path = Path(self.sensor_json_path)
                json_path.parent.mkdir(parents=True, exist_ok=True)
                json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
            except Exception:
                pass
=======
Scouting System - Overlord sensor network and early warning.
"""

from typing import Dict, List, Optional

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:  # Fallbacks for tooling environments
    UnitTypeId = None
    AbilityId = None
    Point2 = None


class ScoutingSystem:
    """Manages overlord placement for vision and drop detection."""

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 22
        self.overlord_assignments: Dict[int, object] = {}
        self.cached_positions: List[object] = []
        self.last_creep_cast: Dict[int, float] = {}
        self.creep_cast_cooldown = 40.0
        self.retreat_until: Dict[int, float] = {}
        self.retreat_duration = 8.0
        self.retreat_radius = 9.0
        self.drop_threat_radius = 12.0
        self.danger_radius = 8.0
        self.drop_threat_types = set()
        if UnitTypeId:
            self.drop_threat_types = {
                UnitTypeId.MEDIVAC,
                UnitTypeId.WARPPRISM,
                UnitTypeId.WARPPRISMPHASING,
            }

    async def on_step(self, iteration: int) -> None:
        if not UnitTypeId or not hasattr(self.bot, "units"):
            return

        if iteration - self.last_update < self.update_interval:
            return

        self.last_update = iteration
        overlords = self.bot.units(UnitTypeId.OVERLORD).ready
        if not overlords:
            return

        self._refresh_positions()
        self._assign_overlords(overlords)
        await self._move_overlords(overlords)
        await self._generate_creep(overlords)

    def _refresh_positions(self) -> None:
        if self.cached_positions:
            return

        positions: List[object] = []
        playable = self._get_playable_bounds()
        if playable:
            left, right, bottom, top = playable
            mid_x = (left + right) / 2
            mid_y = (bottom + top) / 2

            offsets = 5.0
            edge_positions = [
                Point2((left + offsets, mid_y)),
                Point2((right - offsets, mid_y)),
                Point2((mid_x, bottom + offsets)),
                Point2((mid_x, top - offsets)),
                Point2((left + offsets, bottom + offsets)),
                Point2((left + offsets, top - offsets)),
                Point2((right - offsets, bottom + offsets)),
                Point2((right - offsets, top - offsets)),
            ]
            positions.extend(edge_positions)
            positions.extend(self._get_drop_lane_positions(playable))

        enemy_starts = getattr(self.bot, "enemy_start_locations", [])
        positions.extend(enemy_starts)

        townhalls = getattr(self.bot, "townhalls", None)
        if townhalls:
            for base in townhalls:
                positions.append(
                    base.position.towards(self.bot.game_info.map_center, 6)
                )

        self.cached_positions = self._dedupe_positions(positions)

    def _get_playable_bounds(self) -> Optional[tuple]:
        game_info = getattr(self.bot, "game_info", None)
        if not game_info:
            return None

        if hasattr(game_info, "playable_area"):
            area = game_info.playable_area
            left = area.x
            right = area.x + area.width
            bottom = area.y
            top = area.y + area.height
            return left, right, bottom, top

        if hasattr(game_info, "map_size"):
            size = game_info.map_size
            return 0.0, size.x, 0.0, size.y

        return None

    @staticmethod
    def _dedupe_positions(positions: List[object]) -> List[object]:
        if not Point2:
            return positions
        deduped = []
        for pos in positions:
            if not pos:
                continue
            if all(pos.distance_to(other) > 2.5 for other in deduped):
                deduped.append(pos)
        return deduped

    def _assign_overlords(self, overlords) -> None:
        if not self.cached_positions:
            return

        for overlord in overlords:
            if overlord.tag not in self.overlord_assignments:
                index = overlord.tag % len(self.cached_positions)
                self.overlord_assignments[overlord.tag] = self.cached_positions[index]

        valid_tags = {o.tag for o in overlords}
        self.overlord_assignments = {
            tag: pos
            for tag, pos in self.overlord_assignments.items()
            if tag in valid_tags
        }

    async def _move_overlords(self, overlords) -> None:
        actions = []
        enemy_units = getattr(self.bot, "enemy_units", [])
        current_time = getattr(self.bot, "time", 0.0)

        for overlord in overlords:
            if self._should_retreat(overlord, enemy_units, current_time):
                retreat_pos = self._get_retreat_position(overlord)
                if retreat_pos:
                    actions.append(overlord.move(retreat_pos))
                continue

            target = self.overlord_assignments.get(overlord.tag)
            if not target:
                continue

            target = self._offset_target(target, overlord.tag)
            if not self._is_position_safe(target, enemy_units):
                continue

            try:
                dist = overlord.distance_to(target)
            except Exception:
                dist = 0.0

            if dist > 3:
                actions.append(overlord.move(target))

        await self._do_actions(actions)

    def _is_position_safe(self, target, enemy_units) -> bool:
        if not enemy_units:
            return True
        try:
            for enemy in enemy_units:
                if enemy.distance_to(target) < self.danger_radius:
                    return False
        except Exception:
            return True
        return True

    def _should_retreat(self, overlord, enemy_units, current_time: float) -> bool:
        retreat_until = self.retreat_until.get(overlord.tag, 0.0)
        if current_time < retreat_until:
            return True

        nearest_enemy = None
        nearest_dist = None
        for enemy in enemy_units:
            try:
                dist = overlord.distance_to(enemy)
            except Exception:
                continue
            if nearest_dist is None or dist < nearest_dist:
                nearest_dist = dist
                nearest_enemy = enemy

        if nearest_dist is None:
            return False

        if nearest_dist < self.retreat_radius or (
            self._is_drop_threat(nearest_enemy)
            and nearest_dist < self.drop_threat_radius
        ):
            self.retreat_until[overlord.tag] = current_time + self.retreat_duration
            return True

        return False

    def _is_drop_threat(self, enemy) -> bool:
        if not self.drop_threat_types:
            return False
        return enemy.type_id in self.drop_threat_types

    def _get_retreat_position(self, overlord):
        if hasattr(self.bot, "townhalls") and self.bot.townhalls:
            try:
                return self.bot.townhalls.closest_to(overlord.position).position
            except Exception:
                return self.bot.townhalls.first.position
        if hasattr(self.bot, "game_info"):
            return self.bot.game_info.map_center
        return overlord.position

    def _offset_target(self, target, tag: int):
        if not Point2:
            return target
        offset = (tag % 5) - 2
        return Point2((target.x + offset * 1.5, target.y + offset * 1.5))

    def _get_drop_lane_positions(self, playable) -> List[object]:
        if not Point2 or not playable:
            return []
        left, right, bottom, top = playable
        mid_x = (left + right) / 2
        mid_y = (bottom + top) / 2
        margin = 8.0
        thirds_x = [left + margin, mid_x, right - margin]
        thirds_y = [bottom + margin, mid_y, top - margin]

        positions = []
        for x in thirds_x:
            positions.append(Point2((x, bottom + margin)))
            positions.append(Point2((x, top - margin)))
        for y in thirds_y:
            positions.append(Point2((left + margin, y)))
            positions.append(Point2((right - margin, y)))

        return positions

    async def _generate_creep(self, overlords) -> None:
        if not AbilityId:
            return

        creep_ability = getattr(AbilityId, "GENERATECREEP_GENERATECREEP", None)
        if creep_ability is None:
            creep_ability = getattr(AbilityId, "GENERATECREEP", None)

        if creep_ability is None:
            return

        actions = []
        current_time = getattr(self.bot, "time", 0.0)

        for overlord in overlords:
            target = self.overlord_assignments.get(overlord.tag)
            if not target:
                continue

            last_cast = self.last_creep_cast.get(overlord.tag, 0.0)
            if current_time - last_cast < self.creep_cast_cooldown:
                continue

            try:
                if overlord.distance_to(target) > 2:
                    continue
            except Exception:
                continue

            if hasattr(overlord, "is_idle") and not overlord.is_idle:
                continue

            actions.append(overlord(creep_ability))
            self.last_creep_cast[overlord.tag] = current_time

        await self._do_actions(actions)

    async def _do_actions(self, actions: List) -> None:
        if not actions:
            return
        if hasattr(self.bot, "do_actions"):
            await self.bot.do_actions(actions)
        else:
            for action in actions:
                await self.bot.do(action)
>>>>>>> Incoming (Background Agent changes)
