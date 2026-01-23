# -*- coding: utf-8 -*-
"""
Combat Manager - 전투 관리자

타겟팅 시스템과 마이크로 전투를 통합한 전투 관리자
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.units import Units
    from sc2.unit import Unit
    from sc2.position import Point2
else:
    try:
        from sc2.units import Units
        from sc2.unit import Unit
        from sc2.position import Point2
    except ImportError:
        Units = object
        Unit = object
        Point2 = tuple

# Import common helpers to reduce code duplication
try:
    from utils.common_helpers import (
        has_units, units_amount, filter_by_type, closest_enemy, centroid
    )
    HELPERS_AVAILABLE = True
except ImportError:
    HELPERS_AVAILABLE = False


class CombatManager:
    """
    전투 관리자

    기능:
    1. 타겟팅 시스템과 연동
    2. 마이크로 전투 (키팅, 스플릿, 집중 사격)
    3. Boids 알고리즘 기반 군집 제어
    4. 진형 형성 (Concave, 길목 차단)
    5. 공중 유닛 전용 마이크로 (뮤탈리스크 하라스, 타겟 우선순위)
    6. ★ 필수 기지 방어 시스템 ★
    """

    def __init__(self, bot):
        self.bot = bot
        self.targeting = None
        self.micro_combat = None
        self.boids = None

        # Air unit micro state
        self._air_harass_target = None
        self._last_air_harass_time = 0
        self._air_harass_cooldown = 30  # 30 seconds between harass decisions

        # === MULTITASKING SYSTEM ===
        # Task priorities (higher = more important)
        self.task_priorities = {
            "base_defense": 100,      # Defend our base - HIGHEST PRIORITY
            "worker_defense": 90,     # Protect workers
            "counter_attack": 70,     # Attack enemy attackers
            "air_harass": 60,         # Air unit harassment
            "scout": 50,              # Scouting
            "main_attack": 40,        # Main army attack
            "creep_spread": 30,       # Creep spreading
        }

        # Active tasks and assigned units
        self._active_tasks = {}  # task_name -> {"units": set(), "target": position}
        self._unit_assignments = {}  # unit_tag -> task_name

        # Task cooldowns
        self._task_cooldowns = {}

        # === COUNTER ATTACK SYSTEM ===
        self._last_combat_time = 0  # Track when last combat occurred
        self._counter_attack_cooldown = 15  # 15 seconds cooldown between counter attacks

        # === RALLY POINT SYSTEM ===
        # Rally point for army units to gather before attacking
        self._rally_point = None
        self._last_rally_update = 0
        self._rally_update_interval = 30  # Update rally point every 30 seconds
        self._min_army_for_attack = 15  # Minimum supply before attacking

        # === ★ MANDATORY BASE DEFENSE SYSTEM ★ ===
        self._base_defense_active = False
        self._defense_rally_point = None
        self._last_defense_check = 0
        self._defense_check_interval = 5  # 5프레임마다 체크 (더 자주)
        self._worker_defense_threshold = 1  # ★ FIX: 적 1기라도 일꾼 근처 위협 시 방어 ★
        self._critical_defense_threshold = 8  # 적 8기 이상이면 모든 유닛 방어

        # === ★★★ VICTORY CONDITION TRACKING ★★★ ===
        self._victory_push_active = False  # 승리 푸시 모드
        self._last_enemy_structure_count = 0  # 마지막으로 본 적 건물 수
        self._enemy_structures_destroyed = 0  # 파괴한 적 건물 수
        self._last_victory_check = 0  # 마지막 승리 조건 체크 시간
        self._victory_check_interval = 110  # 승리 조건 체크 주기 (약 5초)
        self._endgame_push_threshold = 360  # 6분 이후 승리 푸시 가능
        self._known_enemy_expansions = set()  # 발견한 적 확장 위치
        self._last_expansion_check = 0  # 마지막 확장 체크 시간

        # 매니저 초기화
        self._initialize_managers()
    
    def _initialize_managers(self):
        """매니저들 초기화"""
        try:
            from combat.targeting import Targeting
            self.targeting = Targeting(self.bot)
        except ImportError:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 500 == 0:
                print("[WARNING] Targeting system not available")
        
        try:
            from combat.micro_combat import MicroCombat
            self.micro_combat = MicroCombat(self.bot)
        except ImportError:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 500 == 0:
                print("[WARNING] Micro combat not available")
        
        try:
            from combat.boids_swarm_control import BoidsSwarmController
            self.boids = BoidsSwarmController()
        except ImportError:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 500 == 0:
                print("[WARNING] Boids controller not available")
    
    async def on_step(self, iteration: int):
        """
        매 프레임 호출되는 전투 로직 with multitasking support.

        ★ IMPROVED: 필수 기지 방어 우선 ★

        Priority:
        1. ★ MANDATORY BASE DEFENSE - Always check first ★
        2. Evaluate all possible tasks and their priorities
        3. Assign units to tasks based on priority
        4. Execute all tasks in parallel

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            # Clean up stale unit assignments
            self._cleanup_assignments()

            # ★★★ 승리 조건 체크 및 승리 푸시 활성화 ★★★
            if iteration - self._last_victory_check > self._victory_check_interval:
                await self._check_victory_conditions(iteration)
                self._last_victory_check = iteration

            # ★ 필수 기지 방어 체크 - 항상 최우선 ★
            base_threat = await self._check_mandatory_base_defense(iteration)

            # Skip if MicroController is handling movement
            # This prevents dual command conflicts (both issuing move/attack)
            if hasattr(self.bot, 'micro') and self.bot.micro is not None:
                # ★ 기지 위협 시 MicroController도 방어 모드로 전환 ★
                if base_threat and hasattr(self.bot.micro, 'set_defense_mode'):
                    self.bot.micro.set_defense_mode(True, base_threat)

                # CombatManager only updates targeting info, no direct commands
                # MicroController will handle actual movement
                # BUT still handle air unit harassment (multitasking)
                await self._handle_air_units_separately(iteration)

                # Also ensure burrow controller gets called for banelings
                # even when MicroController is active
                await self._ensure_baneling_burrow(iteration)
                return

            # 아군 유닛과 적 유닛 확인
            if not hasattr(self.bot, 'units') or not hasattr(self.bot, 'enemy_units'):
                return

            army_units = self._filter_army_units(getattr(self.bot, "units", []))
            air_units = self._filter_air_units(getattr(self.bot, "units", []))
            enemy_units = getattr(self.bot, "enemy_units", [])

            # === MULTITASKING: Evaluate and assign tasks ===
            await self._execute_multitasking(army_units, air_units, enemy_units, iteration)

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Combat manager error: {e}")

    async def _execute_multitasking(self, army_units, air_units, enemy_units, iteration: int):
        """
        Execute multitasking logic - run multiple tasks in parallel.

        Task Priority:
        1. Base Defense (if enemies near base)
        2. Worker Defense (if workers attacked)
        3. Air Harassment (if we have 5+ Mutalisks)
        4. Main Army Attack (attack with ground army)
        5. Scouting (use idle Zerglings)
        """
        game_time = getattr(self.bot, "time", 0)

        # Evaluate tasks
        tasks_to_execute = []

        # === TASK 1: Base Defense ===
        base_threat = self._evaluate_base_threat(enemy_units)
        if base_threat:
            tasks_to_execute.append(("base_defense", base_threat, self.task_priorities["base_defense"]))

        # === TASK 2: Air Harassment ===
        if self._has_units(air_units) and self._units_amount(air_units) >= 5:
            harass_target = self._find_harass_target()
            if harass_target:
                tasks_to_execute.append(("air_harass", harass_target, self.task_priorities["air_harass"]))

        # === TASK 2.3: Early Zergling Harass (3-5분) ===
        game_time = getattr(self.bot, 'time', 0)
        if 180 <= game_time <= 300:  # 3-5분
            try:
                from sc2.ids.unit_typeid import UnitTypeId
                zerglings = [u for u in army_units if hasattr(u, 'type_id') and u.type_id == UnitTypeId.ZERGLING]
                if 6 <= len(zerglings) <= 24:
                    harass_target = self._find_harass_target()
                    if harass_target:
                        # Priority 65 (between air_harass and counter_attack)
                        tasks_to_execute.append(("early_harass", harass_target, 65))
            except ImportError:
                pass

        # === TASK 2.5: Counter Attack (after winning a battle) ===
        ground_army = self._filter_ground_units(army_units)
        if self._check_counterattack_opportunity(ground_army, enemy_units, game_time):
            # Counter attack has priority 70 (same as counter_attack task priority)
            enemy_base = self._get_enemy_base_location()
            if enemy_base:
                tasks_to_execute.append(("counter_attack", enemy_base, self.task_priorities["counter_attack"]))
                print(f"[COUNTER_ATTACK] Detected victory - attacking enemy base!")

        # === TASK 3: Main Army Attack ===
        if self._has_units(ground_army):
            attack_target = self._get_attack_target(enemy_units)
            if attack_target:
                tasks_to_execute.append(("main_attack", attack_target, self.task_priorities["main_attack"]))

        # Sort tasks by priority (highest first)
        tasks_to_execute.sort(key=lambda x: x[2], reverse=True)

        # Assign units to tasks
        available_ground = set(u.tag for u in ground_army) if ground_army else set()
        available_air = set(u.tag for u in air_units) if air_units else set()

        for task_name, target, priority in tasks_to_execute:
            if task_name == "base_defense":
                # Use all nearby units for defense
                defense_units = self._get_units_near_base(army_units, 30)
                if self._has_units(defense_units):
                    await self._execute_defense_task(defense_units, target)
                    # Remove from available pool
                    for u in defense_units:
                        available_ground.discard(u.tag)
                        available_air.discard(u.tag)

            elif task_name == "air_harass":
                # Use air units for harassment
                harass_units = [u for u in air_units if u.tag in available_air]
                if harass_units:
                    await self._handle_air_combat(harass_units, enemy_units, iteration)
                    for u in harass_units:
                        available_air.discard(u.tag)

            elif task_name == "early_harass":
                # Use zerglings for early harassment
                try:
                    from sc2.ids.unit_typeid import UnitTypeId
                    harass_zerglings = [u for u in ground_army
                                       if u.tag in available_ground
                                       and hasattr(u, 'type_id')
                                       and u.type_id == UnitTypeId.ZERGLING]
                    if harass_zerglings:
                        await self._zergling_early_harass(harass_zerglings, enemy_units, iteration)
                        for u in harass_zerglings:
                            available_ground.discard(u.tag)
                except ImportError:
                    pass

            elif task_name == "counter_attack":
                # Use all available ground units for counter attack
                attack_units = [u for u in ground_army if u.tag in available_ground]
                if attack_units:
                    # Attack enemy base directly
                    for unit in attack_units:
                        try:
                            self.bot.do(unit.attack(target))
                        except Exception:
                            continue
                    # Remove from available pool
                    for u in attack_units:
                        available_ground.discard(u.tag)

            elif task_name == "main_attack":
                # Use remaining ground units for attack
                attack_units = [u for u in ground_army if u.tag in available_ground]
                if attack_units and self._has_units(enemy_units):
                    await self._execute_combat(attack_units, enemy_units)
                elif attack_units:
                    await self._offensive_attack(attack_units, iteration)

        # Log multitasking status periodically
        if iteration % 200 == 0 and tasks_to_execute:
            active_tasks = [t[0] for t in tasks_to_execute]
            print(f"[MULTITASK] [{int(game_time)}s] Active tasks: {active_tasks}")

    def _evaluate_base_threat(self, enemy_units):
        """
        Check if any base is threatened and return threat info.

        IMPROVED:
        - 1 적만 있어도 감지 (스카우트 대응)
        - 위협 수준 반환 (심각도에 따른 대응)
        - 중후반 대규모 공격 감지
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return None

        game_time = getattr(self.bot, "time", 0)

        # 고위협 유닛 (중후반 푸쉬의 핵심)
        high_threat_units = {
            "SIEGETANK", "SIEGETANKSIEGED", "THOR", "BATTLECRUISER",
            "COLOSSUS", "DISRUPTOR", "IMMORTAL", "ARCHON",
            "ULTRALISK", "BROODLORD", "RAVAGER", "LURKER"
        }

        # 위협 수준: light (1-2), medium (3-5), heavy (6+), critical (고위협 유닛 포함)
        highest_threat = None
        highest_threat_count = 0
        highest_threat_score = 0
        has_high_threat = False

        for th in self.bot.townhalls:
            # 중후반에는 더 넓은 감지 거리 (40)
            detection_range = 25 if game_time < 300 else 40

            nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < detection_range]

            if not nearby_enemies:
                continue

            # 위협 점수 계산
            threat_score = 0
            local_high_threat = False
            for enemy in nearby_enemies:
                enemy_type = getattr(enemy.type_id, "name", "").upper()
                if enemy_type in high_threat_units:
                    threat_score += 5
                    local_high_threat = True
                else:
                    threat_score += 1

            # 가장 높은 위협 선택
            if threat_score > highest_threat_score:
                highest_threat_score = threat_score
                highest_threat_count = len(nearby_enemies)
                highest_threat = self._get_enemy_center(nearby_enemies)
                has_high_threat = local_high_threat

        # 위협이 있으면 디버그 출력
        if highest_threat and self.bot.iteration % 50 == 0:
            if has_high_threat:
                threat_level = "CRITICAL"
            elif highest_threat_count >= 6:
                threat_level = "heavy"
            elif highest_threat_count >= 3:
                threat_level = "medium"
            else:
                threat_level = "light"
            print(f"[DEFENSE] [{int(game_time)}s] Base threat: {highest_threat_count} enemies ({threat_level}, score={highest_threat_score})")

        return highest_threat

    def _get_units_near_base(self, units, range_distance: float = 30):
        """Get units near our bases."""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return []

        near_units = []
        for th in self.bot.townhalls:
            for u in units:
                if u.distance_to(th.position) < range_distance and u not in near_units:
                    near_units.append(u)

        return near_units

    def _get_attack_target(self, enemy_units):
        """Get best attack target for main army."""
        if self._has_units(enemy_units):
            return self._get_enemy_center(enemy_units)

        # No visible enemies - attack enemy base
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]

        return None

    async def _execute_defense_task(self, units, threat_position):
        """
        Execute base defense task.

        IMPROVED:
        - 퀸 우선 방어 (트랜스퓨전 사용 가능)
        - 스파인 크롤러 자동 타겟팅
        - 고위협 유닛 집중 공격 (시즈탱크, 콜로서스 등)
        - 가까운 유닛부터 이동
        """
        if not threat_position:
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            # Fallback to simple attack
            for unit in units:
                try:
                    self.bot.do(unit.attack(threat_position))
                except Exception:
                    continue
            return

        # 고위협 유닛 목록 (우선 집중 공격)
        high_priority_targets = {
            "SIEGETANK", "SIEGETANKSIEGED", "COLOSSUS", "DISRUPTOR",
            "HIGHTEMPLAR", "WIDOWMINE", "LIBERATOR", "LIBERATORAG",
            "IMMORTAL", "THOR", "MEDIVAC"  # 메디박도 우선 제거
        }

        # 적 유닛 중 우선순위 타겟 찾기
        priority_target = None
        enemy_units = getattr(self.bot, "enemy_units", [])
        if enemy_units:
            for enemy in enemy_units:
                enemy_type = getattr(enemy.type_id, "name", "").upper()
                if enemy_type in high_priority_targets and enemy.distance_to(threat_position) < 15:
                    priority_target = enemy
                    break

        # 퀸을 먼저 보내기 (가장 빠른 방어 유닛)
        queens = [u for u in units if hasattr(u, 'type_id') and u.type_id == UnitTypeId.QUEEN]
        other_units = [u for u in units if u not in queens]

        # 퀸 방어 우선
        for queen in queens:
            try:
                # 이미 가까이 있으면 공격, 아니면 이동
                if queen.distance_to(threat_position) < 8:
                    target = priority_target if priority_target else threat_position
                    self.bot.do(queen.attack(target))
                else:
                    self.bot.do(queen.move(threat_position))
            except Exception:
                continue

        # 스파인 크롤러 타겟팅 (고위협 유닛 우선)
        if hasattr(self.bot, "structures"):
            spines = self.bot.structures(UnitTypeId.SPINECRAWLER).ready
            for spine in spines:
                if spine.distance_to(threat_position) < 20:  # 범위 확대
                    try:
                        enemies_near = [e for e in enemy_units if e.distance_to(spine) < 12]
                        if enemies_near:
                            # 우선순위 타겟 먼저
                            priority_enemies = [
                                e for e in enemies_near
                                if getattr(e.type_id, "name", "").upper() in high_priority_targets
                            ]
                            if priority_enemies:
                                target = min(priority_enemies, key=lambda e: e.distance_to(spine))
                            else:
                                target = min(enemies_near, key=lambda e: e.distance_to(spine))
                            self.bot.do(spine.attack(target))
                    except Exception:
                        pass

        # 다른 유닛들 방어 (우선순위 타겟 집중)
        for unit in other_units:
            try:
                if priority_target and unit.distance_to(priority_target) < 10:
                    # 고위협 유닛에 집중
                    self.bot.do(unit.attack(priority_target))
                else:
                    self.bot.do(unit.attack(threat_position))
            except Exception:
                continue

    def _cleanup_assignments(self):
        """Clean up stale unit assignments (dead units)."""
        if not hasattr(self.bot, "units"):
            return

        alive_tags = set(u.tag for u in self.bot.units)
        stale_tags = [tag for tag in self._unit_assignments if tag not in alive_tags]
        for tag in stale_tags:
            del self._unit_assignments[tag]
    
    async def _execute_combat(self, units: Units, enemy_units):
        """
        전투 실행
        
        CRITICAL IMPROVEMENT: 진형 형성 로직 통합
        
        Args:
            units: 아군 유닛들
            enemy_units: 적 유닛들
        """
        try:
            # 0. 진형 형성 (원거리 유닛만)
            await self._form_formation(units, enemy_units)
            
            # 1. 오버킬 분산 타겟 할당
            if self.targeting and self.micro_combat:
                assignments = self.targeting.assign_targets(units, enemy_units)
                if assignments:
                    await self.micro_combat.attack_assigned_targets(units, assignments)
                    return

            # 2. 집중 사격 (타겟팅 시스템 사용)
            if self.targeting:
                focus_target = None
                if hasattr(self.targeting, "get_focus_fire_target"):
                    focus_target = self.targeting.get_focus_fire_target(units, enemy_units)
                elif hasattr(self.targeting, "select_focus_fire_target"):
                    focus_target = self.targeting.select_focus_fire_target(units, enemy_units)
                if focus_target:
                    if self.micro_combat:
                        await self.micro_combat.focus_fire(units, focus_target)
                    return
            
            # 3. 타겟팅 시스템 없으면 기본 공격
            if self.micro_combat:
                await self.micro_combat.kiting(units, enemy_units)
            else:
                # 마이크로 전투도 없으면 기본 공격
                await self._basic_attack(units, enemy_units)
        
        except Exception as e:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 200 == 0:
                print(f"[WARNING] Combat execution error: {e}")
            # 에러 발생 시 기본 공격
            await self._basic_attack(units, enemy_units)
    
    async def _form_formation(self, units: Units, enemy_units):
        """
        진형 형성
        
        CRITICAL IMPROVEMENT: Concave 진형 및 길목 차단 로직
        
        Args:
            units: 아군 유닛들
            enemy_units: 적 유닛들
        """
        try:
            from combat.formation_manager import FormationManager
            
            formation_manager = FormationManager(self.bot)
            
            if not self._has_units(enemy_units) or not self._has_units(units):
                return
            
            # 적 중심 계산
            enemy_center = self._get_enemy_center(enemy_units)
            if enemy_center is None:
                return
            
            # 원거리 유닛만 진형 형성 (히드라리스크, 로ach, Ravager)
            ranged_units = self._filter_units_by_type(
                units, ["HYDRALISK", "ROACH", "RAVAGER"]
            )
            
            if self._has_units(ranged_units) and self._units_amount(ranged_units) >= 3:
                # Concave 진형 형성
                formation_positions = formation_manager.form_concave(
                    ranged_units, enemy_center, formation_radius=8.0
                )
                
                # 유닛들을 진형 위치로 이동
                for unit, target_pos in formation_positions[:10]:  # 최대 10개만
                    try:
                        self.bot.do(unit.move(target_pos))
                    except Exception:
                        pass
            
            # 길목 회피 확인
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                our_base = self.bot.townhalls.first.position
                chokepoint = formation_manager.find_chokepoint(enemy_units, our_base)
                
                if chokepoint and formation_manager.should_avoid_chokepoint(units, chokepoint, enemy_units):
                    # 넓은 곳으로 후퇴
                    retreat_pos = formation_manager.get_retreat_position(units, enemy_units, our_base)
                    if retreat_pos:
                        for unit in units[:10]:  # 최대 10개만
                            try:
                                self.bot.do(unit.move(retreat_pos))
                            except Exception:
                                pass
        
        except Exception as e:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 200 == 0:
                print(f"[WARNING] Formation error: {e}")
    
    async def _basic_attack(self, units: Units, enemy_units):
        """
        기본 공격 (에러 발생 시)
        
        Args:
            units: 아군 유닛들
            enemy_units: 적 유닛들
        """
        try:
            for unit in list(units)[:20]:  # 최대 20개만 처리
                closest_enemy = self._closest_enemy(enemy_units, unit)
                if closest_enemy:
                    self.bot.do(unit.attack(closest_enemy))
        except Exception:
            pass

    async def _offensive_attack(self, army_units, iteration: int):
        """
        선제 공격 로직 - 적 유닛이 보이지 않을 때 적 기지 공격

        ★ IMPROVED: 보이는 모든 적 기지 파괴 우선 ★

        Uses rally point system:
        1. Army gathers at rally point until minimum supply reached
        2. Once enough army, attack enemy base together
        3. Rally point is between our natural and center of map
        4. ★ NEW: 보이는 적 건물(특히 기지) 우선 파괴

        Args:
            army_units: 아군 유닛들
            iteration: 현재 반복 횟수
        """
        try:
            # Update rally point periodically
            game_time = getattr(self.bot, "time", 0)
            if game_time - self._last_rally_update > self._rally_update_interval:
                self._update_rally_point()
                self._last_rally_update = game_time

            # 최소 군대 서플라이 확인
            army_supply = sum(getattr(u, "supply_cost", 1) for u in army_units)

            # If army is small, gather at rally point
            if army_supply < self._min_army_for_attack:
                if self._rally_point:
                    await self._gather_at_rally_point(army_units, iteration)
                return

            # ★★★ 보이는 적 기지/건물 우선 파괴 ★★★
            attack_target = self._find_priority_attack_target()

            if not attack_target:
                # 적 시작 위치로 공격 (fallback)
                if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                    attack_target = self.bot.enemy_start_locations[0]

            if not attack_target:
                return

            # Check if army is gathered (most units near rally point)
            if self._rally_point and not self._is_army_gathered(army_units):
                await self._gather_at_rally_point(army_units, iteration)
                return

            # 매 30 프레임마다 공격 명령 갱신 (더 자주)
            if iteration % 30 != 0:
                return

            # 아군 유닛들을 적 타겟으로 공격 명령
            for unit in list(army_units):  # 모든 유닛 공격
                try:
                    if hasattr(unit, "is_idle") and unit.is_idle:
                        self.bot.do(unit.attack(attack_target))
                    elif not hasattr(unit, "is_attacking") or not unit.is_attacking:
                        self.bot.do(unit.attack(attack_target))
                except Exception:
                    continue

            if iteration % 200 == 0:
                target_name = getattr(attack_target, "name", str(attack_target)[:30])
                print(f"[OFFENSIVE] [{int(self.bot.time)}s] Attacking {target_name} with {army_supply} supply army")

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Offensive attack error: {e}")

    def _find_priority_attack_target(self):
        """
        ★ 우선 공격 타겟 찾기 - 보이는 적 기지 우선 ★

        우선순위:
        1. 적 기지 (타운홀) - 네서스, 사령부, 해처리 등
        2. 적 생산 건물 - 배럭, 게이트웨이, 스포닝풀 등
        3. 적 테크 건물 - 팩토리, 로보, 스파이어 등
        4. 기타 적 건물
        5. ★ 맵 수색 위치 (적 건물이 없을 때) ★
        6. 적 시작 위치 (fallback)

        Returns:
            공격 타겟 위치 또는 유닛
        """
        enemy_structures = getattr(self.bot, "enemy_structures", None)

        # 기지 타입 (최우선)
        townhall_types = {
            "NEXUS", "COMMANDCENTER", "COMMANDCENTERFLYING",
            "ORBITALCOMMAND", "ORBITALCOMMANDFLYING", "PLANETARYFORTRESS",
            "HATCHERY", "LAIR", "HIVE"
        }

        # 생산 건물 타입 (2순위)
        production_types = {
            "BARRACKS", "BARRACKSFLYING", "FACTORY", "FACTORYFLYING",
            "STARPORT", "STARPORTFLYING",
            "GATEWAY", "WARPGATE", "ROBOTICSFACILITY", "STARGATE",
            "SPAWNINGPOOL", "ROACHWARREN", "HYDRALISKDEN", "SPIRE"
        }

        if enemy_structures and enemy_structures.exists:
            # 우선순위별 타겟 찾기
            townhall_targets = []
            production_targets = []
            other_targets = []

            for struct in enemy_structures:
                struct_type = getattr(struct.type_id, "name", "").upper()

                if struct_type in townhall_types:
                    townhall_targets.append(struct)
                elif struct_type in production_types:
                    production_targets.append(struct)
                else:
                    other_targets.append(struct)

            # 1. 기지 우선 (가장 가까운 것)
            if townhall_targets:
                if hasattr(self.bot, "start_location"):
                    return min(townhall_targets, key=lambda s: s.distance_to(self.bot.start_location))
                return townhall_targets[0]

            # 2. 생산 건물
            if production_targets:
                if hasattr(self.bot, "start_location"):
                    return min(production_targets, key=lambda s: s.distance_to(self.bot.start_location))
                return production_targets[0]

            # 3. 기타 건물
            if other_targets:
                if hasattr(self.bot, "start_location"):
                    return min(other_targets, key=lambda s: s.distance_to(self.bot.start_location))
                return other_targets[0]

        # ★★★ 적 건물이 보이지 않으면 맵 수색 ★★★
        return self._get_map_search_target()

    def _get_map_search_target(self):
        """
        ★ 맵 수색 타겟 - AI 상대 승리를 위해 모든 기지 탐색 ★

        확장 위치들을 순회하며 적 기지를 찾습니다.
        """
        game_time = getattr(self.bot, "time", 0)

        # 맵 수색 인덱스 초기화
        if not hasattr(self, "_search_index"):
            self._search_index = 0
            self._last_search_time = 0

        # 수색 위치 목록 생성
        search_locations = []

        # 1. 적 시작 위치
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            search_locations.append(self.bot.enemy_start_locations[0])

        # 2. 확장 위치들 (적 시작 위치에서 가까운 순)
        if hasattr(self.bot, "expansion_locations_list"):
            exp_list = list(self.bot.expansion_locations_list)

            # 적 시작 위치에서 가까운 순으로 정렬
            if search_locations:
                enemy_start = search_locations[0]
                exp_list.sort(key=lambda pos: pos.distance_to(enemy_start))

            # 이미 점령한 위치 제외
            our_bases = set()
            if hasattr(self.bot, "townhalls"):
                for th in self.bot.townhalls:
                    our_bases.add(th.position)

            for exp_pos in exp_list:
                # 우리 기지 근처는 스킵
                if any(exp_pos.distance_to(base) < 5 for base in our_bases):
                    continue
                search_locations.append(exp_pos)

        # 3. 맵 중앙
        if hasattr(self.bot, "game_info"):
            search_locations.append(self.bot.game_info.map_center)

        if not search_locations:
            return None

        # 30초마다 다음 수색 위치로 이동
        if game_time - self._last_search_time > 30:
            self._search_index = (self._search_index + 1) % len(search_locations)
            self._last_search_time = game_time

            if self.bot.iteration % 100 == 0:
                print(f"[SEARCH] [{int(game_time)}s] Searching map location {self._search_index + 1}/{len(search_locations)}")

        return search_locations[self._search_index]

    def _update_rally_point(self):
        """
        Update the rally point for army gathering.

        Rally point is positioned:
        - Between our natural expansion and map center
        - On our side of the map for safety
        - Away from enemy attack routes
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return

        try:
            our_base = self.bot.townhalls.first.position
            map_center = self.bot.game_info.map_center if hasattr(self.bot, "game_info") else our_base

            # Rally point is 30% of the way from our base to map center
            rally_x = our_base.x + (map_center.x - our_base.x) * 0.3
            rally_y = our_base.y + (map_center.y - our_base.y) * 0.3

            if hasattr(self.bot, "Point2"):
                self._rally_point = self.bot.Point2((rally_x, rally_y))
            else:
                from sc2.position import Point2
                self._rally_point = Point2((rally_x, rally_y))

        except Exception:
            # Fallback to main base position
            if hasattr(self.bot, "start_location"):
                self._rally_point = self.bot.start_location

    async def _gather_at_rally_point(self, army_units, iteration: int):
        """
        Gather army units at the rally point.

        Only sends idle or wandering units to rally point.
        """
        if not self._rally_point:
            return

        if iteration % 22 != 0:  # Only update every ~1 second
            return

        for unit in army_units:
            try:
                # Only send idle units or units far from rally point
                is_idle = getattr(unit, "is_idle", False)
                distance_to_rally = unit.distance_to(self._rally_point)

                if is_idle and distance_to_rally > 5:
                    self.bot.do(unit.move(self._rally_point))
                elif distance_to_rally > 20:  # Very far from rally
                    self.bot.do(unit.move(self._rally_point))
            except Exception:
                continue

    def _is_army_gathered(self, army_units) -> bool:
        """
        Check if army is gathered at rally point.

        Returns True if at least 70% of units are near rally point.
        """
        if not self._rally_point or not army_units:
            return True  # No rally point = consider gathered

        near_count = 0
        total = 0

        for unit in army_units:
            total += 1
            try:
                if unit.distance_to(self._rally_point) < 15:
                    near_count += 1
            except Exception:
                continue

        if total == 0:
            return True

        return (near_count / total) >= 0.7

    def _filter_army_units(self, units):
        return self._filter_units_by_type(
            units, ["ZERGLING", "ROACH", "HYDRALISK", "MUTALISK", "CORRUPTOR", "BROODLORD"]
        )

    def _filter_air_units(self, units):
        """Filter air units (Mutalisks, Corruptors, Brood Lords)"""
        return self._filter_units_by_type(
            units, ["MUTALISK", "CORRUPTOR", "BROODLORD", "VIPER"]
        )

    def _filter_ground_units(self, units):
        """Filter ground army units"""
        return self._filter_units_by_type(
            units, ["ZERGLING", "ROACH", "HYDRALISK", "RAVAGER", "ULTRALISK", "LURKER", "BANELING"]
        )

    async def _handle_air_units_separately(self, iteration: int):
        """
        Handle air units even when MicroController is active.
        This enables multitasking (ground army + air harassment).
        """
        if not hasattr(self.bot, 'units'):
            return

        air_units = self._filter_air_units(self.bot.units)
        if not self._has_units(air_units):
            return

        enemy_units = getattr(self.bot, "enemy_units", [])
        await self._handle_air_combat(air_units, enemy_units, iteration)

    async def _handle_air_combat(self, air_units, enemy_units, iteration: int):
        """
        Handle air unit combat and harassment.

        Air Unit Priority:
        1. Defend base if enemies attacking
        2. Harass enemy workers
        3. Pick off isolated units
        4. Attack with main army

        Mutalisk Target Priority:
        1. Workers (high value, easy kills)
        2. Siege units (Tanks, Colossus) - high threat
        3. Enemy air units
        4. Ground army units
        """
        game_time = getattr(self.bot, "time", 0)

        # Check if our base is under attack
        base_threatened = self._is_base_under_attack()

        # Separate Mutalisks from other air units
        mutalisks = self._filter_units_by_type(air_units, ["MUTALISK"])
        other_air = self._filter_units_by_type(air_units, ["CORRUPTOR", "BROODLORD", "VIPER"])

        # === MUTALISK MICRO ===
        if self._has_units(mutalisks):
            mutalisk_count = self._units_amount(mutalisks)

            # If base is threatened, defend
            if base_threatened:
                await self._mutalisk_defense(mutalisks, enemy_units)
            # If we have 5+ Mutalisks, start harassment
            elif mutalisk_count >= 5:
                await self._mutalisk_harass(mutalisks, enemy_units, iteration)
            # Otherwise, attack with priority targeting
            elif self._has_units(enemy_units):
                await self._mutalisk_attack(mutalisks, enemy_units)

        # === OTHER AIR UNITS ===
        if self._has_units(other_air) and self._has_units(enemy_units):
            # Corruptors: Prioritize enemy air/massive
            # Brood Lords: Stay back and attack ground
            await self._other_air_attack(other_air, enemy_units)

    async def _mutalisk_defense(self, mutalisks, enemy_units):
        """Mutalisks defend base - attack enemies near our bases."""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return

        base = self.bot.townhalls.first
        nearby_enemies = [e for e in enemy_units if e.distance_to(base.position) < 25]

        if not nearby_enemies:
            return

        # Target priority: Workers > Air > Ground
        target = self._select_mutalisk_target(nearby_enemies)
        if target:
            for muta in mutalisks:
                try:
                    self.bot.do(muta.attack(target))
                except Exception:
                    continue

    async def _mutalisk_harass(self, mutalisks, enemy_units, iteration: int):
        """
        Mutalisk harassment logic.

        Send Mutalisks to enemy base to harass workers.
        Retreat if anti-air is detected.
        """
        game_time = getattr(self.bot, "time", 0)

        # Check cooldown for harass target decision
        if game_time - self._last_air_harass_time < self._air_harass_cooldown:
            # Continue current harass or attack visible enemies
            if self._air_harass_target:
                await self._execute_harass(mutalisks, enemy_units)
                return
            elif self._has_units(enemy_units):
                await self._mutalisk_attack(mutalisks, enemy_units)
                return

        # Decide new harass target
        self._last_air_harass_time = game_time
        self._air_harass_target = self._find_harass_target()

        if self._air_harass_target:
            await self._execute_harass(mutalisks, enemy_units)
            if iteration % 100 == 0:
                print(f"[AIR HARASS] [{int(game_time)}s] Mutalisks harassing enemy base")
        else:
            # No harass target, attack normally
            if self._has_units(enemy_units):
                await self._mutalisk_attack(mutalisks, enemy_units)

    def _find_harass_target(self):
        """Find best harassment target (enemy base with workers)."""
        # Try enemy main base
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]

        # Try known enemy structures
        enemy_structures = getattr(self.bot, "enemy_structures", [])
        if enemy_structures:
            # Find townhalls
            townhall_names = ["NEXUS", "COMMANDCENTER", "ORBITALCOMMAND", "PLANETARYFORTRESS", "HATCHERY", "LAIR", "HIVE"]
            for struct in enemy_structures:
                if getattr(struct.type_id, "name", "") in townhall_names:
                    return struct.position
            # Any structure as fallback
            return enemy_structures[0].position

        return None

    async def _execute_harass(self, mutalisks, enemy_units):
        """Execute harassment - attack workers, retreat from anti-air."""
        if not self._air_harass_target:
            return

        # Check for anti-air threats near harass target
        anti_air_threats = self._get_anti_air_threats(enemy_units, self._air_harass_target)

        # ★ FIX: 뮤탈리스크는 대공 1-2기에도 치명적 → 퇴각 임계값 하향 ★
        if anti_air_threats and len(anti_air_threats) >= 1:
            # Anti-air detected, retreat immediately (Mutalisks are fragile)
            await self._mutalisk_retreat(mutalisks)
            self._air_harass_target = None
            return

        # Look for workers near harass target
        enemy_workers = [e for e in enemy_units
                        if getattr(e.type_id, "name", "") in ["SCV", "PROBE", "DRONE"]
                        and e.distance_to(self._air_harass_target) < 15]

        if enemy_workers:
            # Attack workers with bouncing logic
            await self._mutalisk_bounce_attack(mutalisks, enemy_workers)
        else:
            # Move to harass target
            for muta in mutalisks:
                try:
                    self.bot.do(muta.attack(self._air_harass_target))
                except Exception:
                    continue

    async def _zergling_early_harass(self, zerglings, enemy_units, iteration: int):
        """
        초반 저글링 견제 로직 (3-5분)

        게임 초반에 6-12 저글링으로 적 일꾼을 견제합니다.
        방어 병력이 많으면 후퇴합니다.
        """
        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            return

        game_time = getattr(self.bot, 'time', 0)

        # 게임 시간 확인 (3-5분)
        if game_time < 180 or game_time > 300:
            return

        # 저글링 수 확인 (6-12기)
        if len(zerglings) < 6 or len(zerglings) > 24:
            return

        # 견제 타겟 찾기
        harass_target = self._find_harass_target()
        if not harass_target:
            return

        # 적 방어 병력 확인 (타겟 근처 15 거리)
        enemy_combat_units = [
            e for e in enemy_units
            if hasattr(e, 'can_attack') and e.can_attack
            and getattr(e.type_id, "name", "") not in ["SCV", "PROBE", "DRONE"]
            and e.distance_to(harass_target) < 15
        ]

        # 방어 병력이 3기 이상이면 후퇴
        if len(enemy_combat_units) >= 3:
            await self._retreat_to_base(zerglings)
            if iteration % 200 == 0:
                print(f"[EARLY HARASS] [{int(game_time)}s] Zerglings retreating from defense")
            return

        # 일꾼 찾기
        enemy_workers = [
            e for e in enemy_units
            if getattr(e.type_id, "name", "") in ["SCV", "PROBE", "DRONE"]
            and e.distance_to(harass_target) < 20
        ]

        if enemy_workers:
            # 일꾼 공격
            for ling in zerglings:
                closest_worker = min(enemy_workers, key=lambda w: w.distance_to(ling))
                try:
                    self.bot.do(ling.attack(closest_worker))
                except Exception:
                    continue
            if iteration % 200 == 0:
                print(f"[EARLY HARASS] [{int(game_time)}s] {len(zerglings)} Zerglings harassing workers")
        else:
            # 일꾼이 없으면 타겟 위치로 이동
            for ling in zerglings:
                try:
                    self.bot.do(ling.attack(harass_target))
                except Exception:
                    continue

    async def _retreat_to_base(self, units):
        """유닛들을 본진으로 후퇴시킵니다."""
        if not units:
            return

        # 본진 위치 찾기
        main_base = None
        if hasattr(self.bot, 'townhalls') and self.bot.townhalls:
            main_base = self.bot.townhalls[0].position
        elif hasattr(self.bot, 'start_location'):
            main_base = self.bot.start_location

        if main_base:
            for unit in units:
                try:
                    self.bot.do(unit.move(main_base))
                except Exception:
                    continue

    def _get_anti_air_threats(self, enemy_units, position, range_check=15):
        """Get enemy units that can attack air near a position."""
        anti_air_names = [
            "MARINE", "HYDRALISK", "STALKER", "PHOENIX", "VOIDRAY",
            "VIKINGFIGHTER", "THOR", "CYCLONE", "LIBERATOR",
            "QUEEN", "CORRUPTOR", "MUTALISK", "ARCHON",
            "MISSILETURRET", "SPORECRAWLER", "PHOTONCANNON"
        ]
        return [e for e in enemy_units
                if getattr(e.type_id, "name", "") in anti_air_names
                and e.distance_to(position) < range_check]

    async def _mutalisk_bounce_attack(self, mutalisks, targets):
        """
        Mutalisk bouncing attack micro.

        Mutalisks deal splash damage in a line.
        Position to maximize bounce damage on grouped workers.
        """
        if not targets:
            return

        # Find clustered targets for maximum bounce
        best_target = None
        best_nearby_count = 0

        for target in targets:
            nearby = [t for t in targets if t.tag != target.tag and target.distance_to(t) < 3]
            if len(nearby) >= best_nearby_count:
                best_nearby_count = len(nearby)
                best_target = target

        if not best_target:
            best_target = targets[0]

        # Attack the best clustered target
        for muta in mutalisks:
            try:
                self.bot.do(muta.attack(best_target))
            except Exception:
                continue

    async def _mutalisk_retreat(self, mutalisks):
        """Retreat Mutalisks to safety."""
        retreat_pos = None

        # Retreat to our base
        if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
            retreat_pos = self.bot.townhalls.first.position
        elif hasattr(self.bot, "start_location"):
            retreat_pos = self.bot.start_location

        if retreat_pos:
            for muta in mutalisks:
                try:
                    self.bot.do(muta.move(retreat_pos))
                except Exception:
                    continue

    async def _mutalisk_attack(self, mutalisks, enemy_units):
        """Mutalisk attack with priority targeting."""
        target = self._select_mutalisk_target(enemy_units)
        if not target:
            return

        for muta in mutalisks:
            try:
                self.bot.do(muta.attack(target))
            except Exception:
                continue

    def _select_mutalisk_target(self, enemy_units):
        """
        Select best target for Mutalisks.

        Priority:
        1. Workers (high value)
        2. Siege units (Tanks, Colossus)
        3. Low HP units (easy kills)
        4. Any ground unit
        """
        if not enemy_units:
            return None

        workers = []
        siege = []
        low_hp = []
        other = []

        for enemy in enemy_units:
            name = getattr(enemy.type_id, "name", "")

            if name in ["SCV", "PROBE", "DRONE"]:
                workers.append(enemy)
            elif name in ["SIEGETANK", "SIEGETANKSIEGED", "COLOSSUS", "LIBERATOR", "WIDOWMINE"]:
                siege.append(enemy)
            elif enemy.health_percentage < 0.3:
                low_hp.append(enemy)
            else:
                other.append(enemy)

        # Return highest priority target
        if workers:
            return min(workers, key=lambda e: e.health)
        if siege:
            return siege[0]
        if low_hp:
            return min(low_hp, key=lambda e: e.health)
        if other:
            return other[0]

        return None

    async def _other_air_attack(self, air_units, enemy_units):
        """Handle Corruptors and Brood Lords."""
        corruptors = self._filter_units_by_type(air_units, ["CORRUPTOR"])
        broodlords = self._filter_units_by_type(air_units, ["BROODLORD"])

        # Corruptors: Attack enemy air or massive units
        if self._has_units(corruptors):
            air_targets = [e for e in enemy_units if getattr(e, "is_flying", False)]
            massive_targets = [e for e in enemy_units
                             if getattr(e.type_id, "name", "") in
                             ["COLOSSUS", "THOR", "BATTLECRUISER", "CARRIER", "TEMPEST", "MOTHERSHIP"]]

            target = None
            if air_targets:
                target = min(air_targets, key=lambda e: e.health)
            elif massive_targets:
                target = massive_targets[0]

            if target:
                for corr in corruptors:
                    try:
                        self.bot.do(corr.attack(target))
                    except Exception:
                        continue

        # Brood Lords: Stay back, attack ground
        if self._has_units(broodlords):
            ground_targets = [e for e in enemy_units if not getattr(e, "is_flying", False)]
            if ground_targets:
                target = min(ground_targets, key=lambda e: e.health)
                for bl in broodlords:
                    try:
                        self.bot.do(bl.attack(target))
                    except Exception:
                        continue

    def _is_base_under_attack(self) -> bool:
        """
        Check if our base is under attack.

        IMPROVED:
        - 1기 이상의 적도 위협으로 감지 (초반 러쉬 대응)
        - 게임 시간에 따른 동적 감지 (초반 더 민감)
        - 고위협 유닛은 더 넓은 범위에서 감지
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return False

        enemy_units = getattr(self.bot, "enemy_units", [])
        if not enemy_units:
            return False

        game_time = getattr(self.bot, "time", 0)

        # 고위협 유닛 목록 (더 넓은 감지 범위)
        high_threat_names = {
            "ZERGLING", "MARINE", "ZEALOT", "REAPER", "ADEPT",
            "BANELING", "ROACH", "STALKER", "MARAUDER",
            "SIEGETANK", "SIEGETANKSIEGED", "WIDOWMINE"
        }

        for th in self.bot.townhalls:
            # 일반 감지 거리
            base_range = 25 if game_time >= 180 else 30  # 초반 더 민감

            # 일반 적 확인
            nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < base_range]

            # 고위협 적은 더 넓은 범위에서 확인
            high_threat_enemies = [
                e for e in enemy_units
                if getattr(e.type_id, "name", "").upper() in high_threat_names
                and e.distance_to(th.position) < base_range + 10
            ]

            # 조건: 1기 이상의 적, 또는 고위협 적 감지
            if len(nearby_enemies) >= 1 or high_threat_enemies:
                return True

        return False

    def _filter_units_by_type(self, units, names):
        if HELPERS_AVAILABLE:
            return filter_by_type(units, names)
        if hasattr(units, "filter"):
            return units.filter(lambda u: u.type_id.name in names)
        return [u for u in units if getattr(u.type_id, "name", "") in names]

    @staticmethod
    def _has_units(units) -> bool:
        if HELPERS_AVAILABLE:
            return has_units(units)
        if hasattr(units, "exists"):
            return bool(units.exists)
        return bool(units)

    @staticmethod
    def _units_amount(units) -> int:
        if HELPERS_AVAILABLE:
            return units_amount(units)
        if hasattr(units, "amount"):
            return int(units.amount)
        return len(units)

    def _get_enemy_center(self, enemy_units):
        if HELPERS_AVAILABLE:
            return centroid(enemy_units)
        if not Point2:
            return None
        items = list(enemy_units)
        if not items:
            return None
        count = len(items)
        x_sum = sum(u.position.x for u in items)
        y_sum = sum(u.position.y for u in items)
        return Point2((x_sum / count, y_sum / count))

    def _closest_enemy(self, enemy_units, unit):
        if HELPERS_AVAILABLE:
            return closest_enemy(unit, enemy_units)
        if hasattr(enemy_units, "closest_to"):
            try:
                return enemy_units.closest_to(unit.position)
            except Exception:
                return None
        closest_unit = None
        closest_dist = None
        for enemy in enemy_units:
            try:
                dist = unit.distance_to(enemy)
            except Exception:
                continue
            if closest_dist is None or dist < closest_dist:
                closest_unit = enemy
                closest_dist = dist
        return closest_unit

    def _check_counterattack_opportunity(self, army_units, enemy_units, game_time: float) -> bool:
        """
        전투 후 역공격 기회 확인

        조건:
        1. 최근 교전이 있었음 (지난 5초 이내에 적을 본 적 있음)
        2. 아군 서플라이 > 적 서플라이 * 2 (압도적 우위)
        3. 최소 서플라이 10 이상
        4. 쿨다운 지남 (15초)

        Returns:
            True if counter attack should be launched
        """
        # Track combat (update last combat time if enemies are visible)
        if enemy_units and len(list(enemy_units)) > 0:
            self._last_combat_time = game_time

        # Check if there was recent combat
        time_since_combat = game_time - self._last_combat_time
        if time_since_combat > 5:  # No recent combat in last 5 seconds
            return False

        # Calculate army supplies
        our_supply = sum(getattr(u, "supply_cost", 1) for u in army_units)
        enemy_supply = sum(getattr(u, "supply_cost", 1) for u in enemy_units) if enemy_units else 0

        # Check cooldown (prevent spamming counter attacks)
        if not hasattr(self, "_last_counter_attack_time"):
            self._last_counter_attack_time = 0

        time_since_last_counter = game_time - self._last_counter_attack_time
        if time_since_last_counter < self._counter_attack_cooldown:
            return False

        # ★ FIX: 카운터 어택 임계값 하향 (2x → 1.4x) ★
        # 유닛 품질 고려: 저그 유닛이 대부분 저렴하므로 낮은 비율로도 공격 가능
        if our_supply >= 8 and our_supply > enemy_supply * 1.4:
            self._last_counter_attack_time = game_time  # Update cooldown
            return True

        # 적이 거의 없으면 바로 공격
        if our_supply >= 12 and enemy_supply <= 3:
            self._last_counter_attack_time = game_time
            return True

        return False

    def _get_enemy_base_location(self):
        """Get enemy base location for counter attack."""
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]
        return None

    async def _ensure_baneling_burrow(self, iteration: int):
        """맹독충 잠복 로직이 항상 실행되도록 보장"""
        try:
            # MicroController의 burrow_controller를 사용
            if not hasattr(self.bot, 'micro') or not self.bot.micro:
                return

            # UnitTypeId import 확인
            try:
                from sc2.ids.unit_typeid import UnitTypeId
            except ImportError:
                return

            # 맹독충만 필터링
            banelings = [u for u in getattr(self.bot, "units", [])
                        if hasattr(u, 'type_id') and u.type_id == UnitTypeId.BANELING]

            if not banelings:
                return

            # 적 유닛
            enemy_units = getattr(self.bot, "enemy_units", [])

            # BurrowController로 처리
            if hasattr(self.bot.micro, 'burrow_controller'):
                await self.bot.micro.burrow_controller.handle_burrow(
                    banelings, enemy_units, iteration, self.bot.do_actions, bot=self.bot
                )

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Baneling burrow error: {e}")

    # ============================================================
    # ★★★ MANDATORY BASE DEFENSE SYSTEM ★★★
    # ============================================================

    async def _check_mandatory_base_defense(self, iteration: int):
        """
        ★ 필수 기지 방어 체크 - 항상 최우선 실행 ★

        기지에 적이 침입하면:
        1. 모든 군대 즉시 귀환
        2. 일꾼도 필요시 방어 참여
        3. 퀸 우선 방어
        4. 스파인 크롤러 타겟팅

        Returns:
            위협 위치 (Point2) 또는 None
        """
        # 체크 간격 (5프레임마다)
        if iteration - self._last_defense_check < self._defense_check_interval:
            return self._defense_rally_point if self._base_defense_active else None
        self._last_defense_check = iteration

        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "enemy_units"):
            self._base_defense_active = False
            return None

        if not self.bot.townhalls.exists:
            self._base_defense_active = False
            return None

        enemy_units = self.bot.enemy_units
        if not enemy_units:
            self._base_defense_active = False
            self._defense_rally_point = None
            return None

        game_time = getattr(self.bot, "time", 0)

        # 기지별 위협 평가
        max_threat_score = 0
        threat_position = None
        threat_enemies = []

        for th in self.bot.townhalls:
            nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < 30]

            if not nearby_enemies:
                continue

            # 위협 점수 계산
            threat_score = 0
            for enemy in nearby_enemies:
                if hasattr(enemy, "can_attack") and enemy.can_attack:
                    threat_score += 2
                else:
                    threat_score += 1
                # 공중 유닛 추가 점수
                if getattr(enemy, "is_flying", False):
                    threat_score += 1

            if threat_score > max_threat_score:
                max_threat_score = threat_score
                threat_enemies = nearby_enemies
                # 적 중심 계산
                x_sum = sum(e.position.x for e in nearby_enemies)
                y_sum = sum(e.position.y for e in nearby_enemies)
                count = len(nearby_enemies)
                try:
                    from sc2.position import Point2
                    threat_position = Point2((x_sum / count, y_sum / count))
                except ImportError:
                    threat_position = nearby_enemies[0].position

        # 위협이 없으면 방어 모드 해제
        if max_threat_score == 0:
            if self._base_defense_active and iteration % 100 == 0:
                print(f"[BASE DEFENSE] [{int(game_time)}s] Threat cleared - returning to normal")
            self._base_defense_active = False
            self._defense_rally_point = None
            return None

        # ★ 위협 감지 - 방어 모드 활성화 ★
        self._base_defense_active = True
        self._defense_rally_point = threat_position

        enemy_count = len(threat_enemies)

        # 로그 출력 (5초마다)
        if iteration % 110 == 0:
            print(f"[BASE DEFENSE] [{int(game_time)}s] ★ MANDATORY DEFENSE ★ "
                  f"Enemies: {enemy_count}, Threat score: {max_threat_score}")

        # ★ 모든 군대 즉시 방어 ★
        await self._execute_mandatory_defense(threat_position, threat_enemies, iteration)

        # ★ 위험 상황: 일꾼도 방어 참여 ★
        if enemy_count >= self._worker_defense_threshold:
            await self._worker_defense(threat_position, threat_enemies, iteration)

        return threat_position

    async def _execute_mandatory_defense(self, threat_position, threat_enemies, iteration: int):
        """
        ★ 필수 방어 실행 - 모든 군대 귀환 ★
        """
        if not hasattr(self.bot, "units"):
            return

        game_time = getattr(self.bot, "time", 0)

        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            return

        # 모든 군대 유닛 수집
        army_types = {
            UnitTypeId.ZERGLING, UnitTypeId.BANELING, UnitTypeId.ROACH,
            UnitTypeId.RAVAGER, UnitTypeId.HYDRALISK, UnitTypeId.LURKER,
            UnitTypeId.MUTALISK, UnitTypeId.CORRUPTOR, UnitTypeId.ULTRALISK,
            UnitTypeId.BROODLORD, UnitTypeId.INFESTOR, UnitTypeId.VIPER
        }

        army_units = [u for u in self.bot.units if u.type_id in army_types]

        if not army_units:
            return

        # 적 중 우선순위 타겟 찾기
        priority_target = None
        for enemy in threat_enemies:
            enemy_type = getattr(enemy.type_id, "name", "").upper()
            # 시즈탱크, 메디박, 콜로서스 등 우선 제거
            if enemy_type in ["SIEGETANK", "SIEGETANKSIEGED", "MEDIVAC",
                              "COLOSSUS", "IMMORTAL", "HIGHTEMPLAR", "DISRUPTOR"]:
                priority_target = enemy
                break

        # 군대 유닛들에게 방어 명령
        for unit in army_units:
            try:
                # 이미 위협 위치 근처면 공격
                if unit.distance_to(threat_position) < 15:
                    if priority_target:
                        self.bot.do(unit.attack(priority_target))
                    elif threat_enemies:
                        closest = min(threat_enemies, key=lambda e: e.distance_to(unit))
                        self.bot.do(unit.attack(closest))
                    else:
                        self.bot.do(unit.attack(threat_position))
                else:
                    # 멀리 있으면 위협 위치로 이동
                    self.bot.do(unit.attack(threat_position))
            except Exception:
                continue

        # 로그 (10초마다)
        if iteration % 220 == 0:
            print(f"[BASE DEFENSE] [{int(game_time)}s] {len(army_units)} units defending base")

    async def _worker_defense(self, threat_position, threat_enemies, iteration: int):
        """
        ★ 일꾼 방어 - 위험 상황에서 일꾼도 싸움 ★
        """
        if not hasattr(self.bot, "workers"):
            return

        game_time = getattr(self.bot, "time", 0)
        workers = self.bot.workers

        if not workers:
            return

        # 위협 근처 일꾼만 방어 (15 거리 내)
        nearby_workers = [w for w in workers if w.distance_to(threat_position) < 15]

        if not nearby_workers:
            return

        # 최대 6명까지만 방어 참여 (경제 보존)
        defense_workers = nearby_workers[:6]

        for worker in defense_workers:
            try:
                if threat_enemies:
                    closest = min(threat_enemies, key=lambda e: e.distance_to(worker))
                    self.bot.do(worker.attack(closest))
                else:
                    self.bot.do(worker.attack(threat_position))
            except Exception:
                continue

        if iteration % 220 == 0:
            print(f"[BASE DEFENSE] [{int(game_time)}s] ★ {len(defense_workers)} WORKERS DEFENDING ★")
