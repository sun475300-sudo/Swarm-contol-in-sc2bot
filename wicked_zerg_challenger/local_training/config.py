# -*- coding: utf-8 -*-

import json
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional

from sc2.ids.unit_typeid import UnitTypeId  # type: ignore

# Logger for learned parameters
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class GamePhase(Enum):
    """Current game phase - transitions dynamically based on scouting"""

    OPENING = auto()
    ECONOMY = auto()
    TECH = auto()
    ATTACK = auto()
    DEFENSE = auto()
    ALL_IN = auto()


class EnemyRace(Enum):
    """Opponent race"""

    TERRAN = auto()
    PROTOSS = auto()
    ZERG = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class Config:
    """AI behavior configuration values (immutable)"""

    MAX_WORKERS: int = 60
    WORKERS_PER_BASE: int = 16
    WORKERS_PER_GAS: int = 3
    MINERAL_THRESHOLD: int = 500
    GAS_THRESHOLD: int = 200

    ALL_IN_12_POOL: bool = False
    ALL_IN_WORKER_LIMIT: int = 12
    ALL_IN_ZERGLING_ATTACK: int = 2

    ZERGLING_ATTACK_THRESHOLD: int = 12
    ROACH_THRESHOLD: int = 8
    HYDRA_THRESHOLD: int = 6
    TOTAL_ARMY_THRESHOLD: int = 60

    RUSH_TIMING_TERRAN: int = 300
    RUSH_TIMING_PROTOSS: int = 240
    RUSH_TIMING_ZERG: int = 180
    ALL_IN_ATTACK_SUPPLY: int = 120
    RALLY_GATHER_PERCENT: float = 0.8
    MIN_DEFENSE_BEFORE_EXPAND: int = 8

    KITING_DISTANCE: float = 2.0
    ENGAGE_DISTANCE: float = 15.0
    RETREAT_HP_PERCENT: float = 0.3

    SPAWNING_POOL_SUPPLY: int = 14
    ROACH_WARREN_TIME: int = 180
    LAIR_TIME: int = 300
    HYDRA_DEN_TIME: int = 360
    TECH_LAIR_MINERALS: int = 150

    INITIAL_SCOUT_SUPPLY: int = 13
    SCOUT_INTERVAL: float = 60.0
    RUSH_DETECTION_DISTANCE: float = 30.0

    EARLY_GAME_TIME: int = 180
    MID_GAME_TIME: int = 360
    LATE_GAME_TIME: int = 720

    SUPPLY_BUFFER: int = 16
    OVERLORD_PREDICT_TIME: float = 5.0

    SC2_PATH: Optional[str] = None
    PROTOCOL_BUFFERS_IMPL: str = "cpp"  # IMPROVED: Use C++ implementation for better performance (10x faster)
    GPU_USAGE_TARGET: float = 0.30
    DIAGNOSE_INTERVAL: int = 500
    WORKER_DEFENSE_RETREAT_THRESHOLD: float = 0.3
    DUPLICATE_PENALTY_MULTI_FACTOR: float = 1.0

    MIN_WORKERS_FOR_ECONOMY: int = 8  # CRITICAL: Minimum workers to maintain economy (prevents economy collapse)
    MIN_DRONES_FOR_DEFENSE: int = 8  # CRITICAL: Minimum drones to preserve during emergency defense
    TERRAIN_ADVANTAGE_MULTIPLIER: float = 1.2
    SPLASH_DAMAGE_PENALTY_MULTIPLIER: float = 1.5

    AUTO_OPTIMIZE_CODE: bool = True
    REPLAY_LEARNING_INTERVAL: int = 1
    REPLAY_LEARNING_ITERATIONS: int = 3


