# -*- coding: utf-8 -*-
"""
Economy Manager - deterministic worker production.
"""

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallbacks for tooling environments

    class UnitTypeId:
        DRONE = "DRONE"
        OVERLORD = "OVERLORD"


from local_training.economy_combat_balancer import EconomyCombatBalancer


class EconomyManager:
    """Manages worker production and basic supply safety."""

    def __init__(self, bot):
        self.bot = bot
        self.balancer = EconomyCombatBalancer(bot)

    async def on_step(self, iteration: int) -> None:
        if not hasattr(self.bot, "larva"):
            return

        await self._train_overlord_if_needed()
        await self._train_drone_if_needed()

    async def _train_overlord_if_needed(self) -> None:
        if not hasattr(self.bot, "supply_left"):
            return

        if self.bot.supply_left >= 2:
            return

        if not self.bot.can_afford(UnitTypeId.OVERLORD):
            return

        larva_unit = self._get_first_larva()
        if not larva_unit:
            return

        try:
            await self.bot.do(larva_unit.train(UnitTypeId.OVERLORD))
        except Exception:
            return

    async def _train_drone_if_needed(self) -> None:
        if not self.balancer.should_train_drone():
            return

        if hasattr(self.bot, "supply_left") and self.bot.supply_left <= 0:
            return

        if not self.bot.can_afford(UnitTypeId.DRONE):
            return

        larva_unit = self._get_first_larva()
        if not larva_unit:
            return

        try:
            await self.bot.do(larva_unit.train(UnitTypeId.DRONE))
        except Exception:
            return

    def _get_first_larva(self):
        larva = getattr(self.bot, "larva", None)
        if not larva:
            return None
        if hasattr(larva, "first"):
            return larva.first
        try:
            return next(iter(larva))
        except Exception:
            return None
