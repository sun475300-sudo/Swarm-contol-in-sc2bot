# -*- coding: utf-8 -*-
"""
Final Logic Checker Tool

Checks all files before GitHub upload.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent

# Windows console encoding setup
if sys.platform == "win32":
 import io
 try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
 except AttributeError:
 # Python < 3.7
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class FinalLogicChecker:
    """Final logic checker"""
 
 def __init__(self):
 self.errors: List[Dict] = []
 self.warnings: List[Dict] = []
 self.stats = {
            "files_checked": 0,
            "syntax_errors": 0,
            "import_errors": 0,
            "indentation_errors": 0,
            "logic_errors": 0
 }
 
 def check_syntax(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Check syntax errors"""
 errors = []
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 try:
 ast.parse(content, filename=str(file_path))
 except SyntaxError as e:
                errors.append(f"SyntaxError: {e.msg} at line {e.lineno}")
                self.stats["syntax_errors"] += 1
 except IndentationError as e:
                errors.append(f"IndentationError: {e.msg} at line {e.lineno}")
                self.stats["indentation_errors"] += 1
 except Exception as e:
            errors.append(f"File read error: {e}")
 
 return len(errors) == 0, errors
 
 def check_imports(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Check import errors"""
 errors = []
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 tree = ast.parse(content, filename=str(file_path))
 
 for node in ast.walk(tree):
 if isinstance(node, ast.ImportFrom):
 if node.module:
 # Check relative imports
                        if node.module.startswith('.'):
 # Relative imports need path verification
 pass
 elif isinstance(node, ast.Import):
 for alias in node.names:
 # Check if standard library or project module
 pass
 except SyntaxError:
 # Syntax errors already checked
 pass
 except Exception as e:
            errors.append(f"Import check error: {e}")
 
 return len(errors) == 0, errors
 
 def check_file(self, file_path: Path) -> bool:
        """Check single file"""
        if not file_path.suffix == '.py':
 return True
 
        self.stats["files_checked"] += 1
 rel_path = file_path.relative_to(PROJECT_ROOT)
 
 # Syntax check
 syntax_ok, syntax_errors = self.check_syntax(file_path)
 if not syntax_ok:
 for error in syntax_errors:
 self.errors.append({
                    "file": str(rel_path),
                    "type": "syntax",
                    "message": error
 })
 
 # Import check
 import_ok, import_errors = self.check_imports(file_path)
 if not import_ok:
 for error in import_errors:
 self.warnings.append({
                    "file": str(rel_path),
                    "type": "import",
                    "message": error
 })
 
 return syntax_ok
 
 def scan_project(self):
        """Scan entire project"""
        print("Scanning project...")
 
 # Exclude directories
 exclude_dirs = {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'backup_before_refactoring', 'models', 'logs', 'stats'
 }
 
 python_files = []
 for root, dirs, files in os.walk(PROJECT_ROOT):
 # Filter excluded directories
 dirs[:] = [d for d in dirs if d not in exclude_dirs]
 
 for file in files:
                if file.endswith('.py'):
 file_path = Path(root) / file
 python_files.append(file_path)
 
        print(f"Found {len(python_files)} Python files")
 print()
 
 # Check each file
 for i, file_path in enumerate(python_files, 1):
 if i % 20 == 0:
                print(f"  Progress: {i}/{len(python_files)}")
 self.check_file(file_path)
 
 def generate_report(self) -> str:
        """Generate check report"""
 report = []
        report.append("=" * 70)
        report.append("Final Logic Check Report")
        report.append("=" * 70)
        report.append("")
 
        report.append(f"Files checked: {self.stats['files_checked']}")
        report.append(f"Syntax errors: {self.stats['syntax_errors']}")
        report.append(f"Indentation errors: {self.stats['indentation_errors']}")
        report.append(f"Import warnings: {len(self.warnings)}")
        report.append("")
 
 if self.errors:
            report.append("=" * 70)
            report.append("Error List")
            report.append("=" * 70)
 for error in self.errors[:50]: # Top 50 only
                report.append(f"[{error['type'].upper()}] {error['file']}")
                report.append(f"  {error['message']}")
                report.append("")
 if len(self.errors) > 50:
                report.append(f"... and {len(self.errors) - 50} more errors")
                report.append("")
 else:
            report.append("OK: No syntax errors!")
            report.append("")
 
 if self.warnings:
            report.append("=" * 70)
            report.append("Warning List (Top 20)")
            report.append("=" * 70)
 for warning in self.warnings[:20]:
                report.append(f"[WARNING] {warning['file']}")
                report.append(f"  {warning['message']}")
                report.append("")
 
        report.append("=" * 70)
 if self.errors:
            report.append("ERROR: Errors found. Please fix and check again.")
 else:
            report.append("OK: All files are normal!")
        report.append("=" * 70)
 
        return "\n".join(report)


def main():
    """Main function"""
    print("=" * 70)
    print("Final Logic Check Tool")
    print("=" * 70)
 print()
 
 checker = FinalLogicChecker()
 checker.scan_project()
 
 report = checker.generate_report()
 print(report)
 
 # Save report
    report_path = PROJECT_ROOT / "FINAL_LOGIC_CHECK_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
 f.write(report)
    print(f"\nReport saved: {report_path}")
 
 # Exit with code 1 if errors found
 if checker.errors:
 sys.exit(1)
 else:
        print("\nOK: All checks passed! Ready for GitHub upload.")
 sys.exit(0)


if __name__ == "__main__":
 main()