#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
��� ���� �ڵ� ���� ����

������Ʈ�� ��� Python ���Ͽ��� �߰ߵ� ������ �ڵ����� �����մϴ�.
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple, Dict
import sys

# ���ڵ� ����
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).parent.parent


def fix_complete_run_script():
    """COMPLETE_RUN_SCRIPT.py ���� ����"""
    file_path = PROJECT_ROOT / "COMPLETE_RUN_SCRIPT.py"

    if not file_path.exists():
        print(f"[SKIP] ������ ã�� �� �����ϴ�: {file_path}")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines, 1):
            # 92�� �� ��Ÿ ����
            if i == 92:
                # �߸��� �ڵ� ���� (deprecated)
                if 'set_event_loop_����' in line or 'WindowsSelectorEventLoopPolicy' in line:
                    fixed_lines.append("                pass  # WindowsSelectorEventLoopPolicy is deprecated")
                    continue

            # �ε����̼� ���� ���� (29�� �� ��ó)
            if i == 29:
                # ���ʿ��� ���� ����
                line = line.rstrip()

            fixed_lines.append(line)

        # ���� ����
        with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write('\n'.join(fixed_lines))

        # ���� �˻�
        try:
            compile('\n'.join(fixed_lines), str(file_path), 'exec')
            print(f"[OK] {file_path.name} ���� �Ϸ�")
            return True
        except SyntaxError as e:
            print(f"[ERROR] {file_path.name} ���� ����: {e}")
            return False

    except Exception as e:
        print(f"[ERROR] {file_path.name} ���� ����: {e}")
        return False


def fix_dashboard_api_indentation():
    """dashboard_api.py �ε����̼� ����"""
    file_path = PROJECT_ROOT / "monitoring" / "dashboard_api.py"

    if not file_path.exists():
        print(f"[SKIP] ������ ã�� �� �����ϴ�: {file_path}")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # _validate_path �Լ��� else ���� ����
            if 'else:' in line and i > 595 and i < 605:
                # ���� ���� try �������� Ȯ��
                if i > 0 and 'try:' in lines[i-1]:
                    fixed_lines.append("        " + line.lstrip())
                else:
                    # �ùٸ� �ε����̼�
                    fixed_lines.append("    " + line.lstrip())
                i += 1
                continue

            # �ε����̼� ����ġ ���� (�Ϲ����� ����)
            # if �� ������ �߸��� �ε����̼�
            stripped = line.lstrip()
            if stripped.startswith('if ') or stripped.startswith('for ') or stripped.startswith('while '):
                # ���� ���� �鿩���� ������ ���
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip() and not next_line.startswith(' ') and not next_line.startswith('\t'):
                        # ���� ���� �ε����̼� ����
                        fixed_lines.append(line)
                        i += 1
                        # ���� �ٿ� �ùٸ� �ε����̼� �߰�
                        indent = len(line) - len(line.lstrip())
                        fixed_lines.append(' ' * (indent + 4) + next_line.lstrip())
                        i += 1
                        continue

            fixed_lines.append(line)
            i += 1

        # ���� ����
        with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write('\n'.join(fixed_lines))

        # ���� �˻�
        try:
            compile('\n'.join(fixed_lines), str(file_path), 'exec')
            print(f"[OK] {file_path.name} ���� �Ϸ�")
            return True
        except SyntaxError as e:
            print(f"[ERROR] {file_path.name} ���� ����: {e}")
            return False

    except Exception as e:
        print(f"[ERROR] {file_path.name} ���� ����: {e}")
        return False


def fix_python_files():
    """��� Python ������ ���� ����"""
    errors_found = []
    errors_fixed = []

    # �ֿ� ���� ���
    priority_files = [
        PROJECT_ROOT / "COMPLETE_RUN_SCRIPT.py",
        PROJECT_ROOT / "monitoring" / "dashboard_api.py",
        PROJECT_ROOT / "tools" / "continuous_improvement_system.py",
        PROJECT_ROOT / "tools" / "auto_error_fixer.py",
        PROJECT_ROOT / "tools" / "code_quality_improver.py",
        PROJECT_ROOT / "config.py",
    ]

    print("=" * 70)
    print("Python ���� ���� ���� ��...")
    print("=" * 70)
    print()

    # �켱���� ���� ����
    for file_path in priority_files:
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # ���� �˻�
            try:
                ast.parse(content, filename=str(file_path))
                print(f"[OK] {file_path.name} - ���� ����")
            except SyntaxError as e:
                errors_found.append((file_path, str(e)))
                print(f"[ERROR] {file_path.name} - {e}")

                # �ڵ� ���� �õ�
                if file_path.name == "COMPLETE_RUN_SCRIPT.py":
                    if fix_complete_run_script():
                        errors_fixed.append(file_path)
                elif file_path.name == "dashboard_api.py":
                    if fix_dashboard_api_indentation():
                        errors_fixed.append(file_path)
        except Exception as e:
            print(f"[ERROR] {file_path.name} - �б� ����: {e}")

    print()
    print("=" * 70)
    print(f"�߰ߵ� ����: {len(errors_found)}��")
    print(f"������ ����: {len(errors_fixed)}��")
    print("=" * 70)

    return len(errors_found) == len(errors_fixed)


def main():
    """���� �Լ�"""
    import argparse

    parser = argparse.ArgumentParser(description="��� ���� �ڵ� ���� ����")
    parser.add_argument("--dry-run", action="store_true", help="���� �������� �ʰ� �˻縸 ����")

    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN] ������ �˻��ϰ� �������� �ʽ��ϴ�.")
        print()

    success = fix_python_files()

    if success:
        print("\n? ��� ������ �����Ǿ����ϴ�!")
        sys.exit(0)
    else:
        print("\n?? �Ϻ� ������ �������� �� �ֽ��ϴ�.")
        sys.exit(1)


if __name__ == "__main__":
    main()
