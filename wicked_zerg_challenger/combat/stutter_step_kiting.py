# -*- coding: utf-8 -*-
"""
Stutter-Step Kiting - 진정한 스터터 스텝 구현

공격 -> 후퇴 -> 공격 사이클:
- 무기 준비 완료: 공격
- 무기 쿨다운 중: 후퇴

히드라, 바퀴 등 원거리 유닛에 적용
"""

from typing import Optional, Dict, Set
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2


class StutterStepKiting:
    """
    Stutter-Step 카이팅 시스템

    기능:
    1. 무기 쿨다운 추적
    2. 공격 -> 후퇴 사이클 관리
    3. 최적 카이팅 거리 유지
    4. DPS 극대화
    """

    # 카이팅 가능 유닛 타입
    KITING_UNITS = {
        UnitTypeId.HYDRALISK,   # 히드라 (사거리 6)
        UnitTypeId.ROACH,       # 바퀴 (사거리 4)
        UnitTypeId.QUEEN,       # 여왕 (사거리 8 공중, 7 지상)
        UnitTypeId.RAVAGER,     # 파괴군주 (사거리 9)
    }

    # 유닛별 카이팅 설정
    KITING_CONFIG = {
        UnitTypeId.HYDRALISK: {
            "attack_range": 6.0,
            "kite_distance": 2.0,      # 후퇴 거리
            "optimal_distance": 5.5,   # 최적 교전 거리
            "cooldown_buffer": 0.1,    # 쿨다운 버퍼 (약간 여유)
        },
        UnitTypeId.ROACH: {
            "attack_range": 4.0,
            "kite_distance": 1.5,
            "optimal_distance": 3.5,
            "cooldown_buffer": 0.15,
        },
        UnitTypeId.QUEEN: {
            "attack_range": 7.0,
            "kite_distance": 2.5,
            "optimal_distance": 6.5,
            "cooldown_buffer": 0.1,
        },
        UnitTypeId.RAVAGER: {
            "attack_range": 9.0,
            "kite_distance": 2.0,
            "optimal_distance": 8.5,
            "cooldown_buffer": 0.1,
        },
    }

    def __init__(self, bot):
        self.bot = bot

        # 카이팅 상태 추적
        self.unit_states: Dict[int, str] = {}  # unit_tag -> "attacking" | "retreating"
        self.last_attack_frame: Dict[int, int] = {}  # unit_tag -> frame
        self.retreat_positions: Dict[int, Point2] = {}  # unit_tag -> retreat_position

    def should_kite(self, unit: Unit) -> bool:
        """유닛이 카이팅을 해야 하는지 확인"""
        return unit.type_id in self.KITING_UNITS

    def execute_kiting(
        self,
        unit: Unit,
        target: Optional[Unit],
        enemies: Units
    ) -> bool:
        """
        스터터 스텝 카이팅 실행

        Args:
            unit: 아군 유닛
            target: 공격 타겟 (None이면 자동 선택)
            enemies: 적 유닛들

        Returns:
            True if command issued, False otherwise
        """
        if not self.should_kite(unit):
            return False

        if not enemies:
            return False

        # 카이팅 설정 가져오기
        config = self.KITING_CONFIG.get(unit.type_id)
        if not config:
            return False

        # 타겟 선택 (가장 가까운 적)
        if not target:
            target = enemies.closest_to(unit.position)

        if not target:
            return False

        distance_to_target = unit.position.distance_to(target.position)

        # ★★★ STUTTER-STEP LOGIC ★★★
        # 1. 무기 쿨다운 체크
        weapon_ready = unit.weapon_cooldown <= config["cooldown_buffer"]

        # 2. 사거리 내에 있는지 확인
        in_attack_range = distance_to_target <= config["attack_range"]

        # 3. 상태 결정
        if weapon_ready and in_attack_range:
            # 무기 준비 완료 + 사거리 내 = 공격!
            self._execute_attack(unit, target)
            return True

        elif not weapon_ready:
            # 무기 쿨다운 중 = 후퇴!
            self._execute_retreat(unit, target, config)
            return True

        elif not in_attack_range and distance_to_target > config["optimal_distance"]:
            # 사거리 밖 + 너무 멀리 = 접근
            self._execute_approach(unit, target, config)
            return True

        else:
            # 최적 거리 유지
            self._maintain_optimal_distance(unit, target, config)
            return True

    def _execute_attack(self, unit: Unit, target: Unit) -> None:
        """공격 실행"""
        unit.attack(target)
        self.unit_states[unit.tag] = "attacking"
        self.last_attack_frame[unit.tag] = self.bot.iteration

    def _execute_retreat(self, unit: Unit, target: Unit, config: dict) -> None:
        """후퇴 실행 (쿨다운 중)"""
        # 적 반대 방향으로 후퇴
        retreat_vector = (unit.position - target.position).normalized
        retreat_distance = config["kite_distance"]
        retreat_position = unit.position + retreat_vector * retreat_distance

        # 맵 경계 체크
        retreat_position = self._clamp_to_map(retreat_position)

        unit.move(retreat_position)
        self.unit_states[unit.tag] = "retreating"
        self.retreat_positions[unit.tag] = retreat_position

    def _execute_approach(self, unit: Unit, target: Unit, config: dict) -> None:
        """접근 (사거리 밖일 때)"""
        # 최적 거리까지 접근
        approach_vector = (target.position - unit.position).normalized
        optimal_offset = config["attack_range"] - 0.5  # 약간 여유
        approach_position = unit.position + approach_vector * optimal_offset

        unit.move(approach_position)
        self.unit_states[unit.tag] = "approaching"

    def _maintain_optimal_distance(self, unit: Unit, target: Unit, config: dict) -> None:
        """최적 거리 유지"""
        distance = unit.position.distance_to(target.position)
        optimal = config["optimal_distance"]

        if distance < optimal - 0.5:
            # 너무 가까우면 살짝 후퇴
            retreat_vector = (unit.position - target.position).normalized
            retreat_position = unit.position + retreat_vector * 0.5
            unit.move(retreat_position)
        elif distance > optimal + 0.5:
            # 너무 멀면 살짝 접근
            approach_vector = (target.position - unit.position).normalized
            approach_position = unit.position + approach_vector * 0.5
            unit.move(approach_position)
        else:
            # 최적 거리 - 공격 준비
            if unit.weapon_cooldown <= 0:
                unit.attack(target)

    def _clamp_to_map(self, position: Point2) -> Point2:
        """위치를 맵 경계 내로 제한"""
        map_center = self.bot.game_info.map_center
        playable_area = self.bot.game_info.playable_area

        x = max(playable_area.x, min(position.x, playable_area.x + playable_area.width))
        y = max(playable_area.y, min(position.y, playable_area.y + playable_area.height))

        return Point2((x, y))

    def get_kiting_status(self, unit: Unit) -> Optional[str]:
        """유닛의 카이팅 상태 반환"""
        return self.unit_states.get(unit.tag)

    def cleanup_dead_units(self, alive_tags: Set[int]) -> None:
        """죽은 유닛 정보 정리"""
        # 살아있는 유닛만 남기기
        self.unit_states = {tag: state for tag, state in self.unit_states.items() if tag in alive_tags}
        self.last_attack_frame = {tag: frame for tag, frame in self.last_attack_frame.items() if tag in alive_tags}
        self.retreat_positions = {tag: pos for tag, pos in self.retreat_positions.items() if tag in alive_tags}
