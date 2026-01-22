#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map Manager for training.

Handles map rotation, selection, and performance tracking.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Dict, List, Optional

TRAINING_MAPS = [
    "LeyLinesAIE_v3",
    "2000AtmospheresAIE",
    "HardwireAIE",
    "BerlingradAIE",
    "BlackburnAIE",
    "CuriosityAIE",
    "IncorporealAIE_v4",
]

MAP_CHARACTERISTICS = {
    "LeyLinesAIE_v3": {
        "description": "Tournament map with standard layout",
        "focus": "General gameplay",
        "difficulty": "Medium",
    },
    "2000AtmospheresAIE": {
        "description": "Wide natural expansion, standard 3-base routes",
        "focus": "Economy optimization and basic macro",
        "difficulty": "Easy",
    },
    "HardwireAIE": {
        "description": "Complex chokepoints, rich resource areas",
        "focus": "Unit control and chokepoint blocking",
        "difficulty": "Hard",
    },
    "BerlingradAIE": {
        "description": "Open areas favor mobility",
        "focus": "Large-scale battles and chaos",
        "difficulty": "Medium",
    },
    "BlackburnAIE": {
        "description": "Relatively short rush distance",
        "focus": "Early pressure defense and crisis management",
        "difficulty": "Hard",
    },
    "CuriosityAIE": {
        "description": "Simple terrain for easy data extraction",
        "focus": "Build order precision testing",
        "difficulty": "Easy",
    },
    "IncorporealAIE_v4": {
        "description": "Available tournament map",
        "focus": "General gameplay",
        "difficulty": "Medium",
    },
}


class MapManager:
    """Manages map selection and performance tracking."""

    def __init__(self, stats_file: str = "map_performance.json"):
        self.stats_file = Path(stats_file)
        self.stats: Dict[str, Dict[str, int]] = self._load_stats()
        self.current_map_index = 0

    def _load_stats(self) -> Dict[str, Dict[str, int]]:
        if not self.stats_file.exists():
            return {}

        try:
            with open(self.stats_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[WARNING] Map stats file read error: {exc}")
        return {}

    def _save_stats(self) -> None:
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        max_retries = 3

        for attempt in range(max_retries):
            try:
                with open(self.stats_file, "w", encoding="utf-8") as handle:
                    json.dump(self.stats, handle, indent=2, ensure_ascii=False)
                return
            except OSError as exc:
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                print(f"[WARNING] Failed to save map stats: {exc}")
                return

    def get_available_maps(self) -> List[str]:
        maps_path = Path("Maps")
        if not maps_path.exists():
            return TRAINING_MAPS.copy()

        all_maps = [m.stem for m in maps_path.glob("*.SC2Map")]
        if not all_maps:
            return TRAINING_MAPS.copy()

        available: List[str] = []
        for map_name in TRAINING_MAPS:
            if map_name in all_maps:
                available.append(map_name)

        for map_name in sorted(all_maps):
            if map_name not in available:
                available.append(map_name)

        return available

    def select_map(self, mode: str = "sequential") -> str:
        available = self.get_available_maps()
        if not available:
            return "LeyLinesAIE_v3"

        if mode == "single":
            return available[0]
        if mode == "random":
            return random.choice(available)
        if mode == "weighted":
            return self._select_weighted(available)

        selected = available[self.current_map_index % len(available)]
        self.current_map_index += 1
        return selected

    def _select_weighted(self, available: List[str]) -> str:
        weights = []
        for map_name in available:
            stats = self.stats.get(map_name, {"wins": 0, "losses": 0})
            total = stats.get("wins", 0) + stats.get("losses", 0)
            win_rate = stats.get("wins", 0) / total if total else 0.0
            weight = max(0.2, 1.0 - win_rate)
            weights.append(weight)

        return random.choices(available, weights=weights, k=1)[0]

    def record_result(self, map_name: str, win: bool) -> None:
        stats = self.stats.setdefault(map_name, {"wins": 0, "losses": 0})
        if win:
            stats["wins"] += 1
        else:
            stats["losses"] += 1
        self._save_stats()

    def get_map_stats(self, map_name: str) -> Dict[str, int]:
        return self.stats.get(map_name, {"wins": 0, "losses": 0})
