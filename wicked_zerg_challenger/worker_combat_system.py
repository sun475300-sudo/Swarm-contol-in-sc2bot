# -*- coding: utf-8 -*-
"""
Worker Combat System - 일꾼 전투 시스템

초반 위협(12저글링, 광자포, 일꾼 러시) 대응:
- 도망만 가는 대신 전투 모드로 전환
- 포위 공격(Surround) 실행
- 드릴 마이크로(Hit & Run)
- 적이 물러나면 다시 채광으로 복귀
"""

from typing import Set, Optional, Dict
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from utils.logger import get_logger


class WorkerCombatSystem:
    """
    일꾼 전투 시스템

    기능:
    1. 초반 위협 감지 (적 전투 유닛이 미네랄 라인 근처)
    2. 전투 모드 활성화 (방어 건물이 없을 때)
    3. 포위 공격 (Surround Attack)
    4. 드릴 마이크로 (Hit & Run)
    5. 위협 제거 후 자동 복귀
    """

    # 위협으로 간주할 유닛 타입
    EARLY_THREATS = {
        UnitTypeId.ZERGLING,
        UnitTypeId.ZEALOT,
        UnitTypeId.MARINE,
        UnitTypeId.PROBE,
        UnitTypeId.SCV,
        UnitTypeId.DRONE,
        UnitTypeId.PHOTONCANNON,
        UnitTypeId.SPINECRAWLER,
    }

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("WorkerCombat")

        # 전투 모드 상태
        self.combat_mode = False
        self.combat_workers: Set[int] = set()  # 전투 중인 일꾼 태그
        self.last_threat_time = 0.0

        # 포위 공격 설정
        self.surround_distance = 1.5  # 포위 거리
        self.engagement_range = 12.0  # 전투 시작 범위
        self.retreat_hp_threshold = 0.3  # 30% HP 이하면 후퇴

        # 드릴 마이크로 설정
        self.drill_attack_cooldown = 0.5  # 공격 후 대기 시간
        self.worker_attack_timings: Dict[int, float] = {}  # 일꾼별 마지막 공격 시간

        # 위협 해제 조건
        self.combat_mode_cooldown = 5.0  # 위협 사라진 후 5초 대기

    async def on_step(self) -> None:
        """매 프레임 실행"""
        if not self.bot.townhalls:
            return

        # 1. 위협 감지
        threats = self._detect_threats()

        # 2. 전투 모드 전환 판단
        if threats:
            self._activate_combat_mode(threats)
        else:
            self._deactivate_combat_mode()

        # 3. 전투 모드 실행
        if self.combat_mode:
            await self._execute_combat_mode(threats)

    def _detect_threats(self) -> Units:
        """초반 위협 감지"""
        if not self.bot.townhalls:
            return Units([], self.bot)

        all_threats = Units([], self.bot)

        # 각 본진/확장 기지 근처 위협 탐지
        for base in self.bot.townhalls.ready:
            nearby_enemies = self.bot.enemy_units.filter(
                lambda u: u.type_id in self.EARLY_THREATS
                and u.position.distance_to(base.position) < self.engagement_range
            )
            all_threats.extend(nearby_enemies)

        return all_threats

    def _activate_combat_mode(self, threats: Units) -> None:
        """전투 모드 활성화"""
        # 방어 건물이 충분하면 일꾼 전투 불필요
        spine_crawlers = self.bot.structures(UnitTypeId.SPINECRAWLER).ready.amount
        if spine_crawlers >= 2:
            return

        # 방어 유닛이 충분하면 일꾼 전투 불필요
        combat_units = self.bot.units.filter(
            lambda u: u.type_id in {UnitTypeId.ZERGLING, UnitTypeId.ROACH, UnitTypeId.QUEEN}
        )
        if combat_units.amount >= 6:
            return

        if not self.combat_mode:
            self.combat_mode = True
            self.logger.info(f"[WORKER_COMBAT] 전투 모드 활성화! 위협: {threats.amount}개")

        self.last_threat_time = self.bot.time

    def _deactivate_combat_mode(self) -> None:
        """전투 모드 비활성화"""
        # 위협이 사라진 후 일정 시간 대기
        if self.combat_mode:
            time_since_threat = self.bot.time - self.last_threat_time
            if time_since_threat > self.combat_mode_cooldown:
                self.combat_mode = False
                self.combat_workers.clear()
                self.logger.info(f"[WORKER_COMBAT] 전투 모드 해제")

    async def _execute_combat_mode(self, threats: Units) -> None:
        """전투 모드 실행"""
        if not threats:
            return

        # 가장 가까운 위협 선택
        closest_threat = threats.closest_to(self.bot.start_location)

        # 전투 가능한 일꾼 모집 (HP 높은 순)
        available_workers = self.bot.workers.filter(
            lambda w: w.health_percentage > self.retreat_hp_threshold
        ).sorted(lambda w: w.health, reverse=True)

        if not available_workers:
            return

        # 위협 수에 따라 동원할 일꾼 수 결정
        worker_count = min(len(available_workers), max(6, threats.amount * 2))
        combat_workers = available_workers[:worker_count]

        # 포위 공격 실행
        await self._execute_surround_attack(combat_workers, closest_threat)

        # 부상당한 일꾼 후퇴
        await self._retreat_wounded_workers()

    async def _execute_surround_attack(self, workers: Units, target: Unit) -> None:
        """포위 공격 실행"""
        if not workers or not target:
            return

        # 포위 위치 계산
        surround_positions = self._calculate_surround_positions(
            target.position,
            len(workers),
            self.surround_distance
        )

        current_time = self.bot.time

        for i, worker in enumerate(workers):
            self.combat_workers.add(worker.tag)

            # 드릴 마이크로: 쿨다운 체크
            last_attack = self.worker_attack_timings.get(worker.tag, 0)
            can_attack = (current_time - last_attack) > self.drill_attack_cooldown

            # 타겟과의 거리
            distance_to_target = worker.position.distance_to(target.position)

            if distance_to_target <= worker.ground_range + 0.5:
                # 사거리 내: 공격
                if can_attack:
                    worker.attack(target)
                    self.worker_attack_timings[worker.tag] = current_time
                else:
                    # 쿨다운 중: 잠시 뒤로 물러남 (드릴 마이크로)
                    retreat_pos = worker.position.towards(target.position, -1.5)
                    worker.move(retreat_pos)
            else:
                # 사거리 밖: 포위 위치로 이동
                if i < len(surround_positions):
                    target_pos = surround_positions[i]
                    worker.move(target_pos)
                else:
                    # 포위 위치가 부족하면 직접 접근
                    worker.attack(target)

    def _calculate_surround_positions(
        self,
        center: Point2,
        count: int,
        radius: float
    ) -> list[Point2]:
        """포위 위치 계산 (원형 배치)"""
        import math
        positions = []

        angle_step = 2 * math.pi / max(count, 1)

        for i in range(count):
            angle = i * angle_step
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            positions.append(Point2((x, y)))

        return positions

    async def _retreat_wounded_workers(self) -> None:
        """부상당한 일꾼 후퇴"""
        wounded = self.bot.workers.filter(
            lambda w: w.tag in self.combat_workers
            and w.health_percentage < self.retreat_hp_threshold
        )

        for worker in wounded:
            # 가장 가까운 본진으로 후퇴
            if self.bot.townhalls:
                nearest_base = self.bot.townhalls.closest_to(worker.position)
                # 본진 뒤쪽으로 이동
                retreat_pos = nearest_base.position.towards(
                    self.bot.game_info.map_center,
                    -3
                )
                worker.move(retreat_pos)

            # 전투 목록에서 제거
            self.combat_workers.discard(worker.tag)

    def force_workers_to_minerals(self) -> None:
        """모든 전투 일꾼을 강제로 채광 복귀"""
        for worker_tag in list(self.combat_workers):
            worker = self.bot.workers.find_by_tag(worker_tag)
            if worker:
                # 가장 가까운 미네랄로 복귀
                if self.bot.townhalls:
                    nearest_base = self.bot.townhalls.closest_to(worker.position)
                    minerals = self.bot.mineral_field.closer_than(10, nearest_base)
                    if minerals:
                        worker.gather(minerals.closest_to(worker))

        self.combat_workers.clear()
        self.combat_mode = False
