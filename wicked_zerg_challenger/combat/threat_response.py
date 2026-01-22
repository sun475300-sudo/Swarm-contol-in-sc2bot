# -*- coding: utf-8 -*-
"""
Threat Response - Splash damage avoidance and threat detection.

This module handles detection and response to area-of-effect threats,
calculating appropriate separation and repulsion for unit survival.
"""

import math
from typing import List, Set, Tuple

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    UnitTypeId = None


class SplashThreatHandler:
    """
    Handles detection and avoidance of splash/AoE damage threats.

    Calculates separation multipliers and repulsion vectors
    to help units avoid taking splash damage.
    """

    def __init__(
        self,
        splash_avoid_radius: float = 10.0,
        repulsion_ground: float = 3.5,
        repulsion_air: float = 10.0,
        separation_min: float = 5.0,
        separation_max: float = 10.0,
    ):
        """
        Initialize splash threat handler.

        Args:
            splash_avoid_radius: Maximum distance to consider splash threats
            repulsion_ground: Repulsion weight for ground units
            repulsion_air: Repulsion weight for air units
            separation_min: Minimum separation multiplier
            separation_max: Maximum separation multiplier
        """
        self.splash_avoid_radius = splash_avoid_radius
        self.repulsion_ground = repulsion_ground
        self.repulsion_air = repulsion_air
        self.separation_min = separation_min
        self.separation_max = separation_max

        # Define splash threat unit types
        self.splash_threat_types: Set = set()
        if UnitTypeId:
            self.splash_threat_types = {
                UnitTypeId.SIEGETANK,
                UnitTypeId.SIEGETANKSIEGED,
                UnitTypeId.HIGHTEMPLAR,
                UnitTypeId.BANELING,
                UnitTypeId.BANELINGBURROWED,
                UnitTypeId.DISRUPTOR,
                UnitTypeId.COLOSSUS,
                UnitTypeId.RAVAGER,  # Corrosive bile
                UnitTypeId.WIDOWMINE,
                UnitTypeId.WIDOWMINEBURROWED,
                UnitTypeId.LIBERATOR,
                UnitTypeId.LIBERATORAG,
            }

    def get_splash_threats(self, enemy_units) -> List:
        """
        Filter enemy units to get only splash damage threats.

        Args:
            enemy_units: Iterable of enemy units

        Returns:
            List of units that deal splash damage
        """
        if not UnitTypeId or not enemy_units:
            return []
        return [
            enemy
            for enemy in enemy_units
            if enemy.type_id in self.splash_threat_types
        ]

    def get_separation_multiplier(self, unit, splash_threats) -> float:
        """
        Calculate separation multiplier based on splash threat proximity.

        Higher multiplier = more separation between friendly units.

        Args:
            unit: The unit to calculate multiplier for
            splash_threats: List of nearby splash threat units

        Returns:
            Separation multiplier (1.0 to separation_max)
        """
        if not splash_threats:
            return 1.0

        nearest_dist = None
        for threat in splash_threats:
            try:
                dist = unit.distance_to(threat)
            except Exception:
                continue
            if nearest_dist is None or dist < nearest_dist:
                nearest_dist = dist

        if nearest_dist is None or nearest_dist > self.splash_avoid_radius:
            return 1.0

        # Linear interpolation based on distance
        ratio = max(0.0, 1.0 - (nearest_dist / self.splash_avoid_radius))
        return min(
            self.separation_max,
            self.separation_min
            + ratio * (self.separation_max - self.separation_min),
        )

    def calculate_repulsion(self, unit, splash_threats) -> Tuple[float, float]:
        """
        Calculate repulsion vector from splash damage threats.

        Args:
            unit: The unit to calculate repulsion for
            splash_threats: List of splash threat units

        Returns:
            Tuple of (x, y) repulsion vector components
        """
        if not splash_threats:
            return 0.0, 0.0

        repulsion_x = 0.0
        repulsion_y = 0.0
        weight = (
            self.repulsion_air
            if getattr(unit, "is_flying", False)
            else self.repulsion_ground
        )

        for threat in splash_threats:
            try:
                dist = unit.distance_to(threat)
            except Exception:
                continue
            if dist <= 0 or dist > self.splash_avoid_radius:
                continue

            strength = (self.splash_avoid_radius - dist) / self.splash_avoid_radius
            dx = unit.position.x - threat.position.x
            dy = unit.position.y - threat.position.y
            repulsion_x += (dx / (dist + 0.1)) * strength * weight
            repulsion_y += (dy / (dist + 0.1)) * strength * weight

        return repulsion_x, repulsion_y

    def calculate_neighbor_separation(
        self, unit, neighbors, radius: float = 10.0
    ) -> Tuple[float, float]:
        """
        Calculate separation force from neighboring friendly units.

        Used for spreading units apart to reduce splash damage impact.

        Args:
            unit: The unit to calculate separation for
            neighbors: List of neighboring friendly units
            radius: Maximum radius to consider neighbors

        Returns:
            Normalized tuple of (x, y) separation vector
        """
        sep_x = 0.0
        sep_y = 0.0
        count = 0

        for neighbor in neighbors:
            if neighbor.tag == unit.tag:
                continue
            try:
                dist = unit.distance_to(neighbor)
            except Exception:
                continue
            if dist <= 0 or dist > radius:
                continue

            dx = unit.position.x - neighbor.position.x
            dy = unit.position.y - neighbor.position.y
            # Inverse square weighting - closer units have stronger effect
            sep_x += dx / (dist * dist + 0.1)
            sep_y += dy / (dist * dist + 0.1)
            count += 1

        if count == 0:
            return 0.0, 0.0

        sep_x /= count
        sep_y /= count

        # Normalize the vector
        length = math.hypot(sep_x, sep_y)
        if length == 0:
            return 0.0, 0.0

        return sep_x / length, sep_y / length

    def is_under_splash_threat(self, unit, splash_threats) -> bool:
        """
        Check if unit is currently under splash damage threat.

        Args:
            unit: Unit to check
            splash_threats: List of splash threat units

        Returns:
            True if unit is within splash_avoid_radius of any threat
        """
        if not splash_threats:
            return False

        for threat in splash_threats:
            try:
                if unit.distance_to(threat) <= self.splash_avoid_radius:
                    return True
            except Exception:
                continue

        return False

    def get_panic_split_direction(self, unit, splash_threats) -> Tuple[float, float]:
        """
        Calculate emergency split direction when under heavy threat.

        Returns a normalized vector pointing away from the nearest threat.

        Args:
            unit: Unit that needs to split
            splash_threats: List of splash threat units

        Returns:
            Normalized tuple of (x, y) escape direction
        """
        if not splash_threats:
            return 0.0, 0.0

        nearest_threat = None
        nearest_dist = float("inf")

        for threat in splash_threats:
            try:
                dist = unit.distance_to(threat)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_threat = threat
            except Exception:
                continue

        if nearest_threat is None:
            return 0.0, 0.0

        dx = unit.position.x - nearest_threat.position.x
        dy = unit.position.y - nearest_threat.position.y
        length = math.hypot(dx, dy)

        if length == 0:
            return 1.0, 0.0  # Default direction

        return dx / length, dy / length
