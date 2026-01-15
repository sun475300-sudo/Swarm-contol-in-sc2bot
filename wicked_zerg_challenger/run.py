# -*- coding: utf-8 -*-
import sys, os
from pathlib import Path

# SC2 path auto-setup function
def _ensure_sc2_path():
    """
    Set SC2PATH environment variable - search via Windows Registry or common paths
    """
    # Skip Windows-specific discovery on non-Windows hosts (AI Arena runs on Linux)
    if sys.platform != "win32":
        return

    if "SC2PATH" in os.environ:
        sc2_path = os.environ["SC2PATH"]
        versions_dir = os.path.join(sc2_path, "Versions")
        if os.path.exists(versions_dir):
            return

    # 1. Find StarCraft II installation path via Windows Registry
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

    # 2. Search common installation paths
    common_paths = [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]

    for path in common_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            print(f"[SC2] Found at common path: {path}")
            return

    print("[WARNING] SC2 installation not found automatically")

# Setup SC2 path before sc2 import
_ensure_sc2_path()

# Bot class import
# Add project root to sys.path to ensure bot modules resolve in packaged environments
sys.path.append(str(Path(__file__).parent))
from wicked_zerg_bot_pro import WickedZergBotPro
from sc2.data import Race, Difficulty  # type: ignore
from sc2.main import run_game  # type: ignore
from sc2.player import Bot, Computer  # type: ignore
from sc2 import maps  # type: ignore

def create_bot():
    """
    AI Arena entry point - Create bot instance.
    This function can be called directly by AI Arena if needed.
    """
    return Bot(Race.Zerg, WickedZergBotPro())

def main():
    """
    Main entry point for bot execution.
    Supports both AI Arena ladder mode and local testing.
    """
    bot = create_bot()

    # 1. Run on AI Arena server (when --LadderServer flag is present)
    if "--LadderServer" in sys.argv:
        from sc2.main import run_ladder_game  # type: ignore
        print("Joining Ladder Game...")
        run_ladder_game(bot)

    # 2. Run on local machine for testing
    else:
        print("Starting Local Game...")
        print("Game window will open - you can watch the game in real-time!")
        map_name = "AbyssalReefLE"
        run_game(
            maps.get(map_name),
            [
                bot,
                Computer(Race.Terran, Difficulty.VeryHard)
            ],
            realtime=False  # False = fast speed, True = real-time speed
        )

if __name__ == "__main__":
    main()
