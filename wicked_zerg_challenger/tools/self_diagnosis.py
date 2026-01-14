#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self-Diagnosis Script for Replay Learning System
"""

import json
import os
from pathlib import Path
from datetime import datetime

def main():
    print("\n" + "="*70)
    print("REPLAY LEARNING SYSTEM - SELF DIAGNOSIS")
    print("="*70 + "\n")
    
    replay_dir = Path("D:/replays/replays")
    
    # 1. Check replay directory
    print("[1] Replay Directory Status")
    print(f"    Path: {replay_dir}")
    if replay_dir.exists():
        replay_files = list(replay_dir.glob("*.SC2Replay"))
        print(f"    Status: ? Exists")
        print(f"    Replay files: {len(replay_files)}")
    else:
        print(f"    Status: ? Not found")
        print(f"    Replay files: 0")
    
    # 2. Check strategy_db.json
    print("\n[2] Strategy Database Status")
    strategy_db_path = replay_dir / "strategy_db.json"
    if strategy_db_path.exists():
        try:
            with open(strategy_db_path, 'r', encoding='utf-8') as f:
                strategy_db = json.load(f)
            
            # CRITICAL: strategy_db.json structure is flat - strategies are top-level keys
            # Keys are like "build_order_ZvP_0_1", "build_order_ZvT_0_2", etc.
            strategy_keys = [k for k in strategy_db.keys() if k.startswith("build_order")]
            total_strategies = len(strategy_keys)
            
            # Find last updated time from strategy objects
            last_updated = "Unknown"
            if strategy_keys:
                # Get the most recent extracted_at timestamp
                extracted_times = []
                for key in strategy_keys:
                    strategy = strategy_db.get(key, {})
                    if isinstance(strategy, dict):
                        extracted_at = strategy.get("extracted_at")
                        if extracted_at:
                            extracted_times.append(extracted_at)
                
                if extracted_times:
                    # Sort and get the most recent
                    extracted_times.sort(reverse=True)
                    last_updated = extracted_times[0]
            
            # Also get matchup breakdown
            matchup_counts = {}
            for key in strategy_keys:
                strategy = strategy_db.get(key, {})
                if isinstance(strategy, dict):
                    matchup = strategy.get("matchup", "Unknown")
                    matchup_counts[matchup] = matchup_counts.get(matchup, 0) + 1
            
            print(f"    Status: ? Exists")
            print(f"    Total strategies: {total_strategies}")
            print(f"    Last updated: {last_updated}")
            if matchup_counts:
                print(f"    Matchup breakdown:")
                for matchup, count in sorted(matchup_counts.items()):
                    print(f"      {matchup}: {count}")
        except Exception as e:
            print(f"    Status: ? Exists but error reading: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"    Status: ? Not found")
    
    # 3. Check learning_status.json
    print("\n[3] Learning Status")
    status_file = replay_dir / "learning_status.json"
    if status_file.exists():
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            replays = status_data.get("replays", {})
            total = len(replays)
            completed = sum(1 for r in replays.values() if r.get("completed", False))
            in_progress = total - completed
            last_updated = status_data.get("_last_updated", "Unknown")
            print(f"    Status: ? Exists")
            print(f"    Total replays: {total}")
            print(f"    Completed (5+ iterations): {completed}")
            print(f"    In progress: {in_progress}")
            print(f"    Last updated: {last_updated}")
        except Exception as e:
            print(f"    Status: ? Exists but error reading: {e}")
    else:
        print(f"    Status: ? Not found")
    
    # 4. Check learning_log.txt
    print("\n[4] Learning Log")
    log_file = replay_dir / "learning_log.txt"
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"    Status: ? Exists")
            print(f"    Total lines: {len(lines)}")
            if lines:
                print(f"    Last entry: {lines[-1][:80]}...")
        except Exception as e:
            print(f"    Status: ? Exists but error reading: {e}")
    else:
        print(f"    Status: ? Not found")
    
    # 5. Check completed directory
    print("\n[5] Completed Replays Directory")
    completed_dir = replay_dir / "completed"
    if completed_dir.exists():
        completed_files = list(completed_dir.glob("*.SC2Replay"))
        print(f"    Status: ? Exists")
        print(f"    Completed replays: {len(completed_files)}")
    else:
        print(f"    Status: ? Not found")
    
    # 6. Check Python processes
    print("\n[6] Running Processes")
    try:
        import subprocess
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        python_processes = [line for line in result.stdout.split('\n') if 'python.exe' in line.lower()]
        python_count = len(python_processes) - 1  # -1 for header
        print(f"    Python processes: {python_count}")
        if python_count > 0:
            print(f"    Status: ? Python processes running")
        else:
            print(f"    Status: ? No Python processes found")
    except Exception as e:
        print(f"    Status: ? Error checking processes: {e}")
    
    # 7. Check code status
    print("\n[7] Code Status")
    script_path = Path(__file__).parent.parent / "local_training" / "scripts" / "replay_build_order_learner.py"
    if script_path.exists():
        print(f"    Status: ? Script exists")
        print(f"    Path: {script_path}")
        # Check auto-commit disabled
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if "Auto commit disabled" in content:
            print(f"    Auto-commit: ? Disabled (results saved only)")
        else:
            print(f"    Auto-commit: ? Status unknown")
    else:
        print(f"    Status: ? Script not found")
    
    # 8. Summary
    print("\n" + "="*70)
    print("DIAGNOSIS SUMMARY")
    print("="*70)
    print("\nSystem Components:")
    print("  ? Replay directory scanning")
    print("  ? Build order extraction")
    print("  ? Learning iteration tracking (min 5 iterations)")
    print("  ? Strategy database (strategy_db.json)")
    print("  ? Learning status tracking")
    print("  ? Auto-commit disabled (results saved only)")
    print("\nExpected Behavior:")
    print("  1. Scan replays from D:\\replays\\replays")
    print("  2. Extract build orders from each replay")
    print("  3. Learn each replay 5+ times (phase-based)")
    print("  4. Save strategies to strategy_db.json")
    print("  5. Save learned parameters to learned_build_orders.json")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
