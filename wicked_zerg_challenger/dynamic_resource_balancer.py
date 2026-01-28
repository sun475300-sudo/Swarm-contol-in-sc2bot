# -*- coding: utf-8 -*-
"""
Dynamic Resource Balancer - 자원 불균형 감지 및 생산 비율 자동 조정

후반 미네랄 과다/가스 부족 시 가스 유닛 비중을 자동 조절합니다.
"""

from typing import Dict, Tuple
from utils.logger import get_logger


class DynamicResourceBalancer:
    """
    ★ Dynamic Resource Balancer ★

    자원 불균형을 감지하고 유닛 생산 비율을 동적으로 조정하여
    미네랄과 가스를 효율적으로 사용합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("ResourceBalancer")

        # ★ 자원 분석 주기 ★
        self.last_analysis = 0
        self.analysis_interval = 44  # 약 2초마다 분석

        # ★ 자원 불균형 임계값 ★
        self.mineral_excess_threshold = 1000  # 미네랄 1000+ 과다
        self.gas_shortage_threshold = 100     # 가스 100- 부족
        self.high_mineral_threshold = 1500    # 미네랄 1500+ 심각한 과다

        # ★ 동적 비율 조정 ★
        self.base_gas_ratio = 0.50  # 기본 가스 유닛 비율
        self.current_gas_ratio = 0.50
        self.min_gas_ratio = 0.30   # 최소 30%
        self.max_gas_ratio = 0.75   # 최대 75%

        # ★ 조정 속도 ★
        self.adjustment_step = 0.05  # 한번에 5% 조정

        # ★ 상태 추적 ★
        self.resource_state = "BALANCED"  # BALANCED, MINERAL_EXCESS, GAS_SHORTAGE, CRITICAL
        self.last_state_change = 0

    def update(self, iteration: int) -> Dict[str, float]:
        """
        자원 상태를 분석하고 조정된 유닛 비율을 반환

        Args:
            iteration: 현재 게임 반복 횟수

        Returns:
            조정된 유닛 비율 딕셔너리 {"gas_unit_ratio": 0.XX}
        """
        if iteration - self.last_analysis < self.analysis_interval:
            return {"gas_unit_ratio": self.current_gas_ratio}

        self.last_analysis = iteration

        # ★ 1. 자원 상태 분석 ★
        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)
        game_time = getattr(self.bot, "time", 0)

        old_state = self.resource_state
        old_ratio = self.current_gas_ratio

        # ★ 2. 자원 불균형 감지 ★
        resource_state, target_ratio = self._analyze_resource_imbalance(
            minerals, gas, game_time
        )

        self.resource_state = resource_state
        self.current_gas_ratio = target_ratio

        # ★ 3. 로그 (상태 변화 시에만) ★
        if old_state != resource_state or abs(old_ratio - target_ratio) > 0.01:
            self.logger.info(
                f"[{int(game_time)}s] ★ RESOURCE BALANCE: {resource_state} ★\n"
                f"  Minerals: {minerals}m, Gas: {gas}g\n"
                f"  Gas Unit Ratio: {old_ratio:.0%} → {target_ratio:.0%}\n"
                f"  Adjustment: {(target_ratio - old_ratio)*100:+.0f}%"
            )
            self.last_state_change = iteration

        return {"gas_unit_ratio": self.current_gas_ratio}

    def _analyze_resource_imbalance(
        self, minerals: int, gas: int, game_time: float
    ) -> Tuple[str, float]:
        """
        자원 불균형을 분석하고 목표 가스 비율 계산

        Args:
            minerals: 현재 미네랄
            gas: 현재 가스
            game_time: 게임 시간

        Returns:
            (resource_state, target_gas_ratio)
        """
        # ★ Early Game (3분 이하): 기본 비율 유지 ★
        if game_time < 180:
            return "BALANCED", self.base_gas_ratio

        # ★ Critical: 미네랄 폭증 + 가스 고갈 ★
        if minerals >= self.high_mineral_threshold and gas < self.gas_shortage_threshold:
            # 가스 유닛 비율 최대로 증가
            target_ratio = min(self.max_gas_ratio, self.current_gas_ratio + self.adjustment_step * 2)
            return "CRITICAL", target_ratio

        # ★ Mineral Excess: 미네랄만 많음 ★
        if minerals >= self.mineral_excess_threshold and gas >= self.gas_shortage_threshold:
            # 가스 유닛 비율 증가
            target_ratio = min(self.max_gas_ratio, self.current_gas_ratio + self.adjustment_step)
            return "MINERAL_EXCESS", target_ratio

        # ★ Gas Shortage: 가스만 부족 ★
        if gas < self.gas_shortage_threshold and minerals < self.mineral_excess_threshold:
            # 가스 유닛 비율 감소 (미네랄 유닛 늘림)
            target_ratio = max(self.min_gas_ratio, self.current_gas_ratio - self.adjustment_step)
            return "GAS_SHORTAGE", target_ratio

        # ★ Balanced: 정상 범위 ★
        # 점진적으로 기본 비율로 복귀
        if self.current_gas_ratio > self.base_gas_ratio:
            target_ratio = max(self.base_gas_ratio, self.current_gas_ratio - self.adjustment_step * 0.5)
        elif self.current_gas_ratio < self.base_gas_ratio:
            target_ratio = min(self.base_gas_ratio, self.current_gas_ratio + self.adjustment_step * 0.5)
        else:
            target_ratio = self.base_gas_ratio

        return "BALANCED", target_ratio

    def get_unit_ratio_adjustments(self) -> Dict[str, float]:
        """
        현재 자원 상태에 따른 유닛별 비율 조정값 반환

        Returns:
            유닛별 비율 조정 딕셔너리
            예: {"hydralisk": 0.30, "mutalisk": 0.15, "zergling": 0.40, "roach": 0.15}
        """
        gas_ratio = self.current_gas_ratio
        mineral_ratio = 1.0 - gas_ratio

        # 자원 상태에 따른 유닛 구성
        if self.resource_state == "CRITICAL":
            # 미네랄 과다 → 가스 유닛 최대한
            return {
                "hydralisk": gas_ratio * 0.50,
                "mutalisk": gas_ratio * 0.30,
                "corruptor": gas_ratio * 0.20,
                "zergling": mineral_ratio * 0.70,
                "roach": mineral_ratio * 0.30,
            }

        elif self.resource_state == "MINERAL_EXCESS":
            # 미네랄 많음 → 가스 유닛 비중 증가
            return {
                "hydralisk": gas_ratio * 0.45,
                "roach": 0.25,  # 약간의 가스 사용
                "mutalisk": gas_ratio * 0.25,
                "zergling": mineral_ratio * 0.80,
            }

        elif self.resource_state == "GAS_SHORTAGE":
            # 가스 부족 → 미네랄 유닛 위주
            return {
                "zergling": mineral_ratio * 0.60,
                "roach": 0.30,  # 약간의 가스 사용
                "hydralisk": gas_ratio * 0.10,
            }

        else:  # BALANCED
            # 균형 잡힌 구성
            return {
                "zergling": 0.30,
                "roach": 0.25,
                "hydralisk": 0.25,
                "mutalisk": 0.15,
                "queen": 0.05,
            }

    def should_build_extractor(self) -> bool:
        """
        추가 가스 건물 건설 필요 여부

        Returns:
            True if more extractors needed
        """
        # Critical 상태에서는 가스 건물 더 짓기
        if self.resource_state == "CRITICAL":
            return True

        # Gas Shortage 상태에서도 가스 건물 짓기
        if self.resource_state == "GAS_SHORTAGE":
            return True

        return False

    def get_current_ratio(self) -> float:
        """현재 가스 유닛 비율 반환"""
        return self.current_gas_ratio
