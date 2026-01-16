#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
�ҽ��ڵ� ����ȭ ����

1. �ε����̼� ���� ����
2. ���ʿ��� �ڵ� ����
3. �ڵ� ��Ÿ�� ����
4. Ÿ�� ��Ʈ �߰�
5. ���� ����ȭ
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set
import sys

# ���ڵ� ����
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).parent.parent


class SourceOptimizer:
    """�ҽ��ڵ� ����ȭ��"""

    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.stats = {
            "files_processed": 0,
            "indentation_fixed": 0,
            "unused_imports_removed": 0,
            "style_issues_fixed": 0,
            "type_hints_added": 0,
        }

    def fix_indentation(self, file_path: Path) -> Tuple[bool, int]:
        """
        �ε����̼� ���� ����

        Returns:
            (success, fixed_lines_count)
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            lines = content.splitlines(keepends=True)
            fixed_lines = []
            indent_stack = [0]  # �鿩���� ���� ����
            fixed_count = 0

            i = 0
            while i < len(lines):
                line = lines[i]
                stripped = line.lstrip()

                # �� ���� �״�� ����
                if not stripped or stripped.startswith('#'):
                    fixed_lines.append(line)
                    i += 1
                    continue

                # ���� ���� ���� �鿩����
                current_indent = len(line) - len(stripped)

                # ���� ���� Ű���� ó��
                if stripped.startswith(('else:', 'elif ', 'except', 'finally:')):
                    if len(indent_stack) > 1:
                        indent_stack.pop()
                    expected_indent = indent_stack[-1]
                elif stripped.startswith(('return ', 'break', 'continue', 'pass')):
                    expected_indent = indent_stack[-1] + 4
                else:
                    expected_indent = indent_stack[-1]

                # �鿩���� ����
                if current_indent != expected_indent and current_indent % 4 == 0:
                    fixed_line = ' ' * expected_indent + stripped
                    fixed_lines.append(fixed_line)
                    fixed_count += 1
                else:
                    fixed_lines.append(line)

                # ���� ���� Ű���� ó��
                if stripped.endswith(':'):
                    if not stripped.startswith(('class ', 'def ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:')):
                        indent_stack.append(expected_indent + 4)

                i += 1

            # ���� ����
            new_content = ''.join(fixed_lines)
            with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(new_content)

            # ���� �˻�
            try:
                compile(new_content, str(file_path), 'exec')
                return True, fixed_count
            except SyntaxError:
                return False, fixed_count

        except Exception as e:
            print(f"[ERROR] {file_path.name}: {e}")
            return False, 0

    def remove_unused_imports(self, file_path: Path) -> Tuple[bool, int]:
        """������� �ʴ� import ����"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            # ���Ǵ� �̸� ����
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    # ���.�Ӽ� ����
                    parts = []
                    n = node
                    while isinstance(n, ast.Attribute):
                        parts.insert(0, n.attr)
                        n = n.value
                    if isinstance(n, ast.Name):
                        parts.insert(0, n.id)
                        used_names.add(parts[0])

            # Import �м�
            lines = content.splitlines()
            import_lines_to_remove = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.asname:
                            if alias.asname not in used_names:
                                import_lines_to_remove.add(node.lineno - 1)
                        else:
                            if alias.name not in used_names:
                                import_lines_to_remove.add(node.lineno - 1)
                elif isinstance(node, ast.ImportFrom):
                    imported_names = [a.asname or a.name for a in node.names]
                    if not any(name in used_names for name in imported_names):
                        import_lines_to_remove.add(node.lineno - 1)

            # Import ����
            if import_lines_to_remove:
                new_lines = [line for i, line in enumerate(lines) if i not in import_lines_to_remove]
                new_content = '\n'.join(new_lines) + '\n'
                with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(new_content)
                return True, len(import_lines_to_remove)

            return True, 0

        except Exception as e:
            print(f"[ERROR] {file_path.name}: {e}")
            return False, 0

    def optimize_file(self, file_path: Path) -> Dict:
        """���� ����ȭ"""
        result = {
            "file": str(file_path),
            "indentation_fixed": 0,
            "unused_imports_removed": 0,
            "success": False
        }

        # 1. �ε����̼� ����
        success, fixed = self.fix_indentation(file_path)
        result["indentation_fixed"] = fixed
        if not success:
            return result

        # 2. ������� �ʴ� import ����
        success, removed = self.remove_unused_imports(file_path)
        result["unused_imports_removed"] = removed

        result["success"] = True
        return result

    def find_all_python_files(self, root: Path = None) -> List[Path]:
        """��� Python ���� ã��"""
        if root is None:
            root = self.project_root

        exclude_dirs = {'__pycache__', '.git', 'node_modules', '.venv', 'venv',
                       'build', 'dist', '.pytest_cache', '.mypy_cache', 'local_training'}

        python_files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
            for filename in filenames:
                if filename.endswith('.py'):
                    python_files.append(Path(dirpath) / filename)
        return python_files

    def optimize_project(self, target_files: List[Path] = None) -> Dict:
        """������Ʈ ����ȭ"""
        if target_files is None:
            # ��� Python ���� ã��
            target_files = self.find_all_python_files()

        results = []
        for file_path in target_files:
            if file_path.exists():
                print(f"����ȭ ��: {file_path.name}...")
                result = self.optimize_file(file_path)
                results.append(result)

                self.stats["files_processed"] += 1
                self.stats["indentation_fixed"] += result["indentation_fixed"]
                self.stats["unused_imports_removed"] += result["unused_imports_removed"]

        return {
            "stats": self.stats,
            "results": results
        }


def main():
    """���� �Լ�"""
    import argparse

    parser = argparse.ArgumentParser(description="�ҽ��ڵ� ����ȭ ����")
    parser.add_argument("--file", type=str, help="Ư�� ���ϸ� ����ȭ")
    parser.add_argument("--all", action="store_true", help="��� Python ���� ����ȭ")
    parser.add_argument("--dry-run", action="store_true", help="���� �������� �ʰ� �˻縸 ����")

    args = parser.parse_args()

    optimizer = SourceOptimizer()

    if args.file:
        file_path = Path(args.file)
        if file_path.exists():
            print(f"����ȭ ��: {file_path}...")
            result = optimizer.optimize_file(file_path)
            print(f"���: {result}")
        else:
            print(f"������ ã�� �� �����ϴ�: {file_path}")
    elif args.all:
        print("��ü ������Ʈ ����ȭ ��...")
        print("�� �۾��� �ð��� �ɸ� �� �ֽ��ϴ�...")
        result = optimizer.optimize_project()
        print("\n" + "=" * 70)
        print("����ȭ �Ϸ�!")
        print("=" * 70)
        print(f"ó���� ����: {result['stats']['files_processed']}��")
        print(f"������ �ε����̼�: {result['stats']['indentation_fixed']}��")
        print(f"���ŵ� unused imports: {result['stats']['unused_imports_removed']}��")
        print("=" * 70)
    else:
        result = optimizer.optimize_project()
        print("\n" + "=" * 70)
        print("����ȭ �Ϸ�!")
        print("=" * 70)
        print(f"ó���� ����: {result['stats']['files_processed']}��")
        print(f"������ �ε����̼�: {result['stats']['indentation_fixed']}��")
        print(f"���ŵ� unused imports: {result['stats']['unused_imports_removed']}��")
        print("=" * 70)


if __name__ == "__main__":
    main()
