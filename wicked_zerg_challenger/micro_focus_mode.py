# -*- coding: utf-8 -*-
"""
Micro Focus Mode - Combat 우선순위 동적 할당

전투 상황 감지 시 MicroController에 더 많은 연산 자원과 우선순위를 할당합니다.
"""

from typing import Optional
from utils.logger import get_logger


class MicroFocusMode:
    """
    ★ Micro Controller Focus Mode ★

    전투 상황의 중요도에 따라 MicroController의 실행 빈도와 우선순위를 동적 조정
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("MicroFocusMode")

        # ★ Focus Mode 상태 ★
        self.is_active = False
        self.focus_level = 0  # 0=Normal, 1=Alert, 2=Combat, 3=Critical
        self.last_mode_change = 0

        # ★ 실행 빈도 조정 ★
        self.normal_interval = 8  # 일반: 8프레임마다 (약 0.35초)
        self.alert_interval = 5   # 경계: 5프레임마다 (약 0.22초)
        self.combat_interval = 3  # 전투: 3프레임마다 (약 0.13초)
        self.critical_interval = 1  # 위급: 매 프레임 (약 0.04초)

        # ★ Combat detection ★
        self.last_combat_check = 0
        self.combat_check_interval = 11  # 0.5초마다 전투 상황 체크
        self.enemy_near_bases_count = 0
        self.our_army_in_combat = 0

    def update(self, iteration: int) -> int:
        """
        전투 상황을 분석하고 적절한 실행 빈도를 반환

        Args:
            iteration: 현재 게임 반복 횟수

        Returns:
            MicroController 실행 간격 (프레임 수)
        """
        if iteration - self.last_combat_check < self.combat_check_interval:
            return self.get_current_interval()

        self.last_combat_check = iteration

        # ★ 1. 전투 상황 분석 ★
        old_level = self.focus_level
        self.focus_level = self._analyze_combat_situation()

        # ★ 2. Focus Mode 활성화/비활성화 ★
        was_active = self.is_active
        self.is_active = self.focus_level >= 2  # Combat 이상이면 활성화

        # ★ 3. 로그 (상태 변화 시에만) ★
        if old_level != self.focus_level or was_active != self.is_active:
            game_time = getattr(self.bot, "time", 0)
            level_name = ["NORMAL", "ALERT", "COMBAT", "CRITICAL"][self.focus_level]
            self.logger.info(
                f"[{int(game_time)}s] ★ MICRO FOCUS: {level_name} ★\n"
                f"  Interval: {self.get_current_interval()} frames\n"
                f"  Enemies near bases: {self.enemy_near_bases_count}\n"
                f"  Army in combat: {self.our_army_in_combat}"
            )
            self.last_mode_change = iteration

        return self.get_current_interval()

    def _analyze_combat_situation(self) -> int:
        """
        전투 상황 분석하여 Focus Level 결정

        Returns:
            0=Normal, 1=Alert, 2=Combat, 3=Critical
        """
        try:
            # 기지 근처 적 유닛 감지
            self.enemy_near_bases_count = self._count_enemies_near_bases()

            # 전투 중인 아군 유닛 수
            self.our_army_in_combat = self._count_army_in_combat()

            # ★ Critical: 기지 직접 공격받는 중 ★
            if self.enemy_near_bases_count >= 5:
                return 3

            # ★ Combat: 대규모 교전 중 ★
            if self.our_army_in_combat >= 10 or self.enemy_near_bases_count >= 3:
                return 2

            # ★ Alert: 적 소규모 발견 ★
            if self.enemy_near_bases_count >= 1 or self.our_army_in_combat >= 5:
                return 1

            # ★ Normal: 평화로운 상황 ★
            return 0

        except Exception as e:
            self.logger.warning(f"Combat analysis failed: {e}")
            return 0

    def _count_enemies_near_bases(self) -> int:
        """기지 근처 적 유닛 수 카운트"""
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "enemy_units"):
            return 0

        townhalls = getattr(self.bot, "townhalls", [])
        enemy_units = getattr(self.bot, "enemy_units", [])

        if not townhalls:
            return 0

        count = 0
        for enemy in enemy_units:
            for base in townhalls:
                distance = enemy.position.distance_to(base.position)
                if distance < 15:  # 기지 15거리 이내
                    count += 1
                    break

        return count

    def _count_army_in_combat(self) -> int:
        """전투 중인 아군 유닛 수 카운트"""
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return 0

        army_units = getattr(self.bot, "units", [])
        enemy_units = getattr(self.bot, "enemy_units", [])

        if not enemy_units:
            return 0

        army_types = {
            "ZERGLING", "BANELING", "ROACH", "RAVAGER",
            "HYDRALISK", "LURKER", "LURKERMP", "MUTALISK",
            "CORRUPTOR", "SWARMHOST", "ULTRALISK", "BROODLORD"
        }

        count = 0
        for unit in army_units:
            type_name = getattr(unit.type_id, "name", "").upper()
            if type_name not in army_types:
                continue

            # 적과 가까우면 전투 중으로 판단
            for enemy in enemy_units:
                distance = unit.position.distance_to(enemy.position)
                if distance < 12:  # 12거리 이내면 교전 중
                    count += 1
                    break

        return count

    def get_current_interval(self) -> int:
        """현재 Focus Level에 따른 실행 간격 반환"""
        intervals = [
            self.normal_interval,
            self.alert_interval,
            self.combat_interval,
            self.critical_interval
        ]
        return intervals[self.focus_level]

    def should_prioritize_micro(self) -> bool:
        """
        Micro Control을 최우선으로 실행해야 하는지 판단

        Returns:
            True if micro should run before other tasks
        """
        return self.focus_level >= 2  # Combat 이상이면 최우선
