#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replay-based smoke pipeline.

Parses replay metadata with sc2reader (if available),
derives lightweight feature heuristics, and runs batch training.
This is intended for smoke testing only.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

from batch_trainer import train_from_manifest

try:
    import sc2reader
    SC2READER_AVAILABLE = True
except ImportError:
    SC2READER_AVAILABLE = False


def build_results_from_replays(replay_dir: Path, max_files: int) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    replay_files = sorted(replay_dir.glob("*.SC2Replay"))[:max_files]
    print(f"[REPLAY] Found {len(replay_files)} replay files")

    for replay_path in replay_files:
        try:
            replay = sc2reader.load_replay(str(replay_path), load_level=1)

            # Handle length - can be Seconds object or int
            raw_length = getattr(replay, "length", None)
            if hasattr(raw_length, "seconds"):
                game_seconds = max(1, int(raw_length.seconds))
            elif raw_length is not None:
                game_seconds = max(1, int(float(str(raw_length).replace("s", "").split(".")[0]) * 60 if "." in str(raw_length) else raw_length))
            else:
                game_seconds = 600  # Default 10 minutes

            minutes = game_seconds / 60.0

            # Find Zerg player (check play_race attribute)
            zerg_player = None
            for p in replay.players:
                race = getattr(p, "play_race", None) or getattr(p, "pick_race", None)
                if race == "Zerg":
                    zerg_player = p
                    break

            # If no Zerg player, still learn from the replay (opponent analysis)
            if zerg_player:
                apm = float(getattr(zerg_player, "avg_apm", 150.0))
                victory = str(getattr(zerg_player, "result", "")).lower() == "win"
            else:
                apm = 150.0
                victory = False

            print(f"[REPLAY] Processed: {replay_path.name} - {minutes:.1f}min, APM:{apm:.0f}, Win:{victory}")

            # Heuristic feature synthesis for smoke training
            minerals = min(2000, apm * 4 + minutes * 200)
            gas = min(1000, apm * 2 + minutes * 100)
            supply_used = min(200, minutes * 12)
            drone_count = min(100, minutes * 4)
            army_count = min(120, minutes * 6)
            enemy_army_count = min(120, minutes * 6)
            enemy_tech_level = 2 if minutes > 10 else 1 if minutes > 6 else 0
            enemy_threat_level = min(4.0, (apm / 100.0))

            results.append(
                {
                    "minerals": minerals,
                    "gas": gas,
                    "supply_used": supply_used,
                    "drone_count": drone_count,
                    "army_count": army_count,
                    "enemy_army_count": enemy_army_count,
                    "enemy_tech_level": enemy_tech_level,
                    "enemy_threat_level": enemy_threat_level,
                    "enemy_unit_diversity": 0.5,
                    "scout_coverage": 0.5,
                    "enemy_main_distance": 50.0,
                    "enemy_expansion_count": 2,
                    "enemy_resource_estimate": 2500,
                    "enemy_upgrade_count": 2,
                    "enemy_air_ground_ratio": 0.5,
                    "victory": victory,
                    "attack_probability": 0.35,
                    "defense_probability": 0.25,
                    "economy_probability": 0.2,
                    "tech_probability": 0.2,
                }
            )
        except Exception:
            continue
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay-based smoke training")
    parser.add_argument("--replay-dir", required=True, help="Directory with .SC2Replay files")
    parser.add_argument("--max-files", type=int, default=30, help="Limit number of replays to sample")
    parser.add_argument("--epochs", type=int, default=2, help="Training epochs")
    parser.add_argument("--output-dir", default="local_training/smoke_output", help="Output directory")
    args = parser.parse_args()

    if not SC2READER_AVAILABLE:
        print("[ERROR] sc2reader is not installed. Install it to use this script.")
        return

    replay_dir = Path(args.replay_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = build_results_from_replays(replay_dir, max(1, args.max_files))
    manifest_path = output_dir / "replay_smoke_manifest.json"
    manifest_path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")

    stats = train_from_manifest(manifest_path, model_path=str(output_dir / "zerg_net_model_replay_smoke.pt"), epochs=args.epochs)
    summary_path = output_dir / "replay_smoke_summary.json"
    summary_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"[SMOKE] Replay smoke complete. Summary -> {summary_path}")


if __name__ == "__main__":
    main()
