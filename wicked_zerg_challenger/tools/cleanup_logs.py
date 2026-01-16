#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup Log Files

Remove old and duplicate log files to reduce disk usage.
"""

import os
import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent.parent  # Go up to project root
LOGS_DIR = PROJECT_ROOT / "logs"

# Keep recent logs (days)
KEEP_RECENT_DAYS = 3

# Keep maximum number of log files
MAX_LOG_FILES = 50

# Log file patterns
LOG_PATTERNS = [
    r"log_\d{8}_\d{6}\.txt",  # log_YYYYMMDD_HHMMSS.txt
    r"training_log.*\.txt",
    r".*\.log",
]


def get_file_age_days(file_path: Path) -> float:
    """Get file age in days"""
    try:
        mtime = file_path.stat().st_mtime
        age_seconds = datetime.now().timestamp() - mtime
        return age_seconds / (24 * 3600)
    except Exception:
        return 0


def find_duplicate_logs() -> Dict[str, List[Path]]:
    """Find duplicate log files by content hash"""
    duplicates: Dict[str, List[Path]] = defaultdict(list)
    
    if not LOGS_DIR.exists():
        return duplicates
    
    for log_file in LOGS_DIR.glob("*.txt"):
        try:
            # Read first 1KB to check similarity
            content = log_file.read_bytes()[:1024]
            content_hash = hash(content)
            duplicates[content_hash].append(log_file)
        except Exception:
            continue
    
    # Only return groups with duplicates
    return {k: v for k, v in duplicates.items() if len(v) > 1}


def cleanup_old_logs(keep_days: int = KEEP_RECENT_DAYS) -> List[Path]:
    """Remove log files older than keep_days"""
    files_to_delete: List[Path] = []
    
    if not LOGS_DIR.exists():
        return files_to_delete
    
    for log_file in LOGS_DIR.glob("*.txt"):
        age_days = get_file_age_days(log_file)
        if age_days > keep_days:
            files_to_delete.append(log_file)
    
    return files_to_delete


def cleanup_excess_logs(max_files: int = MAX_LOG_FILES) -> List[Path]:
    """Keep only the most recent max_files log files"""
    files_to_delete: List[Path] = []
    
    if not LOGS_DIR.exists():
        return files_to_delete
    
    # Get all log files sorted by modification time (newest first)
    all_logs = sorted(
        LOGS_DIR.glob("*.txt"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    
    # Keep training_log.txt if it exists
    training_log = LOGS_DIR / "training_log.txt"
    if training_log in all_logs:
        all_logs.remove(training_log)
        all_logs.insert(0, training_log)
    
    # Delete files beyond max_files
    if len(all_logs) > max_files:
        files_to_delete = all_logs[max_files:]
    
    return files_to_delete


def cleanup_duplicate_logs() -> List[Path]:
    """Remove duplicate log files, keeping the newest"""
    files_to_delete: List[Path] = []
    
    duplicates = find_duplicate_logs()
    
    for duplicate_group in duplicates.values():
        # Sort by modification time (newest first)
        sorted_group = sorted(
            duplicate_group,
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        # Keep the newest, delete others
        files_to_delete.extend(sorted_group[1:])
    
    return files_to_delete


def get_log_file_size_mb(log_file: Path) -> float:
    """Get file size in MB"""
    try:
        return log_file.stat().st_size / (1024 * 1024)
    except Exception:
        return 0


def main():
    """Main function"""
    print("=" * 70)
    print("CLEANUP LOG FILES")
    print("=" * 70)
    print()
    
    if not LOGS_DIR.exists():
        print("Logs directory not found.")
        return
    
    # Count current log files
    current_logs = list(LOGS_DIR.glob("*.txt"))
    total_size_mb = sum(get_log_file_size_mb(f) for f in current_logs)
    
    print(f"Current log files: {len(current_logs)}")
    print(f"Total size: {total_size_mb:.2f} MB")
    print()
    
    # Find files to delete
    old_logs = cleanup_old_logs()
    excess_logs = cleanup_excess_logs()
    duplicate_logs = cleanup_duplicate_logs()
    
    # Combine and deduplicate
    all_files_to_delete = list(set(old_logs + excess_logs + duplicate_logs))
    
    if not all_files_to_delete:
        print("No log files to delete.")
        return
    
    print(f"Files to delete: {len(all_files_to_delete)}")
    print()
    print(f"  Old logs (> {KEEP_RECENT_DAYS} days): {len(old_logs)}")
    print(f"  Excess logs (beyond {MAX_LOG_FILES}): {len(excess_logs)}")
    print(f"  Duplicate logs: {len(duplicate_logs)}")
    print()
    
    # Calculate space to free
    space_to_free = sum(get_log_file_size_mb(f) for f in all_files_to_delete)
    print(f"Space to free: {space_to_free:.2f} MB")
    print()
    
    # Show first 20 files
    print("Files to be deleted (showing first 20):")
    for i, file_path in enumerate(sorted(all_files_to_delete, key=lambda f: f.stat().st_mtime)[:20], 1):
        age_days = get_file_age_days(file_path)
        size_mb = get_log_file_size_mb(file_path)
        print(f"  {i}. {file_path.name} ({age_days:.1f} days old, {size_mb:.2f} MB)")
    
    if len(all_files_to_delete) > 20:
        print(f"  ... and {len(all_files_to_delete) - 20} more files")
    
    print()
    print("Deleting files...")
    print()
    
    deleted_count = 0
    failed_count = 0
    freed_space = 0
    
    for file_path in sorted(all_files_to_delete, key=lambda f: f.stat().st_mtime):
        try:
            size_mb = get_log_file_size_mb(file_path)
            file_path.unlink()
            deleted_count += 1
            freed_space += size_mb
            if deleted_count <= 10:
                print(f"[DELETED] {file_path.name} ({size_mb:.2f} MB)")
        except Exception as e:
            failed_count += 1
            if failed_count <= 5:
                print(f"[ERROR] Failed to delete {file_path.name}: {e}")
    
    print()
    print("=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print(f"Deleted: {deleted_count} files")
    print(f"Freed space: {freed_space:.2f} MB")
    if failed_count > 0:
        print(f"Failed: {failed_count} files")
    
    # Show remaining logs
    remaining_logs = list(LOGS_DIR.glob("*.txt"))
    remaining_size = sum(get_log_file_size_mb(f) for f in remaining_logs)
    print()
    print(f"Remaining log files: {len(remaining_logs)}")
    print(f"Remaining size: {remaining_size:.2f} MB")
    print()


if __name__ == "__main__":
    main()
