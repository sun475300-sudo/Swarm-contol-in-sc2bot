# -*- coding: utf-8 -*-
"""
Build Order System - 빌드 오더 최적화 시스템

목적: 안정적이고 최적화된 빌드 오더 자동 실행
- 12풀 14헷 14가스 표준 빌드
- 타이밍 정확도 향상
- 승률 기반 자동 조정
"""

from typing import Optional, List, Dict, Tuple
from enum import Enum
try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        DRONE = "DRONE"
        OVERLORD = "OVERLORD"
        SPAWNINGPOOL = "SPAWNINGPOOL"
        HATCHERY = "HATCHERY"
        EXTRACTOR = "EXTRACTOR"
        ZERGLING = "ZERGLING"
        QUEEN = "QUEEN"
    class AbilityId:
        pass
    class Point2:
        pass


class BuildOrderType(Enum):
    """빌드 오더 종류"""
    STANDARD_12POOL = "12pool_14hatch_14gas"  # 표준 12풀
    SAFE_14POOL = "14pool_16hatch_15gas"      # 안전한 14풀
    AGGRESSIVE_10POOL = "10pool_gas_ling"     # 공격적 10풀
    ECONOMY_15HATCH = "15hatch_16pool_17gas"  # 경제 우선 15헷


class BuildOrderStep:
    """빌드 오더 단계"""
    def __init__(self, supply: int, action: str, unit_type: UnitTypeId, description: str = ""):
        self.supply = supply  # 이 보급에서 실행
        self.action = action  # "build", "train", "expand"
        self.unit_type = unit_type
        self.description = description
        self.completed = False

    def __repr__(self):
        return f"BuildOrderStep({self.supply} supply: {self.action} {self.unit_type})"


