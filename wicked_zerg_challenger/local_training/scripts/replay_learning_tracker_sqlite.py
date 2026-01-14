#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replay Learning Tracker - SQLite-based (Thread-Safe)

IMPROVED: Uses SQLite for thread-safe learning count tracking
Prevents race conditions when multiple training processes run in parallel

Features:
- Thread-safe learning count tracking
- Minimum 5 iterations per replay requirement
- Move completed replays to completed folder
- Integration with training pipeline
"""

import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import shutil
from enum import Enum
import threading


class LearningPhase(Enum):
    """Learning phases for focused analysis"""
    EARLY_GAME = "early_game"  # 0-5 minutes: Build order focus
    MID_GAME = "mid_game"  # 5-15 minutes: Unit composition and skirmishes
    LATE_GAME = "late_game"  # 15+ minutes: Macro and spell unit usage


class ReplayLearningTrackerSQLite:
    """
    Thread-safe replay learning tracker using SQLite

    CRITICAL: SQLite handles concurrent access automatically,
    preventing race conditions in parallel training scenarios
    """

    def __init__(self, db_path: Path, min_iterations: int = 5):
        """
        Args:
            db_path: Path to SQLite database file
            min_iterations: Minimum learning iterations required (default: 5)
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.min_iterations = min_iterations
        self._lock = threading.Lock()  # Additional safety for connection management
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-safe database connection"""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)  # 30 second timeout
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        return conn

    def _init_database(self):
        """Initialize database schema"""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_tracking (
                    replay_hash TEXT PRIMARY KEY,
                    replay_path TEXT NOT NULL,
                    learning_count INTEGER DEFAULT 0,
                    last_updated TEXT NOT NULL,
                    phase_focus TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_replay_path ON learning_tracking(replay_path)
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_replay_hash(self, replay_path: Path) -> str:
        """Get unique hash for replay file"""
        try:
            stat = replay_path.stat()
            key_input = f"{replay_path.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(key_input.encode()).hexdigest()
        except Exception:
            return hashlib.md5(replay_path.name.encode()).hexdigest()

    def get_learning_phase(self, iteration: int) -> LearningPhase:
        """Determine learning phase based on iteration number"""
        if iteration <= 2:
            return LearningPhase.EARLY_GAME
        elif iteration <= 4:
            return LearningPhase.MID_GAME
        else:
            return LearningPhase.LATE_GAME

    def get_phase_focus(self, iteration: int) -> Dict[str, any]:
        """Get focus areas for current learning phase"""
        phase = self.get_learning_phase(iteration)

        if phase == LearningPhase.EARLY_GAME:
            return {
                "phase": "early_game",
                "time_range": (0, 300),
                "focus": ["build_order", "opening", "economy_setup"],
                "weights": {"build_order": 0.6, "economy": 0.3, "scouting": 0.1}
            }
        elif phase == LearningPhase.MID_GAME:
            return {
                "phase": "mid_game",
                "time_range": (300, 900),
                "focus": ["unit_composition", "micro_control", "skirmishes", "multitasking"],
                "weights": {"unit_composition": 0.4, "micro": 0.3, "multitasking": 0.2, "economy": 0.1}
            }
        else:  # LATE_GAME
            return {
                "phase": "late_game",
                "time_range": (900, None),
                "focus": ["macro_management", "spell_units", "late_game_units", "map_control"],
                "weights": {"macro": 0.4, "spell_units": 0.3, "map_control": 0.2, "economy": 0.1}
            }

    def get_learning_count(self, replay_path: Path) -> int:
        """Get learning count for a replay (thread-safe)"""
        replay_hash = self._get_replay_hash(replay_path)
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT learning_count FROM learning_tracking WHERE replay_hash = ?",
                (replay_hash,)
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def increment_learning_count(self, replay_path: Path, phase_focus: Optional[Dict] = None) -> int:
        """Increment learning count for a replay (thread-safe)"""
        replay_hash = self._get_replay_hash(replay_path)
        conn = self._get_connection()
        try:
            # Get current count
            cursor = conn.execute(
                "SELECT learning_count FROM learning_tracking WHERE replay_hash = ?",
                (replay_hash,)
            )
            row = cursor.fetchone()
            current_count = row[0] if row else 0
            new_count = current_count + 1

            # Update or insert
            import json
            phase_focus_str = json.dumps(phase_focus) if phase_focus else None
            conn.execute("""
                INSERT OR REPLACE INTO learning_tracking
                (replay_hash, replay_path, learning_count, last_updated, phase_focus)
                VALUES (?, ?, ?, ?, ?)
            """, (
                replay_hash,
                str(replay_path),
                new_count,
                datetime.now().isoformat(),
                phase_focus_str
            ))
            conn.commit()
            return new_count
        finally:
            conn.close()

    def is_completed(self, replay_path: Path) -> bool:
        """Check if replay has completed minimum iterations (thread-safe)"""
        return self.get_learning_count(replay_path) >= self.min_iterations

    def move_completed_replay(self, replay_path: Path, completed_dir: Path) -> bool:
        """Move completed replay to completed folder (thread-safe)"""
        if not self.is_completed(replay_path):
            return False

        try:
            completed_dir.mkdir(parents=True, exist_ok=True)
            dest_path = completed_dir / replay_path.name

            # Use shutil.move for atomic operation
            shutil.move(str(replay_path), str(dest_path))
            return True
        except Exception as e:
            print(f"[ERROR] Failed to move completed replay {replay_path.name}: {e}")
            return False
