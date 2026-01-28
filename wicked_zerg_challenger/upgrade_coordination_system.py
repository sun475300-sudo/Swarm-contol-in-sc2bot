# -*- coding: utf-8 -*-
"""
Upgrade Coordination System - 업그레이드 전략 타이밍

업그레이드 완료 시점에 맞춰 공격을 조율:
- "공1업 완료 → 5:30 Roach 타이밍 공격"
- "방1업 완료 → 방어 병력 전선 투입"
- "공3방3 완료 → 최종 결전"
"""

from typing import Dict, List, Optional, Tuple
from utils.logger import get_logger

try:
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:
    class UpgradeId:
        # Zerg Upgrades
        ZERGMISSILEWEAPONSLEVEL1 = "ZERGMISSILEWEAPONSLEVEL1"
        ZERGMISSILEWEAPONSLEVEL2 = "ZERGMISSILEWEAPONSLEVEL2"
        ZERGMISSILEWEAPONSLEVEL3 = "ZERGMISSILEWEAPONSLEVEL3"
        ZERGGROUNDARMORSLEVEL1 = "ZERGGROUNDARMORSLEVEL1"
        ZERGGROUNDARMORSLEVEL2 = "ZERGGROUNDARMORSLEVEL2"
        ZERGGROUNDARMORSLEVEL3 = "ZERGGROUNDARMORSLEVEL3"
        ZERGMELEEWEAPONSLEVEL1 = "ZERGMELEEWEAPONSLEVEL1"
        ZERGMELEEWEAPONSLEVEL2 = "ZERGMELEEWEAPONSLEVEL2"
        ZERGMELEEWEAPONSLEVEL3 = "ZERGMELEEWEAPONSLEVEL3"
        ZERGFLYERARMORSLEVEL1 = "ZERGFLYERARMORSLEVEL1"
        ZERGFLYERARMORSLEVEL2 = "ZERGFLYERARMORSLEVEL2"
        ZERGFLYERARMORSLEVEL3 = "ZERGFLYERARMORSLEVEL3"
        ZERGFLYERWEAPONSLEVEL1 = "ZERGFLYERWEAPONSLEVEL1"
        ZERGFLYERWEAPONSLEVEL2 = "ZERGFLYERWEAPONSLEVEL2"
        ZERGFLYERWEAPONSLEVEL3 = "ZERGFLYERWEAPONSLEVEL3"


