# -*- coding: utf-8 -*-
"""
Formation Tactics - Concave formations and special ability management.

This module handles tactical formations for ranged units and
special ability timing (burrow/unburrow).
"""

import math
from typing import List, Optional, Set, Tuple

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
except ImportError:
    AbilityId = None
    UnitTypeId = None
    UpgradeId = None
    Point2 = None


class ConcaveFormationController:
    """
    Generates concave (arc) formations for ranged units.

    Spreads ranged units in a fan pattern around enemy positions
    to maximize firepower and minimize friendly fire blocking.
    """

    def __init__(
        self,
        concave_weight: float = 0.6,
        spread_angle: float = 0.8,
        range_buffer: float = 0.8,
    ):
        """
        Initialize concave formation controller.

        Args:
            concave_weight: Weight for blending concave position (0-1)
            spread_angle: Maximum spread angle in radians
            range_buffer: Extra distance beyond unit range
        """
        self.concave_weight = concave_weight
        self.spread_angle = spread_angle
        self.range_buffer = range_buffer

        # Ranged unit types that should use concave formations
        self.ranged_unit_types: Set = set()
        if UnitTypeId:
            self.ranged_unit_types = {
                UnitTypeId.ROACH,
                UnitTypeId.RAVAGER,
                UnitTypeId.HYDRALISK,
                UnitTypeId.LURKER,
                UnitTypeId.QUEEN,
            }

    def get_concave_target(self, unit, enemy_center) -> Optional[object]:
        """
        Calculate concave formation position for a ranged unit.

        Spreads units in an arc facing the enemy center.

        Args:
            unit: The ranged unit
            enemy_center: Center position of enemy forces

        Returns:
            Target position for concave formation, or None
        """
        if not Point2 or not enemy_center:
            return None
        if not UnitTypeId or unit.type_id not in self.ranged_unit_types:
            return None
        if getattr(unit, "is_flying", False):
            return None

        # Get unit's attack range
        range_value = getattr(unit, "ground_range", 5.0)
        desired_range = max(4.0, range_value + self.range_buffer)

        # Calculate direction from enemy to unit
        dx = unit.position.x - enemy_center.x
        dy = unit.position.y - enemy_center.y
        length = math.hypot(dx, dy)

        if length == 0:
            dx, dy = 1.0, 0.0
            length = 1.0

        # Normalize direction
        nx = dx / length
        ny = dy / length

        # Apply rotation offset based on unit tag for spreading
        angle = self._get_tag_offset(unit.tag)
        rx, ry = self._rotate(nx, ny, angle)

        return Point2(
            (enemy_center.x + rx * desired_range, enemy_center.y + ry * desired_range)
        )

    def _get_tag_offset(self, tag: int) -> float:
        """
        Map unit tag to angle offset for deterministic spreading.

        Args:
            tag: Unit's unique tag identifier

        Returns:
            Angle offset in radians
        """
        bucket = (tag % 7) - 3  # -3 to 3
        return (bucket / 3.0) * self.spread_angle

    @staticmethod
    def _rotate(x: float, y: float, angle: float) -> Tuple[float, float]:
        """
        Rotate a 2D vector by given angle.

        Args:
            x: X component
            y: Y component
            angle: Rotation angle in radians

        Returns:
            Rotated (x, y) tuple
        """
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return x * cos_a - y * sin_a, x * sin_a + y * cos_a

    @staticmethod
    def blend_positions(base, target, weight: float):
        """
        Blend two positions with given weight.

        Args:
            base: Base position
            target: Target position to blend towards
            weight: Blend weight (0 = base, 1 = target)

        Returns:
            Blended Point2 position
        """
        if not Point2:
            return base
        return Point2(
            (
                base.x + (target.x - base.x) * weight,
                base.y + (target.y - base.y) * weight,
            )
        )


