"""
End-to-end test for dynamic persona assignment and logging accuracy.

Steps:
1) Set default_personality in data/pro_players.json to 'solar' temporarily
2) Instantiate PersonalityManager and TelemetryLogger with a dummy bot
3) Record a game result and verify personality in data/training_stats.json
4) Restore original config value
"""

from pathlib import Path
import json
from types import SimpleNamespace
from sc2.data import Result

from personality_manager import PersonalityManager
from telemetry_logger import TelemetryLogger


CFG_PATH = Path("data/pro_players.json")
STATS_PATH = Path("data/training_stats.json")


def set_default_personality(temp_value: str) -> str:
    if not CFG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CFG_PATH}")
    data = json.loads(CFG_PATH.read_text(encoding="utf-8"))
    original = str(data.get("default_personality", "serral"))
    data["default_personality"] = temp_value
    CFG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return original


def restore_default_personality(original_value: str):
    data = json.loads(CFG_PATH.read_text(encoding="utf-8"))
    data["default_personality"] = original_value
    CFG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_test():
    # 1) Set default_personality to 'solar'
    original = set_default_personality("solar")
    try:
        # 2) Dummy bot
        bot = SimpleNamespace(
            time=321.0,
            iteration=600,
            minerals=900,
            vespene=300,
            supply_army=40,
            supply_used=88,
            supply_cap=120,
            supply_left=32,
            townhalls=SimpleNamespace(amount=3),
            game_phase=SimpleNamespace(name="MID"),
            workers=SimpleNamespace(amount=70),
            units=lambda _: SimpleNamespace(amount=0),
            enemy_units=[],
            opponent_race="Protoss",
        )

        # PersonalityManager default override should pick 'solar'
        pm = PersonalityManager(bot)
        bot.personality = pm.personality
        print(f"[TEST] Selected personality: {bot.personality}")

        # 3) Telemetry logger writing to data/training_stats.json
        tl = TelemetryLogger(bot, instance_id=99)
        tl.stats_file = str(STATS_PATH)
        tl.record_game_result(Result.Defeat, "test_case", {
            "worker_count": 70,
            "townhall_count": 3,
            "army_count": 30,
        })

        # Verify last entry
        lines = [ln.strip() for ln in STATS_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert lines, "No stats logged"
        # Find last JSON object line
        last_line = None
        for ln in reversed(lines):
            if ln.startswith("{") and ln.endswith("}"):
                last_line = ln
                break
        assert last_line is not None, "No JSON lines found in stats file"
        last = json.loads(last_line)
        assert last.get("personality") == "solar", "Logged personality mismatch"
        print("[TEST] OK: data/training_stats.json records personality=solar")
    finally:
        # 4) Restore original config
        restore_default_personality(original)
        print(f"[TEST] Restored default_personality to '{original}'")


if __name__ == "__main__":
    run_test()
