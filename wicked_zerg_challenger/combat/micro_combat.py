#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Micro combat utilities with anti-splash awareness.
"""

from __future__ import annotations

import asyncio
import math
from typing import Iterable, List, Optional, Tuple

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:  # Fallbacks for tooling environments
    UnitTypeId = None
    Point2 = None


class AntiSplashAwareness:
    """Detects splash threats and provides repulsion/separation boosts."""

    def __init__(self) -> None:
        self.avoid_radius = 10.0
        self.min_multiplier = 5.0
        self.max_multiplier = 15.0  # Increased for better panic response
        self.air_multiplier = 12.0  # Increased for air units
        self.ground_multiplier = 8.0  # Increased for ground units
        self.extreme_threat_multiplier = 20.0  # For critical threats
        self.threat_types = set()
        self.extreme_threats = set()  # High-priority splash threats

        if UnitTypeId:
            # Regular splash threats - use getattr for compatibility
            threat_type_names = [
                "SIEGETANK", "SIEGETANKSIEGED", "HIGHTEMPLAR", "BANELING",
                "BANELINGBURROWED", "DISRUPTOR", "COLOSSUS", "HELLION",
                "HELLBAT", "HELLIONTANK", "LIBERATORAG", "LURKERMP",
                "LURKERMPBURROWED", "RAVEN", "WIDOWMINE", "WIDOWMINEBURROWED",
            ]
            for name in threat_type_names:
                unit_type = getattr(UnitTypeId, name, None)
                if unit_type is not None:
                    self.threat_types.add(unit_type)

            # Extreme threats requiring immediate panic split
            extreme_names = ["SIEGETANKSIEGED", "HIGHTEMPLAR", "DISRUPTOR", "BANELING"]
            for name in extreme_names:
                unit_type = getattr(UnitTypeId, name, None)
                if unit_type is not None:
                    self.extreme_threats.add(unit_type)

    def get_threats(self, enemy_units: Iterable) -> List:
        if not self.threat_types or not enemy_units:
            return []
        return [enemy for enemy in enemy_units if enemy.type_id in self.threat_types]

    def separation_multiplier(self, unit, enemy_units: Iterable) -> float:
        threats = self.get_threats(enemy_units)
        if not threats:
            return 1.0

        # Check for extreme threats first (panic mode)
        extreme_nearby = self._has_extreme_threat_nearby(unit, threats)
        if extreme_nearby:
            nearest = extreme_nearby
            if nearest <= self.avoid_radius * 1.2:  # Extended range for extreme threats
                ratio = max(0.0, 1.0 - (nearest / (self.avoid_radius * 1.2)))
                return min(
                    self.extreme_threat_multiplier,
                    self.max_multiplier
                    + ratio * (self.extreme_threat_multiplier - self.max_multiplier),
                )

        # Regular threat handling
        nearest = self._closest_threat_distance(unit, threats)
        if nearest is None or nearest > self.avoid_radius:
            return 1.0

        ratio = max(0.0, 1.0 - (nearest / self.avoid_radius))
        return min(
            self.max_multiplier,
            self.min_multiplier
            + ratio * (self.max_multiplier - self.min_multiplier),
        )

    def repulsion_vector(self, unit, enemy_units: Iterable) -> Tuple[float, float]:
        threats = self.get_threats(enemy_units)
        if not threats:
            return 0.0, 0.0

        repulsion_x = 0.0
        repulsion_y = 0.0
        weight = (
            self.air_multiplier
            if getattr(unit, "is_flying", False)
            else self.ground_multiplier
        )

        for threat in threats:
            try:
                dist = unit.distance_to(threat)
            except Exception:
                continue
            if dist <= 0 or dist > self.avoid_radius:
                continue
            strength = (self.avoid_radius - dist) / self.avoid_radius
            dx = unit.position.x - threat.position.x
            dy = unit.position.y - threat.position.y
            repulsion_x += (dx / (dist + 0.1)) * strength * weight
            repulsion_y += (dy / (dist + 0.1)) * strength * weight

        return repulsion_x, repulsion_y

    def _has_extreme_threat_nearby(self, unit, threats: Iterable) -> Optional[float]:
        """Check for extreme threats and return nearest distance, or None if no extreme threat."""
        if not self.extreme_threats:
            return None

        extreme_distances = []
        for threat in threats:
            if threat.type_id not in self.extreme_threats:
                continue
            try:
                dist = unit.distance_to(threat)
                extreme_distances.append(dist)
            except Exception:
                continue

        if not extreme_distances:
            return None
        return min(extreme_distances)

    @staticmethod
    def _closest_threat_distance(unit, threats: Iterable) -> Optional[float]:
        distances = []
        for threat in threats:
            try:
                distances.append(unit.distance_to(threat))
            except Exception:
                continue
        if not distances:
            return None
        return min(distances)


class ChokePointManager:
    """Detects chokepoints and adjusts unit behavior to prevent congestion."""

    def __init__(self, bot):
        self.bot = bot
        self.chokepoints = []
        self.chokepoint_cache_frame = -1
        self.chokepoint_radius = 5.0  # Detection radius for chokepoints

    def update_chokepoints(self, iteration: int) -> None:
        """Update chokepoint cache every 100 frames."""
        if iteration - self.chokepoint_cache_frame < 100:
            return

        self.chokepoint_cache_frame = iteration
        self.chokepoints = []

        # Get chokepoints from game_info if available
        if hasattr(self.bot, "game_info") and hasattr(
            self.bot.game_info, "map_ramps"
        ):
            for ramp in self.bot.game_info.map_ramps:
                if hasattr(ramp, "top_center"):
                    self.chokepoints.append(ramp.top_center)
                if hasattr(ramp, "bottom_center"):
                    self.chokepoints.append(ramp.bottom_center)

    def is_in_chokepoint(self, position) -> bool:
        """Check if position is near a chokepoint."""
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
        Return cohesion weight modifier for position.
        Lower cohesion in chokepoints to prevent clustering.
        """
        if self.is_in_chokepoint(position):
            return 0.3  # Reduce cohesion to 30% in chokepoints
        return 1.0  # Normal cohesion elsewhere


