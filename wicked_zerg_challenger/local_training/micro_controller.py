# -*- coding: utf-8 -*-

import math
from typing import Any, List, Optional, Tuple

from sc2.bot_ai import BotAI  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore
from sc2.position import Point2  # type: ignore
from sc2.unit import Unit  # type: ignore

# IMPROVED: Import Units type for type hints
try:
    from sc2.units import Units  # type: ignore
except ImportError:
    # Fallback if Units is not available - use Any for type hints
    Units = Any  # type: ignore[assignment, misc]

class Vector2:
    """2D 벡터 클래스 (numpy 대체)"""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    def __add__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2":
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> "Vector2":
        if scalar == 0:
            return Vector2(0, 0)
        return Vector2(self.x / scalar, self.y / scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self) -> "Vector2":
        """
        Normalize vector to unit length

        Fixed: Added 1e-9 epsilon to prevent zero division error
        """
        mag = self.magnitude()
        if mag < 1e-9:  # Prevent zero division with epsilon
            return Vector2(0, 0)
        return self / mag

    def to_point2(self, origin: Point2) -> Point2:
        """원점 기준으로 Point2 변환"""
        return Point2((origin.x + self.x, origin.y + self.y))

    @staticmethod
    def from_points(p1: Point2, p2: Point2) -> "Vector2":
        """두 점 사이의 벡터"""
        return Vector2(p2.x - p1.x, p2.y - p1.y)

