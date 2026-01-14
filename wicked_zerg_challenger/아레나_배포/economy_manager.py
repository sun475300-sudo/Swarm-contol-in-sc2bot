# -*- coding: utf-8 -*-
"""
================================================================================
                    💰 경제 및 기지 관리 (economy_manager.py)
================================================================================
자원 채취와 건물 건설의 자동화를 담당합니다.

핵심 기능:
    1. 일꾼 자동 배분 및 최적화
    2. 산란못 유지 및 재건설 (회복력)
    3. 여왕의 애벌레 생성 (펌핑)
    4. 가스 조절 (발업 후 미네랄 전환)
    5. 테크 업그레이드 (레어, 하이브)
    6. 확장 타이밍 결정
================================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from typing import Dict, Optional

from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2

from config import Config


class EconomyManager:
    """
    경제 관리자

    자원 채취, 건물 건설, 테크 업그레이드를 담당합니다.
    """

    def __init__(self, bot: BotAI):
        """
        Args:
            bot: 메인 봇 인스턴스
        """
        self.bot = bot
        self.config = Config()

        # 가스 조절 상태
        self.gas_workers_reduced = False
        self.speed_upgrade_done = False

        # Stuck unit detection tracking (unit_tag -> last_position -> last_time)
        self.unit_positions: Dict[int, Dict] = {}

        # Building construction flags to prevent infinite loops
        self.spawning_pool_building = (
            False  # Flag to prevent multiple simultaneous Spawning Pool builds
        )
        self.last_spawning_pool_check = 0  # Track last check time to prevent spam

        # Shared build reservations to prevent duplicate construction across managers
        if not hasattr(self.bot, "build_reservations"):
            self.bot.build_reservations: Dict[UnitTypeId, float] = {}
        if not hasattr(self.bot, "_build_reservation_wrapped"):
            original_build = self.bot.build

            async def _build_with_reservation(structure_type, *args, **kwargs):
                try:
                    self._reserve_building(structure_type)
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

        # 1. 이미 존재하는지 확인
        existing = b.structures(structure_id).amount
        if existing > 0:
            return False

        # 2. 현재 건설 중(Pending)인지 확인
        pending = b.already_pending(structure_id)
        if pending > 0:
            return False

        # 3. (중요) 건설하러 이동 중인 일벌레가 있는지 확인
        # 가끔 already_pending에 잡히기 전 찰나의 순간을 방어합니다.
        if check_workers:
            try:
                # 건물 생성 능력 ID 가져오기
                creation_ability = b.game_data.units[structure_id.value].creation_ability
                if creation_ability:
                    # 🚀 성능 최적화: IntelManager 캐시 사용
                    intel = getattr(b, "intel", None)
                    if intel and intel.cached_workers is not None:
                        workers = intel.cached_workers
                    else:
                        workers = b.workers
                    # 일벌레들의 명령 확인
                    for worker in workers:
                        if worker.orders:
                            for order in worker.orders:
                                if order.ability.id == creation_ability.id:
                                    return False
            except (AttributeError, KeyError, TypeError):
                # 에러 발생 시 안전하게 False 반환하지 않고 계속 진행
                # (일부 건물은 creation_ability가 없을 수 있음)
                pass

        # 4. 가스 건물(Extractor) 특수 체크: 같은 가스 지점에 이미 건설 중인지 확인
        if structure_id == UnitTypeId.EXTRACTOR:
            # 가스 지점 근처에 이미 Extractor가 있는지 확인
            vespene_geysers = b.vespene_geyser
            for geyser in vespene_geysers:
                nearby_extractors = b.structures(UnitTypeId.EXTRACTOR).closer_than(1.0, geyser)
                if nearby_extractors:
                    return False

        if reserve_on_pass:
            self._reserve_building(structure_id)

        return True

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
                # 🚀 성능 최적화: IntelManager 캐시 사용
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
            # 🚀 성능 최적화: IntelManager 캐시 사용
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

        # 🚀 성능 최적화: intel_manager 캐시 사용 (중복 연산 방지)
        # IntelManager가 이미 유닛 정보를 캐싱했으므로 재사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_townhalls is not None:
            # 캐시된 townhalls 사용
            townhalls = intel.cached_townhalls
            if not townhalls.exists:
                return
        else:
            # Fallback: 캐시가 없으면 직접 접근 (하위 호환성)
            # 🛡️ 철벽 안전장치: townhalls가 없으면 즉시 리턴 (Micro Ladder 대응)
            if not b.townhalls.exists:
                return
            townhalls = b.townhalls

        # NOTE: Removed emergency Spawning Pool auto-build in deploy package.
        # Spawning Pool construction is handled by early build order and
        # maintenance routines with proper safety checks.

        # Emergency unstuck logic (run every 25 frames for faster response, was 50)
        if getattr(b, "iteration", 0) % 25 == 0:
            await self._unstuck_units()

        # Smart rally point setup (run every 100 frames, about 5 seconds)
        if getattr(b, "iteration", 0) % 100 == 0:
            await self._set_smart_rally_points()

        # 캐싱된 townhalls 사용 (필요한 경우에만 리스트 변환)
        townhalls = list(b.townhalls) if hasattr(self, "_need_townhalls_list") else None

        # 0️⃣ 초반 빌드 오더 (16앞마당-18가스-17산란못) - 최우선
        await self._execute_early_build_order()

        # 1️⃣ 일꾼 자동 배분
        await self._distribute_workers()

        # 1-0️⃣ 자율적 일꾼 행동: 방황하는 일꾼이 스스로 자원으로 돌아감 (본능)
        # 일꾼이 스스로 "나의 집은 본진 자원 지대다"라는 회귀 본능을 가짐
        await self._autonomous_worker_behavior()

        # 1-1️⃣ 자율적 일꾼 행동 관리 (Autonomous Worker Behavior Management)
        # 봇이 스스로 일꾼의 최적 행동을 판단하여 자원 채취에 집중하도록 합니다
        await self._restrict_worker_combat_and_enforce_gathering()

        # 2️⃣ 가스 조절 (발업 후)
        await self._manage_gas_workers()

        # 3️⃣ 산란못 유지 및 재건설
        await self._maintain_spawning_pool()

        # 3-1️⃣ 산란못 완성 후 가시촉수 건설
        await self._build_early_spine_crawler()

        # 4️⃣ 여왕 펌핑
        await self._inject_larva()

        # 4-1️⃣ 점막 확산 (여왕 에너지가 남으면)
        await self._spread_creep()

        # 5️⃣ 가스 건물 관리
        await self._manage_gas_buildings()

        # 6️⃣ 테크 건물 건설
        await self._build_tech_buildings()

        # 7️⃣ 테크 업그레이드
        await self._upgrade_tech()

        # 7-1️⃣ 저글링 발업 최우선 연구 (가스 100 모이면 즉시) - 최우선순위!

        # 7-2️⃣ 자원 소모 최적화 (Macro Hatchery & Resource Flush)
        await self._manage_resource_expenditure()
        # This must be checked BEFORE any other upgrades or tech buildings
        await self._research_zergling_speed()

        # 8️⃣ 확장 결정
        await self._manage_expansion()

        # 8-1️⃣ 공중 방어 건물 건설 (각 부화장마다 포자 촉수)
        await self._build_anti_air_structures()

        # 9️⃣ 업그레이드 연구
        await self._research_upgrades()

    # 0️⃣ 초반 빌드 오더 (16앞마당-18가스-17산란못)
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

        # 맵 크기에 따른 빌드 오더 조정
        map_size = getattr(b, "map_size", "MEDIUM")

        # 상대방 기록 기반 복수 빌드 (6-pool)
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

        # 6-pool 복수 빌드 (이전에 졌던 상대에게) - Use learned parameter
        from config import get_learned_parameter

        aggressive_build_supply = get_learned_parameter("aggressive_build_supply", 6)

        if use_aggressive_build and b.supply_used >= aggressive_build_supply:
            # CRITICAL: Prevent infinite loop - check if already building or exists
            spawning_pools_existing = list(
                b.units.filter(lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure)
            )
            pending_count = b.already_pending(UnitTypeId.SPAWNINGPOOL)
            current_iteration = getattr(b, "iteration", 0)

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

                            # Chat message only once per build attempt
                            if current_iteration % 224 == 0:
                                await b.chat_send(
                                    "🏗️ [자율 판단] 복수 빌드: 산란못 건설을 시작합니다."
                                )

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

        # SMALL 맵: 빠른 풀 - Use learned parameter
        small_map_pool_supply = get_learned_parameter("small_map_pool_supply", 12)

        if map_size == "SMALL" and b.supply_used >= small_map_pool_supply:
            # CRITICAL: Prevent infinite loop - check if already building or exists
            spawning_pools_existing = list(
                b.units.filter(lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure)
            )
            pending_count = b.already_pending(UnitTypeId.SPAWNINGPOOL)
            current_iteration = getattr(b, "iteration", 0)

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

                            # Chat message only once per build attempt
                            if current_iteration % 224 == 0:
                                await b.chat_send(
                                    "🏗️ [자율 판단] 소형 맵 빠른 빌드: 산란못 건설을 시작합니다."
                                )

                            print(
                                f"[BUILD ORDER] [{int(b.time)}s] 12 Supply: Spawning Pool (Small map aggressive build)"
                            )
                            return  # Early pool built, skip standard build
                    except Exception:
                        # Reset flag on error
                        self.spawning_pool_building = False
                        pass

        # LARGE 맵: 경제 우선 - Use learned parameter
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

        # MEDIUM 맵: Standard Serral 빌드 오더: 16앞마당-18가스-17산란못

        # 1. 앞마당 (Natural Expansion) - 최우선 (MEDIUM 맵만) - Use learned parameter
        medium_map_expansion_supply = get_learned_parameter("medium_map_expansion_supply", 16)

        if (
            map_size == "MEDIUM"
            and b.supply_used >= medium_map_expansion_supply
            and len(townhalls) < 2
        ):
            # 이미 확장 중이면 대기
            if b.already_pending(UnitTypeId.HATCHERY) == 0:
                if b.can_afford(UnitTypeId.HATCHERY):
                    try:
                        await b.expand_now()
                        print(
                            f"[BUILD ORDER] [{int(b.time)}s] 16 Supply: Natural Expansion (Serral Build)"
                        )
                    except Exception as e:
                        # 확장 실패는 조용히 처리 (다음 프레임에 재시도)
                        pass

        # 2. 가스 (Extractor) - 앞마당 완성 후 - Use learned parameter
        # 앞마당이 완성되었는지 확인 (2개 이상의 타운홀 또는 앞마당 건설 중)
        gas_extraction_supply = get_learned_parameter("gas_extraction_supply", 18)

        if b.supply_used >= gas_extraction_supply:
            # 앞마당이 완성되었거나 건설 중이면 가스 건설
            if len(townhalls) >= 2 or b.already_pending(UnitTypeId.HATCHERY) > 0:
                spawning_pools = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure
                    )
                )
                extractors = list(
                    b.units.filter(lambda u: u.type_id == UnitTypeId.EXTRACTOR and u.is_structure)
                )

                # 산란못이 없고 가스도 없을 때만 가스 건설 (Serral 빌드: 가스가 먼저)
                # CRITICAL: Don't build extractor if workers are critically low (Priority Zero)
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_workers is not None:
                    worker_count = (
                        intel.cached_workers.amount
                        if hasattr(intel.cached_workers, "amount")
                        else len(list(intel.cached_workers))
                    )
                else:
                    worker_count = (
                        b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
                    )
                if not spawning_pools and len(extractors) == 0:
                    if self._can_build_safely(UnitTypeId.EXTRACTOR, reserve_on_pass=True):
                        # Priority Zero: Don't build extractor if workers < 12 (prevent worker loss)
                        if worker_count >= 12 and b.can_afford(UnitTypeId.EXTRACTOR):
                            try:
                                # 가장 가까운 가스 지점 찾기
                                if hasattr(b, "vespene_geyser"):
                                    vgs = [vg for vg in b.vespene_geyser]
                                else:
                                    try:
                                        map_vespene = getattr(b.game_info, "map_vespene", [])
                                        vgs = [vg for vg in map_vespene] if map_vespene else []
                                    except (AttributeError, TypeError):
                                        vgs = []

                                if vgs and townhalls:
                                    # 본진 근처 가스 우선
                                    if len(townhalls) > 0:
                                        closest_vg = min(
                                            vgs,
                                            key=lambda vg: townhalls[0].distance_to(vg),
                                        )
                                        # 🚀 성능 최적화: IntelManager 캐시 사용
                                        if intel and intel.cached_workers is not None:
                                            workers = (
                                                list(intel.cached_workers)
                                                if intel.cached_workers.exists
                                                else []
                                            )
                                        else:
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
                                # 가스 건설 실패는 조용히 처리
                                pass

        # 3. 산란못 (Spawning Pool) - FALLBACK 로직: 12 supply 이상이고 Spawning Pool이 없으면 무조건 건설
        # CRITICAL: 이 로직은 _execute_early_build_order()가 실패했을 때의 안전장치
        # 🚀 성능 최적화: b.structures 사용
        spawning_pools_existing = list(b.structures(UnitTypeId.SPAWNINGPOOL))
        pending_count = b.already_pending(UnitTypeId.SPAWNINGPOOL)
        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_workers is not None:
            worker_count = (
                intel.cached_workers.amount
                if hasattr(intel.cached_workers, "amount")
                else len(list(intel.cached_workers))
            )
        else:
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

        # FALLBACK: 12 supply 이상이고 Spawning Pool 없으면 무조건 건설 (치명적 버그 방지)
        # 이 로직은 _execute_early_build_order()가 뭔가 이유로 실패했을 때의 최후 보루
        fallback_pool_threshold = 12
        if b.supply_used >= fallback_pool_threshold:
            # 미네랄이 충분하고 Worker가 충분하면 바로 건설
            if b.can_afford(UnitTypeId.SPAWNINGPOOL) and worker_count >= 10:
                try:
                    hatchery = (
                        b.townhalls.ready.random if b.townhalls.ready.exists else (b.townhalls.first if b.townhalls.exists else None)
                    )
                    if hatchery:
                        self.spawning_pool_building = True
                        self.last_spawning_pool_check = current_iteration

                        worker = None
                        try:
                            worker = b.select_build_worker(hatchery.position)
                        except Exception:
                            worker = None

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

                            # Chat message only once per build attempt
                            if current_iteration % 224 == 0:
                                await b.chat_send(
                                    "🏗️ [자율 판단] 산란못 건설을 시작합니다."
                                )

                            print(
                                f"[BUILD ORDER] [{int(b.time)}s] Spawning Pool started at supply {int(b.supply_used)}"
                            )
                    except Exception:
                        # Reset flag on error
                        self.spawning_pool_building = False
                        pass

    # 4-1️⃣ 점막 확산 (Creep Spread)
    async def _spread_creep(self):
        """
        점막 확산: 여왕들이 에너지가 남으면 기지 주변에 점막 종양(Creep Tumor)을 깔도록

        Serral 스타일: 점막 확산으로 이동 속도 향상 및 시야 확보
        """
        b = self.bot

        # 🚀 성능 최적화: IntelManager 캐시 사용
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

        # 기존 점막 종양 확인
        existing_tumors = list(
            b.units.filter(lambda u: u.type_id == UnitTypeId.CREEPTUMOR and u.is_ready)
        )

        for queen in queens:
            # 에너지 25 이상이고 Inject Larva를 사용할 수 없을 때만 점막 확산
            if queen.energy < 25:
                continue

            # Inject Larva 우선 (에너지 25 이상이고 부화장이 있으면)
            ready_townhalls = [th for th in townhalls if th.is_ready]
            can_inject = False
            for th in ready_townhalls:
                if queen.distance_to(th) < 5:
                    can_inject = True
                    break

            # Inject를 할 수 없고 에너지가 25 이상이면 점막 확산
            # Enhanced creep spread for ladder play - more aggressive spreading
            if not can_inject and queen.energy >= 25:
                # 가장 가까운 부화장 근처에 점막 종양 생성
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

                # 점막 종양 생성 위치 (부화장에서 약간 떨어진 곳, 맵 중앙 방향)
                try:
                    map_center = b.game_info.map_center
                    spread_pos = closest_hatch.position.towards(
                        map_center, 10
                    )  # Increased from 8 to 10

                    # 점막 종양 생성
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

    # 1️⃣ 일꾼 자동 배분
    async def _distribute_workers(self):
        """
        일꾼을 미네랄/가스에 최적 배분

        sc2 내장 함수 distribute_workers()를 사용하되,
        가스 건물 완공 직후 일꾼 3명을 수동 지정하는 로직 추가

        🛡️ 안전장치: townhalls나 workers가 없으면 조용히 리턴
        🚀 성능 최적화: IntelManager 캐시 사용
        """
        b = self.bot

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_townhalls is not None and intel.cached_workers is not None:
            townhalls = intel.cached_townhalls
            workers = intel.cached_workers
            if not townhalls.exists or not workers.exists:
                return
        else:
            # 🛡️ 안전장치: townhalls나 workers가 없으면 리턴
            try:
                if not b.townhalls.exists or not b.workers.exists:
                    return
            except Exception:
                return
            townhalls = b.townhalls
            workers = b.workers

        try:
            # 기본 배분
            await b.distribute_workers()
        except Exception as e:
            # Worker distribution 실패 시 조용히 무시 (게임 중단 방지)
            if getattr(b, "iteration", 0) % 100 == 0:
                print(f"[WARNING] distribute_workers() 오류: {e}")
            return

        try:
            # 가스 건물 완공 직후 일꾼 수동 배치 (완공된 익스트랙터만)
            # OPTIMIZED: Use structures() instead of filter() for better performance
            extractors = b.structures(UnitTypeId.EXTRACTOR).ready
            # OPTIMIZED: Process only first 5 extractors (no need to iterate all)
            for extractor in list(extractors)[:5]:
                # 가스에 일꾼이 3명 미만이면 추가 배치
                if extractor.assigned_harvesters < self.config.WORKERS_PER_GAS:
                    # 🚀 성능 최적화: IntelManager 캐시 사용
                    if intel and intel.cached_workers is not None:
                        nearby_workers = intel.cached_workers.closer_than(20, extractor.position)
                    else:
                        nearby_workers = b.workers.closer_than(20, extractor.position)
                    if nearby_workers.exists:
                        # OPTIMIZED: Use first available worker (no need to find min)
                        worker = nearby_workers.first
                        if worker:
                            try:
                                worker.gather(extractor)
                            except Exception:
                                pass
        except Exception:
            # 가스 일꾼 배치 실패 시 조용히 무시
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

        # 1. 본진 근처 자원 지대는 높은 가치
        if b.townhalls.exists:
            closest_base = b.townhalls.closest_to(position)
            distance_to_base = position.distance_to(closest_base.position)

            if distance_to_base < 15:
                value += 100.0  # 본진 근처 자원 지대는 매우 높은 가치
            elif distance_to_base < 30:
                value += 50.0
            else:
                value -= 20.0  # 본진에서 멀면 가치 하락

        # 2. 적 기지 근처는 매우 낮은 가치 (위험)
        if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
            enemy_base = b.enemy_start_locations[0]
            distance_to_enemy = position.distance_to(enemy_base)

            if distance_to_enemy < 80:
                value -= 100.0  # 적 기지 근처는 매우 낮은 가치
            elif distance_to_enemy < 100:
                value -= 50.0

        # 3. 미네랄 필드 근처는 높은 가치
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

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_townhalls is not None and intel.cached_workers is not None:
            townhalls = intel.cached_townhalls
            workers = intel.cached_workers
            if not townhalls.exists or not workers.exists:
                return
        else:
            # 안전장치: townhalls나 workers가 없으면 리턴
            try:
                if not b.townhalls.exists or not b.workers.exists:
                    return
            except Exception:
                return
            townhalls = b.townhalls
            workers = b.workers

        try:
            # 적 기지 위치 확인
            enemy_base = None
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                enemy_base = b.enemy_start_locations[0]

            if not enemy_base:
                return

            # 본진 위치 확인
            main_base = (
                townhalls.first
                if hasattr(townhalls, "first")
                else (list(townhalls)[0] if townhalls.exists else None)
            )
            if not main_base:
                return

            # 모든 일꾼 검사
            for drone in workers:
                try:
                    # 건물 건설 중인 일꾼은 제외 (건설 작업 유지)
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

                    # 현재 위치의 가치 평가
                    current_location_value = self._calculate_location_value(drone.position)

                    # 목표 위치의 가치 평가 (가장 가까운 미네랄 필드)
                    target_location = None
                    if b.mineral_field.exists:
                        target_location = b.mineral_field.closest_to(main_base.position).position

                    if target_location:
                        target_location_value = self._calculate_location_value(target_location)

                        # 가치가 낮은 위치에 있으면 가치가 높은 위치로 이동
                        if current_location_value < target_location_value:
                            # 일꾼이 스스로 "더 가치 있는 곳으로 가야겠다"고 판단
                            minerals_near_base = b.mineral_field.closer_than(15, main_base.position)
                            if minerals_near_base.exists:
                                drone.gather(minerals_near_base.random)
                            else:
                                drone.move(main_base.position)

                    # 자원 채취 중이 아니면 자원 채취 명령
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

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_townhalls is not None and intel.cached_workers is not None:
            townhalls = intel.cached_townhalls
            workers = intel.cached_workers
            if not townhalls.exists or not workers.exists:
                return
        else:
            # 안전장치: townhalls나 workers가 없으면 리턴
            try:
                if not b.townhalls.exists or not b.workers.exists:
                    return
            except Exception:
                return
            townhalls = b.townhalls
            workers = b.workers

        try:
            # 적 기지 위치 확인
            enemy_base = None
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                enemy_base = b.enemy_start_locations[0]

            if not enemy_base:
                return

            # 본진 위치 확인
            main_base = (
                townhalls.first
                if hasattr(townhalls, "first")
                else (list(townhalls)[0] if townhalls.exists else None)
            )
            if not main_base:
                return

            # 모든 일꾼 검사
            for drone in workers:
                try:
                    # 건물 건설 중인 일꾼은 제외 (건설 작업 유지)
                    is_constructing = False
                    if hasattr(drone, "orders") and drone.orders:
                        for order in drone.orders:
                            # 건물 건설 명령인지 확인
                            if hasattr(order, "ability") and order.ability:
                                ability_name = str(order.ability).upper()
                                if "BUILD" in ability_name or "CONSTRUCT" in ability_name:
                                    is_constructing = True
                                    break

                    # 건설 중인 일꾼은 제외
                    if is_constructing:
                        continue

                    # 1. 일꾼이 공격 명령을 받았는지 확인
                    is_attacking = False
                    if hasattr(drone, "orders") and drone.orders:
                        for order in drone.orders:
                            if hasattr(order, "ability") and order.ability:
                                ability_name = str(order.ability).upper()
                                if "ATTACK" in ability_name:
                                    is_attacking = True
                                    break

                    # 2. 일꾼이 적 기지 근처에 있는지 확인 (거리 80 이하로 강화)
                    distance_to_enemy = drone.distance_to(enemy_base)
                    is_near_enemy_base = distance_to_enemy < 80.0

                    # 3. 일꾼이 자원 채취 중인지 확인
                    is_gathering = (
                        drone.is_gathering
                        or drone.is_carrying_minerals
                        or drone.is_carrying_vespene
                    )

                    # 4. 일꾼이 본진에서 멀리 떨어져 있는지 확인
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
                        # 가장 가까운 본진 미네랄 필드로 복귀 (즉시 명령)
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
                            # 🚀 성능 최적화: IntelManager 캐시 사용
                            if intel and intel.cached_workers is not None:
                                gathering_workers = sum(
                                    1
                                    for w in intel.cached_workers
                                    if w.is_gathering or w.is_carrying_minerals
                                )
                                total_workers = (
                                    intel.cached_workers.amount
                                    if hasattr(intel.cached_workers, "amount")
                                    else len(list(intel.cached_workers))
                                )
                            else:
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
                            # 미네랄 필드가 없으면 본진으로 이동
                            drone.move(main_base.position)

                except Exception:
                    # 개별 일꾼 처리 오류 시 다음 일꾼으로
                    continue

        except Exception:
            # 전체 로직 오류 시 조용히 무시 (게임 중단 방지)
            pass

    # 1-0️⃣ 자율적 일꾼 행동 (Autonomous Worker Behavior)
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

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_townhalls is not None and intel.cached_workers is not None:
            townhalls = intel.cached_townhalls
            workers = intel.cached_workers
            if not townhalls.exists or not workers.exists:
                return
        else:
            # 안전장치: townhalls나 workers가 없으면 리턴
            try:
                if not b.townhalls.exists or not b.workers.exists:
                    return
            except Exception:
                return
            townhalls = b.townhalls
            workers = b.workers

        try:
            # 본진 위치 확인
            main_base = (
                townhalls.first
                if hasattr(townhalls, "first")
                else (list(townhalls)[0] if townhalls.exists else None)
            )
            if not main_base:
                return

            # 1. 할 일이 없는(Idle) 일꾼: 스스로 가장 가까운 미네랄을 찾아감
            # 🚀 성능 최적화: IntelManager 캐시 사용
            idle_workers = [w for w in workers if w.is_idle]
            current_iteration = getattr(b, "iteration", 0)
            idle_count = len(idle_workers)

            if idle_count > 0:
                # 10초마다 일꾼 상태를 채팅으로 보고
                if current_iteration % 224 == 0:
                    await b.chat_send(
                        f"🏠 할 일이 없는 일꾼 {idle_count}기 발견. 본진 자원 지대로 자율 복귀 중..."
                    )

            for drone in idle_workers:
                try:
                    # 건물 건설 중인 일꾼은 제외
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

                    # 가장 가까운 미네랄 필드로 자율적 이동 (본능)
                    if b.mineral_field.exists:
                        closest_mineral = b.mineral_field.closest_to(drone.position)
                        if closest_mineral:
                            drone.gather(closest_mineral)
                except Exception:
                    continue

            # 2. 본진에서 너무 멀어진 일꾼: 스스로 본진 자원 지대로 복귀
            # 🚀 성능 최적화: IntelManager 캐시 사용
            for drone in workers:
                try:
                    # 건물 건설 중인 일꾼은 제외
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

                    # 본진에서 멀리 떨어진 일꾼 감지
                    distance_to_base = drone.distance_to(main_base.position)
                    if distance_to_base > 30.0:
                        # 자원 채취 중이 아니면 본진 자원 지대로 복귀
                        if not (
                            drone.is_gathering
                            or drone.is_carrying_minerals
                            or drone.is_carrying_vespene
                        ):
                            # 봇이 자신의 판단을 채팅으로 설명 (성격 반영)
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

            # 3. 자율적 가스/미네랄 균형: 가스 추출장에 일꾼이 부족하면 미네랄에서 데려오고, 넘치면 다시 미네랄로
            if b.structures(UnitTypeId.EXTRACTOR).exists:
                for extractor in b.structures(UnitTypeId.EXTRACTOR).ready:
                    try:
                        # 가스 추출장에 할당된 일꾼 수 확인
                        # 🚀 성능 최적화: IntelManager 캐시 사용
                        if intel and intel.cached_workers is not None:
                            workers_on_gas = [
                                w
                                for w in intel.cached_workers
                                if hasattr(w, "order_target") and w.order_target == extractor.tag
                            ]
                            mineral_workers = [
                                w
                                for w in intel.cached_workers
                                if w.is_gathering and w.is_carrying_minerals
                            ]
                        else:
                            workers_on_gas = [
                                w
                                for w in b.workers
                                if hasattr(w, "order_target") and w.order_target == extractor.tag
                            ]
                            mineral_workers = [
                                w for w in b.workers if w.is_gathering and w.is_carrying_minerals
                            ]
                        worker_count_on_gas = len(workers_on_gas)

                        # 가스 추출장에 일꾼이 부족하면 (3명 미만) 미네랄에서 데려옴
                        if worker_count_on_gas < 3:
                            # 가장 가까운 미네랄 일꾼 찾기
                            if mineral_workers:
                                closest_mineral_worker = min(
                                    mineral_workers,
                                    key=lambda w: w.distance_to(extractor),
                                )
                                closest_mineral_worker.gather(extractor)

                        # 가스 추출장에 일꾼이 넘치면 (4명 이상) 미네랄로 보냄
                        elif worker_count_on_gas > 3:
                            excess_workers = workers_on_gas[3:]  # 3명만 남기고 나머지는 미네랄로
                            for worker in excess_workers:
                                if b.mineral_field.exists:
                                    closest_mineral = b.mineral_field.closest_to(main_base.position)
                                    if closest_mineral:
                                        worker.gather(closest_mineral)
                    except Exception:
                        continue

        except Exception:
            # 전체 로직 오류 시 조용히 무시 (게임 중단 방지)
            pass

    # 2️⃣ 가스 조절 (발업 후 미네랄 전환)
    async def _manage_gas_workers(self):
        """
        가스 조절 - 발업 완료 후 일시적으로 가스 일꾼을 미네랄로 전환

        💡 효과:
            초반 저글링 물량 확보를 위해 가스 대신 미네랄 채취 집중
            테크 속도를 20~30초 앞당길 수 있음
        """
        b = self.bot

        # 발업(저글링 속도) 완료 체크
        if b.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) == 0:
            if UpgradeId.ZERGLINGMOVEMENTSPEED in b.state.upgrades:
                if not self.speed_upgrade_done:
                    self.speed_upgrade_done = True
                    print(f"[UPGRADE] [{int(b.time)}초] 발업 완료! 가스 일꾼 조절 시작")

        # 발업 완료 후 3분까지 가스 일꾼 줄이기 (완공된 익스트랙터만)
        if self.speed_upgrade_done and b.time < 180:
            if not self.gas_workers_reduced:
                # 🚀 성능 최적화: b.structures 사용
                ready_extractors = list(b.structures(UnitTypeId.EXTRACTOR).ready)
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if (
                    intel
                    and intel.cached_workers is not None
                    and intel.cached_townhalls is not None
                ):
                    workers = intel.cached_workers
                    townhalls_list = (
                        list(intel.cached_townhalls) if intel.cached_townhalls.exists else []
                    )
                else:
                    workers = b.workers
                    townhalls_list = [th for th in b.townhalls]

                for extractor in ready_extractors:
                    # 가스 일꾼을 1명만 남기고 미네랄로
                    workers_on_gas = [
                        w
                        for w in workers
                        if hasattr(w, "order_target") and w.order_target == extractor.tag
                    ]
                    for i, worker in enumerate(workers_on_gas):
                        if i >= 1:  # 1명만 남기기
                            # 가장 가까운 미네랄로 이동
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

        # 3분 이후 가스 일꾼 복구
        if b.time >= 180 and self.gas_workers_reduced:
            self.gas_workers_reduced = False
            print(f"[GAS] [{int(b.time)}초] 가스 일꾼 복구")

    # 3️⃣ 산란못 유지 및 재건설 (회복력)
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
            # 🚀 성능 최적화: b.structures 사용
            spawning_pools_existing = list(b.structures(UnitTypeId.SPAWNINGPOOL))
            pending_count = b.already_pending(UnitTypeId.SPAWNINGPOOL)
            # 🚀 성능 최적화: IntelManager 캐시 사용
            intel = getattr(b, "intel", None)
            if intel and intel.cached_workers is not None:
                worker_count = (
                    intel.cached_workers.amount
                    if hasattr(intel.cached_workers, "amount")
                    else len(list(intel.cached_workers))
                )
            else:
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
                # 🚨 CRITICAL: Spawning Pool은 게임 진행 필수이므로 worker 제한 완화
                # 최소 5명의 worker만 있으면 건설 허가 (충분한 여유)
                # 자원도 최소 150 이상이면 건설 (200-50 여유)
                is_early_game = b.time < 120  # 2분 이내
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

                            # Chat message only once per build attempt
                            if current_iteration % 224 == 0:
                                await b.chat_send(
                                    "[AUTONOMY] Rebuilding Spawning Pool. If already building, skip."
                                )
                            # Skip verbose logging here to avoid spam
        except Exception as e:
            # Reset flag on error
            self.spawning_pool_building = False
            # 에러 발생 시 로그만 출력 (게임 중단 방지)
            if getattr(b, "iteration", 0) % 50 == 0:
                print(f"[ERROR] _maintain_spawning_pool 오류: {e}")

    # 4️⃣ 여왕 펌핑 (Inject Larva)
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

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_queens is not None:
            queens = intel.cached_queens
        else:
            queens = b.units(UnitTypeId.QUEEN)
        for queen in queens:
            # 에너지 25 이상, 유휴 또는 이동 중인 여왕만
            if queen.energy < 25:
                continue

            # Allow queens that are idle OR moving to inject (improves responsiveness)
            if not (queen.is_idle or queen.is_moving):
                continue

            # 가장 가까운 부화장에 펌핑
            if not ready_townhalls:
                continue

            # Check if hatchery already has inject buff (avoid duplicate inject)
            closest_hatch = min(ready_townhalls, key=lambda th: queen.distance_to(th))

            # Inject larva (에너지 25가 모일 때마다 수행)
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

    # 5️⃣ 가스 건물 관리 (멀티 가스 자동 건설)
    async def _manage_gas_buildings(self):
        """
        멀티 가스 자동 건설 로직

        모든 완성된 부화장 근처의 가스 간헐천을 확인하여
        가스통이 없는 곳에 자동으로 건설합니다.
        """
        b = self.bot

        # 산란못이 있어야 가스 건설
        # 🚀 성능 최적화: b.structures 사용
        spawning_pools = list(b.structures(UnitTypeId.SPAWNINGPOOL))
        if not spawning_pools:
            return

        # CRITICAL: Priority Zero - Don't build extractors if workers are critically low
        # This prevents wasting workers on extractors when economy is collapsing
        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_workers is not None:
            worker_count = (
                intel.cached_workers.amount
                if hasattr(intel.cached_workers, "amount")
                else len(list(intel.cached_workers))
            )
        else:
            worker_count = (
                b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
            )
        if worker_count < 12:
            return

        # Use safe build check to prevent duplicates
        if not self._can_build_safely(UnitTypeId.EXTRACTOR, reserve_on_pass=True):
            return

        # 자원 체크
        if not b.can_afford(UnitTypeId.EXTRACTOR):
            return

        # 건설 중인 가스통이 너무 많으면 대기 (max 2 simultaneous)
        if b.already_pending(UnitTypeId.EXTRACTOR) >= 2:
            return

        # 1. 모든 완성된 부화장(Hatchery/Lair/Hive)을 순회
        ready_townhalls = b.townhalls.ready
        if not ready_townhalls.exists:
            return

        for hatchery in ready_townhalls:
            # 2. 해당 부화장 근처(거리 15 이내)의 가스 간헐천(Vespene Geyser) 찾기
            try:
                vgs = b.vespene_geyser.closer_than(15, hatchery)
            except (AttributeError, TypeError):
                # vespene_geyser 속성이 없으면 game_info에서 가져오기
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
                # 3. 해당 간헐천에 이미 가스통(Extractor)이 있는지 확인
                nearby_extractors = b.structures(UnitTypeId.EXTRACTOR).closer_than(1, vg)
                if nearby_extractors.exists:
                    continue

                # 4. 건설 중인 가스통도 체크
                if b.already_pending(UnitTypeId.EXTRACTOR) >= 2:
                    return

                # 5. 일벌레 한 마리를 선택해 건설 명령
                nearby_workers = b.workers.closer_than(20, vg)
                if nearby_workers.exists:
                    worker = nearby_workers.closest_to(vg)
                    try:
                        worker.build(UnitTypeId.EXTRACTOR, vg)
                        return  # 한 번에 하나씩만 건설
                    except Exception:
                        continue

    # 6️⃣ 테크 건물 건설
    async def _build_tech_buildings(self):
        """테크 건물 자동 건설"""
        b = self.bot
        if not b.townhalls.exists:
            return
        townhalls = [th for th in b.townhalls]
        if not townhalls:
            return
        hatchery = townhalls[0]

        # [NEW] Lair 변태 (180초 이후, 미네랄/가스 충분) - 다른 테크의 선행조건!
        lairs = list(
            b.units.filter(
                lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure
            )
        )
        if not lairs and b.time > 180 and b.can_afford(UnitTypeId.LAIR):
            hatcheries_ready = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.HATCHERY and u.is_structure and u.is_ready
                )
            )
            if hatcheries_ready:
                try:
                    await hatcheries_ready[0].morph(UnitTypeId.LAIR)
                    print(f"[BUILD] [{int(b.time)}s] Lair morph started (tech prerequisite)")
                except Exception as e:
                    print(f"[WARNING] Lair morph failed: {e}")

        # 로치 워렌 (3분 이후) - 존재/펜딩 검사로 중복 건설 방지
        if b.time > self.config.ROACH_WARREN_TIME:
            if b.structures(UnitTypeId.ROACHWARREN).exists or b.already_pending(UnitTypeId.ROACHWARREN) > 0:
                pass
            elif self._can_build_safely(UnitTypeId.ROACHWARREN, reserve_on_pass=True):
                if b.can_afford(UnitTypeId.ROACHWARREN):
                    # Use safe placement with spacing to prevent SimCity bottleneck
                    build_pos = await self._find_safe_building_placement(
                        UnitTypeId.ROACHWARREN, hatchery.position, placement_step=5
                    )
                    if build_pos:
                        await b.build(UnitTypeId.ROACHWARREN, build_pos)
                    else:
                        await b.build(UnitTypeId.ROACHWARREN, near=hatchery)
                    print(f"[BUILD] [{int(b.time)}초] 로치 워렌 건설")

        # tech_to_hydra: 히드라 덴 (중반 이후, 레어 필요)
        # 6분 이후 또는 중반 단계 이후
        if b.time > 360:  # 6분 이후
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
                if b.structures(UnitTypeId.HYDRALISKDEN).exists or b.already_pending(UnitTypeId.HYDRALISKDEN) > 0:
                    pass
                elif self._can_build_safely(UnitTypeId.HYDRALISKDEN, reserve_on_pass=True):
                    if b.can_afford(UnitTypeId.HYDRALISKDEN):
                        # Use safe placement with spacing to prevent SimCity bottleneck
                        build_pos = await self._find_safe_building_placement(
                            UnitTypeId.HYDRALISKDEN, hatchery.position, placement_step=5
                        )
                        if build_pos:
                            await b.build(UnitTypeId.HYDRALISKDEN, build_pos)
                        else:
                            await b.build(UnitTypeId.HYDRALISKDEN, near=hatchery)
                        print(f"[BUILD] [{int(b.time)}s] Hydralisk Den built")

                # Lurker Den (Serral build: after Hydralisk Den)
                hydra_dens_ready = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.HYDRALISKDEN
                        and u.is_structure
                        and u.is_ready
                    )
                )
                if hydra_dens_ready:
                    lurker_den_exists_or_pending = (
                        b.structures(UnitTypeId.LURKERDEN).exists
                        or b.already_pending(UnitTypeId.LURKERDEN) > 0
                    )
                    if not lurker_den_exists_or_pending:
                        if self._can_build_safely(UnitTypeId.LURKERDEN, reserve_on_pass=True):
                            if b.can_afford(UnitTypeId.LURKERDEN):
                                # Morph Hydralisk Den to Lurker Den
                                hydra_den = hydra_dens_ready[0]
                                if hydra_den.is_ready:
                                    hydra_den(AbilityId.BUILD_LURKERDEN)
                                    print(f"[BUILD] [{int(b.time)}s] Lurker Den morphing")

        # 진화 챔버 (4분 이후) - 존재/펜딩 검사로 중복 건설 방지
        if b.time > 240:
            if b.structures(UnitTypeId.EVOLUTIONCHAMBER).exists or b.already_pending(UnitTypeId.EVOLUTIONCHAMBER) > 0:
                pass
            elif self._can_build_safely(UnitTypeId.EVOLUTIONCHAMBER, reserve_on_pass=True):
                if b.can_afford(UnitTypeId.EVOLUTIONCHAMBER):
                    # Use safe placement with spacing to prevent SimCity bottleneck
                    build_pos = await self._find_safe_building_placement(
                        UnitTypeId.EVOLUTIONCHAMBER, hatchery.position, placement_step=5
                    )
                    if build_pos:
                        await b.build(UnitTypeId.EVOLUTIONCHAMBER, build_pos)
                    else:
                        await b.build(UnitTypeId.EVOLUTIONCHAMBER, near=hatchery)
                    print(f"[BUILD] [{int(b.time)}s] Evolution Chamber built")

        # 스파이어 (Spire) - 공중 유닛을 위한 필수 테크 건물
        # 7분 이후 + 레어 존재 시 건설
        if b.time > 420:  # 7분 이후
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
                        # Use safe placement with spacing to prevent SimCity bottleneck
                        build_pos = await self._find_safe_building_placement(
                            UnitTypeId.SPIRE, hatchery.position, placement_step=5
                        )
                        if build_pos:
                            await b.build(UnitTypeId.SPIRE, build_pos)
                        else:
                            await b.build(UnitTypeId.SPIRE, near=hatchery)
                        print(f"[BUILD] [{int(b.time)}s] Spire built (Air Force activated)")

    # 7️⃣ 테크 업그레이드 (레어, 하이브)
    async def _upgrade_tech(self):
        """
        레어/하이브 업그레이드

        💡 안전한 API 호출:
            hatch(AbilityId.UPGRADETOLAIR_LAIR)
        """
        b = self.bot

        # 레어 업그레이드 (5분 이후)
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

        # 최종 테크 트리: 군락(Hive) 업그레이드 및 최종 병기 건물
        await self._build_ultimate_tech()

    # 7-1️⃣ 최종 테크 트리 자동 건설 (군락, 울트라리스크 동굴, 거대 둥지탑)
    async def _build_ultimate_tech(self):
        """
        최종 테크 트리 자동 건설

        감염 구덩이 -> 군락 -> 울트라리스크 동굴 / 거대 둥지탑
        """
        b = self.bot

        townhalls = b.townhalls
        if not townhalls.exists:
            return

        # 1. 감염 구덩이(Infestation Pit) 건설 (군락으로 가기 위한 선행)
        lairs = b.structures(UnitTypeId.LAIR).ready
        if lairs.exists:
            infestation_pits = b.structures(UnitTypeId.INFESTATIONPIT)
            pending_pits = b.already_pending(UnitTypeId.INFESTATIONPIT)
            if not infestation_pits.exists and pending_pits == 0:
                if self._can_build_safely(UnitTypeId.INFESTATIONPIT, reserve_on_pass=True):
                    if b.can_afford(UnitTypeId.INFESTATIONPIT):
                        try:
                            await b.build(UnitTypeId.INFESTATIONPIT, near=townhalls.random)
                            print(f"[BUILD] [{int(b.time)}s] Infestation Pit built (Hive prerequisite)")
                        except Exception:
                            pass

        # 2. 군락(Hive) 업그레이드
        infestation_pits_ready = b.structures(UnitTypeId.INFESTATIONPIT).ready
        if lairs.exists and infestation_pits_ready.exists:
            hives = b.structures(UnitTypeId.HIVE)
            if not hives.exists:
                if b.can_afford(UnitTypeId.HIVE):
                    try:
                        lairs.random(AbilityId.UPGRADETOHIVE_HIVE)
                    except Exception:
                        pass

        # 3. 최종 병기 건물 건설 (군락 완성 후)
        hives_ready = b.structures(UnitTypeId.HIVE).ready
        if hives_ready.exists:
            # 울트라리스크 동굴 (Ultralisk Cavern)
            ultralisk_caverns = b.structures(UnitTypeId.ULTRALISKCAVERN)
            if not ultralisk_caverns.exists and not b.already_pending(UnitTypeId.ULTRALISKCAVERN):
                if b.can_afford(UnitTypeId.ULTRALISKCAVERN):
                    try:
                        await b.build(UnitTypeId.ULTRALISKCAVERN, near=townhalls.random)
                    except Exception:
                        pass

            # 거대 둥지탑 (Great Spire - 무리 군주용)
            spires = b.structures(UnitTypeId.SPIRE).ready
            # Fix: UnitTypeId.GREAT_SPIRE -> UnitTypeId.GREATERSPIRE (correct SC2 API naming)
            great_spires = b.structures(UnitTypeId.GREATERSPIRE)
            if spires.exists and not great_spires.exists:
                if b.can_afford(UnitTypeId.GREATERSPIRE):
                    try:
                        # Fix: AbilityId should use correct naming for Greater Spire upgrade
                        spires.random(AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE)
                    except Exception:
                        pass

    # 7-2️⃣ 자원 소모 최적화 (Macro Hatchery & Resource Flush)
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
            # 🚀 성능 최적화: IntelManager 캐시 사용
            intel = getattr(b, "intel", None)
            if intel and intel.cached_townhalls is not None:
                townhalls = list(intel.cached_townhalls) if intel.cached_townhalls.exists else []
                if not townhalls:
                    return
            else:
                if not b.townhalls.exists:
                    return
                townhalls = [th for th in b.townhalls]

            # 🚀 성능 최적화: IntelManager 캐시 사용
            if intel and intel.cached_workers is not None:
                worker_count = (
                    intel.cached_workers.amount
                    if hasattr(intel.cached_workers, "amount")
                    else len(list(intel.cached_workers))
                )
            else:
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

    # 8️⃣ 확장 결정
    async def _manage_expansion(self):
        """확장 타이밍 결정 - 멀티(확장 기지) 자동으로 늘리기

        Enhanced for official AI Arena maps:
        - TorchesAIE, PylonAIE, PersephoneAIE, IncorporealAIE,
        - MagannathaAIE, UltraloveAIE, LeyLinesAIE
        """
        b = self.bot

        # 이미 확장 중이면 대기
        if b.already_pending(UnitTypeId.HATCHERY) > 0:
            return

        townhalls = [th for th in b.townhalls]
        current_base_count = len(townhalls)

        # 최대 4개 기지까지 확장
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

        # 적응형 빌드 계획 확인
        build_plan = getattr(b, "current_build_plan", None)
        should_expand_aggressive = build_plan.get("should_expand", False) if build_plan else False

        # 적응형 빌드: 확장 우선 모드면 더 적극적으로 확장
        if should_expand_aggressive:
            if b.minerals >= 250:  # 더 낮은 임계값
                if b.can_afford(UnitTypeId.HATCHERY):
                    try:
                        await b.expand_now()
                        return
                    except Exception:
                        pass

        # Enhanced: More aggressive expansion for ladder play
        # Check worker count and army size before expanding
        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_workers is not None:
            worker_count = (
                intel.cached_workers.amount
                if hasattr(intel.cached_workers, "amount")
                else len(list(intel.cached_workers))
            )
        else:
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
            # 봇이 스스로 판단하여 미네랄이 매우 많을 때 확장 (자율적 판단)
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

        # 자원 체크 (더 적극적으로 확장) - Use learned parameter
        expansion_mineral_minimum = get_learned_parameter("expansion_mineral_minimum", 300)

        if b.minerals < expansion_mineral_minimum:
            return

        # 🛡️ 확장 전 방어 체크 (중요!) - 저글링 8마리 + 여왕 1마리 + 가시촉수 1개
        # 첫 번째 확장(2번째 기지) 전에만 엄격하게 체크
        if current_base_count == 1:
            # 1. 저글링 최소 8마리 체크
            # 🚀 성능 최적화: IntelManager 캐시 사용
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
                return  # 저글링이 부족하면 확장 안 함

            # 2. 여왕 최소 1마리 체크
            if intel and intel.cached_queens is not None:
                queens = intel.cached_queens
                queen_count = queens.amount if hasattr(queens, "amount") else len(list(queens))
            else:
                queens = b.units(UnitTypeId.QUEEN)
                queen_count = queens.amount if hasattr(queens, "amount") else len(list(queens))
            if queen_count < 1:
                return  # 여왕이 없으면 확장 안 함

            # 3. 가시촉수 최소 1개 체크
            # 🚀 성능 최적화: IntelManager 캐시 사용
            if intel and intel.cached_spine_crawlers is not None:
                spine_crawlers = (
                    list(intel.cached_spine_crawlers) if intel.cached_spine_crawlers.exists else []
                )
            else:
                spine_crawlers = list(b.structures(UnitTypeId.SPINECRAWLER))
            if len(spine_crawlers) < 1:
                return  # 가시촉수가 없으면 확장 안 함

        # 두 번째 확장(3번째 기지) 이상일 때는 약간 완화
        elif current_base_count >= 2:
            # 🚀 성능 최적화: IntelManager 캐시 사용
            # intel 변수는 위의 if 블록에서 이미 정의됨
            intel = getattr(b, "intel", None)  # 재정의 (스코프 확보)
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

            # 최소한의 방어 유닛은 있어야 함 (절반 정도)
            if total_defense_units < min_defense // 2:
                return

        # 일꾼 포화도 체크
        workers = [w for w in b.workers]
        current_workers = len(workers)
        optimal_workers = current_base_count * self.config.WORKERS_PER_BASE

        # 확장 조건 (더 적극적으로)
        should_expand = False

        # 조건 1: 일꾼이 충분하면 확장
        if current_workers >= optimal_workers * 0.7:
            should_expand = True

        # 조건 2: 앞마당 멀티 이후 미네랄이 남으면 즉시 세 번째 멀티 시도
        if current_base_count == 2 and b.minerals >= 300:
            should_expand = True

        # 조건 3: 미네랄이 많고 기지가 적으면 확장
        if b.minerals >= 400 and current_base_count < 3:
            should_expand = True

        # 조건 4: 미네랄이 매우 많으면 무조건 확장 (단, 방어 유닛 체크는 통과해야 함)
        if b.minerals >= 600:
            should_expand = True

        # 조건 5: 2분 이후이고 미네랄이 350 이상이면 확장
        if b.time >= 120 and b.minerals >= 350 and current_base_count < 2:
            should_expand = True

        if should_expand:
            if b.can_afford(UnitTypeId.HATCHERY):
                try:
                    await b.expand_now()
                    # 로그는 100 iteration마다만 출력되므로 여기서는 출력 안 함
                except Exception as e:
                    # 확장 실패는 조용히 처리
                    pass

    # 7-1️⃣ 저글링 발업 최우선 연구
    async def _research_zergling_speed(self):
        """
        저글링 발업 (대사 촉진) 최우선 연구

        💡 견제의 핵심:
            가스가 100 모이면 산란못에서 '대사 촉진(Metabolic Boost)' 연구를
            가장 먼저 하도록 설정 (다른 모든 업그레이드보다 우선!)
        """
        b = self.bot

        # 이미 연구 완료했으면 스킵
        if UpgradeId.ZERGLINGMOVEMENTSPEED in b.state.upgrades:
            return

        # 이미 연구 중이면 스킵
        if b.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) > 0:
            return

        # 가스 100 이상 체크 (가장 먼저 체크!)
        if b.vespene < 100:
            return

        # 산란못이 완성되어 있어야 함
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

        # 미네랄 100도 필요하지만, 가스가 100이면 미네랄도 충분할 가능성이 높음
        # 하지만 정확히 체크 - 가스 100이 모이면 즉시 연구!
        if b.minerals >= 100 and b.vespene >= 100:
            pool = ready_idle_pools[0]
            pool.research(UpgradeId.ZERGLINGMOVEMENTSPEED)
            if getattr(b, "iteration", 0) % 50 == 0:
                print(f"[UPGRADE] [{int(b.time)}s] 저글링 발업 연구 시작! (가스 100 달성)")

    # 9️⃣ 업그레이드 연구
    async def _research_upgrades(self):
        """진화 챔버 업그레이드 연구 (저글링 발업은 이미 완료되어야 함)"""
        b = self.bot

        # 진화 챔버 업그레이드
        ready_idle_evos = list(
            b.units.filter(
                lambda u: u.type_id == UnitTypeId.EVOLUTIONCHAMBER
                and u.is_structure
                and u.is_ready
                and u.is_idle
            )
        )
        for evo in ready_idle_evos:
            # 근접 공격력 (Level 1 -> Level 2 -> Level 3 순차 업그레이드)
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

            # 원거리 공격력 (Level 1 -> Level 2 -> Level 3)
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

            # 지상 방어력 (Level 1 -> Level 2 -> Level 3)
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

    # 🛡️ 공중 방어 건물 건설 (각 부화장마다 포자 촉수)
    async def _build_anti_air_structures(self):
        """
        build_anti_air_structures: 각 부화장마다 포자 촉수(Spore Crawler) 1개씩 건설
        여유가 되면 번식지(Lair)로 업그레이드하고 히드라리스크 굴 건설
        밴시나 해방선에 대비
        """
        b = self.bot

        # 모든 부화장 확인 (units.filter 사용)
        townhalls = [th for th in b.townhalls]
        if not townhalls:
            return

        # 1. 각 부화장 옆에 포자 촉수 1개씩 건설
        for hatchery in townhalls:
            # 각 부화장 근처에 포자 촉수가 있는지 체크 (units.filter 사용)
            nearby_spores = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.SPORECRAWLER
                    and u.is_structure
                    and u.distance_to(hatchery) < 15
                )
            )

            # 이미 포자 촉수가 있으면 스킵
            if len(nearby_spores) >= 1:
                continue

            # 이미 건설 중이면 스킵
            if b.already_pending(UnitTypeId.SPORECRAWLER) > 0:
                continue

            # 진화 챔버가 있어야 포자 촉수 건설 가능 (units.filter 사용)
            evolution_chambers = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.EVOLUTIONCHAMBER
                    and u.is_structure
                    and u.is_ready
                )
            )
            if not evolution_chambers:
                continue

            # 자원 체크
            if not b.can_afford(UnitTypeId.SPORECRAWLER):
                continue

            # 부화장 옆에 건설
            build_pos = hatchery.position.towards(b.game_info.map_center, 8)
            try:
                await b.build(UnitTypeId.SPORECRAWLER, near=build_pos)
                # 로그는 100 iteration마다만 출력되므로 여기서는 출력 안 함
            except Exception:
                # 건설 실패는 조용히 처리
                pass

        # 2. 여유가 되면 번식지(Lair)로 업그레이드
        if b.minerals >= 150 and b.vespene >= 100:
            # 부화장이 있고 레어가 없으면 업그레이드
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

            # 레어나 하이브가 없으면 업그레이드
            if hatcheries and not lairs and not hives:
                if b.can_afford(UnitTypeId.LAIR):
                    hatchery = hatcheries[0]
                    hatchery(AbilityId.UPGRADETOLAIR_LAIR)

        # 3. 번식지가 있으면 히드라리스크 굴 건설
        lairs = list(
            b.units.filter(lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure and u.is_ready)
        )
        hives = list(
            b.units.filter(lambda u: u.type_id == UnitTypeId.HIVE and u.is_structure and u.is_ready)
        )

        if lairs or hives:
            # 히드라리스크 굴이 없으면 건설
            hydra_dens = list(
                b.units.filter(lambda u: u.type_id == UnitTypeId.HYDRALISKDEN and u.is_structure)
            )

            if not hydra_dens:
                if b.already_pending(UnitTypeId.HYDRALISKDEN) == 0:
                    if b.can_afford(UnitTypeId.HYDRALISKDEN):
                        if townhalls and len(townhalls) > 0:
                            await b.build(UnitTypeId.HYDRALISKDEN, near=townhalls[0])
                            # 로그는 100 iteration마다만 출력되므로 여기서는 출력 안 함

    # 🛡️ 초반 가시촉수 건설 (산란못 완성 후)
    async def _build_early_spine_crawler(self):
        """
        산란못 완성 후 본진 근처에 가시촉수 1개 건설
        Enhanced: 적 유닛이 본진 근처에 나타나면 즉시 건설!
        """
        b = self.bot

        # 이미 가시촉수가 있으면 건설 안 함 (단, 적이 근처에 있으면 추가 건설 가능)
        spine_crawlers = list(
            b.units.filter(lambda u: u.type_id == UnitTypeId.SPINECRAWLER and u.is_structure)
        )

        # 성격 기반 방어 건물 건설 우선순위 조절
        min_spine_count = 1  # 기본 최소 개수
        try:
            combat_manager = getattr(b, "combat", None)
            if combat_manager:
                personality = getattr(combat_manager, "personality", "NEUTRAL")
                if personality == "CAUTIOUS":
                    min_spine_count = 2  # 신중함: 더 많은 방어 건물 건설
                elif personality == "AGGRESSIVE":
                    min_spine_count = 1  # 공격적: 최소한의 방어만
        except (AttributeError, TypeError):
            pass

        # 적 유닛이 본진 근처에 있는지 체크 (30 거리 내)
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

        # 적이 근처에 없고 이미 가시촉수가 최소 개수 이상이면 건설 안 함 (성격 반영)
        if not enemy_near_base and len(spine_crawlers) >= min_spine_count:
            return

        # 이미 건설 중이면 대기
        if b.already_pending(UnitTypeId.SPINECRAWLER) > 0:
            return

        # 산란못이 완성되어 있어야 함
        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_spawning_pools is not None:
            spawning_pools = (
                list(intel.cached_spawning_pools) if intel.cached_spawning_pools.exists else []
            )
        else:
            # Fallback: b.structures 사용 (더 빠름)
            spawning_pools = list(b.structures(UnitTypeId.SPAWNINGPOOL).ready)
        if not spawning_pools:
            return

        # 자원 체크
        if not b.can_afford(UnitTypeId.SPINECRAWLER):
            return

        # 본진 근처에 건설
        if not b.townhalls.exists:
            return
        townhalls = [th for th in b.townhalls]
        if townhalls:
            hatchery = townhalls[0]
            # 본진에서 약간 떨어진 위치에 건설 (8 거리)
            build_pos = hatchery.position.towards(b.game_info.map_center, 8)
            try:
                await b.build(UnitTypeId.SPINECRAWLER, near=build_pos)
                if enemy_near_base:
                    print(f"[DEFENSE] [{int(b.time)}s] 적 감지! 가시 촉수 긴급 건설!")
            except Exception:
                # 건설 실패는 조용히 처리
                pass

    # 🛡️ 방어 건물 건설 (러시 대응)
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
                await b.build(UnitTypeId.SPINECRAWLER, near=pos)
                print(f"[DEFENSE] [{int(b.time)}초] 스파인 크롤러 건설 (방어)")

    # 📊 경제 상태 조회
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
