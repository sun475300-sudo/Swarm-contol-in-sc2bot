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
            "base_defense": 100,      # Defend our base
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

        # === RALLY POINT SYSTEM ===
        # Rally point for army units to gather before attacking
        self._rally_point = None
        self._last_rally_update = 0
        self._rally_update_interval = 30  # Update rally point every 30 seconds
        self._min_army_for_attack = 15  # Minimum supply before attacking

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

        Multitasking Logic:
        1. Evaluate all possible tasks and their priorities
        2. Assign units to tasks based on priority
        3. Execute all tasks in parallel

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            # Clean up stale unit assignments
            self._cleanup_assignments()

            # Skip if MicroController is handling movement
            # This prevents dual command conflicts (both issuing move/attack)
            if hasattr(self.bot, 'micro') and self.bot.micro is not None:
                # CombatManager only updates targeting info, no direct commands
                # MicroController will handle actual movement
                # BUT still handle air unit harassment (multitasking)
                await self._handle_air_units_separately(iteration)
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

        # === TASK 3: Main Army Attack ===
        ground_army = self._filter_ground_units(army_units)
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
        """Check if any base is threatened and return threat position."""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return None

        for th in self.bot.townhalls:
            nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < 25]
            if len(nearby_enemies) >= 2:
                # Return position of enemies
                return self._get_enemy_center(nearby_enemies)

        return None

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
        """Execute base defense task."""
        if not threat_position:
            return

        for unit in units:
            try:
                await self.bot.do(unit.attack(threat_position))
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
                        await self.bot.do(unit.move(target_pos))
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
                                await self.bot.do(unit.move(retreat_pos))
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
                    await self.bot.do(unit.attack(closest_enemy))
        except Exception:
            pass

    async def _offensive_attack(self, army_units, iteration: int):
        """
        선제 공격 로직 - 적 유닛이 보이지 않을 때 적 기지 공격

        Uses rally point system:
        1. Army gathers at rally point until minimum supply reached
        2. Once enough army, attack enemy base together
        3. Rally point is between our natural and center of map

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

            # 적 시작 위치로 공격
            enemy_start = None
            if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                enemy_start = self.bot.enemy_start_locations[0]

            if not enemy_start:
                return

            # Check if army is gathered (most units near rally point)
            if self._rally_point and not self._is_army_gathered(army_units):
                await self._gather_at_rally_point(army_units, iteration)
                return

            # 매 50 프레임마다 공격 명령 갱신
            if iteration % 50 != 0:
                return

            # 아군 유닛들을 적 기지로 공격 명령
            for unit in list(army_units)[:30]:  # 최대 30개 유닛
                try:
                    if hasattr(unit, "is_idle") and unit.is_idle:
                        await self.bot.do(unit.attack(enemy_start))
                    elif not hasattr(unit, "is_attacking") or not unit.is_attacking:
                        await self.bot.do(unit.attack(enemy_start))
                except Exception:
                    continue

            if iteration % 200 == 0:
                print(f"[OFFENSIVE] [{int(self.bot.time)}s] Attacking enemy base with {army_supply} supply army")

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Offensive attack error: {e}")

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
                    await self.bot.do(unit.move(self._rally_point))
                elif distance_to_rally > 20:  # Very far from rally
                    await self.bot.do(unit.move(self._rally_point))
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
                    await self.bot.do(muta.attack(target))
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

        if anti_air_threats and len(anti_air_threats) >= 3:
            # Too much anti-air, retreat
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
                    await self.bot.do(muta.attack(self._air_harass_target))
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
                await self.bot.do(muta.attack(best_target))
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
                    await self.bot.do(muta.move(retreat_pos))
                except Exception:
                    continue

    async def _mutalisk_attack(self, mutalisks, enemy_units):
        """Mutalisk attack with priority targeting."""
        target = self._select_mutalisk_target(enemy_units)
        if not target:
            return

        for muta in mutalisks:
            try:
                await self.bot.do(muta.attack(target))
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
                        await self.bot.do(corr.attack(target))
                    except Exception:
                        continue

        # Brood Lords: Stay back, attack ground
        if self._has_units(broodlords):
            ground_targets = [e for e in enemy_units if not getattr(e, "is_flying", False)]
            if ground_targets:
                target = min(ground_targets, key=lambda e: e.health)
                for bl in broodlords:
                    try:
                        await self.bot.do(bl.attack(target))
                    except Exception:
                        continue

    def _is_base_under_attack(self) -> bool:
        """Check if our base is under attack."""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return False

        enemy_units = getattr(self.bot, "enemy_units", [])
        if not enemy_units:
            return False

        for th in self.bot.townhalls:
            nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < 20]
            if len(nearby_enemies) >= 3:
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
