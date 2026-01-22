#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replay Quality Filter - advanced filtering for replay collection.

Filters by APM, opponent quality, map list, and file integrity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import sc2reader

    SC2READER_AVAILABLE = True
except ImportError:
    SC2READER_AVAILABLE = False

MIN_ZERG_APM = 250
MIN_GAME_TIME_SECONDS = 300
MAX_GAME_TIME_SECONDS = 1800
LOTV_RELEASE_DATE = datetime(2015, 11, 10)

GRANDMASTER_INDICATORS = {
    "grandmaster",
    "gm",
    "gmaster",
    "grand master",
    "master",
    "masters",
    "diamond 1",
    "d1",
}

PRO_PLAYER_NAMES = {
    "serral",
    "reynor",
    "dark",
    "solar",
    "rogue",
    "soo",
    "shin",
    "byun",
    "maru",
    "oliveira",
    "scarlett",
    "spirit",
    "firefly",
    "kelazhur",
    "elazer",
    "nerchio",
    "snute",
    "lambo",
    "stephano",
    "innovation",
    "ty",
    "trap",
    "stats",
    "classic",
    "zest",
    "hero",
    "parting",
    "sos",
    "bunny",
    "cure",
    "dream",
    "gumiho",
    "polt",
}

OFFICIAL_LADDER_MAPS = {
    "acropolis",
    "ancient cistern",
    "goldenaura",
    "inside and out",
    "mountain pass",
    "sejong station",
    "waterfall",
    "xel'naga caverns",
    "backwater",
    "cosmic sapphire",
    "dragon scales",
    "estuary",
    "hardwire",
    "pathfinders",
    "stargazers",
    "tropical sacrifice",
}


@dataclass
class FilterStats:
    total_checked: int = 0
    passed_all: int = 0
    failed_integrity: int = 0
    failed_apm: int = 0
    failed_opponent: int = 0
    failed_map: int = 0
    failed_duration: int = 0

    def as_dict(self) -> Dict[str, int]:
        return self.__dict__.copy()


class ReplayQualityFilter:
    def __init__(self, min_apm: int = MIN_ZERG_APM):
        self.min_apm = min_apm
        self.stats = FilterStats()

    def check_file_integrity(self, replay_path: Path) -> Tuple[bool, Optional[str]]:
        if not replay_path.exists():
            return False, "File does not exist"

        file_size = replay_path.stat().st_size
        if file_size == 0:
            return False, "File is empty"
        if file_size < 10240:
            return False, f"File too small: {file_size} bytes"

        try:
            with open(replay_path, "rb") as handle:
                header = handle.read(16)
            if len(header) < 16:
                return False, "File header too short"
        except OSError as exc:
            return False, f"Read error: {exc}"

        return True, None

    def _match_opponent(self, replay) -> bool:
        for player in replay.players:
            name = str(player.name).lower()
            if any(indicator in name for indicator in GRANDMASTER_INDICATORS):
                return True
            if name in PRO_PLAYER_NAMES:
                return True
        return False

    def _get_zerg_apm(self, replay) -> Optional[int]:
        for player in replay.players:
            race = str(getattr(player, "play_race", "")).lower()
            if race == "zerg":
                apm = getattr(player, "avg_apm", None)
                return int(apm) if apm is not None else None
        return None

    def _check_map(self, replay) -> bool:
        map_name = str(getattr(replay, "map_name", "")).lower()
        if not map_name:
            return False
        return map_name in OFFICIAL_LADDER_MAPS

    def _check_duration(self, replay) -> bool:
        if not hasattr(replay, "length"):
            return True
        game_seconds = replay.length.seconds
        if game_seconds < MIN_GAME_TIME_SECONDS:
            return False
        if game_seconds > MAX_GAME_TIME_SECONDS:
            return False
        return True

    def _check_patch_date(self, replay) -> bool:
        if not hasattr(replay, "date") or replay.date is None:
            return True
        return replay.date >= LOTV_RELEASE_DATE

    def filter_replay(self, replay_path: Path) -> bool:
        self.stats.total_checked += 1

        ok, _ = self.check_file_integrity(replay_path)
        if not ok:
            self.stats.failed_integrity += 1
            return False

        if not SC2READER_AVAILABLE:
            return True

        try:
            replay = sc2reader.load_replay(str(replay_path), load_map=True)
        except Exception:
            self.stats.failed_integrity += 1
            return False

        if not self._check_patch_date(replay):
            self.stats.failed_integrity += 1
            return False

        if not self._check_duration(replay):
            self.stats.failed_duration += 1
            return False

        zerg_apm = self._get_zerg_apm(replay)
        if zerg_apm is None or zerg_apm < self.min_apm:
            self.stats.failed_apm += 1
            return False

        if not self._match_opponent(replay):
            self.stats.failed_opponent += 1
            return False

        if not self._check_map(replay):
            self.stats.failed_map += 1
            return False

        self.stats.passed_all += 1
        return True

    def filter_directory(self, replay_dir: Path) -> List[Path]:
        replay_dir = Path(replay_dir)
        replays = sorted(replay_dir.glob("*.SC2Replay"))
        valid = []
        for replay_path in replays:
            if self.filter_replay(replay_path):
                valid.append(replay_path)
        return valid


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Replay quality filter")
    parser.add_argument(
        "--source", default="D:/replays/replays", help="Replay directory"
    )
    parser.add_argument(
        "--min-apm", type=int, default=MIN_ZERG_APM, help="Minimum Zerg APM"
    )
    args = parser.parse_args()

    filterer = ReplayQualityFilter(min_apm=args.min_apm)
    valid = filterer.filter_directory(Path(args.source))

    print(f"Total checked: {filterer.stats.total_checked}")
    print(f"Passed: {filterer.stats.passed_all}")
    print(f"Failed integrity: {filterer.stats.failed_integrity}")
    print(f"Failed duration: {filterer.stats.failed_duration}")
    print(f"Failed APM: {filterer.stats.failed_apm}")
    print(f"Failed opponent: {filterer.stats.failed_opponent}")
    print(f"Failed map: {filterer.stats.failed_map}")
    print(f"Valid replays: {len(valid)}")


if __name__ == "__main__":
    main()
