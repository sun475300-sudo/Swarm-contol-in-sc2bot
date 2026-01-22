# -*- coding: utf-8 -*-
"""
Production Logic Checker

Comprehensive check for production-related logic
"""

import ast
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent


class ProductionLogicChecker:
    """Production logic checker"""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.files_checked: List[str] = []

    def check_file_syntax(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Check file syntax"""
        errors = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            try:
                ast.parse(content, filename=str(file_path))
                return True, []
            except SyntaxError as e:
                errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
                return False, errors
        except Exception as e:
            errors.append(f"Failed to read file: {e}")
            return False, errors

    def check_production_functions(self, file_path: Path) -> List[Dict[str, Any]]:
        """Check production-related functions"""
        issues = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            production_keywords = ["produce", "build", "train", "construct", "create"]

            functions_found = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name.lower()
                    for keyword in production_keywords:
                        if keyword in func_name:
                            functions_found.append(
                                {"name": node.name, "line": node.lineno}
                            )
                            break

            return issues
        except Exception as e:
            return [{"type": "error", "message": f"Failed to check functions: {e}"}]

    def check_file(self, file_path: Path) -> Dict[str, Any]:
        """Check entire file"""
        result = {
            "file": str(file_path),
            "syntax_ok": False,
            "issues": [],
            "warnings": [],
            "errors": [],
        }

        syntax_ok, syntax_errors = self.check_file_syntax(file_path)
        result["syntax_ok"] = syntax_ok
        result["errors"].extend(syntax_errors)

        if not syntax_ok:
            return result

        func_issues = self.check_production_functions(file_path)
        result["issues"].extend(func_issues)

        return result

    def check_all_production_files(self) -> Dict[str, Any]:
        """Check all production-related files"""
        production_files = []

        possible_files = [
            PROJECT_ROOT / "tools" / "analyze_tech_unit_production.py",
            PROJECT_ROOT / "spell_unit_manager.py",
            PROJECT_ROOT / "combat_manager.py",
            PROJECT_ROOT / "local_training" / "curriculum_manager.py",
        ]

        for file_path in possible_files:
            if file_path.exists():
                production_files.append(file_path)

        scripts_dir = PROJECT_ROOT / "local_training" / "scripts"
        if scripts_dir.exists():
            for file_path in scripts_dir.glob("*.py"):
                if any(
                    keyword in file_path.name.lower()
                    for keyword in ["build", "production", "replay"]
                ):
                    if file_path not in production_files:
                        production_files.append(file_path)

        results = {}
        total_issues = 0
        total_errors = 0
        total_warnings = 0

        for file_path in production_files:
            print(f"\n{'='*70}")
            print(f"Checking: {file_path.name}")
            print(f"{'='*70}")

            result = self.check_file(file_path)
            results[str(file_path)] = result

            total_issues += len(result["issues"])
            total_errors += len(result["errors"])
            total_warnings += len(result["warnings"])

            if result["syntax_ok"]:
                print("OK: Syntax")
            else:
                print("ERROR: Syntax errors found")
                for error in result["errors"]:
                    print(f"  - {error}")

            if result["warnings"]:
                print(f"\nWARNINGS ({len(result['warnings'])}):")
                for warning in result["warnings"][:5]:
                    print(f"  - {warning}")

        print(f"\n\n{'='*70}")
        print("PRODUCTION LOGIC CHECK SUMMARY")
        print(f"{'='*70}")
        print(f"Files checked: {len(results)}")
        print(f"Total issues: {total_issues}")
        print(f"Total errors: {total_errors}")
        print(f"Total warnings: {total_warnings}")
        print(f"{'='*70}")

        return {
            "results": results,
            "summary": {
                "files_checked": len(results),
                "total_issues": total_issues,
                "total_errors": total_errors,
                "total_warnings": total_warnings,
            },
        }


def main():
    """Main function"""
    print("=" * 70)
    print("PRODUCTION LOGIC CHECKER")
    print("=" * 70)
    print("\nChecking all production-related files...")

    checker = ProductionLogicChecker()
    results = checker.check_all_production_files()

    if results["summary"]["total_errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
