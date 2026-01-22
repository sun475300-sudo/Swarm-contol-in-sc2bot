#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick replay extraction test helper.
"""

from pathlib import Path


def main() -> None:
    replay_dir = Path("D:/replays/replays")
    replays = list(replay_dir.glob("*.SC2Replay")) if replay_dir.exists() else []
    print(f"Replay directory: {replay_dir}")
    print(f"Replays found: {len(replays)}")

    try:
        import sc2reader

        if replays:
            replay = sc2reader.load_replay(str(replays[0]), load_map=True)
            print(f"Loaded replay: {replay.filename}")
            print(f"Players: {len(replay.players)}")
        else:
            print("No replays to load.")
    except ImportError:
        print("sc2reader not installed. Install with: pip install sc2reader")


if __name__ == "__main__":
    main()
