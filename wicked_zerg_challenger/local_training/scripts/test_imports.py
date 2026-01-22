#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import test for local training scripts.
"""


def main() -> None:
    modules = [
        "replay_learning_tracker_sqlite",
        "replay_quality_filter",
        "move_completed_replays",
    ]
    for module in modules:
        try:
            __import__(module)
            print(f"[OK] Imported {module}")
        except Exception as exc:
            print(f"[ERROR] Failed to import {module}: {exc}")


if __name__ == "__main__":
    main()
