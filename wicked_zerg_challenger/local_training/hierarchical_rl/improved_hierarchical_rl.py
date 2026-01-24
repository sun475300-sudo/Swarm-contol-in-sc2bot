# -*- coding: utf-8 -*-
"""
Improved Hierarchical Reinforcement Learning (������ ��ȭ�н� ����)

��ü ���� �����ؾ� �ϴ� ���״� �Ǵ��ؾ� �� ������ �ʹ� �����ϴ�.
�̸� �ϳ��� �𵨷� ó���ϸ� �н��� �����ϴ�.

������ ����:
1. Commander Agent (��ɰ�): �Ž��� ����
   - "Ȯ���� �ұ�? ������ ������? ��ũ�� Ż��?"
   - �Է°�: �ڿ�, �α���, ��� ���� ��

2. Combat Agent (������): ���� ��Ʈ��
   - ��ɰ��� "������"��� �����ϸ�, ��ü���� ���� ��Ʈ�Ѹ� ���
   - �갳, ����, ��ġ ��

3. Queen Agent (����): ���� ����
   - ���� '����(Inject Larva)'�� '����(Creep Tumor)' ���� Ÿ�ָ̹� ����ȭ
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class CommanderAgent:
    """
    ��ɰ� ������Ʈ (Commander Agent)

    �Ž��� ������ �����ϴ�:
    - Ȯ���� �ұ�? ������ ������? ��ũ�� Ż��?
    - �����ұ�? ����ұ�? ������ �����ұ�?

    �Է°�: �ڿ�, �α���, ��� ����, �� ���� ��
    ��°�: ���� ��� (StrategyMode)
    """

    def __init__(self):
        """��ɰ� ������Ʈ �ʱ�ȭ"""
        self.strategy_history: List[str] = []
        self.decision_confidence: float = 0.5

    def make_decision(
        self,
        minerals: int,
        vespene: int,
        supply_used: int,
        supply_cap: int,
        enemy_race: str,
        enemy_army_value: float,
        our_army_value: float,
        map_control: float,
        creep_coverage: float,
    ) -> str:
        """
        �Ž��� ���� ������

        Args:
            minerals: ���� �̳׶�
            vespene: ���� ����
            supply_used: ��� ���� �α���
            supply_cap: �ִ� �α���
            enemy_race: �� ����
            enemy_army_value: �� ���� ��ġ
            our_army_value: �Ʊ� ���� ��ġ
            map_control: �� ��ǵ� (0.0 ~ 1.0)
            creep_coverage: ���� Ŀ������ (0.0 ~ 1.0)

        Returns:
            ���� ���: "ALL_IN", "AGGRESSIVE", "DEFENSIVE", "ECONOMY", "TECH"
        """
        # 1. �ڿ� ���� �м�
        resource_ratio = vespene / (minerals + 1)  # ����/�̳׶� ����
        supply_ratio = supply_used / (supply_cap + 1)  # �α��� ����

        # 2. ���� ��
        army_advantage = our_army_value / (enemy_army_value + 1)

        # 3. �� ��ǵ�
        map_advantage = map_control

        # 4. ���� ���� ����

        # ALL_IN: ���� ���� + �ڿ� ���� + �α��� ����
        if army_advantage > 1.5 and minerals < 500 and supply_ratio > 0.9:
            return "ALL_IN"

        # AGGRESSIVE: ���� ���� + �� ���
        if army_advantage > 1.2 and map_advantage > 0.5 and supply_ratio > 0.7:
            return "AGGRESSIVE"

        # DEFENSIVE: ���� ���� + �� ���� ���ɼ�
        if army_advantage < 0.8 and enemy_army_value > 1000:
            return "DEFENSIVE"

        # TECH: �ڿ� ���� + ���� ���� ����
        if (
            minerals > 1000
            and vespene > 500
            and resource_ratio > 0.3
            and supply_ratio < 0.8
        ):
            return "TECH"

        # ECONOMY: �⺻ ��� (Ȯ��, �ڿ� ����)
        if minerals > 800 or supply_ratio < 0.6:
            return "ECONOMY"

        # �⺻: AGGRESSIVE
        return "AGGRESSIVE"

    def get_sub_agent_commands(self, strategy_mode: str) -> Dict[str, Any]:
        """
        ���� ������Ʈ���� ���� ���� ����

        Args:
            strategy_mode: ���� ���

        Returns:
            ���� ������Ʈ�� ���� ��ųʸ�
        """
        commands = {"combat_agent": {}, "economy_agent": {}, "queen_agent": {}}

        if strategy_mode == "ALL_IN":
            commands["combat_agent"] = {
                "action": "attack",
                "target": "enemy_main",
                "formation": "surround",
                "priority": "high",
            }
            commands["economy_agent"] = {"action": "minimal", "priority": "low"}
            commands["queen_agent"] = {"action": "inject_only", "priority": "high"}

        elif strategy_mode == "AGGRESSIVE":
            commands["combat_agent"] = {
                "action": "harass",
                "target": "enemy_expansions",
                "formation": "loose",
                "priority": "high",
            }
            commands["economy_agent"] = {"action": "expand", "priority": "medium"}
            commands["queen_agent"] = {"action": "inject_and_creep", "priority": "high"}

        elif strategy_mode == "DEFENSIVE":
            commands["combat_agent"] = {
                "action": "defend",
                "target": "our_bases",
                "formation": "tight",
                "priority": "high",
            }
            commands["economy_agent"] = {
                "action": "defensive_buildings",
                "priority": "high",
            }
            commands["queen_agent"] = {
                "action": "inject_and_creep",
                "priority": "medium",
            }

        elif strategy_mode == "TECH":
            commands["combat_agent"] = {"action": "minimal", "priority": "low"}
            commands["economy_agent"] = {"action": "tech_buildings", "priority": "high"}
            commands["queen_agent"] = {"action": "inject_only", "priority": "medium"}

        else:  # ECONOMY
            commands["combat_agent"] = {"action": "scout", "priority": "low"}
            commands["economy_agent"] = {
                "action": "expand_and_drones",
                "priority": "high",
            }
            commands["queen_agent"] = {"action": "inject_and_creep", "priority": "high"}

        return commands


class CombatAgent:
    """
    ���� ������Ʈ (Combat Agent)

    ��ɰ��� "������"��� �����ϸ�,
    ��ü���� ���� ��Ʈ��(�갳, ����, ��ġ)�� ����մϴ�.

    Boids �˰������� Ȱ���Ͽ� ���� ���� ��� �����մϴ�.
    """

    def __init__(self):
        """���� ������Ʈ �ʱ�ȭ"""
        self.current_action = None
        self.target_position = None
        self.formation_mode = "loose"

    def execute_combat(
        self, bot, command: Dict[str, Any], units: "Units", enemy_units: "Units"
    ) -> bool:
        """
        ���� ���� ����

        Args:
            bot: �� ��ü
            command: ��ɰ��� ����
            units: �Ʊ� ���ֵ�
            enemy_units: �� ���ֵ�

        Returns:
            ���� ���� ����
        """
        try:
            action = command.get("action", "attack")
            formation = command.get("formation", "loose")
            target = command.get("target", None)

            # Boids �˰����� ����
            try:
                from combat.boids_swarm_control import BoidsSwarmController
                from combat.micro_combat import MicroCombat

                micro_combat = MicroCombat(bot)

                if action == "attack":
                    # ����: ���� �����ϸ鼭 ����
                    if enemy_units:
                        closest_enemy = enemy_units.closest_to(units.center)
                        if closest_enemy:
                            micro_combat.focus_fire(units, closest_enemy)

                elif action == "harass":
                    # ����: ������ ���� �� ����
                    if enemy_units:
                        micro_combat.kiting(units, enemy_units)

                elif action == "defend":
                    # ���: �Ʊ� ���� �ֺ����� ���
                    if hasattr(bot, "townhalls"):
                        main_base = bot.townhalls.first
                        if main_base:
                            # ���� �ֺ����� ���� ��ġ
                            for unit in units:
                                if unit.distance_to(main_base) > 10:
                                    unit.move(
                                        main_base.position.towards(unit.position, 8)
                                    )

                elif action == "scout":
                    # ����: �� Ž��
                    if units:
                        # ��Ž�� �������� �̵�
                        for unit in units[:3]:  # �ִ� 3�� ���ָ� ����
                            if unit.is_idle:
                                # ���� �������� �̵�
                                import random

                                angle = random.uniform(0, 2 * np.pi)
                                distance = 20.0
                                scout_pos = unit.position.towards(
                                    unit.position.offset(
                                        Point2(
                                            (
                                                np.cos(angle) * distance,
                                                np.sin(angle) * distance,
                                            )
                                        )
                                    ),
                                    distance,
                                )
                                unit.move(scout_pos)

                return True

            except ImportError:
                # Boids�� ������ �⺻ ����
                if enemy_units and units:
                    for unit in units:
                        closest_enemy = enemy_units.closest_to(unit.position)
                        if closest_enemy:
                            unit.attack(closest_enemy)
                return True

        except Exception as e:
            error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            print(f"[WARNING] Combat Agent execution error: {error_msg}")
            return False


class QueenAgent:
    """
    ���� ������Ʈ (Queen Agent)

    ���� '����(Inject Larva)'�� '����(Creep Tumor)' ���� Ÿ�ָ̹� ����ȭ�մϴ�.
    """

    def __init__(self):
        """���� ������Ʈ �ʱ�ȭ"""
        self.last_inject_time: Dict[int, float] = {}  # {hatchery_tag: time}
        self.last_creep_time: Dict[int, float] = {}  # {queen_tag: time}
        self.inject_cooldown = 29.0  # Inject ��Ÿ�� (��)
        self.creep_cooldown = 11.0  # Creep Tumor ��Ÿ�� (��)

    def execute_queen_management(self, bot, command: Dict[str, Any]) -> bool:
        """
        ���� ���� ����

        Args:
            bot: �� ��ü
            command: ��ɰ��� ����

        Returns:
            ���� ���� ����
        """
        try:
            action = command.get("action", "inject_and_creep")
            priority = command.get("priority", "medium")

            if not hasattr(bot, "units") or not hasattr(bot, "townhalls"):
                return False

            queens = bot.units.filter(lambda u: u.name == "Queen")
            if not queens:
                return False

            # 1. Inject Larva (����)
            if "inject" in action:
                self._execute_inject(bot, queens, priority)

            # 2. Creep Tumor (���� ����)
            if "creep" in action:
                self._execute_creep_spread(bot, queens, priority)

            return True

        except Exception as e:
            error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            print(f"[WARNING] Queen Agent execution error: {error_msg}")
            return False

    def _execute_inject(self, bot, queens, priority: str) -> None:
        """Inject Larva ����"""
        if not hasattr(bot, "townhalls"):
            return

        inject_priority = priority == "high"

        for hatch in bot.townhalls:
            # Inject ��Ÿ�� Ȯ��
            last_time = self.last_inject_time.get(hatch.tag, 0.0)
            if bot.time - last_time < self.inject_cooldown:
                continue

            # ���� ����� ���� ã��
            closest_queen = queens.closest_to(hatch.position)
            if not closest_queen:
                continue

            # ������ Inject �������� Ȯ��
            if (
                hasattr(closest_queen, "energy")
                and closest_queen.energy >= 25
                and closest_queen.distance_to(hatch) <= 4
            ):

                # Inject ����
                if hasattr(closest_queen, "can_cast"):
                    if closest_queen.can_cast(closest_queen.abilities.InjectLarva):
                        bot.do(closest_queen(hatch))
                        self.last_inject_time[hatch.tag] = bot.time

    def _execute_creep_spread(self, bot, queens, priority: str) -> None:
        """Creep Tumor ���� ����"""
        creep_priority = priority == "high"

        for queen in queens:
            # Creep Tumor ��Ÿ�� Ȯ��
            last_time = self.last_creep_time.get(queen.tag, 0.0)
            if bot.time - last_time < self.creep_cooldown:
                continue

            # ������ Creep Tumor ���� �������� Ȯ��
            if hasattr(queen, "energy") and queen.energy >= 25:

                # ������ ���� ���� ã��
                # (�����δ� �� �м��� �ʿ������� ���⼭�� �ܼ�ȭ)
                if hasattr(queen, "can_cast"):
                    if queen.can_cast(queen.abilities.BuildCreepTumor):
                        # ���� �������� Creep Tumor ����
                        creep_pos = queen.position.towards(
                            (
                                bot.enemy_start_locations[0]
                                if hasattr(bot, "enemy_start_locations")
                                else queen.position
                            ),
                            8.0,
                        )
                        bot.do(queen(creep_pos))
                        self.last_creep_time[queen.tag] = bot.time


class HierarchicalRLSystem:
    """
    ������ ��ȭ�н� �ý���

    Commander Agent -> Sub Agents (Combat, Economy, Queen) ����
    """

    def __init__(self):
        """������ ��ȭ�н� �ý��� �ʱ�ȭ"""
        self.commander = CommanderAgent()
        self.combat_agent = CombatAgent()
        self.queen_agent = QueenAgent()

    @staticmethod
    def _normalize_enemy_race(value) -> str:
        if value is None:
            return "Unknown"
        if hasattr(value, "name"):
            return str(value.name)
        text = str(value)
        if text.lower().startswith("race."):
            return text.split(".", 1)[1]
        return text

    def step(self, bot, override_strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        매 프레임 실행
        
        Args:
            bot: 봇 객체
            override_strategy: 외부(RL Agent)에서 결정한 전략 (있으면 우선 사용)
            
        Returns:
            실행 결과 딕셔너리
        """
        try:
            # 1. Commander Agent의 상황 판단 (Rule-based)
            rule_based_decision = self.commander.make_decision(
                minerals=bot.minerals,
                vespene=bot.vespene,
                supply_used=bot.supply_used,
                supply_cap=bot.supply_cap,
                enemy_race=self._normalize_enemy_race(
                    getattr(bot, "enemy_race", None)
                ),
                enemy_army_value=(
                    self._calculate_army_value(bot.enemy_units)
                    if hasattr(bot, "enemy_units")
                    else 0
                ),
                our_army_value=(
                    self._calculate_army_value(bot.units)
                    if hasattr(bot, "units")
                    else 0
                ),
                map_control=self._calculate_map_control(bot),
                creep_coverage=self._calculate_creep_coverage(bot),
            )

            # ★ CRITICAL: RL Agent가 결정을 내렸으면 그것을 따름 ★
            if override_strategy:
                strategy_mode = override_strategy
                # 훈련 로깅을 위해 비교 정보 출력 (가끔)
                if bot.iteration % 220 == 0 and strategy_mode != rule_based_decision:
                    print(f"[RL_OVERRIDE] RL: {strategy_mode} vs Rule: {rule_based_decision}")
            else:
                strategy_mode = rule_based_decision

            # 2.  Ʈ  
            commands = self.commander.get_sub_agent_commands(strategy_mode)

            # 3.  Ʈ 
            results = {
                "strategy_mode": strategy_mode,
                "combat_result": False,
                "queen_result": False,
            }

            # Combat Agent ����
            if hasattr(bot, "units") and hasattr(bot, "enemy_units"):
                combat_units = bot.units.filter(
                    lambda u: u.name
                    in ["Zergling", "Roach", "Hydralisk", "Mutalisk", "Lurker"]
                )
                if combat_units:
                    results["combat_result"] = self.combat_agent.execute_combat(
                        bot=bot,
                        command=commands["combat_agent"],
                        units=combat_units,
                        enemy_units=bot.enemy_units,
                    )

            # Queen Agent ����
            results["queen_result"] = self.queen_agent.execute_queen_management(
                bot=bot, command=commands["queen_agent"]
            )

            return results

        except Exception as e:
            error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            print(f"[WARNING] Hierarchical RL step error: {error_msg}")
            return {"strategy_mode": "ECONOMY", "error": str(e)}

    def _calculate_army_value(self, units) -> float:
        """���� ��ġ ���"""
        if not units:
            return 0.0

        # �ܼ�ȭ: ���� �� * 100
        return len(units) * 100.0

    def _calculate_map_control(self, bot) -> float:
        """�� ��ǵ� ��� (0.0 ~ 1.0)"""
        try:
            if not hasattr(bot, "townhalls"):
                return 0.0

            # �Ʊ� ���� �� / (�Ʊ� ���� �� + �� ���� ��)
            our_bases = len(bot.townhalls)
            enemy_bases = (
                len(bot.enemy_structures.townhall)
                if hasattr(bot, "enemy_structures")
                else 1
            )

            total_bases = our_bases + enemy_bases
            if total_bases == 0:
                return 0.5

            return our_bases / total_bases

        except Exception:
            return 0.5

    def _calculate_creep_coverage(self, bot) -> float:
        """���� Ŀ������ ��� (0.0 ~ 1.0)"""
        try:
            if not hasattr(bot, "state") or not hasattr(bot.state, "creep"):
                return 0.0

            map_width = bot.game_info.map_size[0]
            map_height = bot.game_info.map_size[1]
            total_map_area = map_width * map_height

            if total_map_area == 0:
                return 0.0

            creep_coverage = np.sum(bot.state.creep) / total_map_area
            return float(creep_coverage)

        except Exception:
            return 0.0
