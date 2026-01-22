#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Move completed replays to a completed folder.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

from replay_learning_tracker_sqlite import ReplayLearningTrackerSQLite


def move_completed_replays(
    replay_dir: Path,
    completed_dir: Path,
    min_iterations: int,
    dry_run: bool,
) -> Tuple[int, int]:
    replay_dir = Path(replay_dir)
    completed_dir = Path(completed_dir)
    completed_dir.mkdir(parents=True, exist_ok=True)

    tracker_db = replay_dir / ".learning_tracking.sqlite"
    tracker = ReplayLearningTrackerSQLite(tracker_db, min_iterations=min_iterations)

    all_replays = list(replay_dir.glob("*.SC2Replay"))
    completed = []

    for replay_path in all_replays:
        if completed_dir in replay_path.parents:
            continue
        if tracker.is_completed(replay_path):
            completed.append(replay_path)

    moved = 0
    failed = 0
    for replay_path in completed:
        dest_path = completed_dir / replay_path.name
        if dest_path.exists():
            if not dry_run:
                replay_path.unlink(missing_ok=True)
            moved += 1
            continue

        if dry_run:
            print(f"[WOULD MOVE] {replay_path.name}")
            moved += 1
            continue

        try:
            replay_path.replace(dest_path)
            moved += 1
        except Exception as exc:
            print(f"[ERROR] Failed to move {replay_path.name}: {exc}")
            failed += 1

    return moved, failed


def force_move_all(
    replay_dir: Path, completed_dir: Path, dry_run: bool
) -> Tuple[int, int]:
    replay_dir = Path(replay_dir)
    completed_dir = Path(completed_dir)
    completed_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    failed = 0
    for replay_path in replay_dir.glob("*.SC2Replay"):
        if completed_dir in replay_path.parents:
            continue
        dest_path = completed_dir / replay_path.name
        if dest_path.exists():
            continue
        if dry_run:
            print(f"[WOULD MOVE] {replay_path.name}")
            moved += 1
            continue
        try:
            replay_path.replace(dest_path)
            moved += 1
        except Exception as exc:
            print(f"[ERROR] Failed to move {replay_path.name}: {exc}")
            failed += 1
    return moved, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Move completed replays")
    parser.add_argument(
        "--source", default="D:/replays/replays", help="Source replay directory"
    )
    parser.add_argument("--completed", default=None, help="Completed directory")
    parser.add_argument(
        "--min-iterations", type=int, default=5, help="Minimum iterations per replay"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show actions without moving"
    )
    parser.add_argument(
        "--force", action="store_true", help="Move all replays regardless of status"
    )
    args = parser.parse_args()

    replay_dir = Path(args.source)
    completed_dir = Path(args.completed) if args.completed else replay_dir / "completed"

    if not replay_dir.exists():
        print(f"[ERROR] Source directory does not exist: {replay_dir}")
        return

    if args.force:
        print("[WARNING] Force mode: moving all replays")
        moved, failed = force_move_all(replay_dir, completed_dir, args.dry_run)
    else:
        moved, failed = move_completed_replays(
            replay_dir,
            completed_dir,
            min_iterations=args.min_iterations,
            dry_run=args.dry_run,
        )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Moved: {moved}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
