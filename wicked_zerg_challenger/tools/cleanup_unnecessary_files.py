# -*- coding: utf-8 -*-
"""
���ʿ��� ���� ���� ����

�Ʒ�/���࿡ ���ʿ��� ���ϵ��� �����մϴ�.
"""

import os
import shutil
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent


def find_backup_files() -> List[Path]:
    """��� ����(.bak) ã��"""
 backup_files = []
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
 # ������ ���丮 ���͸�
 dirs[:] = [d for d in dirs if d not in {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'models', 'logs', 'stats'
 }]
 
 for file in files:
            if file.endswith('.bak'):
 backup_files.append(Path(root) / file)
 
 return backup_files


def find_cache_files() -> List[Path]:
    """ĳ�� ����(.pyc, .pyo) ã��"""
 cache_files = []
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
 # __pycache__ ���丮 ã��
        if '__pycache__' in dirs:
            cache_dir = Path(root) / '__pycache__'
 for file in (cache_dir).iterdir():
 if file.is_file():
 cache_files.append(file)
            dirs.remove('__pycache__')
 
 # .pyc, .pyo ���� ã��
 for file in files:
            if file.endswith(('.pyc', '.pyo')):
 cache_files.append(Path(root) / file)
 
 return cache_files


def delete_files(file_paths: List[Path], dry_run: bool = True) -> int:
    """���� ����"""
 deleted_count = 0
 
 for file_path in file_paths:
 try:
 if file_path.exists():
 if not dry_run:
 file_path.unlink()
 deleted_count += 1
                print(f"{'[DRY RUN] ' if dry_run else ''}����: {file_path.relative_to(PROJECT_ROOT)}")
 except Exception as e:
            print(f"[ERROR] ���� ����: {file_path.relative_to(PROJECT_ROOT)} - {e}")
 
 return deleted_count


def delete_directories(dir_paths: List[Path], dry_run: bool = True) -> int:
    """���丮 ����"""
 deleted_count = 0
 
 for dir_path in dir_paths:
 try:
 if dir_path.exists() and dir_path.is_dir():
 if not dry_run:
 shutil.rmtree(dir_path)
 deleted_count += 1
                print(f"{'[DRY RUN] ' if dry_run else ''}����: {dir_path.relative_to(PROJECT_ROOT)}")
 except Exception as e:
            print(f"[ERROR] ���� ����: {dir_path.relative_to(PROJECT_ROOT)} - {e}")
 
 return deleted_count


def main():
    """���� �Լ�"""
 import argparse
 
    parser = argparse.ArgumentParser(description="���ʿ��� ���� ���� ����")
    parser.add_argument("--execute", action="store_true", help="������ ���� (�⺻��: dry-run)")
    parser.add_argument("--backup-only", action="store_true", help="��� ����(.bak)�� ����")
    parser.add_argument("--cache-only", action="store_true", help="ĳ�� ���ϸ� ����")
 
 args = parser.parse_args()
 
 dry_run = not args.execute
 
    print("=" * 70)
    print("���ʿ��� ���� ���� ����")
    print("=" * 70)
 print()
 
 if dry_run:
        print("[DRY RUN] ������ �������� �ʰ� Ȯ�θ� �մϴ�.")
        print("������ �����Ϸ��� --execute �ɼ��� ����ϼ���.")
 print()
 
 total_deleted = 0
 
 # ��� ���� ����
 if not args.cache_only:
        print("��� ����(.bak) ã�� ��...")
 backup_files = find_backup_files()
        print(f"  - �߰�: {len(backup_files)}��")
 
 if backup_files:
 print()
 deleted = delete_files(backup_files, dry_run=dry_run)
 total_deleted += deleted
 print()
 
 # ĳ�� ���� ����
 if not args.backup_only:
        print("ĳ�� ����(.pyc, .pyo, __pycache__) ã�� ��...")
 cache_files = find_cache_files()
        print(f"  - �߰�: {len(cache_files)}��")
 
 if cache_files:
 print()
 deleted = delete_files(cache_files, dry_run=dry_run)
 total_deleted += deleted
 print()
 
 # __pycache__ ���丮 ����
 pycache_dirs = []
 for root, dirs, files in os.walk(PROJECT_ROOT):
            if '__pycache__' in dirs:
                pycache_dirs.append(Path(root) / '__pycache__')
 
 if pycache_dirs:
            print(f"__pycache__ ���丮: {len(pycache_dirs)}��")
 deleted = delete_directories(pycache_dirs, dry_run=dry_run)
 total_deleted += deleted
 print()
 
    print("=" * 70)
    print(f"�� {total_deleted}�� ����/���丮 {'���� �Ϸ�' if not dry_run else '���� ����'}")
    print("=" * 70)
 
 if dry_run:
 print()
        print("[TIP] ������ �����Ϸ��� ���� ������ �����ϼ���:")
        print("  python tools/cleanup_unnecessary_files.py --execute")


if __name__ == "__main__":
 main()