#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
연속 학습 루프 - 단일 창에서 반복 실행
"""

from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro
import sys
import os
import time


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


def run_single_game(game_num):
    """Run a single game."""
    _ensure_sc2_path()

    print("\n" + "=" * 60)
    print(f"  TRAINING GAME #{game_num}")
    print("=" * 60)

    # Settings
    map_name = "AbyssalReefLE"
    opponent_race = Race.Protoss
    difficulty = Difficulty.Easy

    print(f"  Map: {map_name}")
    print(f"  Opponent: {opponent_race.name}")
    print(f"  Difficulty: {difficulty.name}")
    print("=" * 60)
    print()

    # Create bot
    bot = Bot(Race.Zerg, WickedZergBotPro(train_mode=False))

    # Run game
    try:
        map_instance = maps.get(map_name)
        if map_instance is None:
            print(f"[ERROR] Map '{map_name}' not found!")
            return False

        run_game(
            map_instance,
            [bot, Computer(opponent_race, difficulty)],
            realtime=False
        )
        print(f"\n[GAME #{game_num} FINISHED]")
        return True
    except Exception as e:
        print(f"[ERROR] Game #{game_num} failed: {e}")
        return False


def main():
    """Run training loop."""
    total_games = 10  # 30분 동안 약 10게임
    start_time = time.time()
    games_completed = 0

    print("\n" + "=" * 70)
    print("  [TRAINING] CONTINUOUS TRAINING LOOP STARTED")
    print("=" * 70)
    print(f"  Target: {total_games} games")
    print(f"  Duration: ~30 minutes")
    print("=" * 70)
    print()

    for game_num in range(1, total_games + 1):
        game_start = time.time()

        success = run_single_game(game_num)

        if success:
            games_completed += 1

        game_duration = time.time() - game_start
        total_duration = time.time() - start_time

        print("\n" + "-" * 70)
        print(f"  Game #{game_num} Duration: {game_duration:.1f}s")
        print(f"  Total Duration: {total_duration/60:.1f} min")
        print(f"  Games Completed: {games_completed}/{game_num}")
        print("-" * 70)
        print()

        # Break if 30 minutes passed
        if total_duration > 1800:  # 30 minutes
            print(f"\n[TIME] Time limit reached ({total_duration/60:.1f} min)")
            break

        # Short delay between games
        time.sleep(2)

    final_duration = time.time() - start_time
    print("\n" + "=" * 70)
    print("  [COMPLETE] TRAINING LOOP COMPLETE")
    print("=" * 70)
    print(f"  Total Games: {games_completed}")
    print(f"  Total Time: {final_duration/60:.1f} minutes")
    print(f"  Avg Time/Game: {final_duration/max(games_completed, 1):.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
