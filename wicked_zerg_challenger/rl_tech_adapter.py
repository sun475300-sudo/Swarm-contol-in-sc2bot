# -*- coding: utf-8 -*-
"""
RL Tech Adapter - Reinforcement Learning for Enemy Tech Response

적 테크 정보를 관찰하고 이에 대응하여 빌드 오더와 유닛 구성을 실시간 조정합니다.
학습된 대응 전략은 commander_knowledge.json에 저장되어 누적 학습됩니다.

Features:
1. Enemy tech building detection (적 테크 건물 감지)
2. Adaptive unit composition (적응형 유닛 구성)
3. Counter-build learning (카운터 빌드 학습)
4. Win/loss feedback integration (승/패 피드백 통합)
"""

from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import json
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        ROACHWARREN = "ROACHWARREN"
        HYDRALISKDEN = "HYDRALISKDEN"
        SPIRE = "SPIRE"
        INFESTATIONPIT = "INFESTATIONPIT"


class RLTechAdapter:
    """
    ★ RL-based Enemy Tech Adaptation System ★

    적 테크를 관찰하고 최적의 카운터 전략을 선택합니다.
    각 게임 결과를 학습하여 점진적으로 성능을 개선합니다.
    """

    def __init__(self, bot, intel_manager=None, knowledge_manager=None):
        self.bot = bot
        self.intel = intel_manager or getattr(bot, "intel", None)
        self.knowledge = knowledge_manager or getattr(bot, "knowledge_manager", None)
        self.logger = get_logger("RLTechAdapter")

        # ★ State Observation ★
        self.observed_enemy_tech: Set[str] = set()
        self.last_tech_scan = 0
        self.tech_scan_interval = 44  # ~2초마다 스캔

        # ★ Decision State ★
        self.current_counter_strategy = "STANDARD"
        self.adaptation_active = False
        self.last_adaptation_time = 0

        # ★ Learning Data ★
        self.game_start_time = 0
        self.adaptations_made: List[Dict] = []  # 이번 게임에서 한 적응들
        self.tech_first_seen: Dict[str, float] = {}  # 각 테크를 처음 본 시간

        # ★ Counter Rules (실시간 조정 가능) ★
        self.counter_priorities = {
            # Terran Tech
            "FACTORY": {
                "counter_units": ["roach", "ravager"],
                "tech_response": "ROACHWARREN",
                "ratio_boost": 0.15,  # Roach 비율 15% 증가
                "timing": 180,  # 3분 전에 감지되면 즉시 대응
            },
            "STARPORT": {
                "counter_units": ["hydralisk", "corruptor"],
                "tech_response": "HYDRALISKDEN",
                "ratio_boost": 0.20,  # Hydra 비율 20% 증가
                "timing": 240,
            },
            "ARMORY": {
                "counter_units": ["roach", "hydralisk"],
                "tech_response": "EVOLUTIONCHAMBER",
                "ratio_boost": 0.10,
                "timing": 300,
            },

            # Protoss Tech
            "ROBOTICSFACILITY": {
                "counter_units": ["roach", "ravager", "hydralisk"],
                "tech_response": "ROACHWARREN",
                "ratio_boost": 0.20,
                "timing": 180,
            },
            "STARGATE": {
                "counter_units": ["hydralisk", "corruptor", "queen"],
                "tech_response": "HYDRALISKDEN",
                "ratio_boost": 0.25,  # 공중 위협은 더 강하게 대응
                "timing": 210,
            },
            "TWILIGHTCOUNCIL": {
                "counter_units": ["roach", "baneling"],
                "tech_response": "ROACHWARREN",
                "ratio_boost": 0.15,
                "timing": 240,
            },
            "DARKSHRINE": {
                "counter_units": ["overseer", "roach"],
                "tech_response": "LAIR",  # 오버시어 위한 레어
                "ratio_boost": 0.10,
                "timing": 300,
            },

            # Zerg Tech
            "ROACHWARREN": {
                "counter_units": ["roach", "hydralisk"],
                "tech_response": "ROACHWARREN",
                "ratio_boost": 0.20,
                "timing": 150,
            },
            "BANELINGNEST": {
                "counter_units": ["roach", "ravager"],
                "tech_response": "ROACHWARREN",
                "ratio_boost": 0.15,
                "timing": 150,
            },
            "SPIRE": {
                "counter_units": ["hydralisk", "corruptor"],
                "tech_response": "HYDRALISKDEN",
                "ratio_boost": 0.25,
                "timing": 240,
            },
        }

        # ★ Learning Rate ★
        self.learning_rate = 0.1  # 학습률
        self.success_memory = {}  # {tech_detected: {response: win_rate}}
        self._load_learning_memory()

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration - self.last_tech_scan < self.tech_scan_interval:
                return

            self.last_tech_scan = iteration
            game_time = getattr(self.bot, "time", 0)

            # ★ 1. Observe: 적 테크 감지 ★
            new_tech_detected = await self._scan_enemy_tech()

            # ★ 2. Decide: 카운터 전략 선택 ★
            if new_tech_detected:
                await self._decide_counter_strategy(new_tech_detected, game_time)

            # ★ 3. Act: 전략 실행 ★
            await self._execute_adaptation(iteration)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[RL_TECH] Error: {e}")

    async def _scan_enemy_tech(self) -> Set[str]:
        """
        적 테크 건물을 스캔하고 새로 발견된 테크를 반환

        Returns:
            새로 발견된 테크 건물 집합
        """
        if not self.intel:
            return set()

        # IntelManager에서 적 테크 정보 가져오기
        current_enemy_tech = getattr(self.intel, "enemy_tech_buildings", set())

        # 새로 발견된 테크
        new_tech = current_enemy_tech - self.observed_enemy_tech

        if new_tech:
            game_time = getattr(self.bot, "time", 0)
            for tech in new_tech:
                self.tech_first_seen[tech] = game_time
                self.logger.info(f"[RL_TECH] [{int(game_time)}s] ★ NEW ENEMY TECH: {tech} ★")

        # 관찰 상태 업데이트
        self.observed_enemy_tech = current_enemy_tech.copy()

        return new_tech

    async def _decide_counter_strategy(self, new_tech: Set[str], game_time: float):
        """
        새로 감지된 테크에 대한 카운터 전략 결정

        Args:
            new_tech: 새로 발견된 테크 건물들
            game_time: 현재 게임 시간
        """
        for tech in new_tech:
            counter_rule = self.counter_priorities.get(tech)

            if not counter_rule:
                continue

            # 타이밍 체크: 너무 늦게 발견되면 대응 안 함
            detection_timing = counter_rule.get("timing", 300)
            if game_time > detection_timing + 120:  # 타이밍 + 2분 이후면 너무 늦음
                self.logger.info(f"[RL_TECH] {tech} detected too late ({int(game_time)}s), skipping response")
                continue

            # ★ 학습된 성공률 확인 ★
            learned_response = self._get_learned_response(tech)
            if learned_response:
                counter_rule = learned_response

            # 적응 기록
            adaptation = {
                "tech_detected": tech,
                "game_time": game_time,
                "counter_strategy": counter_rule,
                "applied": False
            }
            self.adaptations_made.append(adaptation)

            self.logger.info(
                f"[RL_TECH] ★★★ ADAPTING to {tech} ★★★\n"
                f"  Counter Units: {counter_rule['counter_units']}\n"
                f"  Tech Response: {counter_rule['tech_response']}\n"
                f"  Ratio Boost: +{counter_rule['ratio_boost']*100:.0f}%"
            )

            # Blackboard에 카운터 전략 등록
            await self._register_counter_to_blackboard(tech, counter_rule)

    async def _register_counter_to_blackboard(self, tech: str, counter_rule: Dict):
        """
        Blackboard에 카운터 전략을 등록하여 다른 매니저들이 사용할 수 있게 함
        """
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard:
            return

        # StrategyManager에 유닛 비율 조정 요청
        current_ratios = blackboard.get("unit_composition_override", {})

        for unit in counter_rule["counter_units"]:
            # 현재 비율에 boost 추가
            current_ratio = current_ratios.get(unit, 0.0)
            new_ratio = min(1.0, current_ratio + counter_rule["ratio_boost"])
            current_ratios[unit] = new_ratio

        blackboard.set("unit_composition_override", current_ratios)
        blackboard.set("rl_tech_response_active", True)
        blackboard.set("rl_countering_tech", tech)

        self.logger.info(f"[RL_TECH] Registered counter strategy to Blackboard: {current_ratios}")

    async def _execute_adaptation(self, iteration: int):
        """
        적응 전략 실행 (테크 건물 건설 등)
        """
        if not self.adaptations_made:
            return

        game_time = getattr(self.bot, "time", 0)

        for adaptation in self.adaptations_made:
            if adaptation["applied"]:
                continue

            tech_response = adaptation["counter_strategy"].get("tech_response")
            if not tech_response:
                continue

            # 해당 테크 건물 건설 요청
            success = await self._request_tech_building(tech_response)

            if success:
                adaptation["applied"] = True
                self.logger.info(f"[RL_TECH] [{int(game_time)}s] Applied tech response: {tech_response}")

    async def _request_tech_building(self, building_type: str) -> bool:
        """
        특정 테크 건물 건설 요청

        Returns:
            요청 성공 여부
        """
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard:
            return False

        # Blackboard를 통해 건설 요청
        blackboard.set(f"rl_request_{building_type.lower()}", True)

        return True

    def _get_learned_response(self, tech: str) -> Optional[Dict]:
        """
        학습된 성공률을 기반으로 최적 대응 전략 가져오기

        Returns:
            학습된 카운터 룰 또는 None
        """
        tech_memory = self.success_memory.get(tech, {})
        if not tech_memory:
            return None

        # 가장 성공률이 높은 전략 선택
        best_response = max(tech_memory.items(), key=lambda x: x[1], default=None)
        if best_response and best_response[1] > 0.5:  # 50% 이상 승률
            # TODO: best_response[0]에서 카운터 룰 재구성
            return None  # 임시로 None (추후 구현)

        return None

    def record_game_result(self, won: bool, enemy_race: str):
        """
        게임 결과를 기록하여 학습

        Args:
            won: 승리 여부
            enemy_race: 적 종족
        """
        if not self.adaptations_made:
            return

        # 각 적응에 대해 학습
        for adaptation in self.adaptations_made:
            if not adaptation["applied"]:
                continue

            tech = adaptation["tech_detected"]
            strategy = adaptation["counter_strategy"]

            # 성공 메모리 업데이트
            if tech not in self.success_memory:
                self.success_memory[tech] = {}

            response_key = strategy["tech_response"]
            if response_key not in self.success_memory[tech]:
                self.success_memory[tech][response_key] = 0.5  # 초기값 50%

            # Learning rate를 사용한 업데이트
            old_value = self.success_memory[tech][response_key]
            reward = 1.0 if won else 0.0
            new_value = old_value + self.learning_rate * (reward - old_value)
            self.success_memory[tech][response_key] = new_value

            self.logger.info(
                f"[RL_TECH] Learning Update: {tech} → {response_key}\n"
                f"  Result: {'WIN' if won else 'LOSS'}\n"
                f"  Win Rate: {old_value:.2%} → {new_value:.2%}"
            )

        # 학습 데이터 저장
        self._save_learning_memory()

    def _load_learning_memory(self):
        """학습된 메모리 로드"""
        try:
            memory_file = Path(__file__).parent / "rl_tech_memory.json"
            if memory_file.exists():
                with open(memory_file, "r", encoding="utf-8") as f:
                    self.success_memory = json.load(f)
                self.logger.info(f"[RL_TECH] Loaded learning memory: {len(self.success_memory)} entries")
        except Exception as e:
            self.logger.warning(f"[RL_TECH] Failed to load memory: {e}")

    def _save_learning_memory(self):
        """학습된 메모리 저장"""
        try:
            memory_file = Path(__file__).parent / "rl_tech_memory.json"
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(self.success_memory, f, indent=2)
            self.logger.info(f"[RL_TECH] Saved learning memory")
        except Exception as e:
            self.logger.warning(f"[RL_TECH] Failed to save memory: {e}")
