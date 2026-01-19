# -*- coding: utf-8 -*-
"""
Game training execution status checker

Checks if game training is running and if statistics are being updated.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Union, Any

def check_processes():
    """Check running processes"""
    try:
        import psutil
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                proc_info = proc.info
                name = proc_info['name'].lower()
                cmdline_list: List[str] = proc_info.get('cmdline', []) or []
                # Ensure all elements are strings
                cmdline_list = [str(c) for c in cmdline_list if c is not None]
                cmdline = ' '.join(cmdline_list) if cmdline_list else ''
                
                # Check Python processes
                if 'python' in name:
                    if 'run_with_training' in cmdline or 'training' in cmdline.lower():
                        processes.append({
                            'type': 'Training',
                            'pid': proc_info['pid'],
                            'name': proc_info['name'],
                            'cmdline': cmdline[:100]
                        })
                
                # Check SC2 processes
                if 'sc2' in name or 'starcraft' in name:
                    processes.append({
                        'type': 'SC2',
                        'pid': proc_info['pid'],
                        'name': proc_info['name']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return processes
    except ImportError:
        return []

def check_stats_file() -> Optional[Dict]:
    """Check statistics file"""
    script_dir = Path(__file__).parent.parent
    stats_file = script_dir / "local_training" / "scripts" / "training_session_stats.json"
    
    if not stats_file.exists():
        return None
    
    try:
        # File info
        file_stat = stats_file.stat()
        last_modified = datetime.fromtimestamp(file_stat.st_mtime)
        age = datetime.now() - last_modified
        
        # File content
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
        
        return {
            'exists': True,
            'path': str(stats_file),
            'last_modified': last_modified.isoformat(),
            'age_minutes': age.total_seconds() / 60,
            'size_kb': file_stat.st_size / 1024,
            'stats': stats
        }
    except Exception as e:
        return {'exists': True, 'error': str(e)}

def main():
    """Main function"""
    print("=" * 70)
    print("Game Training Execution Status Check")
    print("=" * 70)
    print()
    
    # 1. Process check
    print("1. Process Check")
    print("-" * 70)
    processes = check_processes()
    if processes:
        for proc in processes:
            print(f"  [{proc['type']}] PID: {proc['pid']}, Name: {proc['name']}")
            if 'cmdline' in proc:
                print(f"    Command: {proc['cmdline']}")
    else:
        print("  No game training process found.")
    print()
    
    # 2. Statistics file check
    print("2. Statistics File Check")
    print("-" * 70)
    stats_info = check_stats_file()
    if stats_info:
        if 'error' in stats_info:
            print(f"  [ERROR] Failed to read stats file: {stats_info['error']}")
        else:
            print(f"  File path: {stats_info['path']}")
            print(f"  Last modified: {stats_info['last_modified']}")
            print(f"  Age: {stats_info['age_minutes']:.1f} minutes ago")
            print(f"  File size: {stats_info['size_kb']:.2f} KB")
            
            stats = stats_info['stats']
            session_stats = stats.get('session_stats', {})
            game_history = stats.get('game_history', [])
            
            print()
            print("  Statistics:")
            print(f"    Total games: {session_stats.get('total_games', 0)}")
            print(f"    Win rate: {session_stats.get('win_rate', 0):.2f}%")
            print(f"    Current difficulty: {session_stats.get('current_difficulty', 'Unknown')}")
            print(f"    Game history: {len(game_history)} games")
            
            if game_history:
                latest = game_history[-1]
                print()
                print("  Latest game:")
                print(f"    Game ID: #{latest.get('game_id', '?')}")
                print(f"    Result: {latest.get('result', 'Unknown')}")
                print(f"    Time: {latest.get('timestamp', 'Unknown')}")
                print(f"    Map: {latest.get('map_name', 'Unknown')}")
                print(f"    Opponent: {latest.get('opponent_race', 'Unknown')}")
                print(f"    Difficulty: {latest.get('difficulty', 'Unknown')}")
            
            # Statistics update status
            age_minutes = stats_info['age_minutes']
            if age_minutes < 5:
                print()
                print("  [OK] Statistics updated recently.")
            elif age_minutes < 60:
                print()
                print(f"  [WARNING] Statistics updated {age_minutes:.1f} minutes ago.")
            else:
                print()
                print(f"  [ERROR] Statistics updated {age_minutes/60:.1f} hours ago. Game may not be running.")
    else:
        print("  Statistics file not found.")
    print()
    
    # 3. Recommendations
    print("3. Recommendations")
    print("-" * 70)
    if not processes:
        print("  [WARNING] Game training does not appear to be running.")
        print("  -> Run: python run_with_training.py")
    else:
        print("  [OK] Game training process is running.")
    
    if stats_info and 'age_minutes' in stats_info:
        if stats_info['age_minutes'] > 60:
            print("  [WARNING] Statistics are outdated.")
            print("  -> Game may not be completing or statistics saving may have issues.")
        else:
            print("  [OK] Statistics are up to date.")
    
    print()
    print("=" * 70)
    print("Real-time monitoring: python tools\\monitor_training_progress.py 5")
    print("=" * 70)

if __name__ == "__main__":
    main()
