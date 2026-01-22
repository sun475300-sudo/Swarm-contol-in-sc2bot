#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
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
