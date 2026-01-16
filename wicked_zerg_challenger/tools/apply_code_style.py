#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply code style unification to all Python files
"""

import os
import sys
from pathlib import Path

# Setup encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).parent.parent
EXCLUDE_DIRS = {'__pycache__', '.git', 'node_modules', '.venv', 'venv',
                'build', 'dist', '.pytest_cache', '.mypy_cache', 'local_training'}


def normalize_file(file_path: Path) -> tuple[bool, int]:
    """Normalize code style in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original = content
        fixes = 0

        # 1. Convert tabs to 4 spaces
        if '\t' in content:
            lines = content.splitlines(keepends=True)
            new_lines = []
            for line in lines:
                if '\t' in line:
                    # Simple tab to space conversion
                    line = line.expandtabs(4)
                    fixes += 1
                new_lines.append(line)
            content = ''.join(new_lines)

        # 2. Remove trailing whitespace
        lines = content.splitlines(keepends=True)
        new_lines = []
        for line in lines:
            original_line = line
            if line.endswith(('\r\n', '\n')):
                line_content = line.rstrip('\r\n')
                line_content = line_content.rstrip()
                line = line_content + ('\r\n' if original_line.endswith('\r\n') else '\n')
            else:
                line = line.rstrip()
            if original_line != line:
                fixes += 1
            new_lines.append(line)
        content = ''.join(new_lines)

        # 3. Ensure final newline
        if content and not content.endswith('\n'):
            content += '\n'
            fixes += 1

        if content != original and fixes > 0:
            # Validate syntax before writing
            try:
                compile(content, str(file_path), 'exec')
                with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(content)
                return True, fixes
            except SyntaxError:
                return False, 0

        return True, 0

    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return False, 0


def find_python_files(root: Path = None) -> list[Path]:
    """Find all Python files"""
    if root is None:
        root = PROJECT_ROOT

    python_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for filename in filenames:
            if filename.endswith('.py'):
                python_files.append(Path(dirpath) / filename)

    return python_files


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Apply code style unification")
    parser.add_argument("--all", action="store_true", help="Process all files")
    parser.add_argument("--file", help="Process specific file")

    args = parser.parse_args()

    print("=" * 70)
    print("Code Style Unification")
    print("=" * 70)
    print()

    if args.file:
        file_path = Path(args.file)
        if file_path.exists():
            print(f"Processing: {file_path}")
            success, fixes = normalize_file(file_path)
            if success:
                print(f"  Fixed: {fixes} issues")
            else:
                print(f"  Failed")
        else:
            print(f"File not found: {file_path}")

    elif args.all:
        print("Finding all Python files...")
        files = find_python_files()
        print(f"Found {len(files)} Python files")
        print()

        total_fixed = 0
        total_files_fixed = 0
        errors = 0

        for i, file_path in enumerate(files, 1):
            if i % 10 == 0:
                print(f"Progress: {i}/{len(files)} ({i*100//len(files)}%)")

            success, fixes = normalize_file(file_path)
            if success and fixes > 0:
                total_fixed += fixes
                total_files_fixed += 1
            elif not success:
                errors += 1

        print()
        print("=" * 70)
        print("Complete!")
        print("=" * 70)
        print(f"Processed: {len(files)} files")
        print(f"Fixed: {total_files_fixed} files")
        print(f"Total fixes: {total_fixed}")
        print(f"Errors: {errors}")
        print("=" * 70)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
