# -*- coding: utf-8 -*-
"""
Targeting utilities for combat logic.

Provides basic prioritization for high-threat or low-health targets.
"""

from typing import Iterable, List, Optional, Sequence

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallback for tooling environments
    UnitTypeId = None


def _unit_type_ids(names: Sequence[str]) -> List[object]:
    if not UnitTypeId:
        return []
    ids: List[object] = []
    for name in names:
        unit_type = getattr(UnitTypeId, name, None)
        if unit_type is not None:
            ids.append(unit_type)
    return ids


HIGH_VALUE_TYPES = set(
    _unit_type_ids(
        [
            "SIEGETANKSIEGED",
            "SIEGETANK",
            "COLOSSUS",
            "IMMORTAL",
            "DISRUPTOR",
            "HIGHTEMPLAR",
            "ARCHON",
            "WIDOWMINE",
            "WIDOWMINEBURROWED",
            "BATTLECRUISER",
            "CARRIER",
            "TEMPEST",
            "GHOST",
        ]
    )
)


def _health_ratio(unit) -> float:
    health = getattr(unit, "health", None)
    health_max = getattr(unit, "health_max", None)
    if not health_max:
        return 1.0
    return max(0.0, min(1.0, health / health_max))


def _shield_ratio(unit) -> float:
    shield = getattr(unit, "shield", None)
    shield_max = getattr(unit, "shield_max", None)
    if not shield_max:
        return 1.0
    return max(0.0, min(1.0, shield / shield_max))


def _score_target(unit) -> float:
    base = 1.0
    if unit.type_id in HIGH_VALUE_TYPES:
        base += 3.0

    base += (1.0 - _health_ratio(unit)) * 2.0
    base += (1.0 - _shield_ratio(unit)) * 1.0

    if getattr(unit, "is_flying", False):
        base += 0.2

    if getattr(unit, "is_cloaked", False):
        base += 0.5

    return base


def prioritize_targets(enemies: Iterable) -> List:
    """Return enemies sorted by priority (highest first)."""
    enemy_list = list(enemies) if enemies else []
    enemy_list.sort(key=_score_target, reverse=True)
    return enemy_list


def select_target(unit, enemies: Iterable, max_range: float = 12.0) -> Optional[object]:
    """Pick the best target near the unit."""
    if not enemies:
        return None

    enemy_list = list(enemies)
    if hasattr(enemies, "closer_than") and hasattr(unit, "position"):
        try:
            enemy_list = list(enemies.closer_than(max_range, unit.position))
        except Exception:
            enemy_list = list(enemies)

    if not enemy_list:
        return None

    return prioritize_targets(enemy_list)[0]
