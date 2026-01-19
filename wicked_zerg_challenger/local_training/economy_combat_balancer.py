# -*- coding: utf-8 -*-
"""
Economy-Combat Balance Controller

Dynamically adjusts the ratio between economy (drones) and combat units
based on game state, threat level, and resource availability.
"""

from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        DRONE = "DRONE"
        ZERGLING = "ZERGLING"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        OVERLORD = "OVERLORD"


class BalanceMode(Enum):
    """Economy-Combat balance modes"""
    FULL_ECONOMY = "full_economy"  # 100% economy focus
    ECONOMY_FOCUS = "economy_focus"  # 70% economy, 30% combat
    BALANCED = "balanced"  # 50% economy, 50% combat
    COMBAT_FOCUS = "combat_focus"  # 30% economy, 70% combat
    FULL_COMBAT = "full_combat"  # 100% combat focus


@dataclass
class BalanceState:
    """Current balance state"""
    mode: BalanceMode
    drone_ratio: float  # 0.0 to 1.0
    army_ratio: float  # 0.0 to 1.0
    threat_level: float  # 0.0 to 1.0
    economy_score: float  # 0.0 to 1.0
    reason: str


class EconomyCombatBalancer:
    """
    Balances economy (drones) and combat units based on game state
    """
    
    def __init__(self, bot: Any):
        self.bot = bot
        self.current_state: Optional[BalanceState] = None
        self.last_update_time = 0.0
        self.update_interval = 5.0  # Update every 5 seconds
        
        # Target ratios by mode
        self.mode_ratios = {
            BalanceMode.FULL_ECONOMY: (1.0, 0.0),
            BalanceMode.ECONOMY_FOCUS: (0.7, 0.3),
            BalanceMode.BALANCED: (0.5, 0.5),
            BalanceMode.COMBAT_FOCUS: (0.3, 0.7),
            BalanceMode.FULL_COMBAT: (0.0, 1.0),
        }
    
    def get_balance_state(self) -> BalanceState:
        """
        Calculate current balance state based on game conditions
        
        Returns:
            BalanceState with recommended drone/army ratio
        """
        b = self.bot
        current_time = getattr(b, "time", 0.0)
        
        # Only update every update_interval seconds
        if current_time - self.last_update_time < self.update_interval:
            if self.current_state:
                return self.current_state
        
        # Calculate threat level
        threat_level = self._calculate_threat_level()
        
        # Calculate economy score
        economy_score = self._calculate_economy_score()
        
        # Determine mode based on game state
        mode, reason = self._determine_mode(threat_level, economy_score, current_time)
        
        # Get ratios for this mode
        drone_ratio, army_ratio = self.mode_ratios[mode]
        
        # Adjust ratios based on specific conditions
        drone_ratio, army_ratio = self._adjust_ratios(
            drone_ratio, army_ratio, threat_level, economy_score, current_time
        )
        
        self.current_state = BalanceState(
            mode=mode,
            drone_ratio=drone_ratio,
            army_ratio=army_ratio,
            threat_level=threat_level,
            economy_score=economy_score,
            reason=reason
        )
        
        self.last_update_time = current_time
        
        return self.current_state
    
    def _calculate_threat_level(self) -> float:
        """Calculate threat level (0.0 = safe, 1.0 = critical danger)"""
        b = self.bot
        threat = 0.0
        
        # 1. Enemy units near our bases
        if hasattr(b, "units") and hasattr(b, "enemy_units"):
            enemy_units = b.enemy_units if hasattr(b, "enemy_units") else []
            our_units = b.units if hasattr(b, "units") else []
            
            if enemy_units and hasattr(enemy_units, "closer_than"):
                # Check if enemy units are near our bases
                if hasattr(b, "townhalls") and b.townhalls.exists:
                    for th in b.townhalls:
                        nearby_enemies = enemy_units.closer_than(15, th.position)
                        if nearby_enemies.exists:
                            threat += 0.3
                            break
        
        # 2. Enemy army size vs our army size
        if hasattr(b, "enemy_units") and hasattr(b, "units"):
            enemy_army = self._count_army_units(b.enemy_units if hasattr(b, "enemy_units") else [])
            our_army = self._count_army_units(b.units if hasattr(b, "units") else [])
            
            if enemy_army > 0:
                army_ratio = our_army / max(enemy_army, 1)
                if army_ratio < 0.5:
                    threat += 0.4  # Enemy has 2x our army
                elif army_ratio < 0.7:
                    threat += 0.2  # Enemy has 1.4x our army
        
        # 3. Early game rush detection (first 3 minutes)
        current_time = getattr(b, "time", 0.0)
        if current_time < 180:  # First 3 minutes
            if hasattr(b, "enemy_units"):
                enemy_units = b.enemy_units if hasattr(b, "enemy_units") else []
                if enemy_units and hasattr(enemy_units, "amount"):
                    enemy_count = enemy_units.amount
                    if enemy_count > 5:  # Early rush
                        threat += 0.3
        
        # 4. Supply block increases threat (can't make army)
        supply_left = getattr(b, "supply_left", 0)
        if supply_left < 2:
            threat += 0.1
        
        return min(threat, 1.0)
    
    def _calculate_economy_score(self) -> float:
        """Calculate economy score (0.0 = poor, 1.0 = excellent)"""
        b = self.bot
        score = 0.0
        
        # 1. Drone count
        if hasattr(b, "units"):
            drones = b.units(UnitTypeId.DRONE) if hasattr(b, "units") else []
            drone_count = drones.amount if hasattr(drones, "amount") else len(list(drones))
            
            # Target: 16 drones by 2 min, 24 by 4 min, 30+ by 6 min
            current_time = getattr(b, "time", 0.0)
            if current_time < 120:
                target_drones = 16
            elif current_time < 240:
                target_drones = 24
            else:
                target_drones = 30
            
            if drone_count >= target_drones:
                score += 0.4
            elif drone_count >= target_drones * 0.8:
                score += 0.3
            elif drone_count >= target_drones * 0.6:
                score += 0.2
            else:
                score += 0.1
        
        # 2. Base count
        if hasattr(b, "townhalls"):
            base_count = b.townhalls.amount if hasattr(b.townhalls, "amount") else len(list(b.townhalls))
            if base_count >= 2:
                score += 0.3
            elif base_count >= 1:
                score += 0.15
        
        # 3. Resource income rate
        minerals = getattr(b, "minerals", 0)
        vespene = getattr(b, "vespene", 0)
        current_time = getattr(b, "time", 0.0)
        
        if current_time > 60:  # After 1 minute
            # Good income if we have resources accumulating
            if minerals > 300 or vespene > 200:
                score += 0.2
            elif minerals > 200 or vespene > 100:
                score += 0.1
        
        # 4. Gas extractors
        if hasattr(b, "structures"):
            extractors = b.structures(UnitTypeId.EXTRACTOR) if hasattr(b, "structures") else []
            if extractors.exists if hasattr(extractors, "exists") else len(list(extractors)) > 0:
                score += 0.1
        
        return min(score, 1.0)
    
    def _determine_mode(
        self, threat_level: float, economy_score: float, current_time: float
    ) -> Tuple[BalanceMode, str]:
        """Determine balance mode based on game state"""
        
        # Early game (first 2 minutes): Focus on economy
        if current_time < 120:
            if threat_level > 0.5:
                return BalanceMode.BALANCED, "Early game with threat - balanced"
            return BalanceMode.ECONOMY_FOCUS, "Early game - economy focus"
        
        # Mid game (2-6 minutes): Dynamic based on threat
        if current_time < 360:
            if threat_level > 0.7:
                return BalanceMode.COMBAT_FOCUS, "High threat - combat focus"
            elif threat_level > 0.4:
                return BalanceMode.BALANCED, "Moderate threat - balanced"
            elif economy_score < 0.5:
                return BalanceMode.ECONOMY_FOCUS, "Weak economy - economy focus"
            else:
                return BalanceMode.BALANCED, "Good economy - balanced"
        
        # Late game (6+ minutes): Usually balanced or combat focus
        if threat_level > 0.6:
            return BalanceMode.COMBAT_FOCUS, "Late game high threat - combat focus"
        elif economy_score < 0.6:
            return BalanceMode.ECONOMY_FOCUS, "Late game weak economy - economy focus"
        else:
            return BalanceMode.BALANCED, "Late game - balanced"
    
    def _adjust_ratios(
        self, drone_ratio: float, army_ratio: float,
        threat_level: float, economy_score: float, current_time: float
    ) -> Tuple[float, float]:
        """Fine-tune ratios based on specific conditions"""
        
        # Emergency: Enemy units in our base
        if hasattr(self.bot, "enemy_units") and hasattr(self.bot, "townhalls"):
            enemy_units = self.bot.enemy_units if hasattr(self.bot, "enemy_units") else []
            if enemy_units and hasattr(enemy_units, "closer_than"):
                if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                    for th in self.bot.townhalls:
                        nearby = enemy_units.closer_than(10, th.position)
                        if nearby.exists:
                            # Emergency: Stop making drones, make army
                            drone_ratio = max(0.0, drone_ratio - 0.3)
                            army_ratio = min(1.0, army_ratio + 0.3)
                            break
        
        # Very low economy: Prioritize drones
        if economy_score < 0.3 and threat_level < 0.4:
            drone_ratio = min(1.0, drone_ratio + 0.2)
            army_ratio = max(0.0, army_ratio - 0.2)
        
        # Very high threat: Prioritize army
        if threat_level > 0.8:
            drone_ratio = max(0.0, drone_ratio - 0.2)
            army_ratio = min(1.0, army_ratio + 0.2)
        
        # Ensure ratios sum to 1.0
        total = drone_ratio + army_ratio
        if total > 0:
            drone_ratio /= total
            army_ratio /= total
        
        return drone_ratio, army_ratio
    
    def _count_army_units(self, units) -> int:
        """Count army units (non-worker, non-structure)"""
        if not units:
            return 0
        
        army_types = [
            UnitTypeId.ZERGLING, UnitTypeId.ROACH, UnitTypeId.HYDRALISK,
            UnitTypeId.MUTALISK, UnitTypeId.ULTRALISK, UnitTypeId.BROODLORD
        ]
        
        count = 0
        for unit_type in army_types:
            try:
                unit_group = units.of_type(unit_type) if hasattr(units, "of_type") else []
                if hasattr(unit_group, "amount"):
                    count += unit_group.amount
                else:
                    count += len(list(unit_group))
            except Exception:
                pass
        
        return count
    
    def should_make_drone(self) -> bool:
        """
        Determine if we should make a drone or army unit
        
        Returns:
            True if should make drone, False if should make army
        """
        state = self.get_balance_state()
        
        # Use random selection based on ratio
        import random
        threshold = state.drone_ratio
        
        # Log decision periodically
        b = self.bot
        if hasattr(b, "iteration") and b.iteration % 100 == 0:
            print(f"[BALANCE] Mode: {state.mode.value}, Drone: {state.drone_ratio:.1%}, "
                  f"Army: {state.army_ratio:.1%}, Threat: {state.threat_level:.1%}, "
                  f"Economy: {state.economy_score:.1%}, Reason: {state.reason}")
        
        return random.random() < threshold
    
    def get_target_drone_count(self) -> int:
        """Get target drone count based on current balance state"""
        state = self.get_balance_state()
        current_time = getattr(self.bot, "time", 0.0)
        
        # Base target by time
        if current_time < 120:
            base_target = 16
        elif current_time < 240:
            base_target = 24
        elif current_time < 360:
            base_target = 30
        else:
            base_target = 40
        
        # Adjust based on mode
        if state.mode == BalanceMode.FULL_ECONOMY:
            return int(base_target * 1.2)
        elif state.mode == BalanceMode.ECONOMY_FOCUS:
            return int(base_target * 1.1)
        elif state.mode == BalanceMode.COMBAT_FOCUS:
            return int(base_target * 0.8)
        elif state.mode == BalanceMode.FULL_COMBAT:
            return int(base_target * 0.6)
        else:
            return base_target
