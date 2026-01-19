# -*- coding: utf-8 -*-
"""
Economy-Combat Balance Integration

Integrates the EconomyCombatBalancer into production decisions.
"""

from typing import Any, List, Optional
from pathlib import Path

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        DRONE = "DRONE"
        ZERGLING = "ZERGLING"
        ROACH = "ROACH"
        OVERLORD = "OVERLORD"
        LARVA = "LARVA"

try:
    from local_training.economy_combat_balancer import EconomyCombatBalancer, BalanceMode
    BALANCER_AVAILABLE = True
except ImportError:
    BALANCER_AVAILABLE = False
    EconomyCombatBalancer = None
    BalanceMode = None


class EconomyCombatBalanceIntegration:
    """
    Integrates economy-combat balance into production decisions
    """
    
    def __init__(self, bot: Any):
        self.bot = bot
        if BALANCER_AVAILABLE and EconomyCombatBalancer:
            try:
                self.balancer = EconomyCombatBalancer(bot)
            except Exception as e:
                print(f"[WARNING] Failed to initialize balancer: {e}")
                self.balancer = None
        else:
            self.balancer = None
    
    def should_make_drone(self, larvae_count: int, current_drones: int) -> bool:
        """
        Determine if we should make a drone or army unit
        
        Args:
            larvae_count: Number of available larvae
            current_drones: Current drone count
            
        Returns:
            True if should make drone, False if should make army
        """
        if not self.balancer:
            # Fallback: Simple rule
            current_time = getattr(self.bot, "time", 0.0)
            if current_time < 180:  # First 3 minutes
                return current_drones < 16
            return current_drones < 30
        
        return self.balancer.should_make_drone()
    
    def get_target_drone_count(self) -> int:
        """Get target drone count based on balance state"""
        if not self.balancer:
            # Fallback
            current_time = getattr(self.bot, "time", 0.0)
            if current_time < 120:
                return 16
            elif current_time < 240:
                return 24
            else:
                return 30
        
        return self.balancer.get_target_drone_count()
    
    def get_balance_info(self) -> Optional[dict]:
        """Get current balance state information"""
        if not self.balancer:
            return None
        
        state = self.balancer.get_balance_state()
        return {
            "mode": state.mode.value if state.mode else "unknown",
            "drone_ratio": state.drone_ratio,
            "army_ratio": state.army_ratio,
            "threat_level": state.threat_level,
            "economy_score": state.economy_score,
            "reason": state.reason
        }
