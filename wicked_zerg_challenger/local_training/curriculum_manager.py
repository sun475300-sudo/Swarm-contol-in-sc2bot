# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
import time

try:
    from sc2.difficulty import Difficulty
except ImportError:
    # Fallback if Difficulty is not available
    class Difficulty:
        VeryEasy = None
        Easy = None
        Medium = None
        Hard = None
        VeryHard = None
        CheatInsane = None


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
            Difficulty.VeryEasy,  # Stage 1: Very Easy (starting level)
            Difficulty.Easy,  # Stage 2: Easy (one step up from VeryEasy)
            Difficulty.Medium,  # Stage 3: Medium (one step up from Easy)
            Difficulty.Hard,  # Stage 4: Hard (one step up from Medium)
            Difficulty.VeryHard,  # Stage 5: Very Hard (one step up from Hard)
            Difficulty.CheatInsane,  # Stage 6: Cheat Insane (one step up from VeryHard)
        ]

        # Load current level from file
        self.current_idx = self.load_level()

        # ★ NEW: 승리 횟수 기반 승격 시스템 ★
        # 각 단계에서 필요한 승리 횟수 (달성 시 다음 단계로 승격)
        self.wins_required_per_level = {
            0: 5,   # VeryEasy: 5승 필요
            1: 7,   # Easy: 7승 필요
            2: 10,  # Medium: 10승 필요
            3: 12,  # Hard: 12승 필요
            4: 15,  # VeryHard: 15승 필요
            5: 20,  # CheatInsane: 20승 필요 (마스터!)
        }

        # 현재 레벨에서의 승리/패배 카운터
        self.wins_at_current_level = 0
        self.losses_at_current_level = 0

        # IMPROVED: Minimum games per level before promotion (백업용)
        self.min_games_per_level = {
            0: 10,  # VeryEasy: minimum 10 games
            1: 15,  # Easy: minimum 15 games
            2: 20,  # Medium: minimum 20 games
            3: 25,  # Hard: minimum 25 games
            4: 30,  # VeryHard: minimum 30 games
            5: 40,  # CheatInsane: minimum 40 games
        }

        # Win rate thresholds (백업 시스템으로 유지)
        self.promotion_threshold = 0.80  # 80% win rate to promote (one level up)
        self.demotion_threshold = 0.20  # 20% win rate to demote (one level down)

        # Current level game counter
        self.games_at_current_level = 0

        # 데이터 로드
        self._load_win_loss_data()

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

    def _load_win_loss_data(self):
        """현재 레벨의 승리/패배 데이터 로드."""
        if not self.stats_file.exists():
            return

        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.wins_at_current_level = data.get("wins_at_current_level", 0)
            self.losses_at_current_level = data.get("losses_at_current_level", 0)
        except (IOError, json.JSONDecodeError):
            pass

    def save_level(self):
        """Save current curriculum level and win/loss data to stats file."""
        try:
            data = {
                "curriculum_level_idx": self.current_idx,
                "games_at_current_level": self.games_at_current_level,
                "wins_at_current_level": self.wins_at_current_level,
                "losses_at_current_level": self.losses_at_current_level,
                "wins_required": self.wins_required_per_level.get(self.current_idx, 10),
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

    def record_win(self) -> bool:
        """
        ★ 승리 기록 및 승격 체크 ★

        승리할 때마다 호출됩니다.
        필요한 승리 횟수에 도달하면 자동으로 다음 단계로 승격합니다.

        Returns:
            True if promoted to next level, False otherwise
        """
        self.wins_at_current_level += 1
        self.games_at_current_level += 1

        wins_required = self.wins_required_per_level.get(self.current_idx, 10)

        print(f"\n{'='*70}")
        print(f"[CURRICULUM] 🎉 승리! ({self.wins_at_current_level}/{wins_required})")
        print(f"  현재 단계: {self.get_level_name()} (Level {self.current_idx + 1}/{len(self.levels)})")
        print(f"{'='*70}\n")

        # 승격 체크: 필요한 승리 횟수 달성
        if self.wins_at_current_level >= wins_required:
            return self._promote_to_next_level()

        self.save_level()
        return False

    def record_loss(self) -> bool:
        """
        ★ 패배 기록 및 강등 체크 ★

        패배할 때마다 호출됩니다.
        연속 패배가 많으면 강등될 수 있습니다.

        Returns:
            True if demoted to previous level, False otherwise
        """
        self.losses_at_current_level += 1
        self.games_at_current_level += 1

        wins_required = self.wins_required_per_level.get(self.current_idx, 10)

        print(f"\n{'='*70}")
        print(f"[CURRICULUM] 패배 (승리: {self.wins_at_current_level}/{wins_required})")
        print(f"  현재 단계: {self.get_level_name()} (Level {self.current_idx + 1}/{len(self.levels)})")
        print(f"{'='*70}\n")

        # 강등 체크: 10게임 이상 & 승률 20% 미만
        if self.games_at_current_level >= 10:
            win_rate = self.wins_at_current_level / self.games_at_current_level
            if win_rate < self.demotion_threshold:
                return self._demote_to_previous_level()

        self.save_level()
        return False

    def _promote_to_next_level(self) -> bool:
        """다음 단계로 승격."""
        if self.current_idx >= len(self.levels) - 1:
            print(f"\n{'★'*35}")
            print(f"[CURRICULUM] 🏆 최고 난이도 마스터!")
            print(f"  모든 단계를 완료했습니다!")
            print(f"{'★'*35}\n")
            self.save_level()
            return False

        old_difficulty = self.levels[self.current_idx].name
        self.current_idx += 1
        new_difficulty = self.levels[self.current_idx].name

        # 새 레벨 초기화
        old_wins = self.wins_at_current_level
        self.wins_at_current_level = 0
        self.losses_at_current_level = 0
        self.games_at_current_level = 0

        self.save_level()

        wins_required = self.wins_required_per_level.get(self.current_idx, 10)

        print(f"\n{'★'*35}")
        print(f"[CURRICULUM] 🎊 단계 승격!")
        print(f"  {old_difficulty} -> {new_difficulty}")
        print(f"  이전 단계 승리: {old_wins}승")
        print(f"  다음 목표: {wins_required}승 달성하기")
        print(f"{'★'*35}\n")

        return True

    def _demote_to_previous_level(self) -> bool:
        """이전 단계로 강등."""
        if self.current_idx <= 0:
            self.save_level()
            return False

        old_difficulty = self.levels[self.current_idx].name
        self.current_idx -= 1
        new_difficulty = self.levels[self.current_idx].name

        # 새 레벨 초기화
        self.wins_at_current_level = 0
        self.losses_at_current_level = 0
        self.games_at_current_level = 0

        self.save_level()

        wins_required = self.wins_required_per_level.get(self.current_idx, 10)

        print(f"\n{'='*70}")
        print(f"[CURRICULUM] 📉 난이도 하향 (연습 더 필요)")
        print(f"  {old_difficulty} -> {new_difficulty}")
        print(f"  목표: {wins_required}승 달성하기")
        print(f"{'='*70}\n")

        return True

    def check_promotion(self, win_rate: float, total_games: int) -> bool:
        """
        Check if AI should be promoted to next difficulty.
        (백업 시스템: record_win/record_loss 사용 권장)

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
                self.wins_at_current_level = 0
                self.losses_at_current_level = 0
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
        wins_required = self.wins_required_per_level.get(self.current_idx, 10)

        return {
            "current_level": self.current_idx + 1,
            "total_levels": len(self.levels),
            "current_difficulty": current_difficulty.name,
            "level_name": self.get_level_name(),
            "games_at_current_level": self.games_at_current_level,
            "wins_at_current_level": self.wins_at_current_level,
            "losses_at_current_level": self.losses_at_current_level,
            "wins_required": wins_required,
            "wins_remaining": max(0, wins_required - self.wins_at_current_level),
            "min_games_required": min_games,
            "promotion_threshold": self.promotion_threshold,
            "demotion_threshold": self.demotion_threshold,
            "final_goal": "Beat CheatInsane AI!",
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
