#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creep Manager - vector-driven creep expansion targeting.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

try:
    from sc2.position import Point2
except ImportError:  # Fallbacks for tooling environments
    Point2 = None


class CreepManager:
    """Computes creep tumor targets using map, scout, and expansion data."""

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 22
        self.cached_targets: List[object] = []

    async def on_step(self, iteration: int) -> None:
        if iteration - self.last_update < self.update_interval:
            return
        self.last_update = iteration
        self._refresh_targets()

    def get_creep_target(self, origin_unit) -> Optional[object]:
        if not self.cached_targets:
            self._refresh_targets()

        direction_target = self._get_direction_target()
        origin = getattr(origin_unit, "position", None)
        if not origin or not Point2:
            return None

        if direction_target and self.cached_targets:
            scored = max(
                self.cached_targets,
                key=lambda pos: self._score_target(origin, pos, direction_target),
            )
            return scored

        if direction_target:
            return origin.towards(direction_target, 7)

        return None

    def _refresh_targets(self) -> None:
        targets: List[object] = []
        targets.extend(self._get_expansion_targets())
        targets.extend(self._get_scout_targets())
        targets.extend(self._get_attack_path_targets())
        self.cached_targets = self._dedupe_positions(targets)

    def _get_direction_target(self) -> Optional[object]:
        enemy_starts = getattr(self.bot, "enemy_start_locations", [])
        if enemy_starts:
            return enemy_starts[0]
        if hasattr(self.bot, "game_info"):
            return self.bot.game_info.map_center
        return None

    def _get_expansion_targets(self) -> List[object]:
        expansion_list = getattr(self.bot, "expansion_locations_list", None)
        if not expansion_list:
            return []
        return list(expansion_list)

    def _get_scout_targets(self) -> List[object]:
        scout = getattr(self.bot, "scout", None)
        if not scout:
            return []
        targets: List[object] = []
        targets.extend(getattr(scout, "cached_positions", []))
        assignments = getattr(scout, "overlord_assignments", {})
        targets.extend(assignments.values())
        return targets

    def _get_attack_path_targets(self) -> List[object]:
        if not Point2:
            return []
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return []
        origin = self.bot.townhalls.first.position
        target = self._get_direction_target()
        if not target:
            return []
        path = []
        distance = origin.distance_to(target)
        step = 8.0
        current = origin
        traveled = 0.0
        while traveled + step < distance:
            current = current.towards(target, step)
            path.append(current)
            traveled += step
            if len(path) >= 6:
                break
        return path

    @staticmethod
    def _dedupe_positions(positions: Iterable[object]) -> List[object]:
        if not Point2:
            return list(positions)
        deduped: List[object] = []
        for pos in positions:
            if not pos:
                continue
            if all(pos.distance_to(other) > 2.5 for other in deduped):
                deduped.append(pos)
        return deduped

    @staticmethod
    def _score_target(origin, candidate, direction_target) -> float:
        dx = candidate.x - origin.x
        dy = candidate.y - origin.y
        dist = (dx * dx + dy * dy) ** 0.5

        dir_x = direction_target.x - origin.x
        dir_y = direction_target.y - origin.y
        dir_len = (dir_x * dir_x + dir_y * dir_y) ** 0.5
        if dir_len == 0:
            return dist
        dir_x /= dir_len
        dir_y /= dir_len
        projection = dx * dir_x + dy * dir_y
        return projection - dist * 0.15
