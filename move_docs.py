# -*- coding: utf-8 -*-
"""Move project description files from wicked_zerg_challenger to root directory"""

import os
import shutil
from pathlib import Path

# Get project root
project_root = Path(__file__).parent
wicked_dir = project_root / "wicked_zerg_challenger"

# Files to move
files_to_move = [
    "README_한국어.md",
    "README_PROJECT_HISTORY.md",
    "PROJECT_HISTORY_AND_ISSUES_RESOLVED.md",
    "PROJECT_CLEANUP_COMPLETE.md",
    "프로젝트 설명문",
]

# Rename README.md to README_BOT.md to avoid conflict
readme_src = wicked_dir / "README.md"
readme_dst = wicked_dir / "README_BOT.md"

if readme_src.exists() and not readme_dst.exists():
    shutil.move(str(readme_src), str(readme_dst))
    print(f"? Renamed: {readme_src.name} -> {readme_dst.name}")

# Move files to root
moved_count = 0
for filename in files_to_move:
    src = wicked_dir / filename
    dst = project_root / filename
    
    if src.exists():
        if dst.exists():
            print(f"??  Skipping {filename} (already exists in root)")
        else:
            shutil.move(str(src), str(dst))
            print(f"? Moved: {filename}")
            moved_count += 1
    else:
        print(f"??  Not found: {src}")

print(f"\n? Total files moved: {moved_count}")
