# -*- coding: utf-8 -*-
"""
Evolution Chamber upgrade manager.

Chooses upgrades based on unit composition and opponent race.
"""

from typing import Dict, List, Optional

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:  # Fallbacks for tooling environments
    UnitTypeId = None
    UpgradeId = None


class EvolutionUpgradeManager:
    """Manages evolution chamber upgrades with dynamic priorities."""

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 44
        self.gas_reserve_threshold = 200

    async def on_step(self, iteration: int) -> None:
        if not UnitTypeId or not UpgradeId:
            return
        if iteration - self.last_update < self.update_interval:
            return

        self.last_update = iteration
        if not hasattr(self.bot, "structures"):
            return

        evo_chambers = self.bot.structures(UnitTypeId.EVOLUTIONCHAMBER).ready
        if not evo_chambers:
            return

        upgrade_order = self._get_upgrade_priority()
        vespene = getattr(self.bot, "vespene", 0)
        gas_constrained = vespene < self.gas_reserve_threshold
        for evo in evo_chambers:
            if hasattr(evo, "is_idle") and not evo.is_idle:
                continue

            for upgrade_id in upgrade_order:
                if gas_constrained and upgrade_id != upgrade_order[0]:
                    continue
                if not self._can_research(upgrade_id):
                    continue
                if not self.bot.can_afford(upgrade_id):
                    continue

                try:
                    await self.bot.do(evo.research(upgrade_id))
                    upgrade_name = getattr(upgrade_id, "name", str(upgrade_id))
                    print(f"[UPGRADE] Researching {upgrade_name}")
                except Exception:
                    continue
                return

    def _get_upgrade_priority(self) -> List[object]:
        composition = self._get_unit_composition()
        enemy_race = self._normalize_enemy_race(getattr(self.bot, "enemy_race", ""))
        enemy_units = getattr(self.bot, "enemy_units", [])

        total = max(1, composition["melee"] + composition["ranged"])
        melee_ratio = composition["melee"] / total
        ranged_ratio = composition["ranged"] / total
        zergling_ratio = composition.get("zergling", 0) / total
        hydra_ratio = composition.get("hydralisk", 0) / total
        roach_ratio = composition.get("roach", 0) / total

        melee_bias = melee_ratio >= 0.7 or zergling_ratio >= 0.7
        ranged_bias = ranged_ratio >= 0.6 or hydra_ratio >= 0.45 or roach_ratio >= 0.5

        priorities = []
        if melee_bias:
            priorities = ["melee", "armor", "missile"]
        elif ranged_bias:
            priorities = ["missile", "armor", "melee"]
        else:
            priorities = ["armor", "melee", "missile"]

        if "terran" in enemy_race or self._has_unit(
            enemy_units, ["MARINE", "MARAUDER"]
        ):
            priorities = ["armor"] + [p for p in priorities if p != "armor"]
        elif "protoss" in enemy_race or self._has_unit(
            enemy_units, ["COLOSSUS", "IMMORTAL"]
        ):
            priorities = ["missile"] + [p for p in priorities if p != "missile"]

        upgrade_order: List[object] = []
        for lane in priorities:
            next_upgrade = self._next_upgrade(lane)
            if next_upgrade:
                upgrade_order.append(next_upgrade)

        return upgrade_order

    def _get_unit_composition(self) -> Dict[str, int]:
        counts = {
            "melee": 0,
            "ranged": 0,
            "zergling": 0,
            "hydralisk": 0,
            "roach": 0,
        }
        if not hasattr(self.bot, "units"):
            return counts

        units = self.bot.units
        for unit in units:
            if unit.type_id in self._melee_unit_types():
                counts["melee"] += 1
                if unit.type_id == UnitTypeId.ZERGLING:
                    counts["zergling"] += 1
            elif unit.type_id in self._ranged_unit_types():
                counts["ranged"] += 1
                if unit.type_id == UnitTypeId.HYDRALISK:
                    counts["hydralisk"] += 1
                if unit.type_id == UnitTypeId.ROACH:
                    counts["roach"] += 1

        return counts

    @staticmethod
    def _has_unit(enemy_units, names: List[str]) -> bool:
        if not UnitTypeId or not enemy_units:
            return False
        for name in names:
            unit_id = getattr(UnitTypeId, name, None)
            if unit_id and any(e.type_id == unit_id for e in enemy_units):
                return True
        return False

    @staticmethod
    def _normalize_enemy_race(value) -> str:
        if value is None:
            return ""
        if hasattr(value, "name"):
            return str(value.name).lower()
        text = str(value).lower()
        if text.startswith("race."):
            return text.split(".", 1)[1]
        return text

    @staticmethod
    def _melee_unit_types() -> List[object]:
        if not UnitTypeId:
            return []
        return [
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ULTRALISK,
        ]

    @staticmethod
    def _ranged_unit_types() -> List[object]:
        if not UnitTypeId:
            return []
        return [
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKER,
        ]

    def _next_upgrade(self, lane: str) -> Optional[object]:
        upgrade_paths = {
            "melee": [
                getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL1", None),
                getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL2", None),
                getattr(UpgradeId, "ZERGMELEEWEAPONSLEVEL3", None),
            ],
            "missile": [
                getattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL1", None),
                getattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL2", None),
                getattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL3", None),
            ],
            "armor": [
                getattr(UpgradeId, "ZERGGROUNDARMORSLEVEL1", None),
                getattr(UpgradeId, "ZERGGROUNDARMORSLEVEL2", None),
                getattr(UpgradeId, "ZERGGROUNDARMORSLEVEL3", None),
            ],
        }

        upgrades = [u for u in upgrade_paths.get(lane, []) if u]
        for upgrade in upgrades:
            if self._is_upgrade_done(upgrade):
                continue
            if self.bot.already_pending_upgrade(upgrade) > 0:
                continue
            if not self._tech_requirement_met(upgrade):
                continue
            return upgrade
        return None

    def _is_upgrade_done(self, upgrade_id) -> bool:
        upgrades = getattr(self.bot, "state", None)
        if upgrades and hasattr(self.bot.state, "upgrades"):
            return upgrade_id in self.bot.state.upgrades
        return False

    def _tech_requirement_met(self, upgrade_id) -> bool:
        if not UnitTypeId:
            return True

        name = getattr(upgrade_id, "name", "")
        if "LEVEL2" in name:
            return self._has_lair()
        if "LEVEL3" in name:
            return self._has_hive()
        return True

    def _has_lair(self) -> bool:
        if not hasattr(self.bot, "structures"):
            return False
        lair = self.bot.structures(UnitTypeId.LAIR)
        hive = self.bot.structures(UnitTypeId.HIVE)
        return bool((lair and lair.ready) or (hive and hive.ready))

    def _has_hive(self) -> bool:
        if not hasattr(self.bot, "structures"):
            return False
        hive = self.bot.structures(UnitTypeId.HIVE)
        return bool(hive and hive.ready)
