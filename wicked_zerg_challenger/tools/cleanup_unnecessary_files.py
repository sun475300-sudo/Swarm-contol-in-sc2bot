#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup Unnecessary Files

프로젝트에서 불필요한 파일들을 찾아 삭제하는 스크립트입니다.
"""

import os
from pathlib import Path
from typing import List, Set

PROJECT_ROOT = Path(__file__).parent.parent

# 삭제할 파일 패턴
DELETE_PATTERNS = {
    "backup_files": ["*.bak", "*.tmp", "*.old", "*.orig"],
    "duplicate_files": ["*_fixed.py", "*_old.py", "*_backup.py"],
    "redundant_docs": [
        "*SUMMARY.md",
        "*COMPLETE.md",
        "*COMPLETE_SUMMARY.md",
        "*_SUMMARY.md",
        "*_FIX_SUMMARY.md",
        "*_IMPROVEMENT_SUMMARY.md",
        "*_OPTIMIZATION_SUMMARY.md",
        "*_CLEANUP_SUMMARY.md",
        "*_ANALYSIS_SUMMARY.md",
    ]
}

# 보존할 파일들 (중요한 문서)
KEEP_FILES = {
    "CODE_CHECK_SUMMARY.md",
    "CODE_OPTIMIZATION_SUMMARY.md",
    "GIT_COMMIT_ISSUES_FIXED.md",
    "PROJECT_OPTIMIZATION_COMPLETE.md",
    "CODE_STYLE_UNIFICATION_COMPLETE.md",
    "FULL_CODE_CHECK_COMPLETE.md",
}


def find_files_to_delete(root: Path) -> List[Path]:
    """Find files that should be deleted"""
    files_to_delete: List[Path] = []

    # Find backup files
    for pattern in DELETE_PATTERNS["backup_files"]:
        for ext in [".bak", ".tmp", ".old", ".orig"]:
            for file_path in root.rglob(f"*{ext}"):
                if file_path.is_file():
                    files_to_delete.append(file_path)

    # Find duplicate fixed files
    for pattern in DELETE_PATTERNS["duplicate_files"]:
        for suffix in ["_fixed.py", "_old.py", "_backup.py"]:
            for file_path in root.rglob(f"*{suffix}"):
                if file_path.is_file():
                    files_to_delete.append(file_path)

    # Find redundant documentation files
    for file_path in root.rglob("*.md"):
        if file_path.name in KEEP_FILES:
            continue
        
        # Check if it matches redundant patterns
        for pattern in DELETE_PATTERNS["redundant_docs"]:
            if pattern.replace("*", "") in file_path.name:
                # But keep important ones
                if any(keep in file_path.name for keep in ["CODE_CHECK", "CODE_OPTIMIZATION", 
                                                            "GIT_COMMIT", "PROJECT_OPTIMIZATION"]):
                    continue
                files_to_delete.append(file_path)
                break

    return files_to_delete


def main():
    """Main function"""
    print("=" * 70)
    print("CLEANUP UNNECESSARY FILES")
    print("=" * 70)
    print()

    files_to_delete = find_files_to_delete(PROJECT_ROOT)

    if not files_to_delete:
        print("No unnecessary files found.")
        return

    print(f"Found {len(files_to_delete)} files to delete:")
    print()

    # Group by type
    backup_files = [f for f in files_to_delete if f.suffix in [".bak", ".tmp", ".old", ".orig"]]
    duplicate_files = [f for f in files_to_delete if "_fixed" in f.name or "_old" in f.name]
    redundant_docs = [f for f in files_to_delete if f.suffix == ".md"]

    print(f"  Backup files: {len(backup_files)}")
    print(f"  Duplicate files: {len(duplicate_files)}")
    print(f"  Redundant docs: {len(redundant_docs)}")
    print()

    # Show files
    print("Files to be deleted:")
    for file_path in sorted(files_to_delete):
        rel_path = file_path.relative_to(PROJECT_ROOT)
        print(f"  - {rel_path}")

    print()
    response = input("Delete these files? (yes/no): ")

    if response.lower() in ["yes", "y"]:
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
                print(f"[DELETED] {file_path.relative_to(PROJECT_ROOT)}")
            except Exception as e:
                print(f"[ERROR] Failed to delete {file_path.relative_to(PROJECT_ROOT)}: {e}")

        print()
        print(f"Deleted {deleted_count} files.")
    else:
        print("Deletion cancelled.")


if __name__ == "__main__":
    main()
