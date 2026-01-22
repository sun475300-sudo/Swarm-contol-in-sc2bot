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
    """
    Deterministic economy/combat balancing.

    Features:
    - Dynamic drone targets based on game phase
    - Stops drone production when resources bank (>3000 minerals)
    - Resumes production when workers are lost
    """

    def __init__(self, bot):
        self.bot = bot
        self.resource_bank_threshold = 3000  # Stop drone production above this
        self.min_drone_count = 12  # Always maintain minimum workers

    def get_drone_target(self) -> int:
        """
        Dynamic drone target based on time and expansion count.

        Modified to stop drone production when resources are banking.
        """
        bases = getattr(self.bot, "townhalls", None)
        base_count = max(1, bases.amount if bases else 1)
        game_time = getattr(self.bot, "time", 0.0)

        # Check for resource banking
        minerals = getattr(self.bot, "minerals", 0)
        if minerals > self.resource_bank_threshold:
            # Stop growing economy, focus on spending
            current = self.current_drone_count()
            return current  # Maintain current level, don't grow

        if game_time < 240:  # Early (0-4 min)
            target = 14 * base_count
        elif game_time < 360:  # Mid (4-6 min)
            target = min(55, 16 * base_count + 6)
        else:  # Late (6+ min)
            target = min(85, base_count * 22)

        return max(self.min_drone_count, target)

    def current_drone_count(self) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        drones = self.bot.units(UnitTypeId.DRONE).ready
        return drones.amount if drones else 0

    def should_train_drone(self) -> bool:
        """
        Deterministic worker production decision.

        Priority rules:
        1. Always maintain minimum workers
        2. Stop production when resources bank heavily
        3. Resume when below target
        """
        drones = self.current_drone_count()
        target = self.get_drone_target()

        # Always maintain minimum workers (emergency recovery)
        if drones < self.min_drone_count:
            return True

        # Check if we're below target
        if drones < target:
            return True

        return False