class BuildOrderSystem:
    """
    빌드 오더 시스템

    핵심 기능:
    1. 정확한 타이밍으로 빌드 오더 실행
    2. 승률 기반 빌드 오더 자동 선택
    3. 실시간 진행도 추적
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.enabled = True
        self.build_order_active = True

        # 현재 빌드 오더
        self.current_build_order: BuildOrderType = BuildOrderType.STANDARD_12POOL
        self.build_steps: List[BuildOrderStep] = []
        self.current_step_index = 0

        # 타이밍 추적
        self.step_timings: Dict[int, float] = {}  # supply -> game_time
        self.missed_timings: List[str] = []

        # 성능 통계
        self.build_order_stats = {
            BuildOrderType.STANDARD_12POOL: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.SAFE_14POOL: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.AGGRESSIVE_10POOL: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.ECONOMY_15HATCH: {"games": 0, "wins": 0, "avg_timing": 0.0},
        }

        # 빌드 오더 종료 시간 (이 시간 이후 비활성화)
        self.build_order_end_time = 180.0  # 3분

        # 초기화
        self._setup_build_order()

    def _setup_build_order(self) -> None:
        """현재 빌드 오더 설정"""
        if self.current_build_order == BuildOrderType.STANDARD_12POOL:
            self.build_steps = self._get_standard_12pool_build()
        elif self.current_build_order == BuildOrderType.SAFE_14POOL:
            self.build_steps = self._get_safe_14pool_build()
        elif self.current_build_order == BuildOrderType.AGGRESSIVE_10POOL:
            self.build_steps = self._get_aggressive_10pool_build()
        elif self.current_build_order == BuildOrderType.ECONOMY_15HATCH:
            self.build_steps = self._get_economy_15hatch_build()

        self.current_step_index = 0
        print(f"[BUILD_ORDER] 빌드 오더 설정: {self.current_build_order.value}")
        print(f"[BUILD_ORDER] 총 {len(self.build_steps)}개 단계")

    def _get_standard_12pool_build(self) -> List[BuildOrderStep]:
        """표준 12풀 14헷 14가스 빌드"""
        return [
            # 초반 드론 생산 (자동)
            BuildOrderStep(12, "build", UnitTypeId.SPAWNINGPOOL, "12풀 - Spawning Pool 건설"),
            BuildOrderStep(13, "train", UnitTypeId.OVERLORD, "13오버로드"),
            BuildOrderStep(14, "expand", UnitTypeId.HATCHERY, "14헷 - 자연 확장"),
            BuildOrderStep(14, "build", UnitTypeId.EXTRACTOR, "14가스 - Extractor 건설"),
            BuildOrderStep(16, "train", UnitTypeId.QUEEN, "16퀸 - 첫 Queen"),
            BuildOrderStep(16, "train", UnitTypeId.ZERGLING, "16저글링 - 첫 Zergling (2마리)"),
            BuildOrderStep(18, "train", UnitTypeId.OVERLORD, "18오버로드"),
            BuildOrderStep(20, "train", UnitTypeId.QUEEN, "20퀸 - 자연 확장 Queen"),
            BuildOrderStep(22, "train", UnitTypeId.OVERLORD, "22오버로드"),
            # 이후 자동 생산
        ]

    def _get_safe_14pool_build(self) -> List[BuildOrderStep]:
        """안전한 14풀 빌드 (방어 중시)"""
        return [
            BuildOrderStep(13, "train", UnitTypeId.OVERLORD, "13오버로드"),
            BuildOrderStep(14, "build", UnitTypeId.SPAWNINGPOOL, "14풀 - Spawning Pool"),
            BuildOrderStep(16, "expand", UnitTypeId.HATCHERY, "16헷 - 자연 확장"),
            BuildOrderStep(15, "build", UnitTypeId.EXTRACTOR, "15가스"),
            BuildOrderStep(17, "train", UnitTypeId.QUEEN, "17퀸"),
            BuildOrderStep(18, "train", UnitTypeId.ZERGLING, "18저글링"),
            BuildOrderStep(20, "train", UnitTypeId.OVERLORD, "20오버로드"),
        ]

    def _get_aggressive_10pool_build(self) -> List[BuildOrderStep]:
        """공격적 10풀 빌드 (초반 압박)"""
        return [
            BuildOrderStep(10, "build", UnitTypeId.SPAWNINGPOOL, "10풀 - Spawning Pool"),
            BuildOrderStep(10, "build", UnitTypeId.EXTRACTOR, "10가스 - 조기 가스"),
            BuildOrderStep(13, "train", UnitTypeId.OVERLORD, "13오버로드"),
            BuildOrderStep(14, "train", UnitTypeId.QUEEN, "14퀸"),
            BuildOrderStep(14, "train", UnitTypeId.ZERGLING, "14저글링 - 공격 유닛"),
            BuildOrderStep(16, "train", UnitTypeId.ZERGLING, "16저글링"),
            BuildOrderStep(18, "expand", UnitTypeId.HATCHERY, "18헷 - 늦은 확장"),
        ]

    def _get_economy_15hatch_build(self) -> List[BuildOrderStep]:
        """경제 우선 15헷 빌드"""
        return [
            BuildOrderStep(13, "train", UnitTypeId.OVERLORD, "13오버로드"),
            BuildOrderStep(15, "expand", UnitTypeId.HATCHERY, "15헷 - 조기 확장"),
            BuildOrderStep(16, "build", UnitTypeId.SPAWNINGPOOL, "16풀"),
            BuildOrderStep(17, "build", UnitTypeId.EXTRACTOR, "17가스"),
            BuildOrderStep(18, "train", UnitTypeId.QUEEN, "18퀸"),
            BuildOrderStep(20, "train", UnitTypeId.OVERLORD, "20오버로드"),
        ]

    async def execute(self, iteration: int) -> None:
        """
        매 프레임 빌드 오더 실행
        """
        # 3분 이후 비활성화
        if self.bot.time > self.build_order_end_time:
            if self.build_order_active:
                self.build_order_active = False
                print(f"[BUILD_ORDER] 빌드 오더 단계 완료 (게임 시간: {int(self.bot.time)}초)")
            return

        if not self.enabled or not self.build_order_active:
            return

        # 현재 보급 확인
        current_supply = int(self.bot.supply_used)

        # 다음 스텝 확인
        if self.current_step_index >= len(self.build_steps):
            return

        current_step = self.build_steps[self.current_step_index]

        # 보급 도달 확인
        if current_supply >= current_step.supply:
            # 스텝 실행
            success = await self._execute_step(current_step)

            if success:
                # 타이밍 기록
                self.step_timings[current_step.supply] = self.bot.time
                print(f"[BUILD_ORDER] ✓ {current_step.supply}보급: {current_step.description} (타이밍: {int(self.bot.time)}초)")

                # 다음 스텝으로
                current_step.completed = True
                self.current_step_index += 1

    async def _execute_step(self, step: BuildOrderStep) -> bool:
        """빌드 오더 단계 실행"""
        try:
            if step.action == "build":
                return await self._build_structure(step.unit_type)
            elif step.action == "train":
                return await self._train_unit(step.unit_type)
            elif step.action == "expand":
                return await self._expand(step.unit_type)
            return False
        except Exception as e:
            print(f"[BUILD_ORDER] 단계 실행 실패: {e}")
            return False

    async def _build_structure(self, structure_type: UnitTypeId) -> bool:
        """건물 건설"""
        # 이미 건설 중이거나 있으면 스킵
        if self.bot.structures(structure_type).exists:
            return True
        if self.bot.already_pending(structure_type) > 0:
            return True

        # 자원 확인
        if not self.bot.can_afford(structure_type):
            return False

        # 일꾼 확인
        if not self.bot.workers:
            return False

        # Spawning Pool 건설
        if structure_type == UnitTypeId.SPAWNINGPOOL:
            worker = self.bot.workers.random
            main_base = self.bot.townhalls.first
            location = await self.bot.find_placement(
                UnitTypeId.SPAWNINGPOOL,
                main_base.position.towards(self.bot.game_info.map_center, 5),
                max_distance=15,
                placement_step=2
            )
            if location:
                worker.build(UnitTypeId.SPAWNINGPOOL, location)
                return True

        # Extractor 건설
        elif structure_type == UnitTypeId.EXTRACTOR:
            # 가스 간헐천 확인
            if self.bot.townhalls:
                main_base = self.bot.townhalls.first
                geysers = self.bot.vespene_geyser.closer_than(10, main_base)

                # 빈 간헐천 찾기
                for geyser in geysers:
                    # 이미 Extractor가 있는지 확인
                    if not self.bot.structures(UnitTypeId.EXTRACTOR).closer_than(1, geyser):
                        worker = self.bot.workers.closest_to(geyser)
                        if worker:
                            worker.build_gas(geyser)
                            return True

        return False

    async def _train_unit(self, unit_type: UnitTypeId) -> bool:
        """유닛 생산"""
        # 자원 확인
        if not self.bot.can_afford(unit_type):
            return False

        # Overlord 생산
        if unit_type == UnitTypeId.OVERLORD:
            if self.bot.larva:
                larva = self.bot.larva.first
                larva.train(UnitTypeId.OVERLORD)
                return True

        # Queen 생산
        elif unit_type == UnitTypeId.QUEEN:
            # Spawning Pool 확인
            if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
                return False

            # 대기 중인 Hatchery 찾기
            for hatchery in self.bot.townhalls.ready.idle:
                if self.bot.can_afford(UnitTypeId.QUEEN):
                    hatchery.train(UnitTypeId.QUEEN)
                    return True

        # Zergling 생산
        elif unit_type == UnitTypeId.ZERGLING:
            # Spawning Pool 확인
            if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
                return False

            if self.bot.larva:
                larva = self.bot.larva.first
                larva.train(UnitTypeId.ZERGLING)
                return True

        # Drone 생산 (기본)
        elif unit_type == UnitTypeId.DRONE:
            if self.bot.larva:
                larva = self.bot.larva.first
                larva.train(UnitTypeId.DRONE)
                return True

        return False

    async def _expand(self, structure_type: UnitTypeId) -> bool:
        """확장 기지 건설"""
        # 이미 확장했으면 스킵
        if self.bot.townhalls.amount >= 2:
            return True
        if self.bot.already_pending(UnitTypeId.HATCHERY) > 0:
            return True

        # 자원 확인
        if not self.bot.can_afford(UnitTypeId.HATCHERY):
            return False

        # 확장 위치 찾기
        location = await self.bot.get_next_expansion()
        if location:
            worker = self.bot.workers.random
            if worker:
                worker.build(UnitTypeId.HATCHERY, location)
                return True

        return False

    def select_build_order_by_win_rate(self) -> BuildOrderType:
        """승률 기반 빌드 오더 자동 선택"""
        # 승률 계산
        win_rates = {}
        for build_type, stats in self.build_order_stats.items():
            if stats["games"] > 0:
                win_rates[build_type] = stats["wins"] / stats["games"]
            else:
                win_rates[build_type] = 0.0

        # 승률이 가장 높은 빌드 선택 (최소 5게임 이상)
        best_build = BuildOrderType.STANDARD_12POOL
        best_win_rate = 0.0

        for build_type, win_rate in win_rates.items():
            if self.build_order_stats[build_type]["games"] >= 5 and win_rate > best_win_rate:
                best_build = build_type
                best_win_rate = win_rate

        return best_build

    def record_game_result(self, build_order: BuildOrderType, won: bool) -> None:
        """게임 결과 기록"""
        if build_order in self.build_order_stats:
            self.build_order_stats[build_order]["games"] += 1
            if won:
                self.build_order_stats[build_order]["wins"] += 1

    def get_progress(self) -> str:
        """빌드 오더 진행도 반환"""
        if not self.build_order_active:
            return "빌드 오더 완료"

        completed = sum(1 for step in self.build_steps if step.completed)
        total = len(self.build_steps)

        if total > 0:
            progress = f"{completed}/{total} ({int(completed/total*100)}%)"
        else:
            progress = "0/0"

        # 현재 목표
        if self.current_step_index < len(self.build_steps):
            next_step = self.build_steps[self.current_step_index]
            target = f"다음: {next_step.supply}보급 {next_step.description}"
        else:
            target = "모든 단계 완료"

        return f"{progress} | {target}"

    def get_stats_summary(self) -> str:
        """빌드 오더 통계 요약"""
        lines = []
        lines.append("\n[BUILD_ORDER] === 빌드 오더 통계 ===")

        for build_type, stats in self.build_order_stats.items():
            games = stats["games"]
            wins = stats["wins"]
            win_rate = (wins / games * 100) if games > 0 else 0.0

            lines.append(f"  {build_type.value}: {wins}/{games}승 ({win_rate:.1f}%)")

        lines.append("=" * 40)
        return "\n".join(lines)
