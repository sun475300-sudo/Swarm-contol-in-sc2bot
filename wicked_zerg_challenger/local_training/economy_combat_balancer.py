# -*- coding: utf-8 -*-
"""
Economy-Combat Balancer - Unified worker vs army production balance.

Consolidated version combining original and improved features:
- Dynamic drone targets based on game phase and base count
- Production history tracking for balanced decisions
- Resource banking detection to prevent over-economy
- Balance mode system for strategic flexibility
- Robust error handling
"""

from typing import Dict

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:

    class UnitTypeId:
        DRONE = "DRONE"
        ZERGLING = "ZERGLING"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        MUTALISK = "MUTALISK"
        QUEEN = "QUEEN"
        OVERLORD = "OVERLORD"


class EconomyCombatBalancer:
    """
    Unified economy/combat balancing controller.

    Features:
    - Dynamic drone targets based on game phase (early/mid/late)
    - Production history for ratio-based decisions
    - Resource banking threshold to stop over-economy
    - Balance mode reporting for strategy adaptation
    - Minimum worker maintenance for emergency recovery
    """

    def __init__(self, bot):
        """
        Initialize economy balancer.

        Args:
            bot: The main bot instance
        """
        self.bot = bot

        # Resource thresholds
        self.resource_bank_threshold = 3000
        self.min_drone_count = 12

        # ★★★ MAXIMUM EXPANSION: 최대 멀티를 위한 일꾼 목표 ★★★
        # Drone targets by game phase
        self.drone_targets = {
            "early": 44,   # 0-6 min (2-3베이스 완전 포화)
            "mid": 88,     # 6-12 min (4-5베이스 완전 포화)
            "late": 110,   # 12+ min (6-7베이스 완전 포화)
        }

        # Base calculation
        self.drones_per_base = 22  # 기지당 22마리 (16 미네랄 + 6 가스)

        # Production history tracking
        self.production_history: Dict[str, int] = {
            "drones": 0,
            "army_units": 0,
            "total": 0,
        }

    def get_drone_target(self) -> int:
        """
        Calculate dynamic drone target based on time and expansion count.

        ★ IMPROVED: 실제 기지의 ideal_harvesters 사용 ★

        Returns:
            Target number of drones
        """
        try:
            bases = getattr(self.bot, "townhalls", None)
            base_count = max(1, bases.amount if bases else 1)
            game_time = getattr(self.bot, "time", 0.0)
            game_time_minutes = game_time / 60.0

            # Check for resource banking
            minerals = getattr(self.bot, "minerals", 0)
            if minerals > self.resource_bank_threshold:
                current = self.current_drone_count()
                return current  # Maintain current level

            # ★ 실제 ideal_harvesters 계산 (기지 + 가스) ★
            actual_ideal = self._calculate_actual_ideal_workers()

            # Phase-based target (fallback)
            if game_time_minutes < 6:
                base_target = self.drone_targets["early"]
            elif game_time_minutes < 12:
                base_target = self.drone_targets["mid"]
            else:
                base_target = self.drone_targets["late"]

            # Multi-base adjustment (old method, fallback)
            multi_target = base_count * self.drones_per_base

            # ★ 실제 ideal이 가장 정확한 목표 ★
            # 약간의 여유분 추가 (+4, 이동 중인 일꾼 고려)
            if actual_ideal > 0:
                target = actual_ideal + 4
            else:
                # Use higher of the two (fallback)
                target = max(base_target, multi_target)

            return max(self.min_drone_count, int(target))

        except Exception:
            return 30  # Default fallback

    def _calculate_actual_ideal_workers(self) -> int:
        """
        ★ 실제 필요한 일꾼 수 계산 ★

        기지의 ideal_harvesters + 가스 건물의 ideal_harvesters
        """
        try:
            total_ideal = 0

            # 기지 일꾼
            if hasattr(self.bot, "townhalls"):
                for th in self.bot.townhalls.ready:
                    ideal = getattr(th, "ideal_harvesters", 16)
                    total_ideal += ideal

            # 가스 일꾼
            if hasattr(self.bot, "gas_buildings"):
                for extractor in self.bot.gas_buildings.ready:
                    ideal = getattr(extractor, "ideal_harvesters", 3)
                    total_ideal += ideal

            return total_ideal

        except Exception:
            return 0

    def current_drone_count(self) -> int:
        """Get current number of drones."""
        if not hasattr(self.bot, "units"):
            return 0
        try:
            drones = self.bot.units(UnitTypeId.DRONE).ready
            return drones.amount if drones else 0
        except Exception:
            return 0

    def should_train_drone(self) -> bool:
        """
        Deterministic worker production decision.

        ★ IMPROVED: 기지별 포화도 체크 ★

        Uses both target-based and ratio-based logic for balanced decisions.

        Returns:
            True if should produce a drone
        """
        try:
            drones = self.current_drone_count()
            target = self.get_drone_target()

            # Priority 0: ★ CRITICAL - Always maintain minimum workers ★
            if drones < self.min_drone_count:
                return True

            # Priority 0.5: ★ CRITICAL FIX - 1베이스 expansion 비용 확보 ★
            # 1베이스만 있으면 무조건 28마리까지 생산 (다른 모든 로직 무시)
            base_count = 0
            if hasattr(self.bot, "townhalls"):
                bases = self.bot.townhalls
                base_count = bases.amount if hasattr(bases, "amount") else len(list(bases))

            if base_count <= 1 and drones < 28:
                return True  # 1베이스는 expansion 비용 확보를 위해 무조건 생산

            # Priority 1: ★ 기지 포화도 체크 ★
            saturation_status = self._check_base_saturation()
            if saturation_status == "FULLY_SATURATED":
                return False  # 모든 기지가 포화면 드론 불필요

            # Priority 1.5: ★ 기지가 심하게 부족하면 드론 우선 ★
            if saturation_status == "SEVERELY_UNDER":
                return True

            # Priority 2: Check production history ratio
            total_produced = self.production_history["total"]
            if total_produced > 0:
                drone_ratio = self.production_history["drones"] / total_produced
                target_ratio = self._calculate_target_drone_ratio()

                # If significantly below target ratio, prioritize drones
                if drone_ratio < target_ratio - 0.1:
                    return True

                # If significantly above target ratio, stop drone production
                if drone_ratio > target_ratio + 0.1:
                    return False

            # Priority 3: ★ 포화 상태면 드론 생산 감소 ★
            if saturation_status == "NEAR_SATURATED":
                # 60% 확률로 드론 생산 스킵 (군대 우선)
                import random
                if random.random() < 0.6:
                    return False

            # Priority 4: Simple target comparison
            return drones < target

        except Exception:
            return False

    def _check_base_saturation(self) -> str:
        """
        ★ 기지별 일꾼 포화도 체크 ★

        Returns:
            "FULLY_SATURATED": 모든 기지가 포화 (ideal에 도달)
            "NEAR_SATURATED": 대부분 기지가 거의 포화 (ideal의 90% 이상)
            "UNDER_SATURATED": 일꾼이 부족
            "SEVERELY_UNDER": 심하게 부족 (ideal의 50% 미만)
        """
        try:
            if not hasattr(self.bot, "townhalls"):
                return "UNDER_SATURATED"

            townhalls = self.bot.townhalls.ready
            if not townhalls.exists:
                return "UNDER_SATURATED"

            total_assigned = 0
            total_ideal = 0

            for th in townhalls:
                assigned = getattr(th, "assigned_harvesters", 0)
                ideal = getattr(th, "ideal_harvesters", 16)

                total_assigned += assigned
                total_ideal += ideal

            # 가스 건물 일꾼도 고려
            if hasattr(self.bot, "gas_buildings"):
                for extractor in self.bot.gas_buildings.ready:
                    total_assigned += getattr(extractor, "assigned_harvesters", 0)
                    total_ideal += getattr(extractor, "ideal_harvesters", 3)

            if total_ideal == 0:
                return "UNDER_SATURATED"

            saturation_ratio = total_assigned / total_ideal

            if saturation_ratio >= 1.0:
                return "FULLY_SATURATED"
            elif saturation_ratio >= 0.9:
                return "NEAR_SATURATED"
            elif saturation_ratio >= 0.5:
                return "UNDER_SATURATED"
            else:
                return "SEVERELY_UNDER"

        except Exception:
            return "UNDER_SATURATED"

    def _calculate_target_drone_ratio(self) -> float:
        """
        Calculate target drone-to-army ratio based on game phase.

        ★ IMPROVED: 포화 상태면 병력 비중 증가 ★
        """
        try:
            game_time = getattr(self.bot, "time", 0.0)
            game_time_minutes = game_time / 60.0

            # ★ MACRO ECONOMY: 경제 비중 증가 (빠른 멀티 지원) ★
            if game_time_minutes < 6:
                base_ratio = 0.75  # Early: 75% economy (빠른 드론 생산)
            elif game_time_minutes < 12:
                base_ratio = 0.6   # Mid: 60% economy (멀티 포화)
            else:
                base_ratio = 0.4   # Late: 40% economy (여전히 드론 필요)

            # ★ 포화 상태면 병력 비중 증가 ★
            saturation = self._check_base_saturation()
            if saturation == "FULLY_SATURATED":
                # 포화 상태: 드론 비율 -20%p (병력 우선)
                base_ratio = max(0.1, base_ratio - 0.2)
            elif saturation == "NEAR_SATURATED":
                # 거의 포화: 드론 비율 -10%p
                base_ratio = max(0.2, base_ratio - 0.1)

            return base_ratio

        except Exception:
            return 0.5

    def record_production(self, unit_type) -> None:
        """
        Record a unit production for ratio tracking.

        Args:
            unit_type: UnitTypeId of produced unit
        """
        self.production_history["total"] += 1

        if unit_type == UnitTypeId.DRONE:
            self.production_history["drones"] += 1
        else:
            self.production_history["army_units"] += 1

    def count_army_units(self) -> int:
        """
        Count current army units (excluding workers and support).

        Returns:
            Number of combat-capable army units
        """
        try:
            if not hasattr(self.bot, "units"):
                return 0

            army_count = 0
            all_units = self.bot.units

            for unit in all_units:
                # Skip workers
                if unit.type_id == UnitTypeId.DRONE:
                    continue

                # Skip structures
                if getattr(unit, "is_structure", False):
                    continue

                # Skip support units
                if unit.type_id in {UnitTypeId.QUEEN, UnitTypeId.OVERLORD}:
                    continue

                army_count += 1

            return army_count

        except Exception:
            return 0

    def get_balance_mode(self) -> str:
        """
        Get current balance mode for strategic decisions.

        Returns:
            One of: 'FULL_ECONOMY', 'ECONOMY_FOCUS', 'BALANCED',
                   'COMBAT_FOCUS', 'FULL_COMBAT'
        """
        try:
            drone_count = self.current_drone_count()
            army_count = self.count_army_units()
            target_drones = self.get_drone_target()

            total = drone_count + army_count
            if total == 0:
                return "BALANCED"

            drone_ratio = drone_count / total
            target_ratio = target_drones / (target_drones + max(army_count, 10))

            ratio_diff = drone_ratio - target_ratio

            if ratio_diff > 0.2:
                return "FULL_COMBAT"
            elif ratio_diff > 0.1:
                return "COMBAT_FOCUS"
            elif ratio_diff > -0.1:
                return "BALANCED"
            elif ratio_diff > -0.2:
                return "ECONOMY_FOCUS"
            else:
                return "FULL_ECONOMY"

        except Exception:
            return "BALANCED"

    def get_production_stats(self) -> Dict[str, float]:
        """
        Get production statistics for analysis.

        Returns:
            Dict with production ratios and counts
        """
        total = self.production_history["total"]
        if total == 0:
            return {
                "drone_count": self.current_drone_count(),
                "army_count": self.count_army_units(),
                "drone_ratio": 0.0,
                "army_ratio": 0.0,
                "balance_mode": self.get_balance_mode(),
            }

        return {
            "drone_count": self.current_drone_count(),
            "army_count": self.count_army_units(),
            "drone_ratio": self.production_history["drones"] / total,
            "army_ratio": self.production_history["army_units"] / total,
            "total_produced": total,
            "balance_mode": self.get_balance_mode(),
        }


# Backward compatibility alias
EconomyCombatBalancerImproved = EconomyCombatBalancer
