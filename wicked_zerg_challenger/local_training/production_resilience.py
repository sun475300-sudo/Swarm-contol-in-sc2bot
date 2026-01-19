# -*- coding: utf-8 -*-
from typing import Any, Dict
import random

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    # Mock for testing
class UnitTypeId:
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        HATCHERY = "HATCHERY"
        OVERLORD = "OVERLORD"
        LARVA = "LARVA"
        ZERGLING = "ZERGLING"

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
        pass

        except Exception:
            pass
            pass
        pass

        except Exception:
            pass
            pass
        pass

        except Exception:
            pass
            pass
        pass

        except Exception:
            pass
            result = unit.train(unit_type)
    # train() may return bool or coroutine
    if hasattr(result, '__await__'):
        pass
    await result
    return True
    except Exception as e:
        current_iteration = getattr(self.bot, "iteration", 0)
    if current_iteration % 200 == 0:
        print(f"[WARNING] _safe_train error: {e}")
    return False

def __init__(self, bot: Any) -> None:
        pass
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

    # Shared build reservation map to block duplicate construction across
    # managers
    if not hasattr(self.bot, "build_reservations"):
        pass
    self.bot.build_reservations = {}

    # Wrap bot.build once to enforce reservation checks globally
    # Some harnesses (e.g., tests/FakeBot) may not define build; guard to
    # avoid AttributeError
    if hasattr(
            self.bot,
            "build") and not hasattr(
            self.bot,
            "_build_reservation_wrapped"):
    original_build = self.bot.build

    async def _build_with_reservation(structure_type, *args, **kwargs):
        reservations = getattr(self.bot, "build_reservations", {})
        now = getattr(self.bot, "time", 0.0)
    ts = reservations.get(structure_type)
    # Skip if recently reserved (another manager already issued the build)
    if ts is not None and now - ts < 45.0:
        pass
    return None
    reservations[structure_type] = now
    if structure_type == UnitTypeId.SPAWNINGPOOL:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    if self.bot.structures(
            UnitTypeId.SPAWNINGPOOL).exists or self.bot.already_pending(
            UnitTypeId.SPAWNINGPOOL) > 0:
        # throttle log to reduce spam
    if int(now) % 10 == 0:
        print(f"[POOL GUARD] Blocked duplicate Spawning Pool at {int(now)}s")
    return None
    except Exception:
        pass
    pass
    return await original_build(structure_type, *args, **kwargs)

    self.bot.build = _build_with_reservation  # type: ignore
    self.bot._build_reservation_wrapped = True

