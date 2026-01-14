#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Learning Progress and Build Order Sequence Verification Tool
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

def load_json_safe(file_path: Path) -> Optional[Dict]:
    """Safely load JSON file"""
    if not file_path.exists():
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] Failed to load {file_path}: {e}")
        return None

def check_strategy_db(replay_dir: Path) -> Dict[str, Any]:
    """Check strategy_db.json"""
    strategy_db_path = replay_dir / "strategy_db.json"
    
    print("\n" + "="*70)
    print("Strategy Database (strategy_db.json) Analysis")
    print("="*70)
    
    if not strategy_db_path.exists():
        print(f"File not found: {strategy_db_path}")
        return {}
    
    data = load_json_safe(strategy_db_path)
    if not data:
        return {}
    
    build_orders = {k: v for k, v in data.items() if k.startswith("build_order")}
    
    print(f"File location: {strategy_db_path}")
    print(f"Total strategies: {len(build_orders)}")
    
    matchup_stats = defaultdict(int)
    for key in build_orders.keys():
        if "_ZvT_" in key:
            matchup_stats["ZvT"] += 1
        elif "_ZvP_" in key:
            matchup_stats["ZvP"] += 1
        elif "_ZvZ_" in key:
            matchup_stats["ZvZ"] += 1
    
    print("\nMatchup statistics:")
    for matchup, count in sorted(matchup_stats.items()):
        print(f"  - {matchup}: {count}")
    
    print("\nBuild order sequence verification:")
    sequential_issues = []
    
    for key, strategy in list(build_orders.items())[:20]:
        timings = strategy.get("timings", {})
        if not timings:
            continue
        
        timing_values = sorted([v for v in timings.values() if isinstance(v, (int, float))])
        
        is_sequential = all(timing_values[i] <= timing_values[i+1] for i in range(len(timing_values)-1))
        
        if not is_sequential:
            sequential_issues.append({
                "key": key,
                "timings": timing_values,
            })
    
    if sequential_issues:
        print(f"  WARNING: Sequence issues found: {len(sequential_issues)}")
        for issue in sequential_issues[:5]:
            print(f"    - {issue['key']}: {issue['timings']}")
    else:
        print("  OK: Build orders are learned in correct sequence")
    
    return {
        "total_strategies": len(build_orders),
        "matchup_stats": dict(matchup_stats),
        "sequential_issues": len(sequential_issues)
    }

def check_learned_build_orders() -> Dict[str, Any]:
    """Check learned_build_orders.json"""
    print("\n" + "="*70)
    print("Learned Build Orders Analysis")
    print("="*70)
    
    possible_paths = [
        Path("local_training/scripts/learned_build_orders.json"),
        Path("D:/replays/archive"),
        Path("local_training/learned_build_orders.json"),
    ]
    
    found_files = []
    for path in possible_paths:
        if path.is_dir():
            training_dirs = sorted(path.glob("training_*"), reverse=True)
            if training_dirs:
                latest_file = training_dirs[0] / "learned_build_orders.json"
                if latest_file.exists():
                    found_files.append(latest_file)
        elif path.exists():
            found_files.append(path)
    
    if not found_files:
        print("learned_build_orders.json file not found")
        print("\nChecked paths:")
        for path in possible_paths:
            print(f"  - {path}")
        return {}
    
    latest_file = found_files[0]
    print(f"File location: {latest_file}")
    
    data = load_json_safe(latest_file)
    if not data:
        return {}
    
    learned_params = data.get("learned_parameters", {})
    build_orders = data.get("build_orders", [])
    source_replays = data.get("source_replays", 0)
    
    print(f"Learned parameters: {len(learned_params)}")
    print(f"Build order samples: {len(build_orders)}")
    print(f"Source replays: {source_replays}")
    
    print("\nBuild order sequence verification:")
    sequential_count = 0
    non_sequential_count = 0
    
    for bo in build_orders[:20]:
        timings = bo.get("timings", {})
        if not timings:
            continue
        
        timing_values = sorted([v for v in timings.values() if isinstance(v, (int, float))])
        
        is_sequential = all(timing_values[i] <= timing_values[i+1] for i in range(len(timing_values)-1))
        
        if is_sequential:
            sequential_count += 1
        else:
            non_sequential_count += 1
    
    total_checked = sequential_count + non_sequential_count
    if total_checked > 0:
        sequential_rate = (sequential_count / total_checked) * 100
        print(f"  OK: Sequential build orders: {sequential_count}/{total_checked} ({sequential_rate:.1f}%)")
        if non_sequential_count > 0:
            print(f"  WARNING: Non-sequential build orders: {non_sequential_count}/{total_checked}")
    
    if learned_params:
        print("\nLearned parameters sample (first 10):")
        for i, (key, value) in enumerate(list(learned_params.items())[:10]):
            print(f"  {i+1}. {key}: {value}")
    
    return {
        "learned_params_count": len(learned_params),
        "build_orders_count": len(build_orders),
        "source_replays": source_replays,
        "sequential_rate": (sequential_count / total_checked * 100) if total_checked > 0 else 0
    }

