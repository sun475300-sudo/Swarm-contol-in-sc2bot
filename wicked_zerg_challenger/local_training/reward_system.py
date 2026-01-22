# -*- coding: utf-8 -*-
"""
Zerg Specialized Reward System (Reward Shaping)

���� Ưȭ ���� �ý���: �ܼ��� �¸�/�й� ���� �ܿ���
���� ���� �� "���ϰ� �ִ�"�� Ī���� �־� �н� �ӵ��� ���Դϴ�.

�ٽ� ���� ���:
1. ����(Creep) Ŀ������ ���� (�� ���)
2. ���(Larva) ȿ���� ���� (����)
3. �ڿ� ȸ���� ���� (�Ҹ���)
4. ���� ������ ���� (�Ҹ��� ȿ��)
"""

from typing import Optional
import numpy as np


class ZergRewardSystem:
    """
    ���� Ưȭ ���� �ý���
    
    �ܼ��� "�̱�� +1, ���� -1"�� �н���Ű��,
    AI�� ������ ���� ������ ���� �������� ����ϸ� �н� �ӵ��� �ſ� �������ϴ�.
    **'���ϰ� �ִ�'�� Ī��(����)**�� �߰��߰� ��� ��� �մϴ�.
    """
    
    def __init__(self):
        """���� �ý��� �ʱ�ȭ"""
        self.previous_score = 0
        self.previous_creep_coverage = 0.0
        self.previous_larva_efficiency = 0.0
        
    def calculate_step_reward(self, bot) -> float:
        """
        �� ����(Step)���� AI�� �󸶳� ���ϰ� �ִ��� ����(Reward)�� �ű�ϴ�.
        
        Args:
            bot: ���� ���� ���¸� ��� �ִ� �� ��ü (BotAI �ν��Ͻ�)
            
        Returns:
            �̹� ������ ���� ���� (float)
        """
        reward = 0.0
        
        try:
            # 1. ����(Creep) Ŀ������ ���� (�� ���)
            # ������ �ٽ��� �þ߿� �̵� �ӵ� ������ �ִ� �����Դϴ�.
            reward += self._calculate_creep_reward(bot)
            
            # 2. ���(Larva) ȿ���� ���� (����)
            # ������ �� �ؼ� ��ٰ� �׿������� ���� (�г�Ƽ)
            reward += self._calculate_larva_efficiency_reward(bot)
            
            # 3. �ڿ� ȸ���� ���� (�Ҹ���)
            # �̳׶��� 2000 �̻� ������ '���� �� ���� �ִ�'�� ���̹Ƿ� ����
            reward += self._calculate_resource_turnover_reward(bot)
            
            # 4. ���� ������ ���� (�Ҹ��� ȿ��)
            # (���� �ı��� �� �ڿ� ��ġ) - (���� ���� �ڿ� ��ġ)
            reward += self._calculate_combat_exchange_reward(bot)
            
            # 5. ���� ��� ���� (NEW: Threat-based rewards)
            # ���� ��ũ �ǹ� �߰�, �Ʊ� ���� ü�� ���� ��
            reward += self._calculate_threat_based_reward(bot)
            
            # 6. �þ� Ȯ�� ���� (NEW: Vision acquisition)
            # ���� ��ġ�� �ľ��ϰų� �߿��� ������ ������ ����
            reward += self._calculate_vision_reward(bot)
            
        except Exception as e:
            # ���� �߻� �� ���� 0 ��ȯ
            print(f"[WARNING] Reward calculation error: {e}")
            return 0.0
        
        return reward
    
    def _calculate_creep_reward(self, bot) -> float:
        """
        ����(Creep) Ŀ������ ���� ���
        
        ������ ���� �а� �������� ���� ������ �����Ͽ�,
        ������ �����ϰ� ���� ����(Creep Tumor)�� �ɵ��� �����մϴ�.
        
        Returns:
            ���� ���� ���� (float)
        """
        try:
            if not hasattr(bot, 'state') or not bot.state:
                return 0.0
            
            if not hasattr(bot.state, 'creep') or not bot.state.creep:
                return 0.0
            
            # �� ũ�� ���
            map_width = bot.game_info.map_size[0]
            map_height = bot.game_info.map_size[1]
            total_map_area = map_width * map_height
            
            if total_map_area == 0:
                return 0.0
            
            # ���� Ŀ������ ���
            creep_coverage = np.sum(bot.state.creep) / total_map_area
            
            # ���� Ŀ������ ��� ������ ���� (������ ������ ����)
            coverage_delta = creep_coverage - self.previous_creep_coverage
            reward = coverage_delta * 10.0  # ����ġ ���� (5.0 -> 10.0���� ����)
            
            # ���� Ŀ������ ���� (�� ��ǵ�)
            reward += creep_coverage * 5.0  # ����ġ ���� (2.0 -> 5.0)
            
            # ���� ����(Creep Tumor) ���� ���� (NEW)
            if hasattr(bot, 'structures'):
                creep_tumors = bot.structures.filter(lambda s: s.name == 'CreepTumor')
                tumor_count = len(creep_tumors)
                # ���� ������ �������� ���� (�ִ� 3.0)
                reward += min(tumor_count * 0.5, 3.0)
            
            # ����(Queen)�� ���� ���� ���� �ൿ ���� (NEW)
            if hasattr(bot, 'units'):
                queens = bot.units.filter(lambda u: u.name == 'Queen')
                for queen in queens:
                    # ���� ���� ���� ���� ���� Ȯ��
                    if hasattr(queen, 'energy') and queen.energy >= 25:
                        # �������� ����ϸ� ���� ���� (���� ����)
                        reward += 0.1
            
            self.previous_creep_coverage = creep_coverage
            
            return reward
            
        except Exception:
            return 0.0
    
    def _calculate_larva_efficiency_reward(self, bot) -> float:
        """
        ���(Larva) ȿ���� ���� ���
        
        ������ �� �ؼ� ��ٰ� 3���� �̻� �׿������� ���� (�г�Ƽ)
        ��ٰ� ���ϼ��� �� ū ���Ƽ�� �޽��ϴ�.
        
        Returns:
            ��� ȿ���� ���� ���� (float, ���� ����)
        """
        try:
            if not hasattr(bot, 'townhalls'):
                return 0.0
            
            total_larva_excess = 0
            
            for hatch in bot.townhalls:
                # ��� ���� Ȯ�� (��ó�� �ֺ� 5 Ÿ�� �̳�)
                if hasattr(bot, 'units'):
                    larva_units = bot.units.larva.closer_than(5, hatch.position)
                    larva_count = len(larva_units)
                    
                    # ��ٰ� 3���� �̻� �׿������� ����
                    if larva_count > 3:
                        excess = larva_count - 3
                        total_larva_excess += excess
            
            # ���Ƽ: ��ٰ� ���ϼ��� ����
            penalty = -0.1 * total_larva_excess
            
            return penalty
            
        except Exception:
            return 0.0
    
    def _calculate_resource_turnover_reward(self, bot) -> float:
        """
        �ڿ� ȸ���� ���� ���
        
        �̳׶��� 2000 �̻� ������ '���� �� ���� �ִ�'�� ���̹Ƿ� ����
        ���״� ���� ����� ���ϴ�.
        
        Returns:
            �ڿ� ȸ���� ���� ���� (float, ���� ����)
        """
        try:
            if not hasattr(bot, 'minerals'):
                return 0.0
            
            minerals = bot.minerals
            
            # �̳׶��� 2000 �̻� ������ ���Ƽ
            if minerals > 2000:
                excess = minerals - 2000
                penalty = -0.05 * (excess / 1000)  # 1000���� -0.05�� ����
                return penalty
            
            # �ڿ��� �� ����ϰ� ������ ���� ����
            if minerals < 500:
                return 0.01
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_combat_exchange_reward(self, bot) -> float:
        """
        ���� ������ ���� ���
        
        (���� �ı��� �� �ڿ� ��ġ) - (���� ���� �ڿ� ��ġ)�� ��ȭ���� ����
        
        Returns:
            ���� ������ ���� ���� (float)
        """
        try:
            if not hasattr(bot, 'state') or not bot.state:
                return 0.0
            
            if not hasattr(bot.state, 'score'):
                return 0.0
            
            score = bot.state.score
            
            # ���� ������ ���
            current_kill_value = getattr(score, 'kill_value_units', 0)
            current_lost_value = getattr(score, 'lost_value_units', 0)
            current_net_value = current_kill_value - current_lost_value
            
            # ���� ������ ��� ��ȭ��
            delta_value = current_net_value - self.previous_score
            
            # ��ȭ���� ����� ���� (�Ҹ��� ȿ��)
            reward = delta_value * 0.001
            
            self.previous_score = current_net_value
            
            return reward
            
        except Exception:
            return 0.0
    
    def _calculate_threat_based_reward(self, bot) -> float:
        """
        ���� ��� ���� ��� (NEW)
        
        - ���� ��ũ �ǹ� �߰� �� ���� (���� ȹ��)
        - �Ʊ� ������ ü�� ����(Save) �� ����
        - ���� ������ ���� ��� ����
        
        Returns:
            ���� ��� ���� ���� (float)
        """
        try:
            reward = 0.0
            
            # 1. ���� ��ũ �ǹ� �߰� ���� (���� ȹ��)
            if hasattr(bot, 'enemy_structures'):
                tech_buildings = ['Factory', 'Starport', 'RoboticsFacility', 'Stargate', 
                                 'CyberneticsCore', 'TwilightCouncil', 'FusionCore']
                for building_type in tech_buildings:
                    if hasattr(bot.enemy_structures, building_type.lower()):
                        count = len(getattr(bot.enemy_structures, building_type.lower()))
                        if count > 0:
                            # ��ũ �ǹ� �߰� �� ���� (���� ��ġ)
                            reward += 0.5 * count
            
            # 1-1. ���� ��ũ �ǹ� �ı� ���� (���� ����) - NEW
            # ���� �����Ӱ� ���Ͽ� �ı��� �ǹ� �� Ȯ��
            if not hasattr(self, '_previous_enemy_tech_count'):
                self._previous_enemy_tech_count = {}
            
            current_tech_count = {}
            if hasattr(bot, 'enemy_structures'):
                for building_type in tech_buildings:
                    if hasattr(bot.enemy_structures, building_type.lower()):
                        current_tech_count[building_type] = len(
                            getattr(bot.enemy_structures, building_type.lower())
                        )
            
            # �ı��� �ǹ��� ���� ����
            for building_type, current_count in current_tech_count.items():
                previous_count = self._previous_enemy_tech_count.get(building_type, current_count)
                if previous_count > current_count:
                    destroyed = previous_count - current_count
                    # ��ũ �ǹ� �ı� �� ū ���� (���� ����)
                    reward += 2.0 * destroyed
            
            self._previous_enemy_tech_count = current_tech_count
            
            # 2. �Ʊ� ���� ü�� ���� ����
            if hasattr(bot, 'units'):
                total_health = 0
                total_max_health = 0
                
                # ���� ���ֵ��� ü�� ���� ���
                combat_units = ['Zergling', 'Roach', 'Hydralisk', 'Mutalisk', 'Lurker']
                for unit_type in combat_units:
                    if hasattr(bot.units, unit_type.lower()):
                        units = getattr(bot.units, unit_type.lower())
                        for unit in units:
                            if hasattr(unit, 'health') and hasattr(unit, 'health_max'):
                                total_health += unit.health
                                total_max_health += unit.health_max
                
                # ü�� ������ �������� ���� (���� ����)
                if total_max_health > 0:
                    health_ratio = total_health / total_max_health
                    # ü�� ������ 0.8 �̻��̸� ����
                    if health_ratio > 0.8:
                        reward += 0.1 * (health_ratio - 0.8) * 10
            
            # 3. ���� ������ ���� ��� ���� (������ - ü�� �ս��� ������)
            # ���� ü�°� �񱳴� ���� �����ӿ��� ó��
            
            # 4. ���� ���� (NEW: Risk-Aware Reward)
            # ������ ���� �ʰ� ü���� �����ϸ� �������� �� ����
            if not hasattr(self, '_previous_unit_count'):
                self._previous_unit_count = 0
                self._previous_total_health = 0
            
            current_unit_count = 0
            current_total_health = 0
            if hasattr(bot, 'units'):
                for unit_type in combat_units:
                    if hasattr(bot.units, unit_type.lower()):
                        units = getattr(bot.units, unit_type.lower())
                        current_unit_count += len(units)
                        for unit in units:
                            if hasattr(unit, 'health'):
                                current_total_health += unit.health
            
            # ���� ���� �����ǰų� �����߰�, ü�� �ս��� ������ ���� ����
            if (current_unit_count >= self._previous_unit_count * 0.9 and 
                current_total_health > self._previous_total_health * 0.8):
                # ���� ���� ���� (���� ����)
                reward += 0.5
            
            self._previous_unit_count = current_unit_count
            self._previous_total_health = current_total_health
            
            return reward
            
        except Exception:
            return 0.0
    
    def _calculate_vision_reward(self, bot) -> float:
        """
        �þ� Ȯ�� ���� ��� (NEW)
        
        - ���� ��ġ�� �ľ��ϰų� �߿��� ������ ������ ����
        - ���� ��Ƽ Ÿ�̹� ���� �� ����
        
        Returns:
            �þ� Ȯ�� ���� ���� (float)
        """
        try:
            reward = 0.0
            
            # 1. ���� ��Ƽ �߰� ����
            if hasattr(bot, 'enemy_structures'):
                if hasattr(bot.enemy_structures, 'townhall'):
                    enemy_bases = len(bot.enemy_structures.townhall)
                    if enemy_bases > 1:
                        # ���� ��Ƽ �߰� �� ���� (���� ��ġ)
                        reward += 1.0 * (enemy_bases - 1)
            
            # 2. ���� ���� ��ġ �ľ� ����
            if hasattr(bot, 'enemy_units'):
                enemy_count = len(bot.enemy_units)
                if enemy_count > 0:
                    # ���� ���� ��ġ�� �ľ��ϸ� ���� ����
                    reward += 0.05 * min(enemy_count, 20)  # �ִ� 1.0
            
            # 3. ���� ���� Ÿ�̹� ���� (���� �ǹ� �ı�)
            # �̴� ���� ������ ���󿡼� �̹� ó����
            
            return reward
            
        except Exception:
            return 0.0
    
    def reset(self):
        """
        ���Ǽҵ� �� ���� �ʱ�ȭ
        
        ������ ������ �� ������ ���۵� �� ȣ��˴ϴ�.
        """
        self.previous_score = 0
        self.previous_creep_coverage = 0.0
        self.previous_larva_efficiency = 0.0
        # Reset threat-based reward tracking
        if hasattr(self, '_previous_enemy_tech_count'):
            self._previous_enemy_tech_count = {}
        if hasattr(self, '_previous_unit_count'):
            self._previous_unit_count = 0
        if hasattr(self, '_previous_total_health'):
            self._previous_total_health = 0


# ��� ���� (�ּ� ó��)
"""
# ���� �������� ��� ����:
reward_system = ZergRewardSystem()

async def on_step(self, iteration: int):
    # ... ���� ���� ...
    
    # �� ���� ���� ���
    step_reward = reward_system.calculate_step_reward(self)
    
    # ��ȭ�н� �н��� ���� ���
    if self.train_mode:
        self.rl_agent.update_reward(step_reward)
    
    # ... ������ ���� ...

async def on_end(self, game_result):
    # ���� ���� �� ���� �ý��� �ʱ�ȭ
    reward_system.reset()
"""

