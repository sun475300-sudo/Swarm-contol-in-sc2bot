# -*- coding: utf-8 -*-
"""
Telemetry Logger - Training statistics and data recording system
Collects and stores gameplay data for performance analysis and learning improvement.

Core features:
    1. In-game telemetry data collection (every 100 frames)
    2. Final statistics saving at game end
    3. JSON/CSV format data export
    4. Win rate and match history tracking
"""

import csv
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sc2.data import Result
from sc2.ids.unit_typeid import UnitTypeId


class TelemetryLogger:
    """Logger for training statistics and telemetry data"""

    def __init__(self, bot: Any, instance_id: int = 0):
        """
        Initialize TelemetryLogger

        Args:
            bot: WickedZergBotPro instance
            instance_id: Instance ID (for file naming)
        """
        self.bot = bot
        self.instance_id = instance_id

        # Telemetry data storage
        self.telemetry_data: List[Dict[str, Any]] = []
        self.telemetry_file = f"telemetry_{self.instance_id}.json"

        # Game log
        self.game_log: List[Dict[str, Any]] = []

        # Statistics file
        self.stats_file = "training_stats.json"

        # Win/loss counter
        self.total_games = 0
        self.wins = 0
        self.losses = 0

        print(f"[TELEMETRY] Logger initialized: {self.telemetry_file}")

    def should_log_telemetry(self, iteration: int) -> bool:
        """
        Determine if telemetry should be logged

        Args:
            iteration: Current game frame

        Returns:
            bool: Whether to log (every 100 frames)
        """
        return iteration % 100 == 0

    def log_game_state(self, combat_unit_types: set) -> None:
        """
        Log current game state to telemetry

        Args:
            combat_unit_types: Set of combat unit types
        """
        try:
            bot = self.bot

            # Calculate combat unit count (optimized: whitelist approach)
            army_units = bot.units.filter(lambda u: u.type_id in combat_unit_types)
            army_count = army_units.amount if hasattr(army_units, "amount") else len(army_units)

            # Calculate enemy army count
            enemy_units = getattr(bot, "enemy_units", None)
            enemy_army_count = 0
            if enemy_units:
                enemy_army_count = sum(
                    1
                    for u in enemy_units
                    if hasattr(u, "can_attack")
                    and u.can_attack
                    and not getattr(u, "is_structure", False)
                )

            # Worker count
            workers = bot.workers
            drone_count = workers.amount if hasattr(workers, "amount") else len(workers)

            # Larva count
            larvae = bot.units(UnitTypeId.LARVA)
            larva_count = larvae.amount if hasattr(larvae, "amount") else len(larvae)

            # Queen count and energy
            queens = bot.units(UnitTypeId.QUEEN)
            queen_count = queens.amount if hasattr(queens, "amount") else len(queens)
            queen_energy = (
                sum(q.energy for q in queens if hasattr(q, "energy")) if queen_count > 0 else 0
            )

            # Telemetry entry
            log_entry = {
                "time": int(bot.time),
                "iteration": bot.iteration,
                "minerals": bot.minerals,
                "vespene": bot.vespene,
                "army_count": army_count,
                "army_supply": bot.supply_army,
                "drone_count": drone_count,
                "larva_count": larva_count,
                "queen_count": queen_count,
                "queen_energy": queen_energy,
                "enemy_army_seen": enemy_army_count,
                "supply_used": bot.supply_used,
                "supply_cap": bot.supply_cap,
                "supply_left": bot.supply_left,
                "townhall_count": bot.townhalls.amount
                if hasattr(bot.townhalls, "amount")
                else len(bot.townhalls),
                "game_phase": bot.game_phase.name
                if hasattr(bot.game_phase, "name")
                else str(bot.game_phase),
            }

            self.telemetry_data.append(log_entry)

            # Memory management: keep only last 1000 entries
            if len(self.telemetry_data) > 1000:
                self.telemetry_data = self.telemetry_data[-1000:]

        except Exception as e:
            if bot.iteration % 500 == 0:
                print(f"[WARNING] Telemetry logging error: {e}")

    async def save_telemetry(self) -> None:
        """Save telemetry data to JSON and CSV files"""
        try:
            if not self.telemetry_data:
                print("[TELEMETRY] No data to save")
                return

            # Save as JSON
            with open(self.telemetry_file, "w", encoding="utf-8") as f:
                json.dump(self.telemetry_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            csv_file = self.telemetry_file.replace(".json", ".csv")
            if self.telemetry_data:
                with open(csv_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=self.telemetry_data[0].keys())
                    writer.writeheader()
                    writer.writerows(self.telemetry_data)

            print(f"[TELEMETRY] Data saved: {self.telemetry_file}, {csv_file}")

        except Exception as e:
            print(f"[WARNING] Telemetry save error: {e}")

    def record_game_result(
        self, game_result: Result, loss_reason: str, loss_details: Dict[str, Any]
    ) -> None:
        """
        Record game result to training_stats.json

        Args:
            game_result: Game result (Victory/Defeat/Tie)
            loss_reason: Reason for loss
            loss_details: Detailed loss information
        """
        try:
            bot = self.bot

            # Convert result to string
            result_str = str(game_result)
            if str(game_result) == "Victory":
                result_str = "Victory"
                self.wins += 1
            elif str(game_result) == "Defeat":
                result_str = "Defeat"
                self.losses += 1
            else:
                result_str = "Tie"

            self.total_games += 1

            # Check opponent race
            opponent_race_str = "Unknown"
            if hasattr(bot, "opponent_race") and bot.opponent_race:
                opponent_race_str = str(bot.opponent_race)
            elif hasattr(bot, "intel") and bot.intel and hasattr(bot.intel, "enemy"):
                if hasattr(bot.intel.enemy, "race"):
                    opponent_race_str = str(bot.intel.enemy.race)

            # Check persona
            personality = getattr(bot, "personality", "unknown")

            # Game data
            log_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "instance_id": self.instance_id,
                "personality": personality,
                "opponent_race": opponent_race_str,
                "result": result_str,
                "loss_reason": loss_reason,
                "game_time": int(bot.time),
                "final_supply": bot.supply_used,
                "minerals": bot.minerals,
                "vespene": bot.vespene,
                "worker_count": loss_details.get("worker_count", 0),
                "townhall_count": loss_details.get("townhall_count", 0),
                "army_count": loss_details.get("army_count", 0),
            }

            # Append to training_stats.json (append mode)
            with open(self.stats_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")

            print(f"[STATS] {personality} ({self.instance_id}): {loss_reason} -> {self.stats_file}")

        except Exception as e:
            print(f"[WARNING] Failed to record statistics: {e}")

    def get_win_rate(self) -> float:
        """
        Calculate current win rate

        Returns:
            float: Win rate (0.0 ~ 1.0)
        """
        if self.total_games == 0:
            return 0.0
        return self.wins / self.total_games

    def get_statistics_summary(self) -> Dict[str, Any]:
        """
        Get statistics summary

        Returns:
            Dict: Statistics information
        """
        win_rate = self.get_win_rate()

        return {
            "total_games": self.total_games,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": win_rate,
            "win_rate_percent": f"{win_rate * 100:.1f}%",
        }

    def print_statistics(self) -> None:
        """Print statistics information"""
        stats = self.get_statistics_summary()

        print("\n" + "=" * 70)
        print("Training Statistics")
        print("=" * 70)
        print(f"Total games: {stats['total_games']}")
        print(f"Wins: {stats['wins']} | Losses: {stats['losses']}")
        print(f"Win rate: {stats['win_rate_percent']}")
        print("=" * 70 + "\n")

    def get_final_stats_dict(self) -> Optional[Dict[str, Any]]:
        """
        Create final statistics dictionary at game end

        Returns:
            Dict: Final statistics (None if failed)
        """
        try:
            bot = self.bot

            # Calculate unit counts (optimized: use amount attribute)
            workers_count = (
                bot.workers.amount if hasattr(bot.workers, "amount") else len(bot.workers)
            )
            townhalls_count = (
                bot.townhalls.amount if hasattr(bot.townhalls, "amount") else len(bot.townhalls)
            )

            zerglings = bot.units(UnitTypeId.ZERGLING)
            hydras = bot.units(UnitTypeId.HYDRALISK)
            roaches = bot.units(UnitTypeId.ROACH)
            lurkers = bot.units(UnitTypeId.LURKER)

            zerglings_count = zerglings.amount if hasattr(zerglings, "amount") else len(zerglings)
            hydras_count = hydras.amount if hasattr(hydras, "amount") else len(hydras)
            roaches_count = roaches.amount if hasattr(roaches, "amount") else len(roaches)
            lurkers_count = lurkers.amount if hasattr(lurkers, "amount") else len(lurkers)

            return {
                "minerals": bot.minerals,
                "vespene": bot.vespene,
                "supply_used": bot.supply_used,
                "supply_cap": bot.supply_cap,
                "supply_army": bot.supply_army,
                "workers": workers_count,
                "bases": townhalls_count,
                "zerglings": zerglings_count,
                "hydralisks": hydras_count,
                "roaches": roaches_count,
                "lurkers": lurkers_count,
                "game_time": int(bot.time),
            }

        except Exception as e:
            print(f"[WARNING] Failed to create final statistics: {e}")
            return None

    def clear_telemetry(self) -> None:
        """Clear telemetry data (at new game start)"""
        self.telemetry_data.clear()
        self.game_log.clear()
        print(f"[TELEMETRY] Data cleared for new game")
