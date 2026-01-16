# -*- coding: utf-8 -*-
"""
���� ������Ʈ �м� ����

1. ���ʿ��� ���� �ĺ� �� ����
2. �ڵ� ��Ÿ�� ����ȭ ����
3. ���� ���� ����
4. ������Ʈ ���� �м�
"""

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent


class ComprehensiveAnalyzer:
    """���� ������Ʈ �м���"""
 
 def __init__(self):
 self.unnecessary_files: List[Path] = []
 self.unnecessary_dirs: List[Path] = []
 self.style_issues: Dict[str, List[str]] = {}
 self.import_errors: List[Dict] = []
 self.duplicate_files: List[Dict] = []
 
 def find_unnecessary_files(self) -> Dict:
        """���ʿ��� ���� ã��"""
 unnecessary_patterns = [
            '*.bak',
            '*.tmp',
            '*.swp',
            '*.pyc',
            '*.pyo',
            '*.log',
            '*.cache',
            '*.orig',
            '*.rej',
            '.DS_Store',
            'Thumbs.db',
            'desktop.ini',
 ]
 
 unnecessary_dirs = [
            '__pycache__',
            '.pytest_cache',
            '.mypy_cache',
            '.ruff_cache',
            '.tox',
            '*.egg-info',
            'backup_before_refactoring',
            'node_modules',
 ]
 
 # �Ʒ�/���࿡ ���ʿ��� ���� ����
 exclude_md_patterns = [
            'README*.md',
            'SETUP_GUIDE.md',
            'SETUP.md',
            'CONTRIBUTING.md',
            'LICENSE.md',
 ]
 
 results = {
            "unnecessary_files": [],
            "unnecessary_dirs": [],
            "backup_files": [],
            "cache_files": [],
            "duplicate_docs": []
 }
 
 # ��� ���� ��ĵ
 for root, dirs, files in os.walk(PROJECT_ROOT):
 # ������ ���丮 ���͸�
 dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'node_modules', '.venv', 'venv',
                'models', 'logs', 'stats', 'backup_before_refactoring'
 }]
 
 root_path = Path(root)
 
 # ���ʿ��� ���丮 Ȯ��
 for dir_name in dirs:
 if dir_name in unnecessary_dirs:
 dir_path = root_path / dir_name
 if dir_path.exists():
                        results["unnecessary_dirs"].append(str(dir_path.relative_to(PROJECT_ROOT)))
 
 # ���� Ȯ��
 for file in files:
 file_path = root_path / file
 rel_path = file_path.relative_to(PROJECT_ROOT)
 
 # ��� ����
                if file.endswith('.bak') or file.endswith('.tmp'):
                    results["backup_files"].append(str(rel_path))
 
 # ĳ�� ����
                if file.endswith('.pyc') or file.endswith('.pyo'):
                    results["cache_files"].append(str(rel_path))
 
 # �ߺ� ���� ���� (README, SETUP ����)
                if file.endswith('.md') and file not in ['README.md', 'README_�ѱ���.md', 'SETUP.md', 'SETUP_GUIDE.md', 'CONTRIBUTING.md']:
 # �ʹ� ���� .md ������ ���ʿ��� �� ����
                    if 'ARCHIVE' in str(rel_path) or 'OLD' in str(rel_path) or 'BACKUP' in str(rel_path):
                        results["duplicate_docs"].append(str(rel_path))
 
 return results
 
 def verify_code_style(self) -> Dict:
        """�ڵ� ��Ÿ�� ���� (PEP 8)"""
 issues = {
            "tab_usage": [],
            "line_length": [],
            "import_order": [],
            "naming_conventions": [],
            "whitespace": []
 }
 
 python_files = []
 for root, dirs, files in os.walk(PROJECT_ROOT):
 dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'
 }]
 for file in files:
                if file.endswith('.py'):
 python_files.append(Path(root) / file)
 
 for file_path in python_files:
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()
 
 rel_path = str(file_path.relative_to(PROJECT_ROOT))
 
 for i, line in enumerate(lines, 1):
 # �� ��� �˻�
                    if '\t' in line:
                        issues["tab_usage"].append({
                            "file": rel_path,
                            "line": i,
                            "content": line.strip()[:50]
 })
 
 # �� ���� �˻� (120�� �ʰ��� ���)
 if len(line.rstrip()) > 120:
                        issues["line_length"].append({
                            "file": rel_path,
                            "line": i,
                            "length": len(line.rstrip())
 })
 
 # ���� �˻�
                    if line.strip() and line.startswith('  ') and not line.startswith('    '):
 # 2ĭ �鿩����� PEP 8 ���� (4ĭ ���)
                        if not line.startswith(' ') or line.startswith('   '):
 pass # 3ĭ�� ������
                        elif line.startswith('  ') and not line.startswith('    '):
 # 2ĭ �鿩���� (�Ϻ� ���Ͽ��� ���� �� ����)
 pass
 except Exception:
 continue
 
 return issues
 
 def verify_execution_logic(self) -> Dict:
        """���� ���� ����"""
 entry_points = []
 import_graph = defaultdict(set)
 
 # ���� ������ ã��
 main_files = [
            'main.py',
            'run.py',
            'train.py',
            'COMPLETE_RUN_SCRIPT.py',
            'local_training/train.py',
 ]
 
 for main_file in main_files:
 main_path = PROJECT_ROOT / main_file
 if main_path.exists():
 entry_points.append(str(main_path.relative_to(PROJECT_ROOT)))
 
 # import ������ �м�
 python_files = []
        for root, dirs, files in os.walk(PROJECT_ROOT / 'src' if (PROJECT_ROOT / 'src').exists() else PROJECT_ROOT):
 dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'node_modules', '.venv', 'venv'
 }]
 for file in files:
                if file.endswith('.py'):
 python_files.append(Path(root) / file)
 
 for file_path in python_files:
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 tree = ast.parse(content, filename=str(file_path))
 rel_path = str(file_path.relative_to(PROJECT_ROOT))
 
 for node in ast.walk(tree):
 if isinstance(node, ast.Import):
 for alias in node.names:
 import_graph[rel_path].add(alias.name)
 elif isinstance(node, ast.ImportFrom):
 if node.module:
 import_graph[rel_path].add(node.module)
 except Exception:
 continue
 
 return {
            "entry_points": entry_points,
            "import_graph": {k: list(v) for k, v in import_graph.items()},
            "total_modules": len(python_files)
 }
 
 def analyze_project_structure(self) -> Dict:
        """������Ʈ ���� �м�"""
 structure = {
            "directories": [],
            "python_files": 0,
            "markdown_files": 0,
            "batch_files": 0,
            "config_files": 0,
            "total_files": 0
 }
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
 # ������ ���丮 ���͸�
 dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'node_modules', '.venv', 'venv',
                'models', 'logs', 'stats'
 }]
 
 root_path = Path(root)
 rel_path = root_path.relative_to(PROJECT_ROOT)
 
            if rel_path != Path('.'):
                structure["directories"].append(str(rel_path))
 
 for file in files:
                structure["total_files"] += 1
                if file.endswith('.py'):
                    structure["python_files"] += 1
                elif file.endswith('.md'):
                    structure["markdown_files"] += 1
                elif file.endswith('.bat'):
                    structure["batch_files"] += 1
                elif file.endswith(('.json', '.yaml', '.yml', '.ini', '.cfg', '.toml')):
                    structure["config_files"] += 1
 
 return structure
 
 def generate_report(self) -> str:
        """���� ����Ʈ ����"""
 report = []
        report.append("# ���� ������Ʈ �м� ����Ʈ\n\n")
        report.append(f"**���� �Ͻ�**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        report.append("---\n\n")
 
 # 1. ���ʿ��� ����
 unnecessary = self.find_unnecessary_files()
        report.append("## 1. ���ʿ��� ���� �м�\n\n")
        report.append(f"- **��� ����**: {len(unnecessary['backup_files'])}��\n")
        report.append(f"- **ĳ�� ����**: {len(unnecessary['cache_files'])}��\n")
        report.append(f"- **���ʿ��� ���丮**: {len(unnecessary['unnecessary_dirs'])}��\n")
        report.append(f"- **�ߺ� ����**: {len(unnecessary['duplicate_docs'])}��\n\n")
 
        if unnecessary['backup_files']:
            report.append("### ��� ���� ��� (���� ����)\n\n")
            for file in unnecessary['backup_files'][:20]:
                report.append(f"- `{file}`\n")
            report.append("\n")
 
 # 2. �ڵ� ��Ÿ��
 style_issues = self.verify_code_style()
        report.append("## 2. �ڵ� ��Ÿ�� ����\n\n")
        report.append(f"- **�� ���**: {len(style_issues['tab_usage'])}��\n")
        report.append(f"- **�� ��**: {len(style_issues['line_length'])}��\n\n")
 
 # 3. ���� ����
 execution = self.verify_execution_logic()
        report.append("## 3. ���� ���� ����\n\n")
        report.append(f"- **������**: {len(execution['entry_points'])}��\n")
        for entry in execution['entry_points']:
            report.append(f"  - `{entry}`\n")
        report.append(f"\n- **��� ��**: {execution['total_modules']}��\n\n")
 
 # 4. ������Ʈ ����
 structure = self.analyze_project_structure()
        report.append("## 4. ������Ʈ ����\n\n")
        report.append(f"- **Python ����**: {structure['python_files']}��\n")
        report.append(f"- **Markdown ����**: {structure['markdown_files']}��\n")
        report.append(f"- **��ġ ����**: {structure['batch_files']}��\n")
        report.append(f"- **���� ����**: {structure['config_files']}��\n")
        report.append(f"- **�� ����**: {structure['total_files']}��\n\n")
 
 # ���� ����
        report.append("---\n\n")
        report.append("## ���� ����\n\n")
 
        if unnecessary['backup_files'] or unnecessary['cache_files']:
            report.append("### 1. ���ʿ��� ���� ����\n\n")
            report.append(f"- {len(unnecessary['backup_files'])}���� ��� ���ϰ� {len(unnecessary['cache_files'])}���� ĳ�� ������ �����ϼ���.\n\n")
 
        if style_issues['tab_usage']:
            report.append("### 2. �ڵ� ��Ÿ�� ����ȭ\n\n")
            report.append(f"- {len(style_issues['tab_usage'])}�� ���Ͽ��� �� ���ڸ� �������� �����ϼ���.\n")
            report.append("- `tools/code_quality_improver.py --fix-style`�� �����ϼ���.\n\n")
 
        return ''.join(report)


def main():
    """���� �Լ�"""
    print("=" * 70)
    print("���� ������Ʈ �м� ����")
    print("=" * 70)
 print()
 
 analyzer = ComprehensiveAnalyzer()
 
    print("���ʿ��� ���� �м� ��...")
 unnecessary = analyzer.find_unnecessary_files()
    print(f"  - ��� ����: {len(unnecessary['backup_files'])}��")
    print(f"  - ĳ�� ����: {len(unnecessary['cache_files'])}��")
    print(f"  - ���ʿ��� ���丮: {len(unnecessary['unnecessary_dirs'])}��")
 print()
 
    print("�ڵ� ��Ÿ�� ���� ��...")
 style_issues = analyzer.verify_code_style()
    print(f"  - �� ���: {len(style_issues['tab_usage'])}��")
    print(f"  - �� ��: {len(style_issues['line_length'])}��")
 print()
 
    print("���� ���� ���� ��...")
 execution = analyzer.verify_execution_logic()
    print(f"  - ������: {len(execution['entry_points'])}��")
    print(f"  - ��� ��: {execution['total_modules']}��")
 print()
 
    print("������Ʈ ���� �м� ��...")
 structure = analyzer.analyze_project_structure()
    print(f"  - Python ����: {structure['python_files']}��")
    print(f"  - Markdown ����: {structure['markdown_files']}��")
    print(f"  - ��ġ ����: {structure['batch_files']}��")
 print()
 
    print("����Ʈ ���� ��...")
 report = analyzer.generate_report()
 
    report_path = PROJECT_ROOT / "COMPREHENSIVE_ANALYSIS_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
 f.write(report)
 
    print(f"����Ʈ�� �����Ǿ����ϴ�: {report_path}")
 print()
    print("=" * 70)
    print("�Ϸ�!")
    print("=" * 70)


if __name__ == "__main__":
 main()