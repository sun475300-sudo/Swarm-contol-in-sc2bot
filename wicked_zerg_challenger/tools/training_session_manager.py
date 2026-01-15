# -*- coding: utf-8 -*-
"""
Training Session Manager - Enhanced training process management

This module provides comprehensive tracking, statistics, and adaptive improvements
for the continuous training loop.

Features:
1. Game statistics tracking (win rate, average time, etc.)
2. Learning data validation and backup
3. Adaptive difficulty adjustment
4. Error recovery and resilience
5. Performance monitoring
6. Learning data quality control
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque


@dataclass
class GameResult:
    """Single game result data"""
    game_id: int
    timestamp: str
    map_name: str
    opponent_race: str
    difficulty: str
    result: str  # "Victory" or "Defeat"
    game_time: float  # seconds
    build_order_score: Optional[float] = None
    loss_reason: Optional[str] = None
    parameters_updated: int = 0


@dataclass
class TrainingSessionStats:
    """Overall training session statistics"""
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    average_game_time: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    current_difficulty: str = "Hard"
    total_parameters_updated: int = 0
    last_10_games_win_rate: float = 0.0
    best_win_rate: float = 0.0
    worst_win_rate: float = 100.0


class TrainingSessionManager:
    """
    Enhanced training session manager with comprehensive tracking and adaptive improvements
    """
    
    def __init__(self, stats_file: Optional[Path] = None):
        """
        Initialize TrainingSessionManager
        
        Args:
            stats_file: Path to save training statistics (default: local_training/scripts/training_session_stats.json)
        """
        if stats_file is None:
            script_dir = Path(__file__).parent.parent
            stats_file = script_dir / "local_training" / "scripts" / "training_session_stats.json"
        
        self.stats_file = stats_file
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Game history (keep last 100 games)
        self.game_history: deque = deque(maxlen=100)
        
        # Current session statistics
        self.session_stats = TrainingSessionStats()
        
        # Load existing statistics
        self._load_stats()
        
        # Backup directory for learning data
        self.backup_dir = self.stats_file.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Error recovery tracking
        self.error_history: deque = deque(maxlen=20)
        self.consecutive_errors = 0
        
        print(f"[TRAINING MANAGER] Initialized - Stats file: {self.stats_file}")
        print(f"[TRAINING MANAGER] Current session: {self.session_stats.total_games} games, "
              f"Win rate: {self.session_stats.win_rate:.1f}%")
    
    def _load_stats(self) -> None:
        """Load existing training statistics"""
        if not self.stats_file.exists():
            return
        
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load session stats
            if "session_stats" in data:
                self.session_stats = TrainingSessionStats(**data["session_stats"])
            
            # Load game history
            if "game_history" in data:
                self.game_history = deque([
                    GameResult(**game) for game in data["game_history"]
                ], maxlen=100)
            
            print(f"[TRAINING MANAGER] Loaded {len(self.game_history)} previous games")
        except Exception as e:
            print(f"[WARNING] Failed to load training stats: {e}")
    
    def _save_stats(self) -> None:
        """Save current training statistics"""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "session_stats": asdict(self.session_stats),
                "game_history": [asdict(game) for game in self.game_history]
            }
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARNING] Failed to save training stats: {e}")
    
    def record_game_result(
        self,
        game_id: int,
        map_name: str,
        opponent_race: str,
        difficulty: str,
        result: str,
        game_time: float,
        build_order_score: Optional[float] = None,
        loss_reason: Optional[str] = None,
        parameters_updated: int = 0
    ) -> None:
        """
        Record a game result and update statistics
        
        Args:
            game_id: Game number
            map_name: Map name
            opponent_race: Opponent race
            difficulty: Difficulty level
            result: "Victory" or "Defeat"
            game_time: Game duration in seconds
            build_order_score: Build order comparison score (0.0-1.0)
            loss_reason: Reason for loss (if defeat)
            parameters_updated: Number of parameters updated
        """
        game_result = GameResult(
            game_id=game_id,
            timestamp=datetime.now().isoformat(),
            map_name=map_name,
            opponent_race=opponent_race,
            difficulty=difficulty,
            result=result,
            game_time=game_time,
            build_order_score=build_order_score,
            loss_reason=loss_reason,
            parameters_updated=parameters_updated
        )
        
        # Add to history
        self.game_history.append(game_result)
        
        # Update session statistics
        self.session_stats.total_games += 1
        if result == "Victory":
            self.session_stats.wins += 1
            self.session_stats.consecutive_wins += 1
            self.session_stats.consecutive_losses = 0
        else:
            self.session_stats.losses += 1
            self.session_stats.consecutive_losses += 1
            self.session_stats.consecutive_wins = 0
        
        # Calculate win rate
        if self.session_stats.total_games > 0:
            self.session_stats.win_rate = (
                self.session_stats.wins / self.session_stats.total_games * 100
            )
        
        # Update best/worst win rate
        if self.session_stats.win_rate > self.session_stats.best_win_rate:
            self.session_stats.best_win_rate = self.session_stats.win_rate
        if self.session_stats.win_rate < self.session_stats.worst_win_rate:
            self.session_stats.worst_win_rate = self.session_stats.win_rate
        
        # Calculate average game time
        total_time = sum(game.game_time for game in self.game_history)
        self.session_stats.average_game_time = (
            total_time / len(self.game_history) if self.game_history else 0.0
        )
        
        # Calculate last 10 games win rate
        if len(self.game_history) >= 10:
            last_10 = list(self.game_history)[-10:]
            last_10_wins = sum(1 for g in last_10 if g.result == "Victory")
            self.session_stats.last_10_games_win_rate = last_10_wins / 10 * 100
        else:
            self.session_stats.last_10_games_win_rate = self.session_stats.win_rate
        
        # Update current difficulty
        self.session_stats.current_difficulty = difficulty
        
        # Update total parameters updated
        self.session_stats.total_parameters_updated += parameters_updated
        
        # Save statistics
        self._save_stats()
        
        # Print summary
        self._print_game_summary(game_result)
    
    def _print_game_summary(self, game_result: GameResult) -> None:
        """Print game result summary"""
        print("\n" + "=" * 70)
        print("? [TRAINING SESSION] GAME RESULT SUMMARY")
        print("=" * 70)
        print(f"Game #{game_result.game_id}: {game_result.result}")
        print(f"Map: {game_result.map_name} | Opponent: {game_result.opponent_race} | "
              f"Difficulty: {game_result.difficulty}")
        print(f"Game Time: {game_result.game_time:.1f}s")
        if game_result.build_order_score is not None:
            print(f"Build Order Score: {game_result.build_order_score:.2f}/1.0")
        if game_result.loss_reason:
            print(f"Loss Reason: {game_result.loss_reason}")
        if game_result.parameters_updated > 0:
            print(f"Parameters Updated: {game_result.parameters_updated}")
        print()
        print(f"Session Statistics:")
        print(f"  Total Games: {self.session_stats.total_games}")
        print(f"  Wins: {self.session_stats.wins} | Losses: {self.session_stats.losses}")
        print(f"  Win Rate: {self.session_stats.win_rate:.1f}%")
        print(f"  Last 10 Games Win Rate: {self.session_stats.last_10_games_win_rate:.1f}%")
        print(f"  Average Game Time: {self.session_stats.average_game_time:.1f}s")
        print(f"  Consecutive Wins: {self.session_stats.consecutive_wins}")
        print(f"  Consecutive Losses: {self.session_stats.consecutive_losses}")
        print(f"  Total Parameters Updated: {self.session_stats.total_parameters_updated}")
        print("=" * 70)
    
    def get_adaptive_difficulty(self) -> str:
        """
        Get adaptive difficulty based on recent performance
        
        Returns:
            Difficulty level ("Hard" or "VeryHard")
        """
        # If win rate is high (>70%), increase difficulty
        if self.session_stats.win_rate > 70.0:
            return "VeryHard"
        
        # If win rate is low (<30%), decrease difficulty
        if self.session_stats.win_rate < 30.0:
            return "Hard"
        
        # If last 10 games win rate is high, increase difficulty
        if self.session_stats.last_10_games_win_rate > 75.0:
            return "VeryHard"
        
        # If last 10 games win rate is low, decrease difficulty
        if self.session_stats.last_10_games_win_rate < 25.0:
            return "Hard"
        
        # Default: maintain current difficulty
        return self.session_stats.current_difficulty
    
    def backup_learning_data(self, learned_data_path: Path) -> Optional[Path]:
        """
        Backup learning data before update
        
        Args:
            learned_data_path: Path to learned_build_orders.json
            
        Returns:
            Path to backup file, or None if backup failed
        """
        if not learned_data_path.exists():
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"learned_build_orders_{timestamp}.json"
            
            shutil.copy2(learned_data_path, backup_file)
            print(f"[BACKUP] Learning data backed up to: {backup_file}")
            
            # Keep only last 10 backups
            backups = sorted(self.backup_dir.glob("learned_build_orders_*.json"))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    old_backup.unlink()
            
            return backup_file
        except Exception as e:
            print(f"[WARNING] Failed to backup learning data: {e}")
            return None
    
    def validate_learning_data(self, learned_data_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate learning data before use
        
        Args:
            learned_data_path: Path to learned_build_orders.json
            
        Returns:
            (is_valid, error_message)
        """
        if not learned_data_path.exists():
            return False, "Learning data file does not exist"
        
        try:
            with open(learned_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return False, "Learning data is not a dictionary"
            
            if "learned_parameters" not in data:
                return False, "Missing 'learned_parameters' key"
            
            params = data["learned_parameters"]
            if not isinstance(params, dict):
                return False, "'learned_parameters' is not a dictionary"
            
            # Validate parameter values (should be positive numbers)
            for param_name, value in params.items():
                if not isinstance(value, (int, float)):
                    return False, f"Parameter '{param_name}' is not a number"
                if value < 0:
                    return False, f"Parameter '{param_name}' is negative"
                if value > 200:  # Reasonable upper bound
                    return False, f"Parameter '{param_name}' is too large ({value})"
            
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def record_error(self, error_type: str, error_message: str) -> None:
        """
        Record an error for recovery analysis
        
        Args:
            error_type: Type of error (e.g., "AssertionError", "ImportError")
            error_message: Error message
        """
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message
        }
        
        self.error_history.append(error_record)
        self.consecutive_errors += 1
        
        # If too many consecutive errors, suggest stopping
        if self.consecutive_errors >= 5:
            print(f"\n[WARNING] {self.consecutive_errors} consecutive errors detected!")
            print("[WARNING] Consider stopping training to investigate issues.")
    
    def reset_error_count(self) -> None:
        """Reset consecutive error count after successful game"""
        self.consecutive_errors = 0
    
    def get_training_summary(self) -> str:
        """
        Get comprehensive training summary
        
        Returns:
            Formatted training summary string
        """
        summary_lines = [
            "\n" + "=" * 70,
            "? [TRAINING SESSION] COMPREHENSIVE SUMMARY",
            "=" * 70,
            f"Total Games: {self.session_stats.total_games}",
            f"Wins: {self.session_stats.wins} | Losses: {self.session_stats.losses}",
            f"Win Rate: {self.session_stats.win_rate:.1f}%",
            f"Best Win Rate: {self.session_stats.best_win_rate:.1f}%",
            f"Worst Win Rate: {self.session_stats.worst_win_rate:.1f}%",
            f"Last 10 Games Win Rate: {self.session_stats.last_10_games_win_rate:.1f}%",
            f"Average Game Time: {self.session_stats.average_game_time:.1f}s",
            f"Consecutive Wins: {self.session_stats.consecutive_wins}",
            f"Consecutive Losses: {self.session_stats.consecutive_losses}",
            f"Current Difficulty: {self.session_stats.current_difficulty}",
            f"Recommended Difficulty: {self.get_adaptive_difficulty()}",
            f"Total Parameters Updated: {self.session_stats.total_parameters_updated}",
            f"Consecutive Errors: {self.consecutive_errors}",
            "=" * 70
        ]
        
        return "\n".join(summary_lines)
