from telemetry_logger import TelemetryLogger
from personality_manager import PersonalityManager
from types import SimpleNamespace
from sc2.data import Result


def main():
    # Dummy bot with minimal attributes required by TelemetryLogger
    bot = SimpleNamespace(
        time=123.4,
        iteration=500,
        minerals=800,
        vespene=200,
        supply_army=30,
        supply_used=80,
        supply_cap=110,
        supply_left=30,
        townhalls=SimpleNamespace(amount=3),
        game_phase=SimpleNamespace(name="MID"),
        workers=SimpleNamespace(amount=60),
        units=lambda _: SimpleNamespace(amount=0),
        enemy_units=[],
        opponent_race="Terran",
    )

    # Apply personality (config may override default 'serral')
    pm = PersonalityManager(bot)
    bot.personality = pm.personality

    # Initialize telemetry logger
    tl = TelemetryLogger(bot, instance_id=42)
    # Redirect stats file to data for test isolation
    tl.stats_file = "data/test_training_stats.jsonl"

    # Record a defeat result with minimal loss details
    tl.record_game_result(Result.Defeat, "test_defeat", {
        "worker_count": 60,
        "townhall_count": 3,
        "army_count": 25,
    })

    print("[TEST] Logged to:", tl.stats_file)
    print("[TEST] Personality:", bot.personality)

    # Read back last line
    with open(tl.stats_file, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    assert lines, "No stats logged"
    import json
    last = json.loads(lines[-1])
    assert last.get("personality") == bot.personality, "Personality not logged correctly"
    print("[TEST] OK: personality logged in training stats")


if __name__ == "__main__":
    main()
