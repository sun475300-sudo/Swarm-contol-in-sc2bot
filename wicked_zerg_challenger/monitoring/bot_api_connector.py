#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot API Connector - Real-time connection between bot and dashboard API server

This module provides a bridge between the running bot instance and the FastAPI
monitoring server, enabling real-time game state updates.
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Global bot connector instance
bot_connector: Optional['BotApiConnector'] = None


@dataclass
class GameState:
    """Game state data structure"""
    current_frame: int = 0
    game_status: str = "READY"
    is_running: bool = False
    minerals: int = 50
    vespene: int = 0
    supply_used: int = 12
    supply_cap: int = 15
    units: Dict[str, int] = None
    threat_level: str = "NONE"
    strategy_mode: str = "OPENING"
    map_name: str = "Unknown"
    timestamp: str = ""
    
    def __post_init__(self):
        if self.units is None:
            self.units = {}
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class CombatStats:
    """Combat statistics data structure"""
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    kda_ratio: float = 0.0
    avg_army_supply: float = 0.0
    enemy_killed_supply: int = 0
    supply_lost: int = 0


@dataclass
class LearningProgress:
    """Learning progress data structure"""
    episode: int = 0
    total_episodes: int = 1000
    progress_percent: float = 0.0
    average_reward: float = 0.0
    loss: float = 0.0
    training_hours: float = 0.0
    win_rate_trend: list = None
    training_logs: list = None
    
    def __post_init__(self):
        if self.win_rate_trend is None:
            self.win_rate_trend = []
        if self.training_logs is None:
            self.training_logs = []


