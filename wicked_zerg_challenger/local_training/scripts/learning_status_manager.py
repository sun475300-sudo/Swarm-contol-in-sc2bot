#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Learning Status Manager - Hard requirement enforcement for 5 iterations per replay

This module provides a robust, file-based tracking system to ensure that
each replay file is learned at least 5 times before being moved or deleted.

CRITICAL: This is a hard requirement - files with < 5 learning iterations
MUST NOT be moved/deleted under any circumstances.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import os


class LearningStatusManager:
    """
    Hard requirement: Minimum 5 learning iterations per replay

    This manager enforces the "5 iterations per replay" requirement by:
    1. Maintaining a clear JSON file with replay names and counts
    2. Preventing any move/delete operations on files with < 5 iterations
    3. Providing clear status reporting
    """

    def __init__(self, status_file: Path, min_iterations: int = 5):
        """
        Args:
            status_file: Path to learning_status.json file
            min_iterations: Minimum required learning iterations (default: 5)
        """
        self.status_file = status_file
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.min_iterations = min_iterations
        self.status_data = self._load_status()

    def _load_status(self) -> Dict:
        """Load learning status from JSON file"""
        if not self.status_file.exists():
            # Initialize with format version
            return {
                "_format_version": "1.0",
                "_description": "Replay learning status tracking - Hard requirement: Minimum 5 iterations per replay",
                "_last_updated": datetime.now().isoformat(),
                "replays": {}
            }

        try:
            content = self.status_file.read_text(encoding="utf-8")
            if not content.strip():
                return self._get_default_status()

            data = json.loads(content)
            # Ensure required fields exist
            if "replays" not in data:
                data["replays"] = {}
            return data
        except Exception as e:
            print(f"[WARNING] Failed to load learning status: {e}")
            return self._get_default_status()

    def _get_default_status(self) -> Dict:
        """Get default status structure"""
        return {
            "_format_version": "1.0",
            "_description": "Replay learning status tracking - Hard requirement: Minimum 5 iterations per replay",
            "_last_updated": datetime.now().isoformat(),
            "replays": {}
        }

    def _save_status(self):
        """Save learning status to JSON file (atomic write)"""
        try:
            self.status_data["_last_updated"] = datetime.now().isoformat()

            # CRITICAL: Atomic write to prevent corruption
            temp_file = self.status_file.with_suffix('.tmp')
            temp_file.write_text(
                json.dumps(self.status_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            # Atomic move
            os.replace(str(temp_file), str(self.status_file))
        except Exception as e:
            print(f"[ERROR] Failed to save learning status: {e}")
            raise

    def _get_replay_key(self, replay_path: Path) -> str:
        """Get unique key for replay file"""
        try:
            stat = replay_path.stat()
            # Use filename + size + mtime for unique identification
            key_input = f"{replay_path.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(key_input.encode()).hexdigest()
        except Exception:
            # Fallback to filename
            return hashlib.md5(replay_path.name.encode()).hexdigest()

    def get_learning_count(self, replay_path: Path) -> int:
        """
        Get current learning count for a replay

        Returns:
            Current learning count (0 if not found)
        """
        replay_key = self._get_replay_key(replay_path)
        replay_entry = self.status_data["replays"].get(replay_key, {})

        if isinstance(replay_entry, int):
            # Old format compatibility
            return replay_entry

        return replay_entry.get("count", 0)

    def increment_learning_count(self, replay_path: Path) -> int:
        """
        Increment learning count for a replay

        CRITICAL: This MUST be called after each learning iteration

        Returns:
            New learning count
        """
        replay_key = self._get_replay_key(replay_path)
        current_count = self.get_learning_count(replay_path)
        new_count = current_count + 1

        # Update status
        self.status_data["replays"][replay_key] = {
            "filename": replay_path.name,
            "count": new_count,
            "last_trained": datetime.now().isoformat(),
            "completed": new_count >= self.min_iterations,
            "file_path": str(replay_path)
        }

        self._save_status()
        return new_count

    def is_completed(self, replay_path: Path) -> bool:
        """
        Check if replay has completed minimum learning iterations

        CRITICAL: Only returns True if count >= min_iterations (5)
        """
        return self.get_learning_count(replay_path) >= self.min_iterations

    def can_move_or_delete(self, replay_path: Path) -> bool:
        """
        Check if replay can be moved or deleted

        CRITICAL: Returns False if learning count < min_iterations

        This is a hard requirement - files with < 5 iterations MUST NOT be moved/deleted
        """
        count = self.get_learning_count(replay_path)
        if count < self.min_iterations:
            print(f"[CRITICAL] {replay_path.name}: Learning count {count}/{self.min_iterations} - CANNOT move/delete")
            return False
        return True

    def get_status_summary(self) -> Dict:
        """Get summary of all replay learning status"""
        total_replays = len(self.status_data["replays"])
        completed = sum(1 for entry in self.status_data["replays"].values()
                       if (isinstance(entry, dict) and entry.get("completed", False)) or
                          (isinstance(entry, int) and entry >= self.min_iterations))
        in_progress = total_replays - completed

        return {
            "total_replays": total_replays,
            "completed": completed,
            "in_progress": in_progress,
            "min_iterations": self.min_iterations
        }
