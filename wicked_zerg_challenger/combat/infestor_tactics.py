# -*- coding: utf-8 -*-
"""
Infestor Tactics Controller - Advanced Infestor burrow movement

Features:
1. Burrow Movement: Move while burrowed to avoid detection
2. Flanking: Approach enemy army from behind
3. Infiltration: Sneak into enemy base for Neural Parasite
4. Escape: Burrow move away from threats
"""

from typing import Dict, List, Optional, Set

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
    from sc2.unit import Unit
except ImportError:
    AbilityId = None
    UnitTypeId = None
    UpgradeId = None
    Point2 = None
    Unit = None


class InfestorTacticsController:
    """
    Advanced Infestor tactics with burrow movement.

    Burrow Movement Strategy:
    - Infiltrate enemy bases while burrowed
    - Flank enemy armies
    - Escape from threats
    - Unburrow only when ready to cast spells
    """

    def __init__(
        self,
        infiltration_distance: float = 15.0,  # Distance to infiltrate into enemy base
        flank_distance: float = 8.0,          # Distance to flank behind enemy
        escape_threshold: float = 0.5,        # Health ratio to trigger escape
        energy_threshold: int = 75,           # Minimum energy for infiltration
    ):
        """
        Initialize Infestor tactics controller.

        Args:
            infiltration_distance: How deep to infiltrate enemy base
            flank_distance: Distance to move behind enemy army
            escape_threshold: Health ratio below which to escape
            energy_threshold: Minimum energy for active tactics
        """
        self.infiltration_distance = infiltration_distance
        self.flank_distance = flank_distance
        self.escape_threshold = escape_threshold
        self.energy_threshold = energy_threshold

        # Tactical state tracking
        self.infiltrating: Dict[int, Point2] = {}  # unit_tag -> target_position
        self.flanking: Dict[int, Point2] = {}      # unit_tag -> flank_position
        self.escaping: Set[int] = set()            # unit_tags that are escaping

        self.last_tactic_update: float = 0.0
        self.tactic_update_interval: float = 2.0  # Update every 2 seconds

    def has_burrow_movement(self, bot) -> bool:
        """Check if Burrow Movement upgrade is researched."""
        if not UpgradeId:
            return False
        if hasattr(bot, 'state') and hasattr(bot.state, 'upgrades'):
            return UpgradeId.TUNNELINGCLAWS in bot.state.upgrades
        return False

    def has_burrow(self, bot) -> bool:
        """Check if Burrow upgrade is researched."""
        if not UpgradeId:
            return False
        if hasattr(bot, 'state') and hasattr(bot.state, 'upgrades'):
            return UpgradeId.BURROW in bot.state.upgrades
        return False

    def find_infiltration_target(self, bot) -> Optional[Point2]:
        """
        Find best target for infiltration.

        Priority:
        1. Enemy main base
        2. Enemy natural expansion
        3. Any enemy structure location

        Args:
            bot: Bot instance

        Returns:
            Target position for infiltration
        """
        if not Point2:
            return None

        # Try enemy main base
        if hasattr(bot, 'enemy_start_locations') and bot.enemy_start_locations:
            return bot.enemy_start_locations[0]

        # Try enemy structures
        enemy_structures = getattr(bot, 'enemy_structures', [])
        if enemy_structures and enemy_structures.exists:
            # Prefer townhalls
            townhall_types = {
                UnitTypeId.NEXUS, UnitTypeId.COMMANDCENTER,
                UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS,
                UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE
            }
            for structure in enemy_structures:
                if structure.type_id in townhall_types:
                    return structure.position

            # Any structure
            return enemy_structures.first.position

        return None

    def find_flank_position(
        self,
        infestor: Unit,
        enemy_army_center: Point2,
        bot
    ) -> Optional[Point2]:
        """
        Calculate flanking position behind enemy army.

        Args:
            infestor: The Infestor
            enemy_army_center: Center of enemy army
            bot: Bot instance

        Returns:
            Position behind enemy army
        """
        if not Point2 or not hasattr(bot, 'start_location'):
            return None

        # Calculate direction from our base to enemy
        our_base = bot.start_location
        direction_x = enemy_army_center.x - our_base.x
        direction_y = enemy_army_center.y - our_base.y
        length = (direction_x * direction_x + direction_y * direction_y) ** 0.5

        if length == 0:
            return None

        # Normalize
        norm_x = direction_x / length
        norm_y = direction_y / length

        # Position behind enemy (opposite direction)
        flank_x = enemy_army_center.x + norm_x * self.flank_distance
        flank_y = enemy_army_center.y + norm_y * self.flank_distance

        return Point2((flank_x, flank_y))

    def get_enemy_army_center(self, enemy_units) -> Optional[Point2]:
        """
        Calculate center of enemy army.

        Args:
            enemy_units: All enemy units

        Returns:
            Center position of enemy combat units
        """
        if not enemy_units or not Point2:
            return None

        # Filter combat units only
        combat_units = [
            e for e in enemy_units
            if not getattr(e.type_id, 'name', '').endswith('WORKER')
            and not getattr(e, 'is_structure', False)
        ]

        if not combat_units:
            return None

        # Calculate centroid
        total_x = sum(u.position.x for u in combat_units)
        total_y = sum(u.position.y for u in combat_units)

        return Point2((
            total_x / len(combat_units),
            total_y / len(combat_units)
        ))

    async def execute_burrow_tactics(
        self,
        infestors,
        enemy_units,
        bot,
        current_time: float
    ) -> Set[int]:
        """
        Execute burrow movement tactics.

        Args:
            infestors: All Infestors
            enemy_units: All enemy units
            bot: Bot instance
            current_time: Current game time

        Returns:
            Set of unit tags that performed actions
        """
        if not infestors:
            return set()

        # Check if we have burrow movement
        if not self.has_burrow_movement(bot):
            return set()

        # Limit update frequency
        if current_time - self.last_tactic_update < self.tactic_update_interval:
            return set()

        self.last_tactic_update = current_time
        actions = []
        acted_tags = set()

        # Get enemy army center for flanking
        enemy_army_center = self.get_enemy_army_center(enemy_units)

        for infestor in infestors:
            unit_tag = infestor.tag
            is_burrowed = getattr(infestor, 'is_burrowed', False)
            health_ratio = self._get_health_ratio(infestor)
            energy = getattr(infestor, 'energy', 0)

            # ★ ESCAPE MODE: Low health ★
            if health_ratio < self.escape_threshold and not is_burrowed:
                # Burrow to escape
                if self.has_burrow(bot):
                    burrow_ability = getattr(AbilityId, 'BURROWDOWN_INFESTOR', None)
                    if burrow_ability:
                        try:
                            actions.append(infestor(burrow_ability))
                            self.escaping.add(unit_tag)
                            acted_tags.add(unit_tag)
                            continue
                        except Exception:
                            pass

            elif unit_tag in self.escaping and health_ratio >= 0.8:
                # Stop escaping when healed
                self.escaping.discard(unit_tag)

            # Skip if escaping
            if unit_tag in self.escaping:
                continue

            # ★ INFILTRATION MODE: High energy, target available ★
            if energy >= self.energy_threshold and not unit_tag in self.infiltrating:
                infiltration_target = self.find_infiltration_target(bot)
                if infiltration_target:
                    # Start infiltration
                    self.infiltrating[unit_tag] = infiltration_target

                    # Burrow if not already
                    if not is_burrowed and self.has_burrow(bot):
                        burrow_ability = getattr(AbilityId, 'BURROWDOWN_INFESTOR', None)
                        if burrow_ability:
                            try:
                                actions.append(infestor(burrow_ability))
                                acted_tags.add(unit_tag)
                            except Exception:
                                pass

            # Execute infiltration
            if unit_tag in self.infiltrating:
                target_pos = self.infiltrating[unit_tag]

                # Check if reached target
                if infestor.position.distance_to(target_pos) < 5.0:
                    # Unburrow at target
                    if is_burrowed:
                        unburrow_ability = getattr(AbilityId, 'BURROWUP_INFESTOR', None)
                        if unburrow_ability:
                            try:
                                actions.append(infestor(unburrow_ability))
                                self.infiltrating.pop(unit_tag)
                                acted_tags.add(unit_tag)
                                continue
                            except Exception:
                                pass
                else:
                    # Move towards target while burrowed
                    if is_burrowed:
                        try:
                            actions.append(infestor.move(target_pos))
                            acted_tags.add(unit_tag)
                        except Exception:
                            pass

            # ★ FLANKING MODE: Enemy army detected ★
            elif enemy_army_center and energy >= self.energy_threshold:
                flank_pos = self.find_flank_position(infestor, enemy_army_center, bot)

                if flank_pos:
                    # Start flanking
                    self.flanking[unit_tag] = flank_pos

                    # Burrow if not already
                    if not is_burrowed and self.has_burrow(bot):
                        burrow_ability = getattr(AbilityId, 'BURROWDOWN_INFESTOR', None)
                        if burrow_ability:
                            try:
                                actions.append(infestor(burrow_ability))
                                acted_tags.add(unit_tag)
                            except Exception:
                                pass

                    # Move to flank position
                    if is_burrowed:
                        try:
                            actions.append(infestor.move(flank_pos))
                            acted_tags.add(unit_tag)
                        except Exception:
                            pass

        if actions:
            await bot.do_actions(actions)

        return acted_tags

    @staticmethod
    def _get_health_ratio(unit: Unit) -> float:
        """Get unit's current health ratio (0-1)."""
        health = getattr(unit, 'health', 0)
        health_max = getattr(unit, 'health_max', 1)
        if health_max <= 0:
            return 1.0
        return max(0.0, min(1.0, health / health_max))

    def clear_state(self):
        """Clear all tactical state."""
        self.infiltrating.clear()
        self.flanking.clear()
        self.escaping.clear()
