#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
종합 테스트 - 모든 난이도에서 승률 측정
"""

from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty, Result
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro
import sys
import os
import time
import json
from datetime import datetime


def _ensure_sc2_path():
    """Set SC2PATH environment variable."""
    if sys.platform != "win32":
        return

    if "SC2PATH" in os.environ:
        sc2_path = os.environ["SC2PATH"]
        versions_dir = os.path.join(sc2_path, "Versions")
        if os.path.exists(versions_dir):
            return

    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Blizzard Entertainment\StarCraft II")
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)

        if os.path.exists(install_path):
            os.environ["SC2PATH"] = install_path
            print(f"[SC2] Found via Registry: {install_path}")
            return
    except Exception:
        pass

    common_paths = [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]
    for path in common_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            print(f"[SC2] Using: {path}")
            return


def run_single_game(difficulty, game_num, total_games):
    """Run a single game and return result."""
    print("\n" + "=" * 70)
    print(f"  GAME #{game_num}/{total_games} - {difficulty.name}")
    print("=" * 70)

    # Settings
    map_name = "AbyssalReefLE"
    opponent_race = Race.Protoss

    print(f"  Map: {map_name}")
    print(f"  Opponent: {opponent_race.name}")
    print(f"  Difficulty: {difficulty.name}")
    print("=" * 70)
    print()

    # Create bot
    bot = Bot(Race.Zerg, WickedZergBotPro(train_mode=False))

    # Run game
    try:
        map_instance = maps.get(map_name)
        if map_instance is None:
            print(f"[ERROR] Map '{map_name}' not found!")
            return None

        result = run_game(
            map_instance,
            [bot, Computer(opponent_race, difficulty)],
            realtime=False
        )

        # Get result
        if result is not None:
            # run_game returns Result directly, not a list
            is_victory = (result == Result.Victory)
            print(f"\n[RESULT] Game #{game_num}: {'WIN' if is_victory else 'LOSS'}")
            return is_victory
        else:
            print(f"\n[RESULT] Game #{game_num}: UNKNOWN")
            return None

    except Exception as e:
        print(f"[ERROR] Game #{game_num} failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_difficulty(difficulty, games_per_difficulty=20):
    """Test a specific difficulty."""
    wins = 0
    losses = 0
    errors = 0

    print("\n" + "=" * 70)
    print(f"  TESTING {difficulty.name} DIFFICULTY")
    print("=" * 70)
    print(f"  Target Games: {games_per_difficulty}")
    print(f"  Target Win Rate: 90%+")
    print("=" * 70)
    print()

    start_time = time.time()

    for game_num in range(1, games_per_difficulty + 1):
        game_start = time.time()

        result = run_single_game(difficulty, game_num, games_per_difficulty)

        if result is True:
            wins += 1
        elif result is False:
            losses += 1
        else:
            errors += 1

        game_duration = time.time() - game_start
        total_duration = time.time() - start_time

        # Calculate current win rate
        total_completed = wins + losses
        win_rate = (wins / total_completed * 100) if total_completed > 0 else 0

        print("\n" + "-" * 70)
        print(f"  Game Duration: {game_duration:.1f}s")
        print(f"  Current Score: {wins}W - {losses}L - {errors}E")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Total Time: {total_duration/60:.1f} min")
        print("-" * 70)
        print()

        # Short delay between games
        time.sleep(1)

    total_duration = time.time() - start_time
    total_completed = wins + losses
    final_win_rate = (wins / total_completed * 100) if total_completed > 0 else 0

    return {
        "difficulty": difficulty.name,
        "wins": wins,
        "losses": losses,
        "errors": errors,
        "total_games": total_completed,
        "win_rate": final_win_rate,
        "duration_minutes": total_duration / 60,
        "avg_game_time": total_duration / max(total_completed, 1)
    }


def main():
    """Run comprehensive test."""
    _ensure_sc2_path()

    # Test configuration
    difficulties_to_test = [
        (Difficulty.Easy, 20),
        (Difficulty.Medium, 20),
        (Difficulty.Hard, 20),
        (Difficulty.VeryHard, 20),
        (Difficulty.CheatVision, 20),  # Cheater difficulty
    ]

    print("\n" + "=" * 70)
    print("  COMPREHENSIVE WIN RATE TEST")
    print("=" * 70)
    print(f"  Total Difficulties: {len(difficulties_to_test)}")
    print(f"  Games per Difficulty: 20")
    print(f"  Total Games: {sum(count for _, count in difficulties_to_test)}")
    print(f"  Target: 90%+ win rate on all difficulties")
    print("=" * 70)
    print()

    overall_start = time.time()
    results = []

    for difficulty, games in difficulties_to_test:
        result = test_difficulty(difficulty, games)
        results.append(result)

        # Print summary
        print("\n" + "=" * 70)
        print(f"  {difficulty.name} COMPLETE")
        print("=" * 70)
        print(f"  Win Rate: {result['win_rate']:.1f}%")
        print(f"  Score: {result['wins']}W - {result['losses']}L")
        print(f"  Status: {'PASS' if result['win_rate'] >= 90 else 'FAIL'}")
        print("=" * 70)
        print()

    overall_duration = time.time() - overall_start

    # Final report
    print("\n" + "=" * 70)
    print("  FINAL REPORT")
    print("=" * 70)
    print()

    total_wins = sum(r['wins'] for r in results)
    total_games = sum(r['total_games'] for r in results)
    overall_win_rate = (total_wins / total_games * 100) if total_games > 0 else 0

    for result in results:
        status = "PASS" if result['win_rate'] >= 90 else "FAIL"
        print(f"  {result['difficulty']:12} | {result['win_rate']:5.1f}% | {result['wins']:2}W-{result['losses']:2}L | {status}")

    print("-" * 70)
    print(f"  Overall Win Rate: {overall_win_rate:.1f}%")
    print(f"  Total Time: {overall_duration/60:.1f} minutes")
    print("=" * 70)

    # Save results to JSON
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_win_rate": overall_win_rate,
        "total_wins": total_wins,
        "total_games": total_games,
        "total_duration_minutes": overall_duration / 60,
        "results": results
    }

    report_file = "test_results.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVED] Results saved to: {report_file}")

    # Check if target achieved
    passed_all = all(r['win_rate'] >= 90 for r in results)
    if passed_all:
        print("\n[SUCCESS] All difficulties passed with 90%+ win rate!")
    else:
        print("\n[INCOMPLETE] Some difficulties did not reach 90% win rate.")


if __name__ == "__main__":
    main()
