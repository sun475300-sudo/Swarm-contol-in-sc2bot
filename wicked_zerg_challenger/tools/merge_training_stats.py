"""
Merge per-instance training statistics into a single summary.

Usage:
    python tools/merge_training_stats.py --stats-dir stats --output-prefix stats/training_stats_merged

Outputs:
    - <output-prefix>.json: aggregated summary + per-instance breakdown
    - <output-prefix>.csv : tabular per-instance breakdown for quick plotting
"""

import argparse
import json
from pathlib import Path
from typing import List, Sequence, TypedDict


class InstanceStats(TypedDict):
    instance_id: str
    total_games: int
    wins: int
    losses: int
    avg_game_duration: float
    current_level: int | None


class Summary(TypedDict):
    total_games: int
    wins: int
    losses: int
    win_rate: float
    avg_game_duration: float
    instances: int


class MergedStats(TypedDict):
    summary: Summary
    instances: List[InstanceStats]


def _load_instance_stats(path: Path) -> InstanceStats:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Normalize and guard against missing fields
    return {
        "instance_id": path.stem.replace("training_stats_instance_", ""),
        "total_games": int(data.get("total_games", 0)),
        "wins": int(data.get("wins", 0)),
        "losses": int(data.get("losses", 0)),
        "avg_game_duration": float(data.get("avg_game_duration", 0.0)),
        "current_level": data.get("current_level"),
    }


def _weighted_average(durations: Sequence[float], weights: Sequence[int]) -> float:
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(d * w for d, w in zip(durations, weights))
    return weighted_sum / total_weight


def merge_stats(stats_dir: Path) -> MergedStats:
    instance_files = sorted(stats_dir.glob("training_stats_instance_*.json"))
    if not instance_files:
        raise FileNotFoundError(f"No stats files found in {stats_dir}")

    instances = [_load_instance_stats(path) for path in instance_files]

    total_games = sum(i["total_games"] for i in instances)
    total_wins = sum(i["wins"] for i in instances)
    total_losses = sum(i["losses"] for i in instances)
    avg_duration = _weighted_average(
        [i["avg_game_duration"] for i in instances],
        [i["total_games"] for i in instances],
    )

    merged: MergedStats = {
        "summary": {
            "total_games": total_games,
            "wins": total_wins,
            "losses": total_losses,
            "win_rate": round(total_wins / total_games, 4) if total_games else 0.0,
            "avg_game_duration": round(avg_duration, 2),
            "instances": len(instances),
        },
        "instances": instances,
    }
    return merged


def write_outputs(merged: MergedStats, output_prefix: Path) -> None:
    json_path = output_prefix.with_suffix(".json")
    csv_path = output_prefix.with_suffix(".csv")

    json_path.parent.mkdir(parents=True, exist_ok=True)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    # CSV: instance_id,total_games,wins,losses,win_rate,avg_game_duration,current_level
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(
            "instance_id,total_games,wins,losses,win_rate,avg_game_duration,current_level\n"
        )
        for inst in merged["instances"]:
            games = inst["total_games"]
            wins = inst["wins"]
            win_rate = wins / games if games else 0.0
            f.write(
                f"{inst['instance_id']},{games},{wins},{inst['losses']},{win_rate:.4f},{inst['avg_game_duration']:.2f},{inst['current_level']}\n"
            )

    print(f"[OK] Wrote summary: {json_path}")
    print(f"[OK] Wrote CSV:     {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Merge training stats across instances")
    parser.add_argument(
        "--stats-dir",
        type=Path,
        default=Path("stats"),
        help="Directory containing training_stats_instance_*.json files",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path("stats/training_stats_merged"),
        help="Prefix for output files (without extension)",
    )
    args = parser.parse_args()

    merged = merge_stats(args.stats_dir)
    write_outputs(merged, args.output_prefix)

    summary = merged["summary"]
    print(
        f"[SUMMARY] games={summary['total_games']} wins={summary['wins']} "
        f"losses={summary['losses']} win_rate={summary['win_rate']:.2%} "
        f"avg_game_duration={summary['avg_game_duration']}s"
    )


if __name__ == "__main__":
    main()
