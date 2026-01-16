# -*- coding: utf-8 -*-
"""
ū ���� �� ������ �Լ� �м� ����

ū ���� �и� �� ������ �Լ� �ܼ�ȭ�� ���� �м� ����
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent


def analyze_file_structure(file_path: Path) -> Dict:
    """���� ���� �м�"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            lines = content.splitlines()

        tree = ast.parse(content, filename=str(file_path))

        result = {
            "file": str(file_path.relative_to(PROJECT_ROOT)),
            "total_lines": len(lines),
            "classes": [],
            "functions": [],
            "imports": []
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                func_length = end_line - start_line + 1

                # ���⵵ ���
                complexity = 1
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1

                result["functions"].append({
                    "name": node.name,
                    "line": start_line,
                    "length": func_length,
                    "complexity": complexity
                })

            elif isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                result["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "method_count": len(methods)
                })

        return result
    except Exception as e:
        return {"file": str(file_path.relative_to(PROJECT_ROOT)), "error": str(e)}


def find_large_files(min_lines: int = 1000) -> List[Dict]:
    """ū ���� ã��"""
    large_files = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models', 'logs'
        }]

        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = len(f.readlines())

                    if lines >= min_lines:
                        analysis = analyze_file_structure(file_path)
                        large_files.append(analysis)
                except Exception:
                    continue

    return sorted(large_files, key=lambda x: x.get("total_lines", 0), reverse=True)


def find_complex_functions(min_complexity: int = 15) -> List[Dict]:
    """������ �Լ� ã��"""
    complex_functions = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models', 'logs'
        }]

        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                analysis = analyze_file_structure(file_path)

                for func in analysis.get("functions", []):
                    if func.get("complexity", 0) >= min_complexity:
                        func_info = func.copy()
                        func_info["file"] = analysis["file"]
                        complex_functions.append(func_info)

    return sorted(complex_functions, key=lambda x: x.get("complexity", 0), reverse=True)


def generate_refactoring_suggestions(large_files: List[Dict], complex_functions: List[Dict]) -> str:
    """�����丵 ���� ����"""
    suggestions = []
    suggestions.append("# ū ���� �� ������ �Լ� �����丵 ����\n\n")
    suggestions.append(f"**���� �Ͻ�**: {Path(__file__).stat().st_mtime}\n\n")
    suggestions.append("---\n\n")

    # ū ���� ����
    if large_files:
        suggestions.append("## 1. ū ���� �и� ����\n\n")
        for file_info in large_files:
            file_path = file_info["file"]
            total_lines = file_info.get("total_lines", 0)
            classes = file_info.get("classes", [])
            functions = file_info.get("functions", [])

            suggestions.append(f"### `{file_path}` ({total_lines}��)\n\n")
            suggestions.append(f"- **Ŭ���� ��**: {len(classes)}��\n")
            suggestions.append(f"- **�Լ� ��**: {len(functions)}��\n\n")

            if classes:
                suggestions.append("**�и� ������ Ŭ����**:\n\n")
                for cls in classes[:5]:
                    suggestions.append(f"- `{cls['name']}` (�޼���: {cls['method_count']}��)\n")
                suggestions.append("\n")

            suggestions.append("**�и� ����**:\n\n")
            suggestions.append(f"1. `{file_path}`�� ��ɺ��� ���� ���� �и�\n")
            suggestions.append(f"2. �� Ŭ������ ���� ���Ϸ� �и�\n")
            suggestions.append(f"3. ���� ��ƿ��Ƽ�� `utils/` ������ �̵�\n\n")

    # ������ �Լ� ����
    if complex_functions:
        suggestions.append("## 2. ������ �Լ� �ܼ�ȭ ����\n\n")
        suggestions.append(f"�� {len(complex_functions)}���� ������ �Լ��� �߰ߵǾ����ϴ�.\n\n")

        for func_info in complex_functions[:10]:  # ���� 10����
            file_path = func_info["file"]
            func_name = func_info["name"]
            complexity = func_info["complexity"]
            line = func_info["line"]
            length = func_info["length"]

            suggestions.append(f"### `{file_path}:{line}` - `{func_name}`\n\n")
            suggestions.append(f"- **���⵵**: {complexity}\n")
            suggestions.append(f"- **����**: {length}��\n\n")

            suggestions.append("**�ܼ�ȭ ����**:\n\n")
            suggestions.append(f"1. `{func_name}` �Լ��� ���� �Լ��� �и�\n")
            suggestions.append(f"2. ���ǹ� ������ ���� �޼���� ����\n")
            suggestions.append(f"3. �ߺ� �ڵ� ���� �� ���� �Լ��� ����\n\n")

    suggestions.append("---\n\n")
    suggestions.append("## �����丵 �켱����\n\n")
    suggestions.append("1. **ū ���� �и�**: �ڵ� ������ �� ���������� ���\n")
    suggestions.append("2. **������ �Լ� �ܼ�ȭ**: �׽�Ʈ ���̼� �� ���� ����\n")
    suggestions.append("3. **�ߺ� �ڵ� ����**: �ڵ� ���뼺 ���\n\n")

    return ''.join(suggestions)


def main():
    """���� �Լ�"""
    print("=" * 70)
    print("ū ���� �� ������ �Լ� �м�")
    print("=" * 70)
    print()

    print("ū ���� ã�� ��...")
    large_files = find_large_files(min_lines=1000)
    print(f"  - �߰�: {len(large_files)}��")
    for file_info in large_files:
        print(f"    - {file_info['file']}: {file_info.get('total_lines', 0)}��")
    print()

    print("������ �Լ� ã�� ��...")
    complex_functions = find_complex_functions(min_complexity=15)
    print(f"  - �߰�: {len(complex_functions)}��")
    for func_info in complex_functions[:5]:
        print(f"    - {func_info['file']}:{func_info['line']} - {func_info['name']} (���⵵: {func_info['complexity']})")
    print()

    print("�����丵 ���� ���� ��...")
    suggestions = generate_refactoring_suggestions(large_files, complex_functions)

    report_path = PROJECT_ROOT / "REFACTORING_SUGGESTIONS.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(suggestions)

    print(f"����Ʈ�� �����Ǿ����ϴ�: {report_path}")
    print()
    print("=" * 70)
    print("�Ϸ�!")
    print("=" * 70)


if __name__ == "__main__":
    main()
