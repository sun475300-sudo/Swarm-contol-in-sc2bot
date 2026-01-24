# -*- coding: utf-8 -*-
"""
Run a single game for testing.
단일 게임 테스트용 스크립트.
"""

from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro
import sys
import os


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


def main():
    """Run a single test game."""
    _ensure_sc2_path()

    print("\n" + "=" * 60)
    print("  SINGLE GAME TEST")
    print("=" * 60)

    # Settings
    map_name = "AbyssalReefLE"
    opponent_race = Race.Protoss  # vs Protoss (이전 게임 상대)
    difficulty = Difficulty.Easy  # Easy 난이도로 변경

    print(f"  Map: {map_name}")
    print(f"  Opponent: {opponent_race.name}")
    print(f"  Difficulty: {difficulty.name}")
    print("=" * 60)
    print()

    # Create bot
    bot = Bot(Race.Zerg, WickedZergBotPro(train_mode=False))

    # Run game
    map_instance = maps.get(map_name)
    if map_instance is None:
        print(f"[ERROR] Map '{map_name}' not found!")
        return

    run_game(
        map_instance,
        [bot, Computer(opponent_race, difficulty)],
        realtime=False  # False = 빠른 속도로 훈련
    )

    print("\n[GAME FINISHED]")


if __name__ == "__main__":
    main()
