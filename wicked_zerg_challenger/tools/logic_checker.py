# -*- coding: utf-8 -*-
"""
Logic Checker

Scans source code for overlapping commands, duplicate logic, and bug patterns.
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).parent.parent


class LogicChecker:
    """Logic checker"""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []

    def check_overlapping_commands(self, file_path: Path) -> List[Dict[str, Any]]:
        """Check overlapping commands (same call clustered together)."""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                lines = content.splitlines()

            # Track repeated attribute calls in a short span.
            function_calls: Dict[str, List[int]] = defaultdict(list)

            try:
                tree = ast.parse(content, filename=str(file_path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute):
                            func_name = f"{ast.unparse(node.func)}"
                            function_calls[func_name].append(node.lineno)
            except SyntaxError:
                pass

            # Flag if the same call repeats 3+ times.
            for func_name, line_numbers in function_calls.items():
                if len(line_numbers) >= 3:
                    # Check for a consecutive cluster.
                    consecutive = []
                    for i, line_num in enumerate(line_numbers):
                        if i == 0 or line_num - line_numbers[i - 1] <= 5:  # 5�� �̳�
                            consecutive.append(line_num)
                        else:
                            if len(consecutive) >= 3:
                                issues.append(
                                    {
                                        "type": "overlapping_commands",
                                        "file": str(
                                            file_path.relative_to(PROJECT_ROOT)
                                        ),
                                        "function": func_name,
                                        "lines": consecutive,
                                        "message": (
                                            f"Repeated call '{func_name}' appears "
                                            f"{len(consecutive)} times in a short span"
                                        ),
                                    }
                                )
                            consecutive = [line_num]

            return issues

        except Exception as e:
            return [{"type": "error", "file": str(file_path), "message": str(e)}]

    def check_duplicate_logic(self, file_path: Path) -> List[Dict[str, Any]]:
        """Check duplicate logic blocks."""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Detect repeated 5-line blocks (rough heuristic).
            lines = content.splitlines()
            line_hashes: Dict[str, List[int]] = defaultdict(list)

            # Hash 5-line blocks.
            for i in range(len(lines) - 4):
                block = "\n".join(lines[i : i + 5])
                block_hash = hash(block.strip())
                line_hashes[block_hash].append(i + 1)

            # Flag if the same block appears 2+ times.
            for block_hash, line_numbers in line_hashes.items():
                if len(line_numbers) >= 2:
                    issues.append(
                        {
                            "type": "duplicate_logic",
                            "file": str(file_path.relative_to(PROJECT_ROOT)),
                            "lines": line_numbers,
                            "message": f"Duplicate code block detected (lines: {line_numbers})",
                        }
                    )

            return issues

        except Exception as e:
            return [{"type": "error", "file": str(file_path), "message": str(e)}]

    def check_bug_patterns(self, file_path: Path) -> List[Dict[str, Any]]:
        """Check common bug patterns."""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                lines = content.splitlines()

            # Pattern 1: method call without a None guard.
            for i, line in enumerate(lines, 1):
                if re.search(r"self\.\w+\.\w+\(", line) and "if" not in line[:20]:
                    if "None" not in line and "is not None" not in line:
                        issues.append(
                            {
                                "type": "bug_pattern",
                                "file": str(file_path.relative_to(PROJECT_ROOT)),
                                "line": i,
                                "message": (
                                    "Method call without None check: "
                                    f"{line.strip()[:50]}"
                                ),
                            }
                        )

            # Pattern 2: missing await in async functions (heuristic).
            for i, line in enumerate(lines, 1):
                if "async def" in content:
                    # Heuristic only; intentionally skipped for now.
                    if re.search(r"\b\w+\(.*\)", line) and "await" not in line:
                        # �̰� ��Ȯ���� �����Ƿ� �����
                        pass

            # Pattern 3: file/network operations without try/except.
            for i, line in enumerate(lines, 1):
                if any(
                    keyword in line for keyword in ["open(", "requests.", "urllib."]
                ):
                    # Check for nearby try: in preceding lines.
                    context = "\n".join(lines[max(0, i - 10) : i])
                    if "try:" not in context:
                        issues.append(
                            {
                                "type": "bug_pattern",
                                "file": str(file_path.relative_to(PROJECT_ROOT)),
                                "line": i,
                                "message": (
                                    "File/network call without try/except: "
                                    f"{line.strip()[:50]}"
                                ),
                            }
                        )

            return issues

        except Exception as e:
            return [{"type": "error", "file": str(file_path), "message": str(e)}]

    def scan_all(self, target_files: List[Path] = None) -> Dict[str, Any]:
        """Scan all Python files."""
        if target_files is None:
            target_files = []
            for root, dirs, files in os.walk(PROJECT_ROOT):
                dirs[:] = [
                    d
                    for d in dirs
                    if d
                    not in {
                        "__pycache__",
                        ".git",
                        "node_modules",
                        ".venv",
                        "venv",
                        "models",
                    }
                ]
                for file in files:
                    if file.endswith(".py"):
                        target_files.append(Path(root) / file)

        all_issues = {
            "overlapping_commands": [],
            "duplicate_logic": [],
            "bug_patterns": [],
            "total_files": len(target_files),
        }

        for file_path in target_files:
            overlapping = self.check_overlapping_commands(file_path)
            duplicate = self.check_duplicate_logic(file_path)
            bugs = self.check_bug_patterns(file_path)

            all_issues["overlapping_commands"].extend(overlapping)
            all_issues["duplicate_logic"].extend(duplicate)
            all_issues["bug_patterns"].extend(bugs)

        return all_issues


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Logic checker")
    parser.add_argument("--file", help="Check a specific file")
    parser.add_argument("--all", action="store_true", help="Check all files")

    args = parser.parse_args()

    print("=" * 70)
    print("LOGIC CHECKER")
    print("=" * 70)
    print()

    checker = LogicChecker()

    if args.file:
        file_path = PROJECT_ROOT / args.file
        if file_path.exists():
            overlapping = checker.check_overlapping_commands(file_path)
            duplicate = checker.check_duplicate_logic(file_path)
            bugs = checker.check_bug_patterns(file_path)

            print(f"[FILE] {args.file}")
            print(f"  overlapping commands: {len(overlapping)}")
            print(f"  duplicate logic: {len(duplicate)}")
            print(f"  bug patterns: {len(bugs)}")

            if overlapping:
                print("\nOverlapping commands:")
                for issue in overlapping:
                    print(f"  - {issue['message']}")

            if duplicate:
                print("\nDuplicate logic:")
                for issue in duplicate:
                    print(f"  - {issue['message']}")

            if bugs:
                print("\nBug patterns:")
                for issue in bugs:
                    print(f"  - {issue['message']}")

        else:
            print(f"[ERROR] File not found: {args.file}")
    elif args.all:
        print("Scanning all files...")
        results = checker.scan_all()
        print(f"\nScan complete: {results['total_files']} files")
        print(f"overlapping commands: {len(results['overlapping_commands'])}")
        print(f"duplicate logic: {len(results['duplicate_logic'])}")
        print(f"bug patterns: {len(results['bug_patterns'])}")

        if results["overlapping_commands"]:
            print("\nOverlapping command findings:")
            for issue in results["overlapping_commands"][:10]:
                print(f"  - {issue['file']}: {issue['message']}")

        if results["duplicate_logic"]:
            print("\nDuplicate logic findings:")
            for issue in results["duplicate_logic"][:10]:
                print(f"  - {issue['file']}: {issue['message']}")

        if results["bug_patterns"]:
            print("\nBug pattern findings:")
            for issue in results["bug_patterns"][:10]:
                print(f"  - {issue['file']}: {issue['message']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
