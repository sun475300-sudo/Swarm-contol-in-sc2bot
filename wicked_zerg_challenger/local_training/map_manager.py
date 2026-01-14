# -*- coding: utf-8 -*-
"""
Map Manager for Training
Manages map rotation, selection, and performance tracking
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

import json
import random
from typing import Dict, List, Optional

# Training map pool (Zerg vs Terran focus)
TRAINING_MAPS = [
    "LeyLinesAIE_v3",  # Current default
    "2000AtmospheresAIE",
    "HardwireAIE",
    "BerlingradAIE",
    "BlackburnAIE",
    "CuriosityAIE",
    "IncorporealAIE_v4",  # Available in Maps folder
]

# Map characteristics for reference
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
    """
    Manages map selection and performance tracking
    """

    def __init__(self, stats_file: str = "map_performance.json"):
        """
        Initialize map manager

        Args:
            stats_file: Path to map performance statistics file
        """
        self.stats_file = Path(stats_file)
        self.stats: Dict = self._load_stats()
        self.current_map_index = 0

    def _load_stats(self) -> Dict:
        """Load map performance statistics"""
        if self.stats_file.exists():
            try:
                try:
                    with open(self.stats_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except (IOError, OSError, json.JSONDecodeError) as file_error:
                    print(f"[WARNING] Map stats file read error: {file_error}")
                    return {}
            except Exception:
                return {}
        return {}

    def _save_stats(self):
        """Save map performance statistics"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(self.stats_file, "w", encoding="utf-8") as f:
                    json.dump(self.stats, f, indent=2, ensure_ascii=False)
                return  # Success
            except (IOError, OSError) as e:
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    print(f"[WARNING] Failed to save map stats after {max_retries} retries: {e}")
            except Exception as e:
                print(f"[WARNING] Failed to save map stats: {e}")
                break

    def get_available_maps(self) -> List[str]:
        """
        Get list of available maps from Maps folder

        Returns all .SC2Map files found in the Maps folder,
        prioritizing maps in TRAINING_MAPS list first.

        Returns:
            List of available map names (all maps found)
        """
        maps_path = Path("Maps")
        if not maps_path.exists():
            return []

        available = []
        all_maps = []

        # First, collect all .SC2Map files
        for map_file in maps_path.glob("*.SC2Map"):
            map_name = map_file.stem
            all_maps.append(map_name)

        # Prioritize training maps first, then add others
        for map_name in TRAINING_MAPS:
            if map_name in all_maps:
                available.append(map_name)

        # Add remaining maps that are not in TRAINING_MAPS
        for map_name in sorted(all_maps):
            if map_name not in available:
                available.append(map_name)

        return available

    def select_map(self, mode: str = "sequential") -> str:
        """
        Select a map based on mode

        Args:
            mode: Selection mode
                - "sequential": Rotate through maps in order
                - "random": Random selection
                - "weighted": Weighted by performance
                - "single": Use first available map

        Returns:
            Selected map name
        """
        available = self.get_available_maps()

        if not available:
            # Fallback to default
            return "LeyLinesAIE_v3"

        if mode == "single":
            return available[0]
        elif mode == "random":
            return random.choice(available)
        elif mode == "weighted":
            return self._select_weighted(available)
        else:  # sequential
            selected = available[self.current_map_index % len(available)]
            self.current_map_index += 1
            return selected

    def _select_weighted(self, available: List[str]) -> str:
        """
        Select map based on performance (prefer maps with lower win rate)

        Args:
            available: List of available maps

        Returns:
            Selected map name
        """
        if not self.stats:
            return random.choice(available)

        # Calculate weights (lower win rate = higher weight for training)
        weights = []
        for map_name in available:
            map_stats = self.stats.get(map_name, {})
            wins = map_stats.get("wins", 0)
            losses = map_stats.get("losses", 0)
            total = wins + losses

            if total == 0:
                weight = 10  # High weight for untested maps
            else:
                win_rate = wins / total
                # Lower win rate = higher weight (need more training)
                weight = int((1.0 - win_rate) * 10) + 1

            weights.append(weight)

        return random.choices(available, weights=weights, k=1)[0]

    def record_result(self, map_name: str, result: str, game_time: float = 0):
        """
        Record game result for a map

        Args:
            map_name: Name of the map
            result: "victory" or "defeat"
            game_time: Game duration in seconds
        """
        if map_name not in self.stats:
            self.stats[map_name] = {"wins": 0, "losses": 0, "total_time": 0, "games": 0}

        if result.lower() == "victory":
            self.stats[map_name]["wins"] += 1
        else:
            self.stats[map_name]["losses"] += 1

        self.stats[map_name]["games"] += 1
        self.stats[map_name]["total_time"] += game_time

        self._save_stats()

    def get_map_stats(self, map_name: str) -> Dict:
        """
        Get statistics for a specific map

        Args:
            map_name: Name of the map

        Returns:
            Dictionary with map statistics
        """
        stats = self.stats.get(map_name, {"wins": 0, "losses": 0, "total_time": 0, "games": 0})

        total = stats["wins"] + stats["losses"]
        if total > 0:
            stats["win_rate"] = stats["wins"] / total
            stats["avg_time"] = stats["total_time"] / total
        else:
            stats["win_rate"] = 0.0
            stats["avg_time"] = 0.0

        return stats

    def get_performance_report(self) -> str:
        """
        Generate performance report for all maps

        Returns:
            Formatted report string
        """
        if not self.stats:
            return "No map performance data available yet."

        report = ["=" * 70]
        report.append("Map Performance Report")
        report.append("=" * 70)
        report.append("")

        # Sort by win rate (ascending - worst first)
        sorted_maps = sorted(
            self.stats.items(),
            key=lambda x: x[1].get("wins", 0) / max(x[1].get("wins", 0) + x[1].get("losses", 0), 1),
        )

        for map_name, stats in sorted_maps:
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            total = wins + losses

            if total == 0:
                continue

            win_rate = wins / total * 100
            avg_time = stats.get("total_time", 0) / total if total > 0 else 0

            report.append(f"Map: {map_name}")
            report.append(f"  Games: {total} | Wins: {wins} | Losses: {losses}")
            report.append(f"  Win Rate: {win_rate:.1f}% | Avg Time: {avg_time:.1f}s")

            # Add recommendation
            if win_rate < 30:
                report.append(f"  ??  Low win rate - needs more training")
            elif win_rate > 70:
                report.append(f"  ? High win rate - performing well")

            report.append("")

        report.append("=" * 70)
        return "\n".join(report)


# Global map manager instance
_map_manager: Optional[MapManager] = None


def get_map_manager() -> MapManager:
    """Get global map manager instance"""
    global _map_manager
    if _map_manager is None:
        _map_manager = MapManager()
    return _map_manager
