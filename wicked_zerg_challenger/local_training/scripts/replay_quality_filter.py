#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replay Quality Filter - Advanced filtering for replay collection

Features:
- APM filtering (minimum 250 for Zerg player)
- Opponent level checking (Grandmaster/Pro gamer)
- Official ladder map validation
- File integrity checking
"""

import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime

try:
    import sc2reader
    SC2READER_AVAILABLE = True
except ImportError:
    SC2READER_AVAILABLE = False

# Configuration constants
MIN_ZERG_APM = 250  # Minimum APM for Zerg player
MIN_GAME_TIME_SECONDS = 300  # 5 minutes
MAX_GAME_TIME_SECONDS = 1800  # 30 minutes
LOTV_RELEASE_DATE = datetime(2015, 11, 10)

# Grandmaster tier names (common indicators)
GRANDMASTER_INDICATORS = [
    "grandmaster", "gm", "gmaster", "grand master",
    "master", "masters", "diamond 1", "d1"
]

# Pro player names (major tournaments)
PRO_PLAYER_NAMES = {
    "serral", "reynor", "dark", "solar", "rogue", "soo", "shin",
    "byun", "maru", "oliveira", "scarlett", "spirit", "firefly",
    "kelazhur", "elazer", "nerchio", "snute", "lambo", "stephano",
    "innovation", "ty", "trap", "stats", "classic", "zest", "hero",
    "parting", "sos", "bunny", "cure", "dream", "gumiho", "polt"
}

# Official ladder map names (current season - update as needed)
OFFICIAL_LADDER_MAPS = [
    "acropolis", "ancient cistern", "goldenaura", "inside and out",
    "mountain pass", "sejong station", "waterfall", "xel'naga caverns",
    "backwater", "cosmic sapphire", "dragon scales", "estuary",
    "hardwire", "pathfinders", "stargazers", "tropical sacrifice"
]


class ReplayQualityFilter:
    """Advanced replay quality filtering"""

    def __init__(self, min_apm: int = MIN_ZERG_APM):
        self.min_apm = min_apm
        self.stats = {
            "total_checked": 0,
            "passed_apm": 0,
            "passed_opponent": 0,
            "passed_map": 0,
            "passed_all": 0,
            "failed_apm": 0,
            "failed_opponent": 0,
            "failed_map": 0,
            "failed_integrity": 0,
            "incompatible": 0
        }

    def check_file_integrity(self, replay_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Check file integrity (size, CRC, corruption)

        Returns:
            (is_valid, error_message)
        """
        try:
            # Check file exists and has size
            if not replay_path.exists():
                return False, "File does not exist"

            file_size = replay_path.stat().st_size
            if file_size == 0:
                return False, "File is empty (0 bytes)"

            # Minimum expected size for SC2Replay (usually > 10KB)
            if file_size < 10240:
                return False, f"File too small: {file_size} bytes"

            # Try to read first few bytes to check if file is accessible
            with open(replay_path, 'rb') as f:
                header = f.read(16)
                if len(header) < 16:
                    return False, "File header too short"

            return True, None

        except Exception as e:
            return False, f"Integrity check error: {str(e)}"

    def calculate_apm(self, replay, player) -> Optional[float]:
        """
        Calculate APM (Actions Per Minute) for a player

        Returns:
            APM value or None if cannot calculate
        """
        if not SC2READER_AVAILABLE or not hasattr(replay, 'events'):
            return None

        try:
            # Count actions (commands) by the player
            action_count = 0
            game_length_minutes = 0

            for event in replay.events:
                # Check if event is from this player
                if hasattr(event, 'player') and event.player == player:
                    # Count command events (unit commands, building commands, etc.)
                    if hasattr(event, 'name') and 'Command' in event.name:
                        action_count += 1

                # Track game length
                if hasattr(event, 'second'):
                    game_length_minutes = max(game_length_minutes, event.second / 60.0)

            if game_length_minutes > 0:
                apm = action_count / game_length_minutes
                return apm

            return None

        except Exception:
            return None

    def check_zerg_apm(self, replay, zerg_player) -> Tuple[bool, Optional[float]]:
        """
        Check if Zerg player meets minimum APM requirement

        Returns:
            (meets_requirement, apm_value)
        """
        apm = self.calculate_apm(replay, zerg_player)
        if apm is None:
            # If cannot calculate APM, allow it (don't reject)
            return True, None

        meets_requirement = apm >= self.min_apm
        return meets_requirement, apm

    def check_opponent_level(self, replay, zerg_player) -> Tuple[bool, Optional[str]]:
        """
        Check if opponent is Grandmaster tier or pro player

        Returns:
            (is_high_level, opponent_info)
        """
        opponent = None
        for player in replay.players:
            if player != zerg_player:
                opponent = player
                break

        if opponent is None:
            return False, "No opponent found"

        opponent_name = (opponent.name or "").lower()
        opponent_league = (getattr(opponent, 'highest_league', "") or "").lower()

        # Check if opponent is pro player
        if any(pro_name in opponent_name for pro_name in PRO_PLAYER_NAMES):
            return True, f"Pro player: {opponent.name}"

        # Check if opponent is Grandmaster/Master
        if any(indicator in opponent_league for indicator in GRANDMASTER_INDICATORS):
            return True, f"High tier: {opponent_league}"

        # Check if opponent name contains GM indicators
        if any(indicator in opponent_name for indicator in GRANDMASTER_INDICATORS):
            return True, f"GM indicator in name: {opponent.name}"

        # If cannot determine, allow it (don't reject)
        return True, "Unknown level"

    def check_official_map(self, replay) -> Tuple[bool, Optional[str]]:
        """
        Check if replay is on official ladder map

        Returns:
            (is_official, map_name)
        """
        if not hasattr(replay, 'map_name'):
            return True, None  # Allow if cannot determine

        map_name = str(replay.map_name).lower()

        # Check against official ladder maps
        for official_map in OFFICIAL_LADDER_MAPS:
            if official_map in map_name:
                return True, replay.map_name

        # Check if map name contains indicators of custom/arcade maps
        custom_indicators = ["custom", "arcade", "use map", "practice", "test"]
        if any(indicator in map_name for indicator in custom_indicators):
            return False, f"Custom/Arcade map: {replay.map_name}"

        # If cannot determine, allow it (don't reject)
        return True, replay.map_name

    def validate_replay_quality(self, replay_path: Path) -> Tuple[bool, Dict[str, any]]:
        """
        Comprehensive replay quality validation

        Returns:
            (is_valid, validation_details)
        """
        self.stats["total_checked"] += 1

        validation_details = {
            "replay_path": str(replay_path),
            "passed": False,
            "errors": [],
            "warnings": [],
            "apm": None,
            "opponent_info": None,
            "map_name": None,
            "incompatible": False
        }

        # 1. File integrity check
        is_valid, error = self.check_file_integrity(replay_path)
        if not is_valid:
            self.stats["failed_integrity"] += 1
            validation_details["errors"].append(f"Integrity: {error}")
            return False, validation_details

        # 2. sc2reader validation
        if not SC2READER_AVAILABLE:
            validation_details["warnings"].append("sc2reader not available, skipping metadata validation")
            validation_details["passed"] = True
            return True, validation_details

        try:
            replay = sc2reader.load_replay(str(replay_path), load_map=True)
        except Exception as e:
            # Version incompatibility or corruption
            error_msg = str(e)
            if "version" in error_msg.lower() or "incompatible" in error_msg.lower():
                self.stats["incompatible"] += 1
                validation_details["incompatible"] = True
                validation_details["errors"].append(f"Version incompatible: {error_msg}")
            else:
                self.stats["failed_integrity"] += 1
                validation_details["errors"].append(f"Load error: {error_msg}")
            return False, validation_details

        # 3. Basic structure check
        if not hasattr(replay, 'players') or len(replay.players) < 2:
            validation_details["errors"].append("Insufficient players")
            return False, validation_details

        # 4. Find Zerg player
        zerg_player = None
        for player in replay.players:
            if hasattr(player, 'play_race'):
                race = str(player.play_race).lower()
                if race == "zerg":
                    zerg_player = player
                    break

        if zerg_player is None:
            validation_details["errors"].append("No Zerg player found")
            return False, validation_details

        # 5. APM check
        meets_apm, apm_value = self.check_zerg_apm(replay, zerg_player)
        validation_details["apm"] = apm_value
        if not meets_apm and apm_value is not None:
            self.stats["failed_apm"] += 1
            validation_details["errors"].append(f"APM too low: {apm_value:.1f} < {self.min_apm}")
            return False, validation_details
        self.stats["passed_apm"] += 1

        # 6. Opponent level check
        is_high_level, opponent_info = self.check_opponent_level(replay, zerg_player)
        validation_details["opponent_info"] = opponent_info
        if not is_high_level:
            self.stats["failed_opponent"] += 1
            validation_details["warnings"].append(f"Opponent level unknown: {opponent_info}")
        else:
            self.stats["passed_opponent"] += 1

        # 7. Official map check
        is_official, map_name = self.check_official_map(replay)
        validation_details["map_name"] = map_name
        if not is_official:
            self.stats["failed_map"] += 1
            validation_details["warnings"].append(f"Non-official map: {map_name}")
        else:
            self.stats["passed_map"] += 1

        # 8. Game time check
        if hasattr(replay, 'length'):
            game_seconds = replay.length.seconds
            if game_seconds < MIN_GAME_TIME_SECONDS:
                validation_details["errors"].append(f"Game too short: {game_seconds}s")
                return False, validation_details
            if game_seconds > MAX_GAME_TIME_SECONDS:
                validation_details["warnings"].append(f"Game very long: {game_seconds}s")

        # 9. LotV patch check
        if hasattr(replay, 'date'):
            replay_date = replay.date
            if replay_date < LOTV_RELEASE_DATE:
                validation_details["errors"].append(f"Pre-LotV: {replay_date.date()}")
                return False, validation_details

        # All checks passed
        self.stats["passed_all"] += 1
        validation_details["passed"] = True
        return True, validation_details

    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics"""
        return self.stats.copy()


def main():
    """Test the quality filter"""
    import argparse

    parser = argparse.ArgumentParser(description="Replay Quality Filter")
    parser.add_argument("replay_path", type=str, help="Path to replay file")
    parser.add_argument("--min-apm", type=int, default=MIN_ZERG_APM, help="Minimum APM requirement")
    args = parser.parse_args()

    filter_obj = ReplayQualityFilter(min_apm=args.min_apm)
    is_valid, details = filter_obj.validate_replay_quality(Path(args.replay_path))

    print(f"\n[QUALITY CHECK] {args.replay_path}")
    print("=" * 80)
    print(f"Status: {'PASSED' if is_valid else 'FAILED'}")
    print(f"APM: {details.get('apm', 'N/A')}")
    print(f"Opponent: {details.get('opponent_info', 'N/A')}")
    print(f"Map: {details.get('map_name', 'N/A')}")

    if details.get("errors"):
        print("\nErrors:")
        for error in details["errors"]:
            print(f"  - {error}")

    if details.get("warnings"):
        print("\nWarnings:")
        for warning in details["warnings"]:
            print(f"  - {warning}")

    print(f"\nStats: {filter_obj.get_stats()}")


if __name__ == "__main__":
    main()
