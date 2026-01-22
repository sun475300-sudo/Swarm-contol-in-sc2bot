# -*- coding: utf-8 -*-
"""
Formation Manager - 지형 활용 및 대형 제어

주요 기능:
1. 오목한 대형(Concave): 원거리 유닛을 부채꼴 모양으로 배치하여 화력 극대화
2. 길목 제어(Choke Point): 좁은 입구에서의 방어적 위치 선택
3. 고저차 활용: 언덕, 경사로 등을 활용한 전술
"""

from typing import Dict, List, Optional, Set, Tuple

from sc2.game_info import GameInfo
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class FormationManager:
    """대형 관리자 - 지형 활용, 길목 제어, 고저 활용"""

    def __init__(self, bot):
        self.bot = bot

        # 원거리 유닛 타입
        self.ranged_units = {
            UnitTypeId.HYDRALISK,
            UnitTypeId.ROACH,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.MUTALISK,
        }

        # 근접 유닛 타입
        self.melee_units = {
            UnitTypeId.ZERGLING,
            UnitTypeId.ULTRALISK,
            UnitTypeId.BANELING,
        }

    def form_concave(
        self, units: Units, enemy_center: Point2
    ) -> List[Tuple[Unit, Point2]]:
        """
        오목한 대형(Concave) 형성

        원거리 유닛을 부채꼴 모양으로 배치하여 화력을 극대화함

        Args:
            units: 아군 유닛 집합
            enemy_center: 적군 중심 위치

        Returns:
            (유닛, 목표 위치) 튜플 리스트
        """
        if not units.exists:
            return []

        # 원거리 유닛과 근접 유닛 분리
        ranged = [u for u in units if u.type_id in self.ranged_units]
        melee = [u for u in units if u.type_id in self.melee_units]

        assignments = []

        # 원거리 유닛: 부채꼴 모양으로 배치
        if ranged and enemy_center:
            # 부채꼴의 반지름 (유닛의 사거리)
            radius = 8.0  # 원거리 유닛의 평균 사거리

            # 부채꼴의 중심점 (우리 본진)
            if self.bot.townhalls.exists:
                our_base = self.bot.townhalls.first
                direction = (enemy_center - our_base.position).normalized()
            else:
                direction = Point2((1, 0))  # 기본 방향

            # 부채꼴 모양으로 배치
            angle_step = 180.0 / max(len(ranged), 1)  # 180도 부채꼴

            for i, unit in enumerate(ranged):
                angle = (i * angle_step - 90.0) * 3.14159 / 180.0  # 라디안 변환

                # 부채꼴 위치 계산
                offset_x = radius * direction.x * abs(angle) / 1.57
                offset_y = radius * direction.y * abs(angle) / 1.57

                target_pos = enemy_center + Point2((offset_x, offset_y))
                assignments.append((unit, target_pos))

        # 근접 유닛: 전면 전방에 배치
        if melee and enemy_center:
            for i, unit in enumerate(melee):
                # 전면 전방에 배치
                if self.bot.townhalls.exists:
                    our_base = self.bot.townhalls.first
                    direction = (enemy_center - our_base.position).normalized()
                else:
                    direction = Point2((1, 0))

                target_pos = enemy_center - direction * 3.0  # 적 앞 3 거리
                assignments.append((unit, target_pos))

        return assignments

    def find_choke_points(self, map_info: GameInfo) -> List[Point2]:
        """
        길목(Choke Point) 찾기

        맵의 경사로 및 입구를 찾아 방어적 위치를 활용

        Args:
            map_info: 게임 맵 정보

        Returns:
            길목 위치 리스트
        """
        choke_points = []

        # 간단한 구현: 우리 본진과 적 본진 사이의 중요 길목
        if self.bot.townhalls.exists and self.bot.enemy_start_locations:
            our_base = self.bot.townhalls.first
            enemy_start = self.bot.enemy_start_locations[0]

            # 중간 지점에서 길목 후보지 생성
            mid_point = our_base.position.towards(enemy_start, 20.0)
            choke_points.append(mid_point)

        return choke_points

    def should_avoid_choke(self, units: Units, enemy_units: Units) -> bool:
        """
        길목에서 피해야 하는지 판단

        적이 길목에서 우세할 경우 피하는 것이 유리하므로 회피 결정

        Args:
            units: 아군 유닛
            enemy_units: 적 유닛

        Returns:
            회피가 필요하면 True
        """
        if not units.exists or not enemy_units.exists:
            return False

        # 아군과 적군의 병력 확인
        our_count = len(units)
        enemy_count = len(enemy_units)

        # 적이 병력 우위 상황이면 회피해야 함
        if enemy_count > our_count * 1.5:
            # 적군이 모여있는지 확인
            if enemy_units.exists:
                enemy_positions = [e.position for e in enemy_units]
                avg_enemy_pos = Point2(
                    (
                        sum(p.x for p in enemy_positions) / len(enemy_positions),
                        sum(p.y for p in enemy_positions) / len(enemy_positions),
                    )
                )

                # 적군이 모여있는 정도 (표준편차)
                distances = [p.distance_to(avg_enemy_pos) for p in enemy_positions]
                avg_distance = sum(distances) / len(distances) if distances else 0

                # 적군이 매우 밀집했으면 (길목 방어) 피해야 함
                if avg_distance < 5.0:
                    return True

        return False

    def get_optimal_position(
        self, unit: Unit, enemy_center: Point2, formation_type: str = "concave"
    ) -> Point2:
        """
        최적 위치 계산

        Args:
            unit: 유닛
            enemy_center: 적군 중심 위치
            formation_type: 대형 타입 ("concave", "line", "surround")

        Returns:
            최적 위치
        """
        if formation_type == "concave":
            # 오목한 대형
            if unit.type_id in self.ranged_units:
                # 원거리 유닛: 부채꼴 모양으로 배치
                if self.bot.townhalls.exists:
                    our_base = self.bot.townhalls.first
                    direction = (enemy_center - our_base.position).normalized()
                else:
                    direction = Point2((1, 0))

                # 좌우 방향/후방 위치
                radius = 8.0
                perpendicular = Point2((-direction.y, direction.x))  # 수직 벡터
                target_pos = enemy_center + perpendicular * radius
                return target_pos
            else:
                # 근접 유닛: 전면 돌격
                if self.bot.townhalls.exists:
                    our_base = self.bot.townhalls.first
                    direction = (enemy_center - our_base.position).normalized()
                else:
                    direction = Point2((1, 0))

                return enemy_center - direction * 3.0

        # 기본: 적군을 향하는 위치
        return enemy_center
