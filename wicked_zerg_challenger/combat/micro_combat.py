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
        self.max_multiplier = 10.0
        self.air_multiplier = 10.0
        self.ground_multiplier = 6.0
        self.threat_types = set()
        if UnitTypeId:
            self.threat_types = {
                UnitTypeId.SIEGETANK,
                UnitTypeId.SIEGETANKSIEGED,
                UnitTypeId.HIGHTEMPLAR,
                UnitTypeId.BANELING,
                UnitTypeId.BANELINGBURROWED,
                UnitTypeId.DISRUPTOR,
            }

    def get_threats(self, enemy_units: Iterable) -> List:
        if not self.threat_types or not enemy_units:
            return []
        return [enemy for enemy in enemy_units if enemy.type_id in self.threat_types]

    def separation_multiplier(self, unit, enemy_units: Iterable) -> float:
        threats = self.get_threats(enemy_units)
        if not threats:
            return 1.0

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


class MicroCombat:
    """Lightweight micro helpers with anti-splash reactions."""

    def __init__(self, bot):
        self.bot = bot
        self.anti_splash = AntiSplashAwareness()

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
        actions = []
        threats = list(enemy_units) if enemy_units else []
        for unit in units:
            rep_x, rep_y = self.anti_splash.repulsion_vector(unit, threats)
            if rep_x or rep_y:
                move_target = self._offset_position(unit, rep_x, rep_y)
                if move_target:
                    actions.append(unit.move(move_target))
                    continue

            target = self._closest_enemy(unit, threats)
            if target and hasattr(unit, "distance_to"):
                try:
                    if unit.distance_to(target) < 6:
                        move_target = unit.position.towards(target.position, -3)
                        actions.append(unit.move(move_target))
                        continue
                except Exception:
                    pass
            if target:
                actions.append(unit.attack(target))

        self._issue_actions(actions)

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