class UpgradeCoordinationSystem:
    """
    ★ Upgrade Coordination System ★

    업그레이드 완료 타이밍에 맞춰 전략적 공격을 조율합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("UpgradeCoord")

        # ★ 체크 주기 ★
        self.last_check = 0
        self.check_interval = 22  # 약 1초마다

        # ★ 업그레이드 완료 추적 ★
        self.completed_upgrades: Dict[str, float] = {}
        self.attack_triggers: Dict[str, Dict] = {}  # {upgrade: trigger_info}

        # ★ 타이밍 공격 정의 ★
        self.timing_attacks = {
            # 공1업 완료 → 5:30 Roach 타이밍
            "ATTACK_1": {
                "trigger_upgrade": UpgradeId.ZERGMISSILEWEAPONSLEVEL1,
                "min_game_time": 270,  # 4:30 이후
                "max_game_time": 360,  # 6:00 이전
                "min_army_supply": 30,
                "attack_composition": {"roach": 0.70, "zergling": 0.30},
                "urgency": "HIGH",
                "description": "공1업 Roach 타이밍",
            },
            # 방1업 완료 → 전선 투입
            "DEFENSE_1": {
                "trigger_upgrade": UpgradeId.ZERGGROUNDARMORSLEVEL1,
                "min_game_time": 300,  # 5:00 이후
                "action": "PUSH_FRONT",
                "description": "방1업 전선 투입",
            },
            # 공2업 완료 → 6:30 Hydra 타이밍
            "ATTACK_2": {
                "trigger_upgrade": UpgradeId.ZERGMISSILEWEAPONSLEVEL2,
                "min_game_time": 360,  # 6:00 이후
                "max_game_time": 450,  # 7:30 이전
                "min_army_supply": 50,
                "attack_composition": {"hydralisk": 0.60, "roach": 0.40},
                "urgency": "CRITICAL",
                "description": "공2업 Hydra 타이밍",
            },
            # 공3방3 완료 → 최종 결전
            "FINAL_PUSH": {
                "trigger_upgrade": UpgradeId.ZERGMISSILEWEAPONSLEVEL3,
                "secondary_upgrade": UpgradeId.ZERGGROUNDARMORSLEVEL3,
                "min_game_time": 540,  # 9:00 이후
                "min_army_supply": 150,
                "attack_composition": {"hydralisk": 0.40, "roach": 0.30, "mutalisk": 0.20, "ultralisk": 0.10},
                "urgency": "ALL_IN",
                "description": "공3방3 최종 결전",
            },
            # 공중 업그레이드 → 뮤탈 전환
            "AIR_TIMING": {
                "trigger_upgrade": UpgradeId.ZERGFLYERWEAPONSLEVEL1,
                "min_game_time": 420,  # 7:00 이후
                "min_army_supply": 40,
                "attack_composition": {"mutalisk": 0.80, "corruptor": 0.20},
                "urgency": "HIGH",
                "description": "공중업 뮤탈 타이밍",
            },
        }

        # ★ 활성 타이밍 공격 ★
        self.active_timing_attack: Optional[str] = None

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration - self.last_check < self.check_interval:
                return

            self.last_check = iteration

            # ★ 1. 업그레이드 완료 확인 ★
            new_completions = await self._check_upgrade_completions()

            # ★ 2. 타이밍 공격 트리거 ★
            if new_completions:
                await self._trigger_timing_attacks(new_completions)

            # ★ 3. 활성 타이밍 공격 실행 ★
            if self.active_timing_attack:
                await self._execute_timing_attack()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[UPGRADE_COORD] Error: {e}")

    async def _check_upgrade_completions(self) -> List[str]:
        """
        업그레이드 완료 확인

        Returns:
            새로 완료된 업그레이드 이름 리스트
        """
        if not hasattr(self.bot, "state") or not hasattr(self.bot.state, "upgrades"):
            return []

        current_upgrades = self.bot.state.upgrades
        game_time = getattr(self.bot, "time", 0)

        new_completions = []

        for upgrade_id in current_upgrades:
            upgrade_name = getattr(upgrade_id, "name", str(upgrade_id))

            if upgrade_name not in self.completed_upgrades:
                self.completed_upgrades[upgrade_name] = game_time
                new_completions.append(upgrade_name)

                self.logger.info(
                    f"[{int(game_time)}s] ★ UPGRADE COMPLETE: {upgrade_name} ★"
                )

        return new_completions

    async def _trigger_timing_attacks(self, new_upgrades: List[str]):
        """
        업그레이드 완료에 따른 타이밍 공격 트리거

        Args:
            new_upgrades: 새로 완료된 업그레이드들
        """
        game_time = getattr(self.bot, "time", 0)

        for attack_id, attack_info in self.timing_attacks.items():
            # 이미 트리거되었으면 스킵
            if attack_id in self.attack_triggers:
                continue

            # 주 업그레이드 확인
            trigger_upgrade = attack_info.get("trigger_upgrade")
            if not trigger_upgrade:
                continue

            trigger_name = getattr(trigger_upgrade, "name", str(trigger_upgrade))
            if trigger_name not in new_upgrades:
                continue

            # 시간 조건 확인
            min_time = attack_info.get("min_game_time", 0)
            max_time = attack_info.get("max_game_time", 99999)

            if not (min_time <= game_time <= max_time):
                continue

            # 보조 업그레이드 확인 (있는 경우)
            secondary_upgrade = attack_info.get("secondary_upgrade")
            if secondary_upgrade:
                secondary_name = getattr(secondary_upgrade, "name", str(secondary_upgrade))
                if secondary_name not in self.completed_upgrades:
                    continue

            # 병력 확인
            min_supply = attack_info.get("min_army_supply", 0)
            current_army_supply = self._get_army_supply()

            if current_army_supply < min_supply:
                self.logger.info(
                    f"[{int(game_time)}s] ★ TIMING READY BUT WAITING: {attack_id} ★\n"
                    f"  Army: {current_army_supply}/{min_supply}"
                )
                # 병력 대기 중으로 표시
                self.attack_triggers[attack_id] = {
                    "triggered": False,
                    "waiting_for_army": True,
                }
                continue

            # ★ 타이밍 공격 발동! ★
            self.active_timing_attack = attack_id
            self.attack_triggers[attack_id] = {
                "triggered": True,
                "trigger_time": game_time,
                "waiting_for_army": False,
            }

            self.logger.info(
                f"[{int(game_time)}s] ★★★ TIMING ATTACK: {attack_info['description']} ★★★\n"
                f"  Army Supply: {current_army_supply}\n"
                f"  Urgency: {attack_info.get('urgency', 'NORMAL')}"
            )

            # Blackboard에 타이밍 공격 등록
            await self._register_timing_attack(attack_id, attack_info)

    async def _register_timing_attack(self, attack_id: str, attack_info: Dict):
        """
        Blackboard에 타이밍 공격 등록
        """
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard:
            return

        blackboard.set("timing_attack_active", True)
        blackboard.set("timing_attack_id", attack_id)
        blackboard.set("timing_attack_urgency", attack_info.get("urgency", "NORMAL"))
        blackboard.set("timing_attack_composition", attack_info.get("attack_composition", {}))

        # CombatManager에 강제 공격 명령
        if hasattr(self.bot, "combat") and self.bot.combat:
            if hasattr(self.bot.combat, "_force_attack"):
                self.bot.combat._force_attack = True

    async def _execute_timing_attack(self):
        """
        타이밍 공격 실행 중 모니터링
        """
        if not self.active_timing_attack:
            return

        attack_info = self.timing_attacks[self.active_timing_attack]
        trigger_info = self.attack_triggers[self.active_timing_attack]

        game_time = getattr(self.bot, "time", 0)
        elapsed = game_time - trigger_info.get("trigger_time", game_time)

        # ★ 병력 대기 중 확인 ★
        if trigger_info.get("waiting_for_army"):
            min_supply = attack_info.get("min_army_supply", 0)
            current_supply = self._get_army_supply()

            if current_supply >= min_supply:
                # 병력 준비 완료!
                trigger_info["waiting_for_army"] = False
                trigger_info["triggered"] = True
                trigger_info["trigger_time"] = game_time

                self.logger.info(
                    f"[{int(game_time)}s] ★ TIMING ARMY READY: {self.active_timing_attack} ★\n"
                    f"  Army Supply: {current_supply}/{min_supply}"
                )

                await self._register_timing_attack(self.active_timing_attack, attack_info)

        # ★ 타이밍 공격 지속 시간 (2분) ★
        if elapsed > 120:
            self.logger.info(
                f"[{int(game_time)}s] ★ TIMING COMPLETE: {self.active_timing_attack} ★"
            )

            # 타이밍 종료
            self.active_timing_attack = None

            # Blackboard 업데이트
            blackboard = getattr(self.bot, "blackboard", None)
            if blackboard:
                blackboard.set("timing_attack_active", False)

    def _get_army_supply(self) -> int:
        """
        현재 군대 supply 계산

        Returns:
            군대 supply
        """
        if not hasattr(self.bot, "units"):
            return 0

        army_types = {
            "ZERGLING", "BANELING", "ROACH", "RAVAGER",
            "HYDRALISK", "LURKER", "LURKERMP", "MUTALISK",
            "CORRUPTOR", "BROODLORD", "ULTRALISK", "VIPER",
            "INFESTOR", "SWARMHOST"
        }

        total_supply = 0

        for unit in self.bot.units:
            type_name = getattr(unit.type_id, "name", "").upper()
            if type_name in army_types:
                supply_cost = getattr(unit, "supply_cost", 0)
                total_supply += supply_cost

        return total_supply

    def get_next_timing_attack(self) -> Optional[Tuple[str, Dict]]:
        """
        다음 타이밍 공격 정보 반환

        Returns:
            (attack_id, attack_info) or None
        """
        game_time = getattr(self.bot, "time", 0)

        for attack_id, attack_info in self.timing_attacks.items():
            # 이미 트리거된 공격 제외
            if attack_id in self.attack_triggers:
                continue

            # 시간 조건
            min_time = attack_info.get("min_game_time", 0)
            if game_time < min_time:
                return (attack_id, attack_info)

        return None

    def get_statistics(self) -> Dict:
        """통계 반환"""
        return {
            "completed_upgrades": len(self.completed_upgrades),
            "triggered_attacks": len(self.attack_triggers),
            "active_timing": self.active_timing_attack,
        }
