# -*- coding: utf-8 -*-
"""
Terrain Analysis - Chokepoint detection and terrain-aware modifiers.

This module provides terrain analysis capabilities for tactical decision making,
including chokepoint detection and cohesion modifiers for unit movement.
"""

from typing import List, Optional

try:
    from sc2.position import Point2
except ImportError:
    Point2 = None


class ChokePointDetector:
    """
    Detects chokepoints and narrow passages on the map.

    Caches chokepoint positions and provides utility methods
    for terrain-aware unit behavior modifications.
    """

    def __init__(
        self,
        bot,
        chokepoint_radius: float = 6.0,
        narrow_passage_threshold: float = 4.0,
        cache_update_interval: int = 100,
    ):
        """
        Initialize chokepoint detector.

        Args:
            bot: The bot instance with game_info access
            chokepoint_radius: Radius to consider as "near" a chokepoint
            narrow_passage_threshold: Width threshold for narrow passages
            cache_update_interval: Frames between cache updates
        """
        self.bot = bot
        self.chokepoints: List = []
        self.chokepoint_cache_frame = -1
        self.chokepoint_radius = chokepoint_radius
        self.narrow_passage_threshold = narrow_passage_threshold
        self.cache_update_interval = cache_update_interval

    def update_chokepoints(self, iteration: int) -> None:
        """
        Update chokepoint cache periodically.

        Args:
            iteration: Current game iteration/frame
        """
        if iteration - self.chokepoint_cache_frame < self.cache_update_interval:
            return

        self.chokepoint_cache_frame = iteration
        self.chokepoints = []

        # Get map ramps and chokepoints from game_info
        if hasattr(self.bot, "game_info"):
            game_info = self.bot.game_info
            if hasattr(game_info, "map_ramps"):
                for ramp in game_info.map_ramps:
                    if hasattr(ramp, "top_center"):
                        self.chokepoints.append(ramp.top_center)
                    if hasattr(ramp, "bottom_center"):
                        self.chokepoints.append(ramp.bottom_center)

    def is_in_chokepoint(self, position) -> bool:
        """
        Check if position is near a detected chokepoint.

        Args:
            position: Position to check (Point2 or similar)

        Returns:
            True if position is within chokepoint_radius of any chokepoint
        """
        if not self.chokepoints or not position:
            return False

        for choke in self.chokepoints:
            try:
                if position.distance_to(choke) < self.chokepoint_radius:
                    return True
            except Exception:
                continue
        return False

    def get_cohesion_modifier(self, position) -> float:
        """
        Return cohesion weight modifier based on terrain.

        Lower cohesion in chokepoints to prevent traffic jams and
        allow units to spread out in narrow passages.

        Args:
            position: Position to check

        Returns:
            Float modifier (0.25 in chokepoints, 1.0 elsewhere)
        """
        if self.is_in_chokepoint(position):
            return 0.25  # Reduce cohesion to 25% in chokepoints
        return 1.0

    def get_nearest_chokepoint(self, position) -> Optional[object]:
        """
        Find the nearest chokepoint to a given position.

        Args:
            position: Position to search from

        Returns:
            Nearest chokepoint position or None
        """
        if not self.chokepoints or not position:
            return None

        nearest = None
        nearest_dist = float("inf")

        for choke in self.chokepoints:
            try:
                dist = position.distance_to(choke)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = choke
            except Exception:
                continue

        return nearest

    def get_chokepoint_avoidance_vector(
        self, position, avoidance_weight: float = 1.0
    ) -> tuple:
        """
        Calculate a vector pointing away from nearby chokepoints.

        Args:
            position: Current position
            avoidance_weight: Weight multiplier for avoidance

        Returns:
            Tuple of (x, y) avoidance vector
        """
        if not self.chokepoints or not position or not Point2:
            return 0.0, 0.0

        avoid_x = 0.0
        avoid_y = 0.0

        for choke in self.chokepoints:
            try:
                dist = position.distance_to(choke)
                if dist > self.chokepoint_radius or dist <= 0:
                    continue

                strength = (self.chokepoint_radius - dist) / self.chokepoint_radius
                dx = position.x - choke.x
                dy = position.y - choke.y
                avoid_x += (dx / (dist + 0.1)) * strength * avoidance_weight
                avoid_y += (dy / (dist + 0.1)) * strength * avoidance_weight
            except Exception:
                continue

        return avoid_x, avoid_y
