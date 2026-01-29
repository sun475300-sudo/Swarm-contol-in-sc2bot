# -*- coding: utf-8 -*-
"""
Mutalisk Micro Controller - Advanced Mutalisk tactics

Features:
1. Regen Dance: Damaged Mutalisks retreat to regenerate health
2. Magic Box: Spread formation against splash damage units (Thor, Archon)
3. Bounce targeting optimization
"""

import math
from typing import Dict, List, Optional, Set, Tuple

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit
except ImportError:
    UnitTypeId = None
    Point2 = None
    Unit = None


class MutaliskMicroController:
    """
    Advanced Mutalisk micro management.

    Key tactics:
    - Regen Dance: Rotate damaged units out of combat
    - Magic Box: 3D sphere formation against splash damage
    """

    def __init__(
        self,
        regen_threshold: float = 0.7,     # Retreat when HP < 70%
        regen_target: float = 0.9,        # Return when HP > 90%
        regen_cooldown: float = 3.0,      # Minimum time between regen cycles
        magic_box_radius: float = 2.5,    # Spread radius for magic box
    ):
        """
        Initialize Mutalisk micro controller.

        Args:
            regen_threshold: Health ratio below which to retreat for regen
            regen_target: Health ratio above which to return to combat
            regen_cooldown: Seconds between regen checks
            magic_box_radius: Radius for magic box spread formation
        """
        self.regen_threshold = regen_threshold
        self.regen_target = regen_target
        self.regen_cooldown = regen_cooldown
        self.magic_box_radius = magic_box_radius

        # Regen Dance state tracking
        self.regenerating_units: Dict[int, float] = {}  # unit_tag -> start_time
        self.last_regen_check: float = 0.0

        # Splash damage unit types (Magic Box triggers)
        self.splash_threats: Set = set()
        if UnitTypeId:
            self.splash_threats = {
                UnitTypeId.THOR,
                UnitTypeId.THORAP,
                UnitTypeId.ARCHON,
                UnitTypeId.PHOENIX,  # With range upgrade
                UnitTypeId.TEMPEST,
            }

    def should_use_magic_box(self, enemy_units) -> bool:
        """
        Check if Magic Box formation should be used.

        Args:
            enemy_units: All visible enemy units

        Returns:
            True if splash threats are detected
        """
        if not enemy_units or not self.splash_threats:
            return False

        for enemy in enemy_units:
            if enemy.type_id in self.splash_threats:
                return True

        return False

    def get_magic_box_position(
        self,
        unit: Unit,
        target_center: object,
        unit_index: int,
        total_units: int
    ) -> Optional[object]:
        """
        Calculate Magic Box position for a Mutalisk.

        Spreads units in a spherical pattern around the target.

        Args:
            unit: The Mutalisk
            target_center: Center position to attack
            unit_index: Index of this unit in the group
            total_units: Total number of Mutalisks

        Returns:
            Offset position for Magic Box formation
        """
        if not Point2 or total_units == 0:
            return None

        # Use golden angle for even distribution
        # https://en.wikipedia.org/wiki/Golden_angle
        golden_angle = math.pi * (3.0 - math.sqrt(5.0))  # ~137.5 degrees

        # Calculate angle for this unit
        theta = unit_index * golden_angle

        # Spiral radius increases with index
        radius_factor = math.sqrt(unit_index / max(total_units, 1))
        radius = self.magic_box_radius * radius_factor

        # Calculate offset position
        offset_x = radius * math.cos(theta)
        offset_y = radius * math.sin(theta)

        return Point2((
            target_center.x + offset_x,
            target_center.y + offset_y
        ))

    def get_regen_status(
        self,
        unit: Unit,
        current_time: float
    ) -> Tuple[bool, bool]:
        """
        Get regeneration status for a Mutalisk.

        Args:
            unit: The Mutalisk
            current_time: Current game time in seconds

        Returns:
            Tuple of (should_start_regen, should_end_regen)
        """
        unit_tag = unit.tag
        health_ratio = self._get_health_ratio(unit)

        # Check if already regenerating
        if unit_tag in self.regenerating_units:
            regen_start = self.regenerating_units[unit_tag]
            time_regenerating = current_time - regen_start

            # End regeneration if:
            # 1. Health above target threshold
            # 2. Or regenerating for at least 3 seconds (minimum regen time)
            if health_ratio >= self.regen_target or time_regenerating >= 3.0:
                return (False, True)  # End regen

            return (False, False)  # Continue regen

        # Start regeneration if health below threshold
        if health_ratio < self.regen_threshold:
            return (True, False)  # Start regen

        return (False, False)  # No change

    def mark_regenerating(self, unit_tag: int, current_time: float):
        """Mark a unit as regenerating."""
        self.regenerating_units[unit_tag] = current_time

    def end_regenerating(self, unit_tag: int):
        """Remove a unit from regenerating state."""
        if unit_tag in self.regenerating_units:
            del self.regenerating_units[unit_tag]

    def get_regen_position(self, unit: Unit, bot) -> Optional[object]:
        """
        Get safe position for regeneration.

        Args:
            unit: The Mutalisk
            bot: Bot instance

        Returns:
            Safe position away from enemies
        """
        if not Point2:
            return None

        # Retreat towards our main base
        if hasattr(bot, "townhalls") and bot.townhalls.exists:
            main_base = bot.townhalls.first.position

            # Move 10 units towards base from current position
            direction_x = main_base.x - unit.position.x
            direction_y = main_base.y - unit.position.y
            length = math.hypot(direction_x, direction_y)

            if length > 0:
                norm_x = direction_x / length
                norm_y = direction_y / length

                return Point2((
                    unit.position.x + norm_x * 10,
                    unit.position.y + norm_y * 10
                ))

        # Fallback: move away from current position
        if hasattr(bot, "start_location"):
            return bot.start_location

        return None

    def is_regenerating(self, unit_tag: int) -> bool:
        """Check if a unit is currently regenerating."""
        return unit_tag in self.regenerating_units

    @staticmethod
    def _get_health_ratio(unit: Unit) -> float:
        """Get unit's current health ratio (0-1)."""
        health = getattr(unit, "health", 0)
        health_max = getattr(unit, "health_max", 1)
        if health_max <= 0:
            return 1.0
        return max(0.0, min(1.0, health / health_max))

    async def execute_regen_dance(
        self,
        mutalisks,
        current_time: float,
        bot
    ) -> Tuple[List, List]:
        """
        Execute Regen Dance logic.

        Args:
            mutalisks: All Mutalisks
            current_time: Current game time
            bot: Bot instance

        Returns:
            Tuple of (combat_ready_mutalisks, regenerating_mutalisks)
        """
        combat_ready = []
        regenerating = []
        actions = []

        for muta in mutalisks:
            start_regen, end_regen = self.get_regen_status(muta, current_time)

            if start_regen:
                # Start regeneration
                self.mark_regenerating(muta.tag, current_time)
                regen_pos = self.get_regen_position(muta, bot)
                if regen_pos:
                    try:
                        actions.append(muta.move(regen_pos))
                        regenerating.append(muta)
                    except Exception:
                        combat_ready.append(muta)
                else:
                    combat_ready.append(muta)

            elif end_regen:
                # End regeneration
                self.end_regenerating(muta.tag)
                combat_ready.append(muta)

            elif self.is_regenerating(muta.tag):
                # Continue regenerating
                regen_pos = self.get_regen_position(muta, bot)
                if regen_pos:
                    try:
                        actions.append(muta.move(regen_pos))
                        regenerating.append(muta)
                    except Exception:
                        combat_ready.append(muta)
                else:
                    combat_ready.append(muta)

            else:
                # Combat ready
                combat_ready.append(muta)

        # Execute all move actions
        if actions:
            await bot.do_actions(actions)

        return combat_ready, regenerating

    async def execute_magic_box(
        self,
        mutalisks,
        target_position: object,
        bot
    ):
        """
        Execute Magic Box formation.

        Args:
            mutalisks: All Mutalisks to position
            target_position: Center position to attack from
            bot: Bot instance
        """
        if not mutalisks:
            return

        actions = []
        total = len(mutalisks)

        for index, muta in enumerate(mutalisks):
            magic_pos = self.get_magic_box_position(
                muta,
                target_position,
                index,
                total
            )

            if magic_pos:
                try:
                    # Move to magic box position, then attack
                    actions.append(muta.move(magic_pos))
                except Exception:
                    continue

        if actions:
            await bot.do_actions(actions)
