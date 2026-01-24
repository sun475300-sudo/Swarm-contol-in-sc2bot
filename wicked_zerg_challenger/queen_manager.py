# -*- coding: utf-8 -*-
"""
Queen Manager - Unified queen production, injection, and creep control.

Consolidated version combining features from original and improved versions:
- Robust queen production without gas checks (queens cost minerals only)
- Efficient larva injection with cooldown tracking
- Aggressive creep spread with dedicated forward queens
- Better error handling and distance-based reassignment
"""

from typing import Dict, Optional, Set

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:

    class UnitTypeId:
        QUEEN = "QUEEN"
        HATCHERY = "HATCHERY"
        LAIR = "LAIR"
        HIVE = "HIVE"
        SPAWNINGPOOL = "SPAWNINGPOOL"
        CREEPTUMOR = "CREEPTUMOR"
        CREEPTUMORBURROWED = "CREEPTUMORBURROWED"

    class AbilityId:
        EFFECT_INJECTLARVA = "EFFECT_INJECTLARVA"
        BUILD_CREEPTUMOR_QUEEN = "BUILD_CREEPTUMOR_QUEEN"
        TRANSFUSION_TRANSFUSION = "TRANSFUSION_TRANSFUSION"


class QueenManager:
    """
    Unified queen controller for production and support abilities.

    Features:
    - Auto-inject larva on all hatcheries with cooldown tracking
    - Dedicated creep queens for aggressive map control
    - Dynamic queen production based on base count
    - Distance-based queen reassignment for efficiency
    - Robust error handling with iteration-based logging
    """

    def __init__(self, bot):
        """
        Initialize queen manager.

        Args:
            bot: The main bot instance
        """
        self.bot = bot

        # Injection settings
        self.inject_energy_threshold = 25
        self.inject_cooldown = 29.0  # Inject ability cooldown
        self.max_inject_distance = 4.0
        self.max_queen_travel_distance = 10.0

        # Creep settings - ★ 개선: 과도한 확장 방지 ★
        self.creep_energy_threshold = 25
        self.creep_spread_cooldown = 12.0  # ★ 수정: 8초 → 12초 (과도한 확장 방지)
        self.inject_queen_creep_threshold = 50  # ★ 수정: 40 → 50 (인젝트 우선)

        # Queen production - ★ 기지당 2마리 배치 ★
        self.max_queens_per_base = 2  # 개선: 1 → 2 (기지당 2마리)
        self.creep_queen_bonus = 3    # ★ 개선: 2 → 3 (점막 전용 퀸 추가) ★

        # 점막 확장 추적
        self.creep_tumor_count = 0
        self.last_tumor_check = 0

        # Tracking
        self.inject_assignments: Dict[int, int] = {}  # hatchery_tag -> queen_tag
        self.last_inject_time: Dict[int, float] = {}  # hatchery_tag -> time
        self.last_creep_time: Dict[int, float] = {}  # queen_tag -> time
        self.last_transfuse_time: Dict[int, float] = {}  # queen_tag -> time
        self.assigned_queen_tags: Set[int] = set()
        self.dedicated_creep_queens: Set[int] = set()

        # Transfuse settings
        self.transfuse_energy_threshold = 50
        self.transfuse_cooldown = 1.0  # 1 second minimum between transfuses
        self.transfuse_health_threshold = 0.5  # Target health ratio

    async def on_step(self, iteration: int) -> None:
        """
        Main queen management loop.

        Args:
            iteration: Current game iteration
        """
        if not hasattr(self.bot, "time"):
            return

        try:
            await self._train_queens(iteration)

            queens = (
                self.bot.units(UnitTypeId.QUEEN).ready
                if hasattr(self.bot, "units")
                else []
            )
            hatcheries = (
                self.bot.townhalls.ready if hasattr(self.bot, "townhalls") else []
            )

            if not queens or not hatcheries:
                return

            self._assign_queen_roles(queens, hatcheries)

            # === DEFENSE PRIORITY: Check if base is under attack ===
            under_attack = self._is_base_under_attack()

            if under_attack:
                # Defense mode: Queens defend instead of creep spread
                await self._queen_defense_mode(queens, iteration)
            else:
                # Normal mode
                await self._inject_larva(hatcheries, queens)

            # Transfuse injured units (priority over creep spread)
            # Also transfuse Spine Crawlers during defense
            await self._transfuse_injured_units(queens, iteration, include_structures=under_attack)

            # Only spread creep if not under attack
            if not under_attack:
                # Dedicated creep queens
                creep_queens = [q for q in queens if q.tag not in self.assigned_queen_tags]
                await self._spread_creep(creep_queens, iteration)

                # 인젝트 퀸도 에너지 여유 있으면 점막 확장 (개선)
                await self._inject_queens_spread_creep(queens, iteration)

                # ★★★ NEW: 여유 있는 모든 퀸 점막 확장 활용 ★★★
                await self._utilize_idle_queens_for_creep(queens, iteration)

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Queen manager error: {e}")

    async def _train_queens(self, iteration: int) -> None:
        """Train queens based on base count and need."""
        if not hasattr(self.bot, "townhalls"):
            return

        hatcheries = self.bot.townhalls.ready
        if not hatcheries:
            return

        # Check spawning pool
        if hasattr(self.bot, "structures"):
            pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
            if not pools.exists:
                return

        queens = (
            self.bot.units(UnitTypeId.QUEEN).ready
            if hasattr(self.bot, "units")
            else []
        )

        creep_bonus = self.creep_queen_bonus if hatcheries.amount >= 2 else 0
        desired = max(1, hatcheries.amount * self.max_queens_per_base + creep_bonus)

        if len(queens) >= desired:
            return

        pending = (
            self.bot.already_pending(UnitTypeId.QUEEN)
            if hasattr(self.bot, "already_pending")
            else 0
        )

        for hatch in hatcheries:
            if len(queens) + pending >= desired:
                break

            # Check if hatchery is idle
            if hasattr(hatch, "is_idle") and not hatch.is_idle:
                continue
            if hasattr(hatch, "noqueue") and not hatch.noqueue:
                continue

            # Queens cost minerals only - no gas check needed
            if self.bot.minerals < 150:
                break

            # Check supply
            if hasattr(self.bot, "supply_left") and self.bot.supply_left < 2:
                break

            try:
                if await self._safe_train(hatch, UnitTypeId.QUEEN):
                    pending += 1
            except Exception as e:
                if iteration % 200 == 0:
                    print(f"[WARNING] Queen train error: {e}")
                continue

    def _assign_queen_roles(self, queens, hatcheries) -> None:
        """
        Assign queen roles - inject queens and dedicated creep queens.

        ★ 개선: 기지당 2마리 배치 ★
        Priority:
        1. Inject queens (2 per hatchery - 1차/2차 인젝트 퀸)
        2. Dedicated creep queens for map control
        """
        current_queen_tags = {q.tag for q in queens}
        current_hatch_tags = {h.tag for h in hatcheries}

        # Clean up stale assignments
        self.inject_assignments = {
            hatch_tag: queen_tag
            for hatch_tag, queen_tag in self.inject_assignments.items()
            if hatch_tag in current_hatch_tags and queen_tag in current_queen_tags
        }

        self.dedicated_creep_queens = {
            tag for tag in self.dedicated_creep_queens if tag in current_queen_tags
        }

        # ★ 기지당 2마리 배정을 위한 2차 배정 딕셔너리 ★
        if not hasattr(self, 'secondary_inject_assignments'):
            self.secondary_inject_assignments = {}

        self.secondary_inject_assignments = {
            hatch_tag: queen_tag
            for hatch_tag, queen_tag in self.secondary_inject_assignments.items()
            if hatch_tag in current_hatch_tags and queen_tag in current_queen_tags
        }

        # Assign inject queens (1차 - 메인 인젝트)
        assigned_queens = set(self.inject_assignments.values())
        assigned_queens.update(self.secondary_inject_assignments.values())

        for hatch in hatcheries:
            # 1차 인젝트 퀸 배정
            if hatch.tag in self.inject_assignments:
                # Check if assigned queen is too far
                queen_tag = self.inject_assignments[hatch.tag]
                queen = self._find_queen_by_tag(queens, queen_tag)
                if queen:
                    try:
                        dist = queen.distance_to(hatch.position)
                        if dist > self.max_queen_travel_distance:
                            # Reassign if too far
                            del self.inject_assignments[hatch.tag]
                            assigned_queens.discard(queen_tag)
                    except Exception:
                        pass

            if hatch.tag not in self.inject_assignments:
                candidate = self._find_closest_queen(
                    hatch.position, queens, assigned_queens
                )
                if candidate:
                    self.inject_assignments[hatch.tag] = candidate.tag
                    assigned_queens.add(candidate.tag)

        # ★ 2차 인젝트 퀸 배정 (기지당 2마리) ★
        for hatch in hatcheries:
            if hatch.tag in self.secondary_inject_assignments:
                queen_tag = self.secondary_inject_assignments[hatch.tag]
                queen = self._find_queen_by_tag(queens, queen_tag)
                if queen:
                    try:
                        dist = queen.distance_to(hatch.position)
                        if dist > self.max_queen_travel_distance:
                            del self.secondary_inject_assignments[hatch.tag]
                            assigned_queens.discard(queen_tag)
                    except Exception:
                        pass

            if hatch.tag not in self.secondary_inject_assignments:
                candidate = self._find_closest_queen(
                    hatch.position, queens, assigned_queens
                )
                if candidate:
                    self.secondary_inject_assignments[hatch.tag] = candidate.tag
                    assigned_queens.add(candidate.tag)

        # Assign dedicated creep queens
        unassigned = [q for q in queens if q.tag not in assigned_queens]
        target_creep_queens = min(self.creep_queen_bonus, len(unassigned))

        if target_creep_queens > 0 and hasattr(self.bot, "enemy_start_locations"):
            enemy_start = (
                self.bot.enemy_start_locations[0]
                if self.bot.enemy_start_locations
                else None
            )

            if enemy_start and unassigned:
                # Sort by distance to enemy (closer = better for creep)
                unassigned_sorted = sorted(
                    unassigned,
                    key=lambda q: (
                        q.position.distance_to(enemy_start)
                        if hasattr(q, "position")
                        else 999
                    ),
                )

                for queen in unassigned_sorted[:target_creep_queens]:
                    self.dedicated_creep_queens.add(queen.tag)
                    assigned_queens.add(queen.tag)

        self.assigned_queen_tags = assigned_queens

    async def _inject_larva(self, hatcheries, queens) -> None:
        """
        Inject larva on hatcheries with cooldown tracking.

        ★ 개선: 기지당 2마리 퀸 활용 ★
        - 1차 퀸이 인젝트 불가능하면 2차 퀸이 대신 수행
        - 더 효율적인 라바 생산
        """
        current_time = getattr(self.bot, "time", 0.0)

        for hatch in hatcheries:
            if not hatch:
                continue

            hatch_tag = hatch.tag

            # Check inject cooldown
            last_inject = self.last_inject_time.get(hatch_tag, 0.0)
            if current_time - last_inject < self.inject_cooldown:
                continue

            # ★ 1차 퀸 시도 ★
            queen = self._find_queen_by_tag(
                queens, self.inject_assignments.get(hatch_tag)
            )

            # ★ 1차 퀸이 에너지 부족하면 2차 퀸 시도 ★
            if not queen or getattr(queen, "energy", 0) < self.inject_energy_threshold:
                secondary_assignments = getattr(self, 'secondary_inject_assignments', {})
                secondary_queen = self._find_queen_by_tag(
                    queens, secondary_assignments.get(hatch_tag)
                )
                if secondary_queen and getattr(secondary_queen, "energy", 0) >= self.inject_energy_threshold:
                    queen = secondary_queen

            # Fallback to closest queen if no assignment
            if not queen or getattr(queen, "energy", 0) < self.inject_energy_threshold:
                try:
                    nearby = [
                        q
                        for q in queens
                        if q.distance_to(hatch.position) < self.max_queen_travel_distance
                        and getattr(q, "energy", 0) >= self.inject_energy_threshold
                    ]
                    if nearby:
                        queen = min(
                            nearby, key=lambda q: q.distance_to(hatch.position)
                        )
                except Exception:
                    continue

            if not queen:
                continue

            if getattr(queen, "energy", 0) < self.inject_energy_threshold:
                continue

            # Check distance and issue appropriate command
            try:
                dist = queen.distance_to(hatch)
                if dist > self.max_inject_distance:
                    # Queen too far - move closer first
                    if dist <= self.max_queen_travel_distance:
                        try:
                            result = self.bot.do(queen.move(hatch.position))
                            if hasattr(result, "__await__"):
                                await result
                        except Exception:
                            pass
                    continue
            except Exception:
                continue

            # Execute inject (queen is close enough)
            try:
                if hasattr(queen, "can_cast"):
                    if queen.can_cast(AbilityId.EFFECT_INJECTLARVA):
                        result = self.bot.do(queen(AbilityId.EFFECT_INJECTLARVA, hatch))
                        if hasattr(result, "__await__"):
                            await result
                        self.last_inject_time[hatch_tag] = current_time
                else:
                    result = self.bot.do(queen(AbilityId.EFFECT_INJECTLARVA, hatch))
                    if hasattr(result, "__await__"):
                        await result
                    self.last_inject_time[hatch_tag] = current_time
            except Exception:
                continue

    def _is_base_under_attack(self) -> bool:
        """Check if any base is under attack."""
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "enemy_units"):
            return False

        enemy_units = self.bot.enemy_units
        if not enemy_units:
            return False

        game_time = getattr(self.bot, "time", 0)

        for th in self.bot.townhalls:
            # Dynamic detection range based on game time
            detection_range = 30 if game_time < 180 else 25

            nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < detection_range]
            if nearby_enemies:
                return True

        return False

    async def _queen_defense_mode(self, queens, iteration: int) -> None:
        """
        Queens actively defend when base is under attack.

        Queens will:
        1. Move to defend threatened bases
        2. Attack nearby enemies
        3. ★ Prioritize air units (Queens have good anti-air) ★
        4. ★ IMPROVED: Keep some queens injecting for reinforcements ★
        """
        if not hasattr(self.bot, "enemy_units") or not hasattr(self.bot, "townhalls"):
            return

        enemy_units = self.bot.enemy_units
        if not enemy_units:
            return

        game_time = getattr(self.bot, "time", 0)

        # Find threatened base
        threatened_base = None
        threat_position = None
        nearby_enemies_list = []

        for th in self.bot.townhalls:
            nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < 30]
            if nearby_enemies:
                threatened_base = th
                nearby_enemies_list = nearby_enemies
                # Get center of enemy forces
                x_sum = sum(e.position.x for e in nearby_enemies)
                y_sum = sum(e.position.y for e in nearby_enemies)
                count = len(nearby_enemies)
                try:
                    from sc2.position import Point2
                    threat_position = Point2((x_sum / count, y_sum / count))
                except ImportError:
                    threat_position = nearby_enemies[0].position
                break

        if not threatened_base or not threat_position:
            return

        # ★ 공중 유닛 분류 (퀸 대공 우선) ★
        air_enemies = [e for e in nearby_enemies_list if getattr(e, "is_flying", False)]
        ground_enemies = [e for e in nearby_enemies_list if not getattr(e, "is_flying", False)]

        # Log defense activation
        if iteration % 100 == 0:
            air_count = len(air_enemies)
            ground_count = len(ground_enemies)
            print(f"[QUEEN DEFENSE] [{int(game_time)}s] Queens defending! Air: {air_count}, Ground: {ground_count}")

        # ★ IMPROVED: Keep 1-2 queens injecting for reinforcement ★
        # 전투 중에도 최소 1명의 퀸은 라바 인젝트를 계속해야 병력 충원 가능
        inject_queens = []
        defense_queens = []

        # 해처리 수에 따라 인젝트 퀸 수 결정 (최소 1명, 최대 2명)
        hatcheries = self.bot.townhalls.ready
        num_inject_queens = min(2, max(1, len(hatcheries) // 2))

        # 거리 기준으로 분류: 위협에서 먼 퀸은 인젝트 담당
        sorted_queens = sorted(queens, key=lambda q: q.distance_to(threat_position), reverse=True)

        for i, queen in enumerate(sorted_queens):
            if i < num_inject_queens:
                inject_queens.append(queen)
            else:
                defense_queens.append(queen)

        # ★ 인젝트 퀸은 계속 인젝트 수행 ★
        if inject_queens and hatcheries:
            await self._inject_larva(hatcheries, inject_queens)
            if iteration % 200 == 0:
                print(f"[QUEEN DEFENSE] [{int(game_time)}s] {len(inject_queens)} queens still injecting for reinforcement")

        # Send defense queens to defend
        for queen in defense_queens:
            try:
                dist_to_threat = queen.distance_to(threat_position)

                # If queen is close enough, attack
                if dist_to_threat < 12:
                    # ★ 공중 유닛 우선 공격 (퀸은 대공 유닛) ★
                    target = None
                    
                    # 우선순위: 고위협 공중 > 일반 공중 > 지상
                    # 인터셉터(Interceptor)는 최후순위로 미룸
                    
                    # 고위협 공중 유닛 식별
                    high_value_air = []
                    normal_air = []
                    low_value_air = [] # Interceptors
                    
                    high_value_names = {"CARRIER", "BATTLECRUISER", "TEMPEST", "BROODLORD", "VOIDRAY", "LIBERATOR", "LIBERATORAG"}
                    
                    for e in air_enemies:
                         name = getattr(e.type_id, "name", "").upper()
                         if name == "INTERCEPTOR":
                             low_value_air.append(e)
                         elif name in high_value_names:
                             high_value_air.append(e)
                         else:
                             normal_air.append(e)
                             
                    # 타겟 선정
                    if high_value_air:
                        target = min(high_value_air, key=lambda e: e.distance_to(queen))
                    elif normal_air:
                        target = min(normal_air, key=lambda e: e.distance_to(queen))
                    elif ground_enemies:
                        # 지상 유닛 중 가장 가까운 적
                        target = min(ground_enemies, key=lambda e: e.distance_to(queen))
                    elif low_value_air:
                         # 쏠 게 인터셉터밖에 없으면 그거라도 쏨
                        target = min(low_value_air, key=lambda e: e.distance_to(queen))

                    if target:
                        result = self.bot.do(queen.attack(target))
                        if hasattr(result, "__await__"):
                            await result
                elif dist_to_threat < 25:
                    # Move toward threat
                    result = self.bot.do(queen.attack(threat_position))
                    if hasattr(result, "__await__"):
                        await result
            except Exception:
                continue

    async def _transfuse_injured_units(self, queens, iteration: int, include_structures: bool = False) -> None:
        """
        Transfuse injured biological units.

        Priority targets:
        1. Queens (preserve queens first)
        2. High-value units (Ultralisks, Broodlords)
        3. Low-health combat units
        4. Spine Crawlers (if include_structures=True during defense)
        """
        current_time = getattr(self.bot, "time", 0.0)

        # Find injured units to heal
        injured_targets = []
        if hasattr(self.bot, "units"):
            for unit in self.bot.units:
                if not hasattr(unit, "health") or not hasattr(unit, "health_max"):
                    continue
                if unit.health_max == 0:
                    continue

                health_ratio = unit.health / unit.health_max
                if health_ratio >= self.transfuse_health_threshold:
                    continue

                # Skip non-biological units
                if not getattr(unit, "is_biological", True):
                    continue

                # Calculate priority (lower = higher priority)
                priority = health_ratio  # Base priority on health
                if unit.type_id == UnitTypeId.QUEEN:
                    priority -= 0.5  # Queens highest priority
                elif hasattr(UnitTypeId, "ULTRALISK") and unit.type_id == UnitTypeId.ULTRALISK:
                    priority -= 0.3
                elif hasattr(UnitTypeId, "BROODLORD") and unit.type_id == UnitTypeId.BROODLORD:
                    priority -= 0.3

                injured_targets.append((unit, priority))

        # Include Spine Crawlers during defense (they are biological)
        if include_structures and hasattr(self.bot, "structures"):
            try:
                spines = self.bot.structures(UnitTypeId.SPINECRAWLER)
                for spine in spines:
                    if not hasattr(spine, "health") or not hasattr(spine, "health_max"):
                        continue
                    if spine.health_max == 0:
                        continue

                    health_ratio = spine.health / spine.health_max
                    if health_ratio < 0.7:  # Heal spines below 70% health
                        priority = health_ratio - 0.2  # High priority during defense
                        injured_targets.append((spine, priority))
            except Exception:
                pass

        if not injured_targets:
            return

        # Sort by priority (lowest first)
        injured_targets.sort(key=lambda x: x[1])

        # Assign queens to heal targets
        for target, _ in injured_targets:
            # Find closest queen with enough energy
            best_queen = None
            best_distance = 999

            for queen in queens:
                # Check energy
                if getattr(queen, "energy", 0) < self.transfuse_energy_threshold:
                    continue

                # Check transfuse cooldown
                last_transfuse = self.last_transfuse_time.get(queen.tag, 0.0)
                if current_time - last_transfuse < self.transfuse_cooldown:
                    continue

                # Check distance (transfuse range is 7)
                try:
                    dist = queen.distance_to(target)
                    if dist <= 7 and dist < best_distance:
                        best_distance = dist
                        best_queen = queen
                except Exception:
                    continue

            if best_queen:
                try:
                    if hasattr(best_queen, "can_cast"):
                        if best_queen.can_cast(AbilityId.TRANSFUSION_TRANSFUSION):
                            result = self.bot.do(
                                best_queen(AbilityId.TRANSFUSION_TRANSFUSION, target)
                            )
                            if hasattr(result, "__await__"):
                                await result
                            self.last_transfuse_time[best_queen.tag] = current_time
                    else:
                        result = self.bot.do(
                            best_queen(AbilityId.TRANSFUSION_TRANSFUSION, target)
                        )
                        if hasattr(result, "__await__"):
                            await result
                        self.last_transfuse_time[best_queen.tag] = current_time
                except Exception as e:
                    if iteration % 200 == 0:
                        print(f"[WARNING] Transfuse error: {e}")
                    continue

    async def _spread_creep(self, creep_queens, iteration: int) -> None:
        """
        Spread creep with dedicated queens.

        Dedicated creep queens move toward enemy for aggressive spread.
        """
        current_time = getattr(self.bot, "time", 0.0)
        enemy_start = None

        if hasattr(self.bot, "enemy_start_locations"):
            enemy_start = (
                self.bot.enemy_start_locations[0]
                if self.bot.enemy_start_locations
                else None
            )

        for queen in creep_queens:
            last_time = self.last_creep_time.get(queen.tag, 0.0)
            if current_time - last_time < self.creep_spread_cooldown:
                continue

            if getattr(queen, "energy", 0) < self.creep_energy_threshold:
                continue

            is_dedicated = queen.tag in self.dedicated_creep_queens
            if not is_dedicated:
                if hasattr(queen, "is_idle") and not queen.is_idle:
                    continue

            try:
                # Position dedicated creep queens forward
                if is_dedicated and enemy_start:
                    await self._position_creep_queen_forward(queen, enemy_start)

                target = self._get_creep_target_position(queen)

                # 점막 위에만 종양 설치 가능 확인
                if not self._is_valid_creep_position(target):
                    continue

                if hasattr(queen, "can_cast"):
                    if queen.can_cast(AbilityId.BUILD_CREEPTUMOR_QUEEN):
                        result = self.bot.do(
                            queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, target)
                        )
                        if hasattr(result, "__await__"):
                            await result
                        self.last_creep_time[queen.tag] = current_time
                else:
                    result = self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, target))
                    if hasattr(result, "__await__"):
                        await result
                    self.last_creep_time[queen.tag] = current_time
            except Exception as e:
                if iteration % 200 == 0:
                    print(f"[WARNING] Creep spread error: {e}")
                continue

    async def _inject_queens_spread_creep(self, queens, iteration: int) -> None:
        """
        ★ 수정: 인젝트 퀸이 에너지 여유가 있을 때 점막 확장 (조건 강화)

        조건:
        1. 에너지 60 이상 (인젝트 25 + 종양 25 + 여유 10)
        2. 인젝트 직후가 아닐 때 (쿨다운 20초)
        3. 기지 근처에 점막이 부족할 때
        4. 점막 종양 수 25개 이하
        """
        current_time = getattr(self.bot, "time", 0.0)

        # ★ 점막 종양 수 제한 (25 -> 100)
        tumor_count = self._count_creep_tumors()
        if tumor_count >= 100:
            return

        # 인젝트 퀸만 대상
        inject_queens = [q for q in queens if q.tag in self.assigned_queen_tags]

        for queen in inject_queens:
            # 에너지 확인 (인젝트 + 종양에 충분해야 함)
            if getattr(queen, "energy", 0) < 60:  # ★ 50 → 60으로 증가
                continue

            # ★ 쿨다운 확인 (20초로 증가)
            last_time = self.last_creep_time.get(queen.tag, 0.0)
            if current_time - last_time < 20.0:
                continue

            # 바쁜 퀸은 스킵
            if hasattr(queen, "is_idle") and not queen.is_idle:
                continue

            try:
                # 기지 근처에 점막 놓기
                target = self._get_base_creep_target(queen)

                if not target:
                    continue

                if not self._is_valid_creep_position(target):
                    continue

                if hasattr(queen, "can_cast"):
                    if queen.can_cast(AbilityId.BUILD_CREEPTUMOR_QUEEN):
                        result = self.bot.do(
                            queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, target)
                        )
                        if hasattr(result, "__await__"):
                            await result
                        self.last_creep_time[queen.tag] = current_time
            except Exception:
                continue

    async def _utilize_idle_queens_for_creep(self, queens, iteration: int) -> None:
        """
        ★ 개선: 여유 있는 퀸을 점막 확장에 활용 (조건 강화) ★

        조건:
        1. idle 상태인 퀸 (명령 없음)
        2. 에너지 100 이상인 퀸 (인젝트 4회분 = 충분한 여유)
        3. 최근 점막 생성하지 않은 퀸 (쿨다운 15초)
        4. 게임 시간 5분 이후 (초반 전투력 유지)
        5. 점막 종양 수 30개 이하 (과도한 확장 방지)

        ★ 수정 이유: 전투/방어 필요한 퀸까지 점막에 투입되는 문제 해결
        """
        current_time = getattr(self.bot, "time", 0.0)
        game_time = int(current_time)

        # ★ 조건 1: 게임 시간 5분 이후만 작동 (초반 전투력 유지)
        if game_time < 300:
            return

        # ★ 조건 2: 점막 종양 수 제한 (30 -> 100)
        tumor_count = self._count_creep_tumors()
        if tumor_count >= 100:
            return

        # 여유 퀸 필터링 (조건 강화)
        available_queens = []

        for queen in queens:
            energy = getattr(queen, "energy", 0)

            # 최근 점막 생성 체크 (쿨다운 15초로 증가)
            last_creep = self.last_creep_time.get(queen.tag, 0.0)
            if current_time - last_creep < 15.0:
                continue

            # ★ 강화된 조건: idle + 에너지 100 이상 (인젝트 4회분)
            if hasattr(queen, "is_idle") and queen.is_idle and energy >= 100:
                available_queens.append(queen)

        if not available_queens:
            return

        # 로그 (30초마다)
        if game_time % 30 == 0 and iteration % 22 == 0:
            print(f"[QUEEN CREEP] [{game_time}s] {len(available_queens)} idle/high-energy queens spreading creep (Tumors: {tumor_count}/100)")

        # 각 여유 퀸으로 점막 확장 (최대 2개로 감소)
        tumors_placed = 0
        for queen in available_queens:
            if tumors_placed >= 2:  # ★ 한 번에 최대 2개로 감소
                break

            try:
                # 적 방향으로 점막 타겟 설정
                target = self._get_aggressive_creep_target(queen)

                if not target:
                    target = self._get_creep_target_position(queen)

                if not target:
                    continue

                # 점막 위 확인
                if not self._is_valid_creep_position(target):
                    continue

                # 점막 종양 생성
                if hasattr(queen, "can_cast"):
                    if queen.can_cast(AbilityId.BUILD_CREEPTUMOR_QUEEN):
                        result = self.bot.do(
                            queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, target)
                        )
                        if hasattr(result, "__await__"):
                            await result
                        self.last_creep_time[queen.tag] = current_time
                        tumors_placed += 1
                else:
                    result = self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, target))
                    if hasattr(result, "__await__"):
                        await result
                    self.last_creep_time[queen.tag] = current_time
                    tumors_placed += 1

            except Exception:
                continue

    def _get_aggressive_creep_target(self, queen):
        """
        ★ 적 방향으로 공격적인 점막 타겟 설정 ★

        기지 근처가 아닌 적 방향으로 점막 확장
        """
        try:
            from sc2.position import Point2

            # 적 시작 위치
            enemy_start = None
            if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                enemy_start = self.bot.enemy_start_locations[0]

            if not enemy_start:
                return None

            queen_pos = queen.position

            # ★ 확장 기지 위치 가져오기
            expansion_locations = []
            if hasattr(self.bot, "expansion_locations_list"):
                expansion_locations = list(self.bot.expansion_locations_list)

            # 적 방향으로 8-10 거리 위치 시도 (최대 5회)
            import random
            for _ in range(5):
                distance = random.uniform(7.0, 10.0)
                target = queen_pos.towards(enemy_start, distance)

                # ★ FIX: 확장 기지 위치 근처는 제외 (기지 건설 공간 확보)
                too_close = False
                for exp_loc in expansion_locations:
                    if target.distance_to(exp_loc) < 7.0:
                        too_close = True
                        break

                if not too_close:
                    return target

            # 모든 시도 실패 시 None 반환
            return None

        except Exception:
            return None

    def _get_base_creep_target(self, queen):
        """기지 근처 점막 타겟 위치 결정."""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return None

        # 퀸에서 가장 가까운 기지 찾기
        try:
            closest_base = min(self.bot.townhalls, key=lambda th: queen.distance_to(th.position))
        except Exception:
            return None

        # ★ 확장 기지 위치 가져오기
        expansion_locations = []
        if hasattr(self.bot, "expansion_locations_list"):
            expansion_locations = list(self.bot.expansion_locations_list)

        # 기지 주변 8방향 중 하나 선택
        base_pos = closest_base.position
        import random
        offsets = [(8, 0), (-8, 0), (0, 8), (0, -8), (6, 6), (-6, 6), (6, -6), (-6, -6)]
        random.shuffle(offsets)

        try:
            from sc2.position import Point2
            for dx, dy in offsets:
                target = Point2((base_pos.x + dx, base_pos.y + dy))

                # 맵 경계 체크
                if hasattr(self.bot, "game_info"):
                    map_area = self.bot.game_info.playable_area
                    if not (map_area.x <= target.x <= map_area.x + map_area.width):
                        continue
                    if not (map_area.y <= target.y <= map_area.y + map_area.height):
                        continue

                # ★ FIX: 확장 기지 위치 근처는 제외 (기지 건설 공간 확보)
                too_close = False
                for exp_loc in expansion_locations:
                    if target.distance_to(exp_loc) < 7.0:
                        too_close = True
                        break

                if not too_close:
                    return target
        except Exception:
            return base_pos

        return base_pos

    def _count_creep_tumors(self) -> int:
        """현재 점막 종양 수 반환 (종양 수 제한용)."""
        if not hasattr(self.bot, "structures"):
            return 0

        try:
            tumor_types = {
                UnitTypeId.CREEPTUMOR,
                UnitTypeId.CREEPTUMORBURROWED,
                UnitTypeId.CREEPTUMORQUEEN,
            }
            return sum(1 for s in self.bot.structures if s.type_id in tumor_types)
        except Exception:
            return 0

    def _is_valid_creep_position(self, target) -> bool:
        """점막 종양 설치 가능 위치인지 확인."""
        if not target:
            return False

        try:
            # 점막 위인지 확인
            if hasattr(self.bot, "has_creep"):
                return self.bot.has_creep(target)
        except Exception:
            pass

        # ★ 수정: 확인 불가하면 False 반환 (잘못된 위치 방지)
        return False

    async def _position_creep_queen_forward(self, queen, enemy_start) -> None:
        """Move dedicated creep queen toward enemy for forward creep spread."""
        try:
            farthest_tumor = None
            max_dist = 0

            if hasattr(self.bot, "structures") and hasattr(self.bot, "townhalls"):
                our_base = (
                    self.bot.townhalls.first.position if self.bot.townhalls else None
                )
                if not our_base:
                    return

                for structure in self.bot.structures:
                    if hasattr(structure, "type_id") and structure.type_id in {
                        UnitTypeId.CREEPTUMOR,
                        UnitTypeId.CREEPTUMORBURROWED,
                    }:
                        try:
                            dist = structure.position.distance_to(enemy_start)
                            if dist > max_dist:
                                max_dist = dist
                                farthest_tumor = structure
                        except Exception:
                            continue

            # Move queen toward farthest tumor or enemy base
            if farthest_tumor and hasattr(queen, "distance_to"):
                if queen.distance_to(farthest_tumor) > 8:
                    result = self.bot.do(queen.move(farthest_tumor.position))
                    if hasattr(result, "__await__"):
                        await result
            elif hasattr(queen, "distance_to") and queen.distance_to(enemy_start) > 15:
                forward_pos = queen.position.towards(enemy_start, 10)
                result = self.bot.do(queen.move(forward_pos))
                if hasattr(result, "__await__"):
                    await result
        except Exception:
            pass

    def _get_creep_target_position(self, queen):
        """Pick a creep spread target along the main attack path."""
        creep_manager = getattr(self.bot, "creep_manager", None)
        if creep_manager:
            try:
                target = creep_manager.get_creep_target(queen)
                if target:
                    return target
            except Exception:
                pass

        enemy_starts = getattr(self.bot, "enemy_start_locations", [])
        origin = queen.position

        direction_target = None
        if enemy_starts:
            direction_target = enemy_starts[0]
        elif hasattr(self.bot, "game_info"):
            direction_target = self.bot.game_info.map_center

        candidates = self._collect_creep_targets()
        if direction_target and candidates:
            best = max(
                candidates,
                key=lambda pos: self._score_creep_target(
                    origin, pos, direction_target
                ),
            )
            return best

        if direction_target:
            return origin.towards(direction_target, 7)

        return origin.towards(origin, 3)

    def _collect_creep_targets(self):
        """Collect potential creep target positions."""
        positions = []
        scout = getattr(self.bot, "scout", None)
        if scout:
            positions.extend(getattr(scout, "cached_positions", []))
            assignments = getattr(scout, "overlord_assignments", {})
            positions.extend(assignments.values())

        expansion_list = getattr(self.bot, "expansion_locations_list", None)
        if expansion_list:
            positions.extend(expansion_list)

        return [pos for pos in positions if pos]

    @staticmethod
    def _score_creep_target(origin, candidate, direction_target) -> float:
        """Score a creep target by distance and direction alignment."""
        dx = candidate.x - origin.x
        dy = candidate.y - origin.y
        dist = (dx * dx + dy * dy) ** 0.5

        dir_x = direction_target.x - origin.x
        dir_y = direction_target.y - origin.y
        dir_len = (dir_x * dir_x + dir_y * dir_y) ** 0.5
        if dir_len == 0:
            return dist
        dir_x /= dir_len
        dir_y /= dir_len
        projection = dx * dir_x + dy * dir_y
        return projection + dist * 0.25

    @staticmethod
    def _find_closest_queen(position, queens, excluded_tags: Set[int]):
        """Find closest queen not in excluded set."""
        candidates = [q for q in queens if q.tag not in excluded_tags]
        if not candidates:
            return None
        try:
            return min(candidates, key=lambda q: q.distance_to(position))
        except Exception:
            return candidates[0] if candidates else None

    @staticmethod
    def _find_queen_by_tag(queens, queen_tag: Optional[int]):
        """Find queen by tag."""
        if queen_tag is None:
            return None
        for queen in queens:
            if queen.tag == queen_tag:
                return queen
        return None

    async def _safe_train(self, building, unit_type) -> bool:
        """Safely train a unit with async/sync handling."""
        try:
            result = building.train(unit_type)
            if hasattr(result, "__await__"):
                await result
            else:
                # bot.do() is NOT async in python-sc2
                self.bot.do(result)
            return True
        except Exception:
            return False


# Backward compatibility alias
QueenManagerImproved = QueenManager