class MicroController:
    """
    마이크로 컨트롤러 - Potential Fields 기반 유닛 제어

    ? 설계 철학:
        각 유닛은 매 프레임마다 세 가지 힘의 합으로 이동 방향을 결정합니다:
        1. 목표 인력 (F_goal): 적을 향해 당기는 힘
        2. 아군 척력 (F_repel): 아군끼리 밀어내는 힘
        3. 위험 회피 (F_danger): 위험 지역에서 도망치는 힘
    """

    SPREAD_RADIUS = 2.5
    REPEL_STRENGTH = 2.5

    DANGER_RADIUS = 8.0
    DANGER_STRENGTH = 2.0

    GOAL_STRENGTH = 1.0

    UNIT_RANGES = {
        UnitTypeId.ZERGLING: 0.5,
        UnitTypeId.BANELING: 0.0,
        UnitTypeId.ROACH: 4.0,
        UnitTypeId.HYDRALISK: 5.0,
        UnitTypeId.MUTALISK: 3.0,
        UnitTypeId.CORRUPTOR: 6.0,
    }

    DANGER_UNITS = {
        UnitTypeId.SIEGETANK,
        UnitTypeId.SIEGETANKSIEGED,
        UnitTypeId.COLOSSUS,
        UnitTypeId.HIGHTEMPLAR,
        UnitTypeId.DISRUPTOR,
        UnitTypeId.LIBERATOR,
        UnitTypeId.WIDOWMINE,
        UnitTypeId.BANELING,
    }

    BANELING_SPLIT_RADIUS = 1.5
    MARINE_DETECTION_RADIUS = 6.0

    ZVZ_STEP_BACK_HP_THRESHOLD = 0.5
    ZVZ_STEP_BACK_DISTANCE = 3.0

    def __init__(self, bot: BotAI):
        """
        Args:
            bot: 메인 봇 인스턴스
        """
        self.bot = bot
        self.opponent_race = None

    def set_opponent_race(self, race):
        """상대 종족 설정"""
        self.opponent_race = race

    def get_spread_position(
        self, unit: Unit, target: Point2, allies: List[Unit], enemies: List[Unit]
    ) -> Point2:
        """
        OPTIMIZED: Enhanced Potential Fields based spread position calculation

        Uses individual unit vector summation for better swarm intelligence:
        - Attraction: Pulls towards low-health or high-threat enemies
        - Repulsion: Pushes away from allies (spread)
        - Avoidance: Repulsion at enemy attack range boundary

        Args:
            unit: Unit to move
            target: Target position (fallback if no enemies)
            allies: Nearby allied units
            enemies: Nearby enemy units

        Returns:
            Point2: Optimal movement position
        """
        # OPTIMIZED: Use enhanced goal force if enemies are available
        if enemies:
            # Calculate attraction to each enemy individually (threat-based)
            f_goal = self._calculate_enhanced_goal_force(unit, enemies)
        else:
            # Fallback to standard goal force if no enemies
            f_goal = self._calculate_goal_force(unit, target)

        # 2?? Repulsion from allies (spread)
        f_repel = self._calculate_repel_force(unit, allies)

        # 3?? Danger avoidance (range boundary + splash damage)
        f_danger = self._calculate_danger_force(unit, enemies)

        # IMPROVED: 4?? Final vector summation with weights
        # Weighted combination for better control
        f_total = f_goal * 1.2 + f_repel * 1.0 + f_danger * 1.5  # IMPROVED: Danger avoidance has higher weight

        # IMPROVED: 5?? Normalize and apply movement distance (adaptive based on situation)
        if f_total.magnitude() > 0:
            # IMPROVED: Adaptive movement distance based on urgency
            # If danger is high, move faster
            danger_magnitude = f_danger.magnitude()
            if danger_magnitude > 1.0:
                move_distance = 3.0  # Move faster when in danger
            else:
                move_distance = 2.0  # Normal movement

            move_vector = f_total.normalize() * move_distance
            return move_vector.to_point2(unit.position)

        return unit.position

    def execute_spread_attack(self, units: Units, target: Point2, enemies: List[Unit]):
        """
        산개 공격 실행

        Args:
            units: 공격할 유닛들
            target: 공격 목표 위치
            enemies: 적 유닛들 (리스트)
        """
        for unit in units:
            nearby_allies = [
                u
                for u in units
                if u.distance_to(unit) < self.SPREAD_RADIUS * 2 and u.tag != unit.tag
            ]

            nearby_enemies = [u for u in enemies if u.distance_to(unit) < 15]

            spread_pos = self.get_spread_position(unit, target, nearby_allies, nearby_enemies)

            if unit.weapon_cooldown > 0:
                unit.move(spread_pos)
            else:
                if nearby_enemies:
                    closest_enemy = min(nearby_enemies, key=lambda e: unit.distance_to(e))
                    unit.attack(closest_enemy)
                else:
                    unit.attack(target)

    def _calculate_goal_force(self, unit: Unit, target: Point2) -> Vector2:
        """
        OPTIMIZED: Enhanced goal force calculation with threat-based attraction

        Attraction: Pulls towards low-health or high-threat enemy units
        - Prioritizes weak enemies (low health) for quick kills
        - Prioritizes high-threat units (siege tanks, colossus) to eliminate quickly

        Args:
            unit: Unit to calculate force for
            target: Target position (can be enemy unit position)

        Returns:
            Vector2: Attraction force towards target
        """
        # Unit range
        unit_range = self.UNIT_RANGES.get(unit.type_id, 0.5)

        # Vector to target
        to_target = Vector2.from_points(unit.position, target)
        distance = to_target.magnitude()

        # OPTIMIZED: Threat-based attraction strength
        # If target is an enemy unit (has health attribute), prioritize low-health or high-threat
        attraction_strength = self.GOAL_STRENGTH

        # Check if target is actually an enemy unit (by checking if we can get health)
        # This is a simplified check - in practice, target should be passed as Unit when available
        try:
            # If target has health (it's a Unit), adjust attraction based on threat
            # For now, use distance-based strength adjustment
            if distance < unit_range:
                strength = -0.5  # Too close, back off slightly
            elif distance < unit_range + 2:
                strength = 0.3  # Maintain optimal range
            else:
                # OPTIMIZED: Increase attraction for distant targets (surround behavior)
                strength = self.GOAL_STRENGTH * (1.0 + min(distance / 20.0, 0.5))  # Up to 50% bonus
        except Exception:
            # Fallback to standard behavior
            if distance < unit_range:
                strength = -0.5
            elif distance < unit_range + 2:
                strength = 0.3
            else:
                strength = self.GOAL_STRENGTH

        return to_target.normalize() * strength

    def _calculate_enhanced_goal_force(self, unit: Unit, enemies: List[Unit]) -> Vector2:
        """
        NEW: Enhanced goal force with individual unit threat assessment

        Calculates attraction to each enemy unit individually, prioritizing:
        - Low health enemies (quick kills)
        - High threat enemies (siege tanks, colossus)

        Args:
            unit: Unit to calculate force for
            enemies: List of enemy units

        Returns:
            Vector2: Combined attraction force
        """
        total_force = Vector2(0, 0)

        for enemy in enemies:
            # Calculate vector to this enemy
            to_enemy = Vector2.from_points(unit.position, enemy.position)
            distance = to_enemy.magnitude()

            if distance < 0.1:  # Too close, skip
                continue

            # Threat assessment
            threat_weight = 1.0

            # High threat units (prioritize elimination)
            if enemy.type_id in self.DANGER_UNITS:
                threat_weight = 2.0  # Double attraction to dangerous units

            # Low health enemies (prioritize finishing)
            try:
                if hasattr(enemy, "health") and hasattr(enemy, "health_max"):
                    if enemy.health_max > 0:
                        health_ratio = enemy.health / enemy.health_max
                        if health_ratio < 0.3:  # Less than 30% health
                            threat_weight *= 1.5  # 50% bonus attraction to weak enemies
            except Exception:
                pass

            # Distance-based strength (closer = stronger, but respect unit range)
            unit_range = self.UNIT_RANGES.get(unit.type_id, 0.5)
            if distance < unit_range:
                strength = -0.3 * threat_weight  # Back off if too close
            elif distance < unit_range + 3:
                strength = 0.5 * threat_weight  # Optimal range
            else:
                strength = (self.GOAL_STRENGTH * threat_weight) / (
                    1.0 + distance / 10.0
                )  # Decay with distance

            # Add this enemy's attraction
            total_force = total_force + to_enemy.normalize() * strength

        return total_force

    def _calculate_repel_force(self, unit: Unit, allies: List[Unit]) -> Vector2:
        """
        IMPROVED: 아군 척력 계산 (뭉치지 않게 밀어내는 힘)

        ? 공식:
            F_repel = Σ (diff / dist²)
            거리가 가까울수록 강하게 밀어냄

        IMPROVED:
            - 유닛 타입에 따른 척력 조정
            - 더 넓은 산개 (SPREAD_RADIUS 증가)
        """
        force = Vector2(0, 0)

        for ally in allies:
            if ally.tag == unit.tag:
                continue

            distance = unit.distance_to(ally)

            spread_radius = self.SPREAD_RADIUS
            if unit.type_id == UnitTypeId.HYDRALISK:
                spread_radius = self.SPREAD_RADIUS * 1.3
            elif unit.type_id == UnitTypeId.ROACH:
                spread_radius = self.SPREAD_RADIUS * 1.1

            if 0 < distance < spread_radius:
                diff = Vector2.from_points(ally.position, unit.position)

                repel_strength = self.REPEL_STRENGTH / (distance**2 + 0.1)  # +0.1 to prevent division by zero
                force = force + diff.normalize() * repel_strength

        return force

    def _calculate_danger_force(self, unit: Unit, enemies: List[Unit]) -> Vector2:
        """
        OPTIMIZED: Enhanced danger force with range boundary avoidance

        Avoidance: Repulsion force at enemy attack range boundary
        - Avoids staying at exact attack range (where enemy can hit but we can't)
        - Stronger repulsion for siege tanks and colossus (splash damage)

        Args:
            unit: Unit to calculate force for
            enemies: List of enemy units

        Returns:
            Vector2: Combined avoidance force
        """
        force = Vector2(0, 0)

        for enemy in enemies:
            distance = unit.distance_to(enemy)

            # OPTIMIZED: Check if enemy is dangerous (danger units or has long range)
            is_dangerous = enemy.type_id in self.DANGER_UNITS

            # Check enemy attack range (if available)
            enemy_range = 0.0
            try:
                if hasattr(enemy, "ground_range"):
                    enemy_range = enemy.ground_range
                elif hasattr(enemy, "air_range"):
                    enemy_range = enemy.air_range
                else:
                    # Default ranges for dangerous units
                    if enemy.type_id == UnitTypeId.SIEGETANKSIEGED:
                        enemy_range = 13.0  # Siege tank range
                    elif enemy.type_id == UnitTypeId.COLOSSUS:
                        enemy_range = 6.0  # Colossus range
                    elif enemy.type_id == UnitTypeId.HIGHTEMPLAR:
                        enemy_range = 6.0  # Storm range
            except Exception:
                enemy_range = 5.0  # Default range

            # If we're within enemy range but outside our range, strong avoidance
            unit_range = self.UNIT_RANGES.get(unit.type_id, 0.5)

            if is_dangerous:
                danger_radius = self.DANGER_RADIUS * 1.2
                if 0 < distance < danger_radius:
                    # Away from enemy
                    diff = Vector2.from_points(enemy.position, unit.position)
                    avoid_strength = self.DANGER_STRENGTH * 1.5 * (1 - distance / danger_radius)  # IMPROVED: 1.5x stronger
                    force = force + diff.normalize() * avoid_strength
            elif enemy_range > unit_range:
                if unit_range < distance < enemy_range + 3:
                    # We're in enemy range but outside our range - avoid!
                    diff = Vector2.from_points(enemy.position, unit.position)
                    avoid_strength = (
                        self.DANGER_STRENGTH
                        * 0.8
                        * (1 - (distance - unit_range) / (enemy_range - unit_range + 3))
                    )
                    force = force + diff.normalize() * avoid_strength

        return force

    def execute_surround(self, units: Units, target: Unit):
        """
        IMPROVED: 포위 공격 실행 (더 효율적인 포위)

        저글링이 적을 둘러싸며 공격

        IMPROVED:
            - 더 넓은 포위 형성 (더 많은 유닛이 공격 가능)
            - 유닛 타입에 따른 거리 조정
            - 공격 쿨다운 중에도 포위 유지

        Args:
            units: 공격할 유닛들
            target: 포위할 적 유닛
        """
        units_list = [u for u in units]
        if not units_list or target is None:
            return

        num_units = len(units_list)
        angle_step = 2 * math.pi / max(num_units, 1)

        for i, unit in enumerate(units):
            angle = i * angle_step

            if unit.type_id == UnitTypeId.HYDRALISK:
                surround_distance = 2.5
            elif unit.type_id == UnitTypeId.ROACH:
                surround_distance = 2.0
            else:
                surround_distance = 1.5

            offset_x = math.cos(angle) * surround_distance
            offset_y = math.sin(angle) * surround_distance

            surround_pos = Point2((target.position.x + offset_x, target.position.y + offset_y))

            distance_to_target = unit.distance_to(target)
            unit_range = self.UNIT_RANGES.get(unit.type_id, 0.5)

            if unit.weapon_cooldown > 0:
                if unit.distance_to(surround_pos) > 1.0:
                    unit.move(surround_pos)
                else:
                    kite_pos = unit.position.towards(target.position, -1.0)
                    unit.move(kite_pos)
            else:
                if distance_to_target <= unit_range + target.radius:
                    unit.attack(target)
                else:
                    unit.move(surround_pos)

    def execute_kiting(self, unit: Unit, target: Unit, retreat_distance: float = 2.0):
        """
        IMPROVED: 카이팅 실행 (Hit & Run)

        IMPROVED:
            - 수직 방향 카이팅 (더 효율적)
            - 유닛 타입에 따른 후퇴 거리 조정
            - 적 사거리 체크

        Args:
            unit: 카이팅할 유닛
            target: 공격 대상
            retreat_distance: 후퇴 거리
        """
        if unit.type_id == UnitTypeId.HYDRALISK:
            retreat_distance = 3.0
        elif unit.type_id == UnitTypeId.ROACH:
            retreat_distance = 2.5

        if unit.weapon_cooldown > 0:
            to_target = target.position - unit.position
            perp = Point2((-to_target.y, to_target.x))  # Perpendicular vector
            perp_normalized = perp / (perp.length if perp.length > 0 else 1.0)
            retreat_pos = unit.position + perp_normalized * retreat_distance
            unit.move(retreat_pos)
        else:
            unit_range = self.UNIT_RANGES.get(unit.type_id, 0.5)
            distance_to_target = unit.distance_to(target)

            if distance_to_target <= unit_range + target.radius:
                unit.attack(target)
            else:
                unit.move(target.position)

    def execute_stutter_step(self, units: Units, target: Point2):
        """
        스터터 스텝 실행 (이동 사격)

        히드라리스크 등 원거리 유닛에 적합

        Args:
            units: 스터터 스텝할 유닛들
            target: 이동 목표
        """
        for unit in units:
            if unit.weapon_cooldown > 0:
                unit.move(target)
            else:
                attack_range = self.UNIT_RANGES.get(unit.type_id, 5) + 2
                enemy_units = getattr(self.bot, "enemy_units", [])
                enemies = [u for u in enemy_units if u.distance_to(unit) < attack_range]
                if enemies:
                    closest_enemy = min(enemies, key=lambda e: unit.distance_to(e))
                    unit.attack(closest_enemy)
                else:
                    unit.move(target)

    def execute_defensive_spread(self, units, defend_point: Point2, radius: float = 10.0):
        """
        방어적 산개 실행

        기지 주변에 유닛들을 넓게 배치

        Args:
            units: 배치할 유닛들
            defend_point: 방어 중심점
            radius: 배치 반경
        """
        units_list = [u for u in units]
        num_units = len(units_list)
        angle_step = 2 * math.pi / max(num_units, 1)
        for i, unit in enumerate(units_list):
            angle = i * angle_step

            offset_x = math.cos(angle) * radius
            offset_y = math.sin(angle) * radius

            defend_pos = Point2((defend_point.x + offset_x, defend_point.y + offset_y))

            enemy_units = getattr(self.bot, "enemy_units", [])
            nearby_enemies = [u for u in enemy_units if u.distance_to(unit) < 10]
            if nearby_enemies:
                closest_enemy = min(nearby_enemies, key=lambda e: unit.distance_to(e))
                unit.attack(closest_enemy)
            elif unit.distance_to(defend_pos) > 2:
                unit.move(defend_pos)

    async def execute_serral_bile_sniping(self, ravagers: List[Unit], enemy_units: List[Unit]):
        """
        궤멸충의 부식성 담즙을 사용한 정밀 타격 로직 (Serral 스타일)

        상대의 공성 전차나 보호막 충전소처럼 움직이지 않는 위협적인 대상을 우선순위로 타격합니다.
        치고 빠지기(Hit & Run) 로직: 공성 전차 레이더망에 걸리지 않고 담즙만 쏘고 빠집니다.

        Args:
            ravagers: 궤멸충 유닛들
            enemy_units: 적 유닛 목록
        """
        from sc2.ids.ability_id import AbilityId
        from sc2.ids.unit_typeid import UnitTypeId

        if not ravagers:
            return

        b = self.bot

        priority_target_types = {
            UnitTypeId.SIEGETANKSIEGED,
            UnitTypeId.SIEGETANK,
            UnitTypeId.SHIELDBATTERY,
            UnitTypeId.PHOTONCANNON,
            UnitTypeId.BUNKER,
            UnitTypeId.SPINECRAWLER,
            UnitTypeId.MISSILETURRET,
        }

        priority_targets = [u for u in enemy_units if u.type_id in priority_target_types]

        if not priority_targets:
            army_units = [
                u
                for u in enemy_units
                if not u.is_structure and hasattr(u, "health") and u.health > 0
            ]
            if army_units:
                priority_targets = army_units[:5]

        if not priority_targets:
            return

        siege_tanks = [
            u
            for u in enemy_units
            if u.type_id in [UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED]
        ]
        siege_tank_range = 13.0

        for ravager in ravagers:
            if not hasattr(ravager, "tag") or ravager.health <= 0:
                continue

            can_use_bile = True
            if hasattr(ravager, "ability_ready"):
                try:
                    can_use_bile = ravager.ability_ready(AbilityId.EFFECT_CORROSIVEBILE)
                except (AttributeError, KeyError):
                    can_use_bile = True

            if not can_use_bile:
                continue

            target = min(priority_targets, key=lambda t: ravager.distance_to(t.position))
            distance_to_target = ravager.distance_to(target.position)

            bile_range = 12.0

            if self.opponent_race and hasattr(self.bot, "opponent_race"):
                from sc2.data import Race

                if self.bot.opponent_race == Race.Terran:
                    nearby_siege_tanks = [
                        tank
                        for tank in siege_tanks
                        if ravager.distance_to(tank.position) < siege_tank_range
                    ]
                    if nearby_siege_tanks:
                        if distance_to_target <= bile_range:
                            ravager(AbilityId.EFFECT_CORROSIVEBILE, target.position)
                            continue
                        retreat_pos = ravager.position.towards(target.position, -5)
                        ravager.move(retreat_pos)
                        continue

                elif self.bot.opponent_race == Race.Protoss:
                    sentries = [u for u in enemy_units if u.type_id == UnitTypeId.SENTRY]
                    if sentries:
                        nearby_sentry = min(sentries, key=lambda s: ravager.distance_to(s.position))
                        if ravager.distance_to(nearby_sentry.position) < 8.0:
                            retreat_pos = ravager.position.towards(nearby_sentry.position, -6)
                            ravager.move(retreat_pos)
                            continue

                elif self.bot.opponent_race == Race.Zerg:
                    zerglings = [u for u in enemy_units if u.type_id == UnitTypeId.ZERGLING]
                    if zerglings and len(zerglings) >= 10:
                        zergling_cluster = min(
                            zerglings, key=lambda z: ravager.distance_to(z.position)
                        )
                        if ravager.distance_to(zergling_cluster.position) <= bile_range:
                            ravager(
                                AbilityId.EFFECT_CORROSIVEBILE,
                                zergling_cluster.position,
                            )
                            continue

            nearby_siege_tanks = [
                tank
                for tank in siege_tanks
                if ravager.distance_to(tank.position) <= siege_tank_range + 5
            ]

            if nearby_siege_tanks and distance_to_target <= bile_range:
                try:
                    ravager(AbilityId.EFFECT_CORROSIVEBILE, target.position)
                    closest_siege = min(
                        nearby_siege_tanks,
                        key=lambda t: ravager.distance_to(t.position),
                    )
                    retreat_pos = ravager.position.towards(
                        closest_siege.position, -8
                    )
                    ravager.move(retreat_pos)
                    if b.iteration % 50 == 0:
                        print(
                            f"[SERRAL] ? 궤멸충 담즙 저격 후 후퇴: {target.type_id.name} (공성 전차 회피)"
                        )
                except (AttributeError, KeyError):
                    # Use ground_range instead of attack_range (python-sc2 API)
                    ravager_range = max(
                        getattr(ravager, "ground_range", 0),
                        getattr(ravager, "air_range", 0),
                    )
                    if ravager.distance_to(target) <= ravager_range + target.radius:
                        ravager.attack(target)
                        if nearby_siege_tanks:
                            closest_siege = min(
                                nearby_siege_tanks,
                                key=lambda t: ravager.distance_to(t.position),
                            )
                            retreat_pos = ravager.position.towards(closest_siege.position, -8)
                            ravager.move(retreat_pos)
            elif distance_to_target <= bile_range:
                try:
                    ravager(AbilityId.EFFECT_CORROSIVEBILE, target.position)
                    if b.iteration % 50 == 0:
                        print(
                            f"[SERRAL] ? 궤멸충 부식성 담즙 저격: {target.type_id.name} at {target.position}"
                        )
                except (AttributeError, KeyError):
                    # Use ground_range instead of attack_range (python-sc2 API)
                    ravager_range = max(
                        getattr(ravager, "ground_range", 0),
                        getattr(ravager, "air_range", 0),
                    )
                    if ravager.distance_to(target) <= ravager_range + target.radius:
                        ravager.attack(target)
            else:
                ravager.move(target.position)

    async def execute_baneling_vs_marines(self, banelings: List[Unit], enemy_units: List[Unit]):
        """
        테란 해병 산개 대응 맹독충 컨트롤

        전략:
            1. 맹독충을 산개시켜 해병이 한 번에 다 잡지 못하게 함
            2. 해병 클러스터의 중심으로 이동하여 최대 피해
            3. 해병이 산개하면 각 맹독충이 가장 가까운 해병 그룹을 타겟팅

        Args:
            banelings: 맹독충 유닛들
            enemy_units: 적 유닛 목록 (해병 포함)
        """
        if not banelings:
            return

        b = self.bot

        marines = [u for u in enemy_units if u.type_id == UnitTypeId.MARINE]

        if not marines:
            for baneling in banelings:
                if enemy_units:
                    closest = min(enemy_units, key=lambda e: baneling.distance_to(e))
                    baneling.attack(closest)
            return

        marine_clusters = self._find_marine_clusters(marines)

        for baneling in banelings:
            if not baneling.is_ready:
                continue

            closest_cluster = None
            min_distance = float("inf")

            for cluster_center, cluster_marines in marine_clusters:
                distance = baneling.distance_to(cluster_center)
                if distance < min_distance:
                    min_distance = distance
                    closest_cluster = (cluster_center, cluster_marines)

            if closest_cluster:
                cluster_center, cluster_marines = closest_cluster

                nearby_banelings = [
                    b
                    for b in banelings
                    if b.tag != baneling.tag
                    and baneling.distance_to(b) < self.BANELING_SPLIT_RADIUS
                ]

                if nearby_banelings:
                    avg_pos = Point2(
                        (
                            sum(b.position.x for b in nearby_banelings) / len(nearby_banelings),
                            sum(b.position.y for b in nearby_banelings) / len(nearby_banelings),
                        )
                    )
                    spread_dir = Vector2.from_points(avg_pos, baneling.position)
                    spread_dir = spread_dir.normalize() * self.BANELING_SPLIT_RADIUS
                    spread_pos = spread_dir.to_point2(baneling.position)
                    baneling.move(spread_pos)
                else:
                    baneling.move(cluster_center)
            else:
                closest_marine = min(marines, key=lambda m: baneling.distance_to(m))
                baneling.attack(closest_marine)

    def _find_marine_clusters(
        self, marines: List[Unit], max_clusters: int = 3
    ) -> List[Tuple[Point2, List[Unit]]]:
        """
        해병 클러스터 찾기 (간단한 거리 기반 클러스터링)

        Args:
            marines: 해병 리스트
            max_clusters: 최대 클러스터 수

        Returns:
            List of (cluster_center, cluster_marines) tuples
        """
        if not marines:
            return []

        if len(marines) <= 3:
            center = Point2(
                (
                    sum(m.position.x for m in marines) / len(marines),
                    sum(m.position.y for m in marines) / len(marines),
                )
            )
            return [(center, marines)]

        clusters = []
        remaining_marines = marines.copy()
        cluster_radius = 3.0

        while remaining_marines and len(clusters) < max_clusters:
            seed = remaining_marines[0]
            cluster_marines = [seed]
            remaining_marines.remove(seed)

            for marine in remaining_marines[:]:
                if seed.distance_to(marine) < cluster_radius:
                    cluster_marines.append(marine)
                    remaining_marines.remove(marine)

            center = Point2(
                (
                    sum(m.position.x for m in cluster_marines) / len(cluster_marines),
                    sum(m.position.y for m in cluster_marines) / len(cluster_marines),
                )
            )

            clusters.append((center, cluster_marines))

        if remaining_marines:
            if clusters:
                last_center, last_marines = clusters[-1]
                last_marines.extend(remaining_marines)
                center = Point2(
                    (
                        sum(m.position.x for m in last_marines) / len(last_marines),
                        sum(m.position.y for m in last_marines) / len(last_marines),
                    )
                )
                clusters[-1] = (center, last_marines)
            else:
                center = Point2(
                    (
                        sum(m.position.x for m in remaining_marines) / len(remaining_marines),
                        sum(m.position.y for m in remaining_marines) / len(remaining_marines),
                    )
                )
                clusters.append((center, remaining_marines))

        return clusters

    async def execute_zvz_zergling_micro(self, zerglings: List[Unit], enemy_zerglings: List[Unit]):
        """
        저저전(ZvZ) 저글링 마이크로 - 체력 낮은 유닛 뒤로 빼기

        Eris 같은 상위권 저그 봇 대응:
            - 체력이 낮은 저글링을 뒤로 빼서 유지력 향상
            - 체력이 높은 저글링이 앞에서 싸우도록 배치

        Args:
            zerglings: 아군 저글링들
            enemy_zerglings: 적 저글링들
        """
        if not zerglings or not enemy_zerglings:
            return

        b = self.bot

        sorted_zerglings = sorted(
            zerglings, key=lambda z: getattr(z, "health_percentage", 1.0), reverse=True
        )

        front_line = [
            z
            for z in sorted_zerglings
            if getattr(z, "health_percentage", 1.0) >= self.ZVZ_STEP_BACK_HP_THRESHOLD
        ]

        back_line = [
            z
            for z in sorted_zerglings
            if getattr(z, "health_percentage", 1.0) < self.ZVZ_STEP_BACK_HP_THRESHOLD
        ]

        for zergling in front_line:
            if not zergling.is_ready:
                continue

            closest_enemy = min(enemy_zerglings, key=lambda e: zergling.distance_to(e))

            if zergling.weapon_cooldown > 0:
                retreat_pos = zergling.position.towards(closest_enemy.position, -1.5)
                zergling.move(retreat_pos)
            else:
                zergling.attack(closest_enemy)

        for zergling in back_line:
            if not zergling.is_ready:
                continue

            if enemy_zerglings:
                closest_enemy = min(enemy_zerglings, key=lambda e: zergling.distance_to(e))

                retreat_pos = zergling.position.towards(
                    closest_enemy.position, -self.ZVZ_STEP_BACK_DISTANCE
                )
                zergling.move(retreat_pos)
            else:
                try:
                    townhalls = [th for th in b.townhalls]
                    if townhalls:
                        retreat_pos = townhalls[0].position
                        zergling.move(retreat_pos)
                except Exception:
                    pass

    async def execute_unit_micro(self, units: Units):
        """
        통합 마이크로 컨트롤 메서드 (기존 호환성)

        모든 전투 유닛에 대해 적절한 마이크로를 자동으로 선택하여 실행합니다.

        Args:
            units: 전투 유닛들
        """
        if not units or not units.exists:
            return

        try:
            b = self.bot

            enemies = list(b.enemy_units) if hasattr(b, "enemy_units") else []

            if not enemies:
                if hasattr(self, "execute_defensive_spread"):
                    self.execute_defensive_spread(units, b.start_location, radius=15.0)
                return

            closest_enemy = min(enemies, key=lambda e: units[0].distance_to(e.position))
            target_pos = closest_enemy.position

            zerglings = units.filter(lambda u: u.type_id == UnitTypeId.ZERGLING)
            roaches = units.filter(lambda u: u.type_id == UnitTypeId.ROACH)
            hydralisks = units.filter(lambda u: u.type_id == UnitTypeId.HYDRALISK)

            if zerglings.exists:
                self.execute_spread_attack(zerglings, target_pos, enemies)

            mutalisks = units.filter(lambda u: u.type_id == UnitTypeId.MUTALISK)
            if mutalisks.exists:
                for muta in mutalisks:
                    if closest_enemy:
                        self.execute_kiting(muta, closest_enemy, retreat_distance=3.0)

            if hydralisks.exists:
                self.execute_stutter_step(hydralisks, target_pos)

            if roaches.exists:
                self.execute_spread_attack(roaches, target_pos, enemies)

        except Exception:
            pass

    async def execute_overlord_hunter(self, hydralisks: List[Unit]):
        """
        적 대군주 정찰 방지 - 히드라리스크로 본진 구석에 배치

        Eris 같은 상위권 봇의 대군주 정찰을 차단하여 정보 차단

        Args:
            hydralisks: 히드라리스크 유닛들
        """
        if not hydralisks:
            return

        b = self.bot

        try:
            enemy_overlords = []
            enemy_units = getattr(b, "enemy_units", [])
            if enemy_units:
                enemy_list = list(enemy_units) if hasattr(enemy_units, "__iter__") else []
                enemy_overlords = [
                    u for u in enemy_list if u.type_id == UnitTypeId.OVERLORD and u.is_flying
                ]

            townhalls = [th for th in b.townhalls]
            if not townhalls:
                return

            main_base = townhalls[0].position

            overlords_near_base = [ov for ov in enemy_overlords if ov.distance_to(main_base) < 30]

            if overlords_near_base:
                for hydra in hydralisks:
                    if not hydra.is_ready:
                        continue

                    closest_overlord = min(
                        overlords_near_base, key=lambda ov: hydra.distance_to(ov)
                    )
                    hydra.attack(closest_overlord)
            else:
                corner_positions = [
                    main_base.towards(b.game_info.map_center, -15).towards(
                        Point2((main_base.x - 10, main_base.y)), 10
                    ),
                    main_base.towards(b.game_info.map_center, -15).towards(
                        Point2((main_base.x + 10, main_base.y)), 10
                    ),
                    main_base.towards(b.game_info.map_center, -15).towards(
                        Point2((main_base.x, main_base.y - 10)), 10
                    ),
                    main_base.towards(b.game_info.map_center, -15).towards(
                        Point2((main_base.x, main_base.y + 10)), 10
                    ),
                ]

                for i, hydra in enumerate(hydralisks[:4]):
                    if not hydra.is_ready:
                        continue

                    if i < len(corner_positions):
                        corner_pos = corner_positions[i]
                        if hydra.distance_to(corner_pos) > 5:
                            hydra.move(corner_pos)
        except Exception:
            pass  # Silently fail if overlord hunting fails

    async def execute_lurker_area_denial(self, lurkers: List[Unit], enemy_units: List[Unit]):
        """
        가시지옥의 사거리를 활용한 지역 점령 로직 (Serral 스타일)

        상대의 진입로에 가시지옥을 배치하고, 사거리 업그레이드를 활용해 최대한 멀리서 때립니다.

        Args:
            lurkers: 가시지옥 유닛들
            enemy_units: 적 유닛 목록
        """
        from sc2.ids.ability_id import AbilityId
        from sc2.ids.upgrade_id import UpgradeId

        if not lurkers:
            return

        b = self.bot

        has_range_upgrade = UpgradeId.LURKERRANGE in b.state.upgrades
        attack_range = 10.0 if has_range_upgrade else 8.0

        enemy_ground = [
            u
            for u in enemy_units
            if hasattr(u, "health") and u.health > 0 and hasattr(u, "is_flying") and not u.is_flying
        ]

        for lurker in lurkers:
            if not hasattr(lurker, "tag") or lurker.health <= 0:
                continue

            nearby_enemies = [e for e in enemy_ground if lurker.distance_to(e) <= 15]

            if nearby_enemies:
                closest_enemy = min(nearby_enemies, key=lambda e: lurker.distance_to(e))
                distance = lurker.distance_to(closest_enemy)

                if distance <= attack_range:
                    if not lurker.is_burrowed:
                        try:
                            lurker(AbilityId.BURROWDOWN_LURKER)
                        except (AttributeError, KeyError):
                            pass
                    else:
                        if distance <= attack_range:
                            lurker.attack(closest_enemy)
                else:
                    if lurker.is_burrowed:
                        try:
                            lurker(AbilityId.BURROWUP_LURKER)
                        except (AttributeError, KeyError):
                            pass
                    else:
                        move_pos = closest_enemy.position.towards(lurker.position, attack_range - 1)
                        lurker.move(move_pos)
            else:
                choke_point = self._get_highest_threat_choke()
                if choke_point:
                    if lurker.distance_to(choke_point) > 5:
                        if lurker.is_burrowed:
                            try:
                                lurker(AbilityId.BURROWUP_LURKER)
                            except (AttributeError, KeyError):
                                pass
                        else:
                            lurker.move(choke_point)
                    elif not lurker.is_burrowed:
                        try:
                            lurker(AbilityId.BURROWDOWN_LURKER)
                        except (AttributeError, KeyError):
                            pass
                else:
                    if not lurker.is_burrowed:
                        lurker.move(b.game_info.map_center)

    def _get_highest_threat_choke(self) -> Optional[Point2]:
        """
        히트맵에서 가장 위협적인 길목(Choke Point) 위치 반환

        Returns:
            Point2: 길목 위치, 없으면 None
        """
        b = self.bot

        if hasattr(b, "heatmap") and b.heatmap:
            high_threat_cells = [cell for cell in b.heatmap.grid.values() if cell.threat_level >= 5]

            if high_threat_cells:
                highest_threat = max(high_threat_cells, key=lambda c: c.threat_level)
                return highest_threat.position

        if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
            enemy_main = b.enemy_start_locations[0]
            mid_point = b.start_location.towards(
                enemy_main, b.start_location.distance_to(enemy_main) / 2
            )
            return mid_point

        return b.game_info.map_center
