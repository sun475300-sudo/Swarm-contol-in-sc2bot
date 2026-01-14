#!/usr/bin/env python3
"""Summarize training_stats.json
Print: total games, wins, losses, win rate, games per instance, top loss reasons, avg game time."""

import json
from collections import Counter, defaultdict
from pathlib import Path

p = Path(__file__).parent.parent / "training_stats.json"
if not p.exists():
    print("training_stats.json not found")
    raise SystemExit(1)

wins = 0
losses = 0
games = 0
reasons = Counter()
by_instance = defaultdict(int)
by_personality = Counter()
total_time = 0

with p.open("r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        games += 1
        r = obj.get("result", "").lower()
        if "victory" in r:
            wins += 1
        else:
            losses += 1
        reasons[obj.get("loss_reason", "UNKNOWN")] += 1
        by_instance[obj.get("instance_id", "unknown")] += 1
        by_personality[obj.get("personality", "unknown")] += 1
        total_time += obj.get("game_time", 0)

avg_time = total_time / games if games else 0
win_rate = wins / games * 100 if games else 0

print(
    f"games={games} wins={wins} losses={losses} win_rate={win_rate:.1f}% avg_time={avg_time:.0f}s"
)
print("games per instance:")
for k, v in sorted(by_instance.items()):
    print(f"  {k}: {v}")
print("games per personality:")
for k, v in by_personality.most_common():
    print(f"  {k}: {v}")
print("top loss reasons:")
for reason, count in reasons.most_common(8):
    print(f"  {reason}: {count}")
