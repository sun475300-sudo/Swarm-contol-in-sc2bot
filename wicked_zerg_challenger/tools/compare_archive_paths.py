#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare two archive directories to understand their differences
"""

from pathlib import Path
import json

def main():
    print("\n" + "="*70)
    print("ARCHIVE DIRECTORY COMPARISON")
    print("="*70 + "\n")
    
    # Path 1: Project internal replays_archive
    path1 = Path("wicked_zerg_challenger/replays_archive")
    
    # Path 2: External D:/replays/archive
    path2 = Path("D:/replays/archive")
    
    print("[1] Project Internal Archive")
    print(f"    Path: {path1.absolute()}")
    if path1.exists():
        folders = [f for f in path1.iterdir() if f.is_dir()]
        print(f"    Status: ? Exists")
        print(f"    Training folders: {len(folders)}")
        if folders:
            sample_folder = folders[0]
            print(f"    Sample folder: {sample_folder.name}")
            files = list(sample_folder.glob("*"))
            print(f"    Files in sample folder: {len(files)}")
            for f in files[:5]:
                print(f"      - {f.name}")
            
            # Check file types
            json_files = [f for f in files if f.suffix == '.json']
            print(f"    JSON files: {len(json_files)}")
            if json_files:
                try:
                    with open(json_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"    Sample JSON keys: {list(data.keys())[:5]}")
                except:
                    pass
    else:
        print(f"    Status: ? Not found")
    
    print("\n[2] External Archive (D:/replays/archive)")
    print(f"    Path: {path2}")
    if path2.exists():
        folders = [f for f in path2.iterdir() if f.is_dir()]
        print(f"    Status: ? Exists")
        print(f"    Training folders: {len(folders)}")
        if folders:
            sample_folder = folders[-1]  # Most recent
            print(f"    Sample folder: {sample_folder.name}")
            files = list(sample_folder.glob("*"))
            print(f"    Files in sample folder: {len(files)}")
            for f in files[:5]:
                print(f"      - {f.name}")
            
            # Check file types
            json_files = [f for f in files if f.suffix == '.json']
            print(f"    JSON files: {len(json_files)}")
            if json_files:
                try:
                    with open(json_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"    Sample JSON keys: {list(data.keys())[:5]}")
                except:
                    pass
    else:
        print(f"    Status: ? Not found")
    
    print("\n" + "="*70)
    print("DIFFERENCE SUMMARY")
    print("="*70)
    print("\n[Path 1] wicked_zerg_challenger/replays_archive")
    print("  Purpose: Project internal archive (fallback location)")
    print("  Usage: Used when D:/replays/replays is not available")
    print("  Content: Training status files (instance_*_status.json)")
    print("  Priority: Low (fallback only)")
    
    print("\n[Path 2] D:/replays/archive")
    print("  Purpose: External archive for training results")
    print("  Usage: Primary location for learned_build_orders.json")
    print("  Content: Learned parameters and build orders")
    print("  Priority: High (primary output location)")
    print("  Format: training_YYYYMMDD_HHMMSS/learned_build_orders.json")
    
    print("\n[Key Difference]")
    print("  - Path 1: Old/legacy location, contains training status")
    print("  - Path 2: Current/active location, contains learned parameters")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
