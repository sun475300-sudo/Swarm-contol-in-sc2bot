# -*- coding: utf-8 -*-
"""
Opening Strategy Manager

Manages diverse opening strategies to prevent predictable play patterns.
Implements various Zerg opening builds:
- 12 Pool (Aggressive)
- 15 Hatch (Economic)
- 16 Pool (Balanced)
- 17 Pool (Standard)
- 17 Pool Gas (Tech-focused)
"""

from typing import Any, Dict, Optional, List
from enum import Enum, auto
from dataclasses import dataclass
import random

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        HATCHERY = "HATCHERY"
        OVERLORD = "OVERLORD"
        DRONE = "DRONE"
        ZERGLING = "ZERGLING"


class OpeningStrategy(Enum):
    """Available opening strategies"""
    POOL_12 = auto()  # 12 Pool - Aggressive early rush
    HATCH_15 = auto()  # 15 Hatch - Economic fast expand
    POOL_16 = auto()  # 16 Pool - Balanced
    POOL_17 = auto()  # 17 Pool - Standard
    POOL_17_GAS = auto()  # 17 Pool Gas - Tech-focused
    RANDOM = auto()  # Random strategy selection


@dataclass
class StrategyParams:
    """Parameters for a specific opening strategy"""
    name: str
    pool_supply: float  # Supply to build Spawning Pool
    gas_supply: float  # Supply to build Gas Extractor
    expansion_supply: float  # Supply to build Natural Expansion
    overlord_timing: List[float]  # Supply timings for Overlords
    drone_priority: bool  # True = maximize drones, False = balance with army
    early_aggression: bool  # True = focus on early army, False = economy focus


class OpeningStrategyManager:
    """
    Manages opening strategy selection and execution
    
    Features:
    - Multiple opening strategies
    - Random or adaptive strategy selection
    - Strategy-specific parameters
    - Performance tracking per strategy
    """
    
    # Strategy definitions
    STRATEGIES = {
        OpeningStrategy.POOL_12: StrategyParams(
            name="12 Pool",
            pool_supply=12.0,
            gas_supply=0.0,  # No gas in 12 pool
            expansion_supply=0.0,  # No expansion in 12 pool
            overlord_timing=[13.0, 19.0, 25.0],
            drone_priority=False,
            early_aggression=True
        ),
        OpeningStrategy.HATCH_15: StrategyParams(
            name="15 Hatch",
            pool_supply=0.0,  # No pool, expand first
            gas_supply=0.0,  # No gas initially
            expansion_supply=15.0,
            overlord_timing=[16.0, 24.0, 30.0],
            drone_priority=True,
            early_aggression=False
        ),
        OpeningStrategy.POOL_16: StrategyParams(
            name="16 Pool",
            pool_supply=16.0,
            gas_supply=17.0,
            expansion_supply=30.0,
            overlord_timing=[17.0, 25.0, 31.0],
            drone_priority=True,
            early_aggression=False
        ),
        OpeningStrategy.POOL_17: StrategyParams(
            name="17 Pool",
            pool_supply=17.0,
            gas_supply=18.0,
            expansion_supply=30.0,
            overlord_timing=[18.0, 26.0, 32.0],
            drone_priority=True,
            early_aggression=False
        ),
        OpeningStrategy.POOL_17_GAS: StrategyParams(
            name="17 Pool Gas",
            pool_supply=17.0,
            gas_supply=17.0,  # Gas same time as pool
            expansion_supply=32.0,
            overlord_timing=[18.0, 26.0, 32.0],
            drone_priority=False,
            early_aggression=False
        ),
    }
    
    def __init__(self, bot: Any, strategy: Optional[OpeningStrategy] = None):
        self.bot = bot
        self.current_strategy: Optional[OpeningStrategy] = None
        self.strategy_params: Optional[StrategyParams] = None
        self.strategy_selected = False
        
        # Strategy performance tracking
        self.strategy_stats: Dict[str, Dict[str, float]] = {}
        
        # Select strategy
        if strategy:
            self.select_strategy(strategy)
        else:
            # Default: Random strategy
            self.select_random_strategy()
    
    def select_strategy(self, strategy: OpeningStrategy) -> None:
        """Select a specific opening strategy"""
        if strategy == OpeningStrategy.RANDOM:
            self.select_random_strategy()
        elif strategy in self.STRATEGIES:
            self.current_strategy = strategy
            self.strategy_params = self.STRATEGIES[strategy]
            self.strategy_selected = True
            
            if self.bot.iteration % 50 == 0:
                print(f"[OPENING_STRATEGY] Selected: {self.strategy_params.name}")
        else:
            # Fallback to standard
            self.select_strategy(OpeningStrategy.POOL_17)
    
    def select_random_strategy(self) -> None:
        """Randomly select an opening strategy"""
        strategies = [
            OpeningStrategy.POOL_12,
            OpeningStrategy.HATCH_15,
            OpeningStrategy.POOL_16,
            OpeningStrategy.POOL_17,
            OpeningStrategy.POOL_17_GAS
        ]
        
        # Weighted random selection (favor balanced strategies)
        weights = [0.1, 0.15, 0.25, 0.35, 0.15]  # 17 Pool most common
        selected = random.choices(strategies, weights=weights)[0]
        
        self.select_strategy(selected)
    
    def select_adaptive_strategy(self, enemy_race: Optional[str] = None) -> None:
        """
        Select strategy based on enemy race or game conditions
        
        Args:
            enemy_race: "Terran", "Protoss", or "Zerg"
        """
        if not self.strategy_selected:
            if enemy_race == "Terran":
                # Against Terran: Favor economic builds (they're slower)
                strategies = [OpeningStrategy.HATCH_15, OpeningStrategy.POOL_16, OpeningStrategy.POOL_17]
                weights = [0.4, 0.3, 0.3]
            elif enemy_race == "Protoss":
                # Against Protoss: Favor balanced builds (defend early pressure)
                strategies = [OpeningStrategy.POOL_16, OpeningStrategy.POOL_17, OpeningStrategy.POOL_17_GAS]
                weights = [0.3, 0.4, 0.3]
            elif enemy_race == "Zerg":
                # Against Zerg: Favor aggressive builds (mirror match)
                strategies = [OpeningStrategy.POOL_12, OpeningStrategy.POOL_16, OpeningStrategy.POOL_17]
                weights = [0.3, 0.4, 0.3]
            else:
                # Unknown: Random
                self.select_random_strategy()
                return
            
            selected = random.choices(strategies, weights=weights)[0]
            self.select_strategy(selected)
    
    def get_pool_supply(self) -> float:
        """Get Spawning Pool supply timing for current strategy"""
        if self.strategy_params:
            return self.strategy_params.pool_supply
        return 17.0  # Default
    
    def get_gas_supply(self) -> float:
        """Get Gas Extractor supply timing for current strategy"""
        if self.strategy_params:
            return self.strategy_params.gas_supply
        return 17.0  # Default
    
    def get_expansion_supply(self) -> float:
        """Get Natural Expansion supply timing for current strategy"""
        if self.strategy_params:
            return self.strategy_params.expansion_supply
        return 30.0  # Default
    
    def should_prioritize_drones(self) -> bool:
        """Whether to prioritize drone production"""
        if self.strategy_params:
            return self.strategy_params.drone_priority
        return True  # Default
    
    def should_early_aggression(self) -> bool:
        """Whether to focus on early army production"""
        if self.strategy_params:
            return self.strategy_params.early_aggression
        return False  # Default
    
    def get_overlord_timings(self) -> List[float]:
        """Get Overlord supply timings for current strategy"""
        if self.strategy_params:
            return self.strategy_params.overlord_timing
        return [18.0, 26.0, 32.0]  # Default
    
    def get_strategy_name(self) -> str:
        """Get current strategy name"""
        if self.strategy_params:
            return self.strategy_params.name
        return "Default"
    
    def record_strategy_result(self, result: str, game_time: float) -> None:
        """
        Record strategy performance
        
        Args:
            result: "Victory" or "Defeat"
            game_time: Game duration in seconds
        """
        if not self.strategy_params:
            return
        
        strategy_name = self.strategy_params.name
        
        if strategy_name not in self.strategy_stats:
            self.strategy_stats[strategy_name] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "total_time": 0.0,
                "avg_time": 0.0
            }
        
        stats = self.strategy_stats[strategy_name]
        stats["games"] += 1
        stats["total_time"] += game_time
        stats["avg_time"] = stats["total_time"] / stats["games"]
        
        if result == "Victory":
            stats["wins"] += 1
        else:
            stats["losses"] += 1
    
    def get_strategy_win_rate(self, strategy_name: str) -> float:
        """Get win rate for a specific strategy"""
        if strategy_name not in self.strategy_stats:
            return 0.0
        
        stats = self.strategy_stats[strategy_name]
        total = stats["wins"] + stats["losses"]
        if total == 0:
            return 0.0
        
        return stats["wins"] / total * 100.0
    
    def get_best_strategy(self) -> Optional[str]:
        """Get strategy with highest win rate"""
        if not self.strategy_stats:
            return None
        
        best_name = None
        best_win_rate = -1.0
        
        for name, stats in self.strategy_stats.items():
            total = stats["wins"] + stats["losses"]
            if total >= 5:  # Need at least 5 games for reliability
                win_rate = stats["wins"] / total
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    best_name = name
        
        return best_name
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """Get summary of all strategy performances"""
        summary = {
            "current_strategy": self.get_strategy_name(),
            "strategies": {}
        }
        
        for name, stats in self.strategy_stats.items():
            total = stats["wins"] + stats["losses"]
            win_rate = (stats["wins"] / total * 100.0) if total > 0 else 0.0
            
            summary["strategies"][name] = {
                "games": total,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "win_rate": win_rate,
                "avg_game_time": stats["avg_time"]
            }
        
        return summary