TARGET_PRIORITY = {
    UnitTypeId.SIEGETANK: 10,
    UnitTypeId.SIEGETANKSIEGED: 12,
    UnitTypeId.MEDIVAC: 9,
    UnitTypeId.THOR: 8,
    UnitTypeId.BATTLECRUISER: 11,
    UnitTypeId.LIBERATOR: 9,
    UnitTypeId.WIDOWMINE: 7,
    UnitTypeId.MARINE: 5,
    UnitTypeId.MARAUDER: 6,
    UnitTypeId.HELLION: 4,
    UnitTypeId.CYCLONE: 6,
    UnitTypeId.COLOSSUS: 12,
    UnitTypeId.HIGHTEMPLAR: 11,
    UnitTypeId.DISRUPTOR: 10,
    UnitTypeId.IMMORTAL: 9,
    UnitTypeId.ARCHON: 8,
    UnitTypeId.CARRIER: 11,
    UnitTypeId.VOIDRAY: 7,
    UnitTypeId.STALKER: 5,
    UnitTypeId.ZEALOT: 4,
    UnitTypeId.ADEPT: 5,
    UnitTypeId.SENTRY: 6,
    UnitTypeId.LURKER: 10,
    UnitTypeId.INFESTOR: 9,
    UnitTypeId.BROODLORD: 11,
    UnitTypeId.ULTRALISK: 8,
    UnitTypeId.ROACH: 5,
    UnitTypeId.HYDRALISK: 6,
    UnitTypeId.MUTALISK: 7,
    UnitTypeId.SCV: 8,
    UnitTypeId.PROBE: 8,
    UnitTypeId.DRONE: 8,
    UnitTypeId.COMMANDCENTER: 15,
    UnitTypeId.COMMANDCENTERFLYING: 15,
    UnitTypeId.NEXUS: 15,
    UnitTypeId.HATCHERY: 15,
    UnitTypeId.LAIR: 16,
    UnitTypeId.HIVE: 16,
    UnitTypeId.ORBITALCOMMAND: 14,
    UnitTypeId.PLANETARYFORTRESS: 14,
}


COUNTER_BUILD = {
    EnemyRace.TERRAN: {
        "early_units": [UnitTypeId.ZERGLING, UnitTypeId.BANELING],
        "mid_units": [UnitTypeId.ROACH, UnitTypeId.RAVAGER],
        "late_units": [UnitTypeId.HYDRALISK, UnitTypeId.LURKER],
        "priority_buildings": [UnitTypeId.BANELINGNEST, UnitTypeId.ROACHWARREN],
        "defense_building": UnitTypeId.SPINECRAWLER,
    },
    EnemyRace.PROTOSS: {
        "early_units": [UnitTypeId.ZERGLING, UnitTypeId.ROACH],
        "mid_units": [UnitTypeId.HYDRALISK, UnitTypeId.RAVAGER],
        "late_units": [UnitTypeId.CORRUPTOR, UnitTypeId.BROODLORD],
        "priority_buildings": [UnitTypeId.ROACHWARREN, UnitTypeId.HYDRALISKDEN],
        "defense_building": UnitTypeId.SPORECRAWLER,
    },
    EnemyRace.ZERG: {
        "early_units": [UnitTypeId.ZERGLING, UnitTypeId.BANELING],
        "mid_units": [UnitTypeId.ROACH, UnitTypeId.HYDRALISK],
        "late_units": [UnitTypeId.ULTRALISK, UnitTypeId.BROODLORD],
        "priority_buildings": [UnitTypeId.ROACHWARREN, UnitTypeId.BANELINGNEST],
        "defense_building": UnitTypeId.SPINECRAWLER,
    },
}


THREAT_BUILDINGS = {
    UnitTypeId.BARRACKS: 3,
    UnitTypeId.FACTORY: 2,
    UnitTypeId.STARPORT: 2,
    UnitTypeId.BUNKER: 5,
    UnitTypeId.GATEWAY: 3,
    UnitTypeId.STARGATE: 4,
    UnitTypeId.ROBOTICSFACILITY: 2,
    UnitTypeId.DARKSHRINE: 6,
    UnitTypeId.SPAWNINGPOOL: 2,
    UnitTypeId.ROACHWARREN: 3,
    UnitTypeId.BANELINGNEST: 4,
}


