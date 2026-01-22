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

        # Drone targets by game phase
        self.drone_targets = {
            "early": 30,  # 0-6 min
            "mid": 60,  # 6-12 min
            "late": 80,  # 12+ min
        }

        # Base calculation
        self.drones_per_base = 16

        # Production history tracking
        self.production_history: Dict[str, int] = {
            "drones": 0,
            "army_units": 0,
            "total": 0,
        }

    def get_drone_target(self) -> int:
        """
        Calculate dynamic drone target based on time and expansion count.

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

            # Phase-based target
            if game_time_minutes < 6:
                base_target = self.drone_targets["early"]
            elif game_time_minutes < 12:
                base_target = self.drone_targets["mid"]
            else:
                base_target = self.drone_targets["late"]

            # Multi-base adjustment
            multi_target = base_count * self.drones_per_base

            # Use higher of the two
            target = max(base_target, multi_target)

            return max(self.min_drone_count, int(target))

        except Exception:
            return 30  # Default fallback

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

        Uses both target-based and ratio-based logic for balanced decisions.

        Returns:
            True if should produce a drone
        """
        try:
            drones = self.current_drone_count()
            target = self.get_drone_target()

            # Priority 1: Always maintain minimum workers
            if drones < self.min_drone_count:
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

            # Priority 3: Simple target comparison
            return drones < target

        except Exception:
            return False

    def _calculate_target_drone_ratio(self) -> float:
        """Calculate target drone-to-army ratio based on game phase."""
        try:
            game_time = getattr(self.bot, "time", 0.0)
            game_time_minutes = game_time / 60.0

            if game_time_minutes < 6:
                return 0.7  # Early: 70% economy
            elif game_time_minutes < 12:
                return 0.5  # Mid: 50% economy
            else:
                return 0.3  # Late: 30% economy

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