class MicroCombat:
    """Lightweight micro helpers with anti-splash reactions."""

    def __init__(self, bot):
        self.bot = bot
        self.anti_splash = AntiSplashAwareness()
        self.chokepoint_manager = ChokePointManager(bot)

    def focus_fire(self, units: Iterable, target) -> None:
        actions = []
        enemy_units = getattr(self.bot, "enemy_units", [])
        for unit in units:
            rep_x, rep_y = self.anti_splash.repulsion_vector(unit, enemy_units)
            if rep_x or rep_y:
                move_target = self._offset_position(unit, rep_x, rep_y)
                if move_target:
                    actions.append(unit.move(move_target))
                    continue
            actions.append(unit.attack(target))

        self._issue_actions(actions)

    def kiting(self, units: Iterable, enemy_units: Iterable) -> None:
        """
        Improved kiting logic: only kite when weapon is on cooldown.
        """
        actions = []
        threats = list(enemy_units) if enemy_units else []
        for unit in units:
            # 1. Queen Micro (Transfuse)
            if unit.type_id == getattr(UnitTypeId, "QUEEN", None):
                if self._micro_queen(unit, units, actions):
                    continue

            # 2. Baneling Micro (Crash into clumps)
            if unit.type_id == getattr(UnitTypeId, "BANELING", None):
                if self._micro_baneling(unit, threats, actions):
                    continue

            # 3. Anti-Splash Repulsion
            rep_x, rep_y = self.anti_splash.repulsion_vector(unit, threats)
            if rep_x or rep_y:
                move_target = self._offset_position(unit, rep_x, rep_y)
                if move_target:
                    actions.append(unit.move(move_target))
                    continue

            # 4. Kiting Logic
            target = self._closest_enemy(unit, threats)
            if target:
                # 무기 쿨다운 중이고 사거리가 닿으면 후퇴 (카이팅)
                # Kiting only if weapon is on cooldown
                weapon_cooldown = unit.weapon_cooldown
                ground_range = unit.ground_range
                distance = unit.distance_to(target)

                if weapon_cooldown > 0 and distance < ground_range:
                    # Retreat while cooling down
                    move_target = unit.position.towards(target.position, -2)
                    actions.append(unit.move(move_target))
                else:
                    # Attack if ready or out of range
                    actions.append(unit.attack(target))

        self._issue_actions(actions)

    def _micro_queen(self, queen, friendly_units: Iterable, actions: List) -> bool:
        """Queen Transfuse logic."""
        if not hasattr(self.bot, "abilities"):
            return False
            
        transfuse_id = getattr(self.bot.abilities, "TRANSFUSION_TRANSFUSION", None)
        if not transfuse_id:
            return False

        if queen.energy < 50:
            return False

        # Find injured biological unit/structure nearby
        low_hp_units = [
            u for u in friendly_units 
            if u.is_biological and u.health_percentage < 0.4 and u.distance_to(queen) < 7
        ]
        
        if low_hp_units:
            # Heal the most injured one
            target = min(low_hp_units, key=lambda u: u.health)
            actions.append(queen(transfuse_id, target))
            return True
            
        return False

    def _micro_baneling(self, baneling, enemy_units: Iterable, actions: List) -> bool:
        """Baneling optimization: avoid single units, target clumps."""
        if not enemy_units:
            return False
            
        nearby_enemies = [e for e in enemy_units if e.distance_to(baneling) < 10]
        if not nearby_enemies:
            return False
            
        # 1. Prioritize structures and light units (marines/lings)
        vital_targets = [
            e for e in nearby_enemies 
            if e.is_structure or e.is_light
        ]
        
        if vital_targets:
            # Find the densest cluster center
            center = self._find_center_of_mass(vital_targets)
            if center:
                 actions.append(baneling.move(center))
                 return True
                 
        return False

    def _find_center_of_mass(self, units) -> Optional[Point2]:
        if not units or not Point2:
            return None
        total_x = sum(u.position.x for u in units)
        total_y = sum(u.position.y for u in units)
        return Point2((total_x / len(units), total_y / len(units)))

    @staticmethod
    def _closest_enemy(unit, enemies: Iterable):
        closest = None
        closest_dist = None
        for enemy in enemies:
            try:
                dist = unit.distance_to(enemy)
            except Exception:
                continue
            if closest_dist is None or dist < closest_dist:
                closest = enemy
                closest_dist = dist
        return closest

    @staticmethod
    def _offset_position(unit, dx: float, dy: float):
        if not Point2:
            return None
        try:
            return unit.position + Point2((dx, dy))
        except Exception:
            return None

    def _issue_actions(self, actions: List) -> None:
        if not actions:
            return
        if not hasattr(self.bot, "do_actions"):
            return
        try:
            coro = self.bot.do_actions(actions)
        except Exception:
            return
        if asyncio.iscoroutine(coro):
            try:
                asyncio.create_task(coro)
            except RuntimeError:
                pass
