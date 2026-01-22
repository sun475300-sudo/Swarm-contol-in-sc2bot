# -*- coding: utf-8 -*-
"""
Potential Field Controller - Force-based repulsion model for unit avoidance.

This module implements potential field theory for collision avoidance,
calculating repulsion vectors from enemies, structures, and terrain.
"""

from typing import Iterable, List, Optional, Tuple

try:
    from sc2.position import Point2
except ImportError:
    Point2 = None


class PotentialFieldController:
    """
    Simple repulsion model with air/ground weighting.

    Uses inverse distance weighting to calculate repulsion forces
    from various obstacles (enemies, structures, terrain).
    """

    def __init__(
        self,
        enemy_weight: float = 1.0,
        terrain_weight: float = 1.0,
        structure_weight: float = 1.4,
        enemy_radius: float = 6.0,
        structure_radius: float = 8.0,
        terrain_radius: float = 3.0,
    ):
        """
        Initialize potential field controller.

        Args:
            enemy_weight: Weight multiplier for enemy repulsion
            terrain_weight: Weight multiplier for terrain repulsion
            structure_weight: Weight multiplier for structure repulsion
            enemy_radius: Maximum distance for enemy repulsion effect
            structure_radius: Maximum distance for structure repulsion effect
            terrain_radius: Maximum distance for terrain repulsion effect
        """
        self.enemy_weight = enemy_weight
        self.terrain_weight = terrain_weight
        self.structure_weight = structure_weight
        self.enemy_radius = enemy_radius
        self.structure_radius = structure_radius
        self.terrain_radius = terrain_radius

    def get_repulsion_vector(
        self,
        unit,
        enemy_units: Iterable,
        terrain_points: Optional[List] = None,
        structure_units: Optional[List] = None,
    ) -> Tuple[float, float]:
        """
        Calculate combined repulsion vector from all obstacles.

        Args:
            unit: The unit to calculate repulsion for
            enemy_units: Iterable of enemy units
            terrain_points: Optional list of terrain obstacle points
            structure_units: Optional list of structure units

        Returns:
            Tuple of (x, y) repulsion vector components
        """
        if not Point2:
            return 0.0, 0.0

        terrain_points = terrain_points or []
        is_flying = getattr(unit, "is_flying", False)
        terrain_weight = 0.0 if is_flying else self.terrain_weight

        repulsion_x = 0.0
        repulsion_y = 0.0

        # Calculate enemy repulsion
        repulsion_x, repulsion_y = self._calculate_enemy_repulsion(
            unit, enemy_units, repulsion_x, repulsion_y
        )

        # Calculate structure repulsion
        repulsion_x, repulsion_y = self._calculate_structure_repulsion(
            unit, structure_units, repulsion_x, repulsion_y
        )

        # Calculate terrain repulsion (ground units only)
        if terrain_weight > 0.0:
            repulsion_x, repulsion_y = self._calculate_terrain_repulsion(
                unit, terrain_points, terrain_weight, repulsion_x, repulsion_y
            )

        return repulsion_x, repulsion_y

    def _calculate_enemy_repulsion(
        self, unit, enemy_units, repulsion_x: float, repulsion_y: float
    ) -> Tuple[float, float]:
        """Calculate repulsion from enemy units."""
        for enemy in enemy_units or []:
            try:
                dist = unit.distance_to(enemy)
            except Exception:
                continue
            if dist <= 0 or dist > self.enemy_radius:
                continue
            strength = (self.enemy_radius - dist) / self.enemy_radius
            dx = unit.position.x - enemy.position.x
            dy = unit.position.y - enemy.position.y
            repulsion_x += (dx / (dist + 0.1)) * strength * self.enemy_weight
            repulsion_y += (dy / (dist + 0.1)) * strength * self.enemy_weight
        return repulsion_x, repulsion_y

    def _calculate_structure_repulsion(
        self, unit, structure_units, repulsion_x: float, repulsion_y: float
    ) -> Tuple[float, float]:
        """Calculate repulsion from structures."""
        for structure in structure_units or []:
            try:
                dist = unit.distance_to(structure)
            except Exception:
                continue
            if dist <= 0 or dist > self.structure_radius:
                continue
            strength = (self.structure_radius - dist) / self.structure_radius
            dx = unit.position.x - structure.position.x
            dy = unit.position.y - structure.position.y
            repulsion_x += (dx / (dist + 0.1)) * strength * self.structure_weight
            repulsion_y += (dy / (dist + 0.1)) * strength * self.structure_weight
        return repulsion_x, repulsion_y

    def _calculate_terrain_repulsion(
        self,
        unit,
        terrain_points,
        terrain_weight: float,
        repulsion_x: float,
        repulsion_y: float,
    ) -> Tuple[float, float]:
        """Calculate repulsion from terrain obstacles."""
        for point in terrain_points:
            try:
                terrain_pos = getattr(point, "position", point)
                dist = unit.position.distance_to(terrain_pos)
            except Exception:
                continue
            if dist <= 0 or dist > self.terrain_radius:
                continue
            strength = (self.terrain_radius - dist) / self.terrain_radius
            dx = unit.position.x - terrain_pos.x
            dy = unit.position.y - terrain_pos.y
            repulsion_x += (dx / (dist + 0.1)) * strength * terrain_weight
            repulsion_y += (dy / (dist + 0.1)) * strength * terrain_weight
        return repulsion_x, repulsion_y
