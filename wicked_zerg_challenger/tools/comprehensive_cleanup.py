#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Cleanup - Remove all unnecessary files
"""

import os
from pathlib import Path
from typing import List, Set

PROJECT_ROOT = Path(__file__).parent.parent

# Important files to keep
KEEP_FILES: Set[str] = {
    "README.md",
    "README_BOT.md",
    "README_ko.md",
    "SETUP_GUIDE.md",
    "LICENSE",
    "requirements.txt",
    "py.typed",
    "pyrightconfig.json",
    "CODE_CHECK_SUMMARY.md",
    "CODE_OPTIMIZATION_SUMMARY.md",
    "GIT_COMMIT_ISSUES_FIXED.md",
    "PROJECT_OPTIMIZATION_COMPLETE.md",
    "CODE_STYLE_UNIFICATION_COMPLETE.md",
    "FULL_CODE_CHECK_COMPLETE.md",
    "TRAINING_MONITORING_AND_AUTO_LEARNING_GUIDE.md",
}

# Patterns for files to delete
DELETE_PATTERNS = {
    "extensions": [".bak", ".tmp", ".old", ".orig", ".swp"],
    "suffixes": ["_fixed.py", "_old.py", "_backup.py", "_copy.py"],
    "doc_keywords": [
        "_COMPLETE.md",
        "_SUMMARY.md",
        "_REPORT.md",
        "_FIXED.md",
        "_STARTED.md",
        "_READY.md",
        "_GUIDE.md",  # Except important ones
        "_STATUS.md",
        "_ANALYSIS.md",
        "_IMPROVEMENT.md",
        "_OPTIMIZATION.md",
    ]
}


def should_keep_file(file_path: Path) -> bool:
    """Check if file should be kept"""
    name = file_path.name
    
    # Keep important files
    if name in KEEP_FILES:
        return True
    
    # Keep README and SETUP files
    if name.startswith("README") or name.startswith("SETUP"):
        return True
    
    # Keep LICENSE
    if "LICENSE" in name:
        return True
    
    # Keep important guides
    if "TRAINING_MONITORING" in name or "ARENA_DEPLOYMENT" in name:
        return True
    
    return False


def find_files_to_delete() -> List[Path]:
    """Find all files to delete"""
    files_to_delete: List[Path] = []
    
    # Find backup files
    for ext in DELETE_PATTERNS["extensions"]:
        for file_path in PROJECT_ROOT.rglob(f"*{ext}"):
            if file_path.is_file() and not should_keep_file(file_path):
                files_to_delete.append(file_path)
    
    # Find duplicate Python files
    for suffix in DELETE_PATTERNS["suffixes"]:
        for file_path in PROJECT_ROOT.rglob(f"*{suffix}"):
            if file_path.is_file():
                files_to_delete.append(file_path)
    
    # Find redundant documentation
    for file_path in PROJECT_ROOT.rglob("*.md"):
        if should_keep_file(file_path):
            continue
        
        # Check if matches delete patterns
        for keyword in DELETE_PATTERNS["doc_keywords"]:
            if keyword in file_path.name:
                # Skip if in important directories
                if "docs" in str(file_path) and "archive" not in str(file_path):
                    continue
                files_to_delete.append(file_path)
                break
    
    return files_to_delete


def main():
    """Main function"""
    print("=" * 70)
    print("COMPREHENSIVE CLEANUP")
    print("=" * 70)
    print()
    
    files_to_delete = find_files_to_delete()
    
    if not files_to_delete:
        print("No unnecessary files found.")
        return
    
    print(f"Found {len(files_to_delete)} files to delete:")
    print()
    
    # Group by type
    backup_files = [f for f in files_to_delete if f.suffix in [".bak", ".tmp", ".old", ".orig", ".swp"]]
    duplicate_files = [f for f in files_to_delete if any(suffix in f.name for suffix in ["_fixed", "_old", "_backup", "_copy"])]
    redundant_docs = [f for f in files_to_delete if f.suffix == ".md"]
    
    print(f"  Backup files: {len(backup_files)}")
    print(f"  Duplicate files: {len(duplicate_files)}")
    print(f"  Redundant docs: {len(redundant_docs)}")
    print()
    
    # Show files
    print("Files to be deleted:")
    for i, file_path in enumerate(sorted(files_to_delete), 1):
        rel_path = file_path.relative_to(PROJECT_ROOT)
        print(f"  {i}. {rel_path}")
    
    print()
    print("Deleting files...")
    print()
    
    deleted_count = 0
    failed_count = 0
    
    for file_path in sorted(files_to_delete):
        try:
            file_path.unlink()
            deleted_count += 1
            print(f"[DELETED] {file_path.relative_to(PROJECT_ROOT)}")
        except Exception as e:
            failed_count += 1
            print(f"[ERROR] Failed to delete {file_path.relative_to(PROJECT_ROOT)}: {e}")
    
    print()
    print("=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print(f"Deleted: {deleted_count} files")
    if failed_count > 0:
        print(f"Failed: {failed_count} files")
    print()


if __name__ == "__main__":
    main()
