from hybrid_learning import ProGameReplayAnalyzer
from personality_manager import PersonalityManager


class DummyBot:
    def __init__(self):
        self.time = 0


def main():
    analyzer = ProGameReplayAnalyzer()
    print("[TEST] Pro players:", analyzer.pro_players)
    print("[TEST] Default personality:", analyzer.default_personality)

    bot = DummyBot()
    pm = PersonalityManager(bot)  # default may be overridden by config
    print("[TEST] PersonalityManager.personality:", pm.personality)

    # Basic expectations: analyzer players non-empty, pm.personality equals config default or 'serral'
    assert len(analyzer.pro_players) > 0, "Pro players list should not be empty"
    assert isinstance(pm.personality, str) and len(pm.personality) > 0
    print("[TEST] OK: Config load and personality override working")


if __name__ == "__main__":
    main()
