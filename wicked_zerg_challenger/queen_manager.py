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

        # Creep settings
        self.creep_energy_threshold = 25
        self.creep_spread_cooldown = 12.0  # 개선: 15초 → 12초 (더 공격적인 확장)
        self.inject_queen_creep_threshold = 50  # 인젝트 퀸이 점막 놓을 에너지 임계값

        # Queen production
        self.max_queens_per_base = 1
        self.creep_queen_bonus = 3  # 개선: 2 → 3 (전용 점막 퀸 추가)

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

        Priority:
        1. Inject queens (1 per hatchery)
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

        # Assign inject queens
        assigned_queens = set(self.inject_assignments.values())
        for hatch in hatcheries:
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
                        else:
                            continue
                    except Exception:
                        continue

            candidate = self._find_closest_queen(
                hatch.position, queens, assigned_queens
            )
            if candidate:
                self.inject_assignments[hatch.tag] = candidate.tag
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

        Improved efficiency with distance checks and reassignment.
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

            # Find assigned queen
            queen = self._find_queen_by_tag(
                queens, self.inject_assignments.get(hatch_tag)
            )

            # Fallback to closest queen if no assignment
            if not queen:
                try:
                    nearby = [
                        q
                        for q in queens
                        if q.distance_to(hatch.position) < self.max_queen_travel_distance
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

                    if air_enemies:
                        # 공중 유닛 중 가장 가까운 적 공격
                        target = min(air_enemies, key=lambda e: e.distance_to(queen))
                    elif ground_enemies:
                        # 지상 유닛 중 가장 가까운 적 공격
                        target = min(ground_enemies, key=lambda e: e.distance_to(queen))

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
        인젝트 퀸이 에너지 여유가 있을 때 점막 확장.

        조건:
        1. 에너지 50 이상 (인젝트 25 + 여유)
        2. 인젝트 직후가 아닐 때
        3. 기지 근처에 점막이 부족할 때
        """
        current_time = getattr(self.bot, "time", 0.0)

        # 인젝트 퀸만 대상
        inject_queens = [q for q in queens if q.tag in self.assigned_queen_tags]

        for queen in inject_queens:
            # 에너지 확인 (인젝트 + 종양에 충분해야 함)
            if getattr(queen, "energy", 0) < self.inject_queen_creep_threshold:
                continue

            # 쿨다운 확인 (전용 퀸보다 긴 간격)
            last_time = self.last_creep_time.get(queen.tag, 0.0)
            if current_time - last_time < self.creep_spread_cooldown * 2:
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

    def _get_base_creep_target(self, queen):
        """기지 근처 점막 타겟 위치 결정."""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return None

        # 퀸에서 가장 가까운 기지 찾기
        try:
            closest_base = min(self.bot.townhalls, key=lambda th: queen.distance_to(th.position))
        except Exception:
            return None

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
                return target
        except Exception:
            return base_pos

        return base_pos

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

        # 확인 불가하면 True 반환 (시도해봄)
        return True

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
