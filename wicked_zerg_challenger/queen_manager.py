# -*- coding: utf-8 -*-
"""
Queen Manager - production, inject, and creep spread.

Focused on keeping queen output reliable without unnecessary gas checks.
"""

from typing import Dict, Optional, Set

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallbacks for tooling environments

    class UnitTypeId:
        QUEEN = "QUEEN"
        HATCHERY = "HATCHERY"
        LAIR = "LAIR"
        HIVE = "HIVE"

    class AbilityId:
        EFFECT_INJECTLARVA = "EFFECT_INJECTLARVA"
        BUILD_CREEPTUMOR_QUEEN = "BUILD_CREEPTUMOR_QUEEN"


class QueenManager:
    """Controls queen production and basic support abilities."""

    def __init__(self, bot):
        self.bot = bot
        self.inject_energy_threshold = 25
        self.creep_energy_threshold = 25
        self.creep_spread_cooldown = 30.0
        self.max_queens_per_base = 1
        self.last_creep_time: Dict[int, float] = {}
        self.creep_queen_bonus = 1
        self.inject_assignments: Dict[int, int] = {}
        self.assigned_queen_tags: Set[int] = set()

    async def on_step(self, iteration: int) -> None:
        """Main queen management loop."""
        if not hasattr(self.bot, "time"):
            return

        await self._train_queens()

        queens = (
            self.bot.units(UnitTypeId.QUEEN).ready if hasattr(self.bot, "units") else []
        )
        hatcheries = self.bot.townhalls.ready if hasattr(self.bot, "townhalls") else []
        if not queens or not hatcheries:
            return

        self._assign_queen_roles(queens, hatcheries)
        await self._inject_larva(hatcheries, queens)
        creep_queens = [q for q in queens if q.tag not in self.assigned_queen_tags]
        await self._spread_creep(creep_queens)

    async def _train_queens(self) -> None:
        if not hasattr(self.bot, "townhalls"):
            return

        hatcheries = self.bot.townhalls.ready
        if not hatcheries:
            return

        queens = (
            self.bot.units(UnitTypeId.QUEEN).ready if hasattr(self.bot, "units") else []
        )
        creep_bonus = self.creep_queen_bonus if hatcheries.amount >= 2 else 0
        desired = max(1, hatcheries.amount * self.max_queens_per_base + creep_bonus)

        if len(queens) >= desired:
            return

        pending = (
            self.bot.already_pending(UnitTypeId.QUEEN)
            if hasattr(self.bot, "already_pending")
            else 0
        )
        for hatch in hatcheries:
            if len(queens) + pending >= desired:
                break

            if hasattr(hatch, "noqueue") and not hatch.noqueue:
                continue

            # Queens cost minerals only; no gas gate needed.
            if not self.bot.can_afford(UnitTypeId.QUEEN):
                break

            try:
                await self.bot.do(hatch.train(UnitTypeId.QUEEN))
                pending += 1
            except Exception:
                continue

    def _assign_queen_roles(self, queens, hatcheries) -> None:
        """Assign inject queens per hatchery and track creep queens."""
        current_queen_tags = {q.tag for q in queens}
        current_hatch_tags = {h.tag for h in hatcheries}

        self.inject_assignments = {
            hatch_tag: queen_tag
            for hatch_tag, queen_tag in self.inject_assignments.items()
            if hatch_tag in current_hatch_tags and queen_tag in current_queen_tags
        }

        assigned_queens = set(self.inject_assignments.values())
        for hatch in hatcheries:
            if hatch.tag in self.inject_assignments:
                continue

            candidate = self._find_closest_queen(
                hatch.position, queens, assigned_queens
            )
            if candidate:
                self.inject_assignments[hatch.tag] = candidate.tag
                assigned_queens.add(candidate.tag)

        self.assigned_queen_tags = assigned_queens

    @staticmethod
    def _find_closest_queen(position, queens, excluded_tags: Set[int]):
        candidates = [q for q in queens if q.tag not in excluded_tags]
        if not candidates:
            return None
        try:
            return min(candidates, key=lambda q: q.distance_to(position))
        except Exception:
            return candidates[0]

    @staticmethod
    def _find_queen_by_tag(queens, queen_tag: Optional[int]):
        if queen_tag is None:
            return None
        for queen in queens:
            if queen.tag == queen_tag:
                return queen
        return None

    async def _inject_larva(self, hatcheries, queens) -> None:
        for hatch in hatcheries:
            if not hatch:
                continue

            queen = self._find_queen_by_tag(
                queens, self.inject_assignments.get(hatch.tag)
            )
            if not queen:
                try:
                    queen = queens.closest_to(hatch.position)
                except Exception:
                    continue

            if not queen:
                continue

            if getattr(queen, "energy", 0) < self.inject_energy_threshold:
                continue

            if hasattr(queen, "distance_to") and queen.distance_to(hatch) > 4:
                continue

            try:
                if hasattr(queen, "can_cast"):
                    if queen.can_cast(AbilityId.EFFECT_INJECTLARVA):
                        await self.bot.do(queen(AbilityId.EFFECT_INJECTLARVA, hatch))
                else:
                    await self.bot.do(queen(AbilityId.EFFECT_INJECTLARVA, hatch))
            except Exception:
                continue

    async def _spread_creep(self, creep_queens) -> None:
        current_time = getattr(self.bot, "time", 0.0)

        for queen in creep_queens:
            last_time = self.last_creep_time.get(queen.tag, 0.0)
            if current_time - last_time < self.creep_spread_cooldown:
                continue

            if getattr(queen, "energy", 0) < self.creep_energy_threshold:
                continue

            if hasattr(queen, "is_idle") and not queen.is_idle:
                continue

            try:
                target = self._get_creep_target_position(queen)

                if hasattr(queen, "can_cast"):
                    if queen.can_cast(AbilityId.BUILD_CREEPTUMOR_QUEEN):
                        await self.bot.do(
                            queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, target)
                        )
                        self.last_creep_time[queen.tag] = current_time
                else:
                    await self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, target))
                    self.last_creep_time[queen.tag] = current_time
            except Exception:
                continue

    def _get_creep_target_position(self, queen):
        """Pick a creep spread target along the main attack path."""
        creep_manager = getattr(self.bot, "creep_manager", None)
        if creep_manager:
            try:
                target = creep_manager.get_creep_target(queen)
                if target:
                    return target
            except Exception:
                pass

        enemy_starts = getattr(self.bot, "enemy_start_locations", [])
        origin = queen.position

        direction_target = None
        if enemy_starts:
            direction_target = enemy_starts[0]
        elif hasattr(self.bot, "game_info"):
            direction_target = self.bot.game_info.map_center

        candidates = self._collect_creep_targets()
        if direction_target and candidates:
            best = max(
                candidates,
                key=lambda pos: self._score_creep_target(origin, pos, direction_target),
            )
            return best

        if direction_target:
            return origin.towards(direction_target, 7)

        return origin.towards(origin, 3)

    def _collect_creep_targets(self):
        positions = []
        scout = getattr(self.bot, "scout", None)
        if scout:
            positions.extend(getattr(scout, "cached_positions", []))
            assignments = getattr(scout, "overlord_assignments", {})
            positions.extend(assignments.values())

        expansion_list = getattr(self.bot, "expansion_locations_list", None)
        if expansion_list:
            positions.extend(expansion_list)

        return [pos for pos in positions if pos]

    @staticmethod
    def _score_creep_target(origin, candidate, direction_target) -> float:
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
        return projection + dist * 0.25
