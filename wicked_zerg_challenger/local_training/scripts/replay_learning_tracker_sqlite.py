#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replay Learning Tracker - SQLite-based (thread-safe).

Tracks how many times a replay has been processed and whether it is complete.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional


class LearningPhase(Enum):
    EARLY_GAME = "early_game"
    MID_GAME = "mid_game"
    LATE_GAME = "late_game"


@dataclass
class PhaseFocus:
    phase: str
    time_range: tuple
    focus: list
    weights: dict


class ReplayLearningTrackerSQLite:
    """Thread-safe replay learning tracker using SQLite."""

    def __init__(self, db_path: Path, min_iterations: int = 5):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.min_iterations = min_iterations
        self._lock = threading.Lock()
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_database(self) -> None:
        with self._get_connection() as conn:
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
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_replay_path ON learning_tracking(replay_path)"
            )

    def _get_replay_hash(self, replay_path: Path) -> str:
        try:
            stat = replay_path.stat()
            key_input = f"{replay_path.name}_{stat.st_size}_{stat.st_mtime}"
        except OSError:
            key_input = replay_path.name
        return hashlib.md5(key_input.encode("utf-8")).hexdigest()

    def get_learning_phase(self, iteration: int) -> LearningPhase:
        if iteration <= 2:
            return LearningPhase.EARLY_GAME
        if iteration <= 4:
            return LearningPhase.MID_GAME
        return LearningPhase.LATE_GAME

    def get_phase_focus(self, iteration: int) -> Dict:
        phase = self.get_learning_phase(iteration)
        if phase == LearningPhase.EARLY_GAME:
            return {
                "phase": "early_game",
                "time_range": (0, 300),
                "focus": ["build_order", "opening", "economy_setup"],
                "weights": {"build_order": 0.6, "economy": 0.3, "scouting": 0.1},
            }
        if phase == LearningPhase.MID_GAME:
            return {
                "phase": "mid_game",
                "time_range": (300, 900),
                "focus": [
                    "unit_composition",
                    "micro_control",
                    "skirmishes",
                    "multitasking",
                ],
                "weights": {
                    "unit_composition": 0.4,
                    "micro": 0.3,
                    "multitasking": 0.2,
                    "economy": 0.1,
                },
            }
        return {
            "phase": "late_game",
            "time_range": (900, None),
            "focus": [
                "macro_management",
                "spell_units",
                "late_game_units",
                "map_control",
            ],
            "weights": {
                "macro": 0.4,
                "spell_units": 0.3,
                "map_control": 0.2,
                "economy": 0.1,
            },
        }

    def get_learning_count(self, replay_path: Path) -> int:
        replay_hash = self._get_replay_hash(replay_path)
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT learning_count FROM learning_tracking WHERE replay_hash = ?",
                (replay_hash,),
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def increment_learning_count(
        self,
        replay_path: Path,
        phase_focus: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> int:
        replay_hash = self._get_replay_hash(replay_path)
        phase_focus_str = json.dumps(phase_focus) if phase_focus else None
        metadata_str = json.dumps(metadata) if metadata else None

        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT learning_count FROM learning_tracking WHERE replay_hash = ?",
                (replay_hash,),
            )
            row = cursor.fetchone()
            current_count = int(row[0]) if row else 0
            new_count = current_count + 1

            conn.execute(
                """
                INSERT OR REPLACE INTO learning_tracking
                (replay_hash, replay_path, learning_count, last_updated, phase_focus, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    replay_hash,
                    str(replay_path),
                    new_count,
                    datetime.now().isoformat(),
                    phase_focus_str,
                    metadata_str,
                ),
            )
            conn.commit()
            return new_count

    def is_completed(self, replay_path: Path) -> bool:
        return self.get_learning_count(replay_path) >= self.min_iterations

    def move_completed_replay(self, replay_path: Path, completed_dir: Path) -> bool:
        if not self.is_completed(replay_path):
            return False

        completed_dir.mkdir(parents=True, exist_ok=True)
        dest_path = completed_dir / replay_path.name
        try:
            replay_path.replace(dest_path)
            return True
        except OSError:
            try:
                import shutil

                shutil.move(str(replay_path), str(dest_path))
                return True
            except Exception as exc:
                print(
                    f"[ERROR] Failed to move completed replay {replay_path.name}: {exc}"
                )
                return False
