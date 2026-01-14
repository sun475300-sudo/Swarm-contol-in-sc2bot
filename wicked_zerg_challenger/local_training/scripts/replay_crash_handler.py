#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replay Crash Handler - Handle abnormal termination during learning

This module tracks learning progress and marks replays that repeatedly crash
during learning as "Bad Replay" to prevent infinite retry loops.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import os


class ReplayCrashHandler:
    """
    Handle abnormal termination during replay learning

    Tracks:
    1. Learning in progress (prevents duplicate processing)
    2. Crash count (marks bad replays after repeated crashes)
    3. Recovery from incomplete learning sessions
    """

    def __init__(self, crash_log_file: Path, max_crashes: int = 3):
        """
        Args:
            crash_log_file: Path to crash tracking JSON file
            max_crashes: Maximum crashes before marking as bad replay (default: 3)
        """
        self.crash_log_file = crash_log_file
        self.crash_log_file.parent.mkdir(parents=True, exist_ok=True)
        self.max_crashes = max_crashes
        self.crash_data = self._load_crash_log()

    def _load_crash_log(self) -> Dict:
        """Load crash tracking data from JSON file"""
        if not self.crash_log_file.exists():
            return {
                "_format_version": "1.0",
                "_description": "Replay crash tracking - Prevents infinite retry loops",
                "_last_updated": datetime.now().isoformat(),
                "in_progress": {},  # replay_key -> start_time
                "crash_count": {},  # replay_key -> count
                "bad_replays": []  # List of replay keys marked as bad
            }

        try:
            content = self.crash_log_file.read_text(encoding="utf-8")
            if not content.strip():
                return self._get_default_crash_log()

            data = json.loads(content)
            # Ensure required fields exist
            if "in_progress" not in data:
                data["in_progress"] = {}
            if "crash_count" not in data:
                data["crash_count"] = {}
            if "bad_replays" not in data:
                data["bad_replays"] = []
            return data
        except Exception as e:
            print(f"[WARNING] Failed to load crash log: {e}")
            return self._get_default_crash_log()

    def _get_default_crash_log(self) -> Dict:
        """Get default crash log structure"""
        return {
            "_format_version": "1.0",
            "_description": "Replay crash tracking - Prevents infinite retry loops",
            "_last_updated": datetime.now().isoformat(),
            "in_progress": {},
            "crash_count": {},
            "bad_replays": []
        }

    def _save_crash_log(self):
        """Save crash tracking data to JSON file (atomic write)"""
        max_retries = 3
        retry_delay = 0.1  # 100ms

        for attempt in range(max_retries):
            try:
                self.crash_data["_last_updated"] = datetime.now().isoformat()

                # CRITICAL: Atomic write to prevent corruption
                import time
                import random
                # Use unique temp filename to avoid conflicts with multiple instances
                unique_id = int(time.time() * 1000) + random.randint(0, 999)
                temp_file = self.crash_log_file.with_suffix(f'.tmp.{unique_id}')

                # FIX: Remove existing temp files if they exist (may be locked by another process)
                # Clean up old temp files (older than 1 hour)
                try:
                    temp_dir = self.crash_log_file.parent
                    for old_temp in temp_dir.glob('crash_log.tmp.*'):
                        try:
                            # Check if file is old (more than 1 hour)
                            file_age = time.time() - old_temp.stat().st_mtime
                            if file_age > 3600:  # 1 hour
                                old_temp.unlink()
                        except (PermissionError, OSError):
                            pass  # Skip if can't delete
                except Exception:
                    pass  # Ignore cleanup errors

                # Write to temp file with retry logic
                try:
                    temp_file.write_text(
                        json.dumps(self.crash_data, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        continue  # Retry with new unique filename
                    else:
                        raise

                # Atomic move
                try:
                    os.replace(str(temp_file), str(self.crash_log_file))
                    return  # Success!
                except PermissionError as e:
                    # If replace fails, try direct write (non-atomic but better than failing)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        print(f"[WARNING] Atomic replace failed, trying direct write: {e}")
                        try:
                            self.crash_log_file.write_text(
                                json.dumps(self.crash_data, indent=2, ensure_ascii=False),
                                encoding="utf-8"
                            )
                            # Clean up temp file if it exists
                            if temp_file.exists():
                                try:
                                    temp_file.unlink()
                                except:
                                    pass
                            return  # Success with direct write
                        except PermissionError:
                            raise
            except PermissionError as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    # CRITICAL: Don't raise on permission error - allow learning to continue
                    # This prevents a single file lock from stopping the entire learning process
                    print(f"[WARNING] Permission denied saving crash log after {max_retries} attempts (continuing anyway): {e}")
                    print(f"[INFO] Crash log will be saved on next successful write")
                    return  # Don't raise - allow learning to continue
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"[ERROR] Failed to save crash log after {max_retries} attempts: {e}")
                    # Don't raise - allow learning to continue even if crash log save fails
                    return

    def _get_replay_key(self, replay_path: Path) -> str:
        """Get unique key for replay file"""
        try:
            stat = replay_path.stat()
            key_input = f"{replay_path.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(key_input.encode()).hexdigest()
        except Exception:
            return hashlib.md5(replay_path.name.encode()).hexdigest()

    def mark_learning_start(self, replay_path: Path):
        """
        Mark replay as learning in progress

        CRITICAL: Call this at the START of learning to prevent duplicate processing
        """
        replay_key = self._get_replay_key(replay_path)
        self.crash_data["in_progress"][replay_key] = {
            "filename": replay_path.name,
            "start_time": datetime.now().isoformat(),
            "file_path": str(replay_path)
        }
        self._save_crash_log()

    def mark_learning_complete(self, replay_path: Path):
        """
        Mark replay as learning completed successfully

        CRITICAL: Call this at the END of successful learning to clear in_progress flag
        """
        replay_key = self._get_replay_key(replay_path)
        if replay_key in self.crash_data["in_progress"]:
            del self.crash_data["in_progress"][replay_key]
        # Reset crash count on successful completion
        if replay_key in self.crash_data["crash_count"]:
            del self.crash_data["crash_count"][replay_key]
        self._save_crash_log()

    def mark_crash(self, replay_path: Path):
        """
        Mark replay as crashed during learning

        After max_crashes, the replay will be marked as "bad" and excluded from learning
        """
        replay_key = self._get_replay_key(replay_path)

        # Increment crash count
        current_crashes = self.crash_data["crash_count"].get(replay_key, 0)
        new_crashes = current_crashes + 1

        self.crash_data["crash_count"][replay_key] = new_crashes

        # Clear in_progress flag
        if replay_key in self.crash_data["in_progress"]:
            del self.crash_data["in_progress"][replay_key]

        # Mark as bad replay if exceeds max crashes
        if new_crashes >= self.max_crashes:
            if replay_key not in self.crash_data["bad_replays"]:
                self.crash_data["bad_replays"].append(replay_key)
                print(f"[BAD REPLAY] {replay_path.name} - Marked as bad after {new_crashes} crashes")

        self._save_crash_log()
        return new_crashes

    def is_in_progress(self, replay_path: Path) -> bool:
        """
        Check if replay is currently being learned

        CRITICAL: Automatically ignores stale sessions (older than 1 hour)
        This prevents "Already being learned" false positives from crashed processes
        """
        replay_key = self._get_replay_key(replay_path)

        if replay_key not in self.crash_data["in_progress"]:
            return False

        # CRITICAL: Check if session is stale (older than 1 hour)
        # If stale, automatically clear it and return False
        progress_info = self.crash_data["in_progress"].get(replay_key, {})
        start_time_str = progress_info.get("start_time")

        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                age_seconds = (datetime.now() - start_time).total_seconds()

                # If session is older than 1 hour, it's stale - clear it
                if age_seconds > 3600:  # 1 hour
                    print(f"[STALE AUTO-CLEAR] {replay_path.name} - Clearing stale session (age: {int(age_seconds)}s)")
                    del self.crash_data["in_progress"][replay_key]
                    # Don't save here to avoid blocking - will be saved on next operation
                    return False
            except Exception:
                # If we can't parse the time, consider it stale
                print(f"[STALE AUTO-CLEAR] {replay_path.name} - Clearing invalid session (unparseable time)")
                del self.crash_data["in_progress"][replay_key]
                return False
        else:
            # No start_time means it's invalid - clear it
            print(f"[STALE AUTO-CLEAR] {replay_path.name} - Clearing invalid session (no start_time)")
            del self.crash_data["in_progress"][replay_key]
            return False

        return True

    def is_bad_replay(self, replay_path: Path) -> bool:
        """Check if replay is marked as bad (repeated crashes)"""
        replay_key = self._get_replay_key(replay_path)
        return replay_key in self.crash_data["bad_replays"]

    def get_crash_count(self, replay_path: Path) -> int:
        """Get crash count for a replay"""
        replay_key = self._get_replay_key(replay_path)
        return self.crash_data["crash_count"].get(replay_key, 0)

    def recover_stale_sessions(self, max_age_seconds: int = 1800):
        """
        Recover stale learning sessions (mark as crashed if too old)

        Args:
            max_age_seconds: Maximum age in seconds before marking as stale (default: 30 minutes)

        CRITICAL: This method clears stale sessions to prevent "Already being learned" false positives.
        Sessions older than max_age_seconds are automatically cleared.
        """
        from datetime import datetime, timedelta
        current_time = datetime.now()
        stale_keys = []

        for replay_key, progress_info in self.crash_data["in_progress"].items():
            start_time_str = progress_info.get("start_time")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                    age_seconds = (current_time - start_time).total_seconds()
                    if age_seconds > max_age_seconds:
                        stale_keys.append(replay_key)
                except Exception:
                    # If we can't parse the time, consider it stale
                    stale_keys.append(replay_key)
            else:
                # No start_time means it's invalid - mark as stale
                stale_keys.append(replay_key)

        # Mark stale sessions as crashed
        if stale_keys:
            print(f"[STALE SESSION] Recovering {len(stale_keys)} stale sessions (age > {max_age_seconds}s)...")
            for replay_key in stale_keys:
                progress_info = self.crash_data["in_progress"].get(replay_key, {})
                filename = progress_info.get("filename", "unknown")
                print(f"[STALE SESSION] {filename} - Cleared (stale session)")
                if replay_key in self.crash_data["in_progress"]:
                    del self.crash_data["in_progress"][replay_key]
                # Don't increment crash count for stale sessions - they're just old, not crashed
                # Only increment if it was actually a crash

            # CRITICAL: Save changes even if _save_crash_log() might fail
            # This ensures stale sessions are cleared from memory
            try:
                self._save_crash_log()
            except Exception as e:
                print(f"[WARNING] Failed to save crash log after stale session recovery: {e}")
                # Continue anyway - stale sessions are already cleared from memory
