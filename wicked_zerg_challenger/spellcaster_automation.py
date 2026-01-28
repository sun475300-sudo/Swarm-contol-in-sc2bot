# -*- coding: utf-8 -*-
"""
SpellCaster Automation - 마법 유닛 스킬 자동화

퀸, 궤멸충, 살모사, 감염충의 스킬을 자동으로 사용합니다:
- 퀸: 체력 낮은 유닛 수혈 (Transfuse)
- 궤멸충: 적 밀집 지역 담즙 (Corrosive Bile)
- 살모사: 고가치 유닛 납치 (Abduct), 흑구름 (Blinding Cloud)
- 감염충: 신경 기생충 (Neural Parasite), 진균 번식 (Fungal Growth)

효과: 고급 유닛 활용도 0% → 100%
"""

from typing import List, Dict, Optional
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        QUEEN = "QUEEN"
        RAVAGER = "RAVAGER"
        VIPER = "VIPER"
        INFESTOR = "INFESTOR"
    class AbilityId:
        TRANSFUSION_TRANSFUSION = "TRANSFUSION_TRANSFUSION"
        EFFECT_CORROSIVEBILE = "EFFECT_CORROSIVEBILE"
        EFFECT_ABDUCT = "EFFECT_ABDUCT"
        EFFECT_BLINDINGCLOUD = "EFFECT_BLINDINGCLOUD"
        NEURALPARASITE_NEURALPARASITE = "NEURALPARASITE_NEURALPARASITE"
        FUNGALGROWTH_FUNGALGROWTH = "FUNGALGROWTH_FUNGALGROWTH"
    class UpgradeId:
        pass
    Point2 = tuple


