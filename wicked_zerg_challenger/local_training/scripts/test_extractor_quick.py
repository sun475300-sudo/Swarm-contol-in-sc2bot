#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick extractor sanity check.
"""

from pathlib import Path


def main() -> None:
    replay_dir = Path("D:/replays/replays")
    replays = list(replay_dir.glob("*.SC2Replay")) if replay_dir.exists() else []
    print(f"Replay directory: {replay_dir}")
    print(f"Replays found: {len(replays)}")

    if not replays:
        return

    sample = replays[0]
    print(f"Sample replay: {sample.name}")


if __name__ == "__main__":
    main()
