#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Code Quality Check
빠른 코드 품질 점검 (주요 파일만)

주요 점검 항목:
1. await 누락 문제
2. 주요 파일의 기본 문법 오류
"""

import sys
from pathlib import Path

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# 주요 점검 대상 파일
MAIN_FILES = [
    "wicked_zerg_bot_pro.py",
    "production_manager.py",
    "economy_manager.py",
    "combat_manager.py",
]


def check_await_in_file(file_path: Path) -> list:
    """파일에서 await 누락 문제 찾기"""
    issues = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        in_async = False
        for line_num, line in enumerate(lines, 1):
            if "async def" in line:
                in_async = True
            elif line.strip().startswith("def ") and in_async:
                in_async = False

            if in_async and ".train(" in line and "await" not in line:
                if not line.strip().startswith("#"):
                    issues.append((line_num, line.strip()))

    except Exception as e:
        print(f"[ERROR] {file_path}: {e}", file=sys.stderr)

    return issues


def main():
    """빠른 점검 실행"""
    print("빠른 코드 품질 점검 시작...\n")

    total_issues = 0
    for filename in MAIN_FILES:
        file_path = PROJECT_ROOT / filename
        if not file_path.exists():
            continue

        issues = check_await_in_file(file_path)
        if issues:
            print(f"?? {filename}: {len(issues)}곳 발견")
            for line_num, line in issues[:3]:
                print(f"   Line {line_num}: {line[:60]}...")
            if len(issues) > 3:
                print(f"   ... 외 {len(issues) - 3}곳")
            total_issues += len(issues)
        else:
            print(f"? {filename}: 문제 없음")

    print("\n" + "=" * 60)
    if total_issues == 0:
        print("? 모든 주요 파일 점검 통과!")
        return 0
    else:
        print(f"?? 총 {total_issues}곳의 문제 발견")
        print("자세한 점검: python tools/code_quality_check.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
