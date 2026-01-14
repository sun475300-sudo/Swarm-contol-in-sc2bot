#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check win rate from training statistics"""

import json
from pathlib import Path

def analyze_win_rate():
    """Analyze win rate from training stats"""
    
    # Read training_stats.json (JSON Lines format)
    training_stats_file = Path("local_training/training_stats.json")
    games = []
    
    if training_stats_file.exists():
        with open(training_stats_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        game_data = json.loads(line)
                        games.append(game_data)
                    except json.JSONDecodeError:
                        continue
    
    # Calculate statistics
    total_games = len(games)
    wins = 0
    losses = 0
    draws = 0
    
    # Count by result
    for game in games:
        result = game.get("result", "").lower()
        loss_reason = game.get("loss_reason", "").upper()
        
        if loss_reason == "VICTORY" or result == "victory":
            wins += 1
        elif loss_reason == "DEFEAT" or result == "defeat":
            losses += 1
        else:
            draws += 1
    
    # Calculate win rate
    if total_games > 0:
        win_rate = (wins / total_games) * 100
    else:
        win_rate = 0.0
    
    # Print results
    print("=" * 60)
    print("Recent Win Rate Statistics")
    print("=" * 60)
    print(f"Total Games: {total_games}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Draws: {draws}")
    print(f"Win Rate: {win_rate:.1f}%")
    print("=" * 60)
    
    # Show recent games
    if games:
        print("\nRecent Games (Last 10):")
        print("-" * 60)
        for i, game in enumerate(games[-10:], 1):
            timestamp = game.get("timestamp", "N/A")
            personality = game.get("personality", "unknown")
            opponent = game.get("opponent_race", "unknown")
            result = game.get("loss_reason", game.get("result", "unknown"))
            game_time = game.get("game_time", 0)
            
            result_icon = "WIN" if result.upper() == "VICTORY" else "LOSS" if result.upper() == "DEFEAT" else "DRAW"
            minutes = game_time // 60
            seconds = game_time % 60
            print(f"{i:2d}. [{result_icon}] {timestamp} | {personality} vs {opponent} | {minutes}:{seconds:02d}")
    
    # Check instance status files
    instance_files = [
        Path("local_training/stats/instance_0_status.json"),
        Path("local_training/scripts/stats/instance_0_status.json"),
    ]
    
    for instance_file in instance_files:
        if instance_file.exists():
            try:
                with open(instance_file, "r", encoding="utf-8") as f:
                    instance_data = json.load(f)
                
                if "win_count" in instance_data or "win_rate" in instance_data:
                    print("\n" + "=" * 60)
                    print(f"Instance Status: {instance_file.name}")
                    print("=" * 60)
                    print(f"Game Count: {instance_data.get('game_count', 0)}")
                    print(f"Win Count: {instance_data.get('win_count', 0)}")
                    print(f"Loss Count: {instance_data.get('loss_count', 0)}")
                    if "win_rate" in instance_data:
                        print(f"Win Rate: {instance_data.get('win_rate', 0):.1f}%")
                    print(f"Difficulty: {instance_data.get('difficulty', 'N/A')}")
                    print(f"Status: {instance_data.get('status', 'N/A')}")
            except Exception as e:
                print(f"[WARNING] Failed to read {instance_file}: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    analyze_win_rate()
