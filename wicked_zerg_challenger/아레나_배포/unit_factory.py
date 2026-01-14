# -*- coding: utf-8 -*-
"""
================================================================================
                    🎖️ Unit Production Management (production_manager.py)
================================================================================
Core loop for producing combat units and managing supply.

Core Features:
    1. Predictive Overlord production (prevent supply block)
    2. Drone production (economy)
    3. Queen production (for larvae injection)
    4. Tech-based military unit production (Zergling → Roach → Hydralisk)
    5. Counter-based unit selection (Counter-Build)
================================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    pass

from typing import Dict, Optional

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

from config import EnemyRace, GamePhase


# Logger setup
try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class UnitFactory:
    """Unit Production Specialist"""

    def __init__(self, production_manager):
        self.pm = production_manager
        self.bot = production_manager.bot
        self.config = production_manager.config

    async def _produce_army(self, game_phase: GamePhase, build_plan: Optional[Dict] = None):
        """
        Military unit production

        Production priority (tech-based):
            1. CounterPunchManager priority (when enemy units detected)
            2. Hydralisk (requires Hydralisk Den)
            3. Roach (requires Roach Warren)
            4. Zergling (basic)

        Args:
            game_phase: Current game phase
            build_plan: Adaptive build plan (optional)
        """
        b = self.bot

        try:
            larvae = [u for u in b.units(UnitTypeId.LARVA)]
            if not larvae:
                return

            # Supply check
            if b.supply_left < 2:
                return

            # CRITICAL: Larva Saving - Reserve 30% of larvae for tech unit morphing
            # Reserve some larvae for tech unit morphing when enemy attack intent not confirmed
            total_larvae = len(larvae)
            reserved_larvae_count = max(1, int(total_larvae * 0.3))  # Reserve 30%

            # Check if enemy attack intent is detected
            enemy_attacking = False
            intel = getattr(b, "intel", None)
            if intel:
                # Check if enemy is attacking our bases
                if hasattr(intel, "signals") and isinstance(intel.signals, dict):
                    enemy_attacking = intel.signals.get("enemy_attacking_our_bases", False)

                # Check if we're under attack
                if hasattr(intel, "combat") and hasattr(intel.combat, "under_attack"):
                    if intel.combat.under_attack:
                        enemy_attacking = True

            # If enemy is attacking, use all larvae (no saving)
            # Otherwise, save 30% for tech unit morphing
            if enemy_attacking:
                # Emergency: Enemy attacking - use all larvae
                available_larvae = larvae
                reserved_larvae_count = 0
            else:
                # Normal: Save 30% for tech units (Roaches, Hydralisks)
                if total_larvae > reserved_larvae_count:
                    available_larvae = larvae[:-reserved_larvae_count]
                else:
                    available_larvae = []

            # If no available larvae (all reserved), don't produce
            if not available_larvae:
                return

            # Use available_larvae instead of larvae for the rest of the function
            larvae = available_larvae

            # Check CounterPunchManager priority (when counter strategy is active)
            counter_priority = []
            if hasattr(b, "counter_punch") and b.counter_punch:
                if hasattr(b.counter_punch, "get_train_priority"):
                    counter_priority = b.counter_punch.get_train_priority()  # type: ignore

            # If counter priority exists, apply it first
            if counter_priority:
                for unit_type in counter_priority:
                    if await self._try_produce_unit(unit_type, larvae):
                        return
                # If all counter priority units produced, switch to normal production

            # Enemy tech-based customized unit composition switch (highest priority) - Forced trigger
            # CRITICAL: Enhanced responsiveness - When scouting detects enemy tech building, immediately prioritize counter unit production
            tech_based_units = await self._get_tech_based_unit_composition()
            if tech_based_units:
                # Forced trigger: If tech detected recently (within 30 seconds), produce with highest priority
                intel = getattr(b, "intel", None)
                scout = getattr(b, "scout", None)

                tech_detected_recently = False
                detection_time = 0.0

                # Check detection time from IntelManager
                if intel and hasattr(intel, "enemy_tech_detected"):
                    detection_time = intel.enemy_tech_detected.get("detected_time", 0.0)
                    if detection_time > 0 and b.time - detection_time < 30.0:  # Within 30 seconds
                        tech_detected_recently = True

                # Also check from ScoutManager
                if not tech_detected_recently and scout and hasattr(scout, "enemy_tech_detected"):
                    detection_time = scout.enemy_tech_detected.get("detected_time", 0.0)
                    if detection_time > 0 and b.time - detection_time < 30.0:  # Within 30 seconds
                        tech_detected_recently = True

                # Forced trigger: Immediately produce counter units for recently detected tech
                for unit_type in tech_based_units:
                    if await self._try_produce_unit(unit_type, larvae):
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 25 == 0:  # Print more frequently (enhanced responsiveness)
                            if tech_detected_recently:
                                print(
                                    f"[TECH COUNTER - FORCED TRIGGER] [{int(b.time)}s] IMMEDIATE: Producing {unit_type.name} (Tech detected {b.time - detection_time:.1f}s ago)"
                                )
                            else:
                                print(
                                    f"[TECH COUNTER] [{int(b.time)}s] Producing {unit_type.name} based on enemy tech"
                                )
                        return

            # Check if we should use aggressive build (6-pool) against this opponent
            use_aggressive_build = False
            is_eris_opponent = False

            # opponent_tracker merged into strategy_analyzer
            if hasattr(b, "strategy_analyzer") and b.strategy_analyzer:
                use_aggressive_build = b.strategy_analyzer.should_use_aggressive_build()
                # Check if opponent is Eris (top-ranked Zerg bot)
                current_opponent = getattr(b.strategy_analyzer, "current_opponent", None)
                if current_opponent and "eris" in current_opponent.lower():
                    is_eris_opponent = True

            # Eris-specific special build: Fast Baneling + Mutalisk tech
            if is_eris_opponent and b.time < 300:  # During early 5 minutes
                # Build Baneling Nest with priority
                # 🚀 Performance optimization: Use b.structures (faster)
                spawning_pools = list(b.structures(UnitTypeId.SPAWNINGPOOL).ready)
                if (
                    spawning_pools
                    and self._can_build_safely(UnitTypeId.BANELINGNEST)
                    and b.can_afford(UnitTypeId.BANELINGNEST)
                ):
                    try:
                        # Use _try_build_structure for duplicate prevention
                        if await self._try_build_structure(
                            UnitTypeId.BANELINGNEST, near=spawning_pools[0].position
                        ):
                            print(f"[ERIS COUNTER] [{int(b.time)}s] Building Baneling Nest (Eris counter)")
                    except Exception:
                        pass

                # Fast Lair tech (Mutalisk preparation)
                # 🚀 Performance optimization: Use IntelManager cache
                intel = getattr(b, "intel", None)
                if intel and intel.cached_lairs is not None:
                    lairs = list(intel.cached_lairs) if intel.cached_lairs.exists else []
                else:
                    lairs = (
                        list(b.structures(UnitTypeId.LAIR).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                # 🚀 Performance optimization: Use IntelManager cache
                if intel and intel.cached_townhalls is not None:
                    hatcheries = (
                        list(
                            intel.cached_townhalls.filter(
                                lambda th: th.type_id == UnitTypeId.HATCHERY
                            )
                        )
                        if intel.cached_townhalls.exists
                        else []
                    )
                else:
                    hatcheries = (
                        list(b.structures(UnitTypeId.HATCHERY)) if hasattr(b, "structures") else []
                    )
                if hatcheries and not lairs and b.time > 180 and b.can_afford(UnitTypeId.LAIR):
                    try:
                        if hatcheries:
                            hatcheries[0].morph(UnitTypeId.LAIR)  # type: ignore  # type: ignore
                            print(f"[ERIS COUNTER] [{int(b.time)}s] Starting Lair morph (Mutalisk tech)")
                    except Exception:
                        pass

            # 6-pool aggressive build: Build spawning pool at 6 supply, then rush
            if use_aggressive_build and b.time < 120:  # Only in early game
                # Check if we have spawning pool
                spawning_pools = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure
                    )
                )
                # Enhanced duplicate construction prevention: Don't build if already exists or under construction
                if not spawning_pools and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0:
                    # Build spawning pool immediately if we can afford it
                    if b.can_afford(UnitTypeId.SPAWNINGPOOL) and b.supply_used >= 6:
                        try:
                            if b.townhalls.exists:
                                townhalls_list = list(b.townhalls)
                                if townhalls_list:
                                    # Use _can_build_safely to prevent duplicate construction
                                    if self._can_build_safely(UnitTypeId.SPAWNINGPOOL):
                                        if await self._try_build_structure(
                                            UnitTypeId.SPAWNINGPOOL,
                                            near=townhalls_list[0].position,
                                        ):
                                            # Bot explains its decision via chat
                                            current_iteration = getattr(b, "iteration", 0)
                                            # 🚀 PERFORMANCE: Reduced chat frequency from 224 to 500 frames (~22 seconds)
                                            if current_iteration % 500 == 0:
                                                await b.chat_send(
                                                    "🏗️ [Cautious] Starting Spawning Pool construction for basic defense."
                                                )
                                    return
                        except Exception:
                            pass
                else:
                    pool = spawning_pools[0]
                    if pool.is_ready:
                        # Produce zerglings aggressively (6-pool rush)
                        if await self._try_produce_unit(UnitTypeId.ZERGLING, larvae):
                            return
                        return

            # 12-pool all-in mode: After Spawning Pool complete, produce only Zerglings infinitely
            if self.config.ALL_IN_12_POOL:
                spawning_pools = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure
                    )
                )
                if spawning_pools:
                    # If Spawning Pool complete, produce only Zerglings
                    pool = spawning_pools[0]
                    if pool.is_ready:
                        # Produce Zerglings (no gas or other unit production)
                        if await self._try_produce_unit(UnitTypeId.ZERGLING, larvae):
                            return
                        return

            # Normal mode: Constantly produce Zerglings + Focus Hydra when tech up
            # 1. Always produce Zerglings (when supply available)
            if b.supply_left >= 4:  # Manage with buffer
                if await self._try_produce_unit(UnitTypeId.ZERGLING, larvae):
                    return

            # 2. Reactive production: Detect enemy air units and prepare counters
            # Check if enemy has air units or air tech buildings
            enemy_has_air = False
            if hasattr(b, "scout") and b.scout:
                enemy_has_air = b.scout.enemy_has_air

            # Also check enemy structures for air tech
            enemy_structures = getattr(b, "enemy_structures", [])
            for building in enemy_structures:
                if building.type_id in [
                    UnitTypeId.STARGATE,
                    UnitTypeId.STARPORT,
                    UnitTypeId.FUSIONCORE,
                ]:
                    enemy_has_air = True
                    break

            # If enemy going air: prioritize Hydralisks and Spore Crawlers
            # Tech building construction is now handled by _autonomous_tech_progression()
            # Only produce units if buildings already exist
            if enemy_has_air:
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_hydralisk_dens is not None:
                    hydra_dens = (
                        list(intel.cached_hydralisk_dens)
                        if intel.cached_hydralisk_dens.exists
                        else []
                    )
                else:
                    hydra_dens = (
                        list(b.structures(UnitTypeId.HYDRALISKDEN).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                if hydra_dens:
                    # Prioritize Hydralisk production
                    if await self._try_produce_unit(UnitTypeId.HYDRALISK, larvae):
                        return

                # Build Spore Crawlers for air defense (defensive structure, not tech building)
                if intel and intel.cached_evolution_chambers is not None:
                    evo_chambers_exist = (
                        intel.cached_evolution_chambers.exists
                        if intel.cached_evolution_chambers
                        else False
                    )
                else:
                    evo_chambers_exist = (
                        b.structures(UnitTypeId.EVOLUTIONCHAMBER).ready.exists
                        if hasattr(b, "structures")
                        else False
                    )

                if evo_chambers_exist:
                    # Check if we need more spore crawlers
                    if intel and intel.cached_spore_crawlers is not None:
                        spores = intel.cached_spore_crawlers
                    else:
                        spores = (
                            b.structures(UnitTypeId.SPORECRAWLER).ready
                            if hasattr(b, "structures")
                            else None
                        )
                    if (
                        spores and hasattr(spores, "amount") and spores.amount < 3
                    ):  # Build at least 3 spores
                        for th in b.townhalls.ready:
                            if b.can_afford(UnitTypeId.SPORECRAWLER):
                                # Build spore near townhall
                                await self._try_build_structure(
                                    UnitTypeId.SPORECRAWLER, near=th.position
                                )
                                return

            # Check if enemy is ground-focused: prepare Banelings/Roaches
            # Tech building construction is now handled by _autonomous_tech_progression()
            # Only produce units if buildings already exist
            else:
                # Enemy is ground-focused: prioritize Banelings and Roaches
                # Only produce units if buildings already exist
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_baneling_nests is not None:
                    baneling_nests = (
                        list(intel.cached_baneling_nests)
                        if intel.cached_baneling_nests.exists
                        else []
                    )
                else:
                    baneling_nests = (
                        list(b.structures(UnitTypeId.BANELINGNEST).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                if baneling_nests:
                    if intel and intel.cached_zerglings is not None:
                        zerglings = intel.cached_zerglings
                        zergling_count = (
                            zerglings.amount
                            if hasattr(zerglings, "amount")
                            else len(list(zerglings))
                        )
                    else:
                        zerglings = b.units(UnitTypeId.ZERGLING)
                        zergling_count = (
                            zerglings.amount
                            if hasattr(zerglings, "amount")
                            else len(list(zerglings))
                        )
                    if zergling_count >= 10:
                        # Morph zerglings to banelings if nest exists
                        pass  # Morphing logic is handled elsewhere

                # Produce Roaches if Roach Warren exists
                # 🚀 성능 최적화: IntelManager 캐시 사용
                if intel and intel.cached_roach_warrens is not None:
                    roach_warrens_existing = (
                        list(intel.cached_roach_warrens)
                        if intel.cached_roach_warrens.exists
                        else []
                    )
                    roach_warrens = (
                        list(intel.cached_roach_warrens)
                        if intel.cached_roach_warrens.exists
                        else []
                    )
                else:
                    roach_warrens_existing = (
                        list(b.structures(UnitTypeId.ROACHWARREN).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                    roach_warrens = (
                        list(b.structures(UnitTypeId.ROACHWARREN))
                        if hasattr(b, "structures")
                        else []
                    )

                if roach_warrens_existing:
                    # Roach production logic is handled below
                    pass

                # Produce Roaches for ground combat (enhanced: more aggressive roach production)
                ready_roach_warrens = [rw for rw in roach_warrens if rw.is_ready]
                if ready_roach_warrens:
                    # Check current roach count
                    if intel and intel.cached_roaches is not None:
                        roaches = intel.cached_roaches
                    else:
                        roaches = b.units(UnitTypeId.ROACH)
                    roach_count = (
                        roaches.amount if hasattr(roaches, "amount") else len(list(roaches))
                    )

                    # Produce roaches more aggressively (if we have less than 8 roaches)
                    if roach_count < 8:
                        if await self._try_produce_unit(UnitTypeId.ROACH, larvae):
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[ROACH] [{int(b.time)}s] Roach production started! (Current: {roach_count})"
                                )
                            return
                    # If we have enough roaches, still produce occasionally to maintain army
                    elif roach_count < 15 and b.supply_left >= 2:
                        if await self._try_produce_unit(UnitTypeId.ROACH, larvae):
                            return

                # Produce Banelings from Zerglings
                # 🚀 성능 최적화: IntelManager 캐시 사용
                if intel and intel.cached_baneling_nests is not None:
                    baneling_nests = (
                        list(intel.cached_baneling_nests)
                        if intel.cached_baneling_nests.exists
                        else []
                    )
                else:
                    baneling_nests = (
                        list(b.structures(UnitTypeId.BANELINGNEST).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                if baneling_nests:
                    if intel and intel.cached_zerglings is not None:
                        zerglings_ready = [u for u in intel.cached_zerglings if u.is_ready]
                    else:
                        zerglings_ready = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_ready]
                    if zerglings_ready:
                        for zergling in zerglings_ready[:2]:  # Morph 2 at a time
                            if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                                zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                return

            # 2. When tech up, focus on Hydra production (fallback)
            # 🚀 Performance optimization: Use IntelManager cache
            intel = getattr(b, "intel", None)
            if intel and intel.cached_hydralisk_dens is not None:
                hydra_dens = (
                    list(intel.cached_hydralisk_dens) if intel.cached_hydralisk_dens.exists else []
                )
            else:
                hydra_dens = (
                    list(b.structures(UnitTypeId.HYDRALISKDEN).ready)
                    if hasattr(b, "structures")
                    else []
                )
            if hydra_dens:
                # Hydralisk production
                if await self._try_produce_unit(UnitTypeId.HYDRALISK, larvae):
                    return

            # 3. Reactive tech branching: Unit production based on enemy race
            # Enhanced Lurker production for Division 2 ladder play
            # vs Protoss: Ling-Hydralisk-Lurker - Enhanced version
            if self.enemy_race == EnemyRace.PROTOSS:
                # 🚀 Performance optimization: Use b.structures (faster)
                lurker_dens = list(b.structures(UnitTypeId.LURKERDEN).ready)
                if lurker_dens:
                    # Check if we have Hydralisks to morph
                    # 🚀 Performance optimization: Use IntelManager cache
                    intel = getattr(b, "intel", None)
                    if intel and intel.cached_hydralisks is not None:
                        hydralisks = [
                            u for u in intel.cached_hydralisks if u.is_ready and not u.is_burrowed
                        ]
                    else:
                        hydralisks = [
                            u
                            for u in b.units(UnitTypeId.HYDRALISK)
                            if u.is_ready and not u.is_burrowed
                        ]
                    if hydralisks:
                        # More aggressive Lurker morphing (up to 5 at a time for ladder)
                        for hydra in hydralisks[:5]:  # Increased from 3 to 5
                            if b.can_afford(AbilityId.MORPH_LURKER):
                                try:
                                    hydra(AbilityId.MORPH_LURKER)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(f"[LURKER] [{int(b.time)}s] Lurker morphing started!")
                                except:
                                    pass
                        return

            # vs Terran: Lurker also effective (ground army counter)
            elif self.enemy_race == EnemyRace.TERRAN:
                # 🚀 Performance optimization: Use b.structures (faster)
                lurker_dens = list(b.structures(UnitTypeId.LURKERDEN).ready)
                if lurker_dens and b.time > 300:  # After 5 minutes
                    # 🚀 Performance optimization: Use IntelManager cache
                    intel = getattr(b, "intel", None)
                    if intel and intel.cached_hydralisks is not None:
                        hydralisks = [
                            u for u in intel.cached_hydralisks if u.is_ready and not u.is_burrowed
                        ]
                    else:
                        hydralisks = [
                            u
                            for u in b.units(UnitTypeId.HYDRALISK)
                            if u.is_ready and not u.is_burrowed
                        ]
                    if hydralisks:
                        # Morph up to 3 Hydralisks to Lurkers for ground control
                        for hydra in hydralisks[:3]:
                            if b.can_afford(AbilityId.MORPH_LURKER):
                                try:
                                    hydra(AbilityId.MORPH_LURKER)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(
                                            f"[LURKER] [{int(b.time)}s] Lurker morphing vs Terran!"
                                        )
                                except:
                                    pass
                        return
            # vs Terran: Ling-Baneling-Mutalisk or Ling-Baneling-Ultralisk
            elif self.enemy_race == EnemyRace.TERRAN:
                # Baneling production (requires Baneling Nest)
                # 🚀 Performance optimization: Use b.structures (faster)
                baneling_nests = list(b.structures(UnitTypeId.BANELINGNEST).ready)
                if baneling_nests:
                    zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_ready]
                    if zerglings:
                        for zergling in zerglings[:2]:  # Morph up to 2 at a time
                            if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                                zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                return

                # Mutalisk production (requires Spire)
                # 🚀 Performance optimization: Use b.structures (faster)
                spires = list(b.structures(UnitTypeId.SPIRE).ready)
                if spires:
                    if await self._try_produce_unit(UnitTypeId.MUTALISK, larvae):
                        return

                # Ultralisk production (requires Ultralisk Cavern)
                # 🚀 Performance optimization: Use b.structures (faster)
                ultralisk_caverns = list(b.structures(UnitTypeId.ULTRALISKCAVERN).ready)
                if ultralisk_caverns:
                    if await self._try_produce_unit(UnitTypeId.ULTRALISK, larvae):
                        return
            # vs Zerg: Zergling-Baneling early control fight then Roach-Ravager
            elif self.enemy_race == EnemyRace.ZERG:
                # Early: Zergling-Baneling
                if b.time < 300:  # Before 5 minutes
                    # 🚀 Performance optimization: Use b.structures (faster)
                    baneling_nests = list(b.structures(UnitTypeId.BANELINGNEST).ready)
                    if baneling_nests:
                        # 🚀 Performance optimization: Use IntelManager cache
                        intel = getattr(b, "intel", None)
                        if intel and intel.cached_zerglings is not None:
                            zerglings = intel.cached_zerglings
                        else:
                            zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_ready]
                        # Handle both Units object and list
                        zerglings_list = []
                        try:
                            # Check if it's a Units object (has 'exists' attribute)
                            if hasattr(zerglings, "exists") and not isinstance(zerglings, list):
                                if zerglings.exists:  # type: ignore
                                    zerglings_list = list(zerglings)[:2]
                            elif isinstance(zerglings, list):
                                if zerglings and len(zerglings) > 0:
                                    zerglings_list = zerglings[:2]
                        except Exception:
                            pass

                        for zergling in zerglings_list:
                            if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                                zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                return
                else:
                    # Mid-game onward: Roach-Ravager
                    # 🚀 Performance optimization: Use b.structures (faster)
                    roach_warrens = list(b.structures(UnitTypeId.ROACHWARREN).ready)
                    if roach_warrens:
                        if await self._try_produce_unit(UnitTypeId.ROACH, larvae):
                            return
                        # Ravager morph
                        roaches = [u for u in b.units(UnitTypeId.ROACH) if u.is_ready]
                        if roaches:
                            for roach in roaches[:1]:  # Morph 1 at a time
                                if b.can_afford(AbilityId.MORPHTORAVAGER_RAVAGER):
                                    roach(AbilityId.MORPHTORAVAGER_RAVAGER)
                                    return

            # 4. Final unit production (composition-based)
            if await self._produce_ultimate_units(larvae):
                return

            # 5. Composition-based unit selection (if Hydra fails)
            # Curriculum Learning: Focus on basic units when difficulty is low
            if self._should_use_basic_units():
                # VeryEasy, Easy stages: Focus on Zergling + Roach (avoid complex unit compositions)
                units_to_produce = [UnitTypeId.ZERGLING, UnitTypeId.ROACH]
            else:
                # Medium and above: Normal composition-based unit selection
                units_to_produce = self._get_counter_units(game_phase)

            for unit_type in units_to_produce:
                if unit_type != UnitTypeId.ZERGLING:  # Zergling already handled above
                    if await self._try_produce_unit(unit_type, larvae):
                        return
        except Exception as e:
            # Only log on error (prevent game interruption)
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _produce_army error: {e}")

    # =========================================================================
    # Final unit production (Ultralisk, Brood Lord)
    # =========================================================================

    async def _produce_queen(self):
        """Queen production (1 per Hatchery)"""
        b = self.bot

        # 🚀 Performance optimization: Use .structures().ready (no list conversion needed)
        spawning_pools = b.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not spawning_pools.exists:
            return

        # 🚀 Performance optimization: Use IntelManager cache
        intel = getattr(b, "intel", None)
        if intel:
            queens = intel.cached_queens or b.units(UnitTypeId.QUEEN)
            if intel.cached_townhalls is not None:
                townhalls = list(intel.cached_townhalls) if intel.cached_townhalls.exists else []
            else:
                townhalls = [th for th in b.townhalls]
        else:
            queens = b.units(UnitTypeId.QUEEN)
            townhalls = [th for th in b.townhalls]
        queens_count = len(queens) + b.already_pending(UnitTypeId.QUEEN)

        # 1 Queen per base
        if queens_count < len(townhalls):
            ready_idle_townhalls = [th for th in townhalls if th.is_ready and th.is_idle]
            for hatch in ready_idle_townhalls:
                if b.can_afford(UnitTypeId.QUEEN):
                    hatch.train(UnitTypeId.QUEEN)
                    print(f"👑 [{int(b.time)}s] Queen production")
                    break

    # =========================================================================
    # 3️⃣ Secure defense units before expansion
    # =========================================================================
