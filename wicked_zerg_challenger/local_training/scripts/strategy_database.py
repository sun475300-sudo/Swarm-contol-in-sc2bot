#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Database - Store and manage extracted strategies from replays

Features:
- Store strategies extracted during learning
- Query strategies by type, matchup, timing
- Track strategy effectiveness
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class StrategyType(Enum):
    """Strategy classification types"""
    BUILD_ORDER = "build_order"
    MICRO_CONTROL = "micro_control"
    MULTITASKING = "multitasking"
    DROP_TIMING = "drop_timing"
    RUSH = "rush"
    MACRO = "macro"
    LATE_GAME = "late_game"
    UNKNOWN = "unknown"


class MatchupType(Enum):
    """Matchup types"""
    ZVT = "ZvT"
    ZVP = "ZvP"
    ZVZ = "ZvZ"


@dataclass
class StrategyEntry:
    """Strategy database entry"""
    strategy_id: str
    strategy_type: str
    matchup: str
    timing: float  # Game time in seconds
    description: str
    extracted_from: str  # Replay filename
    extracted_at: str  # ISO timestamp
    effectiveness: Optional[float] = None  # Success rate or impact score
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyEntry':
        """Create from dictionary"""
        return cls(**data)


class StrategyDatabase:
    """Strategy database manager"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.strategies: Dict[str, StrategyEntry] = self._load_database()

    def _load_database(self) -> Dict[str, StrategyEntry]:
        """Load strategy database from JSON file"""
        if not self.db_path.exists():
            return {}

        try:
            content = self.db_path.read_text(encoding="utf-8")
            if not content.strip():
                return {}

            data = json.loads(content)
            strategies = {}
            for strategy_id, entry_data in data.items():
                try:
                    strategies[strategy_id] = StrategyEntry.from_dict(entry_data)
                except Exception as e:
                    print(f"[WARNING] Failed to load strategy {strategy_id}: {e}")
            return strategies

        except Exception as e:
            print(f"[WARNING] Failed to load strategy database: {e}")
            return {}

    def _save_database(self):
        """Save strategy database to JSON file"""
        try:
            data = {
                strategy_id: entry.to_dict()
                for strategy_id, entry in self.strategies.items()
            }
            self.db_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[ERROR] Failed to save strategy database: {e}")

    def add_strategy(
        self,
        strategy_type: StrategyType,
        matchup: MatchupType,
        timing: float,
        description: str,
        extracted_from: str,
        effectiveness: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new strategy to the database

        Returns:
            Strategy ID
        """
        strategy_id = f"{strategy_type.value}_{matchup.value}_{int(timing)}_{len(self.strategies)}"

        entry = StrategyEntry(
            strategy_id=strategy_id,
            strategy_type=strategy_type.value,
            matchup=matchup.value,
            timing=timing,
            description=description,
            extracted_from=extracted_from,
            extracted_at=datetime.now().isoformat(),
            effectiveness=effectiveness,
            details=details or {}
        )

        self.strategies[strategy_id] = entry
        self._save_database()

        return strategy_id

    def get_strategies(
        self,
        strategy_type: Optional[StrategyType] = None,
        matchup: Optional[MatchupType] = None,
        min_timing: Optional[float] = None,
        max_timing: Optional[float] = None
    ) -> List[StrategyEntry]:
        """
        Query strategies with filters

        Returns:
            List of matching strategy entries
        """
        results = []

        for entry in self.strategies.values():
            # Filter by strategy type
            if strategy_type and entry.strategy_type != strategy_type.value:
                continue

            # Filter by matchup
            if matchup and entry.matchup != matchup.value:
                continue

            # Filter by timing
            if min_timing is not None and entry.timing < min_timing:
                continue
            if max_timing is not None and entry.timing > max_timing:
                continue

            results.append(entry)

        return results

    def get_strategy_by_id(self, strategy_id: str) -> Optional[StrategyEntry]:
        """Get strategy by ID"""
        return self.strategies.get(strategy_id)

    def update_effectiveness(self, strategy_id: str, effectiveness: float):
        """Update strategy effectiveness score"""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].effectiveness = effectiveness
            self._save_database()

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        total = len(self.strategies)

        by_type = {}
        by_matchup = {}

        for entry in self.strategies.values():
            by_type[entry.strategy_type] = by_type.get(entry.strategy_type, 0) + 1
            by_matchup[entry.matchup] = by_matchup.get(entry.matchup, 0) + 1

        return {
            "total_strategies": total,
            "by_type": by_type,
            "by_matchup": by_matchup
        }


def main():
    """Test the strategy database"""
    import argparse

    parser = argparse.ArgumentParser(description="Strategy Database")
    parser.add_argument("--db-path", type=str, default="D:/replays/strategy_db.json", help="Database path")
    parser.add_argument("--list", action="store_true", help="List all strategies")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    args = parser.parse_args()

    db = StrategyDatabase(Path(args.db_path))

    if args.stats:
        stats = db.get_statistics()
        print("\n[STRATEGY DATABASE STATISTICS]")
        print("=" * 80)
        print(f"Total strategies: {stats['total_strategies']}")
        print(f"\nBy type: {stats['by_type']}")
        print(f"By matchup: {stats['by_matchup']}")

    if args.list:
        print("\n[ALL STRATEGIES]")
        print("=" * 80)
        for strategy_id, entry in db.strategies.items():
            print(f"\n{strategy_id}:")
            print(f"  Type: {entry.strategy_type}")
            print(f"  Matchup: {entry.matchup}")
            print(f"  Timing: {entry.timing}s")
            print(f"  Description: {entry.description}")
            print(f"  From: {entry.extracted_from}")


if __name__ == "__main__":
    main()
