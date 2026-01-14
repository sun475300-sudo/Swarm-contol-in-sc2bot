#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Code Quality Check
ºü¸¥ ÄÚµå Ç°Áú Á¡°Ë (ÁÖ¿ä ÆÄÀÏ¸¸)

ÁÖ¿ä Á¡°Ë Ç×¸ñ:
1. await ´©¶ô ¹®Á¦
2. ÁÖ¿ä ÆÄÀÏÀÇ ±âº» ¹®¹ý ¿À·ù
"""

import sys
from pathlib import Path

# ÇÁ·ÎÁ§Æ® ·çÆ®
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# ÁÖ¿ä Á¡°Ë ´ë»ó ÆÄÀÏ
MAIN_FILES = [
    "wicked_zerg_bot_pro.py",
    "production_manager.py",
    "economy_manager.py",
    "combat_manager.py",
]


def check_await_in_file(file_path: Path) -> list:
    """ÆÄÀÏ¿¡¼­ await ´©¶ô ¹®Á¦ Ã£±â"""
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
    """ºü¸¥ Á¡°Ë ½ÇÇà"""
    print("ºü¸¥ ÄÚµå Ç°Áú Á¡°Ë ½ÃÀÛ...\n")

    total_issues = 0
    for filename in MAIN_FILES:
        file_path = PROJECT_ROOT / filename
        if not file_path.exists():
            continue

        issues = check_await_in_file(file_path)
        if issues:
            print(f"?? {filename}: {len(issues)}°÷ ¹ß°ß")
            for line_num, line in issues[:3]:
                print(f"   Line {line_num}: {line[:60]}...")
            if len(issues) > 3:
                print(f"   ... ¿Ü {len(issues) - 3}°÷")
            total_issues += len(issues)
        else:
            print(f"? {filename}: ¹®Á¦ ¾øÀ½")

    print("\n" + "=" * 60)
    if total_issues == 0:
        print("? ¸ðµç ÁÖ¿ä ÆÄÀÏ Á¡°Ë Åë°ú!")
        return 0
    else:
        print(f"?? ÃÑ {total_issues}°÷ÀÇ ¹®Á¦ ¹ß°ß")
        print("ÀÚ¼¼ÇÑ Á¡°Ë: python tools/code_quality_check.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
