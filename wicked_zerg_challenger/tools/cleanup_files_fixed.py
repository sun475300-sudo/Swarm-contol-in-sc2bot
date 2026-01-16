# -*- coding: utf-8 -*-
"""
Unnecessary files cleanup tool

Removes unnecessary files for training/execution.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent.parent


def find_backup_files() -> List[Path]:
    """Find backup files (.bak)"""
    backup_files = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'models', 'logs', 'stats'
        }]

        for file in files:
            if file.endswith('.bak'):
                backup_files.append(Path(root) / file)

    return backup_files


def find_cache_files() -> List[Path]:
    """Find cache files (.pyc, .pyo)"""
    cache_files = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        if '__pycache__' in dirs:
            cache_dir = Path(root) / '__pycache__'
            for file in cache_dir.iterdir():
                if file.is_file():
                    cache_files.append(file)
            dirs.remove('__pycache__')

        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                cache_files.append(Path(root) / file)

    return cache_files


def find_empty_directories() -> List[Path]:
    """Find empty directories"""
    empty_dirs = []

    for root, dirs, files in os.walk(PROJECT_ROOT, topdown=False):
        root_path = Path(root)

        # Skip excluded directories
        if any(excluded in str(root_path) for excluded in [
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'models', 'logs', 'stats', '.idea', '.vscode'
        ]):
            continue

        # Check if directory is empty
        try:
            if not any(root_path.iterdir()):
                empty_dirs.append(root_path)
        except (OSError, PermissionError):
            continue

    return empty_dirs


def delete_files(file_paths: List[Path], dry_run: bool = True) -> int:
    """Delete files"""
    deleted_count = 0

    for file_path in file_paths:
        try:
            if file_path.exists():
                if not dry_run:
                    file_path.unlink()
                deleted_count += 1
                status = "[DRY RUN] " if dry_run else ""
                print(f"{status}Deleted: {file_path.relative_to(PROJECT_ROOT)}")
        except Exception as e:
            print(f"[ERROR] Failed to delete {file_path.relative_to(PROJECT_ROOT)}: {e}")

    return deleted_count


def delete_directories(dir_paths: List[Path], dry_run: bool = True) -> int:
    """Delete directories"""
    deleted_count = 0

    for dir_path in dir_paths:
        try:
            if dir_path.exists() and dir_path.is_dir():
                if not dry_run:
                    shutil.rmtree(dir_path)
                deleted_count += 1
                status = "[DRY RUN] " if dry_run else ""
                print(f"{status}Deleted: {dir_path.relative_to(PROJECT_ROOT)}")
        except Exception as e:
            print(f"[ERROR] Failed to delete {dir_path.relative_to(PROJECT_ROOT)}: {e}")

    return deleted_count


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Unnecessary files cleanup tool")
    parser.add_argument("--execute", action="store_true", help="Actually delete (default: dry-run)")
    parser.add_argument("--backup-only", action="store_true", help="Delete backup files only")
    parser.add_argument("--cache-only", action="store_true", help="Delete cache files only")
    parser.add_argument("--empty-dirs", action="store_true", help="Delete empty directories")

    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 70)
    print("Unnecessary Files Cleanup Tool")
    print("=" * 70)
    print()

    if dry_run:
        print("[DRY RUN] Files will not be deleted. Use --execute to actually delete.")
        print()

    total_deleted = 0

    # Backup files
    if not args.cache_only:
        print("Finding backup files (.bak)...")
        backup_files = find_backup_files()
        print(f"  - Found: {len(backup_files)} files")

        if backup_files:
            print()
            deleted = delete_files(backup_files, dry_run=dry_run)
            total_deleted += deleted
            print()

    # Cache files
    if not args.backup_only:
        print("Finding cache files (.pyc, .pyo, __pycache__)...")
        cache_files = find_cache_files()
        print(f"  - Found: {len(cache_files)} files")

        if cache_files:
            print()
            deleted = delete_files(cache_files, dry_run=dry_run)
            total_deleted += deleted
            print()

        # __pycache__ directories
        pycache_dirs = []
        for root, dirs, files in os.walk(PROJECT_ROOT):
            if '__pycache__' in dirs:
                pycache_dirs.append(Path(root) / '__pycache__')

        if pycache_dirs:
            print(f"__pycache__ directories: {len(pycache_dirs)}")
            deleted = delete_directories(pycache_dirs, dry_run=dry_run)
            total_deleted += deleted
            print()

    # Empty directories
    if args.empty_dirs:
        print("Finding empty directories...")
        empty_dirs = find_empty_directories()
        print(f"  - Found: {len(empty_dirs)} directories")

        if empty_dirs:
            print()
            deleted = delete_directories(empty_dirs, dry_run=dry_run)
            total_deleted += deleted
            print()

    print("=" * 70)
    print(f"Total {total_deleted} files/directories {'deleted' if not dry_run else 'to be deleted'}")
    print("=" * 70)

    if dry_run:
        print()
        print("[TIP] To actually delete, run:")
        print("  python tools/cleanup_files_fixed.py --execute")


if __name__ == "__main__":
    main()
