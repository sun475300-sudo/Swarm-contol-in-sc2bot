# -*- coding: utf-8 -*-
"""
Early Defense System - 초반 방어 시스템

목적: 초반 러시 대응 및 초기 생존율 향상
- 1-3분 사이 생존율 극대화
- 초반 러시 감지 및 즉시 대응
- 초기 유닛 생산 우선순위 관리
"""

from typing import Optional, Set
try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        pass
    class AbilityId:
        pass
    class Point2:
        pass


class EarlyDefenseSystem:
    """
    초반 방어 시스템 (0-3분)

    주요 기능:
    1. 초반 적 유닛 감지 및 경보
    2. 초기 Zergling 긴급 생산
    3. 일꾼 자동 대피/방어
    4. Queen 우선 생산
    5. Spawning Pool 우선 건설
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.early_game_threshold = 180.0  # 3분 = 180초
        self.early_rush_detected = False
        self.pool_started = False
        self.queen_started = False
        self.emergency_mode = False
        self.last_enemy_check = 0

        # 초반 위협 감지
        self.early_threats: Set = set()

    async def execute(self, iteration: int) -> None:
        """
        매 스텝마다 초반 방어 로직 실행
        """
        # 3분 이후는 초반 방어 비활성화
        if self.bot.time > self.early_game_threshold:
            return

        # 1. 초반 적 유닛 감지 (매 0.5초마다 체크)
        if self.bot.time - self.last_enemy_check > 0.5:
            await self._detect_early_threats()
            self.last_enemy_check = self.bot.time

        # 2. Spawning Pool 우선 건설 (12 드론 이후)
        if not self.pool_started and self.bot.supply_used >= 12:
            await self._build_early_pool()

        # 3. 초반 Zergling 생산
        if self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
            await self._produce_early_zerglings()

        # 4. Queen 우선 생산
        if not self.queen_started and self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
            await self._produce_first_queen()

        # 5. 긴급 방어 모드 (적 감지 시)
        if self.emergency_mode or self.early_threats:
            await self._emergency_defense()

    async def _detect_early_threats(self) -> None:
        """
        초반 적 유닛 감지 및 경보
        """
        # 적 유닛이 우리 기지 근처에 있는지 확인
        if not self.bot.enemy_units:
            return

        main_base = self.bot.townhalls.first if self.bot.townhalls else None
        if not main_base:
            return

        # 본진 20 거리 내 적 확인
        nearby_enemies = self.bot.enemy_units.closer_than(20, main_base.position)

        if nearby_enemies:
            self.early_rush_detected = True
            self.emergency_mode = True
            self.early_threats = set(nearby_enemies.tags)

            print(f"[EARLY_DEFENSE] [WARNING] 초반 러시 감지! 적 유닛 {nearby_enemies.amount}개 발견 (게임 시간: {int(self.bot.time)}초)")
            print(f"[EARLY_DEFENSE] 긴급 방어 모드 활성화!")

    async def _build_early_pool(self) -> None:
        """
        Spawning Pool 조기 건설 (12풀)
        """
        # 이미 Pool이 있거나 건설 중이면 스킵
        if self.bot.structures(UnitTypeId.SPAWNINGPOOL):
            self.pool_started = True
            return

        if self.bot.already_pending(UnitTypeId.SPAWNINGPOOL) > 0:
            self.pool_started = True
            return

        # 자원 확인
        if self.bot.minerals < 200:
            return

        # 일꾼 확인
        if not self.bot.workers:
            return

        # 건설 위치 선정 (본진 근처)
        main_base = self.bot.townhalls.first if self.bot.townhalls else None
        if not main_base:
            return

        # Pool 건설 via TechCoordinator
        try:
            tech_coordinator = getattr(self.bot, "tech_coordinator", None)
            if tech_coordinator and not tech_coordinator.is_planned(UnitTypeId.SPAWNINGPOOL):
                target_pos = main_base.position.towards(self.bot.game_info.map_center, 5)
                PRIORITY_DEFENSE = 85  # High priority for early defense
                tech_coordinator.request_structure(
                    UnitTypeId.SPAWNINGPOOL,
                    target_pos,
                    PRIORITY_DEFENSE,
                    "EarlyDefenseSystem"
                )
                self.pool_started = True
                print(f"[EARLY_DEFENSE] [OK] Spawning Pool requested via TechCoordinator (게임 시간: {int(self.bot.time)}초)")
            elif not tech_coordinator:
                print(f"[EARLY_DEFENSE] [WARNING] TechCoordinator not available")
        except Exception as e:
            print(f"[EARLY_DEFENSE] Pool 건설 요청 실패: {e}")

    async def _produce_early_zerglings(self) -> None:
        """
        초반 Zergling 생산 (최소 6마리 확보)
        """
        # 목표: 초기 6 Zergling
        target_zerglings = 6

        # 긴급 모드면 12마리
        if self.emergency_mode:
            target_zerglings = 12

        current_zerglings = self.bot.units(UnitTypeId.ZERGLING).amount
        pending_zerglings = self.bot.already_pending(UnitTypeId.ZERGLING)

        if current_zerglings + pending_zerglings >= target_zerglings:
            return

        # 라바 확인
        if not self.bot.larva:
            return

        # 자원 확인
        if self.bot.minerals < 50:
            return

        # Zergling 생산 (가능한 많이)
        larvae_for_lings = min(
            len(self.bot.larva),
            (target_zerglings - current_zerglings - pending_zerglings + 1) // 2,  # 2마리씩
            self.bot.minerals // 50
        )

        for larva in self.bot.larva[:larvae_for_lings]:
            if self.bot.minerals >= 50:
                larva.train(UnitTypeId.ZERGLING)

        if larvae_for_lings > 0:
            print(f"[EARLY_DEFENSE] Zergling {larvae_for_lings * 2}마리 생산 (목표: {target_zerglings})")

    async def _produce_first_queen(self) -> None:
        """
        첫 Queen 우선 생산
        """
        # 이미 Queen이 있으면 스킵
        if self.bot.units(UnitTypeId.QUEEN).amount >= 1:
            self.queen_started = True
            return

        if self.bot.already_pending(UnitTypeId.QUEEN) > 0:
            self.queen_started = True
            return

        # Hatchery 확인
        if not self.bot.townhalls.ready:
            return

        # 자원 확인
        if self.bot.minerals < 150:
            return

        # Queen 생산
        for hatchery in self.bot.townhalls.ready.idle:
            if self.bot.can_afford(UnitTypeId.QUEEN):
                hatchery.train(UnitTypeId.QUEEN)
                self.queen_started = True
                print(f"[EARLY_DEFENSE] [OK] 첫 Queen 생산 시작 (게임 시간: {int(self.bot.time)}초)")
                break

    async def _emergency_defense(self) -> None:
        """
        긴급 방어 모드
        - 전체 일꾼 방어 동원
        - Zergling 총집합
        """
        if not self.early_threats:
            return

        main_base = self.bot.townhalls.first if self.bot.townhalls else None
        if not main_base:
            return

        # 적 유닛 다시 확인
        enemy_units = self.bot.enemy_units.filter(lambda u: u.tag in self.early_threats)
        if not enemy_units:
            # 위협 사라짐
            self.early_threats.clear()
            self.emergency_mode = False
            print(f"[EARLY_DEFENSE] 초반 위협 제거됨. 일반 모드로 복귀.")
            return

        # 가장 가까운 적
        closest_enemy = enemy_units.closest_to(main_base)

        # Zergling 전부 방어
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if zerglings:
            for ling in zerglings:
                if ling.is_idle or ling.is_moving:
                    ling.attack(closest_enemy.position)

        # 일꾼 방어 (적이 매우 가까울 때만)
        if closest_enemy.distance_to(main_base) < 10:
            defending_workers = min(6, len(self.bot.workers))  # 최대 6명
            workers_to_defend = self.bot.workers.closest_n_units(closest_enemy.position, defending_workers)

            for worker in workers_to_defend:
                # ★ CRITICAL: 일꾼이 기지에서 12거리 이상 벗어나지 않도록 체크 ★
                if worker.distance_to(main_base) > 12:
                    # 너무 멀리 나갔으면 복귀
                    worker.gather(self.bot.mineral_field.closest_to(main_base))
                    continue

                # 적이 기지 근처(15거리 이내)에 있을 때만 공격
                if (worker.is_idle or worker.is_gathering) and closest_enemy.distance_to(main_base) < 10:
                    worker.attack(closest_enemy.position)

            print(f"[EARLY_DEFENSE] ⚔️ 일꾼 {defending_workers}명 방어 투입!")

    def get_status(self) -> str:
        """
        현재 초반 방어 상태 반환
        """
        if self.bot.time > self.early_game_threshold:
            return "초반 방어 완료"

        status_parts = []

        if self.emergency_mode:
            status_parts.append("[!] 긴급 방어 모드")
        else:
            status_parts.append("[OK] 정상")

        if self.pool_started:
            status_parts.append("Pool: [OK]")
        else:
            status_parts.append("Pool: [X]")

        if self.queen_started:
            status_parts.append("Queen: [OK]")
        else:
            status_parts.append("Queen: [X]")

        ling_count = self.bot.units(UnitTypeId.ZERGLING).amount
        status_parts.append(f"Lings: {ling_count}")

        return " | ".join(status_parts)
