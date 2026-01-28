# -*- coding: utf-8 -*-
"""
Destructible Awareness System - 파괴 가능 구조물 인지 시스템

맵의 파괴 가능한 구조물 감지 및 처리:
1. Destructible Rocks/Debris 감지
2. 확장 경로 차단 시 파괴
3. 전략적 위치 파괴 (적 견제용)
4. 우선순위 결정 (중요도)
"""

from typing import List, Dict, Optional, Set
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger


class DestructibleStructure:
    """파괴 가능한 구조물 정보"""

    def __init__(self, unit, priority: int = 0):
        self.unit = unit
        self.position = unit.position
        self.priority = priority
        self.is_destroyed = False
        self.blocks_expansion = False
        self.blocks_main_path = False


class DestructibleAwarenessSystem:
    """
    파괴 가능 구조물 인지 시스템

    맵의 파괴 가능한 구조물을 감지하고 필요시 파괴합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("DestructibleAware")

        # 파괴 가능 구조물 추적
        self.destructibles: Dict[int, DestructibleStructure] = {}
        self.destruction_queue: List[int] = []  # 파괴 우선순위 큐

        # 설정
        self.EXPANSION_BLOCK_RADIUS = 8  # 확장 차단 판정 반경
        self.MAIN_PATH_RADIUS = 15  # 주요 경로 판정 반경

        # 파괴 가능한 타입들
        self.DESTRUCTIBLE_TYPES = {
            UnitTypeId.DESTRUCTIBLEROCKEX1DIAGONALHUGEBLBUR,
            UnitTypeId.DESTRUCTIBLEROCK6X6,
            UnitTypeId.DESTRUCTIBLEDEBRIS6X6,
            UnitTypeId.DESTRUCTIBLEDEBRISRAMPDIAGONALHUGEBLUR,
            UnitTypeId.UNBUILDABLEPLATESDESTRUCTIBLE,
            UnitTypeId.UNBUILDABLEBRICKSDESTRUCTIBLE,
        }

        # 통계
        self.total_discovered = 0
        self.total_destroyed = 0

    async def on_start(self):
        """게임 시작 시 실행"""
        await self._discover_all_destructibles()

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 주기적 업데이트 (10초마다)
            if iteration % 220 == 0:
                await self._update_destructibles()
                await self._evaluate_priorities()

            # 파괴 실행 (5초마다)
            if iteration % 110 == 0 and self.destruction_queue:
                await self._execute_destruction()

            # 디버그 출력
            if iteration % 440 == 0 and self.destructibles:  # 20초마다
                self._print_status()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[DESTRUCTIBLE] Error: {e}")

    async def _discover_all_destructibles(self):
        """모든 파괴 가능 구조물 발견"""
        try:
            # 중립 유닛에서 파괴 가능 구조물 찾기
            all_units = self.bot.all_units

            for unit in all_units:
                if self._is_destructible(unit):
                    if unit.tag not in self.destructibles:
                        self.destructibles[unit.tag] = DestructibleStructure(unit)
                        self.total_discovered += 1

            if self.total_discovered > 0:
                self.logger.info(
                    f"[MAP_SCAN] Discovered {self.total_discovered} destructible structures"
                )

        except Exception as e:
            self.logger.error(f"[DESTRUCTIBLE] Discovery error: {e}")

    def _is_destructible(self, unit) -> bool:
        """파괴 가능한 구조물인지 확인"""
        # 타입으로 확인
        if hasattr(unit, 'type_id') and unit.type_id in self.DESTRUCTIBLE_TYPES:
            return True

        # 이름으로 확인 (폴백)
        if hasattr(unit, 'name'):
            name_lower = unit.name.lower()
            if any(keyword in name_lower for keyword in [
                'destructible', 'rock', 'debris', 'unbuildable'
            ]):
                return True

        return False

    async def _update_destructibles(self):
        """파괴 가능 구조물 상태 업데이트"""
        # 파괴된 구조물 제거
        destroyed_tags = []

        for tag, destructible in self.destructibles.items():
            # 유닛이 더 이상 존재하지 않으면 파괴됨
            exists = False
            for unit in self.bot.all_units:
                if unit.tag == tag:
                    exists = True
                    break

            if not exists and not destructible.is_destroyed:
                destructible.is_destroyed = True
                destroyed_tags.append(tag)
                self.total_destroyed += 1
                self.logger.info(
                    f"[DESTROYED] Destructible at {destructible.position} destroyed "
                    f"({self.total_destroyed}/{self.total_discovered})"
                )

        # 파괴된 것들 제거
        for tag in destroyed_tags:
            if tag in self.destructibles:
                del self.destructibles[tag]
            if tag in self.destruction_queue:
                self.destruction_queue.remove(tag)

    async def _evaluate_priorities(self):
        """파괴 우선순위 평가"""
        expansion_locations = list(self.bot.expansion_locations_list)

        for tag, destructible in self.destructibles.items():
            if destructible.is_destroyed:
                continue

            priority = 0

            # 1. 확장 경로 차단 여부 (최우선)
            for exp_loc in expansion_locations:
                if destructible.position.distance_to(exp_loc) < self.EXPANSION_BLOCK_RADIUS:
                    destructible.blocks_expansion = True
                    priority += 100
                    break

            # 2. 본진-확장 경로 차단 여부
            if self.bot.townhalls.amount > 0:
                main_base = self.bot.townhalls.first.position
                for townhall in self.bot.townhalls:
                    path_center = (main_base + townhall.position) / 2
                    if destructible.position.distance_to(path_center) < self.MAIN_PATH_RADIUS:
                        destructible.blocks_main_path = True
                        priority += 50
                        break

            # 3. 적 본진 근처 (견제용)
            if self.bot.enemy_start_locations:
                enemy_base = self.bot.enemy_start_locations[0]
                distance_to_enemy = destructible.position.distance_to(enemy_base)
                if distance_to_enemy < 20:
                    priority += 30

            destructible.priority = priority

        # 우선순위 큐 업데이트
        self.destruction_queue = sorted(
            [tag for tag, d in self.destructibles.items() if not d.is_destroyed],
            key=lambda t: self.destructibles[t].priority,
            reverse=True
        )

    async def _execute_destruction(self):
        """파괴 실행"""
        if not self.destruction_queue:
            return

        # 가장 높은 우선순위 구조물
        target_tag = self.destruction_queue[0]
        target = self.destructibles.get(target_tag)

        if not target or target.is_destroyed:
            return

        # 우선순위가 50 이상일 때만 파괴 (중요한 것만)
        if target.priority < 50:
            return

        # 근처에 공격 가능한 유닛 찾기
        attacking_units = self.bot.units.filter(
            lambda u: u.can_attack_ground and
            u.distance_to(target.position) < 30 and
            u.type_id not in {UnitTypeId.DRONE, UnitTypeId.OVERLORD}
        )

        if not attacking_units:
            # 유닛이 없으면 일꾼 사용
            workers = self.bot.workers
            if workers:
                worker = workers.closest_to(target.position)
                if worker.distance_to(target.position) < 50:
                    # 일꾼 5명 정도 보내기
                    workers_to_send = workers.closest_n_units(target.position, 5)
                    for w in workers_to_send:
                        self.bot.do(w.attack(target.position))

                    reason = "blocks expansion" if target.blocks_expansion else "blocks path"
                    self.logger.info(
                        f"[DESTROY] Sending {len(workers_to_send)} workers to destroy "
                        f"structure at {target.position} ({reason})"
                    )
            return

        # 공격 유닛 사용
        attackers = attacking_units.take(3)  # 3유닛만
        for unit in attackers:
            self.bot.do(unit.attack(target.position))

        reason = "blocks expansion" if target.blocks_expansion else "blocks path"
        self.logger.info(
            f"[DESTROY] Sending {attackers.amount} units to destroy "
            f"structure at {target.position} ({reason}, priority: {target.priority})"
        )

    def _print_status(self):
        """상태 출력"""
        active_count = len([d for d in self.destructibles.values() if not d.is_destroyed])

        if active_count > 0:
            high_priority = len([
                d for d in self.destructibles.values()
                if not d.is_destroyed and d.priority >= 50
            ])

            self.logger.info(
                f"[DESTRUCTIBLE_STATUS] "
                f"Active: {active_count}, High Priority: {high_priority}, "
                f"Destroyed: {self.total_destroyed}/{self.total_discovered}"
            )

    def get_statistics(self) -> Dict:
        """통계 반환"""
        active = len([d for d in self.destructibles.values() if not d.is_destroyed])
        blocks_expansion = len([
            d for d in self.destructibles.values()
            if not d.is_destroyed and d.blocks_expansion
        ])

        return {
            "total_discovered": self.total_discovered,
            "total_destroyed": self.total_destroyed,
            "active": active,
            "blocks_expansion": blocks_expansion,
            "destruction_queue_size": len(self.destruction_queue)
        }
