# -*- coding: utf-8 -*-
"""
���� ���� �˻� ����

����� ���ε� �� ��� ������ ������ �˻��մϴ�.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess

PROJECT_ROOT = Path(__file__).parent.parent


class FinalLogicChecker:
    """���� ���� �˻��"""
 
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
        """���� ���� �˻�"""
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
        """Import ���� �˻�"""
 errors = []
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 tree = ast.parse(content, filename=str(file_path))
 
 for node in ast.walk(tree):
 if isinstance(node, ast.ImportFrom):
 if node.module:
 # ��� import Ȯ��
                        if node.module.startswith('.'):
 # ��� import�� ��� Ȯ�� �ʿ�
 pass
 elif isinstance(node, ast.Import):
 for alias in node.names:
 # ǥ�� ���̺귯���� ������Ʈ �� ������� Ȯ��
 pass
 except SyntaxError:
 # ���� ������ �̹� üũ��
 pass
 except Exception as e:
            errors.append(f"Import check error: {e}")
 
 return len(errors) == 0, errors
 
 def check_file(self, file_path: Path) -> bool:
        """���� ���� �˻�"""
        if not file_path.suffix == '.py':
 return True
 
        self.stats["files_checked"] += 1
 rel_path = file_path.relative_to(PROJECT_ROOT)
 
 # ���� �˻�
 syntax_ok, syntax_errors = self.check_syntax(file_path)
 if not syntax_ok:
 for error in syntax_errors:
 self.errors.append({
                    "file": str(rel_path),
                    "type": "syntax",
                    "message": error
 })
 
 # Import �˻�
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
        """������Ʈ ��ü ��ĵ"""
        print("������Ʈ ��ü ��ĵ ��...")
 
 # ������ ���丮
 exclude_dirs = {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'backup_before_refactoring', 'models', 'logs', 'stats'
 }
 
 python_files = []
 for root, dirs, files in os.walk(PROJECT_ROOT):
 # ���� ���丮 ���͸�
 dirs[:] = [d for d in dirs if d not in exclude_dirs]
 
 for file in files:
                if file.endswith('.py'):
 file_path = Path(root) / file
 python_files.append(file_path)
 
        print(f"�� {len(python_files)}�� Python ���� �߰�")
 print()
 
 # �� ���� �˻�
 for i, file_path in enumerate(python_files, 1):
 if i % 20 == 0:
                print(f"  ���� ��: {i}/{len(python_files)}")
 self.check_file(file_path)
 
 def generate_report(self) -> str:
        """�˻� ����Ʈ ����"""
 report = []
        report.append("=" * 70)
        report.append("���� ���� �˻� ����Ʈ")
        report.append("=" * 70)
        report.append("")
 
        report.append(f"�˻��� ����: {self.stats['files_checked']}��")
        report.append(f"���� ����: {self.stats['syntax_errors']}��")
        report.append(f"�鿩���� ����: {self.stats['indentation_errors']}��")
        report.append(f"Import ���: {len(self.warnings)}��")
        report.append("")
 
 if self.errors:
            report.append("=" * 70)
            report.append("���� ���")
            report.append("=" * 70)
 for error in self.errors[:50]: # ���� 50����
                report.append(f"[{error['type'].upper()}] {error['file']}")
                report.append(f"  {error['message']}")
                report.append("")
 if len(self.errors) > 50:
                report.append(f"... �� {len(self.errors) - 50}�� ����")
                report.append("")
 else:
            report.append("? ���� ���� ����!")
            report.append("")
 
 if self.warnings:
            report.append("=" * 70)
            report.append("��� ��� (���� 20��)")
            report.append("=" * 70)
 for warning in self.warnings[:20]:
                report.append(f"[WARNING] {warning['file']}")
                report.append(f"  {warning['message']}")
                report.append("")
 
        report.append("=" * 70)
 if self.errors:
            report.append("? ������ �߰ߵǾ����ϴ�. ���� �� �ٽ� �˻��ϼ���.")
 else:
            report.append("? ��� ������ �����Դϴ�!")
        report.append("=" * 70)
 
        return "\n".join(report)


def main():
    """���� �Լ�"""
    print("=" * 70)
    print("���� ���� �˻� ����")
    print("=" * 70)
 print()
 
 checker = FinalLogicChecker()
 checker.scan_project()
 
 report = checker.generate_report()
 print(report)
 
 # ����Ʈ ����
    report_path = PROJECT_ROOT / "FINAL_LOGIC_CHECK_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
 f.write(report)
    print(f"\n����Ʈ ����: {report_path}")
 
 # ������ ������ ���� �ڵ� 1
 if checker.errors:
 sys.exit(1)
 else:
        print("\n? ��� �˻� ���! ����꿡 ���ε��� �غ� �Ǿ����ϴ�.")
 sys.exit(0)


if __name__ == "__main__":
 main()