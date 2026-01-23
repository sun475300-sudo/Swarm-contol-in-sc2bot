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

    async def _safe_train(self, unit, unit_type, retry_count: int = 1):
        """
        Safely train a unit, handling both sync and async train() methods.

        Args:
            unit: The larva or unit to train from
            unit_type: The UnitTypeId to train
            retry_count: Number of retry attempts (default: 1)

        Returns:
            True if training succeeded, False otherwise
        """
        last_error = None

        for attempt in range(retry_count + 1):
            try:
                # Validate unit is still valid
                if not unit or not hasattr(unit, 'train'):
                    print(f"[TRAIN_ERROR] Invalid unit for training {unit_type}")
                    return False

                # Create train action and execute it via bot.do()
                action = unit.train(unit_type)
                self.bot.do(action)  # bot.do() is not async, just call it
                return True

            except Exception as e:
                last_error = e
                game_time = getattr(self.bot, "time", 0.0)

                # Always log errors (not just every 200 iterations)
                if attempt == retry_count:  # Final attempt failed
                    print(f"[TRAIN_ERROR] [{int(game_time)}s] Failed to train {unit_type}: {e}")
                else:
                    print(f"[TRAIN_WARN] [{int(game_time)}s] Retry {attempt + 1}/{retry_count} for {unit_type}: {e}")

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

                # === UNIQUE TECH BUILDINGS: Only allow ONE of each ===
                unique_tech_buildings = [
                    UnitTypeId.SPAWNINGPOOL, UnitTypeId.ROACHWARREN,
                    UnitTypeId.BANELINGNEST, UnitTypeId.HYDRALISKDEN,
                    UnitTypeId.SPIRE, UnitTypeId.GREATERSPIRE,
                    UnitTypeId.INFESTATIONPIT, UnitTypeId.ULTRALISKCAVERN,
                    UnitTypeId.EVOLUTIONCHAMBER, UnitTypeId.LURKERDENMP,
                ]

                if structure_type in unique_tech_buildings:
                    try:
                        # Check if exists OR pending
                        if (self.bot.structures(structure_type).exists or
                            self.bot.already_pending(structure_type) > 0):
                            return None  # Silently block duplicate
                        # Check reservation (5 second cooldown for unique buildings)
                        if ts is not None and now - ts < 5.0:
                            return None
                    except Exception:
                        pass

                # Skip if recently reserved (another manager already issued the build)
                if ts is not None and now - ts < 30.0:
                    return None

                reservations[structure_type] = now
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

        # === GAS OVERFLOW PREVENTION: Spend gas when > 1500 ===
        if b.vespene > 1500:
            await self._spend_excess_gas()

        # === MINERAL OVERFLOW PREVENTION: Spend minerals when > 200 ===
        if b.minerals > 200:
            await self._spend_excess_minerals()

        # === AGGRESSIVE EXPANSION: When minerals > 400, prioritize expansion ===
        # Zerg needs expansions for macro advantage
        # IMPROVED: 1분 이후 조기 확장 (자원 여유 시)
        time = getattr(b, "time", 0.0)
        if time >= 60 and b.minerals > 400 and b.already_pending(UnitTypeId.HATCHERY) == 0:
            bases = b.townhalls.amount if hasattr(b, "townhalls") else 1
            # Always try to have one more base building
            if b.can_afford(UnitTypeId.HATCHERY):
                try:
                    if await self._try_expand():
                        print(f"[EARLY_EXPAND] [{int(time)}s] Expanding at 1min+ with {int(b.minerals)} minerals (bases: {bases})")
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

        # === COUNTER ENEMY COMPOSITION ===
        # Analyze enemy units and produce counters
        enemy_units = getattr(b, "enemy_units", [])
        counter_unit = self._get_counter_unit(enemy_units, has_roach_warren, has_hydra_den, has_spire)

        if counter_unit and b.can_afford(counter_unit) and b.supply_left >= 2:
            return await self._safe_train(larva, counter_unit)

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

    async def _ensure_early_defense(self, game_time: float, supply_used: int) -> None:
        """
        3분 전 방어 유닛 빌드 최적화

        목표:
        - 2:00 (120초): 스포닝 풀 완료
        - 2:30 (150초): 최소 6저글링 + 퀸 생산 시작
        - 3:00 (180초): 최소 8저글링 + 퀸 1기 완료

        프로게이머 빌드 참고:
        - 서랄(Serral): 16해처리 → 18가스 → 17풀 → 퀸 우선
        - 이병렬(Rogue): 13풀 → 퀸 → 저글링 러쉬 옵션
        """
        b = self.bot

        try:
            # 게임 시간 180초(3분) 이후는 이 로직 스킵
            if game_time > 180:
                return

            # === 스포닝 풀 확인 ===
            spawning_pool_exists = b.structures(UnitTypeId.SPAWNINGPOOL).exists
            spawning_pool_ready = b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists
            spawning_pool_pending = b.already_pending(UnitTypeId.SPAWNINGPOOL) > 0

            # 100초(1:40) 이후 스포닝 풀이 없으면 긴급 건설
            if game_time >= 100 and not spawning_pool_exists and not spawning_pool_pending:
                if b.can_afford(UnitTypeId.SPAWNINGPOOL) and b.townhalls.exists:
                    try:
                        main_base = b.townhalls.first
                        await b.build(
                            UnitTypeId.SPAWNINGPOOL,
                            near=main_base.position.towards(b.game_info.map_center, 5),
                        )
                        print(f"[EARLY_DEFENSE] [{int(game_time)}s] Emergency Spawning Pool build")
                        return
                    except Exception:
                        pass

            # 스포닝 풀이 완료되지 않았으면 대기
            if not spawning_pool_ready:
                return

            # === 퀸 생산 확인 (방어 + 인젝트 핵심) ===
            queens = b.units(UnitTypeId.QUEEN) if hasattr(b, "units") else []
            queen_count = queens.amount if hasattr(queens, "amount") else 0
            queen_pending = b.already_pending(UnitTypeId.QUEEN)

            # 120초(2분) 이후 퀸이 없으면 긴급 생산
            if game_time >= 120 and queen_count == 0 and queen_pending == 0:
                if b.townhalls.ready.exists and b.can_afford(UnitTypeId.QUEEN):
                    try:
                        for hatchery in b.townhalls.ready:
                            if not hatchery.is_idle:
                                continue
                            b.do(hatchery.train(UnitTypeId.QUEEN))
                            print(f"[EARLY_DEFENSE] [{int(game_time)}s] Emergency Queen production")
                            break
                    except Exception:
                        pass

            # === 저글링 생산 (최소 방어 병력) ===
            zerglings = b.units(UnitTypeId.ZERGLING) if hasattr(b, "units") else []
            zergling_count = zerglings.amount if hasattr(zerglings, "amount") else 0
            zergling_pending = b.already_pending(UnitTypeId.ZERGLING)

            # 150초(2:30) 이후 저글링 6기 미만이면 긴급 생산
            min_zerglings_150s = 6
            min_zerglings_180s = 8

            target_zerglings = min_zerglings_150s if game_time < 180 else min_zerglings_180s

            if game_time >= 150 and (zergling_count + zergling_pending) < target_zerglings:
                larvae = b.units(UnitTypeId.LARVA) if hasattr(b, "units") else []
                if larvae.exists and b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
                    larvae_list = list(larvae.ready) if hasattr(larvae, 'ready') else list(larvae)
                    zerglings_to_produce = min(4, target_zerglings - zergling_count - zergling_pending)

                    for larva in larvae_list[:zerglings_to_produce]:
                        if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
                            # _safe_train already handles exceptions internally
                            await self._safe_train(larva, UnitTypeId.ZERGLING)

                    if zerglings_to_produce > 0:
                        print(f"[EARLY_DEFENSE] [{int(game_time)}s] Emergency Zergling production: {zergling_count} -> {target_zerglings}")

            # === 서플라이 확인 (오버로드) ===
            if b.supply_left < 2 and b.supply_cap < 200:
                larvae = b.units(UnitTypeId.LARVA) if hasattr(b, "units") else []
                if larvae.exists and b.can_afford(UnitTypeId.OVERLORD):
                    larvae_list = list(larvae.ready) if hasattr(larvae, 'ready') else list(larvae)
                    if larvae_list:
                        # _safe_train handles exceptions internally
                        await self._safe_train(larvae_list[0], UnitTypeId.OVERLORD)

        except Exception as e:
            game_time = getattr(b, "time", 0.0)
            print(f"[DEFENSE_ERROR] [{int(game_time)}s] _ensure_early_defense error: {e}")

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

        3분 전 방어 유닛 목표:
        - 2:00 (120초): 스포닝 풀 완료
        - 2:30 (150초): 최소 6저글링 + 퀸 1기 생산 시작
        - 3:00 (180초): 최소 8저글링 + 퀸 1기 완료
        """
        b = self.bot
        time = getattr(b, "time", 0.0)
        supply_used = getattr(b, "supply_used", 0)

        try:
            # === 3분 전 방어 유닛 빌드 최적화 ===
            await self._ensure_early_defense(time, supply_used)

            # Priority 1: Fast Spawning Pool (supply 13-15)
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
                larvae_list = list(larvae)
                if larvae_list:
                    # _safe_train handles exceptions internally
                    await self._safe_train(larvae_list[0], UnitTypeId.OVERLORD)

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
                        # _safe_train handles exceptions internally
                        if await self._safe_train(larva, UnitTypeId.OVERLORD):
                            overlords_produced += 1

            # Unit production
            spawning_pools = b.units(UnitTypeId.SPAWNINGPOOL).ready
            if spawning_pools.exists and larvae.exists:
                larvae_list = list(larvae)
                max_production = min(10, len(larvae_list))
                for larva in larvae_list[:max_production]:
                    if not larva.is_ready:
                        continue
                    if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
                        # _safe_train handles exceptions internally
                        await self._safe_train(larva, UnitTypeId.ZERGLING)

            roach_warrens = b.units(UnitTypeId.ROACHWARREN).ready
            if roach_warrens.exists and larvae.exists:
                larvae_list = list(larvae)
                max_production = min(5, len(larvae_list))
                for larva in larvae_list[:max_production]:
                    if not larva.is_ready:
                        continue
                    if b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
                        # _safe_train handles exceptions internally
                        await self._safe_train(larva, UnitTypeId.ROACH)

            hydra_dens = b.units(UnitTypeId.HYDRALISKDEN).ready
            if hydra_dens.exists and larvae.exists:
                larvae_list = list(larvae)
                max_production = min(5, len(larvae_list))
                for larva in larvae_list[:max_production]:
                    if not larva.is_ready:
                        continue
                    if b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                        # _safe_train handles exceptions internally
                        await self._safe_train(larva, UnitTypeId.HYDRALISK)

        except Exception as e:
            game_time = getattr(b, "time", 0.0)
            print(f"[BOOST_ERROR] [{int(game_time)}s] _boost_early_game error: {e}")

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
                        # _safe_train handles exceptions internally
                        await self._safe_train(larva, UnitTypeId.ZERGLING)

    async def panic_mode_production(self) -> None:
        b = self.bot

        # === PROACTIVE DEFENSE: Build defenses earlier ===
        # Build 1st Spine at 3:00, 2nd at 4:00 (regardless of enemy detection)
        await self._build_early_defense(b)

    async def _build_early_defense(self, b) -> None:
        """
        Build defense structures proactively.

        IMPROVED Timeline:
        - 2:00 (120s): First Spine Crawler (러쉬 대비)
        - 3:00 (180s): Second Spine Crawler
        - 3:30 (210s): First Spore Crawler (오라클/뮤탈 대비)
        - 4:00 (240s): Third Spine Crawler (중기 방어)
        - 확장 기지마다 스파인 + 스포어 1개씩
        """
        game_time = getattr(b, "time", 0)

        # Need Spawning Pool for defense structures
        if not b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            return

        spine_crawlers = b.structures(UnitTypeId.SPINECRAWLER)
        spine_count = spine_crawlers.amount if hasattr(spine_crawlers, 'amount') else len(list(spine_crawlers))
        pending_spines = b.already_pending(UnitTypeId.SPINECRAWLER)

        spore_crawlers = b.structures(UnitTypeId.SPORECRAWLER)
        spore_count = spore_crawlers.amount if hasattr(spore_crawlers, 'amount') else 0
        pending_spores = b.already_pending(UnitTypeId.SPORECRAWLER)

        # Defense cooldown to prevent spam (15초로 더 줄임)
        last_defense_time = getattr(self, "_last_defense_build_time", 0)
        if game_time - last_defense_time < 15:
            return

        # === 러쉬 감지 시 긴급 방어 ===
        under_attack = self._detect_early_rush(b)
        if under_attack and spine_count < 2:
            if b.can_afford(UnitTypeId.SPINECRAWLER) and b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    defense_pos = main_base.position.towards(b.game_info.map_center, 6)
                    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    print(f"[EMERGENCY DEFENSE] [{int(game_time)}s] RUSH DETECTED - Building Spine Crawler!")
                    return
                except Exception:
                    pass

        # 2:00+ : First Spine Crawler (더 빠른 방어)
        if game_time >= 120 and spine_count + pending_spines < 1:
            if b.can_afford(UnitTypeId.SPINECRAWLER) and b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    defense_pos = main_base.position.towards(b.game_info.map_center, 7)
                    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    print(f"[DEFENSE] [{int(game_time)}s] Building Spine Crawler #1")
                    return
                except Exception:
                    pass

        # 3:00+ : Second Spine Crawler
        if game_time >= 180 and spine_count + pending_spines < 2:
            if b.can_afford(UnitTypeId.SPINECRAWLER) and b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    defense_pos = main_base.position.towards(b.game_info.map_center, 9)
                    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    print(f"[DEFENSE] [{int(game_time)}s] Building Spine Crawler #2")
                    return
                except Exception:
                    pass

        # 3:30+ : First Spore Crawler (대공 방어 - 오라클/뮤탈 대비)
        if game_time >= 210 and spore_count + pending_spores < 1:
            if b.can_afford(UnitTypeId.SPORECRAWLER) and b.townhalls.exists:
                try:
                    # 미네랄 라인 근처에 배치 (일꾼 보호)
                    main_base = b.townhalls.first
                    minerals = b.mineral_field.closer_than(10, main_base)
                    if minerals:
                        mineral_center = minerals.center
                        defense_pos = main_base.position.towards(mineral_center, 4)
                    else:
                        defense_pos = main_base.position
                    await b.build(UnitTypeId.SPORECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    print(f"[DEFENSE] [{int(game_time)}s] Building Spore Crawler #1 (anti-air)")
                    return
                except Exception:
                    pass

        # 4:00+ : Third Spine Crawler
        if game_time >= 240 and spine_count + pending_spines < 3:
            if b.can_afford(UnitTypeId.SPINECRAWLER) and b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    defense_pos = main_base.position.towards(b.game_info.map_center, 11)
                    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                    self._last_defense_build_time = game_time
                    print(f"[DEFENSE] [{int(game_time)}s] Building Spine Crawler #3")
                    return
                except Exception:
                    pass

        # === 확장 기지 방어 (5분 이후) ===
        if game_time >= 300:
            await self._build_expansion_defense(b, game_time)

    async def _build_expansion_defense(self, b, game_time: float) -> None:
        """확장 기지에 방어 건물 건설"""
        townhalls = b.townhalls.ready
        if townhalls.amount <= 1:
            return

        # 확장 기지마다 스파인 1개 + 스포어 1개 목표
        for th in townhalls:
            if th == b.townhalls.first:
                continue  # 메인 기지는 이미 처리

            # 이 기지 주변 방어 건물 확인
            nearby_spines = b.structures(UnitTypeId.SPINECRAWLER).closer_than(15, th)
            nearby_spores = b.structures(UnitTypeId.SPORECRAWLER).closer_than(15, th)

            spine_count = nearby_spines.amount if hasattr(nearby_spines, 'amount') else 0
            spore_count = nearby_spores.amount if hasattr(nearby_spores, 'amount') else 0

            # 스파인 크롤러 부족 시
            if spine_count < 1:
                if b.can_afford(UnitTypeId.SPINECRAWLER):
                    try:
                        defense_pos = th.position.towards(b.game_info.map_center, 6)
                        await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
                        self._last_defense_build_time = game_time
                        print(f"[DEFENSE] [{int(game_time)}s] Building Spine at expansion")
                        return
                    except Exception:
                        pass

            # 스포어 크롤러 부족 시
            if spore_count < 1:
                if b.can_afford(UnitTypeId.SPORECRAWLER):
                    try:
                        await b.build(UnitTypeId.SPORECRAWLER, near=th.position)
                        self._last_defense_build_time = game_time
                        print(f"[DEFENSE] [{int(game_time)}s] Building Spore at expansion")
                        return
                    except Exception:
                        pass

    def _detect_early_rush(self, b) -> bool:
        """초반 러쉬 감지"""
        game_time = getattr(b, "time", 0)
        if game_time > 180:  # 3분 이후는 일반 대응
            return False

        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return False

        # 러쉬 유닛 목록
        rush_units = {'ZERGLING', 'MARINE', 'ZEALOT', 'REAPER', 'ADEPT', 'ROACH'}

        for enemy in enemy_units:
            enemy_type = getattr(enemy.type_id, "name", "").upper()
            if enemy_type in rush_units:
                # 기지 근처에 있으면 러쉬로 판단
                for th in b.townhalls:
                    if enemy.distance_to(th.position) < 35:
                        return True
        return False

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
        # NOTE: Roach Warren building is now handled by _auto_build_tech_structures()
        # Removed duplicate code to prevent building spam

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

        # Check if Lair is already pending (Hatchery morphing to Lair)
        if b.already_pending(UnitTypeId.LAIR) > 0:
            return False

        # Cooldown check to prevent spam
        game_time = getattr(b, "time", 0)
        last_lair_morph = getattr(self, "_last_lair_morph_time", 0)
        if game_time - last_lair_morph < 30:  # 30 second cooldown
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
            self._last_lair_morph_time = game_time
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

            # _safe_train handles exceptions internally
            if await self._safe_train(larva, UnitTypeId.MUTALISK):
                produced += 1

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
        # NOTE: Roach Warren building is now handled by _auto_build_tech_structures()
        # Removed duplicate code to prevent building spam

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

    def _get_counter_unit(self, enemy_units, has_roach_warren: bool, has_hydra_den: bool, has_spire: bool):
        """
        Analyze enemy composition and return the best counter unit.

        Counter logic:
        - vs Marines/Zealots/Zerglings (light infantry): Banelings (if nest) > Roaches
        - vs Roaches/Stalkers/Marauders (armored ground): Hydralisks > Roaches
        - vs Air units (Void Rays, Mutas, Vikings): Hydralisks > Mutalisks
        - vs Siege Tanks/Colossus (siege): Mutalisks (to flank) > Roaches
        - vs Immortals (anti-armor): Zerglings (swarm) > Hydralisks

        Args:
            enemy_units: List of detected enemy units
            has_roach_warren: Whether Roach Warren is ready
            has_hydra_den: Whether Hydralisk Den is ready
            has_spire: Whether Spire is ready

        Returns:
            UnitTypeId of the recommended counter unit, or None
        """
        if not enemy_units:
            return None

        b = self.bot

        # Count enemy unit types
        enemy_counts = {
            "light_infantry": 0,  # Marines, Zealots, Zerglings
            "armored_ground": 0,  # Roaches, Stalkers, Marauders
            "air": 0,             # Any flying units
            "siege": 0,           # Siege Tanks, Colossus
            "anti_armor": 0,      # Immortals
        }

        # Light infantry unit IDs
        light_infantry_ids = ["MARINE", "ZEALOT", "ZERGLING", "ADEPT"]
        armored_ground_ids = ["ROACH", "STALKER", "MARAUDER", "IMMORTAL", "RAVAGER"]
        air_unit_ids = ["VOIDRAY", "PHOENIX", "ORACLE", "CARRIER", "TEMPEST",
                        "VIKINGFIGHTER", "BANSHEE", "BATTLECRUISER", "LIBERATOR",
                        "MUTALISK", "CORRUPTOR", "BROODLORD"]
        siege_ids = ["SIEGETANK", "SIEGETANKSIEGED", "COLOSSUS", "DISRUPTOR"]
        anti_armor_ids = ["IMMORTAL"]

        for enemy in enemy_units:
            enemy_name = getattr(enemy.type_id, "name", "")

            if any(light_id in enemy_name for light_id in light_infantry_ids):
                enemy_counts["light_infantry"] += 1
            if any(armored_id in enemy_name for armored_id in armored_ground_ids):
                enemy_counts["armored_ground"] += 1
            if any(air_id in enemy_name for air_id in air_unit_ids):
                enemy_counts["air"] += 1
            if any(siege_id in enemy_name for siege_id in siege_ids):
                enemy_counts["siege"] += 1
            if any(aa_id in enemy_name for aa_id in anti_armor_ids):
                enemy_counts["anti_armor"] += 1

        # Determine main threat
        max_threat = max(enemy_counts.values())
        if max_threat == 0:
            return None

        main_threats = [k for k, v in enemy_counts.items() if v == max_threat]
        main_threat = main_threats[0]

        # Return counter unit based on threat
        if main_threat == "air":
            # vs Air: Hydralisks > Mutalisks
            if has_hydra_den and b.can_afford(UnitTypeId.HYDRALISK):
                return UnitTypeId.HYDRALISK
            if has_spire and b.can_afford(UnitTypeId.MUTALISK):
                return UnitTypeId.MUTALISK

        elif main_threat == "light_infantry":
            # vs Light: Banelings > Roaches
            has_baneling_nest = b.structures(UnitTypeId.BANELINGNEST).ready.exists
            if has_baneling_nest:
                # Note: Banelings are morphed from Zerglings, not trained from larvae
                # Return None here; baneling morphing should be handled separately
                pass
            if has_roach_warren and b.can_afford(UnitTypeId.ROACH):
                return UnitTypeId.ROACH

        elif main_threat == "armored_ground":
            # vs Armored: Hydralisks > Roaches
            if has_hydra_den and b.can_afford(UnitTypeId.HYDRALISK):
                return UnitTypeId.HYDRALISK
            if has_roach_warren and b.can_afford(UnitTypeId.ROACH):
                return UnitTypeId.ROACH

        elif main_threat == "siege":
            # vs Siege: Mutalisks (flank) > Roaches
            if has_spire and b.can_afford(UnitTypeId.MUTALISK):
                return UnitTypeId.MUTALISK
            if has_roach_warren and b.can_afford(UnitTypeId.ROACH):
                return UnitTypeId.ROACH

        elif main_threat == "anti_armor":
            # vs Immortals: Zerglings (swarm) > Hydralisks
            if b.can_afford(UnitTypeId.ZERGLING) and b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                return UnitTypeId.ZERGLING
            if has_hydra_den and b.can_afford(UnitTypeId.HYDRALISK):
                return UnitTypeId.HYDRALISK

        return None

    # === SCOUTING LOGIC ===

    async def manage_zergling_scouts(self) -> None:
        """
        Manage Zergling scouts to explore enemy bases and detect compositions.

        Scout timing:
        - 2:30 (150s): Send first scout pair to enemy natural
        - 4:00 (240s): Scout enemy main base
        - Every 60s after: Continuous scouting

        Scout behavior:
        - Send 2 Zerglings at a time (survivability)
        - Store detected enemy units for counter-unit production
        - Avoid engaging unless overwhelming advantage
        """
        b = self.bot
        game_time = getattr(b, "time", 0)

        # Need Spawning Pool and some Zerglings first
        if not b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            return

        zerglings = b.units(UnitTypeId.ZERGLING)
        if not zerglings.exists or zerglings.amount < 4:
            return  # Need at least 4 Zerglings (2 for scouting, 2 for defense)

        # Initialize scouting state
        if not hasattr(self, "_scout_state"):
            self._scout_state = {
                "last_scout_time": 0,
                "scout_tags": set(),
                "scout_interval": 60,  # Scout every 60 seconds
                "detected_enemy_units": [],
                "enemy_base_scouted": False,
            }

        scout_state = self._scout_state

        # Check if it's time to send scouts
        time_since_last_scout = game_time - scout_state["last_scout_time"]

        # First scout at 2:30 (150s)
        should_scout = False
        if game_time >= 150 and not scout_state["enemy_base_scouted"]:
            should_scout = True
        elif time_since_last_scout >= scout_state["scout_interval"]:
            should_scout = True

        if not should_scout:
            # Just manage existing scouts
            await self._manage_existing_scouts()
            return

        # Send new scouts
        await self._send_zergling_scouts()
        scout_state["last_scout_time"] = game_time

        # Update detected enemies
        await self._update_detected_enemies()

    async def _send_zergling_scouts(self) -> None:
        """Send 2 Zerglings to scout enemy base."""
        b = self.bot

        zerglings = b.units(UnitTypeId.ZERGLING)
        if not zerglings.exists or zerglings.amount < 4:
            return

        scout_state = self._scout_state

        # Find idle or nearby Zerglings not already scouting
        available_zerglings = zerglings.filter(
            lambda z: z.tag not in scout_state["scout_tags"]
        )

        if available_zerglings.amount < 2:
            return

        # Get scout targets
        scout_targets = self._get_scout_targets()
        if not scout_targets:
            return

        # Assign 2 Zerglings to scout
        scouts_sent = 0
        for ling in available_zerglings:
            if scouts_sent >= 2:
                break

            if not scout_targets:
                break

            target = scout_targets[scouts_sent % len(scout_targets)]

            try:
                ling.move(target)
                scout_state["scout_tags"].add(ling.tag)
                scouts_sent += 1
            except Exception:
                continue

        if scouts_sent > 0:
            game_time = getattr(b, "time", 0)
            print(f"[SCOUT] [{int(game_time)}s] Sent {scouts_sent} Zerglings to scout enemy base")

    def _get_scout_targets(self):
        """Get positions to scout (enemy start locations, expansions)."""
        b = self.bot
        targets = []

        # Primary: Enemy start location
        if hasattr(b, "enemy_start_locations") and b.enemy_start_locations:
            targets.append(b.enemy_start_locations[0])

        # Secondary: Natural expansion position (approximation)
        if targets:
            main_pos = targets[0]
            # Natural is usually towards map center
            if hasattr(b, "game_info") and hasattr(b.game_info, "map_center"):
                natural_approx = main_pos.towards(b.game_info.map_center, 20)
                targets.append(natural_approx)

        return targets

    async def _manage_existing_scouts(self) -> None:
        """
        Manage scouts that are already sent out.
        - Remove dead scouts from tracking
        - Re-assign scouts that are idle
        - Update detected enemies
        """
        b = self.bot
        scout_state = self._scout_state

        # Clean up dead scouts
        zerglings = b.units(UnitTypeId.ZERGLING)
        alive_tags = {z.tag for z in zerglings}
        dead_scouts = scout_state["scout_tags"] - alive_tags
        scout_state["scout_tags"] -= dead_scouts

        # Check scout status
        for ling in zerglings:
            if ling.tag not in scout_state["scout_tags"]:
                continue

            # If scout is idle, send it to a new target
            if ling.is_idle:
                targets = self._get_scout_targets()
                if targets:
                    try:
                        ling.move(targets[0])
                    except Exception:
                        pass

        # Update detected enemies
        await self._update_detected_enemies()

    async def _update_detected_enemies(self) -> None:
        """Update the list of detected enemy units for counter-production."""
        b = self.bot
        scout_state = self._scout_state

        # Get all enemy units we can see
        enemy_units = getattr(b, "enemy_units", [])
        if enemy_units:
            # Store a snapshot of enemy types for analysis
            enemy_info = []
            for enemy in enemy_units:
                enemy_name = getattr(enemy.type_id, "name", "UNKNOWN")
                enemy_info.append({
                    "type": enemy_name,
                    "tag": enemy.tag,
                    "position": enemy.position,
                })

            scout_state["detected_enemy_units"] = enemy_info
            scout_state["enemy_base_scouted"] = True

            # Log enemy composition periodically
            if b.iteration % 200 == 0 and enemy_info:
                enemy_summary = {}
                for e in enemy_info:
                    t = e["type"]
                    enemy_summary[t] = enemy_summary.get(t, 0) + 1
                print(f"[SCOUT] Detected enemies: {enemy_summary}")

    def get_detected_enemy_composition(self) -> Dict[str, int]:
        """
        Get a summary of detected enemy unit types.
        Can be used by other managers for decision making.
        """
        if not hasattr(self, "_scout_state"):
            return {}

        enemy_info = self._scout_state.get("detected_enemy_units", [])
        composition = {}
        for e in enemy_info:
            t = e.get("type", "UNKNOWN")
            composition[t] = composition.get(t, 0) + 1

        return composition

    # === GAS OVERFLOW PREVENTION ===

    async def _spend_excess_gas(self) -> None:
        """
        Spend excess gas to prevent overflow (> 3000).

        Priority for gas spending:
        1. Mutalisks (100 gas) - if Spire ready
        2. Hydralisks (50 gas) - if Hydra Den ready
        3. Roaches (25 gas) - if Roach Warren ready
        4. Tech buildings (Spire: 200 gas, Hydra Den: 100 gas)
        5. Lair/Hive upgrades (100-150 gas)
        6. Evolution upgrades (consume gas over time)
        """
        b = self.bot
        gas = b.vespene
        game_time = getattr(b, "time", 0)

        if gas <= 1500:
            return

        # Log gas overflow warning
        if b.iteration % 100 == 0:
            print(f"[GAS OVERFLOW] [{int(game_time)}s] Gas: {int(gas)} - Spending excess gas")

        # Check for larvae
        larvae = b.units(UnitTypeId.LARVA)
        if not larvae.exists:
            # No larvae - try to build tech and MACRO HATCHERY for more larvae
            await self._build_gas_heavy_tech()
            # Build macro hatchery when gas > 2000 and no larvae (desperate for larvae)
            if gas > 2000 and b.minerals > 250 and b.already_pending(UnitTypeId.HATCHERY) < 2:
                try:
                    await b.expand_now()
                    print(f"[GAS SINK] Building Macro Hatchery (no larvae, gas: {int(gas)})")
                except Exception:
                    pass
            return

        larvae_list = list(larvae.ready) if hasattr(larvae, 'ready') else list(larvae)

        # === PRIORITY 0: Build Overlords if supply blocked ===
        # 더 공격적인 오버로드 생산: supply_left < 8 로 조정
        overlords_needed = 0
        if b.supply_left < 8:
            # 가스가 높으면 더 많은 오버로드 생산 (미래 유닛 생산 대비)
            overlords_needed = min(10, (gas - 1000) // 300)  # 가스 1300당 오버로드 1기
            overlords_needed = max(overlords_needed, (8 - b.supply_left) // 2)  # 최소 서플라이 확보

            overlords_produced = 0
            for larva in larvae_list[:overlords_needed]:
                if b.can_afford(UnitTypeId.OVERLORD):
                    if await self._safe_train(larva, UnitTypeId.OVERLORD):
                        overlords_produced += 1
                        larvae_list = [l for l in larvae_list if l.tag != larva.tag]
            if overlords_produced > 0:
                print(f"[GAS SINK] Produced {overlords_produced} Overlords (supply: {int(b.supply_left)} -> {int(b.supply_left + overlords_produced * 8)})")
                # Continue to produce gas units

        if not larvae_list:
            await self._build_gas_heavy_tech()
            return

        total_produced = 0

        # Priority 1: Mutalisks (100 gas each) - Best gas sink
        has_spire = b.structures(UnitTypeId.SPIRE).ready.exists
        if has_spire and b.vespene > 1000:
            produced = 0
            for larva in larvae_list[:10]:  # Produce up to 10 Mutalisks
                if b.vespene < 100:
                    break
                if b.supply_left < 2:
                    break
                if b.can_afford(UnitTypeId.MUTALISK):
                    if await self._safe_train(larva, UnitTypeId.MUTALISK):
                        produced += 1
                        larvae_list = [l for l in larvae_list if l.tag != larva.tag]
            if produced > 0:
                total_produced += produced
                print(f"[GAS SINK] Produced {produced} Mutalisks")

        # Priority 2: Hydralisks (50 gas each)
        has_hydra_den = b.structures(UnitTypeId.HYDRALISKDEN).ready.exists
        if has_hydra_den and b.vespene > 500:
            produced = 0
            for larva in larvae_list[:15]:  # Produce up to 15 Hydralisks
                if b.vespene < 50:
                    break
                if b.supply_left < 2:
                    break
                if b.can_afford(UnitTypeId.HYDRALISK):
                    if await self._safe_train(larva, UnitTypeId.HYDRALISK):
                        produced += 1
                        larvae_list = [l for l in larvae_list if l.tag != larva.tag]
            if produced > 0:
                total_produced += produced
                print(f"[GAS SINK] Produced {produced} Hydralisks")

        # Priority 3: Roaches (25 gas each)
        has_roach_warren = b.structures(UnitTypeId.ROACHWARREN).ready.exists
        if has_roach_warren and b.vespene > 300:
            produced = 0
            for larva in larvae_list[:20]:  # Produce up to 20 Roaches
                if b.vespene < 25:
                    break
                if b.supply_left < 2:
                    break
                if b.can_afford(UnitTypeId.ROACH):
                    if await self._safe_train(larva, UnitTypeId.ROACH):
                        produced += 1
                        larvae_list = [l for l in larvae_list if l.tag != larva.tag]
            if produced > 0:
                total_produced += produced
                print(f"[GAS SINK] Produced {produced} Roaches")

        # Log total production
        if total_produced > 0:
            print(f"[GAS SINK] Total: {total_produced} units (Gas: {int(gas)} -> {int(b.vespene)})")
            return

        # Priority 4: Build gas-heavy tech buildings if no units produced
        await self._build_gas_heavy_tech()

    async def _spend_excess_minerals(self) -> None:
        """
        Spend excess minerals to keep bank below 200.

        Priority for mineral spending:
        1. Drones (if under saturation)
        2. Overlords (if supply blocked)
        3. Zerglings (cheap, fast to produce)
        4. Queens (inject larvae)
        5. Expansions (more income)
        6. Macro hatcheries (more larvae)
        """
        b = self.bot
        minerals = b.minerals

        if minerals <= 200:
            return

        # Calculate how much to spend
        excess = minerals - 200

        larvae = b.units(UnitTypeId.LARVA)
        if not larvae.exists:
            # No larvae - try to build hatchery or queens
            await self._spend_minerals_without_larvae()
            return

        larvae_list = list(larvae.ready) if hasattr(larvae, 'ready') else list(larvae)
        total_produced = 0

        # Priority 1: Overlords if supply blocked
        if b.supply_left < 4:
            for larva in larvae_list[:3]:
                if b.minerals < 100:
                    break
                if b.can_afford(UnitTypeId.OVERLORD):
                    if await self._safe_train(larva, UnitTypeId.OVERLORD):
                        total_produced += 1
                        larvae_list = [l for l in larvae_list if l.tag != larva.tag]

        # Priority 2: Drones if under saturation
        if b.minerals > 150:
            drone_count = b.workers.amount if hasattr(b, "workers") else 0
            base_count = b.townhalls.amount if hasattr(b, "townhalls") else 1
            target_drones = base_count * 16  # 16 mineral workers per base

            if drone_count < target_drones:
                drones_to_make = min(5, target_drones - drone_count)
                for larva in larvae_list[:drones_to_make]:
                    if b.minerals < 50 or b.supply_left < 1:
                        break
                    if b.can_afford(UnitTypeId.DRONE):
                        if await self._safe_train(larva, UnitTypeId.DRONE):
                            total_produced += 1
                            larvae_list = [l for l in larvae_list if l.tag != larva.tag]

        # Priority 3: Zerglings (25 minerals each, very cost-effective)
        if b.minerals > 200 and b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            zerglings_to_make = min(10, (b.minerals - 150) // 25)  # Leave 150 buffer
            for larva in larvae_list[:zerglings_to_make]:
                if b.minerals < 50 or b.supply_left < 1:
                    break
                if b.can_afford(UnitTypeId.ZERGLING):
                    if await self._safe_train(larva, UnitTypeId.ZERGLING):
                        total_produced += 1
                        larvae_list = [l for l in larvae_list if l.tag != larva.tag]

        if total_produced > 0 and b.iteration % 100 == 0:
            print(f"[MINERAL SINK] Produced {total_produced} units (M: {int(minerals)} -> {int(b.minerals)})")

    async def _spend_minerals_without_larvae(self) -> None:
        """Spend minerals when no larvae available."""
        b = self.bot

        if b.minerals <= 200:
            return

        # Build Queens (150 minerals each, provides larvae inject)
        queen_count = b.units(UnitTypeId.QUEEN).amount if hasattr(b, "units") else 0
        base_count = b.townhalls.amount if hasattr(b, "townhalls") else 1

        if queen_count < base_count and b.minerals >= 150:
            idle_hatcheries = b.townhalls.ready.idle
            if idle_hatcheries.exists:
                for hatch in idle_hatcheries:
                    if b.can_afford(UnitTypeId.QUEEN):
                        try:
                            # bot.do() is NOT async in python-sc2
                            b.do(hatch.train(UnitTypeId.QUEEN))
                            return
                        except Exception:
                            pass

        # Build expansion if minerals > 300
        if b.minerals > 300 and b.already_pending(UnitTypeId.HATCHERY) == 0:
            try:
                if await self._try_expand():
                    return
            except Exception:
                pass

        # Build macro hatchery if minerals > 400
        if b.minerals > 400 and b.townhalls.exists:
            # Check if we don't have too many hatcheries already
            if b.townhalls.amount < 5:
                try:
                    await b.build(UnitTypeId.HATCHERY, near=b.townhalls.first.position)
                except Exception:
                    pass

    async def _build_gas_heavy_tech(self) -> None:
        """
        Build gas-heavy tech buildings to spend excess gas.
        Uses existing tech building methods to avoid duplication.

        Buildings (gas cost):
        - Spire: 200 gas
        - Hydralisk Den: 100 gas
        - Infestation Pit: 100 gas
        - Hive upgrade: 150 gas
        """
        b = self.bot
        gas = b.vespene

        if gas <= 1500:
            return

        # Need Lair for most gas-heavy tech
        has_lair = b.structures(UnitTypeId.LAIR).ready.exists or b.structures(UnitTypeId.HIVE).ready.exists

        # Build Spire using existing method (200 gas)
        if has_lair:
            result = await self._build_spire()
            if result:
                print(f"[GAS SINK] Building Spire (200 gas)")
                return

        # Build Hydralisk Den if don't have one (100 gas)
        if has_lair and not b.structures(UnitTypeId.HYDRALISKDEN).exists and b.already_pending(UnitTypeId.HYDRALISKDEN) == 0:
            if b.can_afford(UnitTypeId.HYDRALISKDEN) and b.townhalls.exists:
                try:
                    result = await b.build(UnitTypeId.HYDRALISKDEN, near=b.townhalls.first.position)
                    if result is not None:  # Only print if build actually succeeded
                        print(f"[GAS SINK] Building Hydralisk Den (100 gas)")
                        return
                except Exception:
                    pass

        # Morph to Hive if we have Lair (150 gas) - need Infestation Pit
        if b.structures(UnitTypeId.LAIR).ready.exists and not b.structures(UnitTypeId.HIVE).exists:
            if not b.structures(UnitTypeId.INFESTATIONPIT).exists and b.already_pending(UnitTypeId.INFESTATIONPIT) == 0:
                if b.can_afford(UnitTypeId.INFESTATIONPIT) and b.townhalls.exists:
                    try:
                        result = await b.build(UnitTypeId.INFESTATIONPIT, near=b.townhalls.first.position)
                        if result is not None:
                            print(f"[GAS SINK] Building Infestation Pit (100 gas)")
                            return
                    except Exception:
                        pass

        # Morph to Lair if we don't have one (100 gas)
        if not has_lair and b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            await self._morph_to_lair()
