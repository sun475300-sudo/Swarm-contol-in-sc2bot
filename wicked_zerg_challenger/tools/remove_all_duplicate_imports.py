#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove duplicate imports from all Python files
"""

import os
import sys
from pathlib import Path
from remove_duplicate_imports import DuplicateImportRemover

# Exclude directories
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "models", "replays", "replays_archive", "replays_quarantine",
    "replays_source", "node_modules", "data", "logs", "stats",
    "cleanup_backup", "backups"
}

def should_exclude(path: Path) -> bool:
    """Check if path should be excluded"""
    parts = set(path.parts)
    return any(d in parts for d in EXCLUDE_DIRS)

def find_python_files(base_path: Path):
    """Find all Python files recursively"""
    py_files = []
    for root, dirs, files in os.walk(base_path):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                if not should_exclude(file_path):
                    py_files.append(file_path)
    
    return py_files

def main():
    """Remove duplicate imports from all Python files"""
    
    print("\n" + "="*70)
    print("Remove Duplicate Imports from All Files")
    print("="*70)
    
    base_path = Path(__file__).resolve().parent.parent
    print(f"\nBase path: {base_path}")
    
    # Find all Python files
    print("\nFinding Python files...")
    py_files = find_python_files(base_path)
    print(f"Found {len(py_files)} Python files")
    
    # Process each file
    total_removed = 0
    files_processed = 0
    files_with_duplicates = 0
    
    for py_file in py_files:
        try:
            remover = DuplicateImportRemover(str(py_file))
            results = remover.remove_duplicates()
            
            if results["content_changed"]:
                files_with_duplicates += 1
                total_removed += results["duplicates_removed"]
                remover.create_backup()
                remover.save_changes(results["new_content"])
                print(f"  OK {py_file.relative_to(base_path)}: Removed {results['duplicates_removed']} duplicates")
            
            files_processed += 1
        except Exception as e:
            print(f"  ERROR {py_file.relative_to(base_path)}: {e}")
    
    print("\n" + "="*70)
    print("Duplicate Import Removal Complete!")
    print("="*70)
    print(f"Files processed: {files_processed}")
    print(f"Files with duplicates: {files_with_duplicates}")
    print(f"Total duplicates removed: {total_removed}")

if __name__ == "__main__":
    main()
