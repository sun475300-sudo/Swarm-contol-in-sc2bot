#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import shutil
import os
from datetime import datetime
from pathlib import Path
import argparse

# IMPROVED: Use sys.executable instead of hardcoded path
PYTHON_EXECUTABLE = sys.executable

# IMPROVED: Default to D:\replays as specified in requirements
def get_replay_dir() -> Path:
    """Get replay directory - default to D:\replays"""
    replay_dir_env = os.environ.get("REPLAY_DIR")
    if replay_dir_env and Path(replay_dir_env).exists():
        return Path(replay_dir_env)

    default_path = Path("D:/replays")
    if default_path.exists() or sys.platform == "win32":
        return default_path

    # Fallback to common locations
    possible_paths = [
        Path(__file__).parent / "replays",
        Path("replays"),
    ]
    for path in possible_paths:
        if path.exists():
            return path

    return default_path

LOCAL_REPLAY_DIR = get_replay_dir()

def main():
    parser = argparse.ArgumentParser(description="Integrated training pipeline")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    # IMPROVED: Use environment variable or flexible path detection
    # Priority 1: D:\replays\replays (all Zerg pro gamer replays)
    default_source = os.environ.get("REPLAY_SOURCE_DIR")
    if not default_source or not os.path.exists(default_source):
        # Try common locations (priority: D:\replays\replays)
        possible_paths = [
            Path("D:/replays/replays"),  # All Zerg pro gamer replays (highest priority)
            Path(__file__).parent.parent / "replays_archive",
            Path.home() / "replays" / "replays",
            Path("replays_archive"),
        ]
        for path in possible_paths:
            if path.exists():
                default_source = str(path)
                break
        else:
            default_source = "D:/replays/replays"  # Default to Zerg pro gamer replays directory

    parser.add_argument("--source-replays", default=default_source, help="Source replays folder")
    parser.add_argument("--cleanup", action="store_true", help="Move processed files")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, no training")
    args = parser.parse_args()

    print(f"\n{'='*80}")
    print("WICKED ZERG TRAINING PIPELINE STARTED")
    print(f"{'='*80}")

    # ==========================================
    # Step 1: Prepare Replays
    # ==========================================
    print(f"\n[STEP 1] PREPARE REPLAYS")

    LOCAL_REPLAY_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Source folder check
    source_folder = Path(args.source_replays).resolve()
    if source_folder.exists():
        source_files = list(source_folder.glob("*.SC2Replay"))
        print(f"   [SOURCE] Found {len(source_files)} replays in source. Copying...")
        count = 0
        for src in source_files:
            dst = LOCAL_REPLAY_DIR / src.name
            if not dst.exists():
                try:
                    shutil.copy2(src, dst)
                    count += 1
                except (OSError, PermissionError, FileNotFoundError) as e:
                    # Ignore file copy errors (permission denied, file not found, etc.)
                    pass
        print(f"   [OK] Copied {count} new replays to workspace")

    # 2. Workspace check with validation
    current_replays = list(LOCAL_REPLAY_DIR.glob("*.SC2Replay"))
    print(f"   [TARGET] Total replays found: {len(current_replays)}")

    # IMPROVED: Validate replays using sc2reader metadata (prevents data integrity issues)
    validated_replays = []
    if current_replays:
        print(f"   [VALIDATE] Validating replay files...")
        try:
            import sc2reader
            SC2READER_AVAILABLE = True
        except ImportError:
            SC2READER_AVAILABLE = False
            print(f"   [WARNING] sc2reader not installed. Skipping metadata validation.")
            print(f"   [INFO] Install with: pip install sc2reader")

        if SC2READER_AVAILABLE:
            valid_count = 0
            invalid_count = 0
            LOTV_RELEASE_DATE = datetime(2015, 11, 10)
            MIN_GAME_TIME_SECONDS = 300  # 5 minutes

            for replay_path in current_replays:
                try:
                    replay = sc2reader.load_replay(str(replay_path), load_map=True)

                    # 1. Basic validation: check if replay has players
                    if not hasattr(replay, 'players') or len(replay.players) < 2:
                        invalid_count += 1
                        print(f"   [SKIP] {replay_path.name}: Invalid replay structure")
                        continue

                    # 2. Check if at least one player is Zerg (ZvT, ZvP, ZvZ)
                    has_zerg = any(
                        hasattr(p, 'play_race') and str(p.play_race).lower() == "zerg"
                        for p in replay.players
                    )
                    if not has_zerg:
                        invalid_count += 1
                        print(f"   [SKIP] {replay_path.name}: No Zerg player found")
                        continue

                    # 3. Check game time (minimum 5 minutes)
                    if hasattr(replay, 'length'):
                        game_seconds = replay.length.seconds
                        if game_seconds < MIN_GAME_TIME_SECONDS:
                            invalid_count += 1
                            print(f"   [SKIP] {replay_path.name}: Game too short ({game_seconds}s < {MIN_GAME_TIME_SECONDS}s)")
                            continue

                    # 4. Check LotV patch (replay date should be after LotV release)
                    if hasattr(replay, 'date'):
                        replay_date = replay.date
                        if replay_date < LOTV_RELEASE_DATE:
                            invalid_count += 1
                            print(f"   [SKIP] {replay_path.name}: Pre-LotV replay ({replay_date.date()})")
                            continue

                    validated_replays.append(replay_path)
                    valid_count += 1
                except Exception as e:
                    invalid_count += 1
                    print(f"   [SKIP] {replay_path.name}: Validation error - {e}")

            print(f"   [VALIDATE] Valid: {valid_count}, Invalid: {invalid_count}")
            current_replays = validated_replays
        else:
            # If sc2reader not available, use all replays (fallback)
            validated_replays = current_replays
            print(f"   [WARNING] Using all replays without validation (sc2reader not available)")

    print(f"   [TARGET] Total validated replays ready for training: {len(current_replays)}")

    # IMPROVED: Enhanced error handling with fallback mechanism
    if len(current_replays) == 0:
        print(f"   [ERROR] No valid replays found! Please check {source_folder}")
        print(f"   [INFO] Ensure replays contain Zerg players and are valid SC2Replay files")

        # IMPROVED: Attempt fallback - try to scan parent directory or common locations
        print(f"   [FALLBACK] Attempting to find replays in alternative locations...")
        fallback_paths = [
            Path("replays_archive"),
            Path("../replays_archive"),
            Path.home() / "replays",
        ]

        found_fallback = False
        for fallback_path in fallback_paths:
            if fallback_path.exists():
                fallback_replays = list(fallback_path.glob("*.SC2Replay"))
                if fallback_replays:
                    print(f"   [FALLBACK] Found {len(fallback_replays)} replays in {fallback_path}")
                    print(f"   [INFO] Consider using --source-replays {fallback_path}")
                    found_fallback = True
                    break

        if not found_fallback:
            print(f"   [ERROR] No replays found in fallback locations either")
            print(f"   [INFO] Please ensure replays are available before running training")
            sys.exit(1)
        else:
            # Don't exit, but warn user
            print(f"   [WARNING] Continuing with validation-only mode. Fix replay path before training.")
            if not args.validate_only:
                print(f"   [INFO] Run with --validate-only to check replay paths without training")

    # ==========================================
    # Step 2: Run Training (Corrected Path)
    # ==========================================
    if not args.validate_only:
        print(f"\n{'='*80}")
        print("[STEP 2] RUN TRAINING (SUPERVISED)")
        print(f"{'='*80}")

        # IMPROVED: Check if hybrid_learning.py exists before executing
        hybrid_learning_script = Path("hybrid_learning.py")
        if not hybrid_learning_script.exists():
            # Try to find it in scripts directory or parent directory
            possible_locations = [
                Path(__file__).parent / "hybrid_learning.py",
                Path(__file__).parent.parent / "hybrid_learning.py",
                Path("scripts") / "hybrid_learning.py",
            ]
            for location in possible_locations:
                if location.exists():
                    hybrid_learning_script = location
                    break
            else:
                print(f"   [ERROR] hybrid_learning.py not found!")
                print(f"   [INFO] Please ensure hybrid_learning.py exists in the project directory")
                sys.exit(1)

        cmd = [
            PYTHON_EXECUTABLE,
            str(hybrid_learning_script),
            "--epochs", str(args.epochs)
        ]

        print(f"   [EXEC] Executing: {' '.join(cmd)}")

        # IMPROVED: Use script's directory as working directory for better path resolution
        script_dir = hybrid_learning_script.parent if hybrid_learning_script.parent != Path(".") else Path.cwd()
        result = subprocess.run(cmd, cwd=str(script_dir))

        if result.returncode != 0:
            print(f"\n   [ERROR] TRAINING FAILED! (Exit Code: {result.returncode})")
            sys.exit(1)
        else:
            print(f"\n   [OK] TRAINING COMPLETED SUCCESSFULLY")

    # ==========================================
    # Step 3: Learning Tracking and Cleanup
    # ==========================================
    if args.cleanup:
        print(f"\n{'='*80}")
        print("[STEP 3] LEARNING TRACKING AND CLEANUP")
        print(f"{'='*80}")

        # IMPROVED: Use learning tracker to manage completed replays
        try:
            from scripts.replay_learning_manager import ReplayLearningTracker

            # CRITICAL: Completed replays go to D:\replays\replays\completed
            completed_dir = Path("D:/replays/replays/completed")
            completed_dir.mkdir(parents=True, exist_ok=True)
            tracking_file = LOCAL_REPLAY_DIR / ".learning_tracking.json"
            tracker = ReplayLearningTracker(tracking_file, min_iterations=5)

            # Mark each processed replay as trained once
            moved_count = 0
            for rp in current_replays:
                new_count = tracker.increment_learning_count(rp)
                print(f"   [LEARNING] {rp.name}: {new_count}/5 iterations")

                # Move to completed folder if 5+ iterations
                if tracker.is_completed(rp):
                    if tracker.move_completed_replay(rp, completed_dir):
                        moved_count += 1
                        print(f"   [COMPLETED] Moved {rp.name} to completed folder")

            print(f"\n   [SUMMARY] Moved {moved_count} completed replays to {completed_dir}")

        except ImportError:
            # Fallback: Use simple processed folder
            # CRITICAL: Completed replays go to D:\replays\replays\completed
            processed_dir = Path("D:/replays/replays/completed")
            processed_dir.mkdir(parents=True, exist_ok=True)
            print(f"   [CLEANUP] Moving processed replays to {processed_dir}...")
            for rp in current_replays:
                try:
                    target = processed_dir / rp.name
                    if not target.exists():
                        shutil.move(str(rp), str(target))
                except (OSError, PermissionError, FileNotFoundError) as e:
                    # Ignore file move errors (permission denied, file not found, etc.)
                    pass

    print(f"\n{'='*80}")
    print("PIPELINE COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
