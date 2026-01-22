#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit factory - larva production with gas reservation logic.

Keeps gas-heavy units from being starved by mineral-only spam.
"""

from typing import Iterable, List, Optional

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallbacks for tooling environments
    UnitTypeId = None


class UnitFactory:
    def __init__(self, bot):
        self.bot = bot
        self.min_gas_reserve = 100
        self.min_mineral_reserve_for_gas = 150
        self.gas_unit_ratio_target = 0.35
        self.larva_gas_ratio = 0.4
        self.larva_pressure_threshold = 6
        self.max_larva_spend_per_step = 3

    async def on_step(self, iteration: int) -> None:
        if not UnitTypeId or not hasattr(self.bot, "larva"):
            return

        larva = self.bot.larva
        if not larva:
            return

        if hasattr(self.bot, "supply_left") and self.bot.supply_left <= 0:
            return

        minerals = getattr(self.bot, "minerals", 0)
        vespene = getattr(self.bot, "vespene", 0)
        gas_units = self._count_gas_units()
        total_units = max(1, self._count_combat_units())
        gas_ratio = gas_units / total_units
        can_spend_gas = vespene >= self.min_gas_reserve
        queue = self._build_priority_queue(
            minerals=minerals,
            vespene=vespene,
            gas_ratio=gas_ratio,
            gas_units=gas_units,
            larva_count=len(larva),
            can_spend_gas=can_spend_gas,
        )

        to_spend = 0
        for larva_unit in larva:
            if to_spend >= self.max_larva_spend_per_step:
                break

            unit_type = self._pick_unit(queue)
            if not unit_type:
                break

            try:
                await self.bot.do(larva_unit.train(unit_type))
                to_spend += 1
            except Exception:
                continue

    def _pick_unit(self, queue: List[object]) -> Optional[object]:
        for unit_type in queue:
            if self._can_train(unit_type):
                return unit_type
        return None

    def _can_train(self, unit_type) -> bool:
        if not self.bot.can_afford(unit_type):
            return False
        if not self._requirements_met(unit_type):
            return False
        return True

    def _requirements_met(self, unit_type) -> bool:
        if not hasattr(self.bot, "structures"):
            return True

        requirements = {
            UnitTypeId.ZERGLING: UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.BANELING: UnitTypeId.BANELINGNEST,
            UnitTypeId.ROACH: UnitTypeId.ROACHWARREN,
            UnitTypeId.RAVAGER: UnitTypeId.ROACHWARREN,
            UnitTypeId.HYDRALISK: UnitTypeId.HYDRALISKDEN,
            UnitTypeId.LURKER: UnitTypeId.LURKERDENMP,
        }
        required = requirements.get(unit_type)
        if not required:
            return True

        structures = self.bot.structures(required)
        return bool(structures and structures.ready)

    def _build_priority_queue(
        self,
        minerals: int,
        vespene: int,
        gas_ratio: float,
        gas_units: int,
        larva_count: int,
        can_spend_gas: bool,
    ) -> List[object]:
        gas_priority = can_spend_gas and gas_ratio < self.gas_unit_ratio_target
        larva_gas_target = max(1, int(larva_count * self.larva_gas_ratio))
        gas_shortfall = gas_units < larva_gas_target
        mineral_guard = minerals < self.min_mineral_reserve_for_gas

        allow_mineral_mix = not (gas_priority and (gas_shortfall or mineral_guard))
        if gas_priority and larva_count >= self.larva_pressure_threshold:
            allow_mineral_mix = allow_mineral_mix or minerals >= self.min_mineral_reserve_for_gas * 2

        queue: List[object] = []
        if gas_priority:
            queue.extend(self._filter_units(self._gas_unit_table(), vespene))
            if allow_mineral_mix:
                queue.extend(self._filter_units(self._mineral_unit_table(), vespene))
        else:
            if allow_mineral_mix:
                queue.extend(self._filter_units(self._mineral_unit_table(), vespene))
            queue.extend(self._filter_units(self._gas_unit_table(), vespene))

        if not queue:
            queue = [entry["unit"] for entry in self._gas_unit_table() + self._mineral_unit_table()]
        return queue

    def _filter_units(self, table: List[dict], vespene: int) -> List[object]:
        queue: List[object] = []
        for entry in table:
            unit_type = entry["unit"]
            max_ratio = entry.get("max_ratio")
            min_gas = entry.get("min_gas", 0)
            if max_ratio is not None and self._unit_ratio(unit_type) >= max_ratio:
                continue
            if vespene < min_gas:
                continue
            queue.append(unit_type)
        return queue

    def _gas_unit_table(self) -> List[dict]:
        return [
            {"unit": UnitTypeId.HYDRALISK, "min_gas": 50, "max_ratio": 0.45},
            {"unit": UnitTypeId.ROACH, "min_gas": 25, "max_ratio": 0.5},
            {"unit": UnitTypeId.RAVAGER, "min_gas": 25, "max_ratio": 0.35},
            {"unit": UnitTypeId.LURKER, "min_gas": 75, "max_ratio": 0.2},
            {"unit": UnitTypeId.ULTRALISK, "min_gas": 150, "max_ratio": 0.15},
        ]

    def _mineral_unit_table(self) -> List[dict]:
        return [
            {"unit": UnitTypeId.ZERGLING, "max_ratio": 0.7},
            {"unit": UnitTypeId.BANELING, "max_ratio": 0.35},
        ]

    def _count_combat_units(self) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        units = self.bot.units
        combat_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKER,
            UnitTypeId.ULTRALISK,
        }
        return sum(1 for unit in units if unit.type_id in combat_types)

    def _count_gas_units(self) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        units = self.bot.units
        gas_types = {
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKER,
            UnitTypeId.ULTRALISK,
        }
        return sum(1 for unit in units if unit.type_id in gas_types)

    def _count_unit_type(self, unit_type) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        units = self.bot.units
        return sum(1 for unit in units if unit.type_id == unit_type)

    def _unit_ratio(self, unit_type) -> float:
        total = max(1, self._count_combat_units())
        return self._count_unit_type(unit_type) / total
