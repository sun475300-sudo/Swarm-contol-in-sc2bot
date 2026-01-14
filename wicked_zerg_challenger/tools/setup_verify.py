#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zerg Data Pipeline - Environment Check
"""

import sys
from pathlib import Path


def main():
    print("\n" + "="*80)
    print("ZERG DATA PIPELINE - ENVIRONMENT CHECK")
    print("="*80 + "\n")

    # Python version
    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 8):
        print("WARNING: Python 3.8+ required")
        return 1

    # Check files
    base = Path(__file__).parent
    print(f"\nBase folder: {base}\n")

    files_to_check = [
        ("fetch_replay_links.py", "Link fetcher"),
        ("replay_lifecycle_manager.py", "Lifecycle manager"),
        ("data/zerg_players.json", "Pro player DB"),
    ]

    print("Files:")
    for fname, desc in files_to_check:
        fpath = base / fname
        status = "OK" if fpath.exists() else "MISSING"
        print(f"  [{status}] {fname:<35} ({desc})")

    # Check folders
    folders = [
        ("data", "Data storage"),
        ("logs", "Log storage"),
    ]

    print("\nFolders:")
    for fname, desc in folders:
        fpath = base / fname
        if not fpath.exists():
            fpath.mkdir(exist_ok=True)
        status = "OK"
        print(f"  [{status}] {fname:<35} ({desc})")

    # Quick test import
    print("\nPackages:")
    packages = [
        ("pathlib", "Standard"),
        ("json", "Standard"),
        ("zipfile", "Standard"),
        ("shutil", "Standard"),
        ("sqlite3", "Standard"),
        ("sc2reader", "External"),
        ("torch", "External"),
        ("numpy", "External"),
    ]

    for pkg, category in packages:
        try:
            __import__(pkg)
            print(f"  [OK] {pkg:<35} ({category})")
        except ImportError:
            print(f"  [FAIL] {pkg:<35} ({category})")

    # CRITICAL: Check replay directory access permissions
    print("\nReplay Directory Permissions:")
    replay_dir = Path("D:/replays/replays")
    if replay_dir.exists():
        try:
            # Test write permission
            test_file = replay_dir / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            print(f"  [OK] D:/replays/replays - Read/Write access")
        except PermissionError:
            print(f"  [FAIL] D:/replays/replays - No write permission")
        except Exception as e:
            print(f"  [WARNING] D:/replays/replays - Access check failed: {e}")
    else:
        print(f"  [INFO] D:/replays/replays - Directory does not exist (will be created)")

    # CRITICAL: Check model storage directory permissions
    print("\nModel Storage Permissions:")
    local_training = base.parent / "local_training"
    models_dir = local_training / "models"
    if models_dir.exists():
        try:
            test_file = models_dir / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            print(f"  [OK] local_training/models - Read/Write access")
        except PermissionError:
            print(f"  [FAIL] local_training/models - No write permission")
        except Exception as e:
            print(f"  [WARNING] local_training/models - Access check failed: {e}")
    else:
        try:
            models_dir.mkdir(parents=True, exist_ok=True)
            print(f"  [OK] local_training/models - Created successfully")
        except Exception as e:
            print(f"  [FAIL] local_training/models - Cannot create: {e}")

    # CRITICAL: Check StarCraft II replay folder access
    print("\nStarCraft II Integration:")
    sc2_replay_paths = [
        Path.home() / "Documents" / "StarCraft II" / "Accounts",
        Path("C:/Users") / "Public" / "Documents" / "StarCraft II" / "Accounts",
    ]
    sc2_found = False
    for sc2_path in sc2_replay_paths:
        if sc2_path.exists():
            print(f"  [OK] StarCraft II found: {sc2_path}")
            sc2_found = True
            break
    if not sc2_found:
        print(f"  [WARNING] StarCraft II installation not detected in common locations")

    print("\n" + "="*80)
    print("SETUP CHECK COMPLETE")
    print("="*80 + "\n")

    print("Next steps:")
    print("  1. Modify DOWNLOAD_DIR in replay_lifecycle_manager.py (line 26)")
    print("  2. Run: python fetch_replay_links.py --mode all")
    print("  3. Download ZIP files from browser links")
    print("  4. Run: python replay_lifecycle_manager.py --extract")
    print("  5. Run training in local_training folder\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