class BurrowController:
    """
    Manages burrow and unburrow abilities for applicable units.

    Handles health-based burrowing for survival and
    tactical burrowing for ambush units like banelings.
    """

    def __init__(
        self,
        health_threshold_burrow: float = 0.35,
        health_threshold_unburrow: float = 0.7,
        check_interval: int = 16,
    ):
        """
        Initialize burrow controller.

        Args:
            health_threshold_burrow: Health ratio below which to burrow
            health_threshold_unburrow: Health ratio above which to unburrow
            check_interval: Frames between burrow checks
        """
        self.health_threshold_burrow = health_threshold_burrow
        self.health_threshold_unburrow = health_threshold_unburrow
        self.check_interval = check_interval
        self.last_check_frame = 0

        # Unit types that can burrow
        self.burrow_unit_types: Set = set()
        if UnitTypeId:
            self.burrow_unit_types = {
                UnitTypeId.ROACH,
                UnitTypeId.ROACHBURROWED,
                UnitTypeId.LURKER,  # Likely LURKERMP
                UnitTypeId.LURKERMP,
                UnitTypeId.LURKERMPBURROWED,
                UnitTypeId.BANELING,
                UnitTypeId.BANELINGBURROWED,
                UnitTypeId.INFESTOR,
                UnitTypeId.INFESTORBURROWED,
                UnitTypeId.SWARMHOSTMP,
                UnitTypeId.SWARMHOSTBURROWEDMP,
            }

        # Baneling specific settings
        self.baneling_unburrow_range = 4.5  # 맹독충 잠복 해제 거리 (스플래시 범위 고려)

    def _can_burrow(self, bot) -> bool:
        """잠복 업그레이드 확인"""
        if not UpgradeId:
            return False
        if hasattr(bot, 'state') and hasattr(bot.state, 'upgrades'):
            return UpgradeId.BURROW in bot.state.upgrades
        return False

    async def handle_burrow(
        self, units, enemy_units, iteration: int, do_actions_func, bot=None
    ) -> Set[int]:
        """
        Process burrow/unburrow logic for all applicable units.

        Args:
            units: Friendly combat units
            enemy_units: Enemy units
            iteration: Current game iteration
            do_actions_func: Async function to execute actions
            bot: Bot instance for upgrade checking

        Returns:
            Set of unit tags that should be skipped by movement logic
        """
        if not AbilityId or not UnitTypeId:
            return set()

        if iteration - self.last_check_frame < self.check_interval:
            return set()

        # 잠복 업그레이드 확인
        if bot and not self._can_burrow(bot):
            return set()

        self.last_check_frame = iteration
        actions = []
        skip_units = set()

        for unit in units:
            if unit.type_id not in self.burrow_unit_types:
                continue

            health_ratio = self._health_ratio(unit)
            enemy_nearby = self._enemy_within(enemy_units, unit, 8.0)
            is_burrowed = getattr(unit, "is_burrowed", False)
            down_ability, up_ability = self._get_burrow_abilities(unit.type_id)

            if is_burrowed:
                action = self._handle_burrowed_unit(
                    unit, enemy_units, health_ratio, enemy_nearby, up_ability
                )
                if action:
                    actions.append(action)
                skip_units.add(unit.tag)
            else:
                action = self._handle_unburrowed_unit(
                    unit, health_ratio, enemy_nearby, down_ability
                )
                if action:
                    actions.append(action)
                    skip_units.add(unit.tag)

        if actions:
            await do_actions_func(actions)

        return skip_units

    def _handle_burrowed_unit(
        self, unit, enemy_units, health_ratio: float, enemy_nearby: bool, up_ability
    ):
        """Handle logic for currently burrowed units."""
        # Banelings unburrow when enemies are in optimal range
        if UnitTypeId and unit.type_id == UnitTypeId.BANELING:
            if self._enemy_within(enemy_units, unit, self.baneling_unburrow_range):
                if up_ability:
                    return unit(up_ability)
                return None

        # Unburrow if healthy or no enemies nearby
        if health_ratio >= self.health_threshold_unburrow or not enemy_nearby:
            if up_ability:
                return unit(up_ability)

        return None

    def _handle_unburrowed_unit(
        self, unit, health_ratio: float, enemy_nearby: bool, down_ability
    ):
        """Handle logic for unburrowed units."""
        # Banelings burrow when enemies nearby and idle (ambush)
        if UnitTypeId and unit.type_id == UnitTypeId.BANELING:
            if enemy_nearby and getattr(unit, "is_idle", True) and down_ability:
                return unit(down_ability)
            return None

        # Other units burrow at low health
        if enemy_nearby and health_ratio <= self.health_threshold_burrow:
            if down_ability:
                return unit(down_ability)

        # ★ FIX: Lurkers must burrow to attack! ★
        if UnitTypeId and unit.type_id == UnitTypeId.LURKERMP:
            # 적이 공격 사거리(9) 내에 있으면 잠복
            if self._enemy_within(enemy_units, unit, 9.0) and down_ability:
                return unit(down_ability)

        return None

    @staticmethod
    def _health_ratio(unit) -> float:
        """Calculate unit's current health ratio (0-1)."""
        health = getattr(unit, "health", 0)
        health_max = getattr(unit, "health_max", 0)
        if not health_max:
            return 1.0
        return max(0.0, min(1.0, health / health_max))

    @staticmethod
    def _enemy_within(enemy_units, unit, radius: float) -> bool:
        """Check if any enemy is within given radius."""
        if not enemy_units:
            return False
        try:
            for enemy in enemy_units:
                if unit.distance_to(enemy) <= radius:
                    return True
        except Exception:
            return False
        return False

    @staticmethod
    def _get_burrow_abilities(unit_type) -> Tuple:
        """
        Get burrow down and up ability IDs for given unit type.

        Args:
            unit_type: UnitTypeId of the unit

        Returns:
            Tuple of (burrow_down_ability, burrow_up_ability)
        """
        if not AbilityId:
            return None, None

        down_map = {
            "ROACH": "BURROWDOWN_ROACH",
            "LURKERMP": "BURROWDOWN_LURKER",
            "BANELING": "BURROWDOWN_BANELING",
            "INFESTOR": "BURROWDOWN_INFESTOR",
            "SWARMHOSTMP": "BURROWDOWN_SWARMHOST",
        }
        up_map = {
            "ROACHBURROWED": "BURROWUP_ROACH",
            "LURKERMPBURROWED": "BURROWUP_LURKER",
            "BANELINGBURROWED": "BURROWUP_BANELING",
            "INFESTORBURROWED": "BURROWUP_INFESTOR",
            "SWARMHOSTBURROWEDMP": "BURROWUP_SWARMHOST",
        }

        unit_name = getattr(unit_type, "name", "")
        
        # Try exact match first
        down_name = down_map.get(unit_name)
        up_name = up_map.get(unit_name)
        
        # Helper for common prefixes/suffixes if exact match fails
        if not down_name and not up_name:
             if "ROACH" in unit_name: 
                 down_name, up_name = "BURROWDOWN_ROACH", "BURROWUP_ROACH"
             elif "LURKER" in unit_name:
                 down_name, up_name = "BURROWDOWN_LURKER", "BURROWUP_LURKER"
             elif "BANELING" in unit_name:
                 down_name, up_name = "BURROWDOWN_BANELING", "BURROWUP_BANELING"
             elif "INFESTOR" in unit_name:
                 down_name, up_name = "BURROWDOWN_INFESTOR", "BURROWUP_INFESTOR"
             elif "SWARMHOST" in unit_name:
                 down_name, up_name = "BURROWDOWN_SWARMHOST", "BURROWUP_SWARMHOST"
             else:
                 down_name, up_name = "BURROWDOWN", "BURROWUP"

        down_ability = getattr(AbilityId, down_name or "BURROWDOWN", None)
        up_ability = getattr(AbilityId, up_name or "BURROWUP", None)
        return down_ability, up_ability
