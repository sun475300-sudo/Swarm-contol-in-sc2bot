import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from typing import Any, Dict

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class ProductionResilience:
    """Encapsulates production recovery, larva/resource management, and race counters."""

    def __init__(self, bot: Any) -> None:
        self.bot = bot

    async def fix_production_bottleneck(self) -> None:
        b = self.bot
        try:
            if (
                not b.units(UnitTypeId.SPAWNINGPOOL).exists
                and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0
            ):
                supply_used = getattr(b, "supply_used", 0)
                should_build_pool = supply_used >= 17 and supply_used <= 20
                emergency_build = supply_used > 20 and b.can_afford(UnitTypeId.SPAWNINGPOOL)
                if should_build_pool or emergency_build:
                    if b.can_afford(UnitTypeId.SPAWNINGPOOL):
                        if b.townhalls.exists:
                            try:
                                main_base = b.townhalls.first
                                await b.build(
                                    UnitTypeId.SPAWNINGPOOL,
                                    near=main_base.position.towards(b.game_info.map_center, 5),
                                )
                                if b.iteration % 50 == 0:
                                    print(
                                        f"[TECH BUILD] [{int(b.time)}s] Building Spawning Pool at {supply_used} supply (required for Zergling production)"
                                    )
                                return
                            except Exception as e:
                                if b.iteration % 100 == 0:
                                    print(
                                        f"[TECH BUILD] [{int(b.time)}s] Failed to build Spawning Pool: {e}"
                                    )
            larvae = b.units(UnitTypeId.LARVA)
            if not larvae.exists:
                if b.minerals > 500 and b.already_pending(UnitTypeId.HATCHERY) == 0:
                    if b.townhalls.exists:
                        main_base = b.townhalls.first
                        macro_pos = main_base.position.towards(b.game_info.map_center, 8)
                        try:
                            await b.build(UnitTypeId.HATCHERY, near=macro_pos)
                        except Exception:
                            pass
                return
            if b.supply_left < 4 and b.supply_cap < 200:
                if b.can_afford(UnitTypeId.OVERLORD) and larvae.exists:
                    try:
                        larvae_list = list(larvae)
                        if larvae_list:
                            larvae_list[0].train(UnitTypeId.OVERLORD)
                    except Exception:
                        pass
            spawning_pools = b.units(UnitTypeId.SPAWNINGPOOL).ready
            if spawning_pools.exists:
                larvae_list = list(larvae)
                produced_count = 0
                max_production = min(10, len(larvae_list))
                for i, larva in enumerate(larvae_list[:max_production]):
                    if not larva.is_ready:
                        continue
                    if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
                        try:
                            larva.train(UnitTypeId.ZERGLING)
                            produced_count += 1
                        except Exception:
                            continue
                if produced_count > 0 and b.iteration % 50 == 0:
                    print(
                        f"[PRODUCTION FIX] [{int(b.time)}s] Produced {produced_count} Zerglings (Minerals: {int(b.minerals)}M, Larva: {len(larvae_list)})"
                    )
            roach_warrens = b.units(UnitTypeId.ROACHWARREN).ready
            if roach_warrens.exists:
                larvae_list = list(larvae)
                produced_count = 0
                max_production = min(5, len(larvae_list))
                for i, larva in enumerate(larvae_list[:max_production]):
                    if not larva.is_ready:
                        continue
                    if b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
                        try:
                            larva.train(UnitTypeId.ROACH)
                            produced_count += 1
                        except Exception:
                            continue
            hydra_dens = b.units(UnitTypeId.HYDRALISKDEN).ready
            if hydra_dens.exists:
                larvae_list = list(larvae)
                produced_count = 0
                max_production = min(5, len(larvae_list))
                for i, larva in enumerate(larvae_list[:max_production]):
                    if not larva.is_ready:
                        continue
                    if b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                        try:
                            larva.train(UnitTypeId.HYDRALISK)
                            produced_count += 1
                        except Exception:
                            continue
        except Exception as e:
            if b.iteration % 100 == 0:
                print(f"[WARNING] fix_production_bottleneck error: {e}")

    async def diagnose_production_status(self, iteration: int) -> None:
        b = self.bot
        try:
            if iteration % 50 == 0:
                larvae = b.units(UnitTypeId.LARVA)
                larvae_count = larvae.amount if hasattr(larvae, "amount") else len(list(larvae))
                pending_zerglings = b.already_pending(UnitTypeId.ZERGLING)
                pending_roaches = b.already_pending(UnitTypeId.ROACH)
                pending_hydralisks = b.already_pending(UnitTypeId.HYDRALISK)
                zergling_count = b.units(UnitTypeId.ZERGLING).amount
                roach_count = b.units(UnitTypeId.ROACH).amount
                hydralisk_count = b.units(UnitTypeId.HYDRALISK).amount
                # Check tech buildings - Include near-complete (99%+) as "ready"
                spawning_pool_query = b.structures(UnitTypeId.SPAWNINGPOOL)
                spawning_pool_ready = False
                if spawning_pool_query.ready.exists:
                    spawning_pool_ready = True
                elif spawning_pool_query.exists:
                    try:
                        pool = spawning_pool_query.first
                        if pool.build_progress >= 0.99:
                            spawning_pool_ready = True
                    except Exception:
                        pass

                roach_warren_query = b.structures(UnitTypeId.ROACHWARREN)
                roach_warren_ready = False
                if roach_warren_query.ready.exists:
                    roach_warren_ready = True
                elif roach_warren_query.exists:
                    try:
                        warren = roach_warren_query.first
                        if warren.build_progress >= 0.99:
                            roach_warren_ready = True
                    except Exception:
                        pass

                hydralisk_den_query = b.structures(UnitTypeId.HYDRALISKDEN)
                hydralisk_den_ready = False
                if hydralisk_den_query.ready.exists:
                    hydralisk_den_ready = True
                elif hydralisk_den_query.exists:
                    try:
                        den = hydralisk_den_query.first
                        if den.build_progress >= 0.99:
                            hydralisk_den_ready = True
                    except Exception:
                        pass
                can_afford_zergling = b.can_afford(UnitTypeId.ZERGLING)
                can_afford_roach = b.can_afford(UnitTypeId.ROACH)
                can_afford_hydralisk = b.can_afford(UnitTypeId.HYDRALISK)
                print(f"\n{'=' * 80}")
                print(f"[PRODUCTION DIAGNOSIS] [{int(b.time)}s] Iteration: {iteration}")
                print(f"{'=' * 80}")
                print(f"? Resources:")
                print(f"   Minerals: {int(b.minerals)}M | Vespene: {int(b.vespene)}G")
                print(f"   Supply: {b.supply_used}/{b.supply_cap} (Left: {b.supply_left})")
                print(f"\n? Larva Status:")
                print(f"   Larva Count: {larvae_count}")
                print(
                    f"   Larva Ready: {larvae.ready.exists if hasattr(larvae, 'ready') else 'N/A'}"
                )
                print(f"\n?? Tech Buildings:")
                print(f"   Spawning Pool Ready: {spawning_pool_ready}")
                print(f"   Roach Warren Ready: {roach_warren_ready}")
                print(f"   Hydralisk Den Ready: {hydralisk_den_ready}")
                print(f"\n? Can Afford:")
                print(
                    f"   Zergling: {can_afford_zergling} | Roach: {can_afford_roach} | Hydralisk: {can_afford_hydralisk}"
                )
                print(f"\n? Unit Counts (Current):")
                print(
                    f"   Zerglings: {zergling_count} | Roaches: {roach_count} | Hydralisks: {hydralisk_count}"
                )
                print(f"\n? Pending Units (Including Eggs):")
                print(
                    f"   Zerglings: {pending_zerglings} | Roaches: {pending_roaches} | Hydralisks: {pending_hydralisks}"
                )
                print(f"\n? Diagnosis:")
                if larvae_count == 0:
                    print(
                        f"   ?? NO LARVAE - Production blocked! Need more hatcheries or queen injects."
                    )
                elif larvae_count >= 3 and b.minerals > 500:
                    if spawning_pool_ready and can_afford_zergling and b.supply_left >= 2:
                        print(f"   ? Should produce Zerglings but not producing!")
                        print(
                            f"   ? PROBLEM: Production logic may not be executing or larvae.train() failing"
                        )
                    else:
                        if not spawning_pool_ready:
                            print(f"   ?? Spawning Pool not ready - cannot produce Zerglings")
                        if not can_afford_zergling:
                            print(f"   ?? Cannot afford Zergling (need 50M)")
                        if b.supply_left < 2:
                            print(f"   ?? Supply blocked (need 2 supply)")
                else:
                    print(f"   ? Conditions look normal")
                print(f"{'=' * 80}\n")
        except Exception as e:
            if iteration % 100 == 0:
                print(f"[WARNING] Production diagnosis error: {e}")

    async def build_army_aggressive(self) -> None:
        b = self.bot
        if not b.units(UnitTypeId.LARVA).exists:
            return
        larvae = b.units(UnitTypeId.LARVA).ready
        if b.supply_left < 5 and b.supply_cap < 200:
            if b.can_afford(UnitTypeId.OVERLORD) and not b.already_pending(UnitTypeId.OVERLORD):
                if larvae.exists:
                    larvae_list = list(larvae)
                    if larvae_list:
                        for larva in larvae_list:
                            if larva.is_ready:
                                larva.train(UnitTypeId.OVERLORD)
                                return
        if hasattr(b, "current_build_plan") and "ideal_composition" in b.current_build_plan:
            ideal_comp = b.current_build_plan["ideal_composition"]
        else:
            ideal_comp = await self._determine_ideal_composition()
            if not hasattr(b, "current_build_plan"):
                b.current_build_plan = {}
            b.current_build_plan["ideal_composition"] = ideal_comp
        zerglings = b.units(UnitTypeId.ZERGLING).amount
        roaches = b.units(UnitTypeId.ROACH).amount
        hydralisks = b.units(UnitTypeId.HYDRALISK).amount
        banelings = b.units(UnitTypeId.BANELING).amount
        ravagers = b.units(UnitTypeId.RAVAGER).amount
        total_army = zerglings + roaches + hydralisks + banelings + ravagers
        unit_to_produce = None
        if total_army == 0:
            if b.units(UnitTypeId.SPAWNINGPOOL).ready.exists and b.can_afford(UnitTypeId.ZERGLING):
                unit_to_produce = UnitTypeId.ZERGLING
        else:
            target_hydra = ideal_comp.get(UnitTypeId.HYDRALISK, 0.0)
            target_roach = ideal_comp.get(UnitTypeId.ROACH, 0.0)
            target_ling = ideal_comp.get(UnitTypeId.ZERGLING, 0.0)
            target_baneling = ideal_comp.get(UnitTypeId.BANELING, 0.0)
            target_ravager = ideal_comp.get(UnitTypeId.RAVAGER, 0.0)
            current_hydra = hydralisks / total_army if total_army > 0 else 0
            current_roach = roaches / total_army if total_army > 0 else 0
            current_ling = zerglings / total_army if total_army > 0 else 0
            current_baneling = banelings / total_army if total_army > 0 else 0
            current_ravager = ravagers / total_army if total_army > 0 else 0
            deficits = {
                UnitTypeId.HYDRALISK: target_hydra - current_hydra,
                UnitTypeId.ROACH: target_roach - current_roach,
                UnitTypeId.ZERGLING: target_ling - current_ling,
                UnitTypeId.BANELING: target_baneling - current_baneling,
                UnitTypeId.RAVAGER: target_ravager - current_ravager,
            }
            max_deficit_unit = max(deficits.items(), key=lambda x: x[1])[0]
            max_deficit = deficits[max_deficit_unit]
            if max_deficit > 0:
                if max_deficit_unit == UnitTypeId.HYDRALISK:
                    if b.units(UnitTypeId.HYDRALISKDEN).ready.exists and b.can_afford(
                        UnitTypeId.HYDRALISK
                    ):
                        unit_to_produce = UnitTypeId.HYDRALISK
                elif max_deficit_unit == UnitTypeId.ROACH:
                    if b.units(UnitTypeId.ROACHWARREN).ready.exists and b.can_afford(
                        UnitTypeId.ROACH
                    ):
                        unit_to_produce = UnitTypeId.ROACH
                elif max_deficit_unit == UnitTypeId.RAVAGER:
                    roaches_ready = b.units(UnitTypeId.ROACH).ready
                    if roaches_ready.exists and b.can_afford(AbilityId.MORPHTORAVAGER_RAVAGER):
                        try:
                            roaches_ready.random(AbilityId.MORPHTORAVAGER_RAVAGER)
                            return
                        except Exception:
                            pass
                elif max_deficit_unit == UnitTypeId.BANELING:
                    zerglings_ready = b.units(UnitTypeId.ZERGLING).ready
                    if zerglings_ready.exists and b.units(UnitTypeId.BANELINGNEST).ready.exists:
                        if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                            try:
                                zerglings_ready.random(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                return
                            except Exception:
                                pass
                elif max_deficit_unit == UnitTypeId.ZERGLING:
                    if b.units(UnitTypeId.SPAWNINGPOOL).ready.exists and b.can_afford(
                        UnitTypeId.ZERGLING
                    ):
                        unit_to_produce = UnitTypeId.ZERGLING
                if not unit_to_produce:
                    if b.units(UnitTypeId.SPAWNINGPOOL).ready.exists and b.can_afford(
                        UnitTypeId.ZERGLING
                    ):
                        unit_to_produce = UnitTypeId.ZERGLING
        if unit_to_produce and larvae.exists and b.supply_left >= 2:
            try:
                larvae_list = list(larvae)
                if larvae_list:
                    for larva in larvae_list:
                        if larva.is_ready:
                            larva.train(unit_to_produce)
                            break
            except Exception:
                pass

    async def force_resource_dump(self) -> None:
        b = self.bot
        if b.can_afford(UnitTypeId.HATCHERY) and b.already_pending(UnitTypeId.HATCHERY) < 2:
            try:
                await b.expand_now()
            except Exception:
                pass
        if b.units(UnitTypeId.LARVA).exists:
            larvae = b.units(UnitTypeId.LARVA).ready
            if larvae.exists and b.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
                for larva in larvae:
                    if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
                        try:
                            larva.train(UnitTypeId.ZERGLING)
                        except Exception:
                            continue

    async def panic_mode_production(self) -> None:
        b = self.bot
        if b.production:
            await b.production._produce_overlord()
        if b.production:
            await b.production._produce_queen()
        larvae = list(b.units(UnitTypeId.LARVA))
        if larvae and b.supply_left >= 2:
            if b.can_afford(UnitTypeId.ZERGLING):
                spawning_pools = b.units(UnitTypeId.SPAWNINGPOOL).ready
                if spawning_pools:
                    import random

                    random.choice(larvae).train(UnitTypeId.ZERGLING)

    async def build_terran_counters(self) -> None:
        b = self.bot
        if not b.production:
            return
        baneling_nests = [s for s in b.units(UnitTypeId.BANELINGNEST).structure if s.is_ready]
        if not baneling_nests and b.already_pending(UnitTypeId.BANELINGNEST) == 0 and b.can_afford(UnitTypeId.BANELINGNEST):
            spawning_pools = [s for s in b.units(UnitTypeId.SPAWNINGPOOL).structure if s.is_ready]
            if spawning_pools:
                await b.build(UnitTypeId.BANELINGNEST, near=spawning_pools[0])
        roach_warrens = [s for s in b.units(UnitTypeId.ROACHWARREN).structure if s.is_ready]
        if not roach_warrens and b.already_pending(UnitTypeId.ROACHWARREN) == 0 and b.time > 180 and b.can_afford(UnitTypeId.ROACHWARREN):
            if b.townhalls.exists:
                townhalls_list = list(b.townhalls)
                if townhalls_list:
                    await b.build(UnitTypeId.ROACHWARREN, near=townhalls_list[0])
            else:
                await b.build(UnitTypeId.ROACHWARREN, near=b.game_info.map_center)

    async def build_protoss_counters(self) -> None:
        b = self.bot
        if not b.production:
            return
        hydra_dens = [s for s in b.units(UnitTypeId.HYDRALISKDEN).structure if s.is_ready]
        if not hydra_dens and b.already_pending(UnitTypeId.HYDRALISKDEN) == 0 and b.time > 240 and b.can_afford(UnitTypeId.HYDRALISKDEN):
            lairs = [s for s in b.units(UnitTypeId.LAIR).structure if s.is_ready]
            hives = [s for s in b.units(UnitTypeId.HIVE).structure if s.is_ready]
            if lairs or hives:
                if b.townhalls.exists:
                    townhalls_list = list(b.townhalls)
                    if townhalls_list:
                        await b.build(UnitTypeId.HYDRALISKDEN, near=townhalls_list[0])
                else:
                    await b.build(UnitTypeId.HYDRALISKDEN, near=b.game_info.map_center)
        roach_warrens = [s for s in b.units(UnitTypeId.ROACHWARREN).structure if s.is_ready]
        if not roach_warrens and b.already_pending(UnitTypeId.ROACHWARREN) == 0 and b.time > 180 and b.can_afford(UnitTypeId.ROACHWARREN):
            if b.townhalls.exists:
                townhalls_list = list(b.townhalls)
                if townhalls_list:
                    await b.build(UnitTypeId.ROACHWARREN, near=townhalls_list[0])
            else:
                await b.build(UnitTypeId.ROACHWARREN, near=b.game_info.map_center)

    async def build_zerg_counters(self) -> None:
        b = self.bot
        if not b.production:
            return
        roach_warrens = [s for s in b.units(UnitTypeId.ROACHWARREN).structure if s.is_ready]
        if not roach_warrens and b.already_pending(UnitTypeId.ROACHWARREN) == 0 and b.time > 180 and b.can_afford(UnitTypeId.ROACHWARREN):
            if b.townhalls.exists:
                townhalls_list = list(b.townhalls)
                if townhalls_list:
                    await b.build(UnitTypeId.ROACHWARREN, near=townhalls_list[0])
            else:
                await b.build(UnitTypeId.ROACHWARREN, near=b.game_info.map_center)
        baneling_nests = [s for s in b.units(UnitTypeId.BANELINGNEST).structure if s.is_ready]
        if not baneling_nests and b.already_pending(UnitTypeId.BANELINGNEST) == 0 and b.can_afford(UnitTypeId.BANELINGNEST):
            spawning_pools = [s for s in b.units(UnitTypeId.SPAWNINGPOOL).structure if s.is_ready]
            if spawning_pools:
                await b.build(UnitTypeId.BANELINGNEST, near=spawning_pools[0])
        hydra_dens = [s for s in b.units(UnitTypeId.HYDRALISKDEN).structure if s.is_ready]
        if not hydra_dens and b.already_pending(UnitTypeId.HYDRALISKDEN) == 0 and b.time > 300 and b.can_afford(UnitTypeId.HYDRALISKDEN):
            lairs = [s for s in b.units(UnitTypeId.LAIR).structure if s.is_ready]
            hives = [s for s in b.units(UnitTypeId.HIVE).structure if s.is_ready]
            if lairs or hives:
                if b.townhalls.exists:
                    townhalls_list = list(b.townhalls)
                    if townhalls_list:
                        await b.build(UnitTypeId.HYDRALISKDEN, near=townhalls_list[0])
                else:
                    await b.build(UnitTypeId.HYDRALISKDEN, near=b.game_info.map_center)

    async def _determine_ideal_composition(self) -> Dict[UnitTypeId, float]:
        """Reuses bot's composition logic via in-module call."""
        # Directly call the bot's method for now; can be refactored later
        return await self.bot._determine_ideal_composition()