class SpellCasterAutomation:
    """
    ★ SpellCaster Automation ★

    마법 유닛들의 스킬을 자동으로 사용하여
    전투 효율을 극대화합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("SpellCaster")

        # ★ 체크 주기 ★
        self.last_check = 0
        self.check_interval = 11  # 약 0.5초마다

        # ★ 스킬 쿨다운 추적 ★
        self.last_skill_used = {}  # {unit_tag: {ability: game_time}}

        # ★ 스킬 우선순위 ★
        self.queen_transfuse_threshold = 0.35  # 체력 35% 이하
        self.ravager_min_targets = 3  # 최소 3명 이상 밀집
        self.viper_abduct_range = 9
        self.infestor_fungal_min_targets = 5

        # ★ 통계 ★
        self.skills_used = {
            "transfuse": 0,
            "bile": 0,
            "abduct": 0,
            "blinding_cloud": 0,
            "neural": 0,
            "fungal": 0,
        }

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration - self.last_check < self.check_interval:
                return

            self.last_check = iteration

            # ★ 1. 퀸 수혈 (Transfuse) ★
            await self._queen_transfuse()

            # ★ 2. 궤멸충 담즙 (Corrosive Bile) ★
            await self._ravager_bile()

            # ★ 3. 살모사 스킬 (Abduct, Blinding Cloud) ★
            await self._viper_skills()

            # ★ 4. 감염충 스킬 (Neural, Fungal) ★
            await self._infestor_skills()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[SPELLCASTER] Error: {e}")

    async def _queen_transfuse(self):
        """
        퀸 수혈 (Transfuse) - 체력 낮은 유닛 치료
        """
        if not hasattr(self.bot, "units"):
            return

        queens = self.bot.units(UnitTypeId.QUEEN)
        if not queens:
            return

        for queen in queens:
            # 에너지 체크 (50 필요)
            if queen.energy < 50:
                continue

            # 쿨다운 체크
            if self._is_on_cooldown(queen.tag, "transfuse", 10):
                continue

            # 체력 낮은 유닛 찾기
            injured_units = []
            for unit in self.bot.units:
                if unit.health_percentage < self.queen_transfuse_threshold:
                    # 기계 유닛은 치료 불가
                    type_name = getattr(unit.type_id, "name", "").upper()
                    if "MECHANICAL" in type_name or "BUILDING" in type_name:
                        continue

                    if queen.distance_to(unit) < 7:  # 사거리
                        injured_units.append(unit)

            if not injured_units:
                continue

            # 가장 체력이 낮은 유닛 선택
            target = min(injured_units, key=lambda u: u.health_percentage)

            # 수혈 실행
            abilities = await self.bot.get_available_abilities(queen)
            if AbilityId.TRANSFUSION_TRANSFUSION in abilities:
                self.bot.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, target))
                self._record_skill_use(queen.tag, "transfuse")
                self.skills_used["transfuse"] += 1

                game_time = getattr(self.bot, "time", 0)
                self.logger.info(
                    f"[{int(game_time)}s] ★ TRANSFUSE: {target.type_id.name} "
                    f"({target.health}/{target.health_max}) ★"
                )
                break  # 한 프레임에 하나만

    async def _ravager_bile(self):
        """
        궤멸충 담즙 (Corrosive Bile) - 적 밀집 지역 공격
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return

        ravagers = self.bot.units(UnitTypeId.RAVAGER)
        if not ravagers:
            return

        enemy_units = self.bot.enemy_units

        for ravager in ravagers:
            # 쿨다운 체크 (7초)
            if self._is_on_cooldown(ravager.tag, "bile", 7):
                continue

            # 사거리 내 적 찾기 (사거리 9)
            enemies_in_range = enemy_units.closer_than(9, ravager)
            if not enemies_in_range:
                continue

            # 밀집 지역 찾기
            best_target, target_count = self._find_bile_target(enemies_in_range)

            if target_count < self.ravager_min_targets:
                continue

            # 담즙 발사
            abilities = await self.bot.get_available_abilities(ravager)
            if AbilityId.EFFECT_CORROSIVEBILE in abilities:
                self.bot.do(ravager(AbilityId.EFFECT_CORROSIVEBILE, best_target))
                self._record_skill_use(ravager.tag, "bile")
                self.skills_used["bile"] += 1

                game_time = getattr(self.bot, "time", 0)
                self.logger.info(
                    f"[{int(game_time)}s] ★ BILE: {target_count} targets ★"
                )
                break  # 한 프레임에 하나만

    def _find_bile_target(self, enemies: List) -> tuple:
        """
        담즙 최적 목표 위치 찾기

        Args:
            enemies: 적 유닛 리스트

        Returns:
            (best_position, target_count)
        """
        best_pos = None
        max_count = 0

        for enemy in enemies:
            pos = enemy.position
            # 2.5 반경 내 적 개수 (담즙 효과 범위)
            nearby = sum(1 for e in enemies if e.position.distance_to(pos) < 2.5)

            if nearby > max_count:
                max_count = nearby
                best_pos = pos

        return best_pos, max_count

    async def _viper_skills(self):
        """
        살모사 스킬 (Abduct, Blinding Cloud)
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return

        vipers = self.bot.units(UnitTypeId.VIPER)
        if not vipers:
            return

        enemy_units = self.bot.enemy_units

        for viper in vipers:
            # ★ 1. 납치 (Abduct) - 75 에너지 ★
            if viper.energy >= 75:
                if not self._is_on_cooldown(viper.tag, "abduct", 15):
                    await self._viper_abduct(viper, enemy_units)
                    continue

            # ★ 2. 흑구름 (Blinding Cloud) - 100 에너지 ★
            if viper.energy >= 100:
                if not self._is_on_cooldown(viper.tag, "blinding_cloud", 20):
                    await self._viper_blinding_cloud(viper, enemy_units)
                    continue

    async def _viper_abduct(self, viper, enemies):
        """
        살모사 납치 - 고가치 적 유닛 납치
        """
        # 고가치 유닛 우선순위
        high_value_units = {
            "SIEGETANK", "SIEGETANKSIEGED", "THOR", "BATTLECRUISER",
            "COLOSSUS", "IMMORTAL", "CARRIER", "TEMPEST",
            "RAVAGER", "LURKER", "BROODLORD", "ULTRALISK"
        }

        # 사거리 내 고가치 유닛 찾기
        targets = []
        for enemy in enemies:
            if viper.distance_to(enemy) > self.viper_abduct_range:
                continue

            type_name = getattr(enemy.type_id, "name", "").upper()
            if type_name in high_value_units:
                targets.append(enemy)

        if not targets:
            return

        # 가장 가까운 고가치 유닛 납치
        target = min(targets, key=lambda e: viper.distance_to(e))

        abilities = await self.bot.get_available_abilities(viper)
        if AbilityId.EFFECT_ABDUCT in abilities:
            self.bot.do(viper(AbilityId.EFFECT_ABDUCT, target))
            self._record_skill_use(viper.tag, "abduct")
            self.skills_used["abduct"] += 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ ABDUCT: {target.type_id.name} ★"
            )

    async def _viper_blinding_cloud(self, viper, enemies):
        """
        살모사 흑구름 - 원거리 유닛 무력화
        """
        ranged_units = {
            "MARINE", "MARAUDER", "STALKER", "HYDRALISK",
            "ROACH", "IMMORTAL", "THOR"
        }

        # 원거리 유닛 밀집 지역 찾기
        best_pos = None
        max_count = 0

        for enemy in enemies:
            type_name = getattr(enemy.type_id, "name", "").upper()
            if type_name not in ranged_units:
                continue

            if viper.distance_to(enemy) > 11:  # 사거리
                continue

            pos = enemy.position
            nearby_ranged = sum(
                1 for e in enemies
                if e.position.distance_to(pos) < 4 and
                   getattr(e.type_id, "name", "").upper() in ranged_units
            )

            if nearby_ranged > max_count:
                max_count = nearby_ranged
                best_pos = pos

        if max_count < 3:  # 최소 3명
            return

        abilities = await self.bot.get_available_abilities(viper)
        if AbilityId.EFFECT_BLINDINGCLOUD in abilities:
            self.bot.do(viper(AbilityId.EFFECT_BLINDINGCLOUD, best_pos))
            self._record_skill_use(viper.tag, "blinding_cloud")
            self.skills_used["blinding_cloud"] += 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ BLINDING CLOUD: {max_count} targets ★"
            )

    async def _infestor_skills(self):
        """
        감염충 스킬 (Neural Parasite, Fungal Growth)
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return

        infestors = self.bot.units(UnitTypeId.INFESTOR)
        if not infestors:
            return

        enemy_units = self.bot.enemy_units

        for infestor in infestors:
            # ★ 1. 진균 번식 (Fungal Growth) - 75 에너지 ★
            if infestor.energy >= 75:
                if not self._is_on_cooldown(infestor.tag, "fungal", 10):
                    await self._infestor_fungal(infestor, enemy_units)
                    continue

            # ★ 2. 신경 기생충 (Neural Parasite) - 100 에너지 ★
            if infestor.energy >= 100:
                if not self._is_on_cooldown(infestor.tag, "neural", 20):
                    await self._infestor_neural(infestor, enemy_units)
                    continue

    async def _infestor_fungal(self, infestor, enemies):
        """
        감염충 진균 번식 - 적 밀집 지역 묶기
        """
        # 밀집 지역 찾기 (2 반경 내 5명 이상)
        best_pos = None
        max_count = 0

        for enemy in enemies:
            if infestor.distance_to(enemy) > 10:  # 사거리
                continue

            pos = enemy.position
            nearby = sum(1 for e in enemies if e.position.distance_to(pos) < 2)

            if nearby > max_count:
                max_count = nearby
                best_pos = pos

        if max_count < self.infestor_fungal_min_targets:
            return

        abilities = await self.bot.get_available_abilities(infestor)
        if AbilityId.FUNGALGROWTH_FUNGALGROWTH in abilities:
            self.bot.do(infestor(AbilityId.FUNGALGROWTH_FUNGALGROWTH, best_pos))
            self._record_skill_use(infestor.tag, "fungal")
            self.skills_used["fungal"] += 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ FUNGAL: {max_count} targets ★"
            )

    async def _infestor_neural(self, infestor, enemies):
        """
        감염충 신경 기생충 - 고가치 유닛 빼앗기
        """
        high_value = {
            "THOR", "BATTLECRUISER", "SIEGETANK",
            "COLOSSUS", "IMMORTAL", "CARRIER", "TEMPEST",
            "ULTRALISK", "BROODLORD"
        }

        targets = []
        for enemy in enemies:
            if infestor.distance_to(enemy) > 9:  # 사거리
                continue

            type_name = getattr(enemy.type_id, "name", "").upper()
            if type_name in high_value:
                targets.append(enemy)

        if not targets:
            return

        target = min(targets, key=lambda e: infestor.distance_to(e))

        abilities = await self.bot.get_available_abilities(infestor)
        if AbilityId.NEURALPARASITE_NEURALPARASITE in abilities:
            self.bot.do(infestor(AbilityId.NEURALPARASITE_NEURALPARASITE, target))
            self._record_skill_use(infestor.tag, "neural")
            self.skills_used["neural"] += 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ NEURAL: {target.type_id.name} ★"
            )

    def _is_on_cooldown(self, unit_tag: int, ability: str, cooldown: float) -> bool:
        """
        스킬 쿨다운 체크

        Args:
            unit_tag: 유닛 태그
            ability: 스킬 이름
            cooldown: 쿨다운 시간 (초)

        Returns:
            True if on cooldown
        """
        if unit_tag not in self.last_skill_used:
            return False

        if ability not in self.last_skill_used[unit_tag]:
            return False

        game_time = getattr(self.bot, "time", 0)
        last_used = self.last_skill_used[unit_tag][ability]

        return (game_time - last_used) < cooldown

    def _record_skill_use(self, unit_tag: int, ability: str):
        """
        스킬 사용 기록

        Args:
            unit_tag: 유닛 태그
            ability: 스킬 이름
        """
        game_time = getattr(self.bot, "time", 0)

        if unit_tag not in self.last_skill_used:
            self.last_skill_used[unit_tag] = {}

        self.last_skill_used[unit_tag][ability] = game_time

    def get_statistics(self) -> Dict:
        """통계 반환"""
        return self.skills_used.copy()
