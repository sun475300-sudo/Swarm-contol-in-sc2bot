# -*- coding: utf-8 -*-

from typing import Dict, Optional

import traceback

from sc2.bot_ai import BotAI  # type: ignore
from sc2.ids.ability_id import AbilityId  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore
from sc2.ids.upgrade_id import UpgradeId  # type: ignore
from sc2.position import Point2  # type: ignore

from config import Config

class EconomyManager:
    def __init__(self, bot: BotAI):
        self.bot = bot
        self.config = Config()

        self.gas_workers_reduced = False
        self.speed_upgrade_done = False

        # Stuck unit detection tracking (unit_tag -> last_position -> last_time)
        self.unit_positions: Dict[int, Dict] = {}

        # Building construction flags to prevent infinite loops
        self.spawning_pool_building = (
            False  # Flag to prevent multiple simultaneous Spawning Pool builds
        )
        self.last_spawning_pool_check = 0  # Track last check time to prevent spam
        self.spawning_pool_started_time = 0  # Track when spawning pool build started

        # Shared build reservations to prevent duplicate construction across managers
        if not hasattr(self.bot, "build_reservations"):
            self.bot.build_reservations: Dict[UnitTypeId, float] = {}
        if not hasattr(self.bot, "_build_reservation_wrapped"):
            original_build = self.bot.build

            async def _build_with_reservation(structure_type, *args, **kwargs):
                try:
                    self._reserve_building(structure_type)
                    # Log tech building construction attempts for duplicate detection
                    tech_buildings = {
                        UnitTypeId.SPAWNINGPOOL,
                        UnitTypeId.ROACHWARREN,
                        UnitTypeId.HYDRALISKDEN,
                        UnitTypeId.BANELINGNEST,
                        UnitTypeId.SPIRE,
                        UnitTypeId.GREATERSPIRE,
                        UnitTypeId.INFESTATIONPIT,
                        UnitTypeId.LURKERDEN,
                        UnitTypeId.ULTRALISKCAVERN,
                    }
                    if structure_type in tech_buildings:
                        iteration = getattr(self.bot, "iteration", 0)
                        game_time = getattr(self.bot, "time", 0.0)
                        print(f"[BUILD-WRAPPER] [{int(game_time)}s iter:{iteration}] EconomyManager attempting {structure_type.name}")
                except Exception:
                    pass
                return await original_build(structure_type, *args, **kwargs)

            # Wrap BotAI.build so every build call auto-reserves the structure
            self.bot.build = _build_with_reservation  # type: ignore
            self.bot._build_reservation_wrapped = True

    def _ensure_build_reservations(self) -> Dict[UnitTypeId, float]:
        """Ensure shared reservation map exists and return it."""
        if not hasattr(self.bot, "build_reservations"):
            self.bot.build_reservations = {}
        return self.bot.build_reservations  # type: ignore

    def _cleanup_build_reservations(self) -> None:
        """Remove stale reservations (e.g., failed builds) using game time."""
        try:
            reservations = self._ensure_build_reservations()
            now = getattr(self.bot, "time", 0.0)
            stale_keys = [sid for sid, ts in reservations.items() if now - ts > 45.0]
            for sid in stale_keys:
                reservations.pop(sid, None)
        except Exception:
            pass

    def _reserve_building(self, structure_id: UnitTypeId) -> None:
        """Reserve a structure type to block duplicate build commands in the same window."""
        try:
            reservations = self._ensure_build_reservations()
            reservations[structure_id] = getattr(self.bot, "time", 0.0)
        except Exception:
            pass

    def _can_build_safely(
        self, structure_id: UnitTypeId, check_workers: bool = True, reserve_on_pass: bool = False
    ) -> bool:
        """
        중복 건설을 원천 차단하는 안전한 건설 체크 함수

        Args:
            structure_id: 건설할 건물 타입
            check_workers: 일벌레 명령 체크 여부 (기본값: True)

        Returns:
            bool: 안전하게 건설할 수 있으면 True
        """
        b = self.bot

        # Clear stale reservations and block if another manager reserved this build
        self._cleanup_build_reservations()
        reservations = getattr(b, "build_reservations", {})
        if reservations.get(structure_id) is not None:
            return False

        # Extra guard: if ProductionManager claims tech ownership, skip economy tech builds
        if getattr(b, "production_manager_owns_tech", False):
            # allow extractor/evo chamber which are more economic
            tech_ids = {
                UnitTypeId.SPAWNINGPOOL,
                UnitTypeId.ROACHWARREN,
                UnitTypeId.BANELINGNEST,
                UnitTypeId.HYDRALISKDEN,
                UnitTypeId.INFESTATIONPIT,
                UnitTypeId.SPIRE,
                UnitTypeId.LURKERDENMP,
                UnitTypeId.LURKERDEN,
                UnitTypeId.ULTRALISKCAVERN,
            }
            if structure_id in tech_ids:
                return False

        existing = b.structures(structure_id).amount
        if existing > 0:
            return False

        pending = b.already_pending(structure_id)
        if pending > 0:
            return False

        if check_workers:
            try:
                creation_ability = b.game_data.units[structure_id.value].creation_ability
                if creation_ability:
                    # Use direct workers access (cached_workers is a list, not UnitGroup)
                    workers = b.workers
                    for worker in workers:
                        if worker.orders:
                            for order in worker.orders:
                                if order.ability.id == creation_ability.id:
                                    return False
            except (AttributeError, KeyError, TypeError):
                pass

        if structure_id == UnitTypeId.EXTRACTOR:
            vespene_geysers = b.vespene_geyser
            for geyser in vespene_geysers:
                nearby_extractors = b.structures(UnitTypeId.EXTRACTOR).closer_than(1.0, geyser)
                if nearby_extractors:
                    return False

        if reserve_on_pass:
            self._reserve_building(structure_id)

        return True

    def _is_construction_started(self, unit_type: UnitTypeId) -> bool:
        """
        Check if a structure is already being constructed, including when a worker
        has an active order to build it (pre-pending state).

        Returns True if:
        - The structure already exists
        - Any worker has an order matching the structure's creation ability
        """
        b = self.bot
        try:
            # 1) Already exists
            if b.structures(unit_type).exists:
                return True

            # 2) Any worker moving to build (orders contain creation ability)
            creation_ability = b.game_data.units[unit_type.value].creation_ability
            if creation_ability:
                # Use direct workers access (cached_workers is a list, not UnitGroup)
                workers = b.workers
                for w in workers:
                    if w.orders:
                        for order in w.orders:
                            if order.ability.id == creation_ability.id:
                                return True
        except Exception:
            # Be safe: if any data path fails, assume not started
            pass

        return False

    async def _find_safe_building_placement(
        self, structure_id: UnitTypeId, near: Point2, placement_step: int = 7
    ) -> Optional[Point2]:
        """
        Safe building placement with spacing, spawn zone protection, and Dead Zone offset

        Prevents buildings from blocking unit spawn paths (south/east of hatcheries)
        Uses North-West offset to avoid spawn zones (Dead Zone strategy)
        Uses larger placement_step (6-7) to ensure adequate spacing between buildings

        Args:
            structure_id: Structure to build
            near: Center point for placement search (typically hatchery position)
            placement_step: Grid step size for placement (larger = more spacing, default 6)

        Returns:
            Optional[Point2]: Safe placement position, or None if not found
        """
        b = self.bot

        try:
            # Get all hatcheries to check spawn zones
            hatcheries = []
            try:
                intel = getattr(b, "intel", None)
                if intel and intel.cached_townhalls is not None:
                    hatcheries = (
                        list(intel.cached_townhalls) if intel.cached_townhalls.exists else []
                    )
                else:
                    hatcheries = list(b.townhalls)
            except Exception:
                pass

            # Strategy 1: Offset search origin to avoid spawn zone AND mineral lines
            # This creates a "Dead Zone" in the south/east direction and avoids mineral lines
            offset_near = near
            if hatcheries:
                # Find nearest hatchery
                nearest_hatch = min(hatcheries, key=lambda h: near.distance_to(h.position))
                hatch_pos = nearest_hatch.position

                # Primary: Offset towards map center (away from minerals and spawn zone)
                try:
                    if hasattr(b, "game_info") and hasattr(b.game_info, "map_center"):
                        map_center = b.game_info.map_center
                        # Offset 7 units towards map center (away from mineral lines)
                        offset_near = hatch_pos.towards(map_center, 7)
                    else:
                        # Fallback: North-West offset (away from spawn zone)
                        offset_near = hatch_pos.towards(
                            Point2((hatch_pos.x - 8, hatch_pos.y - 8)), 6
                        )
                except Exception:
                    # Fallback: North-West offset
                    offset_near = hatch_pos.towards(Point2((hatch_pos.x - 8, hatch_pos.y - 8)), 6)

            # Try multiple distances with increasing spacing (prefer larger spacing)
            for distance in range(6, 25, 2):
                try:
                    # Try with offset first (preferred)
                    placement = await b.find_placement(
                        structure_id,
                        offset_near,
                        max_distance=distance,
                        placement_step=placement_step,
                    )
                    if placement is None:
                        # Fallback to original near position
                        placement = await b.find_placement(
                            structure_id,
                            near,
                            max_distance=distance,
                            placement_step=placement_step,
                        )

                    if placement is None:
                        continue

                    # Check if placement is in spawn zone (south/east of any hatchery)
                    is_in_spawn_zone = False
                    for hatchery in hatcheries:
                        if hatchery is None:
                            continue
                        try:
                            hatchery_pos = hatchery.position
                            offset = placement - hatchery_pos
                            distance_to_hatch = placement.distance_to(hatchery_pos)

                            # Spawn zone: within 8 units, and in south/east quadrant (south-east direction)
                            # Increased from 7 to 8 for even better protection
                            if distance_to_hatch < 8.0:
                                # Check if in south-east quadrant (x > -0.5 and y > -0.5 for stricter check)
                                # In SC2, south is positive Y, east is positive X
                                if offset.x > -0.5 and offset.y > -0.5:  # South-east quadrant
                                    is_in_spawn_zone = True
                                    break
                        except Exception:
                            continue

                    # If not in spawn zone, this is a safe placement
                    if not is_in_spawn_zone:
                        return placement

                except Exception:
                    continue

            # Fallback: try without spawn zone check if all attempts failed
            try:
                placement = await b.find_placement(
                    structure_id, offset_near, placement_step=placement_step
                )
                if placement is None:
                    placement = await b.find_placement(
                        structure_id, near, placement_step=placement_step
                    )
                return placement
            except Exception:
                return None

        except Exception:
            # Final fallback: return None if all methods fail
            return None

    async def _unstuck_units(self):
        """
        Enhanced stuck unit detector with 5-second timeout and improved movement

        Detects units that haven't moved for 5 seconds and moves them to safe locations
        This prevents units from getting stuck between buildings (SimCity bottleneck)
        Critical for 26-minute long games where 30% of army stuck = defeat

        Improvements:
        - Reduced timeout from 10s to 5s for faster response
        - Better movement target (towards map center or nearest mineral)
        - Handles all combat units, not just idle ones
        """
        b = self.bot

        try:
            if not b.mineral_field.exists:
                return

            # All units that can get stuck (including workers)
            stuck_unit_types = [
                UnitTypeId.ULTRALISK,
                UnitTypeId.HYDRALISK,
                UnitTypeId.LURKER,
                UnitTypeId.ROACH,
                UnitTypeId.ZERGLING,
                UnitTypeId.DRONE,  # Workers can also get stuck
            ]

            current_time = b.time  # Game time in seconds
            stuck_timeout = 3.0  # Reduced to 3 seconds for faster response (was 5.0)
            moving_stuck_timeout = 1.5  # Reduced to 1.5 seconds for moving-stuck (was 2.0)

            # Get safe movement target (map center or nearest expansion)
            safe_target = None
            try:
                if hasattr(b, "game_info") and hasattr(b.game_info, "map_center"):
                    safe_target = b.game_info.map_center
                elif b.townhalls.exists:
                    safe_target = b.townhalls.first.position.towards(b.start_location, 15)
                else:
                    safe_target = b.start_location.position.towards(b.start_location, 15)
            except Exception:
                safe_target = None

            for unit_type in stuck_unit_types:
                try:
                    units = b.units(unit_type)
                    if not units.exists:
                        continue

                    for unit in units:
                        # Track both idle and moving units (moving units can also get stuck)
                        # Check if unit is alive using health attribute (more reliable than is_alive)
                        unit_health = getattr(unit, "health", 0)
                        if unit_health <= 0:
                            if unit.tag in self.unit_positions:
                                del self.unit_positions[unit.tag]
                            continue

                        unit_tag = unit.tag
                        current_pos = unit.position

                        # Check if unit has orders (thinks it's moving)
                        has_orders = unit.orders and len(unit.orders) > 0
                        is_moving = has_orders  # Simplified: if has orders, assume moving

                        # Check if we're tracking this unit
                        if unit_tag in self.unit_positions:
                            last_data = self.unit_positions[unit_tag]
                            last_pos = last_data["position"]
                            last_time = last_data["time"]
                            last_moving = last_data.get("moving", False)

                            # Check if unit hasn't moved (within 0.3 distance threshold, tighter check)
                            distance_moved = current_pos.distance_to(last_pos)
                            if (
                                distance_moved < 0.3
                            ):  # Reduced from 0.5 to 0.3 for more sensitive detection
                                # Unit hasn't moved, check if timeout reached
                                time_stuck = current_time - last_time

                                # Advanced: If unit thinks it's moving but isn't (stuck in gap between buildings)
                                if is_moving and not last_moving:
                                    # Just started moving, reset timer
                                    self.unit_positions[unit_tag] = {
                                        "position": current_pos,
                                        "time": current_time,
                                        "moving": is_moving,
                                    }
                                    continue
                                elif (
                                    is_moving and last_moving and time_stuck >= moving_stuck_timeout
                                ):
                                    # Unit has orders but hasn't moved for 2+ seconds (stuck in gap)
                                    try:
                                        # Immediate rescue: Stop and move to safe location
                                        move_target = None

                                        # Try nearest mineral first (good for workers and units)
                                        if b.mineral_field.exists:
                                            nearest_mineral = b.mineral_field.closest_to(unit)
                                            if nearest_mineral.distance_to(unit) > 3:
                                                move_target = nearest_mineral.position

                                        # Fallback: move towards map center or safe area
                                        if move_target is None and safe_target:
                                            move_target = safe_target
                                        elif move_target is None and b.townhalls.exists:
                                            # Move away from nearest hatchery (opposite direction)
                                            nearest_hatch = b.townhalls.closest_to(unit)
                                            move_target = unit.position.towards(
                                                nearest_hatch.position, -10
                                            )

                                        if move_target:
                                            unit.stop()  # Stop current orders immediately

                                            # Special handling for workers/drones: Use gather() for no-collision escape
                                            if (
                                                unit_type == UnitTypeId.DRONE
                                                and b.mineral_field.exists
                                            ):
                                                try:
                                                    nearest_mineral = b.mineral_field.closest_to(
                                                        unit
                                                    )
                                                    if nearest_mineral:
                                                        # Use gather() command for emergency mining (no-collision property)
                                                        unit.gather(nearest_mineral)
                                                        if (
                                                            getattr(b, "iteration", 0) % 100 == 0
                                                        ):  # Log occasionally
                                                            print(
                                                                f"[UNSTUCK] [{int(current_time)}s] Freed drone with gather() (moving-stuck {int(time_stuck)}s)"
                                                            )
                                                        # Reset tracking after moving
                                                        del self.unit_positions[unit_tag]
                                                        continue
                                                except Exception:
                                                    # Fallback to regular move if gather fails
                                                    pass

                                            # Regular move command for combat units
                                            unit.move(move_target)  # Move to safe location
                                            if (
                                                getattr(b, "iteration", 0) % 100 == 0
                                            ):  # Log occasionally
                                                print(
                                                    f"[UNSTUCK] [{int(current_time)}s] Freed moving-stuck {unit_type.name} (orders but no movement {int(time_stuck)}s)"
                                                )
                                            # Reset tracking after moving
                                            del self.unit_positions[unit_tag]

                                    except Exception:
                                        pass
                                elif time_stuck >= stuck_timeout:
                                    # Unit has been stuck for 5+ seconds (idle or no movement)
                                    try:
                                        # Find best escape direction
                                        move_target = None

                                        # Try nearest mineral first (good for workers and units)
                                        if b.mineral_field.exists:
                                            nearest_mineral = b.mineral_field.closest_to(unit)
                                            if nearest_mineral.distance_to(unit) > 3:
                                                move_target = nearest_mineral.position

                                        # Fallback: move towards map center or safe area
                                        if move_target is None and safe_target:
                                            move_target = safe_target
                                        elif move_target is None and b.townhalls.exists:
                                            # Move away from nearest hatchery
                                            nearest_hatch = b.townhalls.closest_to(unit)
                                            move_target = unit.position.towards(
                                                nearest_hatch.position, -10
                                            )

                                        if move_target:
                                            unit.stop()  # Stop current orders

                                            # Special handling for workers/drones: Use gather() for no-collision escape
                                            if (
                                                unit_type == UnitTypeId.DRONE
                                                and b.mineral_field.exists
                                            ):
                                                try:
                                                    nearest_mineral = b.mineral_field.closest_to(
                                                        unit
                                                    )
                                                    if nearest_mineral:
                                                        # Use gather() command for emergency mining (no-collision property)
                                                        unit.gather(nearest_mineral)
                                                        if (
                                                            getattr(b, "iteration", 0) % 100 == 0
                                                        ):  # Log occasionally
                                                            print(
                                                                f"[UNSTUCK] [{int(current_time)}s] Freed drone with gather() (stuck {int(time_stuck)}s)"
                                                            )
                                                        # Reset tracking after moving
                                                        del self.unit_positions[unit_tag]
                                                        continue
                                                except Exception:
                                                    # Fallback to regular move if gather fails
                                                    pass

                                            # Regular move command for combat units
                                            unit.move(move_target)  # Move to safe location
                                            if (
                                                getattr(b, "iteration", 0) % 100 == 0
                                            ):  # Log occasionally
                                                print(
                                                    f"[UNSTUCK] [{int(current_time)}s] Freed stuck {unit_type.name} (stuck {int(time_stuck)}s)"
                                                )
                                            # Reset tracking after moving
                                            del self.unit_positions[unit_tag]

                                    except Exception:
                                        pass
                            else:
                                # Unit has moved, update position
                                self.unit_positions[unit_tag] = {
                                    "position": current_pos,
                                    "time": current_time,
                                    "moving": is_moving,
                                }
                        else:
                            # Start tracking this unit
                            self.unit_positions[unit_tag] = {
                                "position": current_pos,
                                "time": current_time,
                                "moving": is_moving,
                            }
                except Exception:
                    continue

            # Clean up tracking for units that no longer exist
            try:
                existing_tags = {u.tag for u in b.units if u.tag in self.unit_positions}
                self.unit_positions = {
                    tag: data for tag, data in self.unit_positions.items() if tag in existing_tags
                }
            except Exception:
                pass

        except Exception:
            # Fail silently to avoid disrupting game flow
            pass

    async def _set_smart_rally_points(self):
        """
        Set smart rally points for hatcheries to prevent units from getting stuck

        Rally points are set towards map center or safe areas away from building clusters
        This ensures newly spawned units immediately move away from dense building areas
        """
        b = self.bot

        try:
            if not b.townhalls.exists:
                return

            # Get map center or safe rally target
            rally_target = None
            try:
                if hasattr(b, "game_info") and hasattr(b.game_info, "map_center"):
                    rally_target = b.game_info.map_center
                elif b.townhalls.exists:
                    # Use direction from start location towards map center
                    first_hatch = b.townhalls.first
                    if first_hatch and hasattr(b, "start_location"):
                        rally_target = first_hatch.position.towards(b.start_location, 15)
            except Exception:
                rally_target = None

            if rally_target is None:
                return

            # Set rally point for each hatchery
            intel = getattr(b, "intel", None)
            townhalls_ready = (
                intel.cached_townhalls.ready
                if intel and intel.cached_townhalls
                else b.townhalls.ready
            )
            for hatchery in townhalls_ready:
                try:
                    # Calculate rally point: away from hatchery towards safe area (10 units distance)
                    rally_point = hatchery.position.towards(rally_target, 10)

                    # Set rally point using RALLY_UNITS ability
                    hatchery(AbilityId.RALLY_UNITS, rally_point)

                except Exception:
                    # Skip if rally point setting fails
                    continue

        except Exception:
            # Fail silently to avoid disrupting game flow
            pass

    async def update(self):
        """
        매 프레임 호출되는 경제 관리 메인 루프 (성능 최적화)

        🛡️ 안전장치: townhalls가 없으면 즉시 리턴 (Melee Ladder 생존)

        🚀 성능 최적화: intel_manager의 캐시된 유닛 정보 사용
        - b.workers 대신 b.intel.cached_workers 사용 (중복 연산 방지)
        - b.townhalls 대신 b.intel.cached_townhalls 사용
        """
        b = self.bot

        intel = getattr(b, "intel", None)
        if intel and intel.cached_townhalls is not None:
            townhalls = intel.cached_townhalls
            if not townhalls.exists:
                return
        else:
            if not b.townhalls.exists:
                return
            townhalls = b.townhalls

        # NOTE: Removed emergency Spawning Pool auto-build.
        # Spawning Pool construction is handled by _execute_early_build_order()
        # and _maintain_spawning_pool() with proper safety checks.

        # Emergency unstuck logic (run every 25 frames for faster response, was 50)
        if getattr(b, "iteration", 0) % 25 == 0:
            await self._unstuck_units()

        # Smart rally point setup (run every 100 frames, about 5 seconds)
        if getattr(b, "iteration", 0) % 100 == 0:
            await self._set_smart_rally_points()

        townhalls = list(b.townhalls) if hasattr(self, "_need_townhalls_list") else None

        await self._execute_early_build_order()

        await self._distribute_workers()

        await self._autonomous_worker_behavior()

        await self._restrict_worker_combat_and_enforce_gathering()

        await self._manage_gas_workers()

        await self._maintain_spawning_pool()

        await self._build_early_spine_crawler()

        await self._inject_larva()

        await self._spread_creep()

        await self._manage_gas_buildings()

        await self._build_tech_buildings()

        await self._upgrade_tech()

        await self._manage_resource_expenditure()
        # This must be checked BEFORE any other upgrades or tech buildings
        await self._research_zergling_speed()

        await self._manage_expansion()

        await self._build_anti_air_structures()

        await self._research_upgrades()

    async def _execute_early_build_order(self):
        """
        Serral 스타일 초반 빌드 오더 (맵 크기 및 상대방 기록에 따라 조정)

        순서 (기본):
            1. 16 서플라이: 앞마당 (Natural Expansion)
            2. 18 서플라이: 가스 (Extractor)
            3. 17 서플라이: 산란못 (Spawning Pool)

        맵 크기별 조정:
            - SMALL: 12 Pool (빠른 공격)
            - MEDIUM: Standard Serral build
            - LARGE: 16 Hatch (경제 우선)

        상대방 기록 기반 조정:
            - 이전에 졌던 상대: 6-pool (복수 빌드)
        """
        b = self.bot

        townhalls = [th for th in b.townhalls]
        if not townhalls:
            return

        map_size = getattr(b, "map_size", "MEDIUM")

        use_aggressive_build = False
        try:
            opponent_tracker = getattr(b, "opponent_tracker", None)
            if opponent_tracker:
                current_opponent = getattr(opponent_tracker, "current_opponent", None)
                if current_opponent:
                    use_aggressive_build = opponent_tracker.should_use_aggressive_build(
                        current_opponent
                    )
                    if use_aggressive_build:
                        write_log = getattr(b, "write_log", None)
                        if write_log:
                            write_log(
                                f"Revenge build activated vs {current_opponent}: 6-pool",
                                "INFO",
                                filter_key="build_events",
                            )
        except Exception:
            pass

        from config import get_learned_parameter

        aggressive_build_supply = get_learned_parameter("aggressive_build_supply", 6)

        if use_aggressive_build and b.supply_used >= aggressive_build_supply:
            # CRITICAL: Prevent infinite loop - check if already building or exists
            spawning_pools_existing = list(
                b.units.filter(lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure)
            )
            pending_count = b.already_pending(UnitTypeId.SPAWNINGPOOL)
            current_iteration = getattr(b, "iteration", 0)

            # Reset flag if pool completed or build timed out (40 seconds)
            if spawning_pools_existing and self.spawning_pool_building:
                self.spawning_pool_building = False
                self.spawning_pool_started_time = 0
            elif self.spawning_pool_building and current_iteration - self.spawning_pool_started_time > 896:  # 40 sec timeout
                self.spawning_pool_building = False
                self.spawning_pool_started_time = 0

            # Only check every 10 frames to prevent spam (224 frames = 10 seconds)
            if current_iteration - self.last_spawning_pool_check < 10:
                return

            # Check if already exists, pending, or currently building
            if spawning_pools_existing or pending_count > 0 or self.spawning_pool_building:
                return  # Already building or exists, skip

            if self._can_build_safely(UnitTypeId.SPAWNINGPOOL, reserve_on_pass=True):
                if b.can_afford(UnitTypeId.SPAWNINGPOOL):
                    try:
                        if townhalls:
                            # Set flag BEFORE building to prevent duplicate attempts
                            self.spawning_pool_building = True
                            self.last_spawning_pool_check = current_iteration
                            self.spawning_pool_started_time = current_iteration

                            # CRITICAL: Check for duplicate construction before building
                            if self._can_build_safely(UnitTypeId.SPAWNINGPOOL, reserve_on_pass=True):
                                # Use safe placement with spacing to prevent SimCity bottleneck
                                build_pos = await self._find_safe_building_placement(
                                    UnitTypeId.SPAWNINGPOOL,
                                    townhalls[0].position,
                                    placement_step=5,
                                )
                                if build_pos:
                                    await b.build(UnitTypeId.SPAWNINGPOOL, build_pos)
                                else:
                                    await b.build(UnitTypeId.SPAWNINGPOOL, near=townhalls[0].position)

                            # Chat message only once per build attempt (disabled to reduce spam)
                            # Use PersonalityManager if needed
                            # if current_iteration % 224 == 0:
                            #     if hasattr(b, "personality_manager"):
                            #         from personality_manager import ChatPriority
                            #         await b.personality_manager.send_chat(
                            #             priority=ChatPriority.LOW
                            #         )

                            print(
                                f"[BUILD ORDER] [{int(b.time)}s] 6 Supply: Spawning Pool (REVENGE BUILD vs {current_opponent})"
                            )
                            write_log = getattr(b, "write_log", None)
                            if write_log:
                                write_log(
                                    f"6-pool revenge build started",
                                    "INFO",
                                    filter_key="build_events",
                                )
                            return  # Early pool built, skip standard build
                    except Exception:
                        # Reset flag on error
                        self.spawning_pool_building = False
                        pass

        small_map_pool_supply = get_learned_parameter("small_map_pool_supply", 12)

        if map_size == "SMALL" and b.supply_used >= small_map_pool_supply:
            # CRITICAL: Prevent infinite loop - check if already building or exists
            spawning_pools_existing = list(
                b.units.filter(lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure)
            )
            pending_count = b.already_pending(UnitTypeId.SPAWNINGPOOL)
            current_iteration = getattr(b, "iteration", 0)

            # Reset flag if pool completed or build timed out (40 seconds)
            if spawning_pools_existing and self.spawning_pool_building:
                self.spawning_pool_building = False
                self.spawning_pool_started_time = 0
            elif self.spawning_pool_building and current_iteration - self.spawning_pool_started_time > 896:  # 40 sec timeout
                self.spawning_pool_building = False
                self.spawning_pool_started_time = 0

            # Only check every 10 frames to prevent spam
            if current_iteration - self.last_spawning_pool_check < 10:
                return

            # Check if already exists, pending, or currently building
            if spawning_pools_existing or pending_count > 0 or self.spawning_pool_building:
                return  # Already building or exists, skip

            if self._can_build_safely(UnitTypeId.SPAWNINGPOOL, reserve_on_pass=True):
                if b.can_afford(UnitTypeId.SPAWNINGPOOL):
                    try:
                        if townhalls:
                            # Set flag BEFORE building to prevent duplicate attempts
                            self.spawning_pool_building = True
                            self.last_spawning_pool_check = current_iteration
                            self.spawning_pool_started_time = current_iteration

                            # CRITICAL: Check for duplicate construction before building
                            if self._can_build_safely(UnitTypeId.SPAWNINGPOOL, reserve_on_pass=True):
                                # Use safe placement with spacing to prevent SimCity bottleneck
                                build_pos = await self._find_safe_building_placement(
                                    UnitTypeId.SPAWNINGPOOL,
                                    townhalls[0].position,
                                    placement_step=5,
                                )
                                if build_pos:
                                    await b.build(UnitTypeId.SPAWNINGPOOL, build_pos)
                                else:
                                    await b.build(UnitTypeId.SPAWNINGPOOL, near=townhalls[0].position)

                            # Chat message disabled to reduce spam
                            # if current_iteration % 224 == 0:
                            #     if hasattr(b, "personality_manager"):
                            #         from personality_manager import ChatPriority
                            #         await b.personality_manager.send_chat(
                            #             priority=ChatPriority.LOW
                            #         )

                            print(
                                f"[BUILD ORDER] [{int(b.time)}s] 12 Supply: Spawning Pool (Small map aggressive build)"
                            )
                            return  # Early pool built, skip standard build
                    except Exception:
                        # Reset flag on error
                        self.spawning_pool_building = False
                        pass

        large_map_expansion_supply = get_learned_parameter("large_map_expansion_supply", 16)

        if (
            map_size == "LARGE"
            and b.supply_used >= large_map_expansion_supply
            and len(townhalls) < 2
        ):
            if b.already_pending(UnitTypeId.HATCHERY) == 0:
                if b.can_afford(UnitTypeId.HATCHERY):
                    try:
                        await b.expand_now()
                        print(
                            f"[BUILD ORDER] [{int(b.time)}s] 16 Supply: Natural Expansion (Large map economy build)"
                        )
                    except Exception:
                        pass

        medium_map_expansion_supply = get_learned_parameter("medium_map_expansion_supply", 16)

        if (
            map_size == "MEDIUM"
            and b.supply_used >= medium_map_expansion_supply
            and len(townhalls) < 2
        ):
            if b.already_pending(UnitTypeId.HATCHERY) == 0:
                if b.can_afford(UnitTypeId.HATCHERY):
                    try:
                        await b.expand_now()
                        print(
                            f"[BUILD ORDER] [{int(b.time)}s] 16 Supply: Natural Expansion (Serral Build)"
                        )
                    except Exception as e:
                        pass

        gas_extraction_supply = get_learned_parameter("gas_extraction_supply", 18)

        if b.supply_used >= gas_extraction_supply:
            if len(townhalls) >= 2 or b.already_pending(UnitTypeId.HATCHERY) > 0:
                spawning_pools = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure
                    )
                )
                extractors = list(
                    b.units.filter(lambda u: u.type_id == UnitTypeId.EXTRACTOR and u.is_structure)
                )

                # CRITICAL: Don't build extractor if workers are critically low (Priority Zero)
                # Use direct workers access (cached_workers is a list, not UnitGroup)
                worker_count = (
                    b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
                )
                if not spawning_pools and len(extractors) == 0:
                    if self._can_build_safely(UnitTypeId.EXTRACTOR, reserve_on_pass=True):
                        # Priority Zero: Don't build extractor if workers < 12 (prevent worker loss)
                        if worker_count >= 12 and b.can_afford(UnitTypeId.EXTRACTOR):
                            try:
                                if hasattr(b, "vespene_geyser"):
                                    vgs = [vg for vg in b.vespene_geyser]
                                else:
                                    try:
                                        map_vespene = getattr(b.game_info, "map_vespene", [])
                                        vgs = [vg for vg in map_vespene] if map_vespene else []
                                    except (AttributeError, TypeError):
                                        vgs = []

                                if vgs and townhalls:
                                    if len(townhalls) > 0:
                                        closest_vg = min(
                                            vgs,
                                            key=lambda vg: townhalls[0].distance_to(vg),
                                        )
                                        # Use direct workers access (cached_workers is a list, not UnitGroup)
                                        workers = [w for w in b.workers]
                                        if workers:
                                            closest_worker = min(
                                                workers,
                                                key=lambda w: w.distance_to(closest_vg),
                                            )
                                            closest_worker.build_gas(closest_vg)
                                            print(
                                                f"[BUILD ORDER] [{int(b.time)}s] 18 Supply: Gas (Serral Build)"
                                            )
                            except Exception as e:
                                pass

        spawning_pools_existing = list(b.structures(UnitTypeId.SPAWNINGPOOL))
        pending_count = b.already_pending(UnitTypeId.SPAWNINGPOOL)
        # Use direct workers access (cached_workers is a list, not UnitGroup)
        worker_count = (
            b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
        )
        current_iteration = getattr(b, "iteration", 0)

        # Reset flag if pool completed or build timed out (40 seconds)
        if spawning_pools_existing and self.spawning_pool_building:
            self.spawning_pool_building = False
            self.spawning_pool_started_time = 0
        elif self.spawning_pool_building and current_iteration - self.spawning_pool_started_time > 896:  # 40 sec timeout
            self.spawning_pool_building = False
            self.spawning_pool_started_time = 0

        # Only check every 10 frames to prevent spam
        if current_iteration - self.last_spawning_pool_check < 10:
            return

        # Check if already exists, pending, or currently building
        if spawning_pools_existing or pending_count > 0 or self.spawning_pool_building:
            return  # Already building or exists, skip

        fallback_pool_threshold = 12
        if b.supply_used >= fallback_pool_threshold:
            if b.can_afford(UnitTypeId.SPAWNINGPOOL) and worker_count >= 10:
                try:
                    hatchery = (
                        b.townhalls.ready.random if b.townhalls.ready.exists else (b.townhalls.first if b.townhalls.exists else None)
                    )
                    if hatchery:
                        self.spawning_pool_building = True
                        self.last_spawning_pool_check = current_iteration
                        self.spawning_pool_started_time = current_iteration

                        worker = None
                        try:
                            worker = b.select_build_worker(hatchery.position)
                        except Exception:
                            worker = None

                        # CRITICAL: Check for duplicate construction before building
                        if self._can_build_safely(UnitTypeId.SPAWNINGPOOL, reserve_on_pass=True):
                            build_pos = await self._find_safe_building_placement(
                                UnitTypeId.SPAWNINGPOOL,
                                hatchery.position,
                                placement_step=5,
                            )

                            if build_pos:
                                await b.build(UnitTypeId.SPAWNINGPOOL, build_pos)
                            else:
                                await b.build(UnitTypeId.SPAWNINGPOOL, near=hatchery)

                        print(f"[BUILD ORDER] [{int(b.time)}s] FALLBACK: Spawning Pool emergency build (Supply: {int(b.supply_used)})")
                        return  # Early exit after fallback build
                except Exception as e:
                    self.spawning_pool_building = False
                    print(f"[WARNING] Spawning Pool fallback build failed: {e}")
                    pass

        # Use learned parameter or config default for pool supply threshold
        from config import get_learned_parameter, Config
        pool_supply_threshold = get_learned_parameter("spawning_pool_supply", Config.SPAWNING_POOL_SUPPLY)

        if b.supply_used >= pool_supply_threshold:
            if self._can_build_safely(UnitTypeId.SPAWNINGPOOL, reserve_on_pass=True):
                # Priority Zero: Don't build spawning pool if workers are critically low
                min_workers = 10
                if worker_count >= min_workers and b.can_afford(UnitTypeId.SPAWNINGPOOL):
                    try:
                        hatchery = (
                            b.townhalls.ready.random if b.townhalls.ready.exists else (b.townhalls.first if b.townhalls.exists else None)
                        )
                        if hatchery:
                            # Set flag BEFORE building to prevent duplicate attempts
                            self.spawning_pool_building = True
                            self.last_spawning_pool_check = current_iteration
                            self.spawning_pool_started_time = current_iteration

                            # Prefer safe placement; if not found, build near hatchery
                            build_pos = await self._find_safe_building_placement(
                                UnitTypeId.SPAWNINGPOOL,
                                hatchery.position,
                                placement_step=5,
                            )

                            worker = None
                            try:
                                worker = b.select_build_worker(hatchery.position)
                            except Exception:
                                worker = None

                            if build_pos:
                                await b.build(UnitTypeId.SPAWNINGPOOL, build_pos)
                            else:
                                await b.build(UnitTypeId.SPAWNINGPOOL, near=hatchery)

                            # Chat message disabled to reduce spam
                            # if current_iteration % 224 == 0:
                            #     if hasattr(b, "personality_manager"):
                            #         from personality_manager import ChatPriority
                            #         await b.personality_manager.send_chat(
                            #             priority=ChatPriority.LOW
                            #         )

                            print(
                                f"[BUILD ORDER] [{int(b.time)}s] Spawning Pool started at supply {int(b.supply_used)}"
                            )
                    except Exception:
                        # Reset flag on error
                        self.spawning_pool_building = False
                        pass

    async def _spread_creep(self):
        """
        점막 확산: 여왕들이 에너지가 남으면 기지 주변에 점막 종양(Creep Tumor)을 깔도록

        Serral 스타일: 점막 확산으로 이동 속도 향상 및 시야 확보
        """
        b = self.bot

        intel = getattr(b, "intel", None)
        if intel and intel.cached_queens is not None:
            queens = intel.cached_queens
        else:
            queens = b.units(UnitTypeId.QUEEN).ready
        if not queens.exists:
            return

        if intel and intel.cached_townhalls is not None:
            townhalls = intel.cached_townhalls.ready
        else:
            townhalls = b.townhalls.ready
        if not townhalls:
            return

        existing_tumors = list(
            b.units.filter(lambda u: u.type_id == UnitTypeId.CREEPTUMOR and u.is_ready)
        )

        for queen in queens:
            if queen.energy < 25:
                continue

            ready_townhalls = [th for th in townhalls if th.is_ready]
            can_inject = False
            for th in ready_townhalls:
                if queen.distance_to(th) < 5:
                    can_inject = True
                    break

            # Enhanced creep spread for ladder play - more aggressive spreading
            if not can_inject and queen.energy >= 25:
                closest_hatch = min(townhalls, key=lambda th: queen.distance_to(th))

                # Enhanced: Check for tumors further away (increased from 10 to 15)
                # This allows more spread coverage
                nearby_tumors = [t for t in existing_tumors if t.distance_to(closest_hatch) < 15]
                if nearby_tumors:
                    # If tumors exist but far from map center, spread towards center
                    if b.time > 180:  # After 3 minutes, spread more aggressively
                        try:
                            map_center = b.game_info.map_center
                            # Find direction towards map center
                            spread_pos = closest_hatch.position.towards(map_center, 12)
                            queen(AbilityId.BUILD_CREEPTUMOR, spread_pos)
                            if getattr(b, "iteration", 0) % 100 == 0:
                                print(
                                    f"[CREEP] [{int(b.time)}s] Aggressive creep spread towards center"
                                )
                        except:
                            pass
                    continue

                try:
                    map_center = b.game_info.map_center
                    spread_pos = closest_hatch.position.towards(
                        map_center, 10
                    )  # Increased from 8 to 10

                    queen(AbilityId.BUILD_CREEPTUMOR, spread_pos)
                    if getattr(b, "iteration", 0) % 100 == 0:
                        print(f"[CREEP] [{int(b.time)}s] Creep tumor spread")
                except:
                    pass

            # Enhanced: Existing tumors should also spread (if energy available)
            if queen.energy >= 50 and b.time > 240:  # After 4 minutes, use tumors to spread
                # Find nearby tumors that can spread
                nearby_tumors = [t for t in existing_tumors if t.distance_to(queen) < 15]
                for tumor in nearby_tumors:
                    if tumor.is_ready:
                        # Check if tumor can spread (no nearby tumors)
                        tumor_nearby = [
                            t
                            for t in existing_tumors
                            if t.distance_to(tumor) < 8 and t.tag != tumor.tag
                        ]
                        if not tumor_nearby:
                            try:
                                # Spread tumor towards map center
                                map_center = b.game_info.map_center
                                spread_pos = tumor.position.towards(map_center, 10)
                                tumor(AbilityId.BUILD_CREEPTUMOR_TUMOR, spread_pos)
                                if getattr(b, "iteration", 0) % 100 == 0:
                                    print(f"[CREEP] [{int(b.time)}s] Tumor spreading")
                            except:
                                pass
                            break  # One spread per queen per cycle

    async def _distribute_workers(self):
        """
        일꾼을 미네랄/가스에 최적 배분

        sc2 내장 함수 distribute_workers()를 사용하되,
        가스 건물 완공 직후 일꾼 3명을 수동 지정하는 로직 추가

        🛡️ 안전장치: townhalls나 workers가 없으면 조용히 리턴
        🚀 성능 최적화: IntelManager 캐시 사용
        """
        b = self.bot

        try:
            if not b.townhalls.exists or not b.workers.exists:
                return
        except Exception:
            return
        townhalls = b.townhalls
        workers = b.workers

        try:
            await b.distribute_workers()
        except Exception as e:
            if getattr(b, "iteration", 0) % 100 == 0:
                print(f"[WARNING] distribute_workers() 오류: {e}")

        try:
            # OPTIMIZED: Use structures() instead of filter() for better performance
            extractors = b.structures(UnitTypeId.EXTRACTOR).ready
            # OPTIMIZED: Process only first 5 extractors (no need to iterate all)
            for extractor in list(extractors)[:5]:
                    if extractor.assigned_harvesters < self.config.WORKERS_PER_GAS:
                        # Use direct workers access (cached_workers is a list, not UnitGroup)
                        nearby_workers = b.workers.closer_than(25, extractor.position)
                        if nearby_workers.exists:
                            idle_workers = nearby_workers.idle
                            if idle_workers.exists:
                                worker = idle_workers.first
                            else:
                                worker = nearby_workers.closest_to(extractor.position)

                            if worker:
                                try:
                                    await b.do(worker.gather(extractor))
                                    if b.iteration % 100 == 0:
                                        print(f"[WORKER] Assigned worker to gas extractor (assigned: {extractor.assigned_harvesters}/{self.config.WORKERS_PER_GAS})")
                                except Exception as e:
                                    if b.iteration % 100 == 0:
                                        print(f"[WARNING] Failed to assign worker to gas: {e}")
                                    pass
        except Exception:
            pass

    # 1-1️⃣ Intelligent worker management: Context-aware worker behavior (Priority)
    def _calculate_location_value(self, position: Point2) -> float:
        """
        위치 가치 평가: 일꾼이 스스로 "이 위치가 내가 있어야 할 곳인가?"를 판단

        Args:
            position: 평가할 위치

        Returns:
            float: 위치의 가치 점수 (-100.0 ~ +100.0)
        """
        b = self.bot

        value = 0.0

        if b.townhalls.exists:
            closest_base = b.townhalls.closest_to(position)
            distance_to_base = position.distance_to(closest_base.position)

            if distance_to_base < 15:
                value += 100.0
            elif distance_to_base < 30:
                value += 50.0
            else:
                value -= 20.0

        if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
            enemy_base = b.enemy_start_locations[0]
            distance_to_enemy = position.distance_to(enemy_base)

            if distance_to_enemy < 80:
                value -= 100.0
            elif distance_to_enemy < 100:
                value -= 50.0

        if b.mineral_field.exists:
            closest_mineral = b.mineral_field.closest_to(position)
            if position.distance_to(closest_mineral.position) < 5:
                value += 30.0

        return value

    async def _intelligent_worker_dispatch(self):
        """
        지능형 일꾼 배치: 가치 기반 의사결정 시스템

        Workers autonomously seek the most valuable locations based on context.
        Intelligent worker management system with autonomous decision-making.

        🚀 성능 최적화: IntelManager 캐시 사용
        """
        b = self.bot

        try:
            if not b.townhalls.exists or not b.workers.exists:
                return
        except Exception:
            return
        townhalls = b.townhalls
        workers = b.workers

        try:
            enemy_base = None
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                enemy_base = b.enemy_start_locations[0]

            if not enemy_base:
                return

            main_base = (
                townhalls.first
                if hasattr(townhalls, "first")
                else (list(townhalls)[0] if townhalls.exists else None)
            )
            if not main_base:
                return

            for drone in workers:
                try:
                    is_constructing = False
                    if hasattr(drone, "orders") and drone.orders:
                        for order in drone.orders:
                            if hasattr(order, "ability") and order.ability:
                                ability_name = str(order.ability).upper()
                                if "BUILD" in ability_name or "CONSTRUCT" in ability_name:
                                    is_constructing = True
                                    break

                    if is_constructing:
                        continue

                    current_location_value = self._calculate_location_value(drone.position)

                    target_location = None
                    if b.mineral_field.exists:
                        target_location = b.mineral_field.closest_to(main_base.position).position

                    if target_location:
                        target_location_value = self._calculate_location_value(target_location)

                        if current_location_value < target_location_value:
                            minerals_near_base = b.mineral_field.closer_than(15, main_base.position)
                            if minerals_near_base.exists:
                                drone.gather(minerals_near_base.random)
                            else:
                                drone.move(main_base.position)

                    is_gathering = (
                        drone.is_gathering
                        or drone.is_carrying_minerals
                        or drone.is_carrying_vespene
                    )
                    if not is_gathering:
                        minerals_near_base = b.mineral_field.closer_than(15, main_base.position)
                        if minerals_near_base.exists:
                            drone.gather(minerals_near_base.random)
                        else:
                            drone.move(main_base.position)

                except Exception:
                    continue

        except Exception:
            pass

    async def _restrict_worker_combat_and_enforce_gathering(self):
        """
        자율적 일꾼 행동 관리: 봇이 스스로 일꾼의 최적 행동을 판단

        Value-based system where workers autonomously recognize that resource gathering is the most valuable action.

        🚀 성능 최적화: IntelManager 캐시 사용
        """
        await self._intelligent_worker_dispatch()
        b = self.bot

        try:
            if not b.townhalls.exists or not b.workers.exists:
                return
        except Exception:
            return
        townhalls = b.townhalls
        workers = b.workers

        try:
            enemy_base = None
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                enemy_base = b.enemy_start_locations[0]

            if not enemy_base:
                return

            main_base = (
                townhalls.first
                if hasattr(townhalls, "first")
                else (list(townhalls)[0] if townhalls.exists else None)
            )
            if not main_base:
                return

            for drone in workers:
                try:
                    is_constructing = False
                    if hasattr(drone, "orders") and drone.orders:
                        for order in drone.orders:
                            if hasattr(order, "ability") and order.ability:
                                ability_name = str(order.ability).upper()
                                if "BUILD" in ability_name or "CONSTRUCT" in ability_name:
                                    is_constructing = True
                                    break

                    if is_constructing:
                        continue

                    is_attacking = False
                    if hasattr(drone, "orders") and drone.orders:
                        for order in drone.orders:
                            if hasattr(order, "ability") and order.ability:
                                ability_name = str(order.ability).upper()
                                if "ATTACK" in ability_name:
                                    is_attacking = True
                                    break

                    # CRITICAL: If worker is attacking, immediately return to gathering
                    if is_attacking or drone.is_attacking:
                        # Workers should gather resources, not fight
                        if b.mineral_field.exists:
                            closest_mineral = b.mineral_field.closest_to(drone.position)
                            if closest_mineral:
                                try:
                                    await b.do(drone.gather(closest_mineral))
                                except Exception:
                                    pass
                        continue  # Skip rest of logic for this worker

                    distance_to_enemy = drone.distance_to(enemy_base)
                    is_near_enemy_base = distance_to_enemy < 80.0

                    is_gathering = (
                        drone.is_gathering
                        or drone.is_carrying_minerals
                        or drone.is_carrying_vespene
                    )

                    distance_to_base = drone.distance_to(main_base.position)
                    is_far_from_base = distance_to_base > 30.0

                    # 5. Intelligent threat assessment: Evaluate danger level before recalling workers
                    # Assess threat based on enemy units nearby and worker's current task importance
                    threat_level = 0.0
                    if is_attacking:
                        threat_level += 100.0  # Under attack - high priority recall
                    if is_near_enemy_base:
                        # Check if enemy units are nearby to assess actual threat
                        try:
                            known_enemy_units = getattr(b, "known_enemy_units", None)
                            if known_enemy_units and hasattr(known_enemy_units, "closer_than"):
                                enemy_units_nearby = known_enemy_units.closer_than(
                                    15, drone.position
                                )
                                if (
                                    enemy_units_nearby
                                    and hasattr(enemy_units_nearby, "exists")
                                    and enemy_units_nearby.exists
                                ):
                                    threat_level += 80.0  # Enemy units nearby - high threat
                                else:
                                    threat_level += 30.0  # Near enemy base but no immediate threat
                            else:
                                threat_level += 30.0  # Near enemy base but cannot assess threat
                        except (AttributeError, TypeError):
                            threat_level += 30.0  # Near enemy base but cannot assess threat
                    if is_far_from_base:
                        threat_level += 20.0  # Distance penalty

                    # Only recall if threat level exceeds threshold (context-aware decision)
                    if threat_level >= 50.0:
                        minerals_near_base = b.mineral_field.closer_than(15, main_base.position)
                        if minerals_near_base.exists:
                            drone.gather(minerals_near_base.random)
                        else:
                            drone.move(main_base.position)
                        continue

                    # 6. Intelligent resource gathering: Assess if worker should gather based on context
                    # Check if worker has a more important task or if gathering is optimal
                    should_gather = True

                    # If worker is idle and no important task, gathering is optimal
                    if not is_gathering:
                        # Check if there are available mineral fields nearby
                        minerals_near_base = b.mineral_field.closer_than(15, main_base.position)
                        if minerals_near_base.exists:
                            # Check if we need more workers gathering (economic assessment)
                            # Use direct workers access (cached_workers is a list, not UnitGroup)
                            gathering_workers = sum(
                                1 for w in b.workers if w.is_gathering or w.is_carrying_minerals
                            )
                            total_workers = (
                                b.workers.amount
                                if hasattr(b.workers, "amount")
                                else len(list(b.workers))
                            )

                            # If we have enough workers gathering relative to mineral fields, allow some flexibility
                            mineral_fields_count = (
                                minerals_near_base.amount
                                if hasattr(minerals_near_base, "amount")
                                else len(list(minerals_near_base))
                            )
                            optimal_gathering_ratio = (
                                mineral_fields_count * 2
                            )  # 2 workers per mineral patch

                            if gathering_workers >= optimal_gathering_ratio * 0.9:
                                # We have enough workers gathering, allow some flexibility
                                should_gather = False

                    if not is_gathering and should_gather:
                        minerals_near_base = b.mineral_field.closer_than(15, main_base.position)
                        if minerals_near_base.exists:
                            drone.gather(minerals_near_base.random)
                        else:
                            drone.move(main_base.position)

                except Exception:
                    continue

        except Exception:
            pass

    async def _autonomous_worker_behavior(self):
        """
        Autonomous worker behavior: Workers autonomously return to resources when idle

        Instills autonomous 'instinct' so workers naturally understand "my home is the main base resource area"
        and return there autonomously based on their own decision-making.

        핵심 원칙:
        1. 할 일이 없는(Idle) 일꾼은 스스로 가장 가까운 미네랄을 찾아감
        2. 본진에서 너무 멀어지면 스스로 본진 자원 지대로 복귀
        3. 가스 추출장에 일꾼이 부족하면 미네랄에서 데려오고, 넘치면 다시 미네랄로 보내는 '자동 균형'

        🚀 성능 최적화: IntelManager 캐시 사용
        """
        b = self.bot

        try:
            if not b.townhalls.exists or not b.workers.exists:
                return
        except Exception:
            return
        townhalls = b.townhalls
        workers = b.workers

        try:
            main_base = (
                townhalls.first
                if hasattr(townhalls, "first")
                else (list(townhalls)[0] if townhalls.exists else None)
            )
            if not main_base:
                return

            idle_workers = [w for w in workers if w.is_idle]
            current_iteration = getattr(b, "iteration", 0)
            idle_count = len(idle_workers)

            if idle_count > 0:
                if current_iteration % 112 == 0:
                    print(f"[WORKER] {idle_count} idle workers detected, assigning to resources...")

            for drone in idle_workers:
                try:
                    is_constructing = False
                    if hasattr(drone, "orders") and drone.orders:
                        for order in drone.orders:
                            if hasattr(order, "ability") and order.ability:
                                ability_name = str(order.ability).upper()
                                if "BUILD" in ability_name or "CONSTRUCT" in ability_name:
                                    is_constructing = True
                                    break

                    if is_constructing:
                        continue

                    extractors = b.structures(UnitTypeId.EXTRACTOR).ready
                    if extractors.exists:
                        for extractor in extractors:
                            if extractor.assigned_harvesters < self.config.WORKERS_PER_GAS:
                                try:
                                    await b.do(drone.gather(extractor))
                                    break
                                except Exception:
                                    pass
                        else:
                            if b.mineral_field.exists:
                                closest_mineral = b.mineral_field.closest_to(drone.position)
                                if closest_mineral:
                                    try:
                                        await b.do(drone.gather(closest_mineral))
                                    except Exception:
                                        pass
                    else:
                        if b.mineral_field.exists:
                            closest_mineral = b.mineral_field.closest_to(drone.position)
                            if closest_mineral:
                                try:
                                    await b.do(drone.gather(closest_mineral))
                                except Exception:
                                    pass
                except Exception:
                    continue

            for drone in workers:
                try:
                    is_constructing = False
                    if hasattr(drone, "orders") and drone.orders:
                        for order in drone.orders:
                            if hasattr(order, "ability") and order.ability:
                                ability_name = str(order.ability).upper()
                                if "BUILD" in ability_name or "CONSTRUCT" in ability_name:
                                    is_constructing = True
                                    break

                    if is_constructing:
                        continue

                    distance_to_base = drone.distance_to(main_base.position)
                    if distance_to_base > 30.0:
                        if not (
                            drone.is_gathering
                            or drone.is_carrying_minerals
                            or drone.is_carrying_vespene
                        ):
                            if current_iteration % 224 == 0:
                                personality = "NEUTRAL"
                                try:
                                    combat_manager = getattr(b, "combat", None)
                                    if combat_manager:
                                        personality = getattr(
                                            combat_manager, "personality", "NEUTRAL"
                                        )
                                except (AttributeError, TypeError):
                                    pass
                                if personality == "CAUTIOUS":
                                    await b.chat_send(
                                        "🛡️ [신중함] 위험 구역에서 일꾼을 철수시켰습니다. 안전이 제일이니까요."
                                    )
                                else:
                                    await b.chat_send(
                                        "🏠 너무 멀리 나왔군요. 안전한 본진 자원 지대로 복귀하겠습니다."
                                    )
                            if b.mineral_field.exists:
                                minerals_near_base = b.mineral_field.closer_than(
                                    15, main_base.position
                                )
                                if minerals_near_base.exists:
                                    drone.gather(minerals_near_base.random)
                                else:
                                    drone.move(main_base.position)
                except Exception:
                    continue

            if b.structures(UnitTypeId.EXTRACTOR).exists:
                for extractor in b.structures(UnitTypeId.EXTRACTOR).ready:
                    try:
                        # Use direct workers access (cached_workers is a list, not UnitGroup)
                        workers_on_gas = [
                            w
                            for w in b.workers
                            if hasattr(w, "order_target") and w.order_target == extractor.tag
                        ]
                        mineral_workers = [
                            w for w in b.workers if w.is_gathering and w.is_carrying_minerals
                        ]
                        worker_count_on_gas = len(workers_on_gas)

                        if worker_count_on_gas < 3:
                            if mineral_workers:
                                closest_mineral_worker = min(
                                    mineral_workers,
                                    key=lambda w: w.distance_to(extractor),
                                )
                                closest_mineral_worker.gather(extractor)

                        elif worker_count_on_gas > 3:
                            excess_workers = workers_on_gas[3:]
                            for worker in excess_workers:
                                if b.mineral_field.exists:
                                    closest_mineral = b.mineral_field.closest_to(main_base.position)
                                    if closest_mineral:
                                        worker.gather(closest_mineral)
                    except Exception:
                        continue

        except Exception:
            pass

    async def _manage_gas_workers(self):
        """
        가스 조절 - 발업 완료 후 일시적으로 가스 일꾼을 미네랄로 전환

        💡 효과:
            초반 저글링 물량 확보를 위해 가스 대신 미네랄 채취 집중
            테크 속도를 20~30초 앞당길 수 있음
        """
        b = self.bot

        if b.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) == 0:
            if UpgradeId.ZERGLINGMOVEMENTSPEED in b.state.upgrades:
                if not self.speed_upgrade_done:
                    self.speed_upgrade_done = True
                    print(f"[UPGRADE] [{int(b.time)}초] 발업 완료! 가스 일꾼 조절 시작")

        if self.speed_upgrade_done and b.time < 180:
            if not self.gas_workers_reduced:
                ready_extractors = list(b.structures(UnitTypeId.EXTRACTOR).ready)
                intel = getattr(b, "intel", None)
                # Use direct access (cached_workers and cached_townhalls are lists, not UnitGroups)
                workers = b.workers
                townhalls_list = [th for th in b.townhalls]

                for extractor in ready_extractors:
                    workers_on_gas = [
                        w
                        for w in workers
                        if hasattr(w, "order_target") and w.order_target == extractor.tag
                    ]
                    for i, worker in enumerate(workers_on_gas):
                        if i >= 1:
                            if townhalls_list:
                                minerals = [
                                    m
                                    for m in b.mineral_field
                                    if m.distance_to(townhalls_list[0]) < 10
                                ]
                                if minerals:
                                    closest_mineral = min(
                                        minerals, key=lambda m: worker.distance_to(m)
                                    )
                                    worker.gather(closest_mineral)

                self.gas_workers_reduced = True
                print(f"[GAS] [{int(b.time)}초] 가스 일꾼 미네랄로 전환")

        if b.time >= 180 and self.gas_workers_reduced:
            self.gas_workers_reduced = False
            print(f"[GAS] [{int(b.time)}초] 가스 일꾼 복구")

    async def _maintain_spawning_pool(self):
        """
        산란못 유지 및 재건설

        💡 회복력(Resilience) 로직:
            not structures(): 건물이 없는지 확인
            already_pending() == 0: 짓고 있는 중도 아닌지 확인
            → 두 조건 만족 시 즉시 재건설
        """
        b = self.bot

        try:
            # CRITICAL: Don't build spawning pool if workers are critically low (Priority Zero)
            # CRITICAL: Prevent infinite loop - check if already building or exists
            spawning_pools_existing = list(b.structures(UnitTypeId.SPAWNINGPOOL))
            pending_count = b.already_pending(UnitTypeId.SPAWNINGPOOL)
            intel = getattr(b, "intel", None)
            # Use direct workers access (cached_workers is a list, not UnitGroup)
            worker_count = (
                b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
            )
            current_iteration = getattr(b, "iteration", 0)

            # Only check every 10 frames to prevent spam
            if current_iteration - self.last_spawning_pool_check < 10:
                return

            # Check if already exists, pending, or currently building
            if spawning_pools_existing or pending_count > 0 or self.spawning_pool_building:
                # Reset flag if building is complete (structure exists)
                if spawning_pools_existing:
                    self.spawning_pool_building = False
                return  # Already building or exists, skip

            if self._can_build_safely(UnitTypeId.SPAWNINGPOOL, reserve_on_pass=True):
                is_early_game = b.time < 120
                min_workers = 5 if is_early_game else 10
                min_minerals = 150 if is_early_game else 200

                if worker_count >= min_workers and b.minerals >= min_minerals:
                    if b.can_afford(UnitTypeId.SPAWNINGPOOL):
                        hatchery = (
                            b.townhalls.ready.random if b.townhalls.ready.exists else (b.townhalls.first if b.townhalls.exists else None)
                        )
                        if hatchery:
                            # Set flag BEFORE building to prevent duplicate attempts
                            self.spawning_pool_building = True
                            self.last_spawning_pool_check = current_iteration

                            # Prefer assigning a specific worker to avoid selection failures
                            worker = None
                            try:
                                worker = b.select_build_worker(hatchery.position)
                            except Exception:
                                worker = None

                            # CRITICAL: Check for duplicate construction before building
                            if self._can_build_safely(UnitTypeId.SPAWNINGPOOL, reserve_on_pass=True):
                                if worker:
                                    await b.build(UnitTypeId.SPAWNINGPOOL, near=hatchery, unit=worker)
                                else:
                                    await b.build(UnitTypeId.SPAWNINGPOOL, near=hatchery)

                            # If build did not start, clear flag to allow retry
                            if (
                                not b.structures(UnitTypeId.SPAWNINGPOOL).exists
                                and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0
                            ):
                                self.spawning_pool_building = False

                            # Chat message disabled to reduce spam
                            # if current_iteration % 224 == 0:
                            #     if hasattr(b, "personality_manager"):
                            #         from personality_manager import ChatPriority
                            #         await b.personality_manager.send_chat(
                            #             "[AUTONOMY] Rebuilding Spawning Pool. If already building, skip.",
                            #             priority=ChatPriority.LOW
                            #         )
                            # Skip verbose logging here to avoid spam
        except Exception as e:
            # Reset flag on error
            self.spawning_pool_building = False
            if getattr(b, "iteration", 0) % 50 == 0:
                print(f"[ERROR] _maintain_spawning_pool 오류: {e}")

    async def _inject_larva(self):
        """
        여왕의 애벌레 생성 (Inject Larva) - 펌핑 자동화

        💡 펌핑이란?
            여왕의 'Inject Larva' 능력으로 부화장에 추가 애벌레 4마리 생성
            저그의 물량을 폭발시키는 핵심 기술
        """
        b = self.bot

        ready_townhalls = [th for th in b.townhalls if th.is_ready]
        if not ready_townhalls:
            return

        intel = getattr(b, "intel", None)
        if intel and intel.cached_queens is not None:
            queens = intel.cached_queens
        else:
            queens = b.units(UnitTypeId.QUEEN)
        for queen in queens:
            if queen.energy < 25:
                continue

            # Allow queens that are idle OR moving to inject (improves responsiveness)
            if not (queen.is_idle or queen.is_moving):
                continue

            if not ready_townhalls:
                continue

            # Check if hatchery already has inject buff (avoid duplicate inject)
            closest_hatch = min(ready_townhalls, key=lambda th: queen.distance_to(th))

            try:
                # Correct syntax for python-sc2: await self.bot.do(queen(AbilityId, target))
                await b.do(queen(AbilityId.EFFECT_INJECTLARVA, closest_hatch))
                if getattr(b, "iteration", 0) % 100 == 0:
                    print(
                        f"[QUEEN] [{int(b.time)}s] 애벌레 생성 (Inject Larva) - 에너지: {queen.energy:.0f}"
                    )
            except Exception as e:
                # Silently fail if inject fails
                pass

    async def _manage_gas_buildings(self):
        """
        멀티 가스 자동 건설 로직

        모든 완성된 부화장 근처의 가스 간헐천을 확인하여
        가스통이 없는 곳에 자동으로 건설합니다.
        """
        b = self.bot

        spawning_pools = list(b.structures(UnitTypeId.SPAWNINGPOOL))
        if not spawning_pools:
            return

        # CRITICAL: Priority Zero - Don't build extractors if workers are critically low
        # This prevents wasting workers on extractors when economy is collapsing
        # Use direct workers access (cached_workers is a list, not UnitGroup)
        worker_count = (
            b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
        )

        if worker_count < 8:
            return

        # Use safe build check to prevent duplicates
        if not self._can_build_safely(UnitTypeId.EXTRACTOR, reserve_on_pass=True):
            return

        if not b.can_afford(UnitTypeId.EXTRACTOR):
            return

        if b.already_pending(UnitTypeId.EXTRACTOR) >= 2:
            return

        ready_townhalls = b.townhalls.ready
        if not ready_townhalls.exists:
            return

        for hatchery in ready_townhalls:
            try:
                vgs = b.vespene_geyser.closer_than(15, hatchery)
            except (AttributeError, TypeError):
                try:
                    map_vespene = getattr(b.game_info, "map_vespene", [])
                    vgs = (
                        [vg for vg in map_vespene if vg.distance_to(hatchery) < 15]
                        if map_vespene
                        else []
                    )
                except (AttributeError, TypeError):
                    vgs = []

            # Check if vgs is a Units object (has .exists) or a list
            vgs_exists = False
            if hasattr(vgs, "exists") and not isinstance(vgs, list):
                vgs_exists = bool(vgs.exists)
            elif isinstance(vgs, list):
                vgs_exists = len(vgs) > 0

            if not vgs_exists:
                continue

            for vg in vgs:
                nearby_extractors = b.structures(UnitTypeId.EXTRACTOR).closer_than(1, vg)
                if nearby_extractors.exists:
                    continue

                if b.already_pending(UnitTypeId.EXTRACTOR) >= 2:
                    return

                nearby_workers = b.workers.closer_than(20, vg)
                if nearby_workers.exists:
                    worker = nearby_workers.closest_to(vg)
                    try:
                        worker.build(UnitTypeId.EXTRACTOR, vg)
                        return
                    except Exception:
                        continue

    async def _build_tech_buildings(self):
        """테크 건물 자동 건설"""
        b = self.bot
        if not b.townhalls.exists:
            return
        townhalls = [th for th in b.townhalls]
        if not townhalls:
            return
        hatchery = townhalls[0]

        lairs = list(
            b.units.filter(
                lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure
            )
        )
        # IMPROVED: Check for Spawning Pool requirement
        spawning_pools_ready = b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists
        if not lairs and b.time > 120 and spawning_pools_ready and b.can_afford(UnitTypeId.LAIR):  # 180 -> 120
            hatcheries_ready = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.HATCHERY and u.is_structure and u.is_ready
                )
            )
            if hatcheries_ready:
                try:
                    hatchery = hatcheries_ready[0]
                    try:
                        # Try morph method first
                        if hasattr(hatchery, 'morph'):
                            await hatchery.morph(UnitTypeId.LAIR)
                        elif hasattr(hatchery, '__call__'):
                            await hatchery(AbilityId.UPGRADETOLAIR_LAIR)
                        else:
                            await b.do(hatchery(AbilityId.UPGRADETOLAIR_LAIR))
                    except AttributeError:
                        # If morph doesn't exist, use ability directly
                        await b.do(hatchery(AbilityId.UPGRADETOLAIR_LAIR))
                    print(f"[BUILD] [{int(b.time)}s] Lair morph started (tech prerequisite)")
                except Exception as e:
                    if b.iteration % 50 == 0:
                        print(f"[WARNING] Lair morph failed: {e}")
                        traceback.print_exc()

        # Roach Warren (3 minutes later) - Delegated to ProductionManager
        # GUARD: Skip to avoid duplicate tech building construction
        if b.time > self.config.ROACH_WARREN_TIME:
            # ProductionManager handles tech buildings exclusively
            pass

        # tech_to_hydra: Hydralisk Den (mid-game, requires Lair) - Delegated to ProductionManager
        if b.time > 360:
            # GUARD: ProductionManager handles tech buildings exclusively
            # Skip Hydralisk Den and Lurker Den construction to avoid duplicates
            pass

        if b.time > 240:
            if self._is_construction_started(UnitTypeId.EVOLUTIONCHAMBER):
                pass
            elif self._can_build_safely(UnitTypeId.EVOLUTIONCHAMBER, reserve_on_pass=True):
                if b.can_afford(UnitTypeId.EVOLUTIONCHAMBER):
                    # CRITICAL: Check for duplicate construction before building
                    if self._can_build_safely(UnitTypeId.EVOLUTIONCHAMBER, reserve_on_pass=True):
                        # Use safe placement with spacing to prevent SimCity bottleneck
                        build_pos = await self._find_safe_building_placement(
                            UnitTypeId.EVOLUTIONCHAMBER, hatchery.position, placement_step=5
                        )
                        if build_pos:
                            await b.build(UnitTypeId.EVOLUTIONCHAMBER, build_pos)
                        else:
                            await b.build(UnitTypeId.EVOLUTIONCHAMBER, near=hatchery)
                        print(f"[BUILD] [{int(b.time)}s] Evolution Chamber built")

        if b.time > 420:
            lairs = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure and u.is_ready
                )
            )
            hives = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.HIVE and u.is_structure and u.is_ready
                )
            )
            lair_exists = bool(lairs or hives)
            if lair_exists:
                if b.structures(UnitTypeId.SPIRE).exists or b.already_pending(UnitTypeId.SPIRE) > 0:
                    pass
                elif self._can_build_safely(UnitTypeId.SPIRE, reserve_on_pass=True):
                    if b.can_afford(UnitTypeId.SPIRE):
                        # CRITICAL: Check for duplicate construction before building
                        if self._can_build_safely(UnitTypeId.SPIRE, reserve_on_pass=True):
                            # Use safe placement with spacing to prevent SimCity bottleneck
                            build_pos = await self._find_safe_building_placement(
                                UnitTypeId.SPIRE, hatchery.position, placement_step=5
                            )
                            if build_pos:
                                await b.build(UnitTypeId.SPIRE, build_pos)
                            else:
                                await b.build(UnitTypeId.SPIRE, near=hatchery)
                            print(f"[BUILD] [{int(b.time)}s] Spire built (Air Force activated)")

    async def _upgrade_tech(self):
        """
        레어/하이브 업그레이드

        💡 안전한 API 호출:
            hatch(AbilityId.UPGRADETOLAIR_LAIR)
        """
        b = self.bot

        if b.time > self.config.LAIR_TIME:
            spawning_pools = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure and u.is_ready
                )
            )
            if spawning_pools:
                lairs = list(
                    b.units.filter(lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure)
                )
                hives = list(
                    b.units.filter(lambda u: u.type_id == UnitTypeId.HIVE and u.is_structure)
                )
                if not lairs and not hives:
                    hatcheries = [
                        th
                        for th in b.townhalls
                        if th.type_id == UnitTypeId.HATCHERY and th.is_ready and th.is_idle
                    ]
                    for hatch in hatcheries:
                        if b.can_afford(UnitTypeId.LAIR):
                            hatch(AbilityId.UPGRADETOLAIR_LAIR)
                            print(f"[UPGRADE] [{int(b.time)}초] 레어 업그레이드")
                            break

        await self._build_ultimate_tech()

    async def _build_ultimate_tech(self):
        """
        최종 테크 트리 자동 건설

        감염 구덩이 -> 군락 -> 울트라리스크 동굴 / 거대 둥지탑
        """
        b = self.bot

        townhalls = b.townhalls
        if not townhalls.exists:
            return

        lairs = b.structures(UnitTypeId.LAIR).ready
        if lairs.exists:
            infestation_pits = b.structures(UnitTypeId.INFESTATIONPIT)
            pending_pits = b.already_pending(UnitTypeId.INFESTATIONPIT)
            if not infestation_pits.exists and pending_pits == 0:
                if self._can_build_safely(UnitTypeId.INFESTATIONPIT, reserve_on_pass=True):
                    if b.can_afford(UnitTypeId.INFESTATIONPIT):
                        # CRITICAL: Additional duplicate check before building
                        if not b.structures(UnitTypeId.INFESTATIONPIT).exists and b.already_pending(UnitTypeId.INFESTATIONPIT) == 0:
                            try:
                                await b.build(UnitTypeId.INFESTATIONPIT, near=townhalls.random)
                                print(f"[BUILD] [{int(b.time)}s] Infestation Pit built (Hive prerequisite)")
                            except Exception:
                                pass

        infestation_pits_ready = b.structures(UnitTypeId.INFESTATIONPIT).ready
        if lairs.exists and infestation_pits_ready.exists:
            hives = b.structures(UnitTypeId.HIVE)
            pending_hives = b.already_pending(UnitTypeId.HIVE)
            if not hives.exists and pending_hives == 0:
                if b.can_afford(UnitTypeId.HIVE):
                    # CRITICAL: Use ready lairs list instead of .random() for safety
                    lairs_ready = [l for l in lairs if l.is_ready]
                    if lairs_ready:
                        try:
                            lairs_ready[0](AbilityId.UPGRADETOHIVE_HIVE)
                            print(f"[BUILD] [{int(b.time)}s] Hive upgrade started")
                        except Exception as e:
                            if b.iteration % 50 == 0:
                                print(f"[WARNING] Hive upgrade failed: {e}")

        hives_ready = b.structures(UnitTypeId.HIVE).ready
        if hives_ready.exists:
            ultralisk_caverns = b.structures(UnitTypeId.ULTRALISKCAVERN)
            if not ultralisk_caverns.exists and not b.already_pending(UnitTypeId.ULTRALISKCAVERN):
                # CRITICAL: Additional duplicate check before building
                if self._can_build_safely(UnitTypeId.ULTRALISKCAVERN, reserve_on_pass=True):
                    if b.can_afford(UnitTypeId.ULTRALISKCAVERN):
                        try:
                            await b.build(UnitTypeId.ULTRALISKCAVERN, near=townhalls.random)
                        except Exception:
                            pass

            spires = b.structures(UnitTypeId.SPIRE).ready
            # Fix: UnitTypeId.GREAT_SPIRE -> UnitTypeId.GREATERSPIRE (correct SC2 API naming)
            great_spires = b.structures(UnitTypeId.GREATERSPIRE)
            pending_greater_spires = b.already_pending(UnitTypeId.GREATERSPIRE)
            if spires.exists and not great_spires.exists and pending_greater_spires == 0:
                if b.can_afford(UnitTypeId.GREATERSPIRE):
                    # CRITICAL: Use ready spires list instead of .random() for safety
                    spires_ready = [s for s in spires if s.is_ready]
                    if spires_ready:
                        try:
                            spires_ready[0](AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE)
                            print(f"[BUILD] [{int(b.time)}s] Greater Spire upgrade started")
                        except Exception as e:
                            if b.iteration % 50 == 0:
                                print(f"[WARNING] Greater Spire upgrade failed: {e}")

    async def _manage_resource_expenditure(self):
        """
        Resource expenditure optimization

        Spends excess minerals when resources are abundant:
        1. Macro Hatcheries: Additional hatcheries for larva production (minerals >= 500)
        2. Static Defense: Spine Crawlers for defense (minerals >= 400)
        3. Resource Flush: Prevents 2500+ mineral accumulation

        Critical for preventing ARMY_OVERWHELMED due to unspent resources
        """
        b = self.bot

        try:
            intel = getattr(b, "intel", None)
            if intel and intel.cached_townhalls is not None:
                townhalls = list(intel.cached_townhalls) if intel.cached_townhalls.exists else []
                if not townhalls:
                    return
            else:
                if not b.townhalls.exists:
                    return
                townhalls = [th for th in b.townhalls]

            # Use direct workers access (cached_workers is a list, not UnitGroup)
            worker_count = (
                b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
            )
            current_base_count = len(townhalls)

            # Strategy 1: Macro Hatchery - Use learned parameters

            macro_hatchery_mineral_threshold = get_learned_parameter(
                "macro_hatchery_mineral_threshold", 500
            )
            macro_hatchery_worker_threshold = get_learned_parameter(
                "macro_hatchery_worker_threshold", 16
            )
            macro_hatchery_max_bases = get_learned_parameter("macro_hatchery_max_bases", 6)

            if (
                b.minerals >= macro_hatchery_mineral_threshold
                and worker_count >= macro_hatchery_worker_threshold
                and current_base_count < macro_hatchery_max_bases
            ):
                # Check if we already have enough hatcheries for workers
                # Optimal: 1 hatchery per 16 workers, but allow macro hatcheries up to 6 total
                optimal_hatcheries = max(current_base_count, (worker_count // 16) + 1)
                if current_base_count < optimal_hatcheries:
                    if (
                        b.can_afford(UnitTypeId.HATCHERY)
                        and b.already_pending(UnitTypeId.HATCHERY) == 0
                    ):
                        try:
                            # Try to build near existing hatchery (macro hatchery style)
                            if townhalls:
                                main_hatch = townhalls[0]
                                # Build near main hatchery but with spacing
                                build_pos = await self._find_safe_building_placement(
                                    UnitTypeId.HATCHERY,
                                    main_hatch.position,
                                    placement_step=6,
                                )
                                # CRITICAL: Check for duplicate construction before building
                                if not b.structures(UnitTypeId.HATCHERY).closer_than(15, build_pos).exists and b.already_pending(UnitTypeId.HATCHERY) == 0:
                                    if build_pos:
                                        await b.build(UnitTypeId.HATCHERY, build_pos)
                                        if getattr(b, "iteration", 0) % 100 == 0:
                                            print(
                                                f"[RESOURCE] [{int(b.time)}s] Macro Hatchery built ({b.minerals} minerals)"
                                            )
                        except Exception:
                            pass

            # Strategy 2: Static Defense - Use learned parameters
            static_defense_mineral_threshold = get_learned_parameter(
                "static_defense_mineral_threshold", 400
            )
            static_defense_time_threshold = get_learned_parameter(
                "static_defense_time_threshold", 180
            )

            if (
                b.minerals >= static_defense_mineral_threshold
                and b.time >= static_defense_time_threshold
            ):
                spine_crawlers = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.SPINECRAWLER and u.is_structure
                    )
                )
                spine_count = len(spine_crawlers)

                # Build up to 4 spine crawlers (reasonable defense without over-investment)
                if spine_count < 4 and b.can_afford(UnitTypeId.SPINECRAWLER):
                    if b.already_pending(UnitTypeId.SPINECRAWLER) == 0:
                        try:
                            if townhalls:
                                # Build near first hatchery for defense
                                main_hatch = townhalls[0]
                                build_pos = await self._find_safe_building_placement(
                                    UnitTypeId.SPINECRAWLER,
                                    main_hatch.position,
                                    placement_step=6,
                                )
                                # CRITICAL: Check for duplicate construction before building
                                if self._can_build_safely(UnitTypeId.SPINECRAWLER, reserve_on_pass=True):
                                    if build_pos:
                                        await b.build(UnitTypeId.SPINECRAWLER, build_pos)
                                        if getattr(b, "iteration", 0) % 100 == 0:
                                            print(
                                                f"[RESOURCE] [{int(b.time)}s] Spine Crawler built ({b.minerals} minerals)"
                                            )
                        except Exception:
                            pass

            # Strategy 3: Resource Flush Emergency (minerals >= 800)
            # Emergency resource expenditure when minerals are very high
            if b.minerals >= 800:
                # Try expansion first (highest priority)
                if current_base_count < 4 and b.can_afford(UnitTypeId.HATCHERY):
                    try:
                        await b.expand_now()
                        if getattr(b, "iteration", 0) % 100 == 0:
                            print(
                                f"[RESOURCE] [{int(b.time)}s] Emergency expansion: {b.minerals} minerals"
                            )
                    except Exception:
                        pass
                # Otherwise, build macro hatchery or static defense
                elif (
                    current_base_count < 6
                    and b.can_afford(UnitTypeId.HATCHERY)
                    and b.already_pending(UnitTypeId.HATCHERY) == 0
                ):
                    try:
                        if townhalls:
                            main_hatch = townhalls[0]
                            build_pos = await self._find_safe_building_placement(
                                UnitTypeId.HATCHERY,
                                main_hatch.position,
                                placement_step=6,
                            )
                            # CRITICAL: Check for duplicate construction before building
                            if not b.structures(UnitTypeId.HATCHERY).closer_than(15, build_pos).exists and b.already_pending(UnitTypeId.HATCHERY) == 0:
                                if build_pos:
                                    await b.build(UnitTypeId.HATCHERY, build_pos)
                                    if getattr(b, "iteration", 0) % 100 == 0:
                                        print(
                                            f"[RESOURCE] [{int(b.time)}s] Emergency Macro Hatchery: {b.minerals} minerals"
                                        )
                    except Exception:
                        pass

        except Exception:
            # Fail silently to avoid disrupting game flow
            pass

    async def _manage_expansion(self):
        """확장 타이밍 결정 - 멀티(확장 기지) 자동으로 늘리기

        Enhanced for official AI Arena maps:
        - TorchesAIE, PylonAIE, PersephoneAIE, IncorporealAIE,
        - MagannathaAIE, UltraloveAIE, LeyLinesAIE
        """
        b = self.bot

        if b.already_pending(UnitTypeId.HATCHERY) > 0:
            return

        townhalls = [th for th in b.townhalls]
        current_base_count = len(townhalls)

        if current_base_count >= 4:
            return

        # Map-specific expansion logic for official AI Arena maps
        # Check if we have expansion locations available
        try:
            expansion_locations = list(b.expansion_locations.keys())
            if not expansion_locations:
                # No expansion locations (Micro Ladder or special map)
                return
        except Exception:
            # Fallback if expansion_locations not available
            pass

        build_plan = getattr(b, "current_build_plan", None)
        should_expand_aggressive = build_plan.get("should_expand", False) if build_plan else False

        if should_expand_aggressive:
            if b.minerals >= 250:
                if b.can_afford(UnitTypeId.HATCHERY):
                    try:
                        await b.expand_now()
                        return
                    except Exception:
                        pass

        # Enhanced: More aggressive expansion for ladder play
        # Check worker count and army size before expanding
        # Use direct workers access (cached_workers is a list, not UnitGroup)
        worker_count = (
            b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
        )
        army_supply = b.supply_army

        # CRITICAL: Emergency expansion when minerals are excessive - Use learned parameters
        # This prevents ARMY_OVERWHELMED defeats due to unspent resources

        emergency_expand_mineral_threshold = get_learned_parameter(
            "emergency_expand_mineral_threshold", 1500
        )
        emergency_expand_max_bases = get_learned_parameter("emergency_expand_max_bases", 4)

        if (
            b.minerals >= emergency_expand_mineral_threshold
            and current_base_count < emergency_expand_max_bases
        ):
            if b.can_afford(UnitTypeId.HATCHERY):
                try:
                    await b.expand_now()
                    if getattr(b, "iteration", 0) % 100 == 0:
                        print(
                            f"[EXPANSION] [{int(b.time)}s] Emergency expansion: {b.minerals} minerals (resource expenditure)"
                        )
                    return
                except Exception:
                    pass

        # Expand if we have enough workers and some army - Use learned parameters
        first_expand_worker_threshold = get_learned_parameter("first_expand_worker_threshold", 16)
        first_expand_army_threshold = get_learned_parameter("first_expand_army_threshold", 10)
        first_expand_mineral_threshold = get_learned_parameter(
            "first_expand_mineral_threshold", 300
        )

        if current_base_count == 1:
            # First expansion: Use learned thresholds
            if (
                worker_count >= first_expand_worker_threshold
                and army_supply >= first_expand_army_threshold
                and b.minerals >= first_expand_mineral_threshold
            ):
                if b.can_afford(UnitTypeId.HATCHERY):
                    try:
                        await b.expand_now()
                        return
                    except Exception:
                        pass
        elif current_base_count == 2:
            # Second expansion: Use learned thresholds
            second_expand_worker_threshold = get_learned_parameter(
                "second_expand_worker_threshold", 32
            )
            second_expand_army_threshold = get_learned_parameter("second_expand_army_threshold", 20)
            second_expand_mineral_threshold = get_learned_parameter(
                "second_expand_mineral_threshold", 300
            )

            if (
                worker_count >= second_expand_worker_threshold
                and army_supply >= second_expand_army_threshold
                and b.minerals >= second_expand_mineral_threshold
            ):
                if b.can_afford(UnitTypeId.HATCHERY):
                    try:
                        await b.expand_now()
                        return
                    except Exception:
                        pass

        expansion_mineral_minimum = get_learned_parameter("expansion_mineral_minimum", 300)

        if b.minerals < expansion_mineral_minimum:
            return

        if current_base_count == 1:
            intel = getattr(b, "intel", None)
            if intel and intel.cached_zerglings is not None:
                zerglings = intel.cached_zerglings
                zergling_count = (
                    zerglings.amount if hasattr(zerglings, "amount") else len(list(zerglings))
                )
            else:
                zerglings = b.units(UnitTypeId.ZERGLING)
                zergling_count = (
                    zerglings.amount if hasattr(zerglings, "amount") else len(list(zerglings))
                )
            if zergling_count < 8:
                return

            if intel and intel.cached_queens is not None:
                queens = intel.cached_queens
                queen_count = queens.amount if hasattr(queens, "amount") else len(list(queens))
            else:
                queens = b.units(UnitTypeId.QUEEN)
                queen_count = queens.amount if hasattr(queens, "amount") else len(list(queens))
            if queen_count < 1:
                return

            if intel and intel.cached_spine_crawlers is not None:
                spine_crawlers = (
                    list(intel.cached_spine_crawlers) if intel.cached_spine_crawlers.exists else []
                )
            else:
                spine_crawlers = list(b.structures(UnitTypeId.SPINECRAWLER))
            if len(spine_crawlers) < 1:
                return

        elif current_base_count >= 2:
            intel = getattr(b, "intel", None)
            if intel and intel.cached_zerglings is not None:
                zerglings = intel.cached_zerglings
                zergling_count = (
                    zerglings.amount if hasattr(zerglings, "amount") else len(list(zerglings))
                )
            else:
                zerglings = b.units(UnitTypeId.ZERGLING)
                zergling_count = (
                    zerglings.amount if hasattr(zerglings, "amount") else len(list(zerglings))
                )

            if intel and intel.cached_roaches is not None:
                roaches = intel.cached_roaches
                roach_count = roaches.amount if hasattr(roaches, "amount") else len(list(roaches))
            else:
                roaches = b.units(UnitTypeId.ROACH)
                roach_count = roaches.amount if hasattr(roaches, "amount") else len(list(roaches))

            total_defense_units = zergling_count + roach_count
            min_defense = self.config.MIN_DEFENSE_BEFORE_EXPAND

            if total_defense_units < min_defense // 2:
                return

        workers = [w for w in b.workers]
        current_workers = len(workers)
        optimal_workers = current_base_count * self.config.WORKERS_PER_BASE

        should_expand = False

        if current_workers >= optimal_workers * 0.7:
            should_expand = True

        if current_base_count == 2 and b.minerals >= 300:
            should_expand = True

        if b.minerals >= 400 and current_base_count < 3:
            should_expand = True

        if b.minerals >= 600:
            should_expand = True

        if b.time >= 120 and b.minerals >= 350 and current_base_count < 2:
            should_expand = True

        if should_expand:
            if b.can_afford(UnitTypeId.HATCHERY):
                try:
                    await b.expand_now()
                except Exception as e:
                    pass

    async def _research_zergling_speed(self):
        """
        저글링 발업 (대사 촉진) 최우선 연구

        💡 견제의 핵심:
            가스가 100 모이면 산란못에서 '대사 촉진(Metabolic Boost)' 연구를
            가장 먼저 하도록 설정 (다른 모든 업그레이드보다 우선!)
        """
        b = self.bot

        if UpgradeId.ZERGLINGMOVEMENTSPEED in b.state.upgrades:
            return

        if b.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) > 0:
            return

        if b.vespene < 100:
            return

        ready_idle_pools = list(
            b.units.filter(
                lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL
                and u.is_structure
                and u.is_ready
                and u.is_idle
            )
        )

        if not ready_idle_pools:
            return

        if b.minerals >= 100 and b.vespene >= 100:
            pool = ready_idle_pools[0]
            pool.research(UpgradeId.ZERGLINGMOVEMENTSPEED)
            if getattr(b, "iteration", 0) % 50 == 0:
                print(f"[UPGRADE] [{int(b.time)}s] 저글링 발업 연구 시작! (가스 100 달성)")

    async def _research_upgrades(self):
        """진화 챔버 업그레이드 연구 (저글링 발업은 이미 완료되어야 함)"""
        b = self.bot

        ready_idle_evos = list(
            b.units.filter(
                lambda u: u.type_id == UnitTypeId.EVOLUTIONCHAMBER
                and u.is_structure
                and u.is_ready
                and u.is_idle
            )
        )
        for evo in ready_idle_evos:
            if UpgradeId.ZERGMELEEWEAPONSLEVEL1 not in b.state.upgrades:
                if b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL1):
                    if not b.already_pending_upgrade(UpgradeId.ZERGMELEEWEAPONSLEVEL1):
                        evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL1)
                        print(f"[UPGRADE] [{int(b.time)}s] Melee Attack Level 1 started")
                        return
            elif UpgradeId.ZERGMELEEWEAPONSLEVEL2 not in b.state.upgrades:
                if b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL2):
                    if not b.already_pending_upgrade(UpgradeId.ZERGMELEEWEAPONSLEVEL2):
                        evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL2)
                        print(f"[UPGRADE] [{int(b.time)}s] Melee Attack Level 2 started")
                        return
            elif UpgradeId.ZERGMELEEWEAPONSLEVEL3 not in b.state.upgrades:
                if b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL3):
                    if not b.already_pending_upgrade(UpgradeId.ZERGMELEEWEAPONSLEVEL3):
                        evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL3)
                        print(f"[UPGRADE] [{int(b.time)}s] Melee Attack Level 3 started")
                        return

            if UpgradeId.ZERGMISSILEWEAPONSLEVEL1 not in b.state.upgrades:
                if b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL1):
                    if not b.already_pending_upgrade(UpgradeId.ZERGMISSILEWEAPONSLEVEL1):
                        evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
                        print(f"[UPGRADE] [{int(b.time)}s] Missile Attack Level 1 started")
                        return
            elif UpgradeId.ZERGMISSILEWEAPONSLEVEL2 not in b.state.upgrades:
                if b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL2):
                    if not b.already_pending_upgrade(UpgradeId.ZERGMISSILEWEAPONSLEVEL2):
                        evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL2)
                        print(f"[UPGRADE] [{int(b.time)}s] Missile Attack Level 2 started")
                        return
            elif UpgradeId.ZERGMISSILEWEAPONSLEVEL3 not in b.state.upgrades:
                if b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL3):
                    if not b.already_pending_upgrade(UpgradeId.ZERGMISSILEWEAPONSLEVEL3):
                        evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL3)
                        print(f"[UPGRADE] [{int(b.time)}s] Missile Attack Level 3 started")
                        return

            if UpgradeId.ZERGGROUNDARMORSLEVEL1 not in b.state.upgrades:
                if b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL1):
                    if not b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL1):
                        evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL1)
                        print(f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 1 started")
                        return
            elif UpgradeId.ZERGGROUNDARMORSLEVEL2 not in b.state.upgrades:
                if b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL2):
                    if not b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL2):
                        evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL2)
                        print(f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 2 started")
                        return
            elif UpgradeId.ZERGGROUNDARMORSLEVEL3 not in b.state.upgrades:
                if b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL3):
                    if not b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL3):
                        evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL3)
                        print(f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 3 started")
                        return

    async def _build_anti_air_structures(self):
        """
        build_anti_air_structures: 각 부화장마다 포자 촉수(Spore Crawler) 1개씩 건설
        여유가 되면 번식지(Lair)로 업그레이드하고 히드라리스크 굴 건설
        밴시나 해방선에 대비
        """
        b = self.bot

        townhalls = [th for th in b.townhalls]
        if not townhalls:
            return

        for hatchery in townhalls:
            nearby_spores = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.SPORECRAWLER
                    and u.is_structure
                    and u.distance_to(hatchery) < 15
                )
            )

            if len(nearby_spores) >= 1:
                continue

            if b.already_pending(UnitTypeId.SPORECRAWLER) > 0:
                continue

            evolution_chambers = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.EVOLUTIONCHAMBER
                    and u.is_structure
                    and u.is_ready
                )
            )
            if not evolution_chambers:
                continue

            if not b.can_afford(UnitTypeId.SPORECRAWLER):
                continue

            build_pos = hatchery.position.towards(b.game_info.map_center, 8)
            # CRITICAL: Check for duplicate construction before building
            if self._can_build_safely(UnitTypeId.SPORECRAWLER, reserve_on_pass=True):
                try:
                    await b.build(UnitTypeId.SPORECRAWLER, near=build_pos)
                except Exception:
                    pass

        if b.minerals >= 150 and b.vespene >= 100:
            hatcheries = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.HATCHERY
                    and u.is_structure
                    and u.is_ready
                    and u.is_idle
                )
            )
            lairs = list(b.units.filter(lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure))
            hives = list(b.units.filter(lambda u: u.type_id == UnitTypeId.HIVE and u.is_structure))

            if hatcheries and not lairs and not hives:
                if b.can_afford(UnitTypeId.LAIR):
                    hatchery = hatcheries[0]
                    hatchery(AbilityId.UPGRADETOLAIR_LAIR)

        lairs = list(
            b.units.filter(lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure and u.is_ready)
        )
        hives = list(
            b.units.filter(lambda u: u.type_id == UnitTypeId.HIVE and u.is_structure and u.is_ready)
        )

        if lairs or hives:
            hydra_dens = list(
                b.units.filter(lambda u: u.type_id == UnitTypeId.HYDRALISKDEN and u.is_structure)
            )

            if not hydra_dens:
                if b.already_pending(UnitTypeId.HYDRALISKDEN) == 0:
                    # CRITICAL: Check for duplicate construction before building
                    if self._can_build_safely(UnitTypeId.HYDRALISKDEN, reserve_on_pass=True):
                        if b.can_afford(UnitTypeId.HYDRALISKDEN):
                            if townhalls and len(townhalls) > 0:
                                await b.build(UnitTypeId.HYDRALISKDEN, near=townhalls[0])

    async def _build_early_spine_crawler(self):
        """
        산란못 완성 후 본진 근처에 가시촉수 1개 건설
        Enhanced: 적 유닛이 본진 근처에 나타나면 즉시 건설!
        """
        b = self.bot

        spine_crawlers = list(
            b.units.filter(lambda u: u.type_id == UnitTypeId.SPINECRAWLER and u.is_structure)
        )

        min_spine_count = 1
        try:
            combat_manager = getattr(b, "combat", None)
            if combat_manager:
                personality = getattr(combat_manager, "personality", "NEUTRAL")
                if personality == "CAUTIOUS":
                    min_spine_count = 2
                elif personality == "AGGRESSIVE":
                    min_spine_count = 1
        except (AttributeError, TypeError):
            pass

        enemy_near_base = False
        try:
            townhalls = [th for th in b.townhalls]
            if townhalls:
                hatchery_pos = townhalls[0].position
                enemy_units = getattr(b, "enemy_units", [])
                if enemy_units:
                    enemy_list = list(enemy_units) if hasattr(enemy_units, "__iter__") else []
                    for enemy in enemy_list:
                        if enemy.distance_to(hatchery_pos) < 30:
                            enemy_near_base = True
                            break
        except Exception:
            pass

        if not enemy_near_base and len(spine_crawlers) >= min_spine_count:
            return

        if b.already_pending(UnitTypeId.SPINECRAWLER) > 0:
            return

        intel = getattr(b, "intel", None)
        if intel and intel.cached_spawning_pools is not None:
            spawning_pools = (
                list(intel.cached_spawning_pools) if intel.cached_spawning_pools.exists else []
            )
        else:
            spawning_pools = list(b.structures(UnitTypeId.SPAWNINGPOOL).ready)
        if not spawning_pools:
            return

        if not b.can_afford(UnitTypeId.SPINECRAWLER):
            return

        if not b.townhalls.exists:
            return
        townhalls = [th for th in b.townhalls]
        if townhalls:
            hatchery = townhalls[0]
            build_pos = hatchery.position.towards(b.game_info.map_center, 8)
            # CRITICAL: Check for duplicate construction before building
            if self._can_build_safely(UnitTypeId.SPINECRAWLER, reserve_on_pass=True):
                try:
                    await b.build(UnitTypeId.SPINECRAWLER, near=build_pos)
                    if enemy_near_base:
                        print(f"[DEFENSE] [{int(b.time)}s] 적 감지! 가시 촉수 긴급 건설!")
                except Exception:
                    pass

    async def build_defense(self, count: int = 3):
        """
        방어 건물 건설 (러시 대응)

        Args:
            count: 건설할 스파인 크롤러 수
        """
        b = self.bot

        spine_crawlers = list(
            b.units.filter(lambda u: u.type_id == UnitTypeId.SPINECRAWLER and u.is_structure)
        )
        spine_count = len(spine_crawlers)
        if spine_count >= count:
            return

        if b.can_afford(UnitTypeId.SPINECRAWLER):
            if not b.townhalls.exists:
                return
            townhalls = [th for th in b.townhalls]
            if townhalls:
                hatchery = townhalls[0]
                pos = hatchery.position.towards(b.game_info.map_center, 8)
                # CRITICAL: Check for duplicate construction before building
                if self._can_build_safely(UnitTypeId.SPINECRAWLER, reserve_on_pass=True):
                    await b.build(UnitTypeId.SPINECRAWLER, near=pos)
                    print(f"[DEFENSE] [{int(b.time)}초] 스파인 크롤러 건설 (방어)")

    def get_economy_status(self) -> dict:
        """현재 경제 상태 반환"""
        b = self.bot
        workers = [w for w in b.workers]
        townhalls = [th for th in b.townhalls]
        return {
            "workers": len(workers),
            "minerals": b.minerals,
            "vespene": b.vespene,
            "bases": len(townhalls),
            "supply": f"{b.supply_used}/{b.supply_cap}",
            "gas_reduced": self.gas_workers_reduced,
        }
