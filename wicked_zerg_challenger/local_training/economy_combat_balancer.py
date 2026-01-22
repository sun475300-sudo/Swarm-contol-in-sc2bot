# -*- coding: utf-8 -*-
"""
EconomyCombatBalancer - deterministic worker vs army balance.

Replaces probabilistic worker decisions with a target-driven model.
"""

from typing import Optional

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallbacks for tooling environments

    class UnitTypeId:
        DRONE = "DRONE"


class EconomyCombatBalancer:
    """Deterministic economy/combat balancing based on drone targets."""

    def __init__(self, bot):
        self.bot = bot

    def get_drone_target(self) -> int:
        """Dynamic drone target based on time and expansion count."""
        bases = getattr(self.bot, "townhalls", None)
        base_count = max(1, bases.amount if bases else 1)
        game_time = getattr(self.bot, "time", 0.0)

        if game_time < 240:  # Early
            target = 14 * base_count
        elif game_time < 360:  # Mid
            target = min(55, 16 * base_count + 6)
        else:  # Late (6+ min)
            target = min(85, base_count * 22)

        return max(12, target)

    def current_drone_count(self) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        drones = self.bot.units(UnitTypeId.DRONE).ready
        return drones.amount if drones else 0

    def should_train_drone(self) -> bool:
        """Deterministic worker production decision."""
        drones = self.current_drone_count()
        target = self.get_drone_target()

        if drones < target:
            return True
        return False
