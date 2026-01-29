# -*- coding: utf-8 -*-
"""
Baneling Tactics Controller - Advanced Baneling micro

Features:
1. Land Mine Mode: Burrow Banelings in strategic locations
2. Auto-unburrow and explode when enemies pass
3. Choke point mining
4. Expansion path mining
"""

from typing import Dict, List, Optional, Set, Tuple

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


class BanelingTacticsController:
    """
    Advanced Baneling tactics controller.

    Land Mine Strategy:
    - Place Banelings in choke points
    - Place along enemy expansion paths
    - Auto-unburrow when enemies approach
    - Explode for maximum damage
    """

    def __init__(
        self,
        mine_spacing: float = 2.5,           # Minimum distance between mines
        unburrow_range: float = 3.5,         # Range to unburrow
        explode_range: float = 2.2,          # Range to auto-explode
        min_targets_for_explode: int = 3,    # Minimum enemies to explode
    ):
        """
        Initialize Baneling tactics controller.

        Args:
            mine_spacing: Minimum distance between burrowed Banelings
            unburrow_range: Distance at which to unburrow
            explode_range: Distance at which to auto-explode
            min_targets_for_explode: Minimum enemy count for auto-explode
        """
        self.mine_spacing = mine_spacing
        self.unburrow_range = unburrow_range
        self.explode_range = explode_range
        self.min_targets_for_explode = min_targets_for_explode

        # Land mine state tracking
        self.active_mines: Dict[int, Point2] = {}  # unit_tag -> position
        self.mine_positions: Set[Tuple[float, float]] = set()  # Occupied positions
        self.last_mine_check: float = 0.0
        self.mine_check_interval: float = 1.0  # Check every second

    def can_burrow(self, bot) -> bool:
        """Check if burrow upgrade is available."""
        if not UpgradeId:
            return False
        if hasattr(bot, 'state') and hasattr(bot.state, 'upgrades'):
            return UpgradeId.BURROW in bot.state.upgrades
        return False

    def find_mine_positions(
        self,
        bot,
        count: int = 5
    ) -> List[Point2]:
        """
        Find strategic positions for Baneling land mines.

        Priority locations:
        1. Choke points near our expansions
        2. Enemy expansion paths
        3. Main army path

        Args:
            bot: Bot instance
            count: Number of positions to find

        Returns:
            List of Point2 positions for mines
        """
        if not Point2:
            return []

        positions = []

        # 1. Choke points near our bases
        if hasattr(bot, 'townhalls') and bot.townhalls.exists:
            for townhall in bot.townhalls:
                # Get expansion locations
                expansions = getattr(bot, 'expansion_locations_list', [])
                if not expansions:
                    continue

                # Find nearby expansions (potential enemy attack paths)
                nearby_expos = [
                    exp for exp in expansions
                    if townhall.position.distance_to(exp) < 30
                    and townhall.position.distance_to(exp) > 5
                ]

                for expo in nearby_expos[:2]:  # Limit to 2 per base
                    # Position between our base and expansion
                    direction = expo - townhall.position
                    mine_pos = townhall.position + direction * 0.6

                    # Check if position is available
                    if self._is_position_available(mine_pos):
                        positions.append(mine_pos)
                        if len(positions) >= count:
                            return positions

        # 2. Enemy expansion paths (if we know enemy location)
        if hasattr(bot, 'enemy_start_locations') and bot.enemy_start_locations:
            enemy_start = bot.enemy_start_locations[0]
            expansions = getattr(bot, 'expansion_locations_list', [])

            if expansions:
                # Find closest expansion to enemy
                enemy_natural = min(
                    expansions,
                    key=lambda exp: exp.distance_to(enemy_start)
                )

                # Place mine near enemy natural
                direction = enemy_natural - enemy_start
                mine_pos = enemy_start + direction * 0.7

                if self._is_position_available(mine_pos):
                    positions.append(mine_pos)

        # 3. Map center (main army path)
        if hasattr(bot, 'game_info') and len(positions) < count:
            map_center = bot.game_info.map_center
            if hasattr(bot, 'start_location'):
                # Position between our start and map center
                direction = map_center - bot.start_location
                mine_pos = bot.start_location + direction * 0.5

                if self._is_position_available(mine_pos):
                    positions.append(mine_pos)

        return positions[:count]

    def _is_position_available(self, position: Point2) -> bool:
        """
        Check if position is available for a mine.

        Args:
            position: Position to check

        Returns:
            True if no mine is already placed nearby
        """
        pos_tuple = (round(position.x, 1), round(position.y, 1))

        # Check against existing mines
        for existing_pos in self.mine_positions:
            dx = existing_pos[0] - pos_tuple[0]
            dy = existing_pos[1] - pos_tuple[1]
            distance = (dx * dx + dy * dy) ** 0.5

            if distance < self.mine_spacing:
                return False

        return True

    def register_mine(self, unit_tag: int, position: Point2):
        """Register a Baneling as an active mine."""
        self.active_mines[unit_tag] = position
        pos_tuple = (round(position.x, 1), round(position.y, 1))
        self.mine_positions.add(pos_tuple)

    def unregister_mine(self, unit_tag: int):
        """Remove a Baneling from active mines."""
        if unit_tag in self.active_mines:
            position = self.active_mines[unit_tag]
            pos_tuple = (round(position.x, 1), round(position.y, 1))
            self.mine_positions.discard(pos_tuple)
            del self.active_mines[unit_tag]

    async def deploy_land_mines(
        self,
        banelings,
        bot,
        current_time: float
    ) -> Set[int]:
        """
        Deploy Banelings as land mines.

        Args:
            banelings: Available Banelings
            bot: Bot instance
            current_time: Current game time

        Returns:
            Set of unit tags that were deployed as mines
        """
        if not banelings or not self.can_burrow(bot):
            return set()

        # Limit check frequency
        if current_time - self.last_mine_check < self.mine_check_interval:
            return set()

        self.last_mine_check = current_time
        deployed = set()

        # Find available Banelings (not burrowed, not already mines)
        available = [
            b for b in banelings
            if not getattr(b, 'is_burrowed', False)
            and b.tag not in self.active_mines
        ]

        if not available:
            return set()

        # Find mine positions
        needed_positions = len(available)
        mine_positions = self.find_mine_positions(bot, needed_positions)

        if not mine_positions:
            return set()

        # Deploy Banelings
        actions = []
        for baneling, target_pos in zip(available, mine_positions):
            # Move to position
            try:
                actions.append(baneling.move(target_pos))

                # If close enough, burrow
                if baneling.position.distance_to(target_pos) < 1.0:
                    burrow_ability = getattr(AbilityId, 'BURROWDOWN_BANELING', None)
                    if burrow_ability:
                        actions.append(baneling(burrow_ability))
                        self.register_mine(baneling.tag, target_pos)
                        deployed.add(baneling.tag)
            except Exception:
                continue

        if actions:
            await bot.do_actions(actions)

        return deployed

    async def manage_land_mines(
        self,
        banelings,
        enemy_units,
        bot
    ) -> Set[int]:
        """
        Manage active land mines - unburrow and explode when enemies approach.

        Args:
            banelings: All Banelings
            enemy_units: All enemy units
            bot: Bot instance

        Returns:
            Set of unit tags that performed actions
        """
        if not banelings or not enemy_units:
            return set()

        actions = []
        acted_tags = set()

        # Check each burrowed Baneling
        burrowed_banelings = [
            b for b in banelings
            if getattr(b, 'is_burrowed', False)
            and b.tag in self.active_mines
        ]

        for baneling in burrowed_banelings:
            # Find nearby enemies
            nearby_enemies = [
                e for e in enemy_units
                if baneling.position.distance_to(e.position) <= self.unburrow_range
            ]

            if nearby_enemies:
                # Unburrow when enemies approach
                unburrow_ability = getattr(AbilityId, 'BURROWUP_BANELING', None)
                if unburrow_ability:
                    try:
                        actions.append(baneling(unburrow_ability))
                        self.unregister_mine(baneling.tag)
                        acted_tags.add(baneling.tag)
                    except Exception:
                        continue

        # Check unburrowed Banelings for auto-explode
        unburrowed_banelings = [
            b for b in banelings
            if not getattr(b, 'is_burrowed', False)
        ]

        for baneling in unburrowed_banelings:
            # Find very close enemies
            close_enemies = [
                e for e in enemy_units
                if baneling.position.distance_to(e.position) <= self.explode_range
            ]

            # Auto-explode if enough enemies
            if len(close_enemies) >= self.min_targets_for_explode:
                explode_ability = getattr(AbilityId, 'EFFECT_EXPLODE', None)
                if explode_ability:
                    try:
                        actions.append(baneling(explode_ability))
                        acted_tags.add(baneling.tag)
                    except Exception:
                        continue

        if actions:
            await bot.do_actions(actions)

        return acted_tags

    def get_active_mine_count(self) -> int:
        """Get number of active land mines."""
        return len(self.active_mines)

    def clear_dead_mines(self, alive_tags: Set[int]):
        """Remove mines that no longer exist."""
        dead_tags = set(self.active_mines.keys()) - alive_tags
        for tag in dead_tags:
            self.unregister_mine(tag)
