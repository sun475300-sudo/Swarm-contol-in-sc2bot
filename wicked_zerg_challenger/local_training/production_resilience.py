# -*- coding: utf-8 -*-
from typing import Any, Dict

from sc2.ids.ability_id import AbilityId  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore

class ProductionResilience:

    def __init__(self, bot: Any) -> None:
        self.bot = bot

        # Shared build reservation map to block duplicate construction across managers
        if not hasattr(self.bot, "build_reservations"):
            self.bot.build_reservations = {}

        # Wrap bot.build once to enforce reservation checks globally
        # Some harnesses (e.g., tests/FakeBot) may not define build; guard to avoid AttributeError
        if hasattr(self.bot, "build") and not hasattr(self.bot, "_build_reservation_wrapped"):
            original_build = self.bot.build

            async def _build_with_reservation(structure_type, *args, **kwargs):
                reservations = getattr(self.bot, "build_reservations", {})
                now = getattr(self.bot, "time", 0.0)
                ts = reservations.get(structure_type)
                # Skip if recently reserved (another manager already issued the build)
                if ts is not None and now - ts < 45.0:
                    return None
                reservations[structure_type] = now
                if structure_type == UnitTypeId.SPAWNINGPOOL:
                    try:
                        if self.bot.structures(UnitTypeId.SPAWNINGPOOL).exists or self.bot.already_pending(UnitTypeId.SPAWNINGPOOL) > 0:
                            # throttle log to reduce spam
                            if int(now) % 10 == 0:
                                print(f"[POOL GUARD] Blocked duplicate Spawning Pool at {int(now)}s")
                            return None
                    except Exception:
                        pass
                return await original_build(structure_type, *args, **kwargs)

            self.bot.build = _build_with_reservation  # type: ignore
            self.bot._build_reservation_wrapped = True

    def _cleanup_build_reservations(self) -> None:
        """Drop stale reservations to avoid permanent blocks."""
        try:
            reservations = getattr(self.bot, "build_reservations", {})
            now = getattr(self.bot, "time", 0.0)
            stale = [sid for sid, ts in reservations.items() if now - ts > 45.0]
            for sid in stale:
                reservations.pop(sid, None)
        except Exception:
            pass

    async def fix_production_bottleneck(self) -> None:
        b = self.bot
        self._cleanup_build_reservations()
        try:
            # === EXTREME EMERGENCY: Minerals > 500 - Force all larvae to Zerglings
            # This is the last line of defense against "1,000+ minerals, 0 army" death spiral
            if b.minerals > 500:
                larvae = b.units(UnitTypeId.LARVA)
                if larvae.exists:
                    # Check Spawning Pool status more reliably
                    spawning_pools_ready = b.structures(UnitTypeId.SPAWNINGPOOL).ready
                    spawning_pools_any = b.structures(UnitTypeId.SPAWNINGPOOL)
                    pending_pools = b.already_pending(UnitTypeId.SPAWNINGPOOL)
                    
                    # Check for duplicate pool builds - only if NO ready pools exist
                    if not spawning_pools_ready.exists and pending_pools == 0 and b.minerals > 500:
                        if b.townhalls.exists and b.can_afford(UnitTypeId.SPAWNINGPOOL):
                            try:
                                main_base = b.townhalls.first
                                await b.build(
                                    UnitTypeId.SPAWNINGPOOL,
                                    near=main_base.position.towards(b.game_info.map_center, 5),
                                )
                                print(f"[PRODUCTION_RESILIENCE] [{int(b.time)}s] EMERGENCY POOL BUILD [Frame:{b.iteration}] Minerals:{int(b.minerals)} Larvae:{len(list(larvae))} Supply:{b.supply_used}/{b.supply_cap}")
                            except Exception as e:
                                if b.iteration % 100 == 0:
                                    print(f"[ERROR] Failed to emergency-build Spawning Pool: {e}")
                        return  # Exit and wait for Spawning Pool to complete
                    
                    # If Spawning Pool is ready, force Zergling production
                    if spawning_pools_ready.exists:
                        # IMPROVED: Force ALL available larvae to produce Zerglings immediately
                        zergling_produced = 0
                        larvae_list = list(larvae) if larvae.exists else []
                        
                        # IMPROVED: ´õ Àû±ØÀûÀ¸·Î ¸ðµç ¶ó¹Ù »ç¿ë
                        for larva in larvae_list:
                            if not hasattr(larva, 'is_ready') or not larva.is_ready:
                                continue
                            
                            # IMPROVED: ÀÎ±¸¼ö Ã¼Å©¸¦ ¸ÕÀúÇÏ¿© ´ë±ºÁÖ »ý»ê ÇÊ¿ä ½Ã ¾Ë¸²
                            if b.supply_left < 1:
                                # ÀÎ±¸¼ö ºÎÁ· - ´ë±ºÁÖ »ý»ê ÇÊ¿ä
                                if b.can_afford(UnitTypeId.OVERLORD) and larvae_list:
                                    try:
                                        await larvae_list[0].train(UnitTypeId.OVERLORD)
                                        print(f"[EXTREME EMERGENCY] Produced Overlord for supply (minerals: {int(b.minerals)})")
                                        return
                                    except Exception:
                                        pass
                                break  # ÀÎ±¸¼ö ºÎÁ·ÇÏ¸é Áß´Ü
                            
                            if b.can_afford(UnitTypeId.ZERGLING):
                                try:
                                    await larva.train(UnitTypeId.ZERGLING)
                                    zergling_produced += 1
                                except Exception as e:
                                    if b.iteration % 50 == 0:
                                        print(f"[ERROR] Failed to force Zergling: {e}")
                                    break  # ÇÑ ¸¶¸® ½ÇÆÐÇÏ¸é Áß´Ü
                            else:
                                # ÀÚ¿ø ºÎÁ·ÇÏ¸é Áß´Ü
                                break
                        
                        if zergling_produced > 0:
                            print(f"[EXTREME EMERGENCY] Produced {zergling_produced} Zerglings (M:{int(b.minerals)}, larvae:{len(larvae_list)})")
                        elif b.iteration % 50 == 0:
                            print(f"[WARNING] No Zerglings produced: larvae={len(larvae_list)}, minerals={int(b.minerals)}, supply={b.supply_left}, can_afford={b.can_afford(UnitTypeId.ZERGLING)}")
                        
                        if zergling_produced > 0:
                            return  # Exit after emergency production
            
            # Gas starvation handler: if vespene is zero and no extractor in progress, build one
            try:
                if getattr(b, "vespene", 0) <= 0:
                    extractors = b.structures(UnitTypeId.EXTRACTOR) if hasattr(b, "structures") else []
                    if not extractors.exists and b.already_pending(UnitTypeId.EXTRACTOR) == 0:
                        geysers = b.vespene_geyser if hasattr(b, "vespene_geyser") else []
                        if geysers:
                            target = geysers.first if hasattr(geysers, "first") else list(geysers)[0]
                            if b.can_afford(UnitTypeId.EXTRACTOR):
                                await b.build(UnitTypeId.EXTRACTOR, target)
            except Exception:
                pass

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
                            await larvae_list[0].train(UnitTypeId.OVERLORD)
                    except Exception:
                        pass
            
            # ??? AGGRESSIVE OVERLORD PRODUCTION: When minerals > 1,000, produce 3-5 Overlords at once
            # This creates a supply buffer (12-20) for aggressive army production
            if b.minerals > 500 and b.supply_left < 20 and larvae.exists:
                overlords_to_produce = min(5, len(larvae) // 2)  # Produce 3-5 overlords
                overlords_produced = 0
                larvae_list = list(larvae)
                for larva in larvae_list:
                    if not larva.is_ready:
                        continue
                    if overlords_produced >= overlords_to_produce:
                        break
                    if b.can_afford(UnitTypeId.OVERLORD):
                        try:
                            await larva.train(UnitTypeId.OVERLORD)
                            overlords_produced += 1
                        except Exception:
                            pass
                if overlords_produced > 0 and b.iteration % 50 == 0:
                    print(f"[OVERLORD BULK PRODUCTION] [{int(b.time)}s] Produced {overlords_produced} Overlords (M:{int(b.minerals)} > 1,000)")
            
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
                            await larva.train(UnitTypeId.ZERGLING)
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
                            await larva.train(UnitTypeId.ROACH)
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
                            await larva.train(UnitTypeId.HYDRALISK)
                            produced_count += 1
                        except Exception:
                            continue
        except Exception as e:
            if b.iteration % 100 == 0:
                print(f"[WARNING] fix_production_bottleneck error: {e}")

    async def diagnose_production_status(self, iteration: int) -> None:
        """
        IMPROVED: Log optimization - Use DEBUG level for frequent diagnostic logs
        This function runs every 50 iterations, so detailed logging should be at DEBUG level
        to prevent I/O overload during real-time game execution.
        """
        b = self.bot
        try:
            # IMPROVED: Only log at DEBUG level during training to reduce I/O overhead
            # Use logger if available, otherwise use print only for critical issues
            try:
                from loguru import logger as loguru_logger
                use_logger = True
            except ImportError:
                use_logger = False
                loguru_logger = None
            
            # Check if we're in training mode (reduce logging frequency)
            is_training = getattr(b, 'train_mode', False)
            
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
                
                # IMPROVED: Use DEBUG level for detailed logs during training
                # Only print critical issues at INFO level
                if is_training and use_logger:
                    # Training mode: Use DEBUG level to reduce I/O overhead
                    loguru_logger.debug(f"[PRODUCTION DIAGNOSIS] [{int(b.time)}s] Iteration: {iteration}")
                    loguru_logger.debug(f"Resources: M:{int(b.minerals)} G:{int(b.vespene)} Supply:{b.supply_used}/{b.supply_cap}")
                    loguru_logger.debug(f"Larva: {larvae_count} | Tech: Pool:{spawning_pool_ready} Warren:{roach_warren_ready} Den:{hydralisk_den_ready}")
                    loguru_logger.debug(f"Units: Z:{zergling_count} R:{roach_count} H:{hydralisk_count} | Pending: Z:{pending_zerglings} R:{pending_roaches} H:{pending_hydralisks}")
                    
                    # Only log critical issues at INFO level
                    if larvae_count == 0:
                        loguru_logger.warning(f"[PRODUCTION] NO LARVAE - Production blocked!")
                    elif larvae_count >= 3 and b.minerals > 500 and spawning_pool_ready and can_afford_zergling and b.supply_left >= 2:
                        loguru_logger.warning(f"[PRODUCTION] Should produce Zerglings but not producing!")
                else:
                    # Non-training mode or no logger: Use print (for debugging)
                    # But reduce frequency - only every 500 iterations instead of 50
                    if iteration % 500 == 0:
                        print(f"\n[PRODUCTION DIAGNOSIS] [{int(b.time)}s] Iteration: {iteration}")
                        print(f"Resources: M:{int(b.minerals)} G:{int(b.vespene)} Supply:{b.supply_used}/{b.supply_cap}")
                        print(f"Larva: {larvae_count} | Tech: Pool:{spawning_pool_ready} Warren:{roach_warren_ready} Den:{hydralisk_den_ready}")
                        print(f"Units: Z:{zergling_count} R:{roach_count} H:{hydralisk_count}")
                        
                        if larvae_count == 0:
                            print(f"[WARNING] NO LARVAE - Production blocked!")
                        elif larvae_count >= 3 and b.minerals > 500 and spawning_pool_ready and can_afford_zergling and b.supply_left >= 2:
                            print(f"[WARNING] Should produce Zerglings but not producing!")
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
        
        # ??? EMERGENCY DEFENSE: Build Spine Crawlers at 2:30+ if enemy detected
        # Prevents 3-minute defeat when bot has 0 army
        if b.time > 150 and b.already_pending(UnitTypeId.SPINECRAWLER) == 0:
            spine_crawlers = b.units(UnitTypeId.SPINECRAWLER)
            spine_count = spine_crawlers.amount if hasattr(spine_crawlers, 'amount') else len(list(spine_crawlers))
            
            # Check if enemy is nearby (scouting system should detect this)
            intel = getattr(b, "intel", None)
            enemy_near_base = False
            if intel and hasattr(intel, "enemy_units_near_base"):
                enemy_near_base = intel.enemy_units_near_base
            
            # Build 1-2 Spine Crawlers for defense if conditions met
            if (enemy_near_base or b.time > 180) and spine_count < 2 and b.can_afford(UnitTypeId.SPINECRAWLER):
                if b.townhalls.exists:
                    try:
                        main_base = b.townhalls.first
                        # Place Spine Crawler in front of base (towards enemy)
                        defense_pos = main_base.position.towards(b.game_info.map_center, 8)
                        await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                        if b.iteration % 50 == 0:
                            print(f"[EMERGENCY DEFENSE] [{int(b.time)}s] Building Spine Crawler for defense")
                    except Exception as e:
                        if b.iteration % 100 == 0:
                            print(f"[EMERGENCY DEFENSE] Failed to build Spine Crawler: {e}")
        
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
            # CRITICAL: Check for duplicate construction before building
            if not b.structures(UnitTypeId.BANELINGNEST).exists:
                spawning_pools = [s for s in b.units(UnitTypeId.SPAWNINGPOOL).structure if s.is_ready]
                if spawning_pools:
                    await b.build(UnitTypeId.BANELINGNEST, near=spawning_pools[0])
        roach_warrens = [s for s in b.units(UnitTypeId.ROACHWARREN).structure if s.is_ready]
        if not roach_warrens and b.already_pending(UnitTypeId.ROACHWARREN) == 0 and b.time > 180 and b.can_afford(UnitTypeId.ROACHWARREN):
            # CRITICAL: Check for duplicate construction before building
            if not b.structures(UnitTypeId.ROACHWARREN).exists:
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