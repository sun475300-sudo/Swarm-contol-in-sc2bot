#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creep Manager - vector-driven creep expansion targeting with tumor relay.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:  # Fallbacks for tooling environments
    Point2 = None
    AbilityId = None
    UnitTypeId = None


class CreepManager:
    """
    Manages creep spread through queens and automatic tumor relay.

    Features:
    - Vector-driven targeting toward enemy base
    - Automatic tumor relay from outermost tumors
    - Prioritizes map center and attack paths
    """

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 12  # 개선: 16 → 12 (더 자주 업데이트)
        self.tumor_relay_interval = 8  # 개선: 12 → 8 (더 빠른 종양 릴레이)
        self.last_tumor_relay = 0
        self.cached_targets: List[object] = []
        self.tumor_spread_cooldowns: Dict[int, int] = {}  # tumor_tag -> last_spread_frame
        self.max_tumors_per_cycle = 4  # 개선: 3 → 4 (한 번에 더 많은 종양 확장)
        self.spread_directions = []  # 확장 방향 캐시
        self._tumor_count_check_interval = 0

    async def on_step(self, iteration: int) -> None:
        """
        Main creep manager loop.
        - Refreshes creep targets periodically
        - Handles automatic tumor relay
        - Tracks creep spread progress
        """
        if iteration - self.last_update < self.update_interval:
            if iteration - self.last_tumor_relay >= self.tumor_relay_interval:
                await self._handle_tumor_relay(iteration)
            return

        self.last_update = iteration
        self._refresh_targets()
        await self._handle_tumor_relay(iteration)

        # 점막 확장 진행 상황 로그 (30초마다)
        self._tumor_count_check_interval += 1
        if self._tumor_count_check_interval >= 50:  # ~30초마다
            self._tumor_count_check_interval = 0
            await self._log_creep_progress(iteration)

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

    async def _handle_tumor_relay(self, iteration: int) -> None:
        """
        ★ 개선: 자동 종양 릴레이 시스템 (과도한 확장 방지)

        조건:
        - 종양 수 35개 이하만 작동
        - 가장 바깥 종양만 확장
        """
        if not UnitTypeId or not AbilityId:
            return

        self.last_tumor_relay = iteration

        # Get all creep tumors (both burrowed and active)
        tumors = []
        if hasattr(self.bot, "structures"):
            tumors = [
                t
                for t in self.bot.structures
                if t.type_id
                in {
                    UnitTypeId.CREEPTUMOR,
                    UnitTypeId.CREEPTUMORBURROWED,
                    UnitTypeId.CREEPTUMORQUEEN,
                }
            ]

        if not tumors:
            return

        # ★ 종양 수 제한 (35개 이상이면 릴레이 중지)
        if len(tumors) >= 35:
            return

        # Clean up old cooldowns
        tumor_tags = {t.tag for t in tumors}
        self.tumor_spread_cooldowns = {
            tag: frame
            for tag, frame in self.tumor_spread_cooldowns.items()
            if tag in tumor_tags
        }

        # Get target direction
        direction_target = self._get_direction_target()
        if not direction_target:
            return

        # Find outermost tumors (farthest from our base, closest to enemy)
        our_base = None
        if hasattr(self.bot, "townhalls") and self.bot.townhalls:
            our_base = self.bot.townhalls.first.position

        if not our_base:
            return

        # Score tumors by distance to enemy
        scored_tumors = []
        for tumor in tumors:
            # Skip if on cooldown (spread within last 50 frames)
            last_spread = self.tumor_spread_cooldowns.get(tumor.tag, 0)
            if iteration - last_spread < 50:
                continue

            try:
                dist_to_enemy = tumor.position.distance_to(direction_target)
                dist_to_base = tumor.position.distance_to(our_base)
                # Prefer tumors far from base and close to enemy
                score = dist_to_base - dist_to_enemy * 0.5
                scored_tumors.append((tumor, score))
            except Exception:
                continue

        if not scored_tumors:
            return

        # Sort by score (highest first) and spread top tumors
        scored_tumors.sort(key=lambda x: x[1], reverse=True)
        actions = []

        # 개선: 최대 4개 종양 확장 (적 방향 + 확장 방향)
        for tumor, _ in scored_tumors[:self.max_tumors_per_cycle]:
            try:
                # Calculate spread target toward enemy
                spread_target = tumor.position.towards(direction_target, 9.0)

                # Check if tumor can spread (has ability)
                if hasattr(tumor, "can_cast") and hasattr(
                    AbilityId, "BUILD_CREEPTUMOR_TUMOR"
                ):
                    if tumor.can_cast(AbilityId.BUILD_CREEPTUMOR_TUMOR):
                        actions.append(
                            tumor(AbilityId.BUILD_CREEPTUMOR_TUMOR, spread_target)
                        )
                        self.tumor_spread_cooldowns[tumor.tag] = iteration
                elif hasattr(AbilityId, "BUILD_CREEPTUMOR_TUMOR"):
                    actions.append(
                        tumor(AbilityId.BUILD_CREEPTUMOR_TUMOR, spread_target)
                    )
                    self.tumor_spread_cooldowns[tumor.tag] = iteration
            except Exception:
                continue

        if actions:
            try:
                if hasattr(self.bot, "do_actions"):
                    result = self.bot.do_actions(actions)
                    if hasattr(result, "__await__"):
                        await result
                else:
                    for action in actions:
                        result = self.bot.do(action)
                        if hasattr(result, "__await__"):
                            await result
            except Exception:
                pass

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

    async def _log_creep_progress(self, iteration: int) -> None:
        """점막 확장 진행 상황 로그"""
        if not UnitTypeId or not hasattr(self.bot, "structures"):
            return

        try:
            game_time = getattr(self.bot, "time", 0)

            # 종양 수 카운트
            tumor_types = {
                UnitTypeId.CREEPTUMOR,
                UnitTypeId.CREEPTUMORBURROWED,
                UnitTypeId.CREEPTUMORQUEEN,
            }
            tumors = [
                t for t in self.bot.structures
                if t.type_id in tumor_types
            ]
            tumor_count = len(tumors)

            # 가장 먼 종양 위치 (적 방향 기준)
            farthest_dist = 0
            if tumors and hasattr(self.bot, "townhalls") and self.bot.townhalls:
                our_base = self.bot.townhalls.first.position
                for tumor in tumors:
                    try:
                        dist = tumor.position.distance_to(our_base)
                        if dist > farthest_dist:
                            farthest_dist = dist
                    except Exception:
                        continue

            print(f"[CREEP] [{int(game_time)}s] Tumors: {tumor_count}, Farthest: {int(farthest_dist)} from base")

        except Exception:
            pass

    def get_tumor_count(self) -> int:
        """현재 종양 수 반환"""
        if not UnitTypeId or not hasattr(self.bot, "structures"):
            return 0

        tumor_types = {
            UnitTypeId.CREEPTUMOR,
            UnitTypeId.CREEPTUMORBURROWED,
            UnitTypeId.CREEPTUMORQUEEN,
        }
        return sum(1 for t in self.bot.structures if t.type_id in tumor_types)
