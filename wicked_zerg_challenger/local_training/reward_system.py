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
        """보상 시스템 초기화"""
        self.previous_score = 0
        self.previous_creep_coverage = 0.0
        self.previous_larva_efficiency = 0.0
        # 확장 추적
        self.previous_base_count = 1
        self.expansion_reward_given = set()
        # 업그레이드 추적
        self.completed_upgrades = set()
        # 보급 차단 추적
        self.supply_blocked_steps = 0
        # 군대 가치 추적
        self.previous_army_value = 0
        
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
            
            # 6. 시야 확보 보상 (Vision acquisition)
            reward += self._calculate_vision_reward(bot)

            # 7. 확장 타이밍 보상 (Expansion timing)
            reward += self._calculate_expansion_reward(bot)

            # 8. 업그레이드 연구 보상 (Upgrade research)
            reward += self._calculate_upgrade_reward(bot)

            # 9. 보급 차단 페널티 (Supply blocked penalty)
            reward += self._calculate_supply_blocked_penalty(bot)

            # 10. 군대 효율성 보상 (Army efficiency)
            reward += self._calculate_army_efficiency_reward(bot)

            # 11. 매크로 해처리 보상 (Macro hatchery)
            reward += self._calculate_macro_hatchery_reward(bot)

            # 12. ★★★ NEW: 초반 방어 병력 보상 (Early defense units) ★★★
            reward += self._calculate_early_defense_reward(bot)

            # 13. ★★★ NEW: 적 피해 보상 (Enemy damage reward) ★★★
            reward += self._calculate_enemy_damage_reward(bot)

            # 14. ★★★ NEW: 전략적 판단 보상 (Strategic Decision Reward) ★★★
            reward += self._calculate_strategic_decision_reward(bot)

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
        자원 회전율 기반 보상

        ★★★ FIX: 2분 이후 미네랄 뱅킹 강력 페널티 ★★★
        - 2분(120초) 이후 미네랄 500+ → 페널티
        - 미네랄 1000+ → 매우 강한 페널티
        - 시간이 지날수록 페널티 증가

        Returns:
            자원 회전율 보상 값 (float, 주로 페널티)
        """
        try:
            if not hasattr(bot, 'minerals') or not hasattr(bot, 'time'):
                return 0.0

            minerals = bot.minerals
            game_time = bot.time  # 게임 시간 (초)

            # ★★★ NEW: 2분(120초) 이후 미네랄 뱅킹 강력 페널티 ★★★
            if game_time >= 120:  # 2분 이후
                if minerals >= 1500:
                    # 미네랄 1500+ → 매우 강한 페널티 (초당 증가)
                    time_factor = min((game_time - 120) / 60.0, 5.0)  # 최대 5배
                    penalty = -0.5 * (minerals / 1000.0) * (1.0 + time_factor)
                    return penalty
                elif minerals >= 1000:
                    # 미네랄 1000-1500 → 강한 페널티
                    time_factor = min((game_time - 120) / 60.0, 3.0)  # 최대 3배
                    penalty = -0.3 * (minerals / 1000.0) * (1.0 + time_factor)
                    return penalty
                elif minerals >= 500:
                    # 미네랄 500-1000 → 중간 페널티
                    penalty = -0.1 * ((minerals - 500) / 500.0)
                    return penalty

            # 초반(2분 이내)은 기존 로직 유지
            if minerals > 2000:
                excess = minerals - 2000
                penalty = -0.05 * (excess / 1000)
                return penalty

            # 자원을 잘 사용하고 있으면 소량 보상
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
    
    def _calculate_expansion_reward(self, bot) -> float:
        """
        확장 타이밍 보상 계산

        적절한 시점에 확장하면 보상:
        - 2번째 기지: 2분 이전 = +3.0, 3분 이전 = +1.5
        - 3번째 기지: 5분 이전 = +3.0, 6분 이전 = +1.5
        - 4번째 기지: 8분 이전 = +2.0

        Returns:
            확장 타이밍 보상 (float)
        """
        try:
            if not hasattr(bot, 'townhalls'):
                return 0.0

            reward = 0.0
            base_count = bot.townhalls.amount
            game_time = getattr(bot, 'time', 0)

            # 기지 수가 증가했는지 확인
            if base_count > self.previous_base_count:
                # 새 확장 보상
                if base_count == 2 and 2 not in self.expansion_reward_given:
                    if game_time < 120:  # 2분 이전
                        reward += 3.0
                    elif game_time < 180:  # 3분 이전
                        reward += 1.5
                    self.expansion_reward_given.add(2)

                elif base_count == 3 and 3 not in self.expansion_reward_given:
                    if game_time < 300:  # 5분 이전
                        reward += 3.0
                    elif game_time < 360:  # 6분 이전
                        reward += 1.5
                    self.expansion_reward_given.add(3)

                elif base_count == 4 and 4 not in self.expansion_reward_given:
                    if game_time < 480:  # 8분 이전
                        reward += 2.0
                    self.expansion_reward_given.add(4)

                self.previous_base_count = base_count

            return reward

        except Exception:
            return 0.0

    def _calculate_upgrade_reward(self, bot) -> float:
        """
        업그레이드 연구 보상 계산

        공방 업그레이드 완료 시 보상:
        - 1레벨 업그레이드: +1.0
        - 2레벨 업그레이드: +1.5
        - 3레벨 업그레이드: +2.0

        Returns:
            업그레이드 보상 (float)
        """
        try:
            if not hasattr(bot, 'state') or not bot.state:
                return 0.0

            if not hasattr(bot.state, 'upgrades'):
                return 0.0

            reward = 0.0
            current_upgrades = set(bot.state.upgrades)

            # 새로 완료된 업그레이드 확인
            new_upgrades = current_upgrades - self.completed_upgrades

            for upgrade in new_upgrades:
                upgrade_name = str(upgrade).upper()
                if 'LEVEL1' in upgrade_name:
                    reward += 1.0
                elif 'LEVEL2' in upgrade_name:
                    reward += 1.5
                elif 'LEVEL3' in upgrade_name:
                    reward += 2.0
                else:
                    # 기타 업그레이드 (저글링 속도 등)
                    reward += 0.5

            self.completed_upgrades = current_upgrades

            return reward

        except Exception:
            return 0.0

    def _calculate_supply_blocked_penalty(self, bot) -> float:
        """
        보급 차단 페널티 계산

        서플라이 블록 상태에 페널티:
        - 블록 상태에서 연속으로 대기하면 페널티 증가

        Returns:
            보급 차단 페널티 (float, 음수)
        """
        try:
            if not hasattr(bot, 'supply_left') or not hasattr(bot, 'supply_cap'):
                return 0.0

            # 서플라이 풀 상태 체크 (오버로드 생산 여유 없음)
            if bot.supply_left <= 0 and bot.supply_cap < 200:
                self.supply_blocked_steps += 1
                # 연속 블록 시 페널티 증가
                penalty = -0.05 * min(self.supply_blocked_steps, 10)
                return penalty
            else:
                self.supply_blocked_steps = 0
                return 0.0

        except Exception:
            return 0.0

    def _calculate_army_efficiency_reward(self, bot) -> float:
        """
        군대 효율성 보상 계산

        효율적인 군대 조합 및 성장 보상:
        - 군대 가치 증가 시 보상
        - 일꾼 대비 적절한 군대 비율 보상

        Returns:
            군대 효율성 보상 (float)
        """
        try:
            if not hasattr(bot, 'units'):
                return 0.0

            reward = 0.0

            # 군대 가치 계산 (유닛 수 * 대략적 가치)
            unit_values = {
                'zergling': 25,
                'baneling': 50,
                'roach': 75,
                'ravager': 100,
                'hydralisk': 100,
                'mutalisk': 100,
                'lurker': 150,
                'ultralisk': 300,
                'broodlord': 300,
                'corruptor': 150,
                'infestor': 150,
                'viper': 200,
            }

            current_army_value = 0
            for unit_type, value in unit_values.items():
                if hasattr(bot.units, unit_type):
                    units = getattr(bot.units, unit_type)
                    current_army_value += len(units) * value

            # 군대 가치 증가 보상
            if current_army_value > self.previous_army_value:
                value_increase = current_army_value - self.previous_army_value
                reward += value_increase * 0.0001  # 소규모 증가 보상

            self.previous_army_value = current_army_value

            # 일꾼 대비 군대 비율 체크
            worker_count = 0
            if hasattr(bot, 'workers'):
                worker_count = bot.workers.amount

            game_time = getattr(bot, 'time', 0)

            # 6분 이후에는 최소 군대가 있어야 함
            if game_time > 360:
                if current_army_value > worker_count * 50:  # 군대 > 일꾼 * 50
                    reward += 0.1  # 적절한 군대 유지 보상

            return reward

        except Exception:
            return 0.0

    def _calculate_macro_hatchery_reward(self, bot) -> float:
        """
        매크로 해처리 보상 계산

        라바 생산력 유지 보상:
        - 기지당 평균 라바 수가 2-3개면 보상
        - 너무 많은 라바 적체는 페널티 (이미 _calculate_larva_efficiency_reward에서 처리)

        Returns:
            매크로 해처리 보상 (float)
        """
        try:
            if not hasattr(bot, 'townhalls') or not hasattr(bot, 'larva'):
                return 0.0

            reward = 0.0
            base_count = bot.townhalls.ready.amount if hasattr(bot.townhalls, 'ready') else 0
            larva_count = len(bot.larva)

            if base_count == 0:
                return 0.0

            avg_larva = larva_count / base_count

            # 기지당 평균 라바가 적정 수준이면 보상
            if 1.5 <= avg_larva <= 3.0:
                reward += 0.05

            # 매크로 해처리 보유 시 추가 보상
            game_time = getattr(bot, 'time', 0)
            if game_time > 480:  # 8분 이후
                # 본진 주변에 추가 해처리가 있으면 보상
                if base_count >= 3 and larva_count >= base_count * 2:
                    reward += 0.1

            return reward

        except Exception:
            return 0.0

    def _calculate_early_defense_reward(self, bot) -> float:
        """
        ★★★ NEW: 초반 방어 병력 보상 ★★★

        사용자 요구사항: "1분동안 아무것도 안해서 병력이 3분안으로 뽑혀있지 않음"

        해결:
        - 1분(60초) 이내: 드론 12 목표
        - 2분(120초) 이내: 저글링 4+ 또는 퀸 1 목표
        - 3분(180초) 이내: 저글링 8+ 또는 퀸 2 목표

        시간 내 목표 달성 시 강한 보상
        미달성 시 강한 페널티

        Returns:
            초반 방어 병력 보상 (float)
        """
        try:
            game_time = getattr(bot, "time", 0)

            if not hasattr(bot, "units"):
                return 0.0

            reward = 0.0

            # 드론 수 체크
            drones = bot.units.filter(lambda u: u.name == "Drone")
            drone_count = len(drones)

            # 저글링 수 체크
            zerglings = bot.units.filter(lambda u: u.name == "Zergling")
            zergling_count = len(zerglings)

            # 퀸 수 체크
            queens = bot.units.filter(lambda u: u.name == "Queen")
            queen_count = len(queens)

            # ★★★ 1분(60초) 이내: 드론 12 목표 ★★★
            if game_time <= 60:
                if drone_count >= 12:
                    reward += 1.0  # 강한 보상
                elif drone_count >= 10:
                    reward += 0.5
                else:
                    # 페널티: 1분에 드론 10 미만
                    reward -= 0.3

            # ★★★ 2분(120초) 이내: 저글링 4+ 또는 퀸 1 목표 ★★★
            elif 60 < game_time <= 120:
                # 드론 유지 보상
                if drone_count >= 14:
                    reward += 0.5

                # 방어 병력 체크
                if zergling_count >= 4 or queen_count >= 1:
                    reward += 1.5  # 매우 강한 보상
                elif zergling_count >= 2:
                    reward += 0.5
                else:
                    # 페널티: 2분에 병력 없음
                    reward -= 2.0  # ★ 강화된 페널티 (1.0 → 2.0) ★

            # ★★★ 3분(180초) 이내: 저글링 8+ 또는 퀸 2 목표 ★★★
            elif 120 < game_time <= 180:
                # 드론 유지 보상
                if drone_count >= 20:
                    reward += 0.3

                # 방어 병력 체크 (더 강화)
                if zergling_count >= 8 or queen_count >= 2:
                    reward += 2.0  # 매우 강한 보상
                elif zergling_count >= 6 or queen_count >= 1:
                    reward += 1.0
                elif zergling_count >= 4:
                    reward += 0.3
                else:
                    # 페널티: 3분에 병력 부족
                    reward -= 2.5  # ★ 강화된 페널티 (1.5 → 2.5) ★

            # ★★★ 3분 이후: 지속적인 병력 유지 보상 ★★★
            elif game_time > 180:
                total_army = zergling_count + queen_count * 2  # 퀸은 2배 가중치

                if total_army >= 15:
                    reward += 1.0
                elif total_army >= 10:
                    reward += 0.5
                elif total_army < 5:
                    # 페널티: 3분 이후 병력 5 미만
                    reward -= 1.0

            return reward

        except Exception:
            return 0.0

    def _calculate_enemy_damage_reward(self, bot) -> float:
        """
        ★★★ NEW: 적 피해 보상 ★★★

        사용자 요구사항: "상대의 병력과 일꾼손실을 더 일으킬수록 보상"

        보상 체계:
        - 적 유닛 킬: +0.01 per unit
        - 적 일꾼 킬: +0.05 per worker (5배 가중치!)
        - 적 건물 파괴: +0.10 per building
        - 적 기지 파괴: +1.0 (매우 강한 보상)

        Returns:
            적 피해 보상 (float)
        """
        try:
            if not hasattr(bot, "state") or not bot.state:
                return 0.0

            if not hasattr(bot.state, "score"):
                return 0.0

            score = bot.state.score
            reward = 0.0

            # 적 유닛 킬 수
            killed_units = getattr(score, "killed_value_units", 0)
            killed_structures = getattr(score, "killed_value_structures", 0)

            # 이전 프레임과 비교하여 증가분만 보상
            if not hasattr(self, "_previous_killed_units"):
                self._previous_killed_units = 0
            if not hasattr(self, "_previous_killed_structures"):
                self._previous_killed_structures = 0

            # 유닛 킬 증가분
            unit_kills_delta = killed_units - self._previous_killed_units
            if unit_kills_delta > 0:
                # 기본 유닛 킬 보상
                reward += unit_kills_delta * 0.001  # 가치 1000당 1.0 보상

                # ★★★ 특별 보상: 적 일꾼 킬 감지 ★★★
                # 일꾼 가치는 보통 50 정도이므로, 유닛 킬이 50 단위로 증가하면 일꾼 킬로 추정
                if 40 <= unit_kills_delta <= 70:  # 일꾼 가치 범위
                    reward += 0.5  # 일꾼 킬 특별 보상!
                    if hasattr(bot, "time"):
                        game_time = bot.time
                        if game_time < 180:  # 3분 이내 일꾼 킬은 더 강한 보상
                            reward += 1.0  # 초반 일꾼 킬 = 매우 강력!

            # 건물 파괴 증가분
            structure_kills_delta = killed_structures - self._previous_killed_structures
            if structure_kills_delta > 0:
                # 건물 파괴 보상
                reward += structure_kills_delta * 0.002  # 가치 1000당 2.0 보상

                # ★★★ 특별 보상: 적 기지 파괴 감지 ★★★
                # 해처리/넥서스/커맨드센터 가치는 보통 350-450
                if structure_kills_delta >= 300:  # 기지 파괴
                    reward += 3.0  # 기지 파괴 특별 보상!

            # 이전 값 업데이트
            self._previous_killed_units = killed_units
            self._previous_killed_structures = killed_structures

            return reward

        except Exception:
            return 0.0

    def _calculate_strategic_decision_reward(self, bot) -> float:
        """
        ★★★ NEW: 전략적 판단 보상 (Strategic Decision Reward) ★★★

        RL Agent의 "직관"을 날카롭게 하기 위한 보상 셰이핑.
        단순히 이기는 것뿐만 아니라, "유리할 때 싸우고 불리할 때 참는" 판단 자체에 보상을 줌.

        로직:
        1. 공격 모드(ATTACK/ALL_IN)일 때:
           - 군사력이 압도적(1.5배 이상)이면 보상 (+0.05)
           - 군사력이 열세(0.8배 이하)인데 공격하면 페널티 (-0.05)
        2. 방어 모드(DEFEND/EMERGENCY)일 때:
           - 군사력이 열세일 때 방어하면 보상 (+0.05)
           - 군사력이 압도적인데 계속 방어만 하면 페널티 (-0.02) (소극적 플레이 방지)

        Returns:
            전략적 판단 보상 (float)
        """
        try:
            if not hasattr(bot, "strategy_manager") or not bot.strategy_manager:
                return 0.0

            # 현재 전략 모드 확인
            current_mode = str(bot.strategy_manager.current_mode).split('.')[-1]
            
            # 군사력 평가
            our_army_value = 0
            if hasattr(bot, "units"):
                # 전투 유닛만 계산 (일꾼, 오버로드 제외)
                combat_units = bot.units.filter(lambda u: u.name not in ["Drone", "Overlord", "Larva", "Egg"])
                our_army_value = len(combat_units) * 100 # 단순 수량 * 100 (추후 정밀 계산 가능)
            
            enemy_army_value = 0
            if hasattr(bot, "enemy_units"):
                enemy_army_value = len(bot.enemy_units) * 100
            
            # 0으로 나누기 방지
            if enemy_army_value == 0:
                enemy_army_value = 1  # 최소값

            army_ratio = our_army_value / enemy_army_value
            reward = 0.0

            # 1. 공격 모드 평가
            if current_mode in ["ATTACK", "ALL_IN", "AGGRESSIVE"]:
                if army_ratio >= 1.5:
                    # 압도적 우위에서 공격: 훌륭한 판단
                    reward += 0.05
                elif army_ratio < 0.8:
                    # 열세에서 무리한 공격: 나쁜 판단 (자살 공격 방지)
                    reward -= 0.05
            
            # 2. 방어 모드 평가
            elif current_mode in ["DEFEND", "EMERGENCY"]:
                if army_ratio < 0.9:
                    # 열세에서 방어: 현명한 판단
                    reward += 0.05
                elif army_ratio > 2.0:
                    # 압도적 우위에서 너무 소극적: 나쁜 판단 (승기 잡아야 함)
                    reward -= 0.02

            return reward

        except Exception:
            return 0.0

    def reset(self):
        """
        에피소드 끝 보상 초기화

        게임이 끝나고 새 게임이 시작될 때 호출됩니다.
        """
        self.previous_score = 0
        self.previous_creep_coverage = 0.0
        self.previous_larva_efficiency = 0.0
        # 확장 추적 리셋
        self.previous_base_count = 1
        self.expansion_reward_given = set()
        # 업그레이드 추적 리셋
        self.completed_upgrades = set()
        # 보급 차단 추적 리셋
        self.supply_blocked_steps = 0
        # 군대 가치 추적 리셋
        self.previous_army_value = 0
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

