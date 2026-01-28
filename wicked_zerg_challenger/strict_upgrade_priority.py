# -*- coding: utf-8 -*-
"""
Strict Upgrade Priority System - 엄격한 업그레이드 우선순위

가스 100 모이면 발업(Metabolic Boost)부터 무조건 찍고
다른 가스 지출(건물, 유닛) 차단

문제: 가스를 건물 짓는 데 다 써서 발업이 몇 분씩 지연됨
해결: 가스 예약 시스템으로 발업 우선순위 강제
"""

from typing import Optional, Dict, Set
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from utils.logger import get_logger


class StrictUpgradePriority:
    """
    엄격한 업그레이드 우선순위 시스템

    기능:
    1. 핵심 업그레이드 우선순위 정의
    2. 가스 예약 시스템 (업그레이드 완료 전까지 가스 차단)
    3. 다른 시스템의 가스 지출 제한
    4. 업그레이드 자동 시작
    """

    # 우선순위별 업그레이드 정의
    CRITICAL_UPGRADES = {
        # Tier 1: 무조건 최우선
        UpgradeId.ZERGLINGMOVEMENTSPEED: {  # 발업
            "cost_gas": 100,
            "cost_minerals": 100,
            "required_building": UnitTypeId.SPAWNINGPOOL,
            "priority": 100,
            "name": "Metabolic Boost (발업)"
        },
    }

    HIGH_PRIORITY_UPGRADES = {
        # Tier 2: 중요하지만 발업 다음
        UpgradeId.GLIALRECONSTITUTION: {  # 바퀴 체력 재생
            "cost_gas": 100,
            "cost_minerals": 100,
            "required_building": UnitTypeId.ROACHWARREN,
            "priority": 80,
            "name": "Glial Reconstitution (바퀴 회복)"
        },
        UpgradeId.EVOLVEGROOVEDSPINES: {  # 히드라 사거리
            "cost_gas": 100,
            "cost_minerals": 100,
            "required_building": UnitTypeId.HYDRALISKDEN,
            "priority": 75,
            "name": "Grooved Spines (히드라 사거리)"
        },
        UpgradeId.EVOLVEMUSCULARAUGMENTS: {  # 히드라 이속
            "cost_gas": 100,
            "cost_minerals": 100,
            "required_building": UnitTypeId.HYDRALISKDEN,
            "priority": 70,
            "name": "Muscular Augments (히드라 이속)"
        },
    }

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("UpgradePriority")

        # 가스 예약 시스템
        self.reserved_gas = 0
        self.reserved_for_upgrade: Optional[UpgradeId] = None

        # 업그레이드 진행 상태
        self.upgrade_in_progress: Set[UpgradeId] = set()
        self.completed_upgrades: Set[UpgradeId] = set()

        # 차단 시스템
        self.gas_spending_blocked = False

    async def on_step(self) -> None:
        """매 프레임 실행"""
        # 1. 완료된 업그레이드 추적
        self._update_completed_upgrades()

        # 2. 핵심 업그레이드 확인 및 예약
        await self._check_critical_upgrades()

        # 3. 고우선순위 업그레이드 확인
        await self._check_high_priority_upgrades()

    def _update_completed_upgrades(self) -> None:
        """완료된 업그레이드 추적"""
        # 발업 확인
        if UpgradeId.ZERGLINGMOVEMENTSPEED in self.bot.state.upgrades:
            if UpgradeId.ZERGLINGMOVEMENTSPEED not in self.completed_upgrades:
                self.completed_upgrades.add(UpgradeId.ZERGLINGMOVEMENTSPEED)
                self.logger.info("[UPGRADE] Metabolic Boost (발업) 완료!")
                self._release_gas_reservation()

        # 다른 업그레이드들도 확인
        for upgrade_id in self.HIGH_PRIORITY_UPGRADES.keys():
            if upgrade_id in self.bot.state.upgrades:
                if upgrade_id not in self.completed_upgrades:
                    self.completed_upgrades.add(upgrade_id)
                    upgrade_name = self.HIGH_PRIORITY_UPGRADES[upgrade_id]["name"]
                    self.logger.info(f"[UPGRADE] {upgrade_name} 완료!")

    async def _check_critical_upgrades(self) -> None:
        """핵심 업그레이드 (발업) 확인 및 시작"""
        # 발업 이미 완료 또는 진행 중이면 스킵
        if UpgradeId.ZERGLINGMOVEMENTSPEED in self.completed_upgrades:
            return
        if UpgradeId.ZERGLINGMOVEMENTSPEED in self.upgrade_in_progress:
            return

        upgrade_info = self.CRITICAL_UPGRADES[UpgradeId.ZERGLINGMOVEMENTSPEED]

        # 산란못 확인
        spawning_pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not spawning_pools:
            return

        # 가스 100 이상이면 예약
        if self.bot.vespene >= upgrade_info["cost_gas"]:
            if self.reserved_for_upgrade != UpgradeId.ZERGLINGMOVEMENTSPEED:
                self._reserve_gas_for_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED)

        # 자원 확인 및 업그레이드 시작
        if (self.bot.minerals >= upgrade_info["cost_minerals"]
            and self.bot.vespene >= upgrade_info["cost_gas"]):

            pool = spawning_pools.idle.first if spawning_pools.idle else None
            if pool:
                # 업그레이드 시작
                if pool.research(UpgradeId.ZERGLINGMOVEMENTSPEED):
                    self.upgrade_in_progress.add(UpgradeId.ZERGLINGMOVEMENTSPEED)
                    self.logger.info(f"[UPGRADE] Metabolic Boost (발업) 시작! (게임 시간: {int(self.bot.time)}초)")
                    self._release_gas_reservation()

    async def _check_high_priority_upgrades(self) -> None:
        """고우선순위 업그레이드 확인"""
        # 발업이 완료되지 않았으면 다른 업그레이드 차단
        if UpgradeId.ZERGLINGMOVEMENTSPEED not in self.completed_upgrades:
            return

        # 각 업그레이드 확인
        for upgrade_id, upgrade_info in self.HIGH_PRIORITY_UPGRADES.items():
            # 이미 완료 또는 진행 중이면 스킵
            if upgrade_id in self.completed_upgrades:
                continue
            if upgrade_id in self.upgrade_in_progress:
                continue

            # 필요 건물 확인
            required_building = upgrade_info["required_building"]
            buildings = self.bot.structures(required_building).ready
            if not buildings:
                continue

            # 자원 확인 및 업그레이드 시작
            if (self.bot.minerals >= upgrade_info["cost_minerals"]
                and self.bot.vespene >= upgrade_info["cost_gas"]):

                building = buildings.idle.first if buildings.idle else None
                if building:
                    if building.research(upgrade_id):
                        self.upgrade_in_progress.add(upgrade_id)
                        self.logger.info(f"[UPGRADE] {upgrade_info['name']} 시작!")

    def _reserve_gas_for_upgrade(self, upgrade_id: UpgradeId) -> None:
        """업그레이드를 위한 가스 예약"""
        if upgrade_id == UpgradeId.ZERGLINGMOVEMENTSPEED:
            upgrade_info = self.CRITICAL_UPGRADES[upgrade_id]
            self.reserved_gas = upgrade_info["cost_gas"]
            self.reserved_for_upgrade = upgrade_id
            self.gas_spending_blocked = True
            self.logger.info(f"[UPGRADE] 가스 {self.reserved_gas} 예약: {upgrade_info['name']}")

    def _release_gas_reservation(self) -> None:
        """가스 예약 해제"""
        if self.reserved_for_upgrade:
            upgrade_name = self.CRITICAL_UPGRADES.get(
                self.reserved_for_upgrade, {}
            ).get("name", "Unknown")
            self.logger.info(f"[UPGRADE] 가스 예약 해제: {upgrade_name}")

        self.reserved_gas = 0
        self.reserved_for_upgrade = None
        self.gas_spending_blocked = False

    def can_spend_gas(self, amount: int, requester: str = "Unknown") -> bool:
        """
        가스 지출 가능 여부 확인

        Args:
            amount: 필요한 가스량
            requester: 요청자 이름 (디버깅용)

        Returns:
            True if gas spending allowed, False if blocked
        """
        # 가스 지출이 차단되어 있으면
        if self.gas_spending_blocked:
            available_gas = self.bot.vespene - self.reserved_gas
            if available_gas < amount:
                if self.reserved_for_upgrade:
                    upgrade_name = self.CRITICAL_UPGRADES.get(
                        self.reserved_for_upgrade, {}
                    ).get("name", "Unknown")
                    self.logger.debug(
                        f"[UPGRADE] 가스 지출 차단: {requester} (예약: {upgrade_name})"
                    )
                return False

        return True

    def get_available_gas(self) -> int:
        """사용 가능한 가스량 반환"""
        if self.gas_spending_blocked:
            return max(0, self.bot.vespene - self.reserved_gas)
        return self.bot.vespene

    def is_metabolic_boost_completed(self) -> bool:
        """발업 완료 여부"""
        return UpgradeId.ZERGLINGMOVEMENTSPEED in self.completed_upgrades
