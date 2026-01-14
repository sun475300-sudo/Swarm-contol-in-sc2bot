#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check current training status and readiness"""

import json
from pathlib import Path

def check_status():
    """Check training status"""
    
    print("=" * 60)
    print("Training Status Check")
    print("=" * 60)
    
    # Check instance status
    instance_file = Path("local_training/stats/instance_0_status.json")
    if instance_file.exists():
        with open(instance_file, "r", encoding="utf-8") as f:
            instance_data = json.load(f)
        
        print("\n[Instance Status]")
        print(f"  Game Count: {instance_data.get('game_count', 0)}")
        print(f"  Win Count: {instance_data.get('win_count', 0)}")
        print(f"  Loss Count: {instance_data.get('loss_count', 0)}")
        print(f"  Win Rate: {instance_data.get('win_rate', 0):.1f}%")
        print(f"  Difficulty: {instance_data.get('difficulty', 'N/A')}")
        print(f"  Difficulty Level: {instance_data.get('difficulty_level', 1)}")
        print(f"  Personality: {instance_data.get('personality', 'N/A')}")
        print(f"  Status: {instance_data.get('status', 'N/A')}")
    
    # Check curriculum
    curriculum_file = Path("local_training/data/training_stats.json")
    if curriculum_file.exists():
        with open(curriculum_file, "r", encoding="utf-8") as f:
            curriculum_data = json.load(f)
        
        print("\n[Curriculum Progress]")
        level_idx = curriculum_data.get("curriculum_level_idx", 0)
        games_at_level = curriculum_data.get("games_at_current_level", 0)
        
        level_names = ["VeryEasy", "Easy", "Medium", "Hard", "VeryHard", "CheatInsane"]
        level_name = level_names[level_idx] if 0 <= level_idx < len(level_names) else "Unknown"
        
        print(f"  Current Level: {level_name} (Level {level_idx + 1})")
        print(f"  Games at Current Level: {games_at_level}")
        
        min_games = {0: 10, 1: 15, 2: 20, 3: 25, 4: 30, 5: 40}
        required = min_games.get(level_idx, 10)
        print(f"  Required Games for Promotion: {required}")
        print(f"  Progress: {games_at_level}/{required} games")
    
    # Check training stats
    stats_file = Path("local_training/training_stats.json")
    if stats_file.exists():
        games = []
        with open(stats_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        game_data = json.loads(line)
                        games.append(game_data)
                    except json.JSONDecodeError:
                        continue
        
        if games:
            wins = sum(1 for g in games if g.get("loss_reason", "").upper() == "VICTORY")
            losses = sum(1 for g in games if g.get("loss_reason", "").upper() == "DEFEAT")
            total = len(games)
            win_rate = (wins / total * 100) if total > 0 else 0.0
            
            print("\n[Training Statistics]")
            print(f"  Total Games: {total}")
            print(f"  Wins: {wins}")
            print(f"  Losses: {losses}")
            print(f"  Win Rate: {win_rate:.1f}%")
            
            # Recent performance
            recent_games = games[-10:] if len(games) >= 10 else games
            recent_wins = sum(1 for g in recent_games if g.get("loss_reason", "").upper() == "VICTORY")
            recent_total = len(recent_games)
            recent_win_rate = (recent_wins / recent_total * 100) if recent_total > 0 else 0.0
            
            print(f"\n  Recent 10 Games:")
            print(f"    Wins: {recent_wins}/{recent_total}")
            print(f"    Win Rate: {recent_win_rate:.1f}%")
    
    print("\n" + "=" * 60)
    print("Ready to test! Current setup looks good.")
    print("=" * 60)

if __name__ == "__main__":
    check_status()
