# -*- coding: utf-8 -*-
"""
AI Arena Entry Point

This is the main entry point for AI Arena deployment.
It supports both ladder server mode (--LadderServer) and local testing.
"""

import sys
import os
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

# Import SC2 library
from sc2.data import Race, Difficulty  # type: ignore
from sc2.main import run_game, run_ladder_game  # type: ignore
from sc2.player import Bot, Computer  # type: ignore
from sc2 import maps  # type: ignore

# Import bot class
from wicked_zerg_bot_pro import WickedZergBotPro


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
        # Start Arena Monitoring Server
        arena_server_manager = None
        try:
            project_root = Path(__file__).parent
            sys.path.insert(0, str(project_root))
            from monitoring.server_manager import start_arena_monitoring
            arena_server_manager = start_arena_monitoring(background=True)
            if arena_server_manager:
                print("\n? Arena monitoring server started")
                print(f"   Server URL: {arena_server_manager.get_server_url()}")
                print(f"   Mobile/Web Access: Available")
        except Exception as e:
            print(f"\n?? Arena monitoring server not available: {e}")
            print("   Continuing without monitoring server...")

        print("\nJoining Ladder Game...")
        try:
            run_ladder_game(bot)
        finally:
            # Stop arena server when done
            if arena_server_manager:
                print("\n[INFO] Stopping arena monitoring server...")
                arena_server_manager.stop_server()

    # 2. Run on local machine for testing
    else:
        # Start Local Monitoring Server
        local_server_manager = None
        try:
            project_root = Path(__file__).parent
            sys.path.insert(0, str(project_root))
            from monitoring.server_manager import start_local_monitoring
            local_server_manager = start_local_monitoring(background=True)
            if local_server_manager:
                print("\n? Local monitoring server started")
                print(f"   Server URL: {local_server_manager.get_server_url()}")
                print(f"   Mobile/Web Access: Available")
        except Exception as e:
            print(f"\n?? Local monitoring server not available: {e}")
            print("   Continuing without monitoring server...")

        print("\nStarting Local Game...")
        print("Game window will open - you can watch the game in real-time!")
        map_name = "AbyssalReefLE"
        try:
            run_game(
                maps.get(map_name),
                [
                    bot,
                    Computer(Race.Terran, Difficulty.VeryHard)
                ],
                realtime=False  # False = fast speed, True = real-time speed
            )
        finally:
            # Stop local server when done
            if local_server_manager:
                print("\n[INFO] Stopping local monitoring server...")
                local_server_manager.stop_server()

if __name__ == "__main__":
 main()
