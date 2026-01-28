# -*- coding: utf-8 -*-
"""
Optimum Defense Squad - 최적 방어 병력 계산 시스템

리퍼 1마리에 저글링 100마리가 회군하는 비효율 방지:
- 적 위협 수준(Threat Value) 계산
- 최소 병력(+20% 여유분)만 차출
- 나머지는 전선 유지 또는 생산 지속
"""

from typing import Dict, List, Tuple, Optional
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        ZERGLING = "ZERGLING"
        BANELING = "BANELING"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        QUEEN = "QUEEN"
        MUTALISK = "MUTALISK"
    Point2 = tuple


class OptimumDefenseSquad:
    """
    ★ Optimum Defense Squad ★

    적 위협을 정확히 평가하고
    제압에 필요한 최소 병력(+20% 여유분)만 차출합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("OptimumDefense")

        # ★ 체크 주기 ★
        self.last_check = 0
        self.check_interval = 11  # 약 0.5초마다

        # ★ 유닛 전투력 값 (Combat Power) ★
        self.unit_combat_values = {
            # Zerg
            "ZERGLING": 5,
            "BANELING": 15,
            "ROACH": 20,
            "RAVAGER": 30,
            "HYDRALISK": 25,
            "LURKER": 40,
            "LURKERMP": 40,
            "MUTALISK": 22,
            "CORRUPTOR": 20,
            "QUEEN": 18,
            "ULTRALISK": 80,
            "BROODLORD": 70,

            # Terran
            "MARINE": 8,
            "MARAUDER": 18,
            "REAPER": 12,
            "HELLION": 15,
            "HELLIONTANK": 25,
            "SIEGETANK": 45,
            "SIEGETANKSIEGED": 50,
            "THOR": 55,
            "VIKING": 20,
            "VIKINGFIGHTER": 18,
            "MEDIVAC": 5,
            "BANSHEE": 30,
            "RAVEN": 10,
            "BATTLECRUISER": 100,
            "LIBERATOR": 35,
            "WIDOWMINE": 20,

            # Protoss
            "ZEALOT": 20,
            "STALKER": 22,
            "SENTRY": 10,
            "ADEPT": 18,
            "HIGHTEMPLAR": 15,
            "DARKTEMPLAR": 35,
            "ARCHON": 50,
            "IMMORTAL": 40,
            "COLOSSUS": 60,
            "DISRUPTOR": 45,
            "PHOENIX": 18,
            "VOIDRAY": 35,
            "ORACLE": 20,
            "CARRIER": 100,
            "TEMPEST": 55,
        }

        # ★ 현재 방어 작전 ★
        self.active_defense: Optional[Dict] = None
        self.defense_cooldown = 0
        self.defending_unit_tags = set()  # Currently defending units

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 1. 쿨다운 체크 (약 0.5초마다 실행)
            if iteration - self.last_check < self.check_interval:
                return
            self.last_check = iteration

            # 2. 위협 감지 및 대응
            await self._manage_defense()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[DEFENSE_ERROR] on_step error: {e}")

    async def _manage_defense(self) -> None:
        """모든 기지에 대한 방어 관리"""
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "enemy_units"):
            return

        current_defenders = set()
        townhalls = self.bot.townhalls.ready

        for th in townhalls:
            # 기지 근처 적 감지 (반경 20)
            threats = [e for e in self.bot.enemy_units 
                      if e.distance_to(th.position) < 20 and not e.is_flying] # 지상 위협 우선
            
            # 공중 유닛도 포함하되, 스포어 범위 밖이면 무시? -> 일단 단순히 거리로 체크
            air_threats = [e for e in self.bot.enemy_units 
                          if e.is_flying and e.distance_to(th.position) < 15]
            
            combined_threats = threats + air_threats
            if not combined_threats:
                continue

            # 위협 위치 (적 유닛들의 평균 위치)
            count = len(combined_threats)
            avg_x = sum(e.position.x for e in combined_threats) / count
            avg_y = sum(e.position.y for e in combined_threats) / count
            threat_pos = Point2((avg_x, avg_y))

            # 방어 병력 계산
            defense_plan = await self.calculate_defense_force(threat_pos, threat_radius=20.0)
            
            # 병력 배치
            if defense_plan["required_units"]:
                await self.deploy_defense_force(defense_plan, threat_pos)
                
                # 방어 중인 유닛 태그 기록
                for tag in defense_plan.get("unit_tags", []):
                    current_defenders.add(tag)

        # 방어 중인 유닛 목록 업데이트 (CombatManager 등에서 참조 가능하게)
        self.defending_unit_tags = current_defenders


    async def calculate_defense_force(
        self,
        threat_position: Point2,
        threat_radius: float = 15.0
    ) -> Dict:
        """
        주어진 위치의 적 위협을 평가하고 필요한 방어 병력 계산

        Args:
            threat_position: 위협 위치
            threat_radius: 위협 감지 반경

        Returns:
            {
                "threat_value": int,
                "required_units": {unit_type: count},
                "unit_tags": [tag1, tag2, ...],
                "overkill": bool
            }
        """
        if not hasattr(self.bot, "enemy_units"):
            return {"threat_value": 0, "required_units": {}, "unit_tags": [], "overkill": False}

        # ★ 1. 위협 평가 ★
        threat_value = 0
        enemy_composition = {}

        for enemy in self.bot.enemy_units:
            distance = enemy.position.distance_to(threat_position)
            if distance <= threat_radius:
                type_name = getattr(enemy.type_id, "name", "").upper()
                combat_value = self.unit_combat_values.get(type_name, 10)
                threat_value += combat_value

                enemy_composition[type_name] = enemy_composition.get(type_name, 0) + 1

        if threat_value == 0:
            return {"threat_value": 0, "required_units": {}, "unit_tags": [], "overkill": False}

        # ★ 2. 필요 병력 계산 (+20% 여유분) ★
        required_power = int(threat_value * 1.2)

        # ★ 3. 최적 방어 조합 선택 ★
        required_units, unit_tags = self._select_defense_units(
            threat_position,
            required_power,
            enemy_composition
        )

        game_time = getattr(self.bot, "time", 0)
        self.logger.info(
            f"[{int(game_time)}s] ★ OPTIMUM DEFENSE ★\n"
            f"  Threat Value: {threat_value}\n"
            f"  Required Power: {required_power} (+20%)\n"
            f"  Enemy: {enemy_composition}\n"
            f"  Defense Force: {required_units}\n"
            f"  Unit Count: {len(unit_tags)}"
        )

        return {
            "threat_value": threat_value,
            "required_power": required_power,
            "required_units": required_units,
            "unit_tags": unit_tags,
            "overkill": False
        }

    def _select_defense_units(
        self,
        threat_position: Point2,
        required_power: int,
        enemy_composition: Dict
    ) -> Tuple[Dict, List]:
        """
        최적 방어 유닛 선택

        Args:
            threat_position: 위협 위치
            required_power: 필요한 전투력
            enemy_composition: 적 유닛 구성

        Returns:
            (required_units, unit_tags)
        """
        if not hasattr(self.bot, "units"):
            return {}, []

        # ★ 1. 사용 가능한 방어 유닛 목록 ★
        available_units = self._get_available_defense_units(threat_position)

        # ★ 2. 우선순위 정렬 (거리, 효율성) ★
        sorted_units = self._sort_by_defense_priority(
            available_units,
            threat_position,
            enemy_composition
        )

        # ★ 3. 필요한 만큼만 선택 ★
        selected_units = {}
        selected_tags = []
        current_power = 0

        for unit in sorted_units:
            if current_power >= required_power:
                break

            type_name = getattr(unit.type_id, "name", "").upper()
            combat_value = self.unit_combat_values.get(type_name, 10)

            selected_units[type_name] = selected_units.get(type_name, 0) + 1
            selected_tags.append(unit.tag)
            current_power += combat_value

        return selected_units, selected_tags

    def _get_available_defense_units(self, threat_position: Point2) -> List:
        """
        방어에 사용 가능한 유닛 목록 반환

        Args:
            threat_position: 위협 위치

        Returns:
            사용 가능한 유닛 리스트
        """
        if not hasattr(self.bot, "units"):
            return []

        defense_unit_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.HYDRALISK,
            UnitTypeId.QUEEN,
            UnitTypeId.MUTALISK,
        }

        available = []
        max_distance = 50  # 50 거리 이내 유닛만

        for unit_type in defense_unit_types:
            units = self.bot.units(unit_type)
            for unit in units:
                if unit.is_idle or not unit.is_attacking:
                    distance = unit.position.distance_to(threat_position)
                    if distance <= max_distance:
                        available.append(unit)

        return available

    def _sort_by_defense_priority(
        self,
        units: List,
        threat_position: Point2,
        enemy_composition: Dict
    ) -> List:
        """
        방어 우선순위로 유닛 정렬

        우선순위:
        1. 거리 (가까울수록 우선)
        2. 카운터 효율성 (적 조합에 효과적인 유닛)
        3. 전투력

        Args:
            units: 유닛 리스트
            threat_position: 위협 위치
            enemy_composition: 적 유닛 구성

        Returns:
            정렬된 유닛 리스트
        """
        def priority_score(unit):
            type_name = getattr(unit.type_id, "name", "").upper()
            distance = unit.position.distance_to(threat_position)
            combat_value = self.unit_combat_values.get(type_name, 10)

            # 거리 점수 (가까울수록 높음)
            distance_score = max(0, 50 - distance)

            # 카운터 효율 점수
            counter_score = self._get_counter_score(type_name, enemy_composition)

            # 종합 점수
            total = distance_score * 2 + counter_score + combat_value * 0.5

            return total

        return sorted(units, key=priority_score, reverse=True)

    def _get_counter_score(self, unit_type: str, enemy_composition: Dict) -> float:
        """
        특정 유닛이 적 조합을 카운터하는 효율 점수

        Args:
            unit_type: 아군 유닛 타입
            enemy_composition: 적 유닛 구성

        Returns:
            카운터 효율 점수 (0-100)
        """
        # 간단한 카운터 매트릭스
        counter_matrix = {
            "QUEEN": ["MUTALISK", "PHOENIX", "BANSHEE", "MEDIVAC"],
            "HYDRALISK": ["MUTALISK", "VIKING", "VOIDRAY", "CORRUPTOR", "MARINE"],
            "ROACH": ["ZEALOT", "STALKER", "MARINE", "MARAUDER", "HELLION"],
            "ZERGLING": ["MARINE", "HELLION", "ZEALOT", "PROBE", "SCV", "DRONE"],
            "MUTALISK": ["MARINE", "QUEEN", "PROBE", "SCV", "DRONE"],
        }

        counters = counter_matrix.get(unit_type, [])
        score = 0

        for enemy_type, count in enemy_composition.items():
            if enemy_type in counters:
                score += count * 20

        return min(score, 100)

    async def deploy_defense_force(self, defense_info: Dict, target_position: Point2):
        """
        계산된 방어 병력을 배치

        Args:
            defense_info: calculate_defense_force 결과
            target_position: 방어 목표 위치
        """
        if not defense_info or not defense_info.get("unit_tags"):
            return

        unit_tags = defense_info["unit_tags"]

        for tag in unit_tags:
            unit = self.bot.units.find_by_tag(tag)
            if unit:
                self.bot.do(unit.attack(target_position))

        game_time = getattr(self.bot, "time", 0)
        self.logger.info(
            f"[{int(game_time)}s] ★ DEFENSE DEPLOYED ★\n"
            f"  Units: {len(unit_tags)}\n"
            f"  Target: {target_position}"
        )

    def should_call_full_defense(self, threat_value: int) -> bool:
        """
        전체 방어가 필요한지 판단 (기지 손실 위기)

        Args:
            threat_value: 위협 수준

        Returns:
            True if full defense needed
        """
        # 위협 수준이 300 이상이면 전체 방어
        return threat_value >= 300
