# -*- coding: utf-8 -*-
from typing import Any, Dict
import random

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
except ImportError:
    # Mock for testing
    class UnitTypeId:
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        HATCHERY = "HATCHERY"
        OVERLORD = "OVERLORD"
        LARVA = "LARVA"
        ZERGLING = "ZERGLING"
        LAIR = "LAIR"
        HIVE = "HIVE"
        SPIRE = "SPIRE"
        MUTALISK = "MUTALISK"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        ROACHWARREN = "ROACHWARREN"
        HYDRALISKDEN = "HYDRALISKDEN"
        BANELINGNEST = "BANELINGNEST"
        EVOLUTIONCHAMBER = "EVOLUTIONCHAMBER"
        DRONE = "DRONE"
    class AbilityId:
        MORPHTORAVAGER_RAVAGER = "MORPHTORAVAGER_RAVAGER"
        MORPHZERGLINGTOBANELING_BANELING = "MORPHZERGLINGTOBANELING_BANELING"
        UPGRADETOLAIR_LAIR = "UPGRADETOLAIR_LAIR"
        UPGRADETOHIVE_HIVE = "UPGRADETOHIVE_HIVE"

try:
    from config import get_learned_parameter
except ImportError:
    # Fallback if config module not available
    def get_learned_parameter(parameter_name: str, default_value: Any = None) -> Any:
        return default_value

try:
    from local_training.economy_combat_balancer import EconomyCombatBalancer
    BALANCER_AVAILABLE = True
except ImportError:
    BALANCER_AVAILABLE = False
    EconomyCombatBalancer = None

try:
    from local_training.resource_manager import ResourceManager
    RESOURCE_MANAGER_AVAILABLE = True
except ImportError:
    RESOURCE_MANAGER_AVAILABLE = False
    ResourceManager = None

try:
    from local_training.opening_strategy_manager import OpeningStrategyManager, OpeningStrategy
    STRATEGY_MANAGER_AVAILABLE = True
except ImportError:
    STRATEGY_MANAGER_AVAILABLE = False
    OpeningStrategyManager = None
    OpeningStrategy = None


