#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
�ΰ� ���� �˻� ����

Git Ŀ�� ���� �ΰ� ����(API Ű, ��й�ȣ ��)�� ���ԵǾ� �ִ��� �˻��մϴ�.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Set

# �ΰ� ���� ����
SENSITIVE_PATTERNS = [
    # API Keys
    (r'sk-[A-Za-z0-9_-]{48,}', 'Manus AI API Key'),
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    (r'AIza[0-9A-Za-z_-]{35}', 'Google API Key'),
    (r'ghp_[A-Za-z0-9]{36}', 'GitHub Personal Access Token'),
    (r'xox[baprs]-[0-9a-zA-Z-]{10,48}', 'Slack Token'),
    (r'sk_live_[0-9a-zA-Z]{24,}', 'Stripe Live Secret Key'),

    # Private Keys
    (r'-----BEGIN.*PRIVATE KEY-----', 'Private Key'),
    (r'-----BEGIN RSA PRIVATE KEY-----', 'RSA Private Key'),
    (r'-----BEGIN DSA PRIVATE KEY-----', 'DSA Private Key'),
    (r'-----BEGIN EC PRIVATE KEY-----', 'EC Private Key'),

    # Passwords and Secrets
    (r'password\s*=\s*["\']([^"\']+)["\']', 'Password in code'),
    (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', 'API Key in code'),
    (r'secret\s*=\s*["\']([^"\']+)["\']', 'Secret in code'),
    (r'token\s*=\s*["\']([^"\']+)["\']', 'Token in code'),
    (r'apikey\s*[:=]\s*["\']([^"\']+)["\']', 'API Key (apikey)'),
]

# �˻翡�� ������ ���� ����
EXCLUDE_PATTERNS = [
    r'\.git/',
    r'__pycache__/',
    r'\.pyc$',
    r'\.pyo$',
    r'\.gitignore$',
    r'node_modules/',
    r'venv/',
    r'\.venv/',
    r'\.env$',
    r'\.env\.local$',
    r'api_keys/',
    r'secrets/',
]

# ���� ���� (false positive ����)
ALLOWED_PATTERNS = [
    r'your-api-key-here',
    r'your_api_key_here',
    r'YOUR_API_KEY',
    r'placeholder',
    r'example',
    r'test',
    r'sample',
    r'XXXX',
    r'XXXXXXXXXXXXXXXX',
]


def should_exclude_file(file_path: str) -> bool:
    """������ �˻翡�� ���ܵǾ�� �ϴ��� Ȯ��"""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True
    return False


def is_allowed_content(match: str) -> bool:
    """���� �������� Ȯ�� (false positive ����)"""
    match_lower = match.lower()
    for pattern in ALLOWED_PATTERNS:
        if pattern.lower() in match_lower:
            return True
    return False


def check_file(file_path: Path, patterns: List[Tuple[str, str]]) -> List[Tuple[int, str, str]]:
    """���Ͽ��� �ΰ� ���� �˻�"""
    issues = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                for pattern, description in patterns:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        matched_text = match.group(0)
                        # ���� �������� Ȯ��
                        if not is_allowed_content(matched_text):
                            # �ΰ� ���� �Ϻθ� ǥ�� (����)
                            display_text = matched_text[:20] + '...' if len(matched_text) > 20 else matched_text
                            issues.append((line_num, description, display_text))
    except Exception as e:
        print(f"??  ���� �б� ����: {file_path} - {e}", file=sys.stderr)

    return issues


def scan_directory(directory: Path, patterns: List[Tuple[str, str]]) -> dict:
    """���丮 ��ĵ"""
    results = {}
    total_issues = 0

    for file_path in directory.rglob('*'):
        if not file_path.is_file():
            continue

        # ���� ���� Ȯ��
        if should_exclude_file(str(file_path)):
            continue

        # .gitignore�� ���Ե� ������ ����
        try:
            rel_path = file_path.relative_to(directory)
            if any(part.startswith('.') for part in rel_path.parts):
                continue
        except ValueError:
            continue

        issues = check_file(file_path, patterns)
        if issues:
            results[str(file_path)] = issues
            total_issues += len(issues)

    return results, total_issues


def main():
    """���� �Լ�"""
    import argparse

    parser = argparse.ArgumentParser(description='�ΰ� ���� �˻� ����')
    parser.add_argument('--path', type=str, default='.', help='�˻��� ���丮 (�⺻��: ���� ���丮)')
    parser.add_argument('--fix', action='store_true', help='�ڵ����� ���� �õ� (����)')

    args = parser.parse_args()

    directory = Path(args.path).resolve()
    if not directory.exists():
        print(f"? ���丮�� ã�� �� �����ϴ�: {directory}", file=sys.stderr)
        sys.exit(1)

    print(f"? �ΰ� ���� �˻� ��: {directory}")
    print("=" * 70)

    results, total_issues = scan_directory(directory, SENSITIVE_PATTERNS)

    if total_issues == 0:
        print("? �ΰ� ������ �߰ߵ��� �ʾҽ��ϴ�.")
        sys.exit(0)

    print(f"\n? {total_issues}���� �ΰ� ������ �߰ߵǾ����ϴ�:\n")

    for file_path, issues in results.items():
        rel_path = Path(file_path).relative_to(directory)
        print(f"? {rel_path}")
        for line_num, description, match_text in issues:
            print(f"   �� {line_num}: {description}")
            print(f"          �߰�: {match_text}")
        print()

    print("=" * 70)
    print("\n??  ���� ����:")
    print("  1. API Ű, ��й�ȣ, ��ū�� �ڵ忡�� �����ϼ���")
    print("  2. ȯ�� ������ ���� ������ ����ϼ���")
    print("  3. .gitignore�� �ΰ� ���� ������ ���ԵǾ� �ִ��� Ȯ���ϼ���")
    print("  4. �̹� Ŀ�Ե� �ΰ� ������ �ִٸ� ��� ������ϼ���")
    print()

    sys.exit(1)


if __name__ == '__main__':
    main()
