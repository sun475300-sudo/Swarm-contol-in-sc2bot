# -*- coding: utf-8 -*-
"""
Boids Algorithm for Swarm Control.

Implements separation, alignment, and cohesion for clustered micro.
"""

import math
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np

if TYPE_CHECKING:
    try:
        from sc2.position import Point2, Point3  # type: ignore[import-untyped]
        from sc2.unit import Unit  # type: ignore[import-untyped]
        from sc2.units import Units  # type: ignore[import-untyped]
    except ImportError:
        Units = object
        Unit = object
        Point2 = object
        Point3 = object


class BoidsSwarmController:
    """Boids-based swarm controller (separation/alignment/cohesion)."""

    def __init__(
        self,
        separation_weight: float = 1.5,  # 분리 가중치
        alignment_weight: float = 1.0,  # 정렬 가중치
        cohesion_weight: float = 1.0,  # 응집 가중치
        separation_radius: float = 2.0,  # 분리 반경
        neighbor_radius: float = 5.0,  # 이웃 인식 반경
        max_speed: float = 3.0,  # 최대 속도
        max_force: float = 0.5,  # 최대 힘
    ):
        """
        Args:
            separation_weight: Weight for separation force.
            alignment_weight: Weight for alignment force.
            cohesion_weight: Weight for cohesion force.
            separation_radius: Minimum spacing distance.
            neighbor_radius: Neighbor detection radius.
            max_speed: Maximum movement speed.
            max_force: Maximum force applied per step.
        """
        self.separation_weight = separation_weight
        self.alignment_weight = alignment_weight
        self.cohesion_weight = cohesion_weight
        self.separation_radius = separation_radius
        self.neighbor_radius = neighbor_radius
        self.max_speed = max_speed
        self.max_force = max_force

    def calculate_swarm_velocity(
        self,
        unit: "Unit",
        neighbors: "Units",
        target: Optional["Point2"] = None,
        enemy_units: Optional["Units"] = None,
        separation_multiplier: float = 1.0,
        cohesion_multiplier: float = 1.0,
    ) -> Tuple[float, float]:
        """
        Calculate movement velocity using boids forces.

        Args:
            unit: The unit to calculate velocity for
            neighbors: Nearby friendly units
            target: Target position to move towards
            enemy_units: Enemy units to avoid
            separation_multiplier: Multiplier for separation force (increased near splash threats)
            cohesion_multiplier: Multiplier for cohesion force (decreased in chokepoints to prevent congestion)

        Returns:
            (velocity_x, velocity_y) tuple
        """
        # 초기 속도 벡터
        velocity = np.array([0.0, 0.0])

        # 1. Separation (분리): 너무 가까운 이웃으로부터 멀어지기
        separation_force = self._calculate_separation(unit, neighbors)
        velocity += separation_force * self.separation_weight * separation_multiplier

        # 2. Alignment (정렬): 이웃과 같은 방향으로 이동
        alignment_force = self._calculate_alignment(unit, neighbors)
        velocity += alignment_force * self.alignment_weight

        # 3. Cohesion (응집): 이웃들의 중심으로 이동
        # Chokepoint에서는 cohesion을 줄여서 길게 늘어서도록 함
        cohesion_force = self._calculate_cohesion(unit, neighbors)
        velocity += cohesion_force * self.cohesion_weight * cohesion_multiplier

        # 4. Target Seeking (목표 추구): 목표 지점으로 이동
        if target:
            target_force = self._calculate_target_seeking(unit, target)
            velocity += target_force * 2.0  # 목표 추구는 높은 가중치

        # 5. Enemy Avoidance (적 회피): 적 유닛으로부터 멀어지기
        if enemy_units:
            avoidance_force = self._calculate_enemy_avoidance(unit, enemy_units)
            velocity += avoidance_force * 1.5  # 적 회피는 높은 가중치

        # 6. Enemy Surrounding (적 포위): 적을 부채꼴 모양으로 이동
        if enemy_units and target:
            surrounding_force = self._calculate_enemy_surrounding(
                unit, enemy_units, target
            )
            velocity += surrounding_force * 1.0

        # 힘 제한 (max_force)
        force_magnitude = np.linalg.norm(velocity)
        if force_magnitude > self.max_force:
            velocity = velocity / force_magnitude * self.max_force

        return float(velocity[0]), float(velocity[1])

    def _calculate_separation(self, unit: "Unit", neighbors: "Units") -> np.ndarray:
        """분리 힘 계산: 너무 가까운 이웃으로부터 멀어지기"""
        separation = np.array([0.0, 0.0])
        count = 0

        unit_pos = np.array([unit.position.x, unit.position.y])

        for neighbor in neighbors:
            if neighbor.tag == unit.tag:
                continue

            neighbor_pos = np.array([neighbor.position.x, neighbor.position.y])
            distance = np.linalg.norm(neighbor_pos - unit_pos)

            if 0 < distance < self.separation_radius:
                # 거리가 가까울수록 더 강한 분리 힘
                diff = unit_pos - neighbor_pos
                diff = diff / (distance**2)  # 거리의 제곱에 반비례
                separation += diff
                count += 1

        if count > 0:
            separation = separation / count
            # 정규화
            magnitude = np.linalg.norm(separation)
            if magnitude > 0:
                separation = separation / magnitude * self.max_force

        return separation

    def _calculate_alignment(self, unit: "Unit", neighbors: "Units") -> np.ndarray:
        """정렬 힘 계산: 이웃과 같은 방향으로 이동"""
        alignment = np.array([0.0, 0.0])
        count = 0

        unit_pos = np.array([unit.position.x, unit.position.y])

        for neighbor in neighbors:
            if neighbor.tag == unit.tag:
                continue

            neighbor_pos = np.array([neighbor.position.x, neighbor.position.y])
            distance = np.linalg.norm(neighbor_pos - unit_pos)

            if 0 < distance < self.neighbor_radius:
                # 이웃의 속도 벡터 (현재는 위치 기반으로 단순화)
                # 실제로는 유닛 방향을 고려해야 하지만, 여기서는 단순화
                alignment += np.array([neighbor.position.x, neighbor.position.y])
                count += 1

        if count > 0:
            alignment = alignment / count
            # 현재 위치와 이웃들의 평균 위치의 차이
            unit_pos = np.array([unit.position.x, unit.position.y])
            alignment = alignment - unit_pos
            # 정규화
            magnitude = np.linalg.norm(alignment)
            if magnitude > 0:
                alignment = alignment / magnitude * self.max_force

        return alignment

    def _calculate_cohesion(self, unit: "Unit", neighbors: "Units") -> np.ndarray:
        """응집 힘 계산: 이웃들의 중심으로 이동"""
        cohesion = np.array([0.0, 0.0])
        count = 0

        unit_pos = np.array([unit.position.x, unit.position.y])

        for neighbor in neighbors:
            if neighbor.tag == unit.tag:
                continue

            neighbor_pos = np.array([neighbor.position.x, neighbor.position.y])
            distance = np.linalg.norm(neighbor_pos - unit_pos)

            if 0 < distance < self.neighbor_radius:
                cohesion += neighbor_pos
                count += 1

        if count > 0:
            # 이웃들의 중심
            cohesion = cohesion / count
            # 중심으로의 벡터
            cohesion = cohesion - unit_pos
            # 정규화
            magnitude = np.linalg.norm(cohesion)
            if magnitude > 0:
                cohesion = cohesion / magnitude * self.max_force

        return cohesion

    def _calculate_target_seeking(self, unit: "Unit", target: "Point2") -> np.ndarray:
        """목표 추구 힘 계산: 목표 지점으로 이동"""
        unit_pos = np.array([unit.position.x, unit.position.y])
        target_pos = np.array([target.x, target.y])

        direction = target_pos - unit_pos
        distance = np.linalg.norm(direction)

        if distance > 0:
            direction = direction / distance
            # 거리에 비례한 힘 적용 (가까워질수록 약해짐)
            force = min(distance / 10.0, 1.0) * self.max_force
            return direction * force

        return np.array([0.0, 0.0])

    def _calculate_enemy_avoidance(
        self, unit: "Unit", enemy_units: "Units"
    ) -> np.ndarray:
        """적 회피 힘 계산: 적 유닛으로부터 멀어지기"""
        avoidance = np.array([0.0, 0.0])
        count = 0

        unit_pos = np.array([unit.position.x, unit.position.y])

        for enemy in enemy_units:
            enemy_pos = np.array([enemy.position.x, enemy.position.y])
            distance = np.linalg.norm(enemy_pos - unit_pos)

            # 위험 반경 (유닛 공격 사거리 + 여유)
            danger_radius = 8.0

            if distance < danger_radius:
                # 적으로부터 멀어지는 벡터
                diff = unit_pos - enemy_pos
                # 거리가 가까울수록 더 강한 회피 힘
                strength = (danger_radius - distance) / danger_radius
                diff = diff / (distance + 0.1)  # 0으로 나누기 방지
                avoidance += diff * strength
                count += 1

        if count > 0:
            avoidance = avoidance / count
            # 정규화
            magnitude = np.linalg.norm(avoidance)
            if magnitude > 0:
                avoidance = avoidance / magnitude * self.max_force

        return avoidance

    def _calculate_enemy_surrounding(
        self, unit: "Unit", enemy_units: "Units", target: "Point2"
    ) -> np.ndarray:
        """적 포위 힘 계산: 적을 부채꼴 모양으로 이동"""
        if len(enemy_units) == 0:
            return np.array([0.0, 0.0])

        # 적군의 중심 계산
        enemy_center = np.array([0.0, 0.0])
        for enemy in enemy_units:
            enemy_center += np.array([enemy.position.x, enemy.position.y])
        enemy_center = enemy_center / len(enemy_units)

        # 유닛의 현재 위치
        unit_pos = np.array([unit.position.x, unit.position.y])

        # 적 중심을 기준으로 한 각도 계산
        to_enemy = enemy_center - unit_pos
        angle = math.atan2(to_enemy[1], to_enemy[0])

        # 포위 각도 (적 주변을 부채꼴 배치)
        # 유닛 태그를 이용한 분산 배치 (단순화)
        surrounding_angle = angle + math.pi / 2  # 90도 회전

        # 포위 위치 계산
        surrounding_distance = 5.0  # 적으로부터의 거리
        surrounding_pos = enemy_center + np.array(
            [
                math.cos(surrounding_angle) * surrounding_distance,
                math.sin(surrounding_angle) * surrounding_distance,
            ]
        )

        # 포위 위치로의 벡터
        direction = surrounding_pos - unit_pos
        magnitude = np.linalg.norm(direction)

        if magnitude > 0:
            direction = direction / magnitude
            return direction * self.max_force * 0.5  # 포위는 약한 힘

        return np.array([0.0, 0.0])

    def apply_boids_to_units(
        self,
        units: "Units",
        target: Optional["Point2"] = None,
        enemy_units: Optional["Units"] = None,
    ) -> List[Tuple["Unit", "Point2"]]:
        """
        모든 유닛에 Boids 알고리즘을 적용

        Args:
            units: 제어할 유닛들
            target: 목표 위치 (선택사항)
            enemy_units: 적 유닛들 (선택사항)

        Returns:
            [(unit, target_position), ...] 리스트
        """
        results = []

        for unit in units:
            # 이웃 유닛들 찾기 (일정 범위)
            neighbors = units.closer_than(self.neighbor_radius, unit.position)

            # Boids 알고리즘으로 속도 벡터 계산
            velocity_x, velocity_y = self.calculate_swarm_velocity(
                unit=unit, neighbors=neighbors, target=target, enemy_units=enemy_units
            )

            # 현재 위치에서 속도 벡터를 더해 목표 위치 계산
            current_pos = unit.position
            target_pos = Point2(
                (current_pos.x + velocity_x, current_pos.y + velocity_y)
            )

            results.append((unit, target_pos))

        return results
