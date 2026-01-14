# -*- coding: utf-8 -*-
# Re-saved as UTF-8 to fix UnicodeDecodeError when Python imports this module on Windows
from sc2.ids.ability_id import AbilityId  # type: ignore
from sc2.ids.buff_id import BuffId  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore


class QueenManager:
    def __init__(self, bot):
        self.bot = bot
        # Track which queen is assigned to which hatchery for efficient injects
        self.queen_hatchery_assignments: dict = {}  # {queen_tag: hatchery_tag}

    async def manage_queens(self):
        # Performance optimization: Use IntelManager cache (fetch once)
        intel = getattr(self.bot, "intel", None)

        # Use cached townhalls
        if intel and intel.cached_townhalls is not None:
            # cached_townhalls is a list, filter ready ones
            hatcheries = [h for h in intel.cached_townhalls if hasattr(h, 'is_ready') and h.is_ready]
            hatcheries_exists = len(hatcheries) > 0
            hatcheries_list = hatcheries
        else:
            hatcheries = self.bot.townhalls.ready
            hatcheries_exists = hatcheries.exists if hasattr(hatcheries, 'exists') else len(list(hatcheries)) > 0
            hatcheries_list = list(hatcheries) if hatcheries_exists else []

        if not hatcheries_exists:
            return

        # Use cached queens
        if intel and intel.cached_queens is not None:
            queens = intel.cached_queens
            queens_exists = len(queens) > 0 if isinstance(queens, list) else (queens.exists if hasattr(queens, 'exists') else True)
        else:
            queens = self.bot.units(UnitTypeId.QUEEN)
            queens_exists = queens.exists if hasattr(queens, 'exists') else len(list(queens)) > 0

        # Clean up dead queen assignments
        if queens_exists:
            queen_tags = {q.tag for q in queens}
            dead_queens = [
                tag for tag in self.queen_hatchery_assignments.keys() if tag not in queen_tags
            ]
            for dead_tag in dead_queens:
                del self.queen_hatchery_assignments[dead_tag]

        if not queens_exists:
            # Queen production (only if we have hatcheries but no queens)
            if self.bot.can_afford(UnitTypeId.QUEEN):
                # Use list iteration instead of .random to avoid conflicts (repo rule)
                idle_hatcheries = [h for h in hatcheries_list if hasattr(h, 'is_idle') and h.is_idle]
                if idle_hatcheries:
                    try:
                        idle_hatcheries[0].train(
                            UnitTypeId.QUEEN
                        )  # train() is not async, removed await
                    except (AttributeError, TypeError) as e:
                        # Handle case where train() might fail
                        pass
            return

        # Assign queens to hatcheries for efficient injects (if not already assigned)
        hatchery_list = hatcheries_list if isinstance(hatcheries_list, list) else (list(hatcheries) if hasattr(hatcheries, '__iter__') else [])
        queen_list = list(queens) if not isinstance(queens, list) else queens

        # Assign queens to hatcheries (one queen per hatchery for optimal injects)
        for i, hatch in enumerate(hatchery_list):
            if i < len(queen_list):
                queen_tag = queen_list[i].tag
                if queen_tag not in self.queen_hatchery_assignments:
                    self.queen_hatchery_assignments[queen_tag] = hatch.tag

        # Queen abilities - process all queens (limited by CPU optimization in main loop)
        for queen in queen_list:
            if not queen.is_ready:
                continue

            # Larva inject (energy >= 25) - Priority 1
            # Use explicit ready queen filter and per-hatchery check to avoid missed injects
            # FIXED: Only skip inject if larva count is EXTREMELY high (>100), not at 30
            current_larva_count = self.bot.units(UnitTypeId.LARVA).amount
            if current_larva_count > 100:
                # Too many larvae already - skip inject to save energy for other abilities
                if getattr(self.bot, "iteration", 0) % 200 == 0:
                    print(
                        f"[QUEEN MANAGER] Skipping inject - {current_larva_count} larvae already available"
                    )
                continue

            ready_queens = [q for q in queen_list if q.energy >= 25]
            if ready_queens:
                for hatch in hatchery_list:
                    # Skip if hatchery already has an active inject buff
                    has_inject_buff = False
                    try:
                        inject_buff = getattr(BuffId, "QUEENSTACKINJECT", None)
                        if inject_buff and hasattr(hatch, "has_buff"):
                            has_inject_buff = hatch.has_buff(inject_buff)  # type: ignore[misc]
                    except Exception:
                        has_inject_buff = False

                    if has_inject_buff:
                        continue

                    # Find queens within 20 range of the hatchery (increased from 15 for better coverage)
                    nearby_queens = [q for q in ready_queens if q.distance_to(hatch) < 20]
                    if nearby_queens:
                        # Choose closest queen to the hatchery
                        queen_to_use = min(nearby_queens, key=lambda q: q.distance_to(hatch))

                        # Allow queens that are idle OR moving to inject (improves responsiveness)
                        if queen_to_use.is_idle or queen_to_use.is_moving:
                            try:
                                await self.bot.do(queen_to_use(AbilityId.EFFECT_INJECTLARVA, hatch))
                                # Update assignment to current hatchery for tracking
                                self.queen_hatchery_assignments[queen_to_use.tag] = hatch.tag

                                # Success debug message (throttled)
                                if getattr(self.bot, "iteration", 0) % 50 == 0:
                                    print(
                                        f"[SUCCESS] {hatch.tag}¿¡ ÆßÇÎ ¿Ï·á! ¿©¿Õ ¿¡³ÊÁö: {queen_to_use.energy}"
                                    )
                            except Exception:
                                # Silently ignore transient failures (network/issue in SC2 API)
                                pass

            # Transfuse (energy >= 50) - Priority 2 (only if not injecting)
            # Performance optimization: Use IntelManager cache + distance calculation optimization
            if queen.energy >= 50:
                # Check if queen is not busy with inject
                is_busy = queen.is_attacking or (queen.orders and len(queen.orders) > 0)

                if not is_busy:
                    heal_range_squared = 8 * 8  # 8^2 = 64 (transfuse range)

                    # Priority 1: Heal other queens (they're expensive and critical)
                    nearby_queens = [
                        q
                        for q in queen_list
                        if q.tag != queen.tag
                        and hasattr(q, "health_percentage")
                        and q.health_percentage < 0.6  # Heal queens at 60% health
                        and q.distance_to(queen.position) ** 2 < heal_range_squared
                    ]

                    # Priority 2: Heal expensive/valuable military units
                    nearby_military = []
                    if intel and intel.cached_military is not None:
                        nearby_military = [
                            u
                            for u in intel.cached_military
                            if hasattr(u, "health_percentage")
                            and u.health_percentage < 0.5
                            and u.distance_to(queen.position) ** 2 < heal_range_squared
                        ]
                    else:
                        # Fallback: Direct filtering (distance calculation optimization)
                        nearby_military = [
                            u
                            for u in self.bot.units
                            if u.type_id
                            in [
                                UnitTypeId.ROACH,
                                UnitTypeId.HYDRALISK,
                                UnitTypeId.RAVAGER,
                                UnitTypeId.LURKER,
                                UnitTypeId.CORRUPTOR,
                                UnitTypeId.MUTALISK,
                            ]
                            and hasattr(u, "health_percentage")
                            and u.health_percentage < 0.5
                            and u.distance_to(queen.position) ** 2 < heal_range_squared
                        ]

                    # Select target: Prioritize queens, then valuable units by health percentage
                    target_unit = None
                    if nearby_queens:
                        # Heal most damaged queen first
                        target_unit = min(nearby_queens, key=lambda u: u.health_percentage)
                    elif nearby_military:
                        # Heal most damaged valuable unit first
                        target_unit = min(nearby_military, key=lambda u: u.health_percentage)

                    if target_unit:
                        try:
                            await self.bot.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, target_unit))
                        except Exception:
                            pass  # Transfuse not available in this version

    async def defend_with_queens(self):
        """
        Queen defense - optimized with IntelManager cache and distance calculation

        Performance optimization:
            - Use IntelManager cache
            - Distance calculation optimization (distance_to_squared)
        """
        # Performance optimization: Use IntelManager cache
        intel = getattr(self.bot, "intel", None)
        if intel and intel.cached_queens is not None:
            queens = intel.cached_queens
        else:
            queens = self.bot.units(UnitTypeId.QUEEN)
        if not queens.exists:
            return

        # Performance optimization: Use IntelManager cache (townhalls)
        # Use list iteration instead of .random to avoid conflicts (repo rule)
        if intel and intel.cached_townhalls is not None:
            townhall_list = list(intel.cached_townhalls) if intel.cached_townhalls.exists else []
        else:
            townhall_list = list(self.bot.townhalls) if self.bot.townhalls.exists else []

        if not townhall_list:
            return

        # Performance optimization: Use IntelManager cache (enemy_units)
        if intel and intel.cached_enemy_units is not None:
            enemy_units = (
                list(intel.cached_enemy_units) if isinstance(intel.cached_enemy_units, list) else []
            )
        else:
            enemy_units = getattr(self.bot, "enemy_units", [])

        if not enemy_units:
            return

        # Performance optimization: Distance calculation optimization (distance_to_squared)
        defend_range_squared = 15 * 15  # 15^2 = 225

        # Assign queens to defend specific hatcheries
        queen_list = list(queens) if queens.exists else []

        for queen in queen_list:
            if not queen.is_ready:
                continue

            # Find the hatchery this queen is assigned to (or closest hatchery)
            assigned_hatch_tag = self.queen_hatchery_assignments.get(queen.tag)
            defend_hatch = None

            if assigned_hatch_tag:
                for th in townhall_list:
                    if th.tag == assigned_hatch_tag:
                        defend_hatch = th
                        break

            # If no assigned hatchery, use closest
            if not defend_hatch:
                defend_hatch = (
                    min(townhall_list, key=lambda th: queen.distance_to(th) ** 2)
                    if townhall_list
                    else None
                )

            if not defend_hatch:
                continue

            defend_point = defend_hatch.position

            # Find enemies near this queen's hatchery
            nearby_enemies = [
                e for e in enemy_units if e.distance_to(defend_point) ** 2 < defend_range_squared
            ]

            if not nearby_enemies:
                continue

            # Priority 1: Air units (queens are excellent anti-air)
            air_enemies = [e for e in nearby_enemies if hasattr(e, "is_flying") and e.is_flying]
            if air_enemies:
                # Prioritize closest air unit
                closest_air = min(air_enemies, key=lambda e: e.distance_to(queen.position) ** 2)
                queen.attack(closest_air)
            else:
                # Priority 2: Ground units (focus on closest threat to hatchery)
                # Attack enemy closest to hatchery (protect the base)
                closest_to_hatch = min(
                    nearby_enemies, key=lambda e: e.distance_to(defend_point) ** 2
                )
                # Only attack if queen is close enough (don't overextend)
                if queen.distance_to(closest_to_hatch) ** 2 < (10 * 10):  # 10 range
                    queen.attack(closest_to_hatch)