class ProductionResilience:

    async def _safe_train(self, unit, unit_type):
        """Safely train a unit, handling both sync and async train() methods"""
        try:
            result = unit.train(unit_type)
            # train() may return bool or coroutine
            if hasattr(result, '__await__'):
                await result
            return True
        except Exception as e:
            current_iteration = getattr(self.bot, "iteration", 0)
            if current_iteration % 200 == 0:
                print(f"[WARNING] _safe_train error: {e}")
            return False

    def __init__(self, bot: Any) -> None:
        self.bot = bot

        # Initialize Economy-Combat Balancer
        if BALANCER_AVAILABLE and EconomyCombatBalancer:
            try:
                self.balancer = EconomyCombatBalancer(bot)
            except Exception as e:
                print(f"[WARNING] Failed to initialize EconomyCombatBalancer: {e}")
                self.balancer = None
        else:
            self.balancer = None

        # Initialize Resource Manager
        if RESOURCE_MANAGER_AVAILABLE and ResourceManager:
            try:
                self.resource_manager = ResourceManager(bot)
            except Exception as e:
                print(f"[WARNING] Failed to initialize ResourceManager: {e}")
                self.resource_manager = None
        else:
            self.resource_manager = None

        # Initialize Opening Strategy Manager
        if STRATEGY_MANAGER_AVAILABLE and OpeningStrategyManager:
            try:
                # Select random strategy for variety
                self.strategy_manager = OpeningStrategyManager(bot, OpeningStrategy.RANDOM if OpeningStrategy else None)
            except Exception as e:
                print(f"[WARNING] Failed to initialize OpeningStrategyManager: {e}")
                self.strategy_manager = None
        else:
            self.strategy_manager = None

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

        # Expansion safety gate / retry policy
        self.last_expansion_attempt = 0.0
        # Tuned defaults (safer expansion gates)
        self.expansion_retry_cooldown = 60.0
        self.min_drones_per_base = 14
        self.min_army_supply = 8
        self.min_army_time = 210.0
        self.enemy_near_base_distance = 24.0
        self.enemy_near_base_scale = 1.1
        self.last_expand_log_time = 0.0

        override = getattr(self.bot, "production_params", None)
        if isinstance(override, dict):
            self.expansion_retry_cooldown = override.get("expansion_retry_cooldown", self.expansion_retry_cooldown)
            self.min_drones_per_base = override.get("min_drones_per_base", self.min_drones_per_base)
            self.min_army_supply = override.get("min_army_supply", self.min_army_supply)
            self.min_army_time = override.get("min_army_time", self.min_army_time)
            self.enemy_near_base_distance = override.get(
                "enemy_near_base_distance", self.enemy_near_base_distance
            )
            self.enemy_near_base_scale = override.get("enemy_near_base_scale", self.enemy_near_base_scale)

    def _can_expand_safely(self) -> tuple:
        b = self.bot
        intel = getattr(b, "intel", None)
        under_attack = False
        enemy_near_base = False

        if intel and hasattr(intel, "is_under_attack"):
            under_attack = bool(intel.is_under_attack())
        if not under_attack and hasattr(b, "enemy_units") and b.enemy_units:
            if b.townhalls.exists:
                base = b.townhalls.first
                threshold = self.enemy_near_base_distance * self.enemy_near_base_scale
                enemy_near_base = any(e.distance_to(base.position) < threshold for e in b.enemy_units)

        # AGGRESSIVE EXPANSION: If minerals > 400, bypass most safety checks
        aggressive_expand = b.minerals > 400

        if under_attack and not aggressive_expand:
            return False, "under_attack"
        if enemy_near_base and not aggressive_expand:
            return False, "enemy_near_base"

        # Relax army requirement - Zerg needs expansions for macro
        supply_army = getattr(b, "supply_army", 0)
        if not aggressive_expand and supply_army < self.min_army_supply and b.time > self.min_army_time:
            return False, "low_army"

        # Relax drone requirement when banking minerals
        drones = b.workers.amount if hasattr(b, "workers") else 0
        bases = b.townhalls.amount if hasattr(b, "townhalls") else 1
        if not aggressive_expand and drones < bases * self.min_drones_per_base:
            return False, "low_drones"

        # Reduce cooldown when banking minerals
        now = getattr(b, "time", 0.0)
        effective_cooldown = self.expansion_retry_cooldown / 2 if aggressive_expand else self.expansion_retry_cooldown
        if now - self.last_expansion_attempt < effective_cooldown:
            return False, "cooldown"

        return True, ""

    async def _try_expand(self) -> bool:
        b = self.bot
        if not b.can_afford(UnitTypeId.HATCHERY):
            self._log_expand_block("insufficient_resources")
            return False
        if b.already_pending(UnitTypeId.HATCHERY) > 0:
            self._log_expand_block("pending_hatchery")
            return False
        can_expand, reason = self._can_expand_safely()
        if not can_expand:
            self._log_expand_block(reason)
            return False

        self.last_expansion_attempt = getattr(b, "time", 0.0)

        # Prefer expand_now or get_next_expansion
        try:
            if hasattr(b, "expand_now"):
                await b.expand_now()
                return True
            if hasattr(b, "get_next_expansion"):
                next_pos = await b.get_next_expansion()
                if next_pos:
                    await b.build(UnitTypeId.HATCHERY, near=next_pos)
                    return True
        except Exception:
            return False

        return False

    def _log_expand_block(self, reason: str) -> None:
        now = getattr(self.bot, "time", 0.0)
        if now - self.last_expand_log_time < 15.0:
            return
        self.last_expand_log_time = now
        if reason:
            print(f"[EXPAND BLOCK] {reason} at {int(now)}s")

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
        """
        Fix production bottlenecks and boost early game build order.
        """
        b = self.bot
        self._cleanup_build_reservations()

        # === AGGRESSIVE EXPANSION: When minerals > 400, prioritize expansion ===
        # Zerg needs expansions for macro advantage
        if b.minerals > 400 and b.already_pending(UnitTypeId.HATCHERY) == 0:
            bases = b.townhalls.amount if hasattr(b, "townhalls") else 1
            # Always try to have one more base building
            if b.can_afford(UnitTypeId.HATCHERY):
                try:
                    if await self._try_expand():
                        if b.iteration % 100 == 0:
                            print(f"[AGGRESSIVE EXPAND] [{int(b.time)}s] Expanding due to mineral bank ({int(b.minerals)} > 400)")
                except Exception:
                    pass

        # === RESOURCE MANAGEMENT: Optimize worker assignment ===
        if self.resource_manager:
            try:
                await self.resource_manager.optimize_resource_gathering()
            except Exception as e:
                if b.iteration % 200 == 0:
                    print(f"[WARNING] Resource manager error: {e}")

        # === EARLY GAME BOOSTER: First 3 minutes - Maximum priority ===
        time = getattr(b, "time", 0.0)
        if time <= 180:  # First 3 minutes
            await self._boost_early_game()

        # === AUTO TECH BUILDINGS: Build tech structures based on game time ===
        await self._auto_build_tech_structures()

        try:
            # === CRITICAL EMERGENCY: Minerals > 3000 - Force immediate production
            # When minerals exceed 3000, force all available production immediately
            if b.minerals > 3000:
                await self._force_emergency_production(b)
                return
            
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

                    # If Spawning Pool is ready, use balance system to decide drone vs army
                    if spawning_pools_ready.exists:
                        # Use Economy-Combat Balancer to decide production
                        if self.balancer:
                            await self._balanced_production(larvae)
                        else:
                            # Fallback: Original emergency logic
                            await self._emergency_zergling_production(larvae)
                        return  # Exit after production decision

        except Exception as e:
            if b.iteration % 100 == 0:
                print(f"[WARNING] fix_production_bottleneck emergency error: {e}")

    async def _balanced_production(self, larvae) -> None:
        """
        Use Economy-Combat Balancer to decide between drones and army units
        """
        b = self.bot
        if not self.balancer:
            return
        
        larvae_list = list(larvae) if larvae.exists else []
        if not larvae_list:
            return
        
        # RESOURCE FLUSH MODE: When minerals >= 1000, produce units based on available tech
        # IMPROVED: Prioritize tech units over Zerglings to balance composition
        if b.minerals >= 1000:
            units_produced = 0
            zergling_count = b.units(UnitTypeId.ZERGLING).amount if hasattr(b, "units") else 0
            max_zerglings = 40  # Cap for resource flush mode

            for larva in larvae_list:
                if not hasattr(larva, 'is_ready') or not larva.is_ready:
                    continue

                if b.supply_left < 1:
                    if b.can_afford(UnitTypeId.OVERLORD):
                        if await self._safe_train(larva, UnitTypeId.OVERLORD):
                            units_produced += 1
                            continue
                    continue

                # IMPROVED: Try tech units first before Zerglings
                produced = await self._produce_army_unit(larva)
                if produced:
                    units_produced += 1
                    continue

                # Fallback: Zerglings only if under cap
                if zergling_count < max_zerglings and b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
                    if await self._safe_train(larva, UnitTypeId.ZERGLING):
                        units_produced += 1
                        zergling_count += 1

            if units_produced > 0:
                print(f"[RESOURCE_FLUSH] [{int(b.time)}s] Produced {units_produced} units (Minerals: {int(b.minerals)})")
            return
        
        # Get current counts
        drones = b.units(UnitTypeId.DRONE) if hasattr(b, "units") else []
        drone_count = drones.amount if hasattr(drones, "amount") else len(list(drones))

        # Get balance state (use correct method names)
        stats = self.balancer.get_production_stats()
        target_drones = self.balancer.get_drone_target()
        balance_mode = self.balancer.get_balance_mode()

        # Log balance decision periodically
        if b.iteration % 100 == 0:
            print(f"[BALANCE] Mode: {balance_mode}, Drone: {stats.get('drone_ratio', 0):.1%}, "
                  f"Army: {stats.get('army_ratio', 0):.1%}, "
                  f"Current: {drone_count}, Target: {target_drones}")
        
        drones_produced = 0
        army_produced = 0
        
        # Process each larva based on balance ratio
        for larva in larvae_list:
            if not hasattr(larva, 'is_ready') or not larva.is_ready:
                continue
            
            # Check supply first
            if b.supply_left < 1:
                if b.can_afford(UnitTypeId.OVERLORD):
                    if await self._safe_train(larva, UnitTypeId.OVERLORD):
                        print(f"[BALANCE] Produced Overlord for supply")
                    break
                continue
            
            # === CHECK MINIMUM DEFENSE FIRST ===
            # Always prioritize army if minimum defense not met
            game_time = getattr(b, "time", 0)
            zergling_count = b.units(UnitTypeId.ZERGLING).amount if hasattr(b, "units") else 0
            roach_count = b.units(UnitTypeId.ROACH).amount if hasattr(b, "units") else 0
            hydra_count = b.units(UnitTypeId.HYDRALISK).amount if hasattr(b, "units") else 0
            mutalisk_count = b.units(UnitTypeId.MUTALISK).amount if hasattr(b, "units") else 0
            total_army_supply = (zergling_count * 0.5) + (roach_count * 2) + (hydra_count * 2) + (mutalisk_count * 2)

            min_defense_met = True
            if game_time >= 120 and game_time < 240:
                min_defense_met = zergling_count >= 6
            elif game_time >= 240 and game_time < 360:
                min_defense_met = zergling_count >= 8 or roach_count >= 4 or total_army_supply >= 8
            elif game_time >= 360:
                min_defense_met = total_army_supply >= 10

            # If minimum defense NOT met, skip droning - prioritize army
            if not min_defense_met:
                unit_produced = await self._produce_army_unit(larva)
                if unit_produced:
                    army_produced += 1
                continue

            # Decide: drone or army?
            # Consider strategy preference
            if self.strategy_manager and self.strategy_manager.should_prioritize_drones():
                # Strategy prefers drones, but still check balancer
                should_train_drone = self.balancer.should_train_drone() or (drone_count < target_drones)
            elif self.strategy_manager and self.strategy_manager.should_early_aggression():
                # Strategy prefers early army
                should_train_drone = False
            else:
                should_train_drone = self.balancer.should_train_drone()

            if should_train_drone and drone_count < target_drones:
                # Make drone
                if b.can_afford(UnitTypeId.DRONE):
                    if await self._safe_train(larva, UnitTypeId.DRONE):
                        drones_produced += 1
                        drone_count += 1
                        continue

            # Make army unit based on composition
            unit_produced = await self._produce_army_unit(larva)
            if unit_produced:
                army_produced += 1

        if drones_produced > 0 or army_produced > 0:
            if b.iteration % 50 == 0:
                print(f"[BALANCE] Produced {drones_produced} drones, {army_produced} army units "
                      f"(Total drones: {drone_count}, Target: {target_drones})")

    async def _produce_army_unit(self, larva) -> bool:
        """
        Produce army unit based on current composition and available tech.

        Unit priority by game phase:
        - Early (0-5min): Zerglings (with cap to avoid spam)
        - Mid (5-10min): Roaches 40%, Hydralisks 30%, Zerglings 30%
        - Late (10min+): Mutalisks 30%, Hydralisks 25%, Roaches 25%, Zerglings 20%

        IMPROVED:
        - Limit Zergling production to avoid spam when waiting for gas.
        - Ensure MINIMUM DEFENSE units before droning/teching.
        """
        b = self.bot
        game_time = getattr(b, "time", 0)

        # Get current unit counts
        zergling_count = b.units(UnitTypeId.ZERGLING).amount if hasattr(b, "units") else 0
        roach_count = b.units(UnitTypeId.ROACH).amount if hasattr(b, "units") else 0
        hydra_count = b.units(UnitTypeId.HYDRALISK).amount if hasattr(b, "units") else 0
        mutalisk_count = b.units(UnitTypeId.MUTALISK).amount if hasattr(b, "units") else 0

        # Check available tech
        has_roach_warren = b.structures(UnitTypeId.ROACHWARREN).ready.exists
        has_hydra_den = b.structures(UnitTypeId.HYDRALISKDEN).ready.exists
        has_spire = b.structures(UnitTypeId.SPIRE).ready.exists

        # === MINIMUM DEFENSE REQUIREMENT ===
        # Always maintain minimum army for defense before teching/droning
        # Early (2-4min): At least 6 Zerglings
        # Mid (4-6min): At least 8 Zerglings OR 4 Roaches
        # Late (6min+): At least 10 army supply
        min_defense_met = True
        total_army_supply = (zergling_count * 0.5) + (roach_count * 2) + (hydra_count * 2) + (mutalisk_count * 2)

        if game_time >= 120 and game_time < 240:
            # 2-4 min: Need at least 6 Zerglings
            min_defense_met = zergling_count >= 6
        elif game_time >= 240 and game_time < 360:
            # 4-6 min: Need at least 8 Zerglings OR 4 Roaches
            min_defense_met = zergling_count >= 8 or roach_count >= 4 or total_army_supply >= 8
        elif game_time >= 360:
            # 6+ min: Need at least 10 army supply
            min_defense_met = total_army_supply >= 10

        # If minimum defense NOT met, prioritize army production
        if not min_defense_met:
            # Force produce Zerglings for minimum defense
            if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
                return await self._safe_train(larva, UnitTypeId.ZERGLING)
            return False  # Wait for resources

        # === Calculate Zergling cap based on game phase ===
        # Early game: Max 20 Zerglings
        # Mid game: Max 30 Zerglings (if tech available)
        # Late game: Max 40 Zerglings (if air tech available)
        max_zerglings = 20
        if game_time > 300:
            max_zerglings = 30 if (has_roach_warren or has_hydra_den) else 50
        if game_time > 600:
            max_zerglings = 40 if has_spire else 60

        # Late game (10+ min): Prioritize air and ranged
        if game_time > 600 and has_spire:
            # Target: Mutalisk 30%, Hydra 25%, Roach 25%, Ling 20%
            total = zergling_count + roach_count + hydra_count + mutalisk_count + 1
            mutalisk_ratio = mutalisk_count / total
            hydra_ratio = hydra_count / total
            roach_ratio = roach_count / total

            # Prioritize Mutalisks if under ratio
            if mutalisk_ratio < 0.30 and b.can_afford(UnitTypeId.MUTALISK) and b.supply_left >= 2:
                return await self._safe_train(larva, UnitTypeId.MUTALISK)

            # Then Hydralisks
            if has_hydra_den and hydra_ratio < 0.25 and b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                return await self._safe_train(larva, UnitTypeId.HYDRALISK)

            # Then Roaches
            if has_roach_warren and roach_ratio < 0.25 and b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
                return await self._safe_train(larva, UnitTypeId.ROACH)

            # Only produce Zerglings if under cap
            if zergling_count < max_zerglings and b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
                return await self._safe_train(larva, UnitTypeId.ZERGLING)
            return False  # Wait for gas instead of spamming Zerglings

        # Mid game (5-10 min): Mixed army
        elif game_time > 300:
            total = zergling_count + roach_count + hydra_count + 1
            roach_ratio = roach_count / total
            hydra_ratio = hydra_count / total

            # Prioritize Hydralisks if Lair tech available
            if has_hydra_den and hydra_ratio < 0.30 and b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                return await self._safe_train(larva, UnitTypeId.HYDRALISK)

            # Then Roaches
            if has_roach_warren and roach_ratio < 0.40 and b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
                return await self._safe_train(larva, UnitTypeId.ROACH)

            # Only produce Zerglings if under cap
            if zergling_count < max_zerglings and b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
                return await self._safe_train(larva, UnitTypeId.ZERGLING)

            # If over Zergling cap but have gas, wait for tech units
            if b.vespene >= 25:  # Have some gas, wait for tech
                return False

        # Early game (0-5 min): Zerglings with cap
        if zergling_count < max_zerglings and b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
            return await self._safe_train(larva, UnitTypeId.ZERGLING)

        return False
    
    async def _emergency_zergling_production(self, larvae) -> None:
        """
        Fallback emergency production when balancer is unavailable.
        IMPROVED: Prioritize tech units over Zerglings; cap Zergling count.
        """
        b = self.bot
        units_produced = 0
        larvae_list = list(larvae) if larvae.exists else []

        # Get current Zergling count
        zergling_count = b.units(UnitTypeId.ZERGLING).amount if hasattr(b, "units") else 0
        max_zerglings = 40  # Cap to prevent spam

        # RESOURCE FLUSH MODE: When minerals >= 1000, produce aggressively but balanced
        flush_mode = b.minerals >= 1000

        for larva in larvae_list:
            if not hasattr(larva, 'is_ready') or not larva.is_ready:
                continue

            if b.supply_left < 1:
                if b.can_afford(UnitTypeId.OVERLORD) and larvae_list:
                    if await self._safe_train(larvae_list[0], UnitTypeId.OVERLORD):
                        print(f"[EMERGENCY] Produced Overlord for supply")
                    if not flush_mode:
                        break
                continue

            # IMPROVED: Try tech units first via _produce_army_unit
            produced = await self._produce_army_unit(larva)
            if produced:
                units_produced += 1
                if not flush_mode:
                    break
                continue

            # Fallback: Zerglings only if under cap
            if zergling_count < max_zerglings and b.can_afford(UnitTypeId.ZERGLING):
                if await self._safe_train(larva, UnitTypeId.ZERGLING):
                    units_produced += 1
                    zergling_count += 1
                    if not flush_mode:
                        break

        if units_produced > 0:
            mode_str = "[RESOURCE_FLUSH]" if flush_mode else "[EMERGENCY]"
            print(f"{mode_str} Produced {units_produced} units (Minerals: {int(b.minerals)})")

    async def _force_emergency_production(self, b: Any) -> None:
        """
        CRITICAL EMERGENCY: Force immediate production when minerals > 3000.
        This method aggressively spends all available resources.
        """
        if not hasattr(b, 'units'):
            return
        
        larvae = b.units(UnitTypeId.LARVA)
        if not larvae.exists:
            return
        
        larvae_list = list(larvae.ready) if hasattr(larvae, 'ready') else list(larvae)
        produced_count = 0
        
        # Force production of all available units
        for larva in larvae_list:
            if not hasattr(larva, 'is_ready') or not larva.is_ready:
                continue
            
            # Check supply first
            if b.supply_left < 1:
                if b.can_afford(UnitTypeId.OVERLORD):
                    if await self._safe_train(larva, UnitTypeId.OVERLORD):
                        produced_count += 1
                        continue
                continue
            
            # Try to produce Zerglings first (cheapest, fastest)
            if b.units(UnitTypeId.SPAWNINGPOOL).ready.exists and b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
                if await self._safe_train(larva, UnitTypeId.ZERGLING):
                    produced_count += 1
                    continue
            
            # Try Roaches if available
            if b.units(UnitTypeId.ROACHWARREN).ready.exists and b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
                if await self._safe_train(larva, UnitTypeId.ROACH):
                    produced_count += 1
                    continue
            
            # Try Hydralisks if available
            if b.units(UnitTypeId.HYDRALISKDEN).ready.exists and b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                if await self._safe_train(larva, UnitTypeId.HYDRALISK):
                    produced_count += 1
                    continue
        
        if produced_count > 0:
            print(f"[FORCE_EMERGENCY] [{int(b.time)}s] Forced production of {produced_count} units (Minerals: {int(b.minerals)})")
        
        # Also try to build structures if we still have too many minerals
        if b.minerals > 2000:
            # Build expansion if possible
            if b.can_afford(UnitTypeId.HATCHERY) and b.already_pending(UnitTypeId.HATCHERY) == 0:
                if b.townhalls.exists and len(b.townhalls) < 3:
                    try:
                        if await self._try_expand():
                            print(f"[FORCE_EMERGENCY] Building expansion to dump minerals")
                    except Exception:
                        pass

    async def _boost_early_game(self) -> None:
        """
        Boost early game production (first 3 minutes).
        Prioritizes fast Spawning Pool, early workers, and quick expansion.
        """
        b = self.bot
        time = getattr(b, "time", 0.0)
        supply_used = getattr(b, "supply_used", 0)

        try:
            # Priority 1: Fast Spawning Pool (supply 13-15)
            if supply_used >= 13 and supply_used <= 15:
                if not b.structures(UnitTypeId.SPAWNINGPOOL).exists and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0:
                    if b.can_afford(UnitTypeId.SPAWNINGPOOL) and b.townhalls.exists:
                        try:
                            main_base = b.townhalls.first
                            await b.build(
                                UnitTypeId.SPAWNINGPOOL,
                                near=main_base.position.towards(b.game_info.map_center, 5),
                            )
                            if b.iteration % 50 == 0:
                                print(f"[EARLY_BOOST] [{int(time)}s] Fast Spawning Pool at supply {supply_used}")
                        except Exception:
                            pass

            # Priority 2: Early workers (maximize drone production)
            larvae = b.units(UnitTypeId.LARVA)
            if larvae.exists and supply_used < 20:
                larvae_list = list(larvae.ready) if hasattr(larvae, 'ready') else list(larvae)
                for larva in larvae_list[:3]:
                    if not hasattr(larva, 'is_ready') or not larva.is_ready:
                        continue
                    if b.supply_left < 1:
                        if b.can_afford(UnitTypeId.OVERLORD):
                            await self._safe_train(larva, UnitTypeId.OVERLORD)
                            break
                        continue
                    if b.can_afford(UnitTypeId.DRONE):
                        if await self._safe_train(larva, UnitTypeId.DRONE):
                            continue

            # NOTE: Extractor building is now handled by _auto_build_extractors()
            # Called from _auto_build_tech_structures() for consistent timing

            # Spawning Pool timing
            if self.strategy_manager:
                spawning_pool_supply = self.strategy_manager.get_pool_supply()
            else:
                spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 17.0)

            if not b.units(UnitTypeId.SPAWNINGPOOL).exists and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0:
                should_build_pool = supply_used >= spawning_pool_supply
                emergency_build = supply_used > 20 and b.can_afford(UnitTypeId.SPAWNINGPOOL)
                if (should_build_pool or emergency_build) and b.can_afford(UnitTypeId.SPAWNINGPOOL) and b.townhalls.exists:
                    try:
                        main_base = b.townhalls.first
                        await b.build(
                            UnitTypeId.SPAWNINGPOOL,
                            near=main_base.position.towards(b.game_info.map_center, 5),
                        )
                        return
                    except Exception:
                        pass

            # Natural Expansion timing
            if self.strategy_manager:
                natural_expansion_supply = self.strategy_manager.get_expansion_supply()
                natural_expansion_supply_max = natural_expansion_supply + 2.0 if natural_expansion_supply > 0 else 0.0
            else:
                natural_expansion_supply = get_learned_parameter("natural_expansion_supply", 30.0)
                natural_expansion_supply_max = natural_expansion_supply + 2.0

            townhalls = b.townhalls if hasattr(b, "townhalls") else []
            if supply_used >= natural_expansion_supply and supply_used <= natural_expansion_supply_max:
                if len(townhalls) < 2:
                    if await self._try_expand():
                        return
            elif supply_used >= 40 and len(townhalls) < 2:
                if await self._try_expand():
                    return

            # Overlord production
            larvae = b.units(UnitTypeId.LARVA)
            if b.supply_left < 6 and b.supply_cap < 200 and b.can_afford(UnitTypeId.OVERLORD) and larvae.exists:
                try:
                    larvae_list = list(larvae)
                    if larvae_list:
                        await self._safe_train(larvae_list[0], UnitTypeId.OVERLORD)
                except Exception:
                    pass

            # Aggressive overlord production when banking minerals
            if b.minerals > 500 and b.supply_left < 20 and larvae.exists:
                overlords_to_produce = min(5, len(larvae) // 2)
                overlords_produced = 0
                for larva in list(larvae):
                    if not larva.is_ready:
                        continue
                    if overlords_produced >= overlords_to_produce:
                        break
                    if b.can_afford(UnitTypeId.OVERLORD):
                        try:
                            if await self._safe_train(larva, UnitTypeId.OVERLORD):
                                overlords_produced += 1
                        except Exception:
                            pass

            # Unit production
            spawning_pools = b.units(UnitTypeId.SPAWNINGPOOL).ready
            if spawning_pools.exists and larvae.exists:
                larvae_list = list(larvae)
                max_production = min(10, len(larvae_list))
                for larva in larvae_list[:max_production]:
                    if not larva.is_ready:
                        continue
                    if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
                        try:
                            await self._safe_train(larva, UnitTypeId.ZERGLING)
                        except Exception:
                            continue

            roach_warrens = b.units(UnitTypeId.ROACHWARREN).ready
            if roach_warrens.exists and larvae.exists:
                larvae_list = list(larvae)
                max_production = min(5, len(larvae_list))
                for larva in larvae_list[:max_production]:
                    if not larva.is_ready:
                        continue
                    if b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
                        try:
                            await self._safe_train(larva, UnitTypeId.ROACH)
                        except Exception:
                            continue

            hydra_dens = b.units(UnitTypeId.HYDRALISKDEN).ready
            if hydra_dens.exists and larvae.exists:
                larvae_list = list(larvae)
                max_production = min(5, len(larvae_list))
                for larva in larvae_list[:max_production]:
                    if not larva.is_ready:
                        continue
                    if b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                        try:
                            await self._safe_train(larva, UnitTypeId.HYDRALISK)
                        except Exception:
                            continue

        except Exception as e:
            if b.iteration % 100 == 0:
                print(f"[WARNING] _boost_early_game error: {e}")

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
                if is_training and use_logger and loguru_logger is not None:
                    # Training mode: Use DEBUG level to reduce I/O overhead
                    loguru_logger.debug(
                        f"[PRODUCTION DIAGNOSIS] [{int(b.time)}s] Iteration: {iteration}")
                    loguru_logger.debug(
                        f"Resources: M:{int(b.minerals)} G:{int(b.vespene)} Supply:{b.supply_used}/{b.supply_cap}")
                    loguru_logger.debug(
                        f"Larva: {larvae_count} | Tech: Pool:{spawning_pool_ready} Warren:{roach_warren_ready} Den:{hydralisk_den_ready}")
                    loguru_logger.debug(
                        f"Units: Z:{zergling_count} R:{roach_count} H:{hydralisk_count} | Pending: Z:{pending_zerglings} R:{pending_roaches} H:{pending_hydralisks}")

                    # Only log critical issues at INFO level
                    if larvae_count == 0:
                        loguru_logger.warning(f"[PRODUCTION] NO LARVAE - Production blocked!")
                    elif larvae_count >= 3 and b.minerals > 500 and spawning_pool_ready and can_afford_zergling and b.supply_left >= 2:
                        loguru_logger.warning(
                            f"[PRODUCTION] Should produce Zerglings but not producing!")
                else:
                    # Non-training mode or no logger: Use print (for debugging)
                    # But reduce frequency - only every 500 iterations instead of 50
                    if iteration % 500 == 0:
                        print(
                            f"\n[PRODUCTION DIAGNOSIS] [{int(b.time)}s] Iteration: {iteration}")
                        print(
                            f"Resources: M:{int(b.minerals)} G:{int(b.vespene)} Supply:{b.supply_used}/{b.supply_cap}")
                        print(
                            f"Larva: {larvae_count} | Tech: Pool:{spawning_pool_ready} Warren:{roach_warren_ready} Den:{hydralisk_den_ready}")
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
                                if await self._safe_train(larva, UnitTypeId.OVERLORD):
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
                    if b.units(UnitTypeId.HYDRALISKDEN).ready.exists and b.can_afford(UnitTypeId.HYDRALISK):
                        unit_to_produce = UnitTypeId.HYDRALISK
                elif max_deficit_unit == UnitTypeId.ROACH:
                    if b.units(UnitTypeId.ROACHWARREN).ready.exists and b.can_afford(UnitTypeId.ROACH):
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
                    if b.units(UnitTypeId.SPAWNINGPOOL).ready.exists and b.can_afford(UnitTypeId.ZERGLING):
                        unit_to_produce = UnitTypeId.ZERGLING
        if not unit_to_produce:
            if b.units(UnitTypeId.SPAWNINGPOOL).ready.exists and b.can_afford(UnitTypeId.ZERGLING):
                unit_to_produce = UnitTypeId.ZERGLING
        if unit_to_produce and larvae.exists and b.supply_left >= 2:
            try:
                larvae_list = list(larvae)
                if larvae_list:
                    for larva in larvae_list:
                        if larva.is_ready:
                            if await self._safe_train(larva, unit_to_produce):
                                break
            except Exception:
                pass

    async def force_resource_dump(self) -> None:
        b = self.bot
        if b.can_afford(UnitTypeId.HATCHERY) and b.already_pending(UnitTypeId.HATCHERY) < 2:
            try:
                await self._try_expand()
            except Exception:
                pass
        if b.units(UnitTypeId.LARVA).exists:
            larvae = b.units(UnitTypeId.LARVA).ready
            if larvae.exists and b.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
                for larva in larvae:
                    if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
                        try:
                            await self._safe_train(larva, UnitTypeId.ZERGLING)
                        except Exception:
                            continue

    async def panic_mode_production(self) -> None:
        b = self.bot

        # EMERGENCY DEFENSE: Build Spine Crawlers at 2:30+ if enemy detected
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
                            print(
                                f"[EMERGENCY DEFENSE] [{int(b.time)}s] Building Spine Crawler for defense")
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
                    # CRITICAL FIX: Use _safe_train instead of direct train() call
                    larva = random.choice(larvae)
                    if larva.is_ready:
                        await self._safe_train(larva, UnitTypeId.ZERGLING)

    async def build_terran_counters(self) -> None:
        b = self.bot
        if not b.production:
            return
        baneling_nests = [
            s for s in b.units(UnitTypeId.BANELINGNEST).structure if s.is_ready]
        if not baneling_nests and b.already_pending(UnitTypeId.BANELINGNEST) == 0 and b.can_afford(UnitTypeId.BANELINGNEST):
            # CRITICAL: Check for duplicate construction before building
            if not b.structures(UnitTypeId.BANELINGNEST).exists:
                spawning_pools = [
                    s for s in b.units(UnitTypeId.SPAWNINGPOOL).structure if s.is_ready]
                if spawning_pools:
                    await b.build(UnitTypeId.BANELINGNEST, near=spawning_pools[0])
        roach_warrens = [
            s for s in b.units(UnitTypeId.ROACHWARREN).structure if s.is_ready]
        if not roach_warrens and b.already_pending(UnitTypeId.ROACHWARREN) == 0 and b.time > 180 and b.can_afford(UnitTypeId.ROACHWARREN):
            # CRITICAL: Check for duplicate construction before building
            if not b.structures(UnitTypeId.ROACHWARREN).exists:
                if b.townhalls.exists:
                    townhalls_list = list(b.townhalls)
                    if townhalls_list:
                        await b.build(UnitTypeId.ROACHWARREN, near=townhalls_list[0])
                else:
                    await b.build(UnitTypeId.ROACHWARREN, near=b.game_info.map_center)

    async def _auto_build_tech_structures(self) -> None:
        """
        Automatically build tech structures based on game time.

        Tech progression timeline:
        - 2:00 (120s): First Extractor
        - 2:30 (150s): Second Extractor
        - 3:00 (180s): Roach Warren
        - 4:00 (240s): Lair + Evolution Chamber
        - 5:00 (300s): Hydralisk Den (requires Lair)
        - 6:00 (360s): Spire (requires Lair)
        """
        b = self.bot
        game_time = getattr(b, "time", 0)

        # === EXTRACTORS: Build early for gas income ===
        await self._auto_build_extractors(game_time)

        # Need Spawning Pool first for all tech
        if not b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            return

        # SPAM FIX: Add cooldown for tech buildings
        last_tech_build = getattr(self, "_last_tech_build_time", 0)
        if game_time - last_tech_build < 15:  # 15 second cooldown between tech builds
            return

        # 3:00+ : Roach Warren
        if game_time >= 180:
            if not b.structures(UnitTypeId.ROACHWARREN).exists and b.already_pending(UnitTypeId.ROACHWARREN) == 0:
                if b.can_afford(UnitTypeId.ROACHWARREN) and b.townhalls.exists:
                    try:
                        await b.build(UnitTypeId.ROACHWARREN, near=b.townhalls.first.position)
                        self._last_tech_build_time = game_time
                        print(f"[AUTO TECH] [{int(game_time)}s] Building Roach Warren")
                        return  # One tech building at a time
                    except Exception:
                        pass

        # 4:00+ : Lair
        if game_time >= 240:
            if not b.structures(UnitTypeId.LAIR).exists and not b.structures(UnitTypeId.HIVE).exists:
                await self._morph_to_lair()

        # 4:00+ : Evolution Chamber (for upgrades) - Build BEFORE Hydra Den
        if game_time >= 240:
            if not b.structures(UnitTypeId.EVOLUTIONCHAMBER).exists and b.already_pending(UnitTypeId.EVOLUTIONCHAMBER) == 0:
                if b.can_afford(UnitTypeId.EVOLUTIONCHAMBER) and b.townhalls.exists:
                    try:
                        await b.build(UnitTypeId.EVOLUTIONCHAMBER, near=b.townhalls.first.position)
                        self._last_tech_build_time = game_time
                        print(f"[AUTO TECH] [{int(game_time)}s] Building Evolution Chamber")
                        return
                    except Exception:
                        pass

        # 5:00+ : Hydralisk Den (requires Lair)
        if game_time >= 300:
            has_lair = b.structures(UnitTypeId.LAIR).ready.exists or b.structures(UnitTypeId.HIVE).ready.exists
            if has_lair:
                if not b.structures(UnitTypeId.HYDRALISKDEN).exists and b.already_pending(UnitTypeId.HYDRALISKDEN) == 0:
                    if b.can_afford(UnitTypeId.HYDRALISKDEN) and b.townhalls.exists:
                        try:
                            await b.build(UnitTypeId.HYDRALISKDEN, near=b.townhalls.first.position)
                            self._last_tech_build_time = game_time
                            print(f"[AUTO TECH] [{int(game_time)}s] Building Hydralisk Den")
                            return
                        except Exception:
                            pass

        # 6:00+ : Spire (requires Lair)
        if game_time >= 360:
            has_lair = b.structures(UnitTypeId.LAIR).ready.exists or b.structures(UnitTypeId.HIVE).ready.exists
            if has_lair:
                if not b.structures(UnitTypeId.SPIRE).exists and b.already_pending(UnitTypeId.SPIRE) == 0:
                    if b.can_afford(UnitTypeId.SPIRE) and b.townhalls.exists:
                        try:
                            await b.build(UnitTypeId.SPIRE, near=b.townhalls.first.position)
                            self._last_tech_build_time = game_time
                            print(f"[AUTO TECH] [{int(game_time)}s] Building Spire")
                            return
                        except Exception:
                            pass

    async def _auto_build_extractors(self, game_time: float) -> None:
        """
        Automatically build extractors for gas income.

        Timeline:
        - 1:30 (90s): First extractor (for early Roach/tech)
        - 2:00 (120s): Second extractor (same base)
        - Each new base: Build 2 extractors
        """
        b = self.bot

        # Don't build extractors before 1:30 (need pool first usually)
        if game_time < 90:
            return

        # Count current extractors (including pending)
        extractors = b.structures(UnitTypeId.EXTRACTOR)
        extractor_count = extractors.amount if hasattr(extractors, "amount") else len(list(extractors))
        pending_extractors = b.already_pending(UnitTypeId.EXTRACTOR)
        total_extractors = extractor_count + pending_extractors

        # Calculate target extractors: 2 per base
        base_count = b.townhalls.amount if hasattr(b.townhalls, "amount") else len(list(b.townhalls))
        target_extractors = base_count * 2

        # Early game timing:
        # 1:30 (90s): First extractor
        # 2:00 (120s): Second extractor
        if game_time >= 90 and total_extractors < 1:
            target_extractors = max(target_extractors, 1)
        if game_time >= 120:
            target_extractors = max(target_extractors, 2)

        # Don't build more than needed
        if total_extractors >= target_extractors:
            return

        # SPAM FIX: Add cooldown check
        last_extractor_time = getattr(self, "_last_extractor_build_time", 0)
        if game_time - last_extractor_time < 10:  # 10 second cooldown
            return

        # Check resources
        if not b.can_afford(UnitTypeId.EXTRACTOR):
            return

        # Find available geysers
        geysers = b.vespene_geyser if hasattr(b, "vespene_geyser") else []
        if not geysers:
            return

        # Find geysers near our townhalls that don't have extractors
        for townhall in b.townhalls:
            if total_extractors >= target_extractors:
                break

            nearby_geysers = [g for g in geysers if g.distance_to(townhall.position) < 12]
            for geyser in nearby_geysers:
                # Check if this geyser already has an extractor (ready or building)
                has_extractor = any(
                    e.distance_to(geyser.position) < 2
                    for e in extractors
                )
                if has_extractor:
                    continue

                # Also check if there's a pending extractor on this geyser
                # by checking if any worker is building near it
                if pending_extractors > 0:
                    # Skip if we already have pending extractors
                    return

                # Build extractor on this geyser
                try:
                    await b.build(UnitTypeId.EXTRACTOR, geyser)
                    self._last_extractor_build_time = game_time
                    print(f"[AUTO TECH] [{int(game_time)}s] Building Extractor #{total_extractors + 1}")
                    return  # Build one at a time
                except Exception:
                    continue

    async def _morph_to_lair(self) -> bool:
        """
        Morph a Hatchery to Lair.
        Lair is required for: Hydralisk Den, Spire, Infestation Pit, etc.
        """
        b = self.bot

        # Check if we already have Lair or Hive
        if b.structures(UnitTypeId.LAIR).exists or b.structures(UnitTypeId.HIVE).exists:
            return False

        # Check requirements: Spawning Pool must be ready
        if not b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            return False

        # Check resources: Lair costs 150 minerals, 100 gas
        if b.minerals < 150 or b.vespene < 100:
            return False

        # Find an idle Hatchery to morph
        hatcheries = b.structures(UnitTypeId.HATCHERY).ready.idle
        if not hatcheries.exists:
            return False

        try:
            hatch = hatcheries.first
            # Use ability to morph to Lair
            result = hatch(AbilityId.UPGRADETOLAIR_LAIR)
            if hasattr(result, "__await__"):
                await result
            else:
                result_do = self.bot.do(result)
                if hasattr(result_do, "__await__"):
                    await result_do
            print(f"[TECH UPGRADE] [{int(b.time)}s] Morphing Hatchery to Lair")
            return True
        except Exception as e:
            if b.iteration % 200 == 0:
                print(f"[WARNING] Lair morph error: {e}")
            return False

    async def _build_spire(self) -> bool:
        """
        Build Spire for Mutalisk production.
        Requires: Lair or Hive
        """
        b = self.bot

        # Check if Spire already exists or pending
        if b.structures(UnitTypeId.SPIRE).exists or b.already_pending(UnitTypeId.SPIRE) > 0:
            return False

        # Check Lair/Hive requirement
        if not b.structures(UnitTypeId.LAIR).ready.exists and not b.structures(UnitTypeId.HIVE).ready.exists:
            return False

        # Check resources: Spire costs 200 minerals, 200 gas
        if not b.can_afford(UnitTypeId.SPIRE):
            return False

        # Build near townhall
        if b.townhalls.exists:
            try:
                await b.build(UnitTypeId.SPIRE, near=b.townhalls.first.position)
                print(f"[TECH BUILD] [{int(b.time)}s] Building Spire for Mutalisks")
                return True
            except Exception as e:
                if b.iteration % 200 == 0:
                    print(f"[WARNING] Spire build error: {e}")
        return False

    async def _produce_mutalisks(self, count: int = 5) -> int:
        """
        Produce Mutalisks from larvae.
        Mutalisk: 100 minerals, 100 gas, 2 supply

        Args:
            count: Maximum number of Mutalisks to produce

        Returns:
            Number of Mutalisks produced
        """
        b = self.bot

        # Check Spire requirement
        if not b.structures(UnitTypeId.SPIRE).ready.exists:
            return 0

        larvae = b.units(UnitTypeId.LARVA)
        if not larvae.exists:
            return 0

        produced = 0
        larvae_list = list(larvae.ready) if hasattr(larvae, 'ready') else list(larvae)

        for larva in larvae_list[:count]:
            if produced >= count:
                break

            # Check resources and supply
            if not b.can_afford(UnitTypeId.MUTALISK):
                break
            if b.supply_left < 2:
                break

            try:
                if await self._safe_train(larva, UnitTypeId.MUTALISK):
                    produced += 1
            except Exception:
                continue

        if produced > 0:
            print(f"[MUTALISK] [{int(b.time)}s] Produced {produced} Mutalisks")

        return produced

    async def _build_air_tech(self) -> None:
        """
        Build air tech progression: Lair -> Spire -> Mutalisks
        Called when minerals > 400 and gas > 200 (mid-game)
        """
        b = self.bot

        # Step 1: Ensure Lair
        if not b.structures(UnitTypeId.LAIR).exists and not b.structures(UnitTypeId.HIVE).exists:
            if b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                await self._morph_to_lair()
            return

        # Step 2: Build Spire
        if not b.structures(UnitTypeId.SPIRE).exists and b.already_pending(UnitTypeId.SPIRE) == 0:
            if b.structures(UnitTypeId.LAIR).ready.exists or b.structures(UnitTypeId.HIVE).ready.exists:
                await self._build_spire()
            return

        # Step 3: Produce Mutalisks
        if b.structures(UnitTypeId.SPIRE).ready.exists:
            # Produce more Mutalisks if we have excess resources
            mutalisk_count = b.units(UnitTypeId.MUTALISK).amount
            if mutalisk_count < 15:  # Target: 15 Mutalisks
                await self._produce_mutalisks(count=5)

    async def build_protoss_counters(self) -> None:
        b = self.bot
        if not b.production:
            return

        # First, check if we need to morph to Lair for Hydralisk Den
        lairs = b.structures(UnitTypeId.LAIR)
        hives = b.structures(UnitTypeId.HIVE)
        if not lairs.exists and not hives.exists:
            # Need Lair for Hydralisk Den - try to morph
            if b.time > 200 and b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                await self._morph_to_lair()

        hydra_dens = [
            s for s in b.units(UnitTypeId.HYDRALISKDEN).structure if s.is_ready]
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
        roach_warrens = [
            s for s in b.units(UnitTypeId.ROACHWARREN).structure if s.is_ready]
        if not roach_warrens and b.already_pending(UnitTypeId.ROACHWARREN) == 0 and b.time > 180 and b.can_afford(UnitTypeId.ROACHWARREN):
            if b.townhalls.exists:
                townhalls_list = list(b.townhalls)
                if townhalls_list:
                    await b.build(UnitTypeId.ROACHWARREN, near=townhalls_list[0])
            else:
                await b.build(UnitTypeId.ROACHWARREN, near=b.game_info.map_center)

    async def build_zerg_counters(self) -> None:
        """Build counter units against Zerg opponents.
        Note: Most tech building is now handled by _auto_build_tech_structures.
        This method adds Zerg-specific Baneling Nest priority.
        """
        b = self.bot
        if not b.production:
            return

        # Baneling Nest for anti-Zerg (Zerglings counter)
        if not b.structures(UnitTypeId.BANELINGNEST).exists and b.already_pending(UnitTypeId.BANELINGNEST) == 0:
            if b.can_afford(UnitTypeId.BANELINGNEST) and b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                if b.townhalls.exists:
                    try:
                        await b.build(UnitTypeId.BANELINGNEST, near=b.townhalls.first.position)
                    except Exception:
                        pass

    async def _determine_ideal_composition(self) -> Dict[UnitTypeId, float]:
        """Reuses bot's composition logic via in-module call."""
        return await self.bot._determine_ideal_composition()
