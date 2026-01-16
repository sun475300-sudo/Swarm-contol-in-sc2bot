#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup Korean Documentation Files

Remove Korean documentation files that are redundant or temporary.
"""

import os
import re
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent

# Keep important Korean files
KEEP_PATTERNS = [
    "README",
    "SETUP",
    "LICENSE",
]


def has_korean_characters(text: str) -> bool:
    """Check if text contains Korean characters"""
    # Korean character range: \uAC00-\uD7A3
    korean_pattern = re.compile(r'[\uAC00-\uD7A3]+')
    return bool(korean_pattern.search(text))


def should_delete_korean_file(file_path: Path) -> bool:
    """Check if Korean file should be deleted"""
    name = file_path.name
    
    # Keep if matches keep patterns
    if any(keep in name for keep in KEEP_PATTERNS):
        return False
    
    # Check if has Korean characters
    if not has_korean_characters(name):
        return False
    
    # Delete if contains report keywords (in Korean or English)
    delete_keywords = [
        "보고서", "요약", "완료", "분석", "해결", "개선", "점검",
        "REPORT", "SUMMARY", "COMPLETE", "ANALYSIS", "FIX"
    ]
    
    return any(keyword in name for keyword in delete_keywords)


def main():
    """Main function"""
    print("=" * 70)
    print("CLEANUP KOREAN DOCUMENTATION FILES")
    print("=" * 70)
    print()
    
    files_to_delete: List[Path] = []
    
    # Find Korean documentation files
    for file_path in PROJECT_ROOT.glob("*.md"):
        if should_delete_korean_file(file_path):
            files_to_delete.append(file_path)
    
    if not files_to_delete:
        print("No Korean documentation files to delete.")
        return
    
    print(f"Found {len(files_to_delete)} Korean documentation files to delete:")
    print()
    
    for i, file_path in enumerate(sorted(files_to_delete), 1):
        print(f"  {i}. {file_path.name}")
    
    print()
    print("Deleting files...")
    print()
    
    deleted_count = 0
    failed_count = 0
    
    for file_path in sorted(files_to_delete):
        try:
            file_path.unlink()
            deleted_count += 1
            print(f"[DELETED] {file_path.name}")
        except Exception as e:
            failed_count += 1
            print(f"[ERROR] Failed to delete {file_path.name}: {e}")
    
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
