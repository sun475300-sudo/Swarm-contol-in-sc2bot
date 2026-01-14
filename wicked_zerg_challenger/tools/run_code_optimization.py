#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run complete code optimization process
- Format code (remove trailing whitespace, normalize blank lines)
- Remove duplicate imports
- Analyze for code duplication
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Exclude directories
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "models", "replays", "replays_archive", "replays_quarantine",
    "replays_source", "node_modules", "data", "logs", "stats",
    "cleanup_backup"
}

def should_exclude(path: Path) -> bool:
    """Check if path should be excluded"""
    parts = set(path.parts)
    return any(d in parts for d in EXCLUDE_DIRS)

def format_python_file(file_path: Path) -> Tuple[int, int]:
    """
    Format Python file:
    - Remove trailing whitespace
    - Normalize blank lines (max 2 consecutive)
    - Remove trailing blank lines at end of file
    Returns: (bytes_reduced, lines_modified)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_size = len(content)
        lines = content.split('\n')
        original_lines = len(lines)

        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in lines]

        # Join and remove excessive blank lines (more than 2 consecutive)
        content = '\n'.join(lines)
        content = re.sub(r'\n{4,}', '\n\n\n', content)

        # Remove trailing blank lines at end of file
        content = content.rstrip() + '\n'

        new_size = len(content)
        bytes_reduced = original_size - new_size

        if bytes_reduced > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return (bytes_reduced, 1)

        return (0, 0)

    except Exception as e:
        print(f"  [ERROR] Failed to format {file_path.name}: {e}")
        return (0, 0)

def find_python_files(base_path: Path) -> List[Path]:
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

def analyze_duplicate_imports(file_path: Path) -> List[str]:
    """Find duplicate imports in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        imports = {}
        duplicates = []

        for i, line in enumerate(lines, 1):
            # Match import statements
            match = re.match(r'^(from\s+\S+\s+)?import\s+(.+)$', line.strip())
            if match:
                import_stmt = line.strip()
                if import_stmt in imports:
                    duplicates.append(f"Line {i}: {import_stmt} (duplicate of line {imports[import_stmt]})")
                else:
                    imports[import_stmt] = i

        return duplicates
    except Exception as e:
        return [f"Error analyzing: {e}"]

def main():
    """Run complete code optimization"""
    print("\n" + "="*70)
    print("Code Optimization Process")
    print("="*70)

    base_path = Path(__file__).resolve().parent.parent
    print(f"\nBase path: {base_path}")

    # Find all Python files
    print("\n[1/3] Finding Python files...")
    py_files = find_python_files(base_path)
    print(f"Found {len(py_files)} Python files")

    # Format files
    print("\n[2/3] Formatting files (removing trailing whitespace, normalizing blank lines)...")
    total_bytes_reduced = 0
    files_modified = 0

    for py_file in py_files:
        bytes_reduced, modified = format_python_file(py_file)
        if modified > 0:
            total_bytes_reduced += bytes_reduced
            files_modified += modified
            print(f"  OK {py_file.relative_to(base_path)} (-{bytes_reduced} bytes)")

    print(f"\nFormatted {files_modified} files ({total_bytes_reduced:,} bytes reduced)")

    # Analyze duplicate imports
    print("\n[3/3] Analyzing duplicate imports...")
    files_with_duplicates = 0
    total_duplicates = 0

    for py_file in py_files[:50]:  # Limit to first 50 files for performance
        duplicates = analyze_duplicate_imports(py_file)
        if duplicates:
            files_with_duplicates += 1
            total_duplicates += len(duplicates)
            print(f"  WARN {py_file.relative_to(base_path)}: {len(duplicates)} duplicate imports")

    if files_with_duplicates == 0:
        print("  OK No duplicate imports found in sampled files")
    else:
        print(f"\nFound {total_duplicates} duplicate imports in {files_with_duplicates} files")
        print("  (Use tools/remove_duplicate_imports.py to fix)")

    # Summary
    print("\n" + "="*70)
    print("Optimization Complete!")
    print("="*70)
    print(f"Files formatted: {files_modified}")
    print(f"Bytes reduced: {total_bytes_reduced:,}")
    print(f"Files with duplicate imports: {files_with_duplicates}")
    print("\nNext steps:")
    print("  - Run tools/remove_duplicate_imports.py to remove duplicate imports")
    print("  - Run tools/scan_unused_imports.py to find unused imports")

if __name__ == "__main__":
    main()
