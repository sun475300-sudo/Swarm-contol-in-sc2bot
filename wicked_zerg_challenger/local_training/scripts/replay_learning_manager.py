#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replay Learning Manager - Track and manage learning iterations per replay

Features:
- Track learning count for each replay file
- Minimum 5 iterations per replay requirement
- Move completed replays to completed folder
- Integration with training pipeline
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import shutil
from enum import Enum


class LearningPhase(Enum):
    """Learning phases for focused analysis"""
    EARLY_GAME = "early_game"  # 0-5 minutes: Build order focus
    MID_GAME = "mid_game"  # 5-15 minutes: Unit composition and skirmishes
    LATE_GAME = "late_game"  # 15+ minutes: Macro and spell unit usage


class ReplayLearningTracker:
    """Track learning count for each replay file"""

    def __init__(self, tracking_file: Path, min_iterations: int = 5):
        self.tracking_file = tracking_file
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        self.min_iterations = min_iterations
        self.learning_counts: Dict[str, Dict] = self._load_tracking()

    def get_learning_phase(self, iteration: int) -> LearningPhase:
        """
        Determine learning phase based on iteration number

        Phase distribution:
        - Iterations 1-2: Early game (build order)
        - Iterations 3-4: Mid game (unit composition, skirmishes)
        - Iteration 5+: Late game (macro, spell units)
        """
        if iteration <= 2:
            return LearningPhase.EARLY_GAME
        elif iteration <= 4:
            return LearningPhase.MID_GAME
        else:
            return LearningPhase.LATE_GAME

    def get_phase_focus(self, iteration: int) -> Dict[str, any]:
        """
        Get focus areas for current learning phase

        Returns:
            Dictionary with focus areas and weights
        """
        phase = self.get_learning_phase(iteration)

        if phase == LearningPhase.EARLY_GAME:
            return {
                "phase": "early_game",
                "time_range": (0, 300),  # 0-5 minutes
                "focus": ["build_order", "opening", "economy_setup"],
                "weights": {"build_order": 0.6, "economy": 0.3, "scouting": 0.1}
            }
        elif phase == LearningPhase.MID_GAME:
            return {
                "phase": "mid_game",
                "time_range": (300, 900),  # 5-15 minutes
                "focus": ["unit_composition", "micro_control", "skirmishes", "multitasking"],
                "weights": {"unit_composition": 0.4, "micro": 0.3, "multitasking": 0.2, "economy": 0.1}
            }
        else:  # LATE_GAME
            return {
                "phase": "late_game",
                "time_range": (900, None),  # 15+ minutes
                "focus": ["macro_management", "spell_units", "late_game_units", "map_control"],
                "weights": {"macro": 0.4, "spell_units": 0.3, "map_control": 0.2, "economy": 0.1}
            }

    def _load_tracking(self) -> Dict[str, Dict]:
        """Load learning count tracking from JSON file"""
        if not self.tracking_file.exists():
            return {}
        try:
            content = self.tracking_file.read_text(encoding="utf-8")
            if not content.strip():
                return {}
            data = json.loads(content)
            # Support both old format (count only) and new format (full metadata)
            if isinstance(data, dict):
                # Convert old format to new format
                converted = {}
                for key, value in data.items():
                    if isinstance(value, int):
                        converted[key] = {
                            "count": value,
                            "last_trained": None,
                            "completed": value >= self.min_iterations
                        }
                    else:
                        converted[key] = value
                return converted
            return {}
        except Exception as e:
            print(f"[WARNING] Failed to load learning tracking: {e}")
            return {}

    def _save_tracking(self):
        """Save learning count tracking to JSON file"""
        try:
            # CRITICAL: Atomic write to prevent corruption
            temp_file = self.tracking_file.with_suffix('.tmp')
            temp_file.write_text(
                json.dumps(self.learning_counts, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            # Atomic move
            import os
            os.replace(str(temp_file), str(self.tracking_file))
        except Exception as e:
            print(f"[WARNING] Failed to save learning tracking: {e}")

    def _get_replay_hash(self, replay_path: Path) -> str:
        """Get hash of replay file for tracking"""
        try:
            # Use file size + modification time as hash (faster than full file hash)
            stat = replay_path.stat()
            hash_input = f"{replay_path.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(hash_input.encode()).hexdigest()
        except Exception:
            # Fallback to filename
            return hashlib.md5(replay_path.name.encode()).hexdigest()

    def get_learning_count(self, replay_path: Path) -> int:
        """Get current learning count for a replay"""
        replay_hash = self._get_replay_hash(replay_path)
        entry = self.learning_counts.get(replay_hash, {})
        if isinstance(entry, int):
            # Old format compatibility
            return entry
        return entry.get("count", 0)

    def increment_learning_count(self, replay_path: Path) -> int:
        """Increment learning count for a replay and return new count"""
        replay_hash = self._get_replay_hash(replay_path)
        entry = self.learning_counts.get(replay_hash, {})

        if isinstance(entry, int):
            # Old format compatibility
            current_count = entry
        else:
            current_count = entry.get("count", 0)

        new_count = current_count + 1
        self.learning_counts[replay_hash] = {
            "filename": replay_path.name,
            "count": new_count,
            "last_trained": datetime.now().isoformat(),
            "completed": new_count >= self.min_iterations
        }
        self._save_tracking()
        return new_count

    def is_completed(self, replay_path: Path) -> bool:
        """Check if replay has completed minimum learning iterations"""
        return self.get_learning_count(replay_path) >= self.min_iterations

    def get_replays_for_training(self, replay_dir: Path, completed_dir: Path) -> List[Path]:
        """
        Get list of replays that need training (not yet completed)

        Returns:
            List of replay paths that need more training iterations
        """
        all_replays = list(replay_dir.glob("*.SC2Replay"))
        training_replays = []

        for replay_path in all_replays:
            # Skip completed folder
            if completed_dir in replay_path.parents:
                continue

            # Skip if already completed
            if self.is_completed(replay_path):
                continue

            training_replays.append(replay_path)

        return training_replays

    def move_completed_replay(self, replay_path: Path, completed_dir: Path) -> bool:
        """Move completed replay to completed folder"""
        try:
            target = completed_dir / replay_path.name
            if not target.exists():
                shutil.move(str(replay_path), str(target))
                return True
            else:
                # Target exists, remove source
                replay_path.unlink()
                return True
        except Exception as e:
            print(f"[ERROR] Failed to move completed replay {replay_path.name}: {e}")
            return False


def main():
    """Test the learning tracker"""
    import argparse

    parser = argparse.ArgumentParser(description="Replay Learning Tracker")
    parser.add_argument("--replay-dir", type=str, default="D:/replays", help="Replay directory")
    parser.add_argument("--list", action="store_true", help="List replay learning status")
    args = parser.parse_args()

    replay_dir = Path(args.replay_dir)
    completed_dir = replay_dir / "completed"
    tracking_file = replay_dir / ".learning_tracking.json"

    tracker = ReplayLearningTracker(tracking_file)

    if args.list:
        print(f"\n[LEARNING STATUS] Replays in {replay_dir}")
        print("=" * 80)

        all_replays = list(replay_dir.glob("*.SC2Replay"))
        for replay_path in all_replays:
            count = tracker.get_learning_count(replay_path)
            completed = tracker.is_completed(replay_path)
            status = "COMPLETED" if completed else f"{count}/{tracker.min_iterations}"
            print(f"  {replay_path.name}: {status}")

        print(f"\nTotal: {len(all_replays)} replays")
        completed_count = sum(1 for rp in all_replays if tracker.is_completed(rp))
        print(f"Completed: {completed_count}, Pending: {len(all_replays) - completed_count}")


if __name__ == "__main__":
    main()
