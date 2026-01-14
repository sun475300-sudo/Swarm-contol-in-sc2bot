# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
from sc2.data import Difficulty  # type: ignore


class CurriculumManager:
    def __init__(self, stats_file: str = "training_stats.json"):
        # Create data directory if needed (in local_training folder)
        script_dir = Path(__file__).parent
        self.data_dir = script_dir / "data"
        self.data_dir.mkdir(exist_ok=True)

        # Stats file path (in data/ directory)
        self.stats_file = (
            self.data_dir / stats_file if not os.path.isabs(stats_file) else Path(stats_file)
        )

        # IMPROVED: Difficulty levels progression (gradually increasing, ONE level at a time)
        # CRITICAL: Always progresses sequentially - never skips levels
        # Progression: VeryEasy -> Easy -> Medium -> Hard -> VeryHard -> CheatInsane
        self.levels = [
            Difficulty.VeryEasy,      # Stage 1: Very Easy (starting level)
            Difficulty.Easy,          # Stage 2: Easy (one step up from VeryEasy)
            Difficulty.Medium,        # Stage 3: Medium (one step up from Easy)
            Difficulty.Hard,          # Stage 4: Hard (one step up from Medium)
            Difficulty.VeryHard,      # Stage 5: Very Hard (one step up from Hard)
            Difficulty.CheatInsane,   # Stage 6: Cheat Insane (one step up from VeryHard)
        ]

        # Load current level from file
        self.current_idx = self.load_level()

        # IMPROVED: Minimum games per level before promotion
        # Ensures sufficient practice at each level before moving up
        self.min_games_per_level = {
            0: 10,   # VeryEasy: minimum 10 games
            1: 15,   # Easy: minimum 15 games
            2: 20,   # Medium: minimum 20 games
            3: 25,   # Hard: minimum 25 games
            4: 30,   # VeryHard: minimum 30 games
            5: 40,   # CheatInsane: minimum 40 games
        }

        # IMPROVED: Win rate thresholds (conservative to ensure gradual progression)
        # Higher threshold means more games needed before promotion (one level at a time)
        self.promotion_threshold = 0.80   # 80% win rate to promote (one level up)
        self.demotion_threshold = 0.20    # 20% win rate to demote (one level down)

        # Current level game counter
        self.games_at_current_level = 0

    def load_level(self) -> int:
        """Load curriculum level from stats file."""
        if not self.stats_file.exists():
            return 0

        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                level_idx = data.get("curriculum_level_idx", 0)

                # Validate index
                if 0 <= level_idx < len(self.levels):
                    self.games_at_current_level = data.get("games_at_current_level", 0)
                    return level_idx
                else:
                    return 0
        except (IOError, json.JSONDecodeError):
            return 0

    def save_level(self):
        """Save current curriculum level to stats file."""
        try:
            data = {
                "curriculum_level_idx": self.current_idx,
                "games_at_current_level": self.games_at_current_level,
            }
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError:
            pass

    def get_difficulty(self) -> Difficulty:
        """Get current difficulty level."""
        if 0 <= self.current_idx < len(self.levels):
            return self.levels[self.current_idx]
        else:
            return self.levels[0]  # Default: VeryEasy

    def get_level_name(self) -> str:
        """Get current level name."""
        difficulty_names = [
            "Very Easy",
            "Easy",
            "Medium",
            "Hard",
            "Very Hard",
            "Cheat Insane",
        ]

        if 0 <= self.current_idx < len(difficulty_names):
            return difficulty_names[self.current_idx]
        return "Very Easy"

    def check_promotion(self, win_rate: float, total_games: int) -> bool:
        """
        Check if AI should be promoted to next difficulty.

        IMPROVED: Ensures difficulty increases by exactly ONE level at a time.
        Never skips levels - always goes: VeryEasy -> Easy -> Medium -> Hard -> VeryHard -> CheatInsane
        """
        min_games = self.min_games_per_level.get(self.current_idx, 10)

        # IMPROVED: Only promote if conditions are met AND we're not at max level
        if (total_games >= min_games and
            win_rate >= self.promotion_threshold and
            self.current_idx < len(self.levels) - 1):

            # IMPROVED: Always increase by exactly 1 level (never skip levels)
            new_idx = self.current_idx + 1

            # Safety check: ensure we don't exceed bounds
            if 0 <= new_idx < len(self.levels):
                old_difficulty = self.levels[self.current_idx].name
                new_difficulty = self.levels[new_idx].name

                # IMPROVED: Only promote one level at a time
                self.current_idx = new_idx
                self.games_at_current_level = 0
                self.save_level()

                print(f"\n{'='*70}")
                print(f"[CURRICULUM] Difficulty increased by ONE level")
                print(f"  {old_difficulty} -> {new_difficulty}")
                print(f"  Win Rate: {win_rate*100:.1f}% (threshold: {self.promotion_threshold*100}%)")
                print(f"  Games at previous level: {total_games}")
                print(f"{'='*70}\n")

                return True

        return False

    def check_demotion(self, win_rate: float, total_games: int) -> bool:
        """
        Check if AI should be demoted to previous difficulty.

        IMPROVED: Ensures difficulty decreases by exactly ONE level at a time.
        Never skips levels - always goes down one step at a time.
        """
        if win_rate < self.demotion_threshold and self.current_idx > 0:
            # IMPROVED: Always decrease by exactly 1 level (never skip levels)
            new_idx = self.current_idx - 1

            # Safety check: ensure we don't go below 0
            if 0 <= new_idx < len(self.levels):
                old_difficulty = self.levels[self.current_idx].name
                new_difficulty = self.levels[new_idx].name

                # IMPROVED: Only demote one level at a time
                self.current_idx = new_idx
                self.games_at_current_level = 0
                self.save_level()

                print(f"\n{'='*70}")
                print(f"[CURRICULUM] Difficulty decreased by ONE level")
                print(f"  {old_difficulty} -> {new_difficulty}")
                print(f"  Win Rate: {win_rate*100:.1f}% (threshold: {self.demotion_threshold*100}%)")
                print(f"  Games at previous level: {total_games}")
                print(f"{'='*70}\n")

                return True

        return False

    def record_game(self):
        """Record game at current level."""
        self.games_at_current_level += 1
        self.save_level()

    def get_level_name_from_idx(self, idx: int) -> str:
        """Get level name from index."""
        difficulty_names = [
            "Very Easy",
            "Easy",
            "Medium",
            "Hard",
            "Very Hard",
            "Cheat Insane",
        ]

        if 0 <= idx < len(difficulty_names):
            return difficulty_names[idx]
        return "Very Easy"

    def get_progress_info(self) -> dict:
        """Get current progress information."""
        current_difficulty = self.get_difficulty()
        min_games = self.min_games_per_level.get(self.current_idx, 10)

        return {
            "current_level": self.current_idx + 1,
            "total_levels": len(self.levels),
            "current_difficulty": current_difficulty.name,
            "level_name": self.get_level_name(),
            "games_at_current_level": self.games_at_current_level,
            "min_games_required": min_games,
            "promotion_threshold": self.promotion_threshold,
            "demotion_threshold": self.demotion_threshold,
        }
    
    def update_priority(self, building_name: str, priority: str = "Urgent") -> None:
        """
        Build-Order Gap Analyzer에서 호출: 건물 건설 우선순위 업데이트
        
        Args:
            building_name: 건물 이름 (예: "SpawningPool", "Extractor")
            priority: 우선순위 ("Urgent", "High", "Normal", "Low")
        """
        # 우선순위 저장 (다음 게임에서 사용)
        if not hasattr(self, 'building_priorities'):
            self.building_priorities = {}
        
        self.building_priorities[building_name] = priority
        
        # 우선순위 파일에 저장
        try:
            priority_file = self.data_dir / "building_priorities.json"
            with open(priority_file, 'w', encoding='utf-8') as f:
                json.dump(self.building_priorities, f, indent=2, ensure_ascii=False)
            print(f"[CURRICULUM] Updated priority for {building_name}: {priority}")
        except Exception as e:
            print(f"[WARNING] Failed to save building priority: {e}")
    
    def get_priority(self, building_name: str) -> str:
        """
        건물의 현재 우선순위 조회
        
        Args:
            building_name: 건물 이름
        
        Returns:
            우선순위 ("Urgent", "High", "Normal", "Low")
        """
        if not hasattr(self, 'building_priorities'):
            # 파일에서 로드 시도
            try:
                priority_file = self.data_dir / "building_priorities.json"
                if priority_file.exists():
                    with open(priority_file, 'r', encoding='utf-8') as f:
                        self.building_priorities = json.load(f)
                else:
                    self.building_priorities = {}
            except Exception:
                self.building_priorities = {}
        
        return self.building_priorities.get(building_name, "Normal")