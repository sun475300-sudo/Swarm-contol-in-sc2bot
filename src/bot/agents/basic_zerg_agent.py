# -*- coding: utf-8 -*-
"""
Basic Zerg Agent - A simplified Zerg agent that works without SC2 runtime.
"""

from typing import Dict, Any
from ..strategy.intel_manager import IntelManager
from ..strategy.strategy_manager import StrategyManager, StrategyDecision
from .base_agent import BaseAgent


class BasicZergAgent(BaseAgent):
    """
    SC2 없이도 동작 가능한 추상화된 Zerg 에이전트.
    관측 obs(dict)를 받아 문자열 action을 반환한다.
    
    This agent implements a basic decision-making loop:
    1. Update intelligence from observation
    2. Make strategic decision
    3. Execute low-level action based on decision
    """

    def __init__(self) -> None:
        """Initialize BasicZergAgent with intel and strategy managers."""
        self.intel = IntelManager()
        self.strategy = StrategyManager(self.intel)

    def reset(self) -> None:
        """Reset agent state between episodes."""
        self.intel.reset()
        super().reset()

    def on_step(self, obs: Dict[str, Any]) -> str:
        """
        Process observation and return action.
        
        Args:
            obs: Observation dictionary containing game state
            
        Returns:
            Action string (e.g., "train_drone", "train_zergling", "wait")
        """
        # Update intelligence from observation
        self.intel.update_from_obs(obs)
        
        # Make strategic decision
        decision = self.strategy.decide()
        
        # Execute low-level action
        return self._low_level_action(decision, obs)

    def _low_level_action(self, decision: StrategyDecision, obs: Dict[str, Any]) -> str:
        """
        Convert strategic decision to low-level action.
        
        Args:
            decision: Strategic decision from StrategyManager
            obs: Current observation
            
        Returns:
            Action string to execute
        """
        minerals = obs.get("minerals", 0)
        gas = obs.get("gas", 0)
        supply_used = obs.get("food_used", 0)
        supply_cap = obs.get("food_cap", 15)

        # Defense mode: build defensive structures or train defensive units
        if decision.mode == "defend":
            if minerals >= 100 and supply_used < supply_cap - 2:
                return "build_spine"
            elif minerals >= 50 and supply_used < supply_cap - 1:
                return "train_zergling"
            else:
                return "wait"

        # Army mode: train combat units
        if decision.mode == "army":
            if decision.tech_focus == "anti_air":
                if minerals >= 150 and gas >= 100 and supply_used < supply_cap - 2:
                    return "train_queen"
                elif minerals >= 50 and supply_used < supply_cap - 1:
                    return "train_zergling"
            elif decision.tech_focus == "mixed":
                if minerals >= 75 and gas >= 25 and supply_used < supply_cap - 2:
                    return "train_roach"
                elif minerals >= 50 and supply_used < supply_cap - 1:
                    return "train_zergling"
            else:  # ground
                if minerals >= 50 and supply_used < supply_cap - 1:
                    return "train_zergling"
            return "wait"

        # Economy mode: train workers and expand
        if decision.mode == "eco":
            if minerals >= 300 and obs.get("base_count", 1) < 3:
                return "expand"
            elif minerals >= 50 and supply_used < supply_cap - 1:
                return "train_drone"
            else:
                return "wait"

        # Expand mode: build new base
        if decision.mode == "expand":
            if minerals >= 300:
                return "expand"
            elif minerals >= 50 and supply_used < supply_cap - 1:
                return "train_drone"
            else:
                return "wait"

        # All-in mode: attack move
        if decision.mode == "all_in":
            if supply_used >= supply_cap * 0.9:
                return "attack_move"
            elif minerals >= 50 and supply_used < supply_cap - 1:
                return "train_zergling"
            else:
                return "wait"

        # Default: wait
        return "wait"