LOG_CONFIG = {
    "enabled": True,
    "log_file": "game_log.txt",
    "kpi_file": "kpi_data.csv",
    "log_interval": 30,
}


class ConfigLoader:
    """Loads configuration with learned parameter overrides"""

    def __init__(self, learned_config_file: str = "learned_config.json"):
        self.learned_config_file = Path(learned_config_file)
        self.learned_params = {}
        self.load_learned_config()

    def load_learned_config(self):
        """Load learned configuration parameters"""
        if self.learned_config_file.exists():
            try:
                with open(self.learned_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.learned_params = data.get("parameters", {})
            except Exception as e:
                print(f"[WARNING] Failed to load learned config: {e}")
                self.learned_params = {}
        else:
            self.learned_params = {}

    def get_config(self) -> dict:
        """Get configuration with learned overrides applied"""
        config_dict = {
            "MAX_WORKERS": Config.MAX_WORKERS,
            "WORKERS_PER_BASE": Config.WORKERS_PER_BASE,
            "WORKERS_PER_GAS": Config.WORKERS_PER_GAS,
            "MINERAL_THRESHOLD": Config.MINERAL_THRESHOLD,
            "GAS_THRESHOLD": Config.GAS_THRESHOLD,
            "ZERGLING_ATTACK_THRESHOLD": Config.ZERGLING_ATTACK_THRESHOLD,
            "ROACH_THRESHOLD": Config.ROACH_THRESHOLD,
            "HYDRA_THRESHOLD": Config.HYDRA_THRESHOLD,
            "TOTAL_ARMY_THRESHOLD": Config.TOTAL_ARMY_THRESHOLD,
            "SPAWNING_POOL_SUPPLY": Config.SPAWNING_POOL_SUPPLY,
            "ROACH_WARREN_TIME": Config.ROACH_WARREN_TIME,
            "LAIR_TIME": Config.LAIR_TIME,
            "HYDRA_DEN_TIME": Config.HYDRA_DEN_TIME,
            "SUPPLY_BUFFER": Config.SUPPLY_BUFFER,
        }

        for param_name, param_data in self.learned_params.items():
            if isinstance(param_data, dict):
                value = param_data.get("value")
            else:
                value = param_data

            param_mapping = {
                "macro_hatchery_threshold": "MINERAL_THRESHOLD",
                "priority_zero_threshold": "WORKERS_PER_BASE",
                "expansion_mineral_threshold": "MINERAL_THRESHOLD",
                "mineral_flush_threshold": "MINERAL_THRESHOLD",
            }

            mapped_name = param_mapping.get(param_name, param_name.upper())
            if mapped_name and mapped_name in config_dict:
                config_dict[mapped_name] = value

        return config_dict

    def get_parameter(self, parameter_name: str, default_value: Any = None) -> Any:
        """Get a specific learned parameter value"""
        param_data = self.learned_params.get(parameter_name)
        if param_data is None:
            return default_value

        if isinstance(param_data, dict):
            return param_data.get("value", default_value)
        else:
            return param_data


_config_loader = None


def get_config_loader() -> ConfigLoader:
    """Get global config loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_learned_parameter(parameter_name: str, default_value: Any = None) -> Any:
    learned_json_path = Path(__file__).parent / "learned_build_orders.json"
    if learned_json_path.exists():
        try:
            with open(learned_json_path, 'r', encoding='utf-8') as f:
                learned_data = json.load(f)
                if isinstance(learned_data, dict):
                    if "learned_parameters" in learned_data:
                        learned_params = learned_data["learned_parameters"]
                    else:
                        learned_params = learned_data
                    if parameter_name in learned_params:
                        return learned_params[parameter_name]
        except Exception:
            pass
    loader = get_config_loader()
    return loader.get_parameter(parameter_name, default_value)