def _cleanup_build_reservations(self) -> None:
        """Drop stale reservations to avoid permanent blocks."""
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        reservations = getattr(self.bot, "build_reservations", {})
        now = getattr(self.bot, "time", 0.0)
    stale = [sid for sid, ts in reservations.items() if now - ts > 45.0]
    for sid in stale:
        pass
    reservations.pop(sid, None)
    except Exception:
        pass
    pass

    async def fix_production_bottleneck(self) -> None:
        """
        Fix production bottlenecks and boost early game build order.
        """
        b = self.bot
        self._cleanup_build_reservations()
        
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
        
        try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        # === EXTREME EMERGENCY: Minerals > 500 - Force all larvae to Zerglings
        # This is the last line of defense against "1,000+ minerals, 0 army"
        # death spiral
    if b.minerals > 500:
        pass
    larvae = b.units(UnitTypeId.LARVA)
    if larvae.exists:
        # Check Spawning Pool status more reliably
    spawning_pools_ready = b.structures(UnitTypeId.SPAWNINGPOOL).ready
    spawning_pools_any = b.structures(UnitTypeId.SPAWNINGPOOL)
    pending_pools = b.already_pending(UnitTypeId.SPAWNINGPOOL)

    # Check for duplicate pool builds - only if NO ready pools exist
    if not spawning_pools_ready.exists and pending_pools == 0 and b.minerals > 500:
        pass
    if b.townhalls.exists and b.can_afford(UnitTypeId.SPAWNINGPOOL):
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    main_base = b.townhalls.first
    await b.build(
        UnitTypeId.SPAWNINGPOOL,
        near=main_base.position.towards(b.game_info.map_center, 5),
    )
    print(f"[PRODUCTION_RESILIENCE] [{int(b.time)}s] EMERGENCY POOL BUILD [Frame:{b.iteration}] Minerals:{int(b.minerals)} Larvae:{len(list(larvae))} Supply:{b.supply_used}/{b.supply_cap}")
    except Exception as e:
        pass
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
        
        # Get current counts
        drones = b.units(UnitTypeId.DRONE) if hasattr(b, "units") else []
        drone_count = drones.amount if hasattr(drones, "amount") else len(list(drones))
        
        # Get balance state
        state = self.balancer.get_balance_state()
        target_drones = self.balancer.get_target_drone_count()
        
        # Log balance decision periodically
        if b.iteration % 100 == 0:
            print(f"[BALANCE] Mode: {state.mode.value}, Drone: {state.drone_ratio:.1%}, "
                  f"Army: {state.army_ratio:.1%}, Threat: {state.threat_level:.1%}, "
                  f"Economy: {state.economy_score:.1%}, Current: {drone_count}, Target: {target_drones}")
        
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
            
            # Decide: drone or army?
            # Consider strategy preference
            if self.strategy_manager and self.strategy_manager.should_prioritize_drones():
                # Strategy prefers drones, but still check balancer
                should_make_drone = self.balancer.should_make_drone() or (drone_count < target_drones)
            elif self.strategy_manager and self.strategy_manager.should_early_aggression():
                # Strategy prefers early army
                should_make_drone = False
            else:
                should_make_drone = self.balancer.should_make_drone()
            
            if should_make_drone and drone_count < target_drones:
                # Make drone
                if b.can_afford(UnitTypeId.DRONE):
                    if await self._safe_train(larva, UnitTypeId.DRONE):
                        drones_produced += 1
                        drone_count += 1
                        continue
            
            # Make army unit (Zergling)
            if b.can_afford(UnitTypeId.ZERGLING):
                if await self._safe_train(larva, UnitTypeId.ZERGLING):
                    army_produced += 1
        
        if drones_produced > 0 or army_produced > 0:
            if b.iteration % 50 == 0:
                print(f"[BALANCE] Produced {drones_produced} drones, {army_produced} army units "
                      f"(Total drones: {drone_count}, Target: {target_drones})")
    
    async def _emergency_zergling_production(self, larvae) -> None:
        """Fallback emergency zergling production (original logic)"""
        b = self.bot
        zergling_produced = 0
        larvae_list = list(larvae) if larvae.exists else []
        
        for larva in larvae_list:
            if not hasattr(larva, 'is_ready') or not larva.is_ready:
                continue
            
            if b.supply_left < 1:
                if b.can_afford(UnitTypeId.OVERLORD) and larvae_list:
                    if await self._safe_train(larvae_list[0], UnitTypeId.OVERLORD):
                        print(f"[EMERGENCY] Produced Overlord for supply")
                    break
            
            if b.can_afford(UnitTypeId.ZERGLING):
                if await self._safe_train(larva, UnitTypeId.ZERGLING):
                    zergling_produced += 1
                    break
        
        if zergling_produced > 0:
            print(f"[EMERGENCY] Produced {zergling_produced} Zerglings")

    # Gas extraction: Build at pro baseline supply (17-18)
    supply_used = getattr(b, "supply_used", 0)
    gas_supply = get_learned_parameter("gas_supply", 17.0)
    gas_supply_max = gas_supply + 1.0  # Allow up to 18 (17-18 range)
    
    try:
        # Priority 1: Build at target supply (17-18)
        if supply_used >= gas_supply and supply_used <= gas_supply_max:
            extractors = b.structures(UnitTypeId.EXTRACTOR) if hasattr(b, "structures") else []
            if not extractors.exists and b.already_pending(UnitTypeId.EXTRACTOR) == 0:
                geysers = b.vespene_geyser if hasattr(b, "vespene_geyser") else []
                if geysers:
                    target = geysers.first if hasattr(geysers, "first") else list(geysers)[0]
                    if b.can_afford(UnitTypeId.EXTRACTOR):
                        await b.build(UnitTypeId.EXTRACTOR, target)
                        if b.iteration % 50 == 0:
                            print(f"[TECH BUILD] [{int(b.time)}s] Building Gas Extractor at {supply_used} supply (pro baseline: {gas_supply})")
        # Priority 2: Emergency build if vespene is zero and no extractor
        elif getattr(b, "vespene", 0) <= 0:
            extractors = b.structures(UnitTypeId.EXTRACTOR) if hasattr(b, "structures") else []
            if not extractors.exists and b.already_pending(UnitTypeId.EXTRACTOR) == 0:
                geysers = b.vespene_geyser if hasattr(b, "vespene_geyser") else []
                if geysers:
                    target = geysers.first if hasattr(geysers, "first") else list(geysers)[0]
                    if b.can_afford(UnitTypeId.EXTRACTOR):
                        await b.build(UnitTypeId.EXTRACTOR, target)
    except Exception:
        pass

    # Spawning Pool: Use strategy-specific timing or learned parameter
    if self.strategy_manager:
        spawning_pool_supply = self.strategy_manager.get_pool_supply()
    else:
        spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 17.0)
    if (
        not b.units(UnitTypeId.SPAWNINGPOOL).exists
        and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0
    ):
        supply_used = getattr(b, "supply_used", 0)
        # Priority 1: Build at target supply (17)
        should_build_pool = supply_used >= spawning_pool_supply
        # Priority 2: Emergency build if too late (supply > 20)
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
                            print(f"[TECH BUILD] [{int(b.time)}s] Building Spawning Pool at {supply_used} supply (pro baseline: {spawning_pool_supply})")
                        return
                    except Exception as e:
                        if b.iteration % 100 == 0:
                            print(f"[TECH BUILD] [{int(b.time)}s] Failed to build Spawning Pool: {e}")
    # Natural Expansion: Use strategy-specific timing or learned parameter
    if self.strategy_manager:
        natural_expansion_supply = self.strategy_manager.get_expansion_supply()
        natural_expansion_supply_max = natural_expansion_supply + 2.0 if natural_expansion_supply > 0 else 0.0
    else:
        natural_expansion_supply = get_learned_parameter("natural_expansion_supply", 30.0)
        natural_expansion_supply_max = natural_expansion_supply + 2.0  # Allow up to 32 (30-32 range)
    
    larvae = b.units(UnitTypeId.LARVA)
    if not larvae.exists:
        pass
    
    townhalls = b.townhalls if hasattr(b, "townhalls") else []
    supply_used = getattr(b, "supply_used", 0)
    
    # Priority 1: Build at target supply (30-32)
    if supply_used >= natural_expansion_supply and supply_used <= natural_expansion_supply_max:
        if len(townhalls) < 2 and b.already_pending(UnitTypeId.HATCHERY) == 0:
            if b.can_afford(UnitTypeId.HATCHERY):
                if b.townhalls.exists:
                    try:
                        main_base = b.townhalls.first
                        macro_pos = main_base.position.towards(b.game_info.map_center, 8)
                        await b.build(UnitTypeId.HATCHERY, near=macro_pos)
                        if b.iteration % 50 == 0:
                            print(f"[TECH BUILD] [{int(b.time)}s] Building Natural Expansion at {supply_used} supply (pro baseline: {natural_expansion_supply})")
                        return
                    except Exception as e:
                        if b.iteration % 100 == 0:
                            print(f"[TECH BUILD] [{int(b.time)}s] Failed to build Natural Expansion: {e}")
    # Priority 2: Force expansion if too late (supply 40+) and still no expansion
    elif supply_used >= 40 and len(townhalls) < 2 and b.already_pending(UnitTypeId.HATCHERY) == 0:
        if b.can_afford(UnitTypeId.HATCHERY):
            if b.townhalls.exists:
                try:
                    main_base = b.townhalls.first
                    macro_pos = main_base.position.towards(b.game_info.map_center, 8)
                    await b.build(UnitTypeId.HATCHERY, near=macro_pos)
                    if b.iteration % 50 == 0:
                        print(f"[TECH BUILD] [{int(b.time)}s] FORCING Natural Expansion at {supply_used} supply (emergency)")
                    return
                except Exception:
                    pass
    if b.supply_left < 4 and b.supply_cap < 200:
        pass
    if b.can_afford(UnitTypeId.OVERLORD) and larvae.exists:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    larvae_list = list(larvae)
    if larvae_list:
        pass
    await self._safe_train(larvae_list[0], UnitTypeId.OVERLORD)
    except Exception:
        pass
    pass

    # ??? AGGRESSIVE OVERLORD PRODUCTION: When minerals > 1,000, produce 3-5 Overlords at once
    # This creates a supply buffer (12-20) for aggressive army production
    if b.minerals > 500 and b.supply_left < 20 and larvae.exists:
        pass
    overlords_to_produce = min(5, len(larvae) // 2)  # Produce 3-5 overlords
    overlords_produced = 0
    larvae_list = list(larvae)
    for larva in larvae_list:
        pass
    if not larva.is_ready:
        pass
    continue
    if overlords_produced >= overlords_to_produce:
        pass
    break
    if b.can_afford(UnitTypeId.OVERLORD):
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    if await self._safe_train(larva, UnitTypeId.OVERLORD):
        pass
    overlords_produced += 1
    except Exception:
        pass
    pass
    if overlords_produced > 0 and b.iteration % 50 == 0:
        print(
            f"[OVERLORD BULK PRODUCTION] [{int(b.time)}s] Produced {overlords_produced} Overlords (M:{int(b.minerals)} > 1,000)")

    spawning_pools = b.units(UnitTypeId.SPAWNINGPOOL).ready
    if spawning_pools.exists:
        pass
    larvae_list = list(larvae)
    produced_count = 0
    max_production = min(10, len(larvae_list))
    for i, larva in enumerate(larvae_list[:max_production]):
        pass
    if not larva.is_ready:
        pass
    continue
    if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    if await self._safe_train(larva, UnitTypeId.ZERGLING):
        pass
    produced_count += 1
    except Exception:
        pass
    continue
    if produced_count > 0 and b.iteration % 50 == 0:
        pass
    print(
        f"[PRODUCTION FIX] [{int(b.time)}s] Produced {produced_count} Zerglings (Minerals: {int(b.minerals)}M, Larva: {len(larvae_list)})"
    )
    roach_warrens = b.units(UnitTypeId.ROACHWARREN).ready
    if roach_warrens.exists:
        pass
    larvae_list = list(larvae)
    produced_count = 0
    max_production = min(5, len(larvae_list))
    for i, larva in enumerate(larvae_list[:max_production]):
        pass
    if not larva.is_ready:
        pass
    continue
    if b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    if await self._safe_train(larva, UnitTypeId.ROACH):
        pass
    produced_count += 1
    except Exception:
        pass
    continue
    hydra_dens = b.units(UnitTypeId.HYDRALISKDEN).ready
    if hydra_dens.exists:
        pass
    larvae_list = list(larvae)
    produced_count = 0
    max_production = min(5, len(larvae_list))
    for i, larva in enumerate(larvae_list[:max_production]):
        pass
    if not larva.is_ready:
        pass
    continue
    if b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    if await self._safe_train(larva, UnitTypeId.HYDRALISK):
        pass
    produced_count += 1
    except Exception:
        pass
    continue
    except Exception as e:
        pass
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
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        # IMPROVED: Only log at DEBUG level during training to reduce I/O overhead
        # Use logger if available, otherwise use print only for critical issues
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    use_logger = True
    except ImportError:
        pass
    use_logger = False
    logger = None

    # Check if we're in training mode (reduce logging frequency)
    is_training = getattr(b, 'train_mode', False)

    if iteration % 50 == 0:
        pass
    larvae = b.units(UnitTypeId.LARVA)
    larvae_count = larvae.amount if hasattr(
        larvae, "amount") else len(
        list(larvae))
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
        pass
    spawning_pool_ready = True
    elif spawning_pool_query.exists:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pool = spawning_pool_query.first
    if pool.build_progress >= 0.99:
        pass
    spawning_pool_ready = True
    except Exception:
        pass
    pass

    roach_warren_query = b.structures(UnitTypeId.ROACHWARREN)
    roach_warren_ready = False
    if roach_warren_query.ready.exists:
        pass
    roach_warren_ready = True
    elif roach_warren_query.exists:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    warren = roach_warren_query.first
    if warren.build_progress >= 0.99:
        pass
    roach_warren_ready = True
    except Exception:
        pass
    pass

    hydralisk_den_query = b.structures(UnitTypeId.HYDRALISKDEN)
    hydralisk_den_ready = False
    if hydralisk_den_query.ready.exists:
        pass
    hydralisk_den_ready = True
    elif hydralisk_den_query.exists:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    den = hydralisk_den_query.first
    if den.build_progress >= 0.99:
        pass
    hydralisk_den_ready = True
    except Exception:
        pass
    pass
    can_afford_zergling = b.can_afford(UnitTypeId.ZERGLING)
    can_afford_roach = b.can_afford(UnitTypeId.ROACH)
    can_afford_hydralisk = b.can_afford(UnitTypeId.HYDRALISK)

    # IMPROVED: Use DEBUG level for detailed logs during training
    # Only print critical issues at INFO level
    if is_training and use_logger and loguru_logger is not None:
        # Training mode: Use DEBUG level to reduce I/O overhead
        logger.debug(
            f"[PRODUCTION DIAGNOSIS] [{int(b.time)}s] Iteration: {iteration}")
        logger.debug(
            f"Resources: M:{int(b.minerals)} G:{int(b.vespene)} Supply:{b.supply_used}/{b.supply_cap}")
        logger.debug(
            f"Larva: {larvae_count} | Tech: Pool:{spawning_pool_ready} Warren:{roach_warren_ready} Den:{hydralisk_den_ready}")
        logger.debug(
            f"Units: Z:{zergling_count} R:{roach_count} H:{hydralisk_count} | Pending: Z:{pending_zerglings} R:{pending_roaches} H:{pending_hydralisks}")

    # Only log critical issues at INFO level
    if larvae_count == 0:
        logger.warning(f"[PRODUCTION] NO LARVAE - Production blocked!")
    elif larvae_count >= 3 and b.minerals > 500 and spawning_pool_ready and can_afford_zergling and b.supply_left >= 2:
        logger.warning(
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
        pass
    if iteration % 100 == 0:
        print(f"[WARNING] Production diagnosis error: {e}")

    async def build_army_aggressive(self) -> None:
    b = self.bot
    if not b.units(UnitTypeId.LARVA).exists:
        pass
    return
    larvae = b.units(UnitTypeId.LARVA).ready
    if b.supply_left < 5 and b.supply_cap < 200:
        pass
    if b.can_afford(
            UnitTypeId.OVERLORD) and not b.already_pending(
            UnitTypeId.OVERLORD):
    if larvae.exists:
        pass
    larvae_list = list(larvae)
    if larvae_list:
        pass
    for larva in larvae_list:
        pass
    if larva.is_ready:
        pass
    if await self._safe_train(larva, UnitTypeId.OVERLORD):
        pass
    return
    if hasattr(
        b,
            "current_build_plan") and "ideal_composition" in b.current_build_plan:
        ideal_comp = b.current_build_plan["ideal_composition"]
    else:
        pass
    ideal_comp = await self._determine_ideal_composition()
    if not hasattr(b, "current_build_plan"):
        pass
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
        pass
    if b.units(
            UnitTypeId.SPAWNINGPOOL).ready.exists and b.can_afford(
            UnitTypeId.ZERGLING):
    unit_to_produce = UnitTypeId.ZERGLING
    else:
        pass
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
        pass
    if max_deficit_unit == UnitTypeId.HYDRALISK:
        pass
    if b.units(UnitTypeId.HYDRALISKDEN).ready.exists and b.can_afford(
        UnitTypeId.HYDRALISK
    ):
    unit_to_produce = UnitTypeId.HYDRALISK
    elif max_deficit_unit == UnitTypeId.ROACH:
        pass
    if b.units(UnitTypeId.ROACHWARREN).ready.exists and b.can_afford(
        UnitTypeId.ROACH
    ):
    unit_to_produce = UnitTypeId.ROACH
    elif max_deficit_unit == UnitTypeId.RAVAGER:
        pass
    roaches_ready = b.units(UnitTypeId.ROACH).ready
    if roaches_ready.exists and b.can_afford(AbilityId.MORPHTORAVAGER_RAVAGER):
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    roaches_ready.random(AbilityId.MORPHTORAVAGER_RAVAGER)
    return
    except Exception:
        pass
    pass
    elif max_deficit_unit == UnitTypeId.BANELING:
        pass
    zerglings_ready = b.units(UnitTypeId.ZERGLING).ready
    if zerglings_ready.exists and b.units(
            UnitTypeId.BANELINGNEST).ready.exists:
    if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    zerglings_ready.random(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
    return
    except Exception:
        pass
    pass
    elif max_deficit_unit == UnitTypeId.ZERGLING:
        pass
    if b.units(UnitTypeId.SPAWNINGPOOL).ready.exists and b.can_afford(
        UnitTypeId.ZERGLING
    ):
    unit_to_produce = UnitTypeId.ZERGLING
    if not unit_to_produce:
        pass
    if b.units(UnitTypeId.SPAWNINGPOOL).ready.exists and b.can_afford(
        UnitTypeId.ZERGLING
    ):
    unit_to_produce = UnitTypeId.ZERGLING
    if unit_to_produce and larvae.exists and b.supply_left >= 2:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    larvae_list = list(larvae)
    if larvae_list:
        pass
    for larva in larvae_list:
        pass
    if larva.is_ready:
        pass
    if await self._safe_train(larva, unit_to_produce):
        pass
    break
    except Exception:
        pass
    pass

    async def force_resource_dump(self) -> None:
    b = self.bot
    if b.can_afford(
            UnitTypeId.HATCHERY) and b.already_pending(
            UnitTypeId.HATCHERY) < 2:
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    await b.expand_now()
    except Exception:
        pass
    pass
    if b.units(UnitTypeId.LARVA).exists:
        pass
    larvae = b.units(UnitTypeId.LARVA).ready
    if larvae.exists and b.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
        pass
    for larva in larvae:
        pass
    if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    await self._safe_train(larva, UnitTypeId.ZERGLING)
    except Exception:
        pass
    continue

    async def panic_mode_production(self) -> None:
    b = self.bot

    # ??? EMERGENCY DEFENSE: Build Spine Crawlers at 2:30+ if enemy detected
    # Prevents 3-minute defeat when bot has 0 army
    if b.time > 150 and b.already_pending(UnitTypeId.SPINECRAWLER) == 0:
        pass
    spine_crawlers = b.units(UnitTypeId.SPINECRAWLER)
    spine_count = spine_crawlers.amount if hasattr(
        spine_crawlers, 'amount') else len(
        list(spine_crawlers))

    # Check if enemy is nearby (scouting system should detect this)
    intel = getattr(b, "intel", None)
    enemy_near_base = False
    if intel and hasattr(intel, "enemy_units_near_base"):
        pass
    enemy_near_base = intel.enemy_units_near_base

    # Build 1-2 Spine Crawlers for defense if conditions met
    if (enemy_near_base or b.time > 180) and spine_count < 2 and b.can_afford(
            UnitTypeId.SPINECRAWLER):
    if b.townhalls.exists:
        pass
    try:
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    pass

    except Exception:
        pass
        pass
    main_base = b.townhalls.first
    # Place Spine Crawler in front of base (towards enemy)
    defense_pos = main_base.position.towards(b.game_info.map_center, 8)
    await b.build(UnitTypeId.SPINECRAWLER, near=defense_pos)
    if b.iteration % 50 == 0:
        print(
            f"[EMERGENCY DEFENSE] [{int(b.time)}s] Building Spine Crawler for defense")
    except Exception as e:
        pass
    if b.iteration % 100 == 0:
        print(f"[EMERGENCY DEFENSE] Failed to build Spine Crawler: {e}")

    if b.production:
        pass
    await b.production._produce_overlord()
    if b.production:
        pass
    await b.production._produce_queen()
    larvae = list(b.units(UnitTypeId.LARVA))
    if larvae and b.supply_left >= 2:
        pass
    if b.can_afford(UnitTypeId.ZERGLING):
        pass
    spawning_pools = b.units(UnitTypeId.SPAWNINGPOOL).ready
    if spawning_pools:
        pass
import random
    # CRITICAL FIX: Use _safe_train instead of direct train() call
    larva = random.choice(larvae)
    if larva.is_ready:
        pass
    await self._safe_train(larva, UnitTypeId.ZERGLING)

    async def build_terran_counters(self) -> None:
    b = self.bot
    if not b.production:
        pass
    return
    baneling_nests = [
        s for s in b.units(
            UnitTypeId.BANELINGNEST).structure if s.is_ready]
    if not baneling_nests and b.already_pending(
            UnitTypeId.BANELINGNEST) == 0 and b.can_afford(
            UnitTypeId.BANELINGNEST):
        # CRITICAL: Check for duplicate construction before building
    if not b.structures(UnitTypeId.BANELINGNEST).exists:
        pass
    spawning_pools = [
        s for s in b.units(
            UnitTypeId.SPAWNINGPOOL).structure if s.is_ready]
    if spawning_pools:
        pass
    await b.build(UnitTypeId.BANELINGNEST, near=spawning_pools[0])
    roach_warrens = [
        s for s in b.units(
            UnitTypeId.ROACHWARREN).structure if s.is_ready]
    if not roach_warrens and b.already_pending(
            UnitTypeId.ROACHWARREN) == 0 and b.time > 180 and b.can_afford(
            UnitTypeId.ROACHWARREN):
        # CRITICAL: Check for duplicate construction before building
    if not b.structures(UnitTypeId.ROACHWARREN).exists:
        pass
    if b.townhalls.exists:
        pass
    townhalls_list = list(b.townhalls)
    if townhalls_list:
        pass
    await b.build(UnitTypeId.ROACHWARREN, near=townhalls_list[0])
    else:
        pass
    await b.build(UnitTypeId.ROACHWARREN, near=b.game_info.map_center)

    async def build_protoss_counters(self) -> None:
    b = self.bot
    if not b.production:
        pass
    return
    hydra_dens = [
        s for s in b.units(
            UnitTypeId.HYDRALISKDEN).structure if s.is_ready]
    if not hydra_dens and b.already_pending(
            UnitTypeId.HYDRALISKDEN) == 0 and b.time > 240 and b.can_afford(
            UnitTypeId.HYDRALISKDEN):
    lairs = [s for s in b.units(UnitTypeId.LAIR).structure if s.is_ready]
    hives = [s for s in b.units(UnitTypeId.HIVE).structure if s.is_ready]
    if lairs or hives:
        pass
    if b.townhalls.exists:
        pass
    townhalls_list = list(b.townhalls)
    if townhalls_list:
        pass
    await b.build(UnitTypeId.HYDRALISKDEN, near=townhalls_list[0])
    else:
        pass
    await b.build(UnitTypeId.HYDRALISKDEN, near=b.game_info.map_center)
    roach_warrens = [
        s for s in b.units(
            UnitTypeId.ROACHWARREN).structure if s.is_ready]
    if not roach_warrens and b.already_pending(
            UnitTypeId.ROACHWARREN) == 0 and b.time > 180 and b.can_afford(
            UnitTypeId.ROACHWARREN):
    if b.townhalls.exists:
        pass
    townhalls_list = list(b.townhalls)
    if townhalls_list:
        pass
    await b.build(UnitTypeId.ROACHWARREN, near=townhalls_list[0])
    else:
        pass
    await b.build(UnitTypeId.ROACHWARREN, near=b.game_info.map_center)

    async def build_zerg_counters(self) -> None:
    b = self.bot
    if not b.production:
        pass
    return
    roach_warrens = [
        s for s in b.units(
            UnitTypeId.ROACHWARREN).structure if s.is_ready]
    if not roach_warrens and b.already_pending(
            UnitTypeId.ROACHWARREN) == 0 and b.time > 180 and b.can_afford(
            UnitTypeId.ROACHWARREN):
    if b.townhalls.exists:
        pass
    townhalls_list = list(b.townhalls)
    if townhalls_list:
        pass
    await b.build(UnitTypeId.ROACHWARREN, near=townhalls_list[0])
    else:
        pass
    await b.build(UnitTypeId.ROACHWARREN, near=b.game_info.map_center)
    baneling_nests = [
        s for s in b.units(
            UnitTypeId.BANELINGNEST).structure if s.is_ready]
    if not baneling_nests and b.already_pending(
            UnitTypeId.BANELINGNEST) == 0 and b.can_afford(
            UnitTypeId.BANELINGNEST):
    spawning_pools = [
        s for s in b.units(
            UnitTypeId.SPAWNINGPOOL).structure if s.is_ready]
    if spawning_pools:
        pass
    await b.build(UnitTypeId.BANELINGNEST, near=spawning_pools[0])
    hydra_dens = [
        s for s in b.units(
            UnitTypeId.HYDRALISKDEN).structure if s.is_ready]
    if not hydra_dens and b.already_pending(
            UnitTypeId.HYDRALISKDEN) == 0 and b.time > 300 and b.can_afford(
            UnitTypeId.HYDRALISKDEN):
    lairs = [s for s in b.units(UnitTypeId.LAIR).structure if s.is_ready]
    hives = [s for s in b.units(UnitTypeId.HIVE).structure if s.is_ready]
    if lairs or hives:
        pass
    if b.townhalls.exists:
        pass
    townhalls_list = list(b.townhalls)
    if townhalls_list:
        pass
    await b.build(UnitTypeId.HYDRALISKDEN, near=townhalls_list[0])
    else:
        pass
    await b.build(UnitTypeId.HYDRALISKDEN, near=b.game_info.map_center)

    async def _determine_ideal_composition(self) -> Dict[UnitTypeId, float]:
        """Reuses bot's composition logic via in-module call."""
        # Directly call the bot's method for now; can be refactored later
    return await self.bot._determine_ideal_composition()
