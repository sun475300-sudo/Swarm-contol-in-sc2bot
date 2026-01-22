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
        separation_weight: float = 1.5,  # �и� ����ġ
        alignment_weight: float = 1.0,  # ���� ����ġ
        cohesion_weight: float = 1.0,  # ���� ����ġ
        separation_radius: float = 2.0,  # �и� �ݰ�
        neighbor_radius: float = 5.0,  # �̿� �ν� �ݰ�
        max_speed: float = 3.0,  # �ִ� �ӵ�
        max_force: float = 0.5,  # �ִ� ��
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
    ) -> Tuple[float, float]:
        """Calculate movement velocity using boids forces."""
        # �ʱ� �ӵ� ����
        velocity = np.array([0.0, 0.0])

        # 1. Separation (�и�): �ʹ� ����� �̿����κ��� �־�����
        separation_force = self._calculate_separation(unit, neighbors)
        velocity += separation_force * self.separation_weight * separation_multiplier

        # 2. Alignment (����): �̿��� ���� �������� �̵�
        alignment_force = self._calculate_alignment(unit, neighbors)
        velocity += alignment_force * self.alignment_weight

        # 3. Cohesion (����): �̿����� �߽����� �̵�
        cohesion_force = self._calculate_cohesion(unit, neighbors)
        velocity += cohesion_force * self.cohesion_weight

        # 4. Target Seeking (��ǥ ����): ��ǥ �������� �̵�
        if target:
            target_force = self._calculate_target_seeking(unit, target)
            velocity += target_force * 2.0  # ��ǥ ������ ���� ����ġ

        # 5. Enemy Avoidance (�� ȸ��): �� �������κ��� �־�����
        if enemy_units:
            avoidance_force = self._calculate_enemy_avoidance(unit, enemy_units)
            velocity += avoidance_force * 1.5  # �� ȸ�Ǵ� ���� ����ġ

        # 6. Enemy Surrounding (�� ����): ���� ���δ� ���·� �̵�
        if enemy_units and target:
            surrounding_force = self._calculate_enemy_surrounding(
                unit, enemy_units, target
            )
            velocity += surrounding_force * 1.0

        # �� ���� (max_force)
        force_magnitude = np.linalg.norm(velocity)
        if force_magnitude > self.max_force:
            velocity = velocity / force_magnitude * self.max_force

        return float(velocity[0]), float(velocity[1])

    def _calculate_separation(self, unit: "Unit", neighbors: "Units") -> np.ndarray:
        """�и� �� ���: �ʹ� ����� �̿����κ��� �־�����"""
        separation = np.array([0.0, 0.0])
        count = 0

        unit_pos = np.array([unit.position.x, unit.position.y])

        for neighbor in neighbors:
            if neighbor.tag == unit.tag:
                continue

            neighbor_pos = np.array([neighbor.position.x, neighbor.position.y])
            distance = np.linalg.norm(neighbor_pos - unit_pos)

            if 0 < distance < self.separation_radius:
                # �Ÿ��� �������� �� ���� �и� ��
                diff = unit_pos - neighbor_pos
                diff = diff / (distance**2)  # �Ÿ��� ������ �ݺ��
                separation += diff
                count += 1

        if count > 0:
            separation = separation / count
            # ����ȭ
            magnitude = np.linalg.norm(separation)
            if magnitude > 0:
                separation = separation / magnitude * self.max_force

        return separation

    def _calculate_alignment(self, unit: "Unit", neighbors: "Units") -> np.ndarray:
        """���� �� ���: �̿��� ���� �������� �̵�"""
        alignment = np.array([0.0, 0.0])
        count = 0

        unit_pos = np.array([unit.position.x, unit.position.y])

        for neighbor in neighbors:
            if neighbor.tag == unit.tag:
                continue

            neighbor_pos = np.array([neighbor.position.x, neighbor.position.y])
            distance = np.linalg.norm(neighbor_pos - unit_pos)

            if 0 < distance < self.neighbor_radius:
                # �̿��� �ӵ� ���� (����� ��ġ ������� �ٻ�)
                # �����δ� ���� �������� ��ġ�� �����ؾ� ������, ���⼭�� �ܼ�ȭ
                alignment += np.array([neighbor.position.x, neighbor.position.y])
                count += 1

        if count > 0:
            alignment = alignment / count
            # ���� ��ġ���� �̿����� ��� ��ġ���� ����
            unit_pos = np.array([unit.position.x, unit.position.y])
            alignment = alignment - unit_pos
            # ����ȭ
            magnitude = np.linalg.norm(alignment)
            if magnitude > 0:
                alignment = alignment / magnitude * self.max_force

        return alignment

    def _calculate_cohesion(self, unit: "Unit", neighbors: "Units") -> np.ndarray:
        """���� �� ���: �̿����� �߽����� �̵�"""
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
            # �̿����� �߽�
            cohesion = cohesion / count
            # �߽������� ����
            cohesion = cohesion - unit_pos
            # ����ȭ
            magnitude = np.linalg.norm(cohesion)
            if magnitude > 0:
                cohesion = cohesion / magnitude * self.max_force

        return cohesion

    def _calculate_target_seeking(self, unit: "Unit", target: "Point2") -> np.ndarray:
        """��ǥ ���� �� ���: ��ǥ �������� �̵�"""
        unit_pos = np.array([unit.position.x, unit.position.y])
        target_pos = np.array([target.x, target.y])

        direction = target_pos - unit_pos
        distance = np.linalg.norm(direction)

        if distance > 0:
            direction = direction / distance
            # �Ÿ��� ���� �� ���� (�������� ������)
            force = min(distance / 10.0, 1.0) * self.max_force
            return direction * force

        return np.array([0.0, 0.0])

    def _calculate_enemy_avoidance(
        self, unit: "Unit", enemy_units: "Units"
    ) -> np.ndarray:
        """�� ȸ�� �� ���: �� �������κ��� �־�����"""
        avoidance = np.array([0.0, 0.0])
        count = 0

        unit_pos = np.array([unit.position.x, unit.position.y])

        for enemy in enemy_units:
            enemy_pos = np.array([enemy.position.x, enemy.position.y])
            distance = np.linalg.norm(enemy_pos - unit_pos)

            # ���� �ݰ� (���� ���� ��Ÿ� + ����)
            danger_radius = 8.0

            if distance < danger_radius:
                # �����κ��� �־����� ����
                diff = unit_pos - enemy_pos
                # �Ÿ��� �������� �� ���� ȸ�� ��
                strength = (danger_radius - distance) / danger_radius
                diff = diff / (distance + 0.1)  # 0���� ������ ����
                avoidance += diff * strength
                count += 1

        if count > 0:
            avoidance = avoidance / count
            # ����ȭ
            magnitude = np.linalg.norm(avoidance)
            if magnitude > 0:
                avoidance = avoidance / magnitude * self.max_force

        return avoidance

    def _calculate_enemy_surrounding(
        self, unit: "Unit", enemy_units: "Units", target: "Point2"
    ) -> np.ndarray:
        """�� ���� �� ���: ���� ���δ� ���·� �̵�"""
        if len(enemy_units) == 0:
            return np.array([0.0, 0.0])

        # ������ �߽� ���
        enemy_center = np.array([0.0, 0.0])
        for enemy in enemy_units:
            enemy_center += np.array([enemy.position.x, enemy.position.y])
        enemy_center = enemy_center / len(enemy_units)

        # ���� ���� ��ġ
        unit_pos = np.array([unit.position.x, unit.position.y])

        # �� �߽��� �������� �� ���� ���
        to_enemy = enemy_center - unit_pos
        angle = math.atan2(to_enemy[1], to_enemy[0])

        # ���� ���� (�� �ֺ��� ���δ� ��ġ)
        # ���� ������ �ε����� ���� ���� ���� (�ܼ�ȭ)
        surrounding_angle = angle + math.pi / 2  # 90�� ȸ��

        # ���� ��ġ ���
        surrounding_distance = 5.0  # �����κ����� �Ÿ�
        surrounding_pos = enemy_center + np.array(
            [
                math.cos(surrounding_angle) * surrounding_distance,
                math.sin(surrounding_angle) * surrounding_distance,
            ]
        )

        # ���� ��ġ���� ����
        direction = surrounding_pos - unit_pos
        magnitude = np.linalg.norm(direction)

        if magnitude > 0:
            direction = direction / magnitude
            return direction * self.max_force * 0.5  # ������ ���� ��

        return np.array([0.0, 0.0])

    def apply_boids_to_units(
        self,
        units: "Units",
        target: Optional["Point2"] = None,
        enemy_units: Optional["Units"] = None,
    ) -> List[Tuple["Unit", "Point2"]]:
        """
        ���� ���ֿ� Boids �˰����� ����

        Args:
            units: ������ ���ֵ�
            target: ��ǥ ���� (������)
            enemy_units: �� ���ֵ� (������)

        Returns:
            [(unit, target_position), ...] ����Ʈ
        """
        results = []

        for unit in units:
            # �̿� ���ֵ� ã�� (���� ��)
            neighbors = units.closer_than(self.neighbor_radius, unit.position)

            # Boids �˰��������� �ӵ� ���� ���
            velocity_x, velocity_y = self.calculate_swarm_velocity(
                unit=unit, neighbors=neighbors, target=target, enemy_units=enemy_units
            )

            # ���� ��ġ���� �ӵ� ���͸� ���� ��ǥ ��ġ ���
            current_pos = unit.position
            target_pos = Point2(
                (current_pos.x + velocity_x, current_pos.y + velocity_y)
            )

            results.append((unit, target_pos))

        return results