class BotApiConnector:
    """
    Connector between bot and dashboard API server.
    
    This class maintains a connection to the FastAPI server and provides
    methods to update game state, combat stats, and learning progress.
    """
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initialize the bot API connector.
        
        Args:
            api_url: Base URL of the FastAPI server (default: http://localhost:8000)
        """
        self.api_url = api_url.rstrip('/')
        self.current_state: Optional[GameState] = None
        self.combat_stats: Optional[CombatStats] = None
        self.learning_progress: Optional[LearningProgress] = None
        self.last_update_time = 0
        self.update_interval = 0.5  # Update every 0.5 seconds
        
        logger.info(f"BotApiConnector initialized with API URL: {self.api_url}")
    
    def update_state(self, bot_instance) -> bool:
        """
        Update game state from bot instance.
        
        Args:
            bot_instance: The bot instance (WickedZergBotPro)
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Throttle updates to avoid overwhelming the server
            current_time = time.time()
            if current_time - self.last_update_time < self.update_interval:
                return True  # Skip this update
            
            # Extract game state from bot instance
            state = GameState(
                current_frame=getattr(bot_instance, 'iteration', 0),
                game_status=self._get_game_status(bot_instance),
                is_running=getattr(bot_instance, 'is_running', False),
                minerals=int(getattr(bot_instance, 'minerals', 50)),
                vespene=int(getattr(bot_instance, 'vespene', 0)),
                supply_used=getattr(bot_instance, 'supply_used', 12),
                supply_cap=getattr(bot_instance, 'supply_cap', 15),
                units=self._extract_units(bot_instance),
                threat_level=self._get_threat_level(bot_instance),
                strategy_mode=self._get_strategy_mode(bot_instance),
                map_name=self._get_map_name(bot_instance),
                timestamp=datetime.now().isoformat()
            )
            
            self.current_state = state
            self.last_update_time = current_time
            
            # Send update to API server
            return self._send_state_update(state)
            
        except Exception as e:
            logger.debug(f"Failed to update game state: {e}")
            return False
    
    def _get_game_status(self, bot_instance) -> str:
        """Extract game status from bot instance"""
        try:
            if not hasattr(bot_instance, 'townhalls') or not bot_instance.townhalls.exists:
                return "ENDED"
            if getattr(bot_instance, 'is_running', False):
                return "IN_PROGRESS"
            return "READY"
        except Exception:
            return "UNKNOWN"
    
    def _extract_units(self, bot_instance) -> Dict[str, int]:
        """Extract unit counts from bot instance"""
        units = {}
        try:
            from sc2.ids.unit_typeid import UnitTypeId
            
            # Common Zerg units
            unit_types = {
                'zerglings': UnitTypeId.ZERGLING,
                'roaches': UnitTypeId.ROACH,
                'hydralisks': UnitTypeId.HYDRALISK,
                'queens': UnitTypeId.QUEEN,
                'drones': UnitTypeId.DRONE,
                'overlords': UnitTypeId.OVERLORD,
            }
            
            for name, unit_id in unit_types.items():
                try:
                    count = bot_instance.units(unit_id).amount if hasattr(bot_instance, 'units') else 0
                    units[name] = count
                except Exception:
                    units[name] = 0
        except Exception:
            pass
        
        return units
    
    def _get_threat_level(self, bot_instance) -> str:
        """Determine threat level from bot instance"""
        try:
            if hasattr(bot_instance, 'early_defense') and bot_instance.early_defense:
                if hasattr(bot_instance.early_defense, 'is_panic_mode'):
                    if bot_instance.early_defense.is_panic_mode():
                        return "HIGH"
            return "NONE"
        except Exception:
            return "NONE"
    
    def _get_strategy_mode(self, bot_instance) -> str:
        """Extract strategy mode from bot instance"""
        try:
            if hasattr(bot_instance, 'strategy_mode'):
                return str(bot_instance.strategy_mode)
            if hasattr(bot_instance, 'game_phase'):
                return str(bot_instance.game_phase)
            return "OPENING"
        except Exception:
            return "OPENING"
    
    def _get_map_name(self, bot_instance) -> str:
        """Extract map name from bot instance"""
        try:
            if hasattr(bot_instance, 'game_info') and bot_instance.game_info:
                return bot_instance.game_info.map_name
            return "Unknown"
        except Exception:
            return "Unknown"
    
    def _send_state_update(self, state: GameState) -> bool:
        """
        Send game state update to API server.
        
        Args:
            state: GameState object to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import requests
            
            url = f"{self.api_url}/api/game-state/update"
            data = {
                "current_frame": state.current_frame,
                "game_status": state.game_status,
                "is_running": state.is_running,
                "minerals": state.minerals,
                "vespene": state.vespene,
                "supply_used": state.supply_used,
                "supply_cap": state.supply_cap,
                "units": state.units,
                "threat_level": state.threat_level,
                "strategy_mode": state.strategy_mode,
                "map_name": state.map_name,
                "last_update": state.timestamp
            }
            
            response = requests.post(url, json=data, timeout=1.0)
            return response.status_code == 200
            
        except Exception as e:
            # Silent fail - don't spam logs if server is not available
            return False
    
    def get_game_state(self) -> Optional[GameState]:
        """Get current game state"""
        return self.current_state
    
    def get_combat_stats(self) -> Optional[CombatStats]:
        """Get combat statistics"""
        return self.combat_stats
    
    def get_learning_progress(self) -> Optional[LearningProgress]:
        """Get learning progress"""
        return self.learning_progress
    
    def set_strategy_mode(self, strategy: str):
        """Set strategy mode"""
        logger.info(f"Strategy mode set to: {strategy}")
        # Strategy is set in bot instance, not via API
    
    def resume_game(self):
        """Resume game"""
        logger.info("Game resumed")
        # Game control is handled by bot instance
    
    def pause_game(self):
        """Pause game"""
        logger.info("Game paused")
        # Game control is handled by bot instance


# Initialize global connector instance
def init_connector(api_url: str = "http://localhost:8000") -> BotApiConnector:
    """
    Initialize the global bot connector instance.
    
    Args:
        api_url: Base URL of the FastAPI server
        
    Returns:
        BotApiConnector: The initialized connector instance
    """
    global bot_connector
    bot_connector = BotApiConnector(api_url)
    logger.info("Global bot_connector initialized")
    return bot_connector


# Auto-initialize if not already initialized
if bot_connector is None:
    try:
        import os
        api_url = os.environ.get("MONITORING_API_URL", "http://localhost:8000")
        bot_connector = BotApiConnector(api_url)
        logger.info("BotApiConnector auto-initialized")
    except Exception as e:
        logger.warning(f"Failed to auto-initialize BotApiConnector: {e}")
        bot_connector = None