def check_learning_tracking(replay_dir: Path) -> Dict[str, Any]:
    """Check learning tracking file"""
    print("\n" + "="*70)
    print("Learning Tracking Analysis")
    print("="*70)
    
    tracking_file = replay_dir / ".learning_tracking.json"
    
    if not tracking_file.exists():
        print(f"File not found: {tracking_file}")
        return {}
    
    data = load_json_safe(tracking_file)
    if not data:
        return {}
    
    print(f"File location: {tracking_file}")
    
    total_replays = len(data)
    completed_replays = sum(1 for v in data.values() if isinstance(v, dict) and v.get("count", 0) >= 5)
    in_progress = total_replays - completed_replays
    
    print(f"Total replays: {total_replays}")
    print(f"Completed replays (5+ iterations): {completed_replays}")
    print(f"In progress: {in_progress}")
    
    phase_stats = defaultdict(int)
    for key, value in data.items():
        if isinstance(value, dict):
            phase = value.get("phase", "unknown")
            phase_stats[phase] += 1
    
    if phase_stats:
        print("\nLearning phase statistics:")
        for phase, count in sorted(phase_stats.items()):
            print(f"  - {phase}: {count}")
    
    return {
        "total_replays": total_replays,
        "completed_replays": completed_replays,
        "in_progress": in_progress
    }

def main():
    """Main function"""
    print("="*70)
    print("Learning Progress and Build Order Sequence Verification")
    print("="*70)
    
    replay_dir = Path("D:/replays/replays")
    if not replay_dir.exists():
        print(f"Replay directory not found: {replay_dir}")
        print("Checking other paths...")
        replay_dir = Path("replays")
    
    if not replay_dir.exists():
        print("Replay directory not found.")
        return
    
    print(f"\nReplay directory: {replay_dir}")
    
    strategy_stats = check_strategy_db(replay_dir)
    learned_stats = check_learned_build_orders()
    tracking_stats = check_learning_tracking(replay_dir)
    
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    
    if strategy_stats:
        print(f"Strategy database: {strategy_stats.get('total_strategies', 0)} strategies")
        if strategy_stats.get('sequential_issues', 0) > 0:
            print(f"WARNING: Sequence issues: {strategy_stats['sequential_issues']} found")
        else:
            print("Build order sequence: OK")
    
    if learned_stats:
        print(f"Learned parameters: {learned_stats.get('learned_params_count', 0)}")
        print(f"Build order samples: {learned_stats.get('build_orders_count', 0)}")
        if learned_stats.get('sequential_rate', 0) > 0:
            print(f"Sequence accuracy: {learned_stats['sequential_rate']:.1f}%")
    
    if tracking_stats:
        print(f"Completed replays: {tracking_stats.get('completed_replays', 0)}")
        print(f"In progress: {tracking_stats.get('in_progress', 0)}")
    
    print("\n" + "="*70)
    print("Verification complete!")
    print("="*70)

if __name__ == "__main__":
    main()
