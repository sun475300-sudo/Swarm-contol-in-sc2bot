#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Learning Logger - Log learning progress and extracted strategies

Features:
- Log each learning completion with strategy summary
- Track which strategies were extracted from which replays
- Maintain learning history
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


class LearningLogger:
    """Log learning progress and extracted strategies"""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_learning_completion(
        self,
        replay_path: Path,
        iteration: int,
        phase: str,
        strategies_extracted: List[Dict[str, Any]],
        focus_areas: Dict[str, Any]
    ):
        """
        Log learning completion for a replay

        Args:
            replay_path: Path to replay file
            iteration: Current iteration number
            phase: Learning phase (early_game, mid_game, late_game)
            strategies_extracted: List of strategies extracted
            focus_areas: Focus areas for this iteration
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "replay": replay_path.name,
            "iteration": iteration,
            "phase": phase,
            "focus_areas": focus_areas,
            "strategies_extracted": strategies_extracted,
            "strategy_count": len(strategies_extracted)
        }

        # Append to log file
        try:
            # Read existing logs
            existing_logs = []
            if self.log_file.exists():
                content = self.log_file.read_text(encoding="utf-8")
                if content.strip():
                    try:
                        existing_logs = json.loads(content)
                        if not isinstance(existing_logs, list):
                            existing_logs = []
                    except json.JSONDecodeError:
                        existing_logs = []

            # Append new entry
            existing_logs.append(log_entry)

            # Write back
            self.log_file.write_text(
                json.dumps(existing_logs, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

        except Exception as e:
            print(f"[WARNING] Failed to write learning log: {e}")

    def log_strategy_extraction(
        self,
        replay_path: Path,
        strategy_type: str,
        timing: float,
        description: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a specific strategy extraction

        Args:
            replay_path: Path to replay file
            strategy_type: Type of strategy (e.g., "drop_timing", "build_order")
            timing: Game time in seconds when strategy occurred
            description: Description of the strategy
            details: Additional details about the strategy
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "replay": replay_path.name,
            "strategy_type": strategy_type,
            "timing": timing,
            "description": description,
            "details": details or {}
        }

        # Append to strategy log
        strategy_log_file = self.log_file.parent / "strategy_extractions.json"
        try:
            existing_logs = []
            if strategy_log_file.exists():
                content = strategy_log_file.read_text(encoding="utf-8")
                if content.strip():
                    try:
                        existing_logs = json.loads(content)
                        if not isinstance(existing_logs, list):
                            existing_logs = []
                    except json.JSONDecodeError:
                        existing_logs = []

            existing_logs.append(log_entry)
            strategy_log_file.write_text(
                json.dumps(existing_logs, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

        except Exception as e:
            print(f"[WARNING] Failed to write strategy log: {e}")

    def get_learning_summary(self, replay_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Get learning summary

        Args:
            replay_path: Optional filter by specific replay

        Returns:
            Summary statistics
        """
        if not self.log_file.exists():
            return {"total_entries": 0, "total_strategies": 0}

        try:
            content = self.log_file.read_text(encoding="utf-8")
            if not content.strip():
                return {"total_entries": 0, "total_strategies": 0}

            logs = json.loads(content)
            if not isinstance(logs, list):
                logs = []

            # Filter by replay if specified
            if replay_path:
                logs = [log for log in logs if log.get("replay") == replay_path.name]

            total_strategies = sum(log.get("strategy_count", 0) for log in logs)

            # Count by phase
            phase_counts = {}
            for log in logs:
                phase = log.get("phase", "unknown")
                phase_counts[phase] = phase_counts.get(phase, 0) + 1

            return {
                "total_entries": len(logs),
                "total_strategies": total_strategies,
                "by_phase": phase_counts
            }

        except Exception as e:
            print(f"[WARNING] Failed to read learning log: {e}")
            return {"total_entries": 0, "total_strategies": 0, "error": str(e)}


def main():
    """Test the learning logger"""
    import argparse

    parser = argparse.ArgumentParser(description="Learning Logger")
    parser.add_argument("--log-file", type=str, default="D:/replays/learning_log.txt", help="Log file path")
    parser.add_argument("--summary", action="store_true", help="Show learning summary")
    args = parser.parse_args()

    logger = LearningLogger(Path(args.log_file))

    if args.summary:
        summary = logger.get_learning_summary()
        print("\n[LEARNING SUMMARY]")
        print("=" * 80)
        print(f"Total entries: {summary.get('total_entries', 0)}")
        print(f"Total strategies: {summary.get('total_strategies', 0)}")
        if 'by_phase' in summary:
            print(f"By phase: {summary['by_phase']}")


if __name__ == "__main__":
    main()
