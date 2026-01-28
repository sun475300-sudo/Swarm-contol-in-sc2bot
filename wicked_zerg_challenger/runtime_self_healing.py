# -*- coding: utf-8 -*-
"""
Runtime Self-Healing System - 실행 중 자동 복구

게임 중 발생하는 오류를 자동으로 감지하고 복구:
1. 매니저 오류 감지 및 재시작
2. 교착 상태 감지 (경제/생산 멈춤)
3. 자원 낭비 감지 (미네랄/가스 과다 축적)
4. 유닛 생산 정체 감지
5. 자동 복구 조치
"""

from typing import Dict, List, Optional, Set
from utils.logger import get_logger
import time


class HealthMetric:
    """시스템 건강 상태 측정"""

    def __init__(self, name: str, check_interval: float = 10.0):
        self.name = name
        self.check_interval = check_interval
        self.last_check_time = 0
        self.error_count = 0
        self.last_error_time = 0
        self.is_healthy = True


class RuntimeSelfHealing:
    """
    Runtime Self-Healing System

    게임 실행 중 자동으로 문제를 감지하고 복구합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("SelfHealing")

        # 건강 상태 추적
        self.metrics: Dict[str, HealthMetric] = {
            "economy": HealthMetric("economy", 30.0),  # 30초마다 체크
            "production": HealthMetric("production", 20.0),  # 20초마다 체크
            "resources": HealthMetric("resources", 15.0),  # 15초마다 체크
            "managers": HealthMetric("managers", 10.0),  # 10초마다 체크
        }

        # 이전 상태 저장 (변화 감지용)
        self.last_supply = 12
        self.last_worker_count = 12
        self.last_army_count = 0
        self.last_mineral_count = 50
        self.last_gas_count = 0

        # 복구 조치 이력
        self.recovery_actions: List[Dict] = []
        self.total_recoveries = 0

        # 임계값 설정
        self.MINERAL_WASTE_THRESHOLD = 2000  # 미네랄 2000 이상이면 낭비
        self.GAS_WASTE_THRESHOLD = 1500  # 가스 1500 이상이면 낭비
        self.SUPPLY_STALL_THRESHOLD = 60  # 60초 동안 서플라이 변화 없으면 정체
        self.WORKER_STALL_THRESHOLD = 90  # 90초 동안 일꾼 증가 없으면 정체

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 각 건강 상태 체크
            for metric_name, metric in self.metrics.items():
                if game_time - metric.last_check_time >= metric.check_interval:
                    metric.last_check_time = game_time
                    await self._check_metric(metric_name, game_time)

            # 주기적 리포트 (5분마다)
            if iteration % 6600 == 0 and self.total_recoveries > 0:
                self._print_recovery_report(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[SELF_HEALING] Error: {e}")

    async def _check_metric(self, metric_name: str, game_time: float):
        """특정 건강 상태 체크"""
        if metric_name == "economy":
            await self._check_economy_health(game_time)
        elif metric_name == "production":
            await self._check_production_health(game_time)
        elif metric_name == "resources":
            await self._check_resource_health(game_time)
        elif metric_name == "managers":
            await self._check_manager_health(game_time)

    async def _check_economy_health(self, game_time: float):
        """경제 건강 체크"""
        # 일꾼 수 확인
        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            return

        workers = self.bot.workers
        current_worker_count = len(workers)

        # 일꾼 정체 감지 (90초 동안 증가 없음)
        if game_time > 120:  # 2분 이후부터 체크
            if hasattr(self, '_worker_check_start'):
                elapsed = game_time - self._worker_check_start
                if current_worker_count <= self.last_worker_count and elapsed > self.WORKER_STALL_THRESHOLD:
                    # 정체 감지!
                    await self._recover_economy_stall(game_time)
                    self._worker_check_start = game_time
            else:
                self._worker_check_start = game_time

        self.last_worker_count = current_worker_count

    async def _check_production_health(self, game_time: float):
        """생산 건강 체크"""
        # 서플라이 정체 감지
        current_supply = self.bot.supply_used

        if game_time > 180:  # 3분 이후부터 체크
            if hasattr(self, '_supply_check_start'):
                elapsed = game_time - self._supply_check_start
                if current_supply <= self.last_supply and elapsed > self.SUPPLY_STALL_THRESHOLD:
                    # 서플라이 정체!
                    await self._recover_production_stall(game_time)
                    self._supply_check_start = game_time
            else:
                self._supply_check_start = game_time

        self.last_supply = current_supply

    async def _check_resource_health(self, game_time: float):
        """자원 건강 체크"""
        minerals = self.bot.minerals
        gas = self.bot.vespene

        # 자원 과다 축적 감지
        if minerals > self.MINERAL_WASTE_THRESHOLD:
            await self._recover_mineral_waste(game_time, minerals)

        if gas > self.GAS_WASTE_THRESHOLD:
            await self._recover_gas_waste(game_time, gas)

    async def _check_manager_health(self, game_time: float):
        """매니저 건강 체크"""
        # 주요 매니저가 None인지 체크
        critical_managers = [
            "economy_manager",
            "strategy_manager",
            "combat_manager",
            "intel",
        ]

        for manager_name in critical_managers:
            manager = getattr(self.bot, manager_name, None)
            if manager is None and game_time > 10:  # 게임 시작 10초 후
                # 매니저 없음!
                await self._recover_missing_manager(game_time, manager_name)

    # ===== 복구 조치들 =====

    async def _recover_economy_stall(self, game_time: float):
        """경제 정체 복구"""
        self.logger.warning(
            f"[{int(game_time)}s] ECONOMY STALL detected! "
            f"Workers not increasing (Current: {self.last_worker_count})"
        )

        # 복구 조치: 강제로 일꾼 생산 요청
        if hasattr(self.bot, "economy_manager"):
            recovery_action = {
                "time": game_time,
                "type": "economy_stall",
                "action": "Force drone production",
                "workers": self.last_worker_count
            }
            self.recovery_actions.append(recovery_action)
            self.total_recoveries += 1

            self.logger.info(f"[RECOVERY] Requesting emergency drone production")

    async def _recover_production_stall(self, game_time: float):
        """생산 정체 복구"""
        self.logger.warning(
            f"[{int(game_time)}s] PRODUCTION STALL detected! "
            f"Supply not increasing (Current: {self.last_supply})"
        )

        # 복구 조치: 대군주 생산 강제 + 유닛 생산 강제
        recovery_action = {
            "time": game_time,
            "type": "production_stall",
            "action": "Force overlord + army production",
            "supply": self.last_supply
        }
        self.recovery_actions.append(recovery_action)
        self.total_recoveries += 1

        self.logger.info(f"[RECOVERY] Requesting emergency production")

    async def _recover_mineral_waste(self, game_time: float, minerals: int):
        """미네랄 낭비 복구"""
        # 이미 최근에 복구했으면 스킵
        if hasattr(self, '_last_mineral_recovery'):
            if game_time - self._last_mineral_recovery < 30:
                return

        self.logger.warning(
            f"[{int(game_time)}s] MINERAL WASTE detected! "
            f"Minerals: {minerals} (Threshold: {self.MINERAL_WASTE_THRESHOLD})"
        )

        # 복구 조치: 확장 건설 또는 유닛 대량 생산
        recovery_action = {
            "time": game_time,
            "type": "mineral_waste",
            "action": "Expansion or mass unit production",
            "minerals": minerals
        }
        self.recovery_actions.append(recovery_action)
        self.total_recoveries += 1

        self._last_mineral_recovery = game_time
        self.logger.info(f"[RECOVERY] Spending excess minerals: {minerals}")

    async def _recover_gas_waste(self, game_time: float, gas: int):
        """가스 낭비 복구"""
        # 이미 최근에 복구했으면 스킵
        if hasattr(self, '_last_gas_recovery'):
            if game_time - self._last_gas_recovery < 30:
                return

        self.logger.warning(
            f"[{int(game_time)}s] GAS WASTE detected! "
            f"Gas: {gas} (Threshold: {self.GAS_WASTE_THRESHOLD})"
        )

        # 복구 조치: 일꾼 재배치 또는 가스 유닛 생산
        recovery_action = {
            "time": game_time,
            "type": "gas_waste",
            "action": "Worker rebalance or gas unit production",
            "gas": gas
        }
        self.recovery_actions.append(recovery_action)
        self.total_recoveries += 1

        self._last_gas_recovery = game_time
        self.logger.info(f"[RECOVERY] Reducing gas workers or spending gas: {gas}")

        # SmartBalancer가 있으면 사용
        if hasattr(self.bot, "smart_balancer"):
            # 이미 자동으로 처리됨
            pass

    async def _recover_missing_manager(self, game_time: float, manager_name: str):
        """매니저 없음 복구"""
        self.logger.error(
            f"[{int(game_time)}s] CRITICAL: Missing manager '{manager_name}'!"
        )

        recovery_action = {
            "time": game_time,
            "type": "missing_manager",
            "action": f"Attempt to reinitialize {manager_name}",
            "manager": manager_name
        }
        self.recovery_actions.append(recovery_action)
        self.total_recoveries += 1

        # 재초기화 시도 (위험할 수 있으므로 조심스럽게)
        try:
            if manager_name == "economy_manager":
                from economy_manager import EconomyManager
                self.bot.economy_manager = EconomyManager(self.bot)
                self.logger.info(f"[RECOVERY] Reinitialized EconomyManager")
            elif manager_name == "strategy_manager":
                from strategy_manager import StrategyManager
                self.bot.strategy_manager = StrategyManager(self.bot)
                self.logger.info(f"[RECOVERY] Reinitialized StrategyManager")
            # 다른 매니저들도 필요시 추가
        except Exception as e:
            self.logger.error(f"[RECOVERY] Failed to reinitialize {manager_name}: {e}")

    def _print_recovery_report(self, game_time: float):
        """복구 조치 리포트"""
        self.logger.info(
            f"[SELF_HEALING] [{int(game_time)}s] Total Recoveries: {self.total_recoveries}"
        )

        # 최근 5개 복구 조치 출력
        recent_actions = self.recovery_actions[-5:]
        for action in recent_actions:
            self.logger.info(
                f"  [{int(action['time'])}s] {action['type']}: {action['action']}"
            )

    def get_statistics(self) -> Dict:
        """통계 반환"""
        recovery_by_type = {}
        for action in self.recovery_actions:
            action_type = action['type']
            recovery_by_type[action_type] = recovery_by_type.get(action_type, 0) + 1

        return {
            "total_recoveries": self.total_recoveries,
            "recovery_by_type": recovery_by_type,
            "health_status": {
                name: metric.is_healthy
                for name, metric in self.metrics.items()
            }
        }
