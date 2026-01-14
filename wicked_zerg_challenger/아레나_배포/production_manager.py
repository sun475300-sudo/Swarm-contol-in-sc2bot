# -*- coding: utf-8 -*-
"""
Production Manager

Core loop for unit production and supply management.
Responsibilities:
    1. Predictive Overlord production (prevent supply block)
    2. Drone production (economy)
    3. Queen production (creep/larva)
    4. Tech-based army production (Zergling → Roach → Hydralisk)
    5. Counter-based unit selection (Counter-Build)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from wicked_zerg_bot_pro import WickedZergBotPro

import json
import os
import random
from typing import Dict, List, Optional

from sc2.data import Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2

from config import COUNTER_BUILD, Config, EnemyRace, GamePhase, get_learned_parameter
from unit_factory import UnitFactory

# Logger setup
try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class ProductionManager:
    """
    생산 관리자

    유닛 생산 우선순위와 인구수 관리를 담당합니다.
    """

    def __init__(self, bot: "WickedZergBotPro"):
        """
        Args:
            bot: 메인 봇 인스턴스
        """
        self.bot = bot
        self.config = Config()

        # Unit Factory (유닛 생산 전문 모듈)
        self.unit_factory = UnitFactory(self)

        # 승률 추적 (CombatManager와 공유)
        self.last_calculated_win_rate: float = 50.0

        # 자원 임계값 설정 (건설 후에도 최소 자원 보유)
        # 건물을 지은 후에도 즉시 다른 대응(유닛 생산, 연구)을 할 수 있는 최소 자원
        self.mineral_reserve_threshold: float = 300.0  # 최소 미네랄 보유량
        self.vespene_reserve_threshold: float = 100.0  # 최소 가스 보유량

        # 가치 기반 의사결정 시스템 (Utility System)
        self.current_mode: str = "PRODUCTION"  # "PRODUCTION" or "CONSTRUCTION" - 상태 머신
        self.tech_priority_score: float = 0.0  # 테크 건물 건설의 가치 점수 (0.0 ~ 100.0)
        self.production_priority_score: float = 0.0  # 유닛 생산의 가치 점수 (0.0 ~ 100.0)

        # 자율적 자원 관리 (Autonomous Resource Management)
        self.autonomous_reserve_minerals: float = 0.0  # 봇이 스스로 결정한 미네랄 저축량
        self.autonomous_reserve_vespene: float = 0.0  # 봇이 스스로 결정한 가스 저축량

        # 상위 테크 판단용 공유 지식
        self.high_tech_units = {
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKERMP,
            UnitTypeId.MUTALISK,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.ULTRALISK,
            UnitTypeId.BROODLORD,
            UnitTypeId.INFESTOR,
            UnitTypeId.SWARMHOSTMP,
        }
        self.high_tech_zergling_ratio: float = 0.7  # Force tech when zerglings exceed 70% of army
        self.high_tech_gas_threshold: int = 200  # Minimum gas to trigger tech shift

        # 유닛 가치 가중치 (RL 보상 및 생산 우선순위용)
        self.unit_value_weights = {
            UnitTypeId.ZERGLING: 1.0,
            UnitTypeId.ROACH: 2.5,
            UnitTypeId.RAVAGER: 3.5,
            UnitTypeId.HYDRALISK: 3.5,
            UnitTypeId.MUTALISK: 4.5,
            UnitTypeId.CORRUPTOR: 4.0,
            UnitTypeId.LURKERMP: 6.0,
            UnitTypeId.ULTRALISK: 10.0,
            UnitTypeId.BROODLORD: 12.0,
            UnitTypeId.INFESTOR: 8.0,
            UnitTypeId.SWARMHOSTMP: 7.0,
        }

        # Tier 기반 보상 가중치 (승리 시 유닛 구성에 따른 보너스)
        self.tier_reward_weights = {
            UnitTypeId.ZERGLING: 0.1,
            UnitTypeId.ROACH: 0.5,
            UnitTypeId.RAVAGER: 0.8,
            UnitTypeId.HYDRALISK: 1.2,
            UnitTypeId.MUTALISK: 1.5,
            UnitTypeId.CORRUPTOR: 1.3,
            UnitTypeId.LURKERMP: 2.0,
            UnitTypeId.ULTRALISK: 3.0,
            UnitTypeId.BROODLORD: 3.5,
            UnitTypeId.INFESTOR: 2.5,
            UnitTypeId.SWARMHOSTMP: 2.2,
        }

        # 레거시 플래그 제거됨 - 이제 current_mode 기반 자율 의사결정만 사용
        # self.stop_unit_production과 self.can_train_combat_units는 더 이상 사용하지 않음
        self.tech_build_queue: List[Dict[str, Any]] = []  # 건설 대기 중인 테크 건물 큐

        # Building construction throttling to prevent command spam
        self.last_build_check: Dict[
            UnitTypeId, int
        ] = {}  # Track last check iteration for each building type
        self.build_check_interval: int = (
            22  # Check building construction every 22 frames (~1 second, prevents spam)
        )

        # Shared build reservations (cross-manager) to block duplicate construction commands
        if not hasattr(self.bot, "build_reservations"):
            self.bot.build_reservations: Dict[UnitTypeId, float] = {}

        # Track recent builds to prevent duplicate build commands (structure_type -> iteration)
        if not hasattr(self.bot, "just_built_structures"):
            self.bot.just_built_structures: Dict[UnitTypeId, int] = {}

        # Load learned parameters from self-evolution system
        # These override default Config values
        self.expansion_mineral_threshold = get_learned_parameter(
            "expansion_mineral_threshold", self.config.MINERAL_THRESHOLD
        )
        self.priority_zero_threshold = get_learned_parameter(
            "priority_zero_threshold", 10
        )  # Default: 10 workers
        self.macro_hatchery_threshold = get_learned_parameter(
            "macro_hatchery_threshold", 500
        )  # Default: 500 minerals

        # Log learned parameters if they differ from defaults
        if self.expansion_mineral_threshold != self.config.MINERAL_THRESHOLD:
            print(
                f"[EVOLUTION] Using learned expansion_mineral_threshold: {self.expansion_mineral_threshold} (default: {self.config.MINERAL_THRESHOLD})"
            )
        if self.priority_zero_threshold != 10:
            print(
                f"[EVOLUTION] Using learned priority_zero_threshold: {self.priority_zero_threshold} (default: 10)"
            )

        # 상대 종족 (정찰로 업데이트)
        self.enemy_race: EnemyRace = EnemyRace.UNKNOWN

        # 생산 통계
        self.first_zergling_time: Optional[float] = None
        self.supply_block_count: int = 0

        # 🏗️ 빌드 오더 타이밍 추적 (RL 보상 계산용)
        self.build_order_timing: Dict[str, Optional[float]] = {
            "spawning_pool": None,  # 산란못 완공 시간
            "roach_warren": None,  # 로치 워렌 완공 시간
            "hydralisk_den": None,  # 히드라 둥지 완공 시간
            "expansion": None,  # 멀티 확장 시간
        }
        self.spawning_pool_completed = False  # 산란못 완공 여부
        self.roach_warren_completed = False  # 로치 워렌 완공 여부
        self.hydralisk_den_completed = False  # 히드라 둥지 완공 여부

        # Serral 빌드 오더 추적 (이전에 _should_use_basic_units 메서드에 잘못 들어가 있음)
        self.serral_build_completed = {
            "natural_expansion": False,  # 16 앞마당
            "gas": False,  # 18 가스
            "spawning_pool": False,  # 17 산란못
            "third_hatchery": False,  # 28 세 번째 해처리
            "speed_upgrade": False,  # 30 발업
        }

        # Serral 빌드 오더 타이밍 (신경망 학습용)
        self.serral_build_order_timing: Dict[str, Optional[float]] = {
            "natural_expansion_supply": None,
            "natural_expansion_time": None,
            "gas_supply": None,
            "gas_time": None,
            "spawning_pool_supply": None,
            "spawning_pool_time": None,
            "third_hatchery_supply": None,
            "third_hatchery_time": None,
            "speed_upgrade_supply": None,
            "speed_upgrade_time": None,
        }

        # Curriculum Learning: 난이도 인식
        self.curriculum_level_idx = self._load_curriculum_level()

    def _load_curriculum_level(self) -> int:
        """
        Curriculum Learning 레벨 로드

        Returns:
            int: 현재 curriculum 레벨 인덱스 (0=VeryEasy, 5=CheatInsane)
        """
        try:
            stats_file = os.path.join("data", "training_stats.json")
            if os.path.exists(stats_file):
                with open(stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    level_idx = data.get("curriculum_level_idx", 0)
                    # 유효성 검사
                    if 0 <= level_idx <= 5:
                        return level_idx
        except Exception:
            pass
        return 0  # 기본값: VeryEasy

    def _should_use_basic_units(self) -> bool:
        """
        난이도가 낮을 때 기본 물량(저글링/바퀴) 중심으로 생산할지 결정

        Returns:
            bool: True면 기본 물량 중심, False면 정상 생산
        """
        # VeryEasy, Easy 단계에서는 기본 물량 중심
        return self.curriculum_level_idx <= 1

    def _should_force_high_tech_production(self) -> bool:
        """Force tech production when army is overly zergling-heavy and gas is floating."""
        b = self.bot
        intel = getattr(b, "intel", None)

        # Prefer cached counts for performance
        if intel and intel.cached_zerglings is not None:
            zerglings = intel.cached_zerglings
            zergling_count = (
                zerglings.amount if hasattr(zerglings, "amount") else len(list(zerglings))
            )
        else:
            zerglings = b.units(UnitTypeId.ZERGLING)
            zergling_count = (
                zerglings.amount if hasattr(zerglings, "amount") else len(list(zerglings))
            )

        # Approximate supply: zerglings use 0.5 supply each
        zergling_supply = zergling_count * 0.5
        army_supply = max(1.0, float(getattr(b, "supply_army", 0.0)))
        zergling_ratio = zergling_supply / army_supply

        # Gas float check + require at least two bases for sustainability
        if intel and intel.cached_townhalls is not None:
            base_count = (
                intel.cached_townhalls.amount
                if hasattr(intel.cached_townhalls, "amount")
                else len(list(intel.cached_townhalls))
            )
        else:
            base_count = len(list(b.townhalls)) if hasattr(b, "townhalls") else 0

        return (
            zergling_ratio >= self.high_tech_zergling_ratio
            and b.vespene >= self.high_tech_gas_threshold
            and base_count >= 2
            and army_supply >= 8  # ensure we have an army before shifting priorities
        )

    def _select_counter_unit_by_matchup(self) -> Optional[UnitTypeId]:
        """Select best high-tech unit based on enemy composition (counter-based selection)."""
        b = self.bot
        intel = getattr(b, "intel", None)

        # Count enemy threats via cached intel or direct query
        enemy_air_count = 0
        enemy_armored_ground = 0
        enemy_bio_count = 0

        if intel and hasattr(intel, "enemy_intel"):
            enemy_units_seen = getattr(intel.enemy_intel, "units_seen", set())
            # Air threats
            air_units = {
                UnitTypeId.MUTALISK,
                UnitTypeId.VOIDRAY,
                UnitTypeId.PHOENIX,
                UnitTypeId.CARRIER,
                UnitTypeId.BATTLECRUISER,
                UnitTypeId.LIBERATOR,
                UnitTypeId.BANSHEE,
            }
            enemy_air_count = len([u for u in enemy_units_seen if u in air_units])

            # Armored ground (Immortals, Siege Tanks, etc.)
            armored_units = {UnitTypeId.IMMORTAL, UnitTypeId.SIEGETANK, UnitTypeId.THOR}
            enemy_armored_ground = len([u for u in enemy_units_seen if u in armored_units])

            # Bio units (Marines, Zealots, etc.)
            bio_units = {UnitTypeId.MARINE, UnitTypeId.MARAUDER, UnitTypeId.ZEALOT}
            enemy_bio_count = len([u for u in enemy_units_seen if u in bio_units])

        # Counter selection logic
        # 1. Enemy has strong armored ground → Brood Lord (if Greater Spire ready)
        if enemy_armored_ground >= 2:
            if b.structures(UnitTypeId.GREATERSPIRE).ready.exists:
                return UnitTypeId.BROODLORD
            # Fallback: Ravager (bile attacks)
            if b.structures(UnitTypeId.ROACHWARREN).ready.exists:
                return UnitTypeId.RAVAGER

        # 2. Enemy has air units → Corruptor or Hydralisk
        if enemy_air_count >= 3:
            if b.structures(UnitTypeId.SPIRE).ready.exists:
                return UnitTypeId.CORRUPTOR
            if b.structures(UnitTypeId.HYDRALISKDEN).ready.exists:
                return UnitTypeId.HYDRALISK

        # 3. Enemy is bio-heavy → Ultralisk (if Ultralisk Cavern ready)
        if enemy_bio_count >= 3:
            if b.structures(UnitTypeId.ULTRALISKCAVERN).ready.exists:
                return UnitTypeId.ULTRALISK
            # Fallback: Lurker for splash damage
            if b.structures(UnitTypeId.LURKERDEN).ready.exists:
                return UnitTypeId.LURKERMP

        # 4. Default: Mutalisk for mobility (if Spire ready and low enemy anti-air)
        if enemy_air_count < 3 and b.structures(UnitTypeId.SPIRE).ready.exists:
            return UnitTypeId.MUTALISK

        return None  # No clear counter choice; fall back to standard production

    def _ensure_build_reservations(self) -> Dict[UnitTypeId, float]:
        """Ensure shared reservation map exists and return it."""
        if not hasattr(self.bot, "build_reservations"):
            self.bot.build_reservations = {}
        return self.bot.build_reservations  # type: ignore

    def _cleanup_build_reservations(self) -> None:
        """Remove stale reservations to avoid blocking rebuilds after failed attempts."""
        try:
            reservations = self._ensure_build_reservations()
            now = getattr(self.bot, "time", 0.0)
            stale_keys = [sid for sid, ts in reservations.items() if now - ts > 45.0]
            for sid in stale_keys:
                reservations.pop(sid, None)
        except Exception:
            pass

    def _reserve_building(self, structure_id: UnitTypeId) -> None:
        """Reserve a structure type so parallel managers don't issue duplicate builds."""
        try:
            reservations = self._ensure_build_reservations()
            reservations[structure_id] = getattr(self.bot, "time", 0.0)
        except Exception:
            pass

    def _can_build_safely(
        self, structure_id: UnitTypeId, check_workers: bool = True, reserve_on_pass: bool = False
    ) -> bool:
        """
        중복 건설을 원천 차단하는 안전한 건설 체크 함수

        Args:
            structure_id: 건설할 건물 타입
            check_workers: 일벌레 명령 체크 여부 (기본값: True)

        Returns:
            bool: 안전하게 건설할 수 있으면 True
        """
        b = self.bot

        # Block duplicate attempts if another manager reserved this build recently
        self._cleanup_build_reservations()
        reservations = getattr(b, "build_reservations", {})
        if reservations.get(structure_id) is not None:
            return False

        # 1. 이미 존재하는지 확인 (건설 완료된 건물)
        existing = b.structures(structure_id).amount
        if existing > 0:
            return False

        # 1.5. 건설 중인 건물도 확인 (is_ready가 False인 경우)
        building_structures = b.structures(structure_id)
        if building_structures.exists:
            # 건설 중인 건물이 있으면 건설 불가
            for struct in building_structures:
                if not struct.is_ready:
                    return False

        # 2. 현재 건설 중(Pending)인지 확인
        pending = b.already_pending(structure_id)
        if pending > 0:
            return False

        # 3. (중요) 건설하러 이동 중인 일벌레가 있는지 확인
        # 가끔 already_pending에 잡히기 전 찰나의 순간을 방어합니다.
        if check_workers:
            try:
                # 건물 생성 능력 ID 가져오기
                creation_ability = b.game_data.units[structure_id.value].creation_ability
                if creation_ability:
                    # 일벌레들의 명령 확인
                    for worker in b.workers:
                        if worker.orders:
                            for order in worker.orders:
                                if order.ability.id == creation_ability.id:
                                    return False
            except (AttributeError, KeyError, TypeError):
                # 에러 발생 시 안전하게 False 반환하지 않고 계속 진행
                # (일부 건물은 creation_ability가 없을 수 있음)
                pass

        # 4. 가스 건물(Extractor) 특수 체크: 같은 가스 지점에 이미 건설 중인지 확인
        if structure_id == UnitTypeId.EXTRACTOR:
            # 가스 지점 근처에 이미 Extractor가 있는지 확인
            vespene_geysers = b.vespene_geyser
            for geyser in vespene_geysers:
                nearby_extractors = b.structures(UnitTypeId.EXTRACTOR).closer_than(1.0, geyser)
                if nearby_extractors:
                    return False

        # 5. Recent build check (prevent concurrency issues)
        # Avoid issuing multiple build commands for the same structure within a few frames
        if hasattr(b, 'just_built_structures'):
            last_build_iteration = b.just_built_structures.get(structure_id, -1000)
            # Block if the same structure was built within the last 10 frames
            if b.iteration - last_build_iteration < 10:
                return False

        if reserve_on_pass:
            self._reserve_building(structure_id)

        return True

    async def update(self, game_phase: GamePhase):
        """
        매 프레임 호출되는 생산 관리 메인 루프

        🛡️ 안전장치: townhalls나 workers가 없으면 즉시 리턴 (Melee Ladder 생존)

        Args:
            game_phase: 현재 게임 단계
        """
        b = self.bot

        # 🛡️ 철벽 안전장치: townhalls가 비어있으면 즉시 리턴
        # 🚀 성능 최적화: IntelManager 캐시 사용
        try:
            intel = getattr(b, "intel", None)
            if intel and intel.cached_townhalls is not None:
                townhalls = intel.cached_townhalls
                if not townhalls.exists:
                    return
            else:
                # Fallback: 직접 접근
                if not b.townhalls.exists:
                    return
                townhalls = b.townhalls
        except Exception:
            # townhalls 접근 실패 시 조용히 리턴
            return

        try:
            # 적응형 빌드 계획 가져오기
            build_plan = getattr(b, "current_build_plan", None)
            army_ratio = build_plan.get("army_ratio", 0.7) if build_plan else 0.7
            priority_unit = (
                build_plan.get("priority_unit", UnitTypeId.ZERGLING)
                if build_plan
                else UnitTypeId.ZERGLING
            )

            # OPTIMIZED: Force resource consumption BEFORE can_afford checks
            # This prevents mineral accumulation (5,000+ minerals problem)
            # Check minerals BEFORE any production decisions
            # CRITICAL: Lower threshold (500) for aggressive resource spending
            from config import get_learned_parameter

            aggressive_flush_threshold = get_learned_parameter(
                "aggressive_flush_threshold", 500
            )  # Lower threshold
            flush_mode_threshold = get_learned_parameter("flush_mode_threshold", 1500)

            # If minerals exceed aggressive threshold (500+), force resource consumption FIRST
            if b.minerals >= aggressive_flush_threshold:
                # Force flush BEFORE any other production decisions
                if await self._flush_resources():
                    return  # Resources flushed, continue next frame

            # 0️⃣ Serral 빌드 오더 실행 (초반 최우선)
            if game_phase == GamePhase.OPENING:
                if await self._execute_serral_opening():
                    return

            # 5️⃣ 드론 생산 (경제 단계) - 공격 유닛 생산 후에만
            # 🚀 성능 최적화: 캐시된 workers 사용 (불필요한 리스트 변환 제거)
            try:
                if intel and intel.cached_workers is not None:
                    # 캐시된 workers 사용 (이미 필터링됨)
                    worker_count = (
                        intel.cached_workers.amount
                        if hasattr(intel.cached_workers, "amount")
                        else len(list(intel.cached_workers))
                    )
                else:
                    # Fallback: 직접 접근 (하위 호환성)
                    worker_count = (
                        b.workers.amount if hasattr(b.workers, "amount") else len(list(b.workers))
                    )
            except Exception:
                worker_count = 0

            # PRIORITY ZERO: Worker count below threshold - ABSOLUTE EMERGENCY (prevent total economy collapse)
            # CRITICAL: In Priority Zero, overlord production takes precedence if supply blocked
            # This prevents the "can't afford drone because supply blocked" death spiral
            # Uses learned parameter (default: 10, learned: priority_zero_threshold)
            if worker_count < self.priority_zero_threshold:
                # If supply blocked and have 100+ minerals, produce overlord FIRST
                if b.supply_left <= 2 and b.minerals >= 100:
                    if await self._produce_overlord():
                        return  # Overlord produced, will try drone next frame

                # Then try to produce drone
                if await self._produce_drone():
                    return

            # 1️⃣ 대군주 예측 생산 (최우선) - Normal priority after Priority Zero check
            if await self._produce_overlord():
                return

            # 2️⃣ 여왕 생산
            await self._produce_queen()

            # 3️⃣ 확장 전 방어 유닛 우선 생산
            if await self._ensure_defense_before_expansion():
                return

            # 3.5️⃣ 상대 공격 전 방어 병력 유지 및 미네랄 소비 (NEW)
            # 상대가 공격을 오기 전에 미네랄이 많이 남으면 병력을 생산하고,
            # 기지를 방어할 수 있을 만큼의 병력을 유지
            if await self._maintain_defensive_army():
                return

            # 4️⃣ Adaptive unit production logic (Context-aware Emergency Production)
            # 산란못이 완성되었고 저글링이 부족하면 일벌레보다 저글링 우선!
            if await self._produce_emergency_units():
                return

            # 4.5️⃣ RESOURCE FLUSH: Aggressive Larva Usage (Priority #1 Fix - URGENT)
            # Resource flush thresholds are now learned parameters (not hardcoded)
            # Bot learns optimal thresholds through experience
            # This prevents the "4,200 minerals but no army" problem
            if await self._flush_resources():
                return  # Resources flushed, will continue next frame

            # 4.5.5️⃣ AGGRESSIVE UNIT PRODUCTION: Always produce units when resources and larvae are available
            # CRITICAL: This ensures continuous unit production regardless of other conditions
            # This prevents resource accumulation and ensures army is always growing
            if await self._aggressive_unit_production():
                return  # Units produced, continue next frame

            # 4.6️⃣ MACRO HATCHERY: 자율적 해처리 건설 (봇이 스스로 판단하여 학습된 임계값에 도달하면 건설)
            # Threshold is learned parameter, not hardcoded
            # Bot learns optimal timing through experience
            if await self._build_macro_hatchery():
                return  # Macro hatchery construction started

            # 4.7️⃣ MANDATORY UPGRADES: Auto-research upgrades when resources are available
            # This ensures upgrades are always researched when resources are available
            if await self._research_mandatory_upgrades():
                return  # Upgrade research started

            # NOTE: Tech building construction and upgrades are handled by EconomyManager.

            # EMERGENCY: Worker count below 16 - CRITICAL PRIORITY (prevent ECONOMY_COLLAPSE)
            # This must be checked BEFORE any other production to ensure worker recovery
            if worker_count < 16:
                if await self._produce_drone():
                    return

            # 드론 60마리까지는 모든 라바를 드론에 집중 (수비 위주 운영)
            if worker_count < 60:
                if await self._produce_drone():
                    return

            # 드론 60마리 이후: 적응형 빌드 계획 반영
            if game_phase in [GamePhase.OPENING, GamePhase.ECONOMY]:
                if not self.config.ALL_IN_12_POOL:  # 올인 모드가 아니면 일반 드론 생산
                    # 적응형 빌드: worker_limit 반영
                    worker_limit = (
                        build_plan.get("worker_limit", self.config.MAX_WORKERS)
                        if build_plan
                        else self.config.MAX_WORKERS
                    )
                    if worker_count < worker_limit:
                        # 경제 집중 모드면 드론 우선 생산
                        if build_plan and build_plan.get("priority_unit") == UnitTypeId.DRONE:
                            if await self._produce_drone():
                                return
                        # 일반 모드
                        elif worker_count < self.config.MAX_WORKERS:
                            if await self._produce_drone():
                                return
                else:
                    # 12못 올인 모드: 드론 12마리까지만 생산
                    if worker_count < self.config.ALL_IN_WORKER_LIMIT:
                        if await self._produce_drone():
                            return

        except Exception as e:
            # Error handling for production logic
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] Production manager update error: {e}")

        # 6️⃣ 가스 확보용 빠른 멀티 확장 (가스 수입 극대화)
        await self._expand_for_gas()

        # 6.4️⃣ 승률 대조 및 채팅 출력 (10초마다)
        await self.display_matchup_win_rate()

        # 6.5️⃣ 중반 강력 빌드 생산 (러쉬 실패 시 전환)
        if hasattr(b, "mid_game_strong_build_active") and b.mid_game_strong_build_active:
            if await self._produce_mid_game_strong_build():
                return  # Strong build units produced

        # 7️⃣ 군사 유닛 생산 (드론 60마리 이후 또는 적응형 빌드 계획 반영)
        await self._produce_army(game_phase, build_plan)

    # 1️⃣ 대군주 예측 생산
    async def _produce_overlord(self) -> bool:
        """
        대군주 예측 생산 - 인구수 막힘 방지 (개선된 자동화 로직)

        Enhanced: Predictive overlord production based on:
        1. Current supply usage rate
        2. Larva production rate
        3. Planned unit production
        4. Dynamic buffer adjustment

        This prevents supply blocks by predicting future supply needs
        """
        b = self.bot

        # 🚀 성능 최적화: 캐시된 larva 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_larva is not None:
            larvae = intel.cached_larva
        else:
            larvae = b.larva

        if not larvae or not larvae.exists:
            return False

        # Dynamic supply buffer: Adjust based on game phase and production rate
        # Early game: Smaller buffer (8 supply)
        # Mid game: Medium buffer (12 supply)
        # Late game: Larger buffer (16 supply)
        game_time = b.time
        if game_time < 180:  # First 3 minutes
            supply_buffer = 8
        elif game_time < 600:  # 3-10 minutes
            supply_buffer = 12
        else:  # After 10 minutes
            supply_buffer = 16

        # Calculate production rate (units per minute)
        # Estimate based on larva count, hatchery count, AND military production buildings
        # 🚀 성능 최적화: .amount 속성 사용 (리스트 변환 불필요)
        if intel and intel.cached_townhalls is not None:
            hatchery_count = (
                intel.cached_townhalls.amount
                if hasattr(intel.cached_townhalls, "amount")
                else len(list(intel.cached_townhalls))
            )
        else:
            hatchery_count = (
                b.townhalls.amount if hasattr(b.townhalls, "amount") else len(list(b.townhalls))
            )
        larva_count = larvae.amount if hasattr(larvae, "amount") else len(list(larvae))

        # CRITICAL: Count military production buildings (가속 로직)
        # More production buildings = faster supply consumption = need more overlords
        spawning_pools = (
            b.structures(UnitTypeId.SPAWNINGPOOL).ready.amount
            if hasattr(b.structures(UnitTypeId.SPAWNINGPOOL).ready, "amount")
            else len(list(b.structures(UnitTypeId.SPAWNINGPOOL).ready))
        )
        roach_warrens = (
            b.structures(UnitTypeId.ROACHWARREN).ready.amount
            if hasattr(b.structures(UnitTypeId.ROACHWARREN).ready, "amount")
            else len(list(b.structures(UnitTypeId.ROACHWARREN).ready))
        )
        hydra_dens = (
            b.structures(UnitTypeId.HYDRALISKDEN).ready.amount
            if hasattr(b.structures(UnitTypeId.HYDRALISKDEN).ready, "amount")
            else len(list(b.structures(UnitTypeId.HYDRALISKDEN).ready))
        )

        # Military production building count (병력 생산 건물 수)
        military_buildings = spawning_pools + roach_warrens + hydra_dens

        # Estimate production rate: ~1 unit per 12 seconds per hatchery (with larva)
        # More hatcheries = faster production = need more overlords
        base_production_rate = hatchery_count * (larva_count / 3)  # Rough estimate

        # CRITICAL: Accelerated production rate calculation (가속 로직)
        # Each military building multiplies production rate by 1.2x
        production_multiplier = 1.0 + (military_buildings * 0.2)  # 20% per building
        estimated_production_rate = base_production_rate * production_multiplier

        # CRITICAL: Overlord production time (약 15초) 고려한 선제적 생산
        # Current supply consumption rate (supply per second)
        # Estimate: 1 unit per 12 seconds per hatchery, each unit = 2 supply average
        supply_consumption_per_second = estimated_production_rate * (
            2.0 / 60.0
        )  # supply per second
        overlord_production_time = 15.0  # seconds

        # Calculate how much supply will be consumed during overlord production
        supply_needed_during_production = supply_consumption_per_second * overlord_production_time

        # Accelerated buffer: Increase buffer based on production buildings
        # More military buildings = higher buffer needed
        accelerated_buffer_bonus = military_buildings * 2  # +2 supply per building
        supply_buffer += int(accelerated_buffer_bonus)

        # Also account for supply needed during overlord production
        supply_buffer = max(supply_buffer, int(supply_needed_during_production) + 4)

        # Adjust buffer based on production rate
        if estimated_production_rate > 5:  # High production rate
            supply_buffer += 4  # Need more buffer
        elif estimated_production_rate < 2:  # Low production rate
            supply_buffer = max(6, supply_buffer - 2)  # Can use smaller buffer

        pending_overlords = b.already_pending(UnitTypeId.OVERLORD)

        # CRITICAL: If supply_left < 4, produce overlord IMMEDIATELY (emergency)
        # This prevents supply blocks during rapid unit production
        # OPTIMIZED: Proactive overlord production to prevent supply blocks
        # Produce overlord when supply_left < 5 to ensure continuous unit production
        # This prevents supply blocks during rapid unit production
        supply_threshold = (
            5  # Produce overlord when 5 supply left (optimal for continuous production)
        )
        if b.supply_left < supply_threshold and b.supply_cap < 200:
            if b.can_afford(UnitTypeId.OVERLORD) and larvae and len(larvae) > 0:
                if pending_overlords == 0:
                    random.choice(larvae).train(UnitTypeId.OVERLORD)
                    print(f"[OVERLORD] Emergency production at {b.supply_left} supply left")
                    return True
                elif pending_overlords == 1 and b.supply_left < 2:
                    # Double emergency: produce second overlord
                    if b.can_afford(UnitTypeId.OVERLORD) and len(larvae) > 1:
                        random.choice(larvae).train(UnitTypeId.OVERLORD)
                        print(
                            f"[OVERLORD] Double emergency production at {b.supply_left} supply left"
                        )
                        return True

        # PREDICTIVE: Calculate needed overlords based on supply buffer
        if b.supply_left < supply_buffer and b.supply_cap < 200:
            # Calculate how many overlords we need
            # Each overlord provides 8 supply
            supply_deficit = supply_buffer - b.supply_left
            needed_overlords = max(1, (supply_deficit + 7) // 8)  # Round up

            # If supply is very low (< 8), always produce at least 2 overlords
            if b.supply_left < 8:
                needed_overlords = max(needed_overlords, 2)

            # If we have multiple hatcheries and high production, produce more overlords
            if hatchery_count >= 2 and estimated_production_rate > 3:
                needed_overlords = max(needed_overlords, 2)

            # Produce overlords if needed
            if pending_overlords < needed_overlords:
                if b.can_afford(UnitTypeId.OVERLORD) and larvae and len(larvae) > 0:
                    # Produce multiple overlords if needed and affordable
                    overlords_to_produce = int(
                        min(needed_overlords - pending_overlords, len(larvae))
                    )
                    for _ in range(overlords_to_produce):
                        if b.can_afford(UnitTypeId.OVERLORD) and larvae:
                            random.choice(larvae).train(UnitTypeId.OVERLORD)
                            if overlords_to_produce > 1:
                                print(
                                    f"[OVERLORD] Predictive production: {overlords_to_produce} overlords (supply: {b.supply_left}/{b.supply_cap})"
                                )
                    return True
                else:
                    # 인구수 막힘 카운트 및 경고
                    self.supply_block_count += 1
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 22 == 0:  # Log every second (22.4 FPS)
                        print(
                            f"[WARNING] [{int(b.time)}s] Supply block risk! Need {needed_overlords} overlords but can't afford (supply: {b.supply_left}/{b.supply_cap})"
                        )

        # PROACTIVE: If we have excess minerals and supply is getting low, produce overlord early
        # This prevents supply blocks during economic booms
        # Use learned parameter for excess mineral threshold

        excess_mineral_threshold = get_learned_parameter("excess_mineral_threshold", 200)

        if b.supply_left < supply_buffer + 4 and b.supply_cap < 200:
            if (
                b.minerals >= excess_mineral_threshold and larvae and len(larvae) > 0
            ):  # Excess minerals
                if pending_overlords == 0:
                    if b.can_afford(UnitTypeId.OVERLORD):
                        random.choice(larvae).train(UnitTypeId.OVERLORD)
                        print(f"[OVERLORD] Proactive production (excess minerals: {b.minerals})")
                        return True

        return False

    # 2️⃣ 여왕 생산
    async def _produce_queen(self):
        """여왕 생산 (부화장마다 1마리)"""
        b = self.bot

        # 🚀 산란못 준비 상태는 sticky 플래그도 허용 (fog/캐시 문제 방지)
        if not self._has_required_building(UnitTypeId.SPAWNINGPOOL):
            return

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel:
            queens = intel.cached_queens or b.units(UnitTypeId.QUEEN)
            if intel.cached_townhalls is not None:
                townhalls = list(intel.cached_townhalls) if intel.cached_townhalls.exists else []
            else:
                townhalls = [th for th in b.townhalls]
        else:
            queens = b.units(UnitTypeId.QUEEN)
            townhalls = [th for th in b.townhalls]
        queens_count = len(queens) + b.already_pending(UnitTypeId.QUEEN)

        # 기지당 여왕 1마리
        if queens_count < len(townhalls):
            ready_idle_townhalls = [th for th in townhalls if th.is_ready and th.is_idle]
            for hatch in ready_idle_townhalls:
                if b.can_afford(UnitTypeId.QUEEN):
                    hatch.train(UnitTypeId.QUEEN)
                    print(f"👑 [{int(b.time)}초] 여왕 생산")
                    break

    # 3️⃣ 확장 전 방어 유닛 확보
    async def _ensure_defense_before_expansion(self) -> bool:
        """
        멀티 확장 전에 기본적인 방어 유닛과 가시 촉수를 확보

        Enhanced: Also builds Spine Crawlers vs Terran for early defense

        Returns:
            bool: 방어 유닛/건물을 생산했으면 True
        """
        b = self.bot

        try:
            # 12못 올인 모드에서는 확장 전 방어 체크 안 함 (올인 빌드)
            if self.config.ALL_IN_12_POOL:
                return False

            # 🚀 성능 최적화: IntelManager 캐시 사용
            intel = getattr(b, "intel", None)
            if intel and intel.cached_townhalls is not None:
                townhalls = list(intel.cached_townhalls) if intel.cached_townhalls.exists else []
            else:
                townhalls = [th for th in b.townhalls]
            current_base_count = len(townhalls)

            # 이미 확장 중이면 체크 안 함
            if b.already_pending(UnitTypeId.HATCHERY) > 0:
                return False

            # 첫 번째 확장(2번째 기지) 전에만 엄격하게 체크
            if current_base_count >= 2:
                return False

            # Priority 1: Build Spine Crawlers vs Terran (early defense against Hellions/Marines)
            if hasattr(b, "opponent_race") and b.opponent_race == Race.Terran:
                spawning_pools = [s for s in b.structures(UnitTypeId.SPAWNINGPOOL) if s.is_ready]
                if spawning_pools:
                    spine_crawlers = [
                        s for s in b.structures(UnitTypeId.SPINECRAWLER) if s.is_ready
                    ]
                    # Build 1-2 spine crawlers early vs Terran for defense
                    if len(spine_crawlers) < 2 and b.time < 300:  # First 5 minutes
                        if b.can_afford(UnitTypeId.SPINECRAWLER):
                            try:
                                # Place spine crawler near main hatchery
                                main_hatch = townhalls[0] if townhalls else None
                                if main_hatch:
                                    # Place 5 units away from hatchery (towards mineral line)
                                    if b.mineral_field.exists:
                                        nearest_mineral = b.mineral_field.closest_to(main_hatch)
                                        spine_pos = main_hatch.position.towards(
                                            nearest_mineral.position, 5
                                        )
                                    else:
                                        spine_pos = main_hatch.position.offset(Point2((5, 0)))

                                    await b.build(UnitTypeId.SPINECRAWLER, near=spine_pos)
                                    print(
                                        f"[EVOLUTION] Early Defense: Building Spine Crawler vs Terran (Time: {int(b.time)}s)"
                                    )
                                    return True
                            except Exception:
                                pass  # Silently fail if construction fails

            # 현재 방어 유닛 수 체크
            # 🚀 성능 최적화: .amount 속성 사용 (불필요한 리스트 변환 제거)
            zerglings = b.units(UnitTypeId.ZERGLING)
            roaches = b.units(UnitTypeId.ROACH)
            zergling_count = (
                zerglings.amount if hasattr(zerglings, "amount") else len(list(zerglings))
            )
            roach_count = roaches.amount if hasattr(roaches, "amount") else len(list(roaches))
            total_defense_units = zergling_count + roach_count
            min_defense = self.config.MIN_DEFENSE_BEFORE_EXPAND

            # 방어 유닛이 부족하면 우선 생산
            if total_defense_units < min_defense:
                # 🚀 성능 최적화: 캐시된 larva 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_larva is not None:
                    larvae = intel.cached_larva
                else:
                    larvae = b.larva

                if not larvae or not larvae.exists:
                    return False

                # 인구수 체크
                if b.supply_left < 2:
                    return False

                # 산란못이 있어야 저글링 생산 가능 (sticky 플래그 허용)
                if self._has_required_building(UnitTypeId.SPAWNINGPOOL):
                    # 저글링 우선 생산
                    if b.can_afford(UnitTypeId.ZERGLING):
                        ready_larvae = larvae.ready.idle if hasattr(larvae, "ready") else larvae
                        if ready_larvae.exists:
                            ready_larvae.random.train(UnitTypeId.ZERGLING)
                            return True
        except Exception as e:
            # 에러 발생 시 로그만 출력 (게임 중단 방지)
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _ensure_defense_before_expansion 오류: {e}")
            return False

            # 로치 워렌이 있으면 로치 생산
            # 🚀 성능 최적화: .of_type() 사용 (리스트 변환 불필요)
            roach_warrens = b.structures(UnitTypeId.ROACHWARREN).ready
            if roach_warrens.exists:
                if b.can_afford(UnitTypeId.ROACH):
                    ready_larvae = larvae.ready.idle if hasattr(larvae, "ready") else larvae
                    if ready_larvae.exists:
                        ready_larvae.random.train(UnitTypeId.ROACH)
                        return True

        return False

    # 3.5️⃣ 상대 공격 전 방어 병력 유지 및 미네랄 소비
    async def _maintain_defensive_army(self) -> bool:
        """
        상대가 공격을 오기 전에 방어 병력을 유지하고 미네랄을 소비

        기능:
        1. 상대 공격 준비 상태 감지 (적 유닛이 본진으로 이동 중인지 확인)
        2. 미네랄이 많이 쌓이면 (800+) 병력 생산 강화
        3. 최소 방어 병력 유지 (본진 방어 가능한 수준)

        Returns:
            bool: 병력을 생산했으면 True
        """
        b = self.bot

        try:
            # 현재 병력 수 확인
            # 🚀 성능 최적화: IntelManager 캐시 사용
            intel = getattr(b, "intel", None)
            if intel:
                zerglings = (
                    intel.cached_zerglings.amount
                    if intel.cached_zerglings and hasattr(intel.cached_zerglings, "amount")
                    else (
                        len(list(intel.cached_zerglings))
                        if intel.cached_zerglings and intel.cached_zerglings.exists
                        else 0
                    )
                )
                roaches = (
                    intel.cached_roaches.amount
                    if intel.cached_roaches and hasattr(intel.cached_roaches, "amount")
                    else (
                        len(list(intel.cached_roaches))
                        if intel.cached_roaches and intel.cached_roaches.exists
                        else 0
                    )
                )
                hydralisks = (
                    intel.cached_hydralisks.amount
                    if intel.cached_hydralisks and hasattr(intel.cached_hydralisks, "amount")
                    else (
                        len(list(intel.cached_hydralisks))
                        if intel.cached_hydralisks and intel.cached_hydralisks.exists
                        else 0
                    )
                )
            else:
                zerglings = b.units(UnitTypeId.ZERGLING).amount
                roaches = b.units(UnitTypeId.ROACH).amount
                hydralisks = b.units(UnitTypeId.HYDRALISK).amount
            total_army_supply = b.supply_army if hasattr(b, "supply_army") else 0

            # 라바 확인
            # 🚀 성능 최적화: 캐시된 larva 사용
            intel = getattr(b, "intel", None)
            if intel and intel.cached_larva is not None:
                larvae = intel.cached_larva
            else:
                larvae = b.larva

            if not larvae or not larvae.exists:
                return False

            # 1. 상대 공격 준비 상태 감지
            enemy_attacking_soon = False
            try:
                # 적 유닛이 본진 근처(반경 50)에 있는지 확인
                if hasattr(b, "enemy_units") and b.enemy_units.exists:
                    townhall_positions = [th.position for th in b.townhalls]
                    if townhall_positions:
                        # 본진 근처 적 유닛 확인
                        near_enemies = b.enemy_units.filter(
                            lambda u: any(u.distance_to(base) < 50 for base in townhall_positions)
                        )
                        if near_enemies.exists:
                            enemy_attacking_soon = True

                # 적 건물이 본진 근처에 있는지 확인 (프록시 건물)
                if hasattr(b, "enemy_structures") and b.enemy_structures.exists:
                    townhall_positions = [th.position for th in b.townhalls]
                    if townhall_positions:
                        near_enemy_structures = b.enemy_structures.filter(
                            lambda s: any(s.distance_to(base) < 40 for base in townhall_positions)
                        )
                        if near_enemy_structures.exists:
                            enemy_attacking_soon = True
            except Exception:
                pass

            # 2. 최소 방어 병력 계산 (본진 방어 가능한 수준)
            # 게임 시간과 상대 종족에 따라 최소 방어 병력 결정
            min_defense_supply = 20  # 기본 최소 방어 병력 (서플라이 기준)

            # 게임 시간에 따라 최소 방어 병력 증가
            if b.time > 300:  # 5분 이후
                min_defense_supply = 40
            if b.time > 600:  # 10분 이후
                min_defense_supply = 60

            # 상대가 공격 준비 중이면 더 많은 병력 필요
            if enemy_attacking_soon:
                min_defense_supply = max(min_defense_supply, 50)

            # 3. 미네랄이 많이 쌓였거나 방어 병력이 부족하면 병력 생산
            mineral_threshold = 800  # 미네랄 800 이상이면 병력 생산 강화
            needs_army_production = False

            if b.minerals >= mineral_threshold:
                # 미네랄이 많이 쌓였으면 병력 생산
                needs_army_production = True
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    print(
                        f"[DEFENSE ARMY] [{int(b.time)}s] High minerals ({int(b.minerals)}M) - Producing defensive army"
                    )

            if total_army_supply < min_defense_supply:
                # 방어 병력이 부족하면 병력 생산
                needs_army_production = True
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    print(
                        f"[DEFENSE ARMY] [{int(b.time)}s] Low army supply ({total_army_supply}/{min_defense_supply}) - Building defense"
                    )

            if not needs_army_production:
                return False

            # 4. 병력 생산 (우선순위: 히드라 > 바퀴 > 저글링)
            # 히드라 둥지가 있으면 히드라 우선 생산
            hydra_dens = [s for s in b.structures(UnitTypeId.HYDRALISKDEN) if s.is_ready]
            if hydra_dens and hydralisks < 15:
                if b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                    if larvae and len(larvae) > 0:
                        random.choice(larvae).train(UnitTypeId.HYDRALISK)
                        return True

            # 바퀴 소굴이 있으면 바퀴 생산
            roach_warrens = [s for s in b.structures(UnitTypeId.ROACHWARREN) if s.is_ready]
            if roach_warrens and roaches < 20:
                if b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
                    if larvae and len(larvae) > 0:
                        random.choice(larvae).train(UnitTypeId.ROACH)
                        return True

            # 산란못이 있으면 저글링 생산
            spawning_pools = [s for s in b.structures(UnitTypeId.SPAWNINGPOOL) if s.is_ready]
            if spawning_pools and zerglings < 40:  # 저글링은 40마리(20쌍)까지 유지
                if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
                    if larvae and len(larvae) > 0:
                        random.choice(larvae).train(UnitTypeId.ZERGLING)
                        return True

        except Exception as e:
            # 에러 발생 시 조용히 무시
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 100 == 0:
                print(f"[WARNING] _maintain_defensive_army error: {e}")

        return False

    # 4️⃣ Adaptive unit production logic (Context-aware Emergency Production)
    async def _produce_emergency_units(self) -> bool:
        """
        Adaptive unit production logic based on game state

        산란못이 완성되었고 저글링이 부족하면 일벌레보다 저글링 우선!
        바퀴 소굴이 있으면 바퀴 생산

        Returns:
            bool: 공격 유닛을 생산했으면 True
        """
        b = self.bot

        # 🚀 성능 최적화: 캐시된 larva 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_larva is not None:
            larvae = intel.cached_larva
        else:
            larvae = b.larva

        if not larvae or not larvae.exists:
            return False

        # 인구수 체크 (대군주 최우선) - 언제나 최우선
        if b.supply_left < 4 and not b.already_pending(UnitTypeId.OVERLORD):
            if b.can_afford(UnitTypeId.OVERLORD):
                ready_larvae = larvae.ready.idle if hasattr(larvae, "ready") else larvae
                if ready_larvae.exists:
                    ready_larvae.random.train(UnitTypeId.OVERLORD)
                    return True

        # 상성 기반 맞춤 생산 (정찰 정보 활용)
        if hasattr(b, "scout") and b.scout:
            comp = b.scout.enemy_composition

            # 1. Adaptive counter: If enemy is building air units (void rays, etc.) -> Consider hydralisks/queens
            if comp.get("voidrays", 0) > 0:
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_hydralisk_dens is not None:
                    hydra_dens = (
                        list(intel.cached_hydralisk_dens)
                        if intel.cached_hydralisk_dens.exists
                        else []
                    )
                else:
                    hydra_dens = [s for s in b.structures(UnitTypeId.HYDRALISKDEN) if s.is_ready]
                if hydra_dens:
                    if b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                        if larvae and len(larvae) > 0:
                            random.choice(larvae).train(UnitTypeId.HYDRALISK)
                            return True

            # 2. 적이 해병(Marine) 위주라면? -> 맹독충 변태 (40% 비중)
            marines = comp.get("marines", 0)
            if marines > 10:
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_baneling_nests is not None:
                    baneling_nests = (
                        list(intel.cached_baneling_nests)
                        if intel.cached_baneling_nests.exists
                        else []
                    )
                else:
                    baneling_nests = [
                        s for s in b.structures(UnitTypeId.BANELINGNEST) if s.is_ready
                    ]
                if baneling_nests:
                    zerglings = b.units(UnitTypeId.ZERGLING)
                    if zerglings.exists:
                        # Increase baneling production to 40% ratio vs Terran Bio
                        # Convert more zerglings to banelings (up to 40% of zergling count)
                        # 🚀 성능 최적화: .amount 속성 사용 (리스트 변환 불필요)
                        zergling_count = (
                            zerglings.amount
                            if hasattr(zerglings, "amount")
                            else len(list(zerglings))
                        )
                        target_banelings = int(zergling_count * 0.4)
                        current_banelings = b.units(UnitTypeId.BANELING).amount
                        needed_banelings = max(0, target_banelings - current_banelings)

                        if needed_banelings > 0:
                            for zergling in zerglings[: min(needed_banelings, len(zerglings))]:
                                if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                                    try:
                                        zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                        print(
                                            f"[EVOLUTION] Unit Composition: Morphing Zergling to Baneling vs Terran Bio (Marines: {marines}, Target: 40% ratio)"
                                        )
                                        return True
                                    except Exception:
                                        pass

            # 3. 적이 공성전차/거신을 많이 뽑는다면? -> 뮤탈리스크/궤멸충 (Mech 대응)
            tanks = comp.get("tanks", 0)
            colossi = comp.get("colossi", 0)
            if tanks > 2 or colossi > 0:
                # Terran Mech detected - prioritize Ravagers and Mutalisks
                # Ravagers for Corrosive Bile vs Siege Tanks
                roach_warrens = [s for s in b.structures(UnitTypeId.ROACHWARREN) if s.is_ready]
                if roach_warrens:
                    roaches = b.units(UnitTypeId.ROACH)
                    if roaches.exists:
                        # Convert up to 30% of roaches to ravagers vs mech
                        target_ravagers = int(len(roaches) * 0.3)
                        current_ravagers = b.units(UnitTypeId.RAVAGER).amount
                        needed_ravagers = max(0, target_ravagers - current_ravagers)

                        if needed_ravagers > 0:
                            for roach in roaches[: min(needed_ravagers, len(roaches))]:
                                if b.can_afford(AbilityId.MORPHTORAVAGER_RAVAGER):
                                    try:
                                        roach(AbilityId.MORPHTORAVAGER_RAVAGER)
                                        print(
                                            f"[EVOLUTION] Unit Composition: Morphing Roach to Ravager vs Terran Mech (Tanks: {tanks})"
                                        )
                                        return True
                                    except Exception:
                                        pass

                # Mutalisks for air mobility vs Siege Tanks
                spires = [s for s in b.structures(UnitTypeId.SPIRE) if s.is_ready]
                if spires:
                    if b.can_afford(UnitTypeId.MUTALISK) and b.supply_left >= 2:
                        if larvae and len(larvae) > 0:
                            try:
                                random.choice(larvae).train(UnitTypeId.MUTALISK)
                                print(
                                    f"[EVOLUTION] Unit Composition: Producing Mutalisk vs Terran Mech (Tanks: {tanks})"
                                )
                                return True
                            except Exception:
                                pass

                # Hydralisks as backup vs mech
                hydra_dens = [s for s in b.structures(UnitTypeId.HYDRALISKDEN) if s.is_ready]
                if hydra_dens and b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                    if larvae and len(larvae) > 0:
                        try:
                            random.choice(larvae).train(UnitTypeId.HYDRALISK)
                            return True
                        except Exception:
                            pass

        # 유닛 비율 기반 생산 로직 (Balanced Production)
        # 라바 올인 방지: 유닛 비율을 체크하여 균형잡힌 생산

        # 유닛별 현재 수량
        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_zerglings is not None:
            zerglings = (
                intel.cached_zerglings.amount
                if hasattr(intel.cached_zerglings, "amount")
                else len(list(intel.cached_zerglings))
            )
        else:
            zerglings = b.units(UnitTypeId.ZERGLING).amount

        if intel and intel.cached_roaches is not None:
            roaches = (
                intel.cached_roaches.amount
                if hasattr(intel.cached_roaches, "amount")
                else len(list(intel.cached_roaches))
            )
        else:
            roaches = b.units(UnitTypeId.ROACH).amount

        if intel and intel.cached_hydralisks is not None:
            hydralisks = (
                intel.cached_hydralisks.amount
                if hasattr(intel.cached_hydralisks, "amount")
                else len(list(intel.cached_hydralisks))
            )
        else:
            hydralisks = b.units(UnitTypeId.HYDRALISK).amount

        # 로그 출력 (100 프레임마다) - Use print instead of logger to avoid buffer conflicts in parallel training
        current_iteration = getattr(b, "iteration", 0)
        if current_iteration % 100 == 0:
            try:
                # Safe print that won't cause buffer detachment errors
                time_str = f"[{int(b.time)}s]" if hasattr(b, "time") else "[?s]"
                print(
                    f"{time_str} [ARMY] Zerglings: {zerglings} | Roaches: {roaches} | Hydralisks: {hydralisks}"
                )
            except (ValueError, AttributeError, OSError):
                # Skip logging if buffer is detached (normal in parallel processes)
                pass

        # Priority 1: Produce Hydralisks aggressively when Hydralisk Den is available
        hydra_dens = [s for s in b.structures(UnitTypeId.HYDRALISKDEN) if s.is_ready]
        if hydra_dens:
            # Produce Hydralisks aggressively - maintain at least 10, up to 30+
            # Hydralisks are high-tech units with good range and damage
            if hydralisks < 30:
                if b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
                    if larvae and len(larvae) > 0:
                        random.choice(larvae).train(UnitTypeId.HYDRALISK)
                        return True

        # Priority 2: Produce Roaches when Roach Warren is available
        roach_warrens = [s for s in b.structures(UnitTypeId.ROACHWARREN) if s.is_ready]
        if roach_warrens:
            # More aggressive roach production - maintain at least 15, up to 40+
            # Roaches are tanky mid-tech units
            if roaches < 40:
                if b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
                    if larvae and len(larvae) > 0:
                        random.choice(larvae).train(UnitTypeId.ROACH)
                        return True

        # Priority 3: Produce Zerglings aggressively (increased limits)
        spawning_pools = [s for s in b.structures(UnitTypeId.SPAWNINGPOOL) if s.is_ready]
        if spawning_pools:
            # Significantly increased zergling production limits
            # Enemy nearby: up to 100 zerglings (50 pairs)
            # No enemy nearby: up to 80 zerglings (40 pairs)
            enemy_nearby = b.enemy_units.exists
            max_zerglings = 100 if enemy_nearby else 80  # Increased from 30/20 to 100/80

            if zerglings < max_zerglings:
                if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
                    if larvae and len(larvae) > 0:
                        random.choice(larvae).train(UnitTypeId.ZERGLING)
                        return True

        return False

    # 4.5️⃣ RESOURCE FLUSH: Aggressive Larva Usage (Priority #1 Fix)
    async def _flush_resources(self) -> bool:
        """
        Aggressively spend excess minerals by using all available larvae

        This prevents the "2,500 minerals but no army" problem by forcing
        unit production when minerals accumulate beyond 500.

        Logic:
        - Trigger: minerals >= 500 AND workers >= 16
        - Strategy: Spend ALL available larvae immediately
        - Priority: Most expensive units first (Hydralisk > Roach > Zergling)

        Returns:
            bool: True if any units were produced (resources flushed)
        """
        b = self.bot

        # Check trigger conditions - Use learned parameters instead of hardcoded values
        # Bot learns optimal mineral thresholds for resource flushing
        # CRITICAL: Lower thresholds for aggressive resource spending

        aggressive_flush_threshold = get_learned_parameter(
            "aggressive_flush_threshold", 500
        )  # NEW: Lower threshold (500)
        mineral_flush_threshold = get_learned_parameter("mineral_flush_threshold", 1000)
        flush_mode_threshold = get_learned_parameter(
            "flush_mode_threshold", 1500
        )  # NEW: Flush mode threshold
        emergency_flush_threshold = get_learned_parameter("emergency_flush_threshold", 2000)
        extreme_emergency_threshold = get_learned_parameter("extreme_emergency_threshold", 3000)

        # NEW: Intelligent resource consumption modes
        aggressive_flush = b.minerals >= aggressive_flush_threshold  # 500+: Aggressive flush mode
        flush_mode = b.minerals >= flush_mode_threshold  # 1,500+: Flush mode (infinite production)
        emergency_flush = b.minerals >= emergency_flush_threshold
        extreme_emergency = b.minerals >= extreme_emergency_threshold

        # IMPROVED: Calculate larva generation rate vs mineral income rate
        # If minerals are accumulating faster than larvae can be used, prioritize macro hatchery
        try:
            # 🚀 성능 최적화: 캐시된 larva 사용
            intel = getattr(b, "intel", None)
            if intel and intel.cached_larva is not None:
                larvae = intel.cached_larva
            else:
                larvae = b.larva
            larva_count = (
                larvae.amount
                if hasattr(larvae, "amount")
                else (len(list(larvae)) if larvae.exists else 0)
            )

            # Estimate larva generation rate (3 per hatchery every 11 seconds)
            # 🚀 성능 최적화: .ready.amount 사용 (리스트 변환 불필요)
            intel = getattr(b, "intel", None)
            if intel and intel.cached_townhalls is not None:
                hatchery_count = (
                    intel.cached_townhalls.ready.amount
                    if hasattr(intel.cached_townhalls, "ready")
                    else len(list(intel.cached_townhalls))
                )
            else:
                hatchery_count = (
                    b.townhalls.ready.amount
                    if hasattr(b.townhalls, "ready")
                    else len(list(b.townhalls.ready))
                )
            larva_generation_rate = (hatchery_count * 3) / 11.0  # larvae per second

            # Estimate mineral income rate (rough estimate: 50 per worker per minute = 0.83 per second)
            # 🚀 성능 최적화: .filter() 사용 (리스트 컴프리헨션보다 빠름)
            if intel and intel.cached_workers is not None:
                gathering_workers = intel.cached_workers.filter(lambda w: w.is_gathering)
                worker_count = (
                    gathering_workers.amount
                    if hasattr(gathering_workers, "amount")
                    else len(list(gathering_workers))
                )
            else:
                gathering_workers = b.workers.filter(lambda w: w.is_gathering)
                worker_count = (
                    gathering_workers.amount
                    if hasattr(gathering_workers, "amount")
                    else len(list(gathering_workers))
                )
            estimated_mineral_income = worker_count * 0.83  # minerals per second

            # If mineral income exceeds what we can spend with current larvae, prioritize macro hatchery
            # Each larva can produce ~50-100 minerals worth of units
            mineral_spending_capacity = larva_count * 75  # Average unit cost

            # If we have more than 2x spending capacity in minerals, prioritize macro hatchery
            if b.minerals > mineral_spending_capacity * 2 and larva_count < 5:
                # Force macro hatchery construction even if below threshold
                if (
                    b.can_afford(UnitTypeId.HATCHERY)
                    and b.already_pending(UnitTypeId.HATCHERY) == 0
                ):
                    if await self._build_macro_hatchery():
                        return True  # Return early if macro hatchery construction started
        except Exception:
            pass  # Silently fail if calculation fails

        # CRITICAL: If minerals exceed extreme emergency threshold, force production immediately
        # This prevents the "5000+ minerals but 0 army" problem
        if extreme_emergency:
            # Force production mode - ignore tech building construction
            self.current_mode = "PRODUCTION"
            # Log emergency status (reduced chat frequency for CPU optimization)
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 100 == 0:
                print(
                    f"[EMERGENCY FLUSH] [{int(b.time)}s] EXTREME EMERGENCY: {b.minerals} minerals, {b.supply_army} army supply - FORCING PRODUCTION"
                )
                # 🚀 PERFORMANCE: Reduced chat frequency from 100 to 500 frames (~22 seconds)
                if current_iteration % 500 == 0:
                    try:
                        await b.chat_send(
                            f"🔥 [긴급] 미네랄 {int(b.minerals)}원 쌓임! 병력 생산 최우선!"
                        )
                    except Exception:
                        pass

            # PANIC MODE: If no larvae available, prioritize macro hatchery construction
            try:
                # 🚀 성능 최적화: 캐시된 larva 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_larva is not None:
                    larvae = intel.cached_larva
                else:
                    larvae = b.larva
                if not larvae or len(larvae) == 0:
                    # No larvae available - build macro hatchery immediately
                    # This is the highest priority when minerals exceed 3000
                    if (
                        b.can_afford(UnitTypeId.HATCHERY)
                        and b.already_pending(UnitTypeId.HATCHERY) == 0
                    ):
                        # Force macro hatchery construction
                        await self._build_macro_hatchery()
                        return True  # Return early to prioritize hatchery construction
            except Exception:
                pass

            # PANIC MODE: Build defensive structures (Spine Crawlers) to consume minerals
            # This helps when larvae are limited but minerals are excessive
            if b.minerals >= 4000:  # Even more extreme threshold
                try:
                    # Check if we can build spine crawlers
                    spawning_pools = [
                        s for s in b.structures(UnitTypeId.SPAWNINGPOOL) if s.is_ready
                    ]
                    if spawning_pools and b.can_afford(UnitTypeId.SPINECRAWLER):
                        # Build spine crawlers near townhalls for defense
                        for th in b.townhalls:
                            if b.structures(UnitTypeId.SPINECRAWLER).closer_than(10, th).amount < 2:
                                # Find placement near townhall
                                try:

                                    spine_pos = th.position.offset(Point2((5, 5)))
                                    await b.build(UnitTypeId.SPINECRAWLER, near=spine_pos)
                                    print(
                                        f"[PANIC MODE] Building Spine Crawler to consume {b.minerals} minerals"
                                    )
                                    return True  # Return to prioritize structure construction
                                except Exception:
                                    continue
                except Exception:
                    pass

        # NEW: Flush mode (1,500+) - Force infinite production if larvae available
        if flush_mode and not emergency_flush and not extreme_emergency:
            # In flush mode, prioritize unit production over everything
            self.current_mode = "PRODUCTION"

        # CRITICAL: Lower threshold for aggressive resource spending (500+)
        if (
            not aggressive_flush
            and not flush_mode
            and not emergency_flush
            and not extreme_emergency
        ):
            return False

        # Get worker count safely - Use IntelManager cache to avoid redundant queries
        try:
            intel = getattr(b, "intel", None)
            if intel and intel.cached_workers is not None:
                workers = intel.cached_workers
                worker_count = workers.amount if hasattr(workers, "amount") else len(list(workers))
            else:
                # Fallback: direct access if intel cache not available
                workers = [w for w in b.workers] if b.workers.exists else []
                worker_count = len(workers)
        except Exception:
            worker_count = 0

        # Only flush if we have enough workers (prevent economy collapse)
        # 하지만 긴급 상황(미네랄 2000+)이면 일꾼이 12명 이상이면 병력 생산
        # EXTREME EMERGENCY (미네랄 3000+): 일꾼이 10명 이상이면 무조건 병력 생산
        # AGGRESSIVE FLUSH (미네랄 500+): 일꾼이 14명 이상이면 병력 생산 (더 낮은 임계값)
        if extreme_emergency:
            if worker_count < 10:
                return False
        elif emergency_flush:
            if worker_count < 12:
                return False
        elif aggressive_flush:
            # Aggressive flush mode (500+ minerals): Lower worker requirement
            if worker_count < 14:
                return False
        else:
            if worker_count < 16:
                return False

        # Get all available larvae
        # 🚀 성능 최적화: IntelManager 캐시 사용
        try:
            intel = getattr(b, "intel", None)
            if intel and intel.cached_larva is not None:
                larvae = intel.cached_larva
                larva_count = (
                    larvae.amount
                    if hasattr(larvae, "amount")
                    else (len(list(larvae)) if larvae.exists else 0)
                )
            else:
                # Fallback: 직접 접근
                larvae = b.larva
                larva_count = (
                    larvae.amount
                    if hasattr(larvae, "amount")
                    else (len(list(larvae)) if larvae.exists else 0)
                )

            # CRITICAL: If no larvae and minerals are high, prioritize macro hatchery
            if not larvae or larva_count == 0:
                # No larvae available - build macro hatchery immediately if minerals are high
                if b.minerals >= aggressive_flush_threshold and b.can_afford(UnitTypeId.HATCHERY):
                    if await self._build_macro_hatchery():
                        return True  # Macro hatchery construction started
                return False
        except Exception:
            return False

        # Check supply - don't flush if supply blocked (but allow overlord production)
        if b.supply_left < 2:
            # If supply blocked but minerals are high, try to produce overlord
            if b.minerals >= aggressive_flush_threshold and b.can_afford(UnitTypeId.OVERLORD):
                if larvae and len(larvae) > 0:
                    try:

                        random.choice(larvae).train(UnitTypeId.OVERLORD)
                        return True  # Overlord produced
                    except Exception:
                        pass
            return False

        # Track how many units we produce
        units_produced = 0
        minerals_before = b.minerals

        # CRITICAL: In extreme emergency, prioritize unit production over everything
        # Force production mode to prevent tech building construction
        if extreme_emergency:
            self.current_mode = "PRODUCTION"

        # Priority order: Most expensive units first
        # This maximizes resource consumption efficiency
        # Also consider enemy composition for better unit selection
        unit_priority = []

        # Check enemy composition for smart unit selection
        enemy_comp = {}
        if hasattr(b, "scout") and b.scout:
            enemy_comp = getattr(b.scout, "enemy_composition", {})

        marines = enemy_comp.get("marines", 0)
        tanks = enemy_comp.get("tanks", 0)

        # Terran Bio (Marines/Medivacs): Prioritize Banelings and Hydralisks
        if marines > 10 and tanks < 3:
            # Bio composition detected - prioritize splash damage
            baneling_nests = [s for s in b.structures(UnitTypeId.BANELINGNEST) if s.is_ready]
            if baneling_nests:
                # Try to morph zerglings to banelings first
                zerglings = b.units(UnitTypeId.ZERGLING)
                if zerglings.exists and b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                    for zergling in zerglings[: min(5, len(zerglings))]:
                        try:
                            zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                            units_produced += 1
                        except Exception:
                            pass
                # Then prioritize Hydralisks for range
                unit_priority = [
                    UnitTypeId.HYDRALISK,  # Range + splash vs bio
                    UnitTypeId.ROACH,  # Tanky
                    UnitTypeId.ZERGLING,  # For baneling morphing
                ]
            else:
                unit_priority = [
                    UnitTypeId.HYDRALISK,  # Range advantage vs bio
                    UnitTypeId.ROACH,
                    UnitTypeId.ZERGLING,
                ]
        # Terran Mech (Siege Tanks): Prioritize Ravagers and Mutalisks
        elif tanks > 2:
            # Mech composition detected - prioritize Ravagers and Mutalisks
            unit_priority = [
                UnitTypeId.MUTALISK,  # Air mobility vs tanks
                UnitTypeId.ROACH,  # For ravager morphing
                UnitTypeId.HYDRALISK,  # Range
            ]
        else:
            # Default: Most expensive units first
            unit_priority = [
                UnitTypeId.HYDRALISK,  # 100/50 - Most expensive
                UnitTypeId.ROACH,  # 75/25
                UnitTypeId.ZERGLING,  # 50/0 - Cheapest but still useful
            ]

        # Try to produce units with each available larva
        for larva in larvae:
            if not larva.is_ready:
                continue

            # Try each unit type in priority order
            produced = False
            for unit_type in unit_priority:
                # Check if we can afford this unit
                if not b.can_afford(unit_type):
                    continue

                # Check if required building exists
                required_building = self._get_required_building(unit_type)
                if required_building:
                    required_structures = [s for s in b.structures(required_building) if s.is_ready]
                    if not required_structures:
                        # 긴급 상황: 건물이 없어도 저글링은 생산 가능 (산란못만 있으면 됨)
                        if emergency_flush and unit_type == UnitTypeId.ZERGLING:
                            spawning_pools = [
                                s for s in b.structures(UnitTypeId.SPAWNINGPOOL) if s.is_ready
                            ]
                            if spawning_pools:
                                # 산란못이 있으면 저글링 생산 가능
                                pass
                            else:
                                continue
                        else:
                            continue

                # Check supply requirements
                supply_cost = 2 if unit_type != UnitTypeId.OVERLORD else 8
                if b.supply_left < supply_cost:
                    # 긴급 상황: 인구수 막힘이면 대군주 생산 시도
                    if emergency_flush and b.supply_left < 2:
                        if b.can_afford(UnitTypeId.OVERLORD) and b.supply_left >= 1:
                            try:
                                larva.train(UnitTypeId.OVERLORD)
                                units_produced += 1
                                produced = True
                                break
                            except Exception:
                                pass
                    continue

                # Produce the unit!
                try:
                    larva.train(unit_type)
                    units_produced += 1
                    produced = True
                    break  # Move to next larva
                except Exception:
                    # If training fails, try next unit type
                    continue

            # If we couldn't produce anything with this larva, continue to next
            if not produced:
                continue

        # Log if we actually produced units
        if units_produced > 0:
            minerals_spent = minerals_before - b.minerals
            log_msg = f"[EVOLUTION] Resource Flush Triggered: Produced {units_produced} units, spent {minerals_spent} minerals (Minerals: {minerals_before} -> {b.minerals})"
            print(log_msg)

            # 봇이 자신의 판단을 채팅으로 설명 (빈도 감소로 CPU 부하 감소)
            current_iteration = getattr(b, "iteration", 0)
            # 🚀 PERFORMANCE: Reduced chat frequency from every flush to 500 frames (~22 seconds)
            if current_iteration % 500 == 0:
                try:
                    mood = (
                        "🔥 긴급"
                        if extreme_emergency
                        else (
                            "🔥 공격적"
                            if emergency_flush
                            else ("⚡ 적극적" if aggressive_flush else "💰 경제적")
                        )
                    )
                    await b.chat_send(
                        f"{mood} [자원 관리] 자원이 넘쳐납니다({minerals_before}M)! {units_produced}기 병력을 생산했습니다. (현재: {b.minerals}M, 병력: {b.supply_army})"
                    )
                except Exception:
                    pass

            # Also log to file if possible
            try:

                if not logging.getLogger().handlers:
                    logging.basicConfig(
                        filename="training_debug.log",
                        level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        filemode="a",
                    )
                logging.info(log_msg)
            except Exception:
                pass  # Silently fail if logging setup fails

            return True

        return False

    # 4.5.5️⃣ AGGRESSIVE UNIT PRODUCTION: Always produce units when possible
    async def _aggressive_unit_production(self) -> bool:
        """
        Aggressively produce combat units whenever resources and larvae are available

        This function ensures continuous unit production by:
        1. Checking for available larvae
        2. Checking for available resources
        3. Producing the best affordable unit immediately

        This prevents resource accumulation and ensures army is always growing.

        Returns:
            bool: True if any units were produced
        """
        b = self.bot

        # Get available larvae
        # 🚀 성능 최적화: IntelManager 캐시 사용
        try:
            intel = getattr(b, "intel", None)
            if intel and intel.cached_larva is not None:
                larvae = (
                    intel.cached_larva.ready
                    if hasattr(intel.cached_larva, "ready")
                    else intel.cached_larva
                )
                if not larvae.exists:
                    return False
            else:
                # Fallback: 직접 접근
                larvae = [u for u in b.units(UnitTypeId.LARVA) if u.is_ready]
                if not larvae or len(larvae) == 0:
                    return False
        except Exception:
            return False

        # Check if we have enough resources to produce units
        # Lower threshold: produce units even with minimal resources
        if b.minerals < 50:  # Minimum for Zergling
            return False

        # Check supply - don't produce if supply blocked (unless we can produce overlord)
        if b.supply_left < 2:
            # Try to produce overlord if we can afford it
            if b.can_afford(UnitTypeId.OVERLORD) and b.supply_left >= 1:
                try:

                    random.choice(larvae).train(UnitTypeId.OVERLORD)
                    return True
                except Exception:
                    pass
            return False

        # Priority order: Produce the best affordable unit
        # Check what buildings we have to determine what units we can produce
        spawning_pools = [s for s in b.structures(UnitTypeId.SPAWNINGPOOL) if s.is_ready]
        roach_warrens = [s for s in b.structures(UnitTypeId.ROACHWARREN) if s.is_ready]
        hydra_dens = [s for s in b.structures(UnitTypeId.HYDRALISKDEN) if s.is_ready]
        spires = [s for s in b.structures(UnitTypeId.SPIRE) if s.is_ready]

        # Build unit priority list based on available buildings
        unit_priority = []

        if hydra_dens and b.can_afford(UnitTypeId.HYDRALISK):
            unit_priority.append(UnitTypeId.HYDRALISK)

        if roach_warrens and b.can_afford(UnitTypeId.ROACH):
            unit_priority.append(UnitTypeId.ROACH)

        if spawning_pools and b.can_afford(UnitTypeId.ZERGLING):
            unit_priority.append(UnitTypeId.ZERGLING)

        # If no buildings available, return False (can't produce combat units)
        if not unit_priority:
            return False

        # Try to produce units with available larvae
        units_produced = 0
        for larva in larvae:
            if not larva.is_ready:
                continue

            produced = False
            for unit_type in unit_priority:
                if not b.can_afford(unit_type):
                    continue

                # Check supply
                supply_cost = 2 if unit_type != UnitTypeId.OVERLORD else 8
                if b.supply_left < supply_cost:
                    continue

                # Produce the unit
                try:
                    larva.train(unit_type)
                    units_produced += 1
                    produced = True
                    break
                except Exception:
                    continue

            if produced:
                continue

        # Log if units were produced
        if units_produced > 0:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 100 == 0:  # Log every ~5 seconds
                print(
                    f"[AGGRESSIVE PRODUCTION] [{int(b.time)}s] Produced {units_produced} units (Minerals: {b.minerals}, Supply: {b.supply_army}/{b.supply_cap})"
                )
            return True

        return False

    # 4.6️⃣ MACRO HATCHERY: 자율적 해처리 건설 (Autonomous Hatchery Construction)
    async def _build_macro_hatchery(self) -> bool:
        """
        봇이 스스로 판단하여 minerals >= 1000일 때 해처리 건설 (자율적 판단)

        Logic:
        - If minerals >= 1000, larva generation cannot keep up with income
        - Build macro hatchery in main base (not expansion) to increase larva production
        - This prevents mineral accumulation beyond 1000
        - IMPROVED: Also check larva count - if larva is low (< 3) and minerals >= 600, build macro hatchery

        Returns:
            bool: True if macro hatchery construction was started
        """
        b = self.bot

        # Check trigger condition - Use learned parameter instead of hardcoded value

        macro_hatchery_threshold = get_learned_parameter("macro_hatchery_threshold", 1000)

        # IMPROVED: Check larva count - if larva is low, lower threshold for macro hatchery
        try:
            larvae = [u for u in b.units(UnitTypeId.LARVA)]
            larva_count = len(larvae) if larvae else 0
        except Exception:
            larva_count = 0

        # If larva count is low (< 3) and we have enough minerals (600+), build macro hatchery
        # This prevents larva shortage when producing 100+ units
        larva_shortage_threshold = 600  # Lower threshold when larva is low
        if larva_count < 3 and b.minerals >= larva_shortage_threshold:
            # Larva shortage detected - build macro hatchery immediately
            pass  # Continue to building logic below
        elif b.minerals < macro_hatchery_threshold:
            return False

        # Check if we already have enough hatcheries
        # 🚀 성능 최적화: IntelManager 캐시 사용
        try:
            intel = getattr(b, "intel", None)
            if intel and intel.cached_townhalls is not None:
                townhalls = intel.cached_townhalls
                hatchery_count = (
                    townhalls.amount
                    if hasattr(townhalls, "amount")
                    else (len(list(townhalls)) if townhalls.exists else 0)
                )
            else:
                # Fallback: 직접 접근
                if not b.townhalls.exists:
                    return False
                townhalls = b.townhalls
                hatchery_count = (
                    townhalls.amount if hasattr(townhalls, "amount") else len(list(townhalls))
                )
                if hatchery_count == 0:
                    return False
        except Exception:
            hatchery_count = 0

        # IMPROVED: Calculate optimal hatchery count based on unit production needs
        # With 100+ unit production limits, we need more hatcheries for larva generation
        # Each hatchery generates 3 larva every 11 seconds = ~0.27 larva/sec
        # To maintain 100+ units, we need at least 3-4 hatcheries (including macro hatcheries)
        try:
            # Count total army supply to determine hatchery needs
            army_supply = b.supply_army if hasattr(b, "supply_army") else 0
            # If army supply > 50, we need at least 3 hatcheries
            # If army supply > 100, we need at least 4 hatcheries
            min_hatcheries_needed = 2  # Base: main + natural
            if army_supply > 50:
                min_hatcheries_needed = 3
            if army_supply > 100:
                min_hatcheries_needed = 4

            # If we have fewer hatcheries than needed, lower threshold
            if hatchery_count < min_hatcheries_needed:
                # Lower threshold when hatcheries are insufficient
                macro_hatchery_threshold = min(
                    macro_hatchery_threshold, 700
                )  # Lower to 700 if hatcheries insufficient
        except Exception:
            pass

        # Don't build if already building a hatchery
        if b.already_pending(UnitTypeId.HATCHERY) > 0:
            return False

        # IMPROVED: Retry logic - prevent spam attempts after failures
        # If we failed recently (within last 5 seconds), wait before retrying
        current_time = int(b.time)
        if hasattr(self, "last_macro_hatchery_attempt_time"):
            time_since_last_attempt = current_time - self.last_macro_hatchery_attempt_time
            # If we failed multiple times, increase wait time (exponential backoff)
            if hasattr(self, "macro_hatchery_failures") and self.macro_hatchery_failures > 0:
                wait_time = min(5 + (self.macro_hatchery_failures * 2), 15)  # Max 15 seconds
                if time_since_last_attempt < wait_time:
                    return False  # Wait before retrying

        # Check if we can afford it
        if not b.can_afford(UnitTypeId.HATCHERY):
            return False

        # Get worker count - need at least 16 workers
        try:
            workers = [w for w in b.workers] if b.workers.exists else []
            worker_count = len(workers)
        except Exception:
            worker_count = 0

        if worker_count < 16:
            return False

        # Find main base hatchery for macro hatchery placement
        try:
            main_hatchery = None
            if b.townhalls.exists:
                # Find the oldest hatchery (main base)
                townhalls_list = [th for th in b.townhalls]
                if townhalls_list:
                    main_hatchery = min(townhalls_list, key=lambda th: th.tag)
        except Exception:
            return False

        if not main_hatchery:
            return False

        # Build macro hatchery near main base (offset to avoid blocking)
        try:
            # OPTIMIZED: Find idle worker with pathing verification (before finding location)
            # Prioritize idle workers over gathering workers for better pathing
            idle_workers = [w for w in b.workers if w.is_idle]
            gathering_workers = [w for w in b.workers if w.is_gathering]

            # Try idle workers first (better for construction)
            available_workers = idle_workers if idle_workers else gathering_workers
            if not available_workers:
                return False

            worker = available_workers[0]

            # IMPROVED: Use find_placement to find valid build location
            # This prevents "construction failed" errors by ensuring valid placement
            build_location = None

            # Method 1: Try to use find_placement API (most reliable)
            try:
                # Search for placement near main hatchery, 15-20 units away
                # This ensures adequate spacing and avoids blocking worker paths

                # Try multiple search strategies
                search_centers = []

                # Strategy 1: Towards map center (away from minerals)
                if hasattr(b, "game_info") and hasattr(b.game_info, "map_center"):
                    map_center = b.game_info.map_center
                    search_centers.append(main_hatchery.position.towards(map_center, 15))

                # Strategy 2: Expansion locations (if available)
                if hasattr(b, "expansion_locations"):
                    try:
                        expansion_locations = list(b.expansion_locations)
                        for exp_loc in expansion_locations:
                            # Check if location is far enough from existing hatcheries
                            too_close = False
                            for th in b.townhalls:
                                if th.position.distance_to(exp_loc) < 10:
                                    too_close = True
                                    break
                            if not too_close:
                                search_centers.append(exp_loc)
                    except Exception:
                        pass

                # Strategy 3: Offset positions (north-west, north-east, etc.)
                offsets = [
                    Point2((15, -15)),
                    Point2((-15, -15)),
                    Point2((15, 15)),
                    Point2((-15, 15)),
                ]
                for offset in offsets:
                    search_centers.append(main_hatchery.position.offset(offset))

                # Try each search center to find valid placement
                for search_center in search_centers:
                    try:
                        # Use find_placement to find valid build location
                        # max_distance=5 ensures we stay close to search center
                        # random_alternative=True helps find alternative if exact position blocked
                        placement = await b.find_placement(
                            UnitTypeId.HATCHERY,
                            near=search_center,
                            max_distance=5,
                            random_alternative=True,
                        )

                        if placement:
                            # OPTIMIZED: Verify worker can reach this location with pathing check
                            # Check if location is pathable and not blocked
                            if b.in_pathing_grid(placement):
                                # Additional check: Verify worker can path to this location
                                try:
                                    # Check if worker can reach the location (distance check)
                                    if worker.distance_to(placement) < 50:  # Reasonable distance
                                        build_location = placement
                                        break
                                except Exception:
                                    # If distance check fails, still use the location if pathable
                                    build_location = placement
                                    break
                    except Exception:
                        continue

            except Exception:
                pass

            # Method 2: Fallback to manual calculation if find_placement failed
            if not build_location:
                if hasattr(b, "game_info") and hasattr(b.game_info, "map_center"):
                    map_center = b.game_info.map_center
                    build_location = main_hatchery.position.towards(map_center, 15)
                else:
                    # Fallback: offset to north-west

                    build_location = main_hatchery.position.offset(Point2((15, -15)))

            # Verify we have a valid location
            if not build_location:
                return False

            # Verify worker can reach location (pathing check)
            try:
                if not b.in_pathing_grid(build_location):
                    return False
            except Exception:
                pass  # If pathing check fails, still try to build

            # Try to build macro hatchery
            build_success = False
            build_error = None

            # Check pending count BEFORE build attempt to verify construction started
            pending_before = b.already_pending(UnitTypeId.HATCHERY)

            try:
                # Use build API - worker assignment is handled automatically by python-sc2
                # Note: build_worker parameter is not supported in python-sc2 API
                # If worker needs to be used, move worker first, then build
                if worker and worker.distance_to(build_location) > 5:
                    # Move worker closer if too far away
                    worker.move(build_location)

                # Build hatchery at the specified location
                await b.build(UnitTypeId.HATCHERY, near=build_location)

                # CRITICAL: Verify construction actually started by checking pending count
                # Note: pending count update happens in next frame, so we check optimistically
                # We'll verify success in the next call to this method
                pending_after = b.already_pending(UnitTypeId.HATCHERY)
                if pending_after > pending_before:
                    build_success = True
                else:
                    # Build command might still succeed, but pending hasn't updated yet
                    # Set to True optimistically, but track for verification next frame
                    build_success = True  # Optimistic - will verify in next frame
                    # Note: If build actually failed, we'll detect it next frame when hatchery_count doesn't increase

            except Exception as e:
                # Build failed - track failure for retry logic
                build_error = str(e)
                build_success = False

                # Track consecutive failures
                if not hasattr(self, "macro_hatchery_failures"):
                    self.macro_hatchery_failures = 0
                self.macro_hatchery_failures += 1
                self.last_macro_hatchery_attempt_time = int(b.time)

                # Log failure only if it's a new failure pattern (not spam)
                if self.macro_hatchery_failures <= 3:  # Log first 3 failures
                    try:
                        worker_info = ""
                        if worker and build_location:
                            try:
                                worker_info = f" (Worker: {worker.tag}, Distance: {worker.distance_to(build_location):.1f})"
                            except Exception:
                                worker_info = f" (Worker: {worker.tag if hasattr(worker, 'tag') else 'Unknown'})"
                        location_info = (
                            f"Location: {build_location}" if build_location else "No location"
                        )
                        print(
                            f"[MACRO HATCHERY] Construction failed (attempt {self.macro_hatchery_failures}): {build_error[:100]}{worker_info}, {location_info}"
                        )
                    except Exception:
                        # Fallback: simple error message if formatting fails
                        print(
                            f"[MACRO HATCHERY] Construction failed (attempt {self.macro_hatchery_failures}): {build_error[:100]}"
                        )

                # If we've failed multiple times, try alternative strategies
                if self.macro_hatchery_failures >= 3:
                    # Try building at expansion location instead
                    if hasattr(b, "expansion_locations"):
                        try:
                            expansion_locations = list(b.expansion_locations)
                            for exp_loc in expansion_locations[
                                :3
                            ]:  # Try first 3 expansion locations
                                # Check if location is far enough from existing hatcheries
                                too_close = False
                                for th in b.townhalls:
                                    if th.position.distance_to(exp_loc) < 15:
                                        too_close = True
                                        break
                                if not too_close:
                                    # Try building at expansion location
                                    try:
                                        exp_placement = await b.find_placement(
                                            UnitTypeId.HATCHERY,
                                            near=exp_loc,
                                            max_distance=8,
                                            random_alternative=True,
                                        )
                                        if exp_placement and b.in_pathing_grid(exp_placement):
                                            # Verify pending count before alternative build
                                            alt_pending_before = b.already_pending(
                                                UnitTypeId.HATCHERY
                                            )
                                            await b.build(UnitTypeId.HATCHERY, near=exp_placement)
                                            # Verify construction started (pending count updates next frame, so check optimistically)
                                            alt_pending_after = b.already_pending(
                                                UnitTypeId.HATCHERY
                                            )
                                            if alt_pending_after > alt_pending_before:
                                                build_success = True
                                                print(
                                                    f"[MACRO HATCHERY] Successfully built at expansion location after {self.macro_hatchery_failures} failures"
                                                )
                                                self.macro_hatchery_failures = (
                                                    0  # Reset failure counter
                                                )
                                                break
                                            else:
                                                # Build might still succeed, but pending hasn't updated yet (next frame)
                                                # Set optimistically - will verify in next frame
                                                build_success = True
                                                self.macro_hatchery_failures = (
                                                    0  # Reset on optimistic success
                                                )
                                                break
                                    except Exception:
                                        continue
                        except Exception:
                            pass

                if not build_success:
                    return False

            # Verify construction actually started (check in next frame)
            # Update attempt tracking
            self.last_macro_hatchery_attempt_time = int(b.time)

            # NEW: Track attempt for success rate monitoring
            if not hasattr(self, "macro_hatchery_total_attempts"):
                self.macro_hatchery_total_attempts = 0
                self.macro_hatchery_successes = 0
                self.macro_hatchery_attempts_list = []

            self.macro_hatchery_total_attempts += 1
            attempt_record = {
                "time": int(b.time),
                "minerals": b.minerals,
                "hatchery_count": hatchery_count,
                "success": False,  # Will be updated in next frame if construction started
                "pending_before": b.already_pending(UnitTypeId.HATCHERY),
            }
            self.macro_hatchery_attempts_list.append(attempt_record)

            # NEW: Log macro event to analysis_hub for dashboard tracking
            # This connects production_manager to analysis_hub for data-driven evolution
            # 🚀 Updated: Use analysis_hub instead of battle_analyzer
            if hasattr(b, "analysis_hub") and b.analysis_hub:
                try:
                    b.analysis_hub.log_macro_event(success=build_success)
                except Exception:
                    pass  # Silently fail to avoid interrupting game flow
            # Backward compatibility: Also check battle_analyzer (if exists)
            elif hasattr(b, "battle_analyzer") and b.battle_analyzer:
                try:
                    b.battle_analyzer.log_macro_event(success=build_success)
                except Exception:
                    pass  # Silently fail to avoid interrupting game flow

            # Only log if we attempted to build (reduce log spam)
            # Check if construction actually started by checking pending count
            # Note: This check happens in next frame, so we log optimistically
            if build_success:
                # Reset failure counter on successful attempt
                if hasattr(self, "macro_hatchery_failures"):
                    self.macro_hatchery_failures = 0

                # Mark attempt as successful (will be verified in next frame)
                if self.macro_hatchery_attempts_list:
                    self.macro_hatchery_attempts_list[-1]["success"] = True
                    self.macro_hatchery_successes += 1

                # Only log once per attempt to reduce spam
                # Use a simple counter to limit logging frequency
                if not hasattr(self, "_last_macro_hatchery_log_frame"):
                    self._last_macro_hatchery_log_frame = 0

                # Log only every 100 frames (about every 4 seconds) to reduce spam
                # Also verify pending count increased (construction actually started)
                current_frame = getattr(b, "iteration", 0)
                pending_now = b.already_pending(UnitTypeId.HATCHERY)
                if current_frame - self._last_macro_hatchery_log_frame >= 100:
                    # Only log if we actually have a pending hatchery or this is a new attempt
                    if (
                        pending_now > 0
                        or not hasattr(self, "_last_pending_count")
                        or pending_now != self._last_pending_count
                    ):
                        log_msg = f"[EVOLUTION] Macro Hatchery Construction: Building macro hatchery (Minerals: {b.minerals}, Hatcheries: {hatchery_count}, Pending: {pending_now})"
                        print(log_msg)
                        self._last_pending_count = pending_now

                    # Log to file
                    try:

                        if not logging.getLogger().handlers:
                            logging.basicConfig(
                                filename="training_debug.log",
                                level=logging.INFO,
                                format="%(asctime)s [%(levelname)s] %(message)s",
                                filemode="a",
                            )
                        logging.info(log_msg)
                    except Exception:
                        pass

                    self._last_macro_hatchery_log_frame = current_frame

                return True

            return False

        except Exception as e:
            # Silently fail if construction fails
            return False

    # 5️⃣ 드론 생산
    async def _produce_drone(self) -> bool:
        """
        드론 생산 - 경제 관리 (드론 60마리까지 최우선)

        CRITICAL: Worker count below 16 is EMERGENCY - must recover immediately
        to prevent ECONOMY_COLLAPSE losses.

        Returns:
            bool: 드론을 생산했으면 True
        """
        b = self.bot

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_larva is not None:
            larvae = intel.cached_larva
            if not larvae.exists:
                return False
        else:
            # Fallback: 직접 접근
            larvae = [u for u in b.units(UnitTypeId.LARVA)]
            if not larvae:
                return False

        if intel and intel.cached_workers is not None:
            workers = intel.cached_workers
            worker_count = workers.amount if hasattr(workers, "amount") else len(list(workers))
        else:
            # Fallback: 직접 접근
            workers = [w for w in b.workers]
            worker_count = len(workers)

        # PRIORITY ZERO: Worker count below threshold (ABSOLUTE EMERGENCY - prevent total collapse)
        # CRITICAL: Use learned parameter for minimum mineral threshold
        # This prevents the "30 mineral curse" where bot can't afford drone
        # Uses learned parameter (default: 10, learned: priority_zero_threshold)

        minimum_mineral_threshold = get_learned_parameter("minimum_mineral_threshold", 50)

        if worker_count < self.priority_zero_threshold:
            if b.minerals < minimum_mineral_threshold:
                # Not enough minerals - return False to prevent other spending
                # Gas workers should be moved to minerals by gas_maximizer
                return False

            if b.can_afford(UnitTypeId.DRONE) and larvae and len(larvae) > 0:
                random.choice(larvae).train(UnitTypeId.DRONE)
                return True
            # If can't afford, still return False but this will be checked every frame
            # The bot should prioritize getting 50 minerals for a drone above all else
            return False

        # EMERGENCY PRIORITY: Worker count below 16 (CRITICAL - prevent economy collapse)
        # Ignore supply block if workers are critically low (produce overlord in parallel)
        if worker_count < 16:
            if b.can_afford(UnitTypeId.DRONE) and larvae and len(larvae) > 0:
                random.choice(larvae).train(UnitTypeId.DRONE)
                return True
            # If can't afford, skip supply check and return False (will try next frame)
            return False

        # 드론 60마리까지는 최우선 (수비 위주 운영)
        if worker_count < 60:
            # 인구수 여유만 체크
            if b.supply_left <= 2:
                return False

            if b.can_afford(UnitTypeId.DRONE) and larvae and len(larvae) > 0:
                random.choice(larvae).train(UnitTypeId.DRONE)
                return True

        # 드론 60마리 이후는 기존 로직
        if worker_count >= self.config.MAX_WORKERS:
            return False

        # 군대가 어느 정도 있을 때만 드론 추가 생산
        if b.supply_army < 10:
            return False

        # 인구수 여유 체크
        if b.supply_left <= 2:
            return False

        if b.can_afford(UnitTypeId.DRONE) and larvae and len(larvae) > 0:
            random.choice(larvae).train(UnitTypeId.DRONE)
            return True

        return False

    # 4️⃣ 군사 유닛 생산
    async def _produce_army(self, game_phase: GamePhase, build_plan: Optional[Dict] = None):
        """
        군사 유닛 생산

        생산 우선순위 (테크 기반):
            1. CounterPunchManager 우선순위 (상대 유닛 감지 시)
            2. 히드라리스크 (히드라 덴 필요)
            3. 로치 (로치 워렌 필요)
            4. 저글링 (기본)

        Args:
            game_phase: 현재 게임 단계
            build_plan: 적응형 빌드 계획 (선택적)
        """
        b = self.bot

        try:
            larvae = [u for u in b.units(UnitTypeId.LARVA)]
            if not larvae:
                return

            # 인구수 체크
            if b.supply_left < 2:
                return

            # CRITICAL: Larva Saving - 라바 30%는 테크 유닛 변태를 위해 보유
            # 상대방의 공격 의사가 확인되지 않았을 때 테크 유닛 변태를 위해 라바 일부 보유
            total_larvae = len(larvae)
            reserved_larvae_count = max(1, int(total_larvae * 0.3))  # 30% 보유

            # Check if enemy attack intent is detected
            enemy_attacking = False
            intel = getattr(b, "intel", None)
            if intel:
                # Check if enemy is attacking our bases
                if hasattr(intel, "signals") and isinstance(intel.signals, dict):
                    enemy_attacking = intel.signals.get("enemy_attacking_our_bases", False)

                # Check if we're under attack
                if hasattr(intel, "combat") and hasattr(intel.combat, "under_attack"):
                    if intel.combat.under_attack:
                        enemy_attacking = True

            # If enemy is attacking, use all larvae (no saving)
            # Otherwise, save 30% for tech unit morphing
            if enemy_attacking:
                # Emergency: Enemy attacking - use all larvae
                available_larvae = larvae
                reserved_larvae_count = 0
            else:
                # Normal: Save 30% for tech units (Roaches, Hydralisks)
                if total_larvae > reserved_larvae_count:
                    available_larvae = larvae[:-reserved_larvae_count]
                else:
                    available_larvae = []

            # If no available larvae (all reserved), don't produce
            if not available_larvae:
                return

            # Use available_larvae instead of larvae for the rest of the function
            larvae = available_larvae

            # 고급화 트리거: 저글링 비중이 과도하고 가스가 남으면 테크 유닛 우선
            force_high_tech = self._should_force_high_tech_production()
            if force_high_tech:
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 75 == 0:
                    print(
                        f"[TECH SHIFT] {int(b.time)}s | Zergling-heavy army detected; boosting high-tech production"
                    )

                # Counter-based unit selection when tech shift is triggered
                counter_unit = self._select_counter_unit_by_matchup()
                if counter_unit:
                    if await self._try_produce_unit(counter_unit, larvae):
                        if current_iteration % 75 == 0:
                            print(
                                f"[COUNTER PRODUCTION] {int(b.time)}s | Producing {counter_unit.name} to counter enemy composition"
                            )
                        return

            # CounterPunchManager 우선순위 확인 (카운터 전략이 활성화된 경우)
            counter_priority = []
            if hasattr(b, "counter_punch") and b.counter_punch:
                if hasattr(b.counter_punch, "get_train_priority"):
                    counter_priority = b.counter_punch.get_train_priority()  # type: ignore

            # 카운터 우선순위가 있으면 우선 적용
            if counter_priority:
                for unit_type in counter_priority:
                    if await self._try_produce_unit(unit_type, larvae):
                        return
                # 카운터 우선순위의 유닛을 모두 생산했으면 일반 생산으로 전환

            # 상대 테크 기반 맞춤형 유닛 조합 전환 (최우선) - 강제 트리거
            # CRITICAL: 반응성 강화 - 정찰에서 적의 기술 건물 발견 시 즉시 대응 유닛 생산 우선순위 최상단
            tech_based_units = await self._get_tech_based_unit_composition()
            if tech_based_units:
                # 강제 트리거: 최근에 테크가 감지되었으면 (30초 이내) 최우선 생산
                intel = getattr(b, "intel", None)
                scout = getattr(b, "scout", None)

                tech_detected_recently = False
                detection_time = 0.0

                # IntelManager에서 감지 시간 확인
                if intel and hasattr(intel, "enemy_tech_detected"):
                    detection_time = intel.enemy_tech_detected.get("detected_time", 0.0)
                    if detection_time > 0 and b.time - detection_time < 30.0:  # 30초 이내
                        tech_detected_recently = True

                # ScoutManager에서도 확인
                if not tech_detected_recently and scout and hasattr(scout, "enemy_tech_detected"):
                    detection_time = scout.enemy_tech_detected.get("detected_time", 0.0)
                    if detection_time > 0 and b.time - detection_time < 30.0:  # 30초 이내
                        tech_detected_recently = True

                # 강제 트리거: 최근 감지된 테크에 대해 즉시 대응 유닛 생산
                for unit_type in tech_based_units:
                    if await self._try_produce_unit(unit_type, larvae):
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 25 == 0:  # 더 자주 출력 (반응성 강화)
                            if tech_detected_recently:
                                print(
                                    f"[TECH COUNTER - FORCED TRIGGER] [{int(b.time)}s] IMMEDIATE: Producing {unit_type.name} (Tech detected {b.time - detection_time:.1f}s ago)"
                                )
                            else:
                                print(
                                    f"[TECH COUNTER] [{int(b.time)}s] Producing {unit_type.name} based on enemy tech"
                                )
                        return

            # Check if we should use aggressive build (6-pool) against this opponent
            use_aggressive_build = False
            is_eris_opponent = False

            # opponent_tracker merged into strategy_analyzer
            if hasattr(b, "strategy_analyzer") and b.strategy_analyzer:
                use_aggressive_build = b.strategy_analyzer.should_use_aggressive_build()
                # Check if opponent is Eris (top-ranked Zerg bot)
                current_opponent = getattr(b.strategy_analyzer, "current_opponent", None)
                if current_opponent and "eris" in current_opponent.lower():
                    is_eris_opponent = True

            # Eris 전용 특수 빌드: 빠른 맹독충 + 뮤탈리스크 테크
            if is_eris_opponent and b.time < 300:  # 초반 5분 동안
                # 맹독충 둥지 우선 건설
                # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                spawning_pools = list(b.structures(UnitTypeId.SPAWNINGPOOL).ready)
                if (
                    spawning_pools
                    and self._can_build_safely(UnitTypeId.BANELINGNEST, reserve_on_pass=True)
                    and b.can_afford(UnitTypeId.BANELINGNEST)
                ):
                    try:
                        # Use _try_build_structure for duplicate prevention
                        if await self._try_build_structure(
                            UnitTypeId.BANELINGNEST, near=spawning_pools[0].position
                        ):
                            print(f"[ERIS COUNTER] [{int(b.time)}s] 맹독충 둥지 건설 (Eris 대응)")
                    except Exception:
                        pass

                # 빠른 레어 테크 (뮤탈리스크 준비)
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_lairs is not None:
                    lairs = list(intel.cached_lairs) if intel.cached_lairs.exists else []
                else:
                    lairs = (
                        list(b.structures(UnitTypeId.LAIR).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                # 🚀 성능 최적화: IntelManager 캐시 사용
                if intel and intel.cached_townhalls is not None:
                    hatcheries = (
                        list(
                            intel.cached_townhalls.filter(
                                lambda th: th.type_id == UnitTypeId.HATCHERY
                            )
                        )
                        if intel.cached_townhalls.exists
                        else []
                    )
                else:
                    hatcheries = (
                        list(b.structures(UnitTypeId.HATCHERY)) if hasattr(b, "structures") else []
                    )
                if hatcheries and not lairs and b.time > 180 and b.can_afford(UnitTypeId.LAIR):
                    try:
                        if hatcheries:
                            await hatcheries[0].morph(UnitTypeId.LAIR)  # [FIX] Added await
                            print(f"[ERIS COUNTER] [{int(b.time)}s] 레어 변태 시작 (뮤탈 테크)")
                    except Exception:
                        pass

            # NOTE: Spawning Pool construction is now ONLY handled by EconomyManager
            # to prevent duplicate construction. ProductionManager only checks if
            # Spawning Pool is ready for unit production.

            # 6-pool aggressive build: Use existing spawning pool for zergling rush
            if use_aggressive_build and b.time < 120:  # Only in early game
                spawning_pools = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure
                    )
                )
                if spawning_pools:
                    pool = spawning_pools[0]
                    if pool.is_ready:
                        # Produce zerglings aggressively (6-pool rush)
                        if await self._try_produce_unit(UnitTypeId.ZERGLING, larvae):
                            return
                        return

            # 12못 올인 모드: 산란못 완성 후 저글링만 무한 생산
            if self.config.ALL_IN_12_POOL:
                spawning_pools = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure
                    )
                )
                if spawning_pools:
                    # 산란못이 완성되었으면 저글링만 생산
                    pool = spawning_pools[0]
                    if pool.is_ready:
                        # 저글링 생산 (가스나 다른 유닛 생산 안 함)
                        if await self._try_produce_unit(UnitTypeId.ZERGLING, larvae):
                            return
                        return

            # 일반 모드: 저글링 끊임없이 생산 + 테크 올라가면 히드라 주력
            # 고급화 트리거 시 테크 유닛을 먼저 시도하여 저글링 비중을 줄임
            if force_high_tech:
                if await self._try_produce_unit(UnitTypeId.HYDRALISK, larvae):
                    return
                if await self._try_produce_unit(UnitTypeId.ROACH, larvae):
                    return

            # 1. 저글링은 항상 생산 (인구수 여유 있을 때)
            if not force_high_tech and b.supply_left >= 4:  # 여유 있게 관리
                if await self._try_produce_unit(UnitTypeId.ZERGLING, larvae):
                    return

            # 2. Reactive production: Detect enemy air units and prepare counters
            # Check if enemy has air units or air tech buildings
            enemy_has_air = False
            if hasattr(b, "scout") and b.scout:
                enemy_has_air = b.scout.enemy_has_air

            # Also check enemy structures for air tech
            enemy_structures = getattr(b, "enemy_structures", [])
            for building in enemy_structures:
                if building.type_id in [
                    UnitTypeId.STARGATE,
                    UnitTypeId.STARPORT,
                    UnitTypeId.FUSIONCORE,
                ]:
                    enemy_has_air = True
                    break

            # If enemy going air: prioritize Hydralisks and Spore Crawlers
            # Tech building construction is now handled by _autonomous_tech_progression()
            # Only produce units if buildings already exist
            if enemy_has_air:
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_hydralisk_dens is not None:
                    hydra_dens = (
                        list(intel.cached_hydralisk_dens)
                        if intel.cached_hydralisk_dens.exists
                        else []
                    )
                else:
                    hydra_dens = (
                        list(b.structures(UnitTypeId.HYDRALISKDEN).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                if hydra_dens:
                    # Prioritize Hydralisk production
                    if await self._try_produce_unit(UnitTypeId.HYDRALISK, larvae):
                        return

                # Build Spore Crawlers for air defense (defensive structure, not tech building)
                if intel and intel.cached_evolution_chambers is not None:
                    evo_chambers_exist = (
                        intel.cached_evolution_chambers.exists
                        if intel.cached_evolution_chambers
                        else False
                    )
                else:
                    evo_chambers_exist = (
                        b.structures(UnitTypeId.EVOLUTIONCHAMBER).ready.exists
                        if hasattr(b, "structures")
                        else False
                    )

                if evo_chambers_exist:
                    # Check if we need more spore crawlers
                    if intel and intel.cached_spore_crawlers is not None:
                        spores = intel.cached_spore_crawlers
                    else:
                        spores = (
                            b.structures(UnitTypeId.SPORECRAWLER).ready
                            if hasattr(b, "structures")
                            else None
                        )
                    if (
                        spores and hasattr(spores, "amount") and spores.amount < 3
                    ):  # Build at least 3 spores
                        for th in b.townhalls.ready:
                            if b.can_afford(UnitTypeId.SPORECRAWLER):
                                # Build spore near townhall
                                await self._try_build_structure(
                                    UnitTypeId.SPORECRAWLER, near=th.position
                                )
                                return

            # Check if enemy is ground-focused: prepare Banelings/Roaches
            # Tech building construction is now handled by _autonomous_tech_progression()
            # Only produce units if buildings already exist
            else:
                # Enemy is ground-focused: prioritize Banelings and Roaches
                # Only produce units if buildings already exist
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_baneling_nests is not None:
                    baneling_nests = (
                        list(intel.cached_baneling_nests)
                        if intel.cached_baneling_nests.exists
                        else []
                    )
                else:
                    baneling_nests = (
                        list(b.structures(UnitTypeId.BANELINGNEST).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                if baneling_nests:
                    if intel and intel.cached_zerglings is not None:
                        zerglings = intel.cached_zerglings
                        zergling_count = (
                            zerglings.amount
                            if hasattr(zerglings, "amount")
                            else len(list(zerglings))
                        )
                    else:
                        zerglings = b.units(UnitTypeId.ZERGLING)
                        zergling_count = (
                            zerglings.amount
                            if hasattr(zerglings, "amount")
                            else len(list(zerglings))
                        )
                    if zergling_count >= 10:
                        # Morph zerglings to banelings if nest exists
                        pass  # Morphing logic is handled elsewhere

                # Produce Roaches if Roach Warren exists
                # 🚀 성능 최적화: IntelManager 캐시 사용
                if intel and intel.cached_roach_warrens is not None:
                    roach_warrens_existing = (
                        list(intel.cached_roach_warrens)
                        if intel.cached_roach_warrens.exists
                        else []
                    )
                    roach_warrens = (
                        list(intel.cached_roach_warrens)
                        if intel.cached_roach_warrens.exists
                        else []
                    )
                else:
                    roach_warrens_existing = (
                        list(b.structures(UnitTypeId.ROACHWARREN).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                    roach_warrens = (
                        list(b.structures(UnitTypeId.ROACHWARREN))
                        if hasattr(b, "structures")
                        else []
                    )

                if roach_warrens_existing:
                    # Roach production logic is handled below
                    pass

                # Produce Roaches for ground combat (enhanced: more aggressive roach production)
                ready_roach_warrens = [rw for rw in roach_warrens if rw.is_ready]
                if ready_roach_warrens:
                    # Check current roach count
                    if intel and intel.cached_roaches is not None:
                        roaches = intel.cached_roaches
                    else:
                        roaches = b.units(UnitTypeId.ROACH)
                    roach_count = (
                        roaches.amount if hasattr(roaches, "amount") else len(list(roaches))
                    )

                    # Produce roaches more aggressively (if we have less than 8 roaches)
                    if roach_count < 8:
                        if await self._try_produce_unit(UnitTypeId.ROACH, larvae):
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[ROACH] [{int(b.time)}s] Roach production started! (Current: {roach_count})"
                                )
                            return
                    # If we have enough roaches, still produce occasionally to maintain army
                    elif roach_count < 15 and b.supply_left >= 2:
                        if await self._try_produce_unit(UnitTypeId.ROACH, larvae):
                            return

                # Produce Banelings from Zerglings
                # 🚀 성능 최적화: IntelManager 캐시 사용
                if intel and intel.cached_baneling_nests is not None:
                    baneling_nests = (
                        list(intel.cached_baneling_nests)
                        if intel.cached_baneling_nests.exists
                        else []
                    )
                else:
                    baneling_nests = (
                        list(b.structures(UnitTypeId.BANELINGNEST).ready)
                        if hasattr(b, "structures")
                        else []
                    )
                if baneling_nests:
                    if intel and intel.cached_zerglings is not None:
                        zerglings_ready = [u for u in intel.cached_zerglings if u.is_ready]
                    else:
                        zerglings_ready = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_ready]
                    if zerglings_ready:
                        for zergling in zerglings_ready[:2]:  # Morph 2 at a time
                            if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                                zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                return

            # 2. 테크가 올라가면 히드라 주력 생산 (fallback)
            # 🚀 성능 최적화: IntelManager 캐시 사용
            intel = getattr(b, "intel", None)
            if intel and intel.cached_hydralisk_dens is not None:
                hydra_dens = (
                    list(intel.cached_hydralisk_dens) if intel.cached_hydralisk_dens.exists else []
                )
            else:
                hydra_dens = (
                    list(b.structures(UnitTypeId.HYDRALISKDEN).ready)
                    if hasattr(b, "structures")
                    else []
                )
            if hydra_dens:
                # Hydralisk production
                if await self._try_produce_unit(UnitTypeId.HYDRALISK, larvae):
                    return

            # 3. 반응형 테크 분기: 상대 종족에 따른 유닛 생산
            # Enhanced Lurker production for Division 2 ladder play
            # vs 프로토스: 링-히드라리스크-가시지옥(Lurker) - 강화된 버전
            if self.enemy_race == EnemyRace.PROTOSS:
                # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                lurker_dens = list(b.structures(UnitTypeId.LURKERDEN).ready)
                if lurker_dens:
                    # Check if we have Hydralisks to morph
                    # 🚀 성능 최적화: IntelManager 캐시 사용
                    intel = getattr(b, "intel", None)
                    if intel and intel.cached_hydralisks is not None:
                        hydralisks = [
                            u for u in intel.cached_hydralisks if u.is_ready and not u.is_burrowed
                        ]
                    else:
                        hydralisks = [
                            u
                            for u in b.units(UnitTypeId.HYDRALISK)
                            if u.is_ready and not u.is_burrowed
                        ]
                    if hydralisks:
                        # More aggressive Lurker morphing (up to 5 at a time for ladder)
                        for hydra in hydralisks[:5]:  # Increased from 3 to 5
                            if b.can_afford(AbilityId.MORPH_LURKER):
                                try:
                                    hydra(AbilityId.MORPH_LURKER)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(f"[LURKER] [{int(b.time)}s] Lurker morphing started!")
                                except:
                                    pass
                        return

            # vs 테란: Lurker도 효과적 (지상군 대응)
            elif self.enemy_race == EnemyRace.TERRAN:
                # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                lurker_dens = list(b.structures(UnitTypeId.LURKERDEN).ready)
                if lurker_dens and b.time > 300:  # 5분 이후
                    # 🚀 성능 최적화: IntelManager 캐시 사용
                    intel = getattr(b, "intel", None)
                    if intel and intel.cached_hydralisks is not None:
                        hydralisks = [
                            u for u in intel.cached_hydralisks if u.is_ready and not u.is_burrowed
                        ]
                    else:
                        hydralisks = [
                            u
                            for u in b.units(UnitTypeId.HYDRALISK)
                            if u.is_ready and not u.is_burrowed
                        ]
                    if hydralisks:
                        # Morph up to 3 Hydralisks to Lurkers for ground control
                        for hydra in hydralisks[:3]:
                            if b.can_afford(AbilityId.MORPH_LURKER):
                                try:
                                    hydra(AbilityId.MORPH_LURKER)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(
                                            f"[LURKER] [{int(b.time)}s] Lurker morphing vs Terran!"
                                        )
                                except:
                                    pass
                        return
            # vs 테란: 링-맹독충-뮤탈리스크 또는 링-맹독충-울트라리스크
            elif self.enemy_race == EnemyRace.TERRAN:
                # 맹독충 생산 (바네스팅 필요)
                # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                baneling_nests = list(b.structures(UnitTypeId.BANELINGNEST).ready)
                if baneling_nests:
                    zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_ready]
                    if zerglings:
                        for zergling in zerglings[:2]:  # 최대 2마리씩 변태
                            if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                                zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                return

                # 뮤탈리스크 생산 (스파이어 필요)
                # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                spires = list(b.structures(UnitTypeId.SPIRE).ready)
                if spires:
                    if await self._try_produce_unit(UnitTypeId.MUTALISK, larvae):
                        return

                # 울트라리스크 생산 (울트라리스크 동굴 필요)
                # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                ultralisk_caverns = list(b.structures(UnitTypeId.ULTRALISKCAVERN).ready)
                if ultralisk_caverns:
                    if await self._try_produce_unit(UnitTypeId.ULTRALISK, larvae):
                        return
            # vs 저그: 저글링-맹독충 초반 컨트롤 싸움 후 바퀴-궤멸충
            elif self.enemy_race == EnemyRace.ZERG:
                # 초반: 저글링-맹독충
                if b.time < 300:  # 5분 이전
                    # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                    baneling_nests = list(b.structures(UnitTypeId.BANELINGNEST).ready)
                    if baneling_nests:
                        # 🚀 성능 최적화: IntelManager 캐시 사용
                        intel = getattr(b, "intel", None)
                        if intel and intel.cached_zerglings is not None:
                            zerglings = intel.cached_zerglings
                        else:
                            zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_ready]
                        # Handle both Units object and list
                        zerglings_list = []
                        try:
                            # Check if it's a Units object (has 'exists' attribute)
                            if hasattr(zerglings, "exists") and not isinstance(zerglings, list):
                                if zerglings.exists:  # type: ignore
                                    zerglings_list = list(zerglings)[:2]
                            elif isinstance(zerglings, list):
                                if zerglings and len(zerglings) > 0:
                                    zerglings_list = zerglings[:2]
                        except Exception:
                            pass

                        for zergling in zerglings_list:
                            if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                                zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                return
                else:
                    # 중반 이후: 바퀴-궤멸충
                    # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                    roach_warrens = list(b.structures(UnitTypeId.ROACHWARREN).ready)
                    if roach_warrens:
                        if await self._try_produce_unit(UnitTypeId.ROACH, larvae):
                            return
                        # 궤멸충 변태
                        roaches = [u for u in b.units(UnitTypeId.ROACH) if u.is_ready]
                        if roaches:
                            for roach in roaches[:1]:  # 1마리씩 변태
                                if b.can_afford(AbilityId.MORPHTORAVAGER_RAVAGER):
                                    roach(AbilityId.MORPHTORAVAGER_RAVAGER)
                                    return

            # 4. 최종 유닛 생산 (상성 기반)
            if await self._produce_ultimate_units(larvae):
                return

            # 5. 상성 기반 유닛 선택 (히드라가 안 되면)
            # Curriculum Learning: 난이도가 낮을 때 기본 물량 중심으로 생산
            if self._should_use_basic_units():
                # VeryEasy, Easy 단계: 저글링 + 바퀴 중심 (복잡한 유닛 조합 피함)
                units_to_produce = [UnitTypeId.ZERGLING, UnitTypeId.ROACH]
            else:
                # Medium 이상: 정상적인 상성 기반 유닛 선택
                units_to_produce = self._get_counter_units(game_phase)

            if force_high_tech:
                # Push tech units to the front when zergling ratio is too high
                tech_priority = [UnitTypeId.HYDRALISK, UnitTypeId.ROACH]
                units_to_produce = tech_priority + [
                    u for u in units_to_produce if u not in tech_priority
                ]

            for unit_type in units_to_produce:
                if unit_type != UnitTypeId.ZERGLING:  # 저글링은 이미 위에서 처리
                    if await self._try_produce_unit(unit_type, larvae):
                        return
        except Exception as e:
            # 에러 발생 시 로그만 출력 (게임 중단 방지)
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _produce_army 오류: {e}")

    # 최종 유닛 생산 (울트라리스크, 무리 군주)
    async def _produce_ultimate_units(self, larvae) -> bool:
        """
        최종 유닛 생산 및 상성 활용

        Args:
            larvae: 사용 가능한 애벌레

        Returns:
            bool: 최종 유닛을 생산했으면 True
        """
        b = self.bot

        if not larvae or len(larvae) == 0:
            return False

        # 인구수 체크
        if b.supply_left < 2:
            return False

        # A. 상대가 지상군(해병, 추적자) 위주라면? -> 울트라리스크!
        ultralisk_caverns = b.structures(UnitTypeId.ULTRALISKCAVERN).ready
        if ultralisk_caverns.exists:
            ultralisks = b.units(UnitTypeId.ULTRALISK)
            if ultralisks.amount < 6:  # 6마리 정도면 지상 평정
                if b.can_afford(UnitTypeId.ULTRALISK) and b.supply_left >= 6:
                    if await self._try_produce_unit(UnitTypeId.ULTRALISK, larvae):
                        return True

        # B. 상대가 공성 전차나 방어 타워가 많다면? -> 무리 군주!
        # Fix: UnitTypeId.GREAT_SPIRE -> UnitTypeId.GREATERSPIRE (correct SC2 API naming)
        great_spires = b.structures(UnitTypeId.GREATERSPIRE).ready
        if great_spires.exists:
            broodlords = b.units(UnitTypeId.BROODLORD)
            if broodlords.amount < 5:
                corruptors = b.units(UnitTypeId.CORRUPTOR)
                if corruptors.exists:
                    for corruptor in corruptors[: min(2, len(corruptors))]:
                        # Try to morph to Broodlord (check for correct ability ID)
                        morph_ability = None
                        if hasattr(AbilityId, "MORPHTOBROODLORD"):
                            morph_ability = AbilityId.MORPHTOBROODLORD  # type: ignore
                        elif hasattr(AbilityId, "MORPH_BROODLORD"):
                            morph_ability = AbilityId.MORPH_BROODLORD  # type: ignore

                        if morph_ability and b.can_afford(morph_ability):
                            try:
                                corruptor(morph_ability)
                                return True
                            except Exception:
                                continue

        return False

    async def _get_tech_based_unit_composition(self) -> List[UnitTypeId]:
        """
        상대 테크 기반 맞춤형 유닛 조합 선택

        정찰로 감지된 적 건물에 따라 유닛 생산 우선순위를 자동으로 변경합니다.

        Returns:
            List[UnitTypeId]: 생산할 유닛 목록 (우선순위 순), 없으면 빈 리스트
        """
        b = self.bot

        # IntelManager 또는 ScoutManager에서 테크 정보 가져오기
        tech_info = {}

        # 1. bot.enemy_tech에서 직접 가져오기 (가장 빠름)
        if hasattr(b, "enemy_tech"):
            tech_type = getattr(b, "enemy_tech", "GROUND")
            if tech_type == "AIR":
                tech_info = {"air_tech": True}
            elif tech_type == "MECHANIC":
                tech_info = {"mech_tech": True}
            elif tech_type == "BIO":
                tech_info = {"bio_tech": True}

        # 2. IntelManager에서 테크 정보 가져오기 (안전한 접근)
        if not tech_info:
            intel_manager = getattr(b, "intel", None)
            if intel_manager:
                intel_tech_info = getattr(intel_manager, "enemy_tech_detected", {})
                if intel_tech_info:
                    tech_info = intel_tech_info

        # 3. IntelManager에 없으면 ScoutManager에서 가져오기 (안전한 접근)
        if not tech_info:
            scout_manager = getattr(b, "scout", None)
            if scout_manager:
                scout_tech_info = getattr(scout_manager, "enemy_tech_detected", {})
                if scout_tech_info:
                    tech_info = scout_tech_info

        # 테크 정보가 없으면 빈 리스트 반환
        if not tech_info:
            return []

        # 공중 테크 감지 시: 히드라리스크 + 여왕 우선 (강제 트리거 - 즉시 대응)
        # CRITICAL: 반응성 강화 - 공중 테크 감지 시 히드라 덴 건설 강제 트리거
        if tech_info.get("air_tech", False):
            # 히드라 덴이 없으면 즉시 건설 요청 (강제 트리거)
            hydra_dens = list(
                b.units.filter(lambda u: u.type_id == UnitTypeId.HYDRALISKDEN and u.is_structure)
            )
            if not hydra_dens or not any(d.is_ready for d in hydra_dens):
                # 히드라 덴이 없거나 건설 중이면, 건설을 최우선으로 처리
                detection_time = tech_info.get("detected_time", 0.0)
                if b.time - detection_time < 10.0:  # 감지 후 10초 이내
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 25 == 0:
                        print(
                            f"[TECH COUNTER - URGENT] [{int(b.time)}s] AIR TECH DETECTED! Building Hydralisk Den ASAP!"
                        )

            # 히드라 덴이 준비되어 있으면 히드라 우선 생산
            hydra_dens_ready = [d for d in hydra_dens if d.is_ready] if hydra_dens else []
            if hydra_dens_ready:
                # 히드라 덴 준비됨 - 히드라 최우선 생산
                return [UnitTypeId.HYDRALISK, UnitTypeId.QUEEN, UnitTypeId.ZERGLING]
            else:
                # 히드라 덴이 없으면 여왕 우선 생산 (대공 방어용)
                return [UnitTypeId.QUEEN, UnitTypeId.ZERGLING]  # 여왕은 즉시 생산 가능

        # 메카닉 테크 감지 시: 궤멸충 + 바퀴 우선
        # Tech building construction is now handled by _autonomous_tech_progression()
        elif tech_info.get("mech_tech", False):
            # 로치 워렌이 준비되어 있으면 로치/궤멸충 우선 생산
            roach_warrens = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.ROACHWARREN and u.is_structure and u.is_ready
                )
            )
            lairs = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure and u.is_ready
                )
            )
            if roach_warrens:
                if lairs:
                    # 레어가 있으면 궤멸충 변태 가능 (로치를 궤멸충으로 변태)
                    # 로치를 궤멸충으로 변태하는 로직은 별도로 처리
                    roaches = list(b.units(UnitTypeId.ROACH).ready.idle)
                    if roaches and b.can_afford(AbilityId.MORPHTORAVAGER_RAVAGER):
                        try:
                            roaches[0](AbilityId.MORPHTORAVAGER_RAVAGER)
                        except Exception:
                            pass
                    return [UnitTypeId.RAVAGER, UnitTypeId.ROACH, UnitTypeId.ZERGLING]
                else:
                    # 레어가 없으면 로치만 생산
                    return [UnitTypeId.ROACH, UnitTypeId.ZERGLING]
            else:
                # 로치 워렌이 없으면 기본 유닛만 생산 (건설은 자율적 판단으로)
                return [UnitTypeId.ZERGLING]

        # 바이오 테크 감지 시: 맹독충 + 저글링 우선
        # Tech building construction is now handled by _autonomous_tech_progression()
        elif tech_info.get("bio_tech", False):
            # 맹독충 둥지가 준비되어 있으면 맹독충 우선 생산
            baneling_nests = list(
                b.units.filter(
                    lambda u: u.type_id == UnitTypeId.BANELINGNEST and u.is_structure and u.is_ready
                )
            )
            if baneling_nests:
                # 저글링을 맹독충으로 변태하는 로직 (별도로 처리)
                zerglings = list(b.units(UnitTypeId.ZERGLING).ready.idle)
                if zerglings and b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                    try:
                        zerglings[0](AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                    except Exception:
                        pass
                return [UnitTypeId.BANELING, UnitTypeId.ZERGLING]
            else:
                # 맹독충 둥지가 없으면 기본 유닛만 생산 (건설은 자율적 판단으로)
                return [UnitTypeId.ZERGLING]

        # 테크가 감지되지 않았으면 빈 리스트 반환 (기본 생산 로직 사용)
        return []

    def _get_counter_units(self, game_phase: GamePhase) -> List[UnitTypeId]:
        """
        상성 기반 유닛 선택

        Args:
            game_phase: 현재 게임 단계

        Returns:
            List[UnitTypeId]: 생산할 유닛 목록 (우선순위 순)
        """
        b = self.bot

        # tech_to_hydra: 중반 이후 히드라 우선 생산
        # 히드라 덴이 있고 중반 이후면 히드라 우선
        hydra_dens = list(
            b.units.filter(
                lambda u: u.type_id == UnitTypeId.HYDRALISKDEN and u.is_structure and u.is_ready
            )
        )
        if hydra_dens and b.time > 360:  # 6분 이후
            # 공중 대응을 위해 히드라 우선
            return [UnitTypeId.HYDRALISK, UnitTypeId.ROACH, UnitTypeId.ZERGLING]

        # 상대 종족이 알려지지 않았으면 기본 유닛
        if self.enemy_race == EnemyRace.UNKNOWN:
            return [UnitTypeId.HYDRALISK, UnitTypeId.ROACH, UnitTypeId.ZERGLING]

        # 상성 테이블에서 유닛 가져오기
        counter = COUNTER_BUILD.get(self.enemy_race, {})

        if game_phase in [GamePhase.OPENING, GamePhase.ECONOMY]:
            return counter.get("early_units", [UnitTypeId.ZERGLING])
        elif game_phase in [GamePhase.TECH, GamePhase.ATTACK]:
            return counter.get("mid_units", [UnitTypeId.ROACH, UnitTypeId.ZERGLING])
        else:
            return counter.get("late_units", [UnitTypeId.HYDRALISK, UnitTypeId.ROACH])

    async def _try_build_structure(
        self, structure_type: UnitTypeId, near: Optional[Point2] = None
    ) -> bool:
        """
        Try to build a structure (with duplicate prevention and resource threshold)

        Args:
            structure_type: Structure type to build
            near: Optional position to build near

        Returns:
            bool: True if build command was issued
        """
        b = self.bot

        # 1. 기본 자원 체크
        if not b.can_afford(structure_type):
            return False

        # 2. 중복 건설 방지 체크 (4단계)
        # This checks: existing structures, pending construction, and workers moving to build
        if not self._can_build_safely(structure_type, check_workers=True, reserve_on_pass=True):
            return False

        # 2.5 최종 중복 건설 검증 (마지막 안전장치)
        # 건설 명령 직전에 한 번 더 확인하여 동시성 문제 방지
        if b.structures(structure_type).exists or b.already_pending(structure_type) > 0:
            return False

        # 3. 자원 임계값 체크 (건설 후에도 최소 자원 보유)
        # 건물 비용을 확인하여 건설 후에도 임계값 이상의 자원이 남도록 보장
        try:
            # 건물 비용 가져오기
            unit_data = b.game_data.units[structure_type.value]
            mineral_cost = unit_data.cost.minerals
            vespene_cost = unit_data.cost.vespene

            # 건설 후 남을 자원 계산: (현재 자원 - 건물 비용) >= 임계값
            remaining_minerals = b.minerals - mineral_cost
            remaining_vespene = b.vespene - vespene_cost

            # 테크 건물인 경우에만 임계값 체크 (일반 건물은 예외)
            tech_buildings = {
                UnitTypeId.SPAWNINGPOOL,
                UnitTypeId.ROACHWARREN,
                UnitTypeId.HYDRALISKDEN,
                UnitTypeId.BANELINGNEST,
                UnitTypeId.SPIRE,
                UnitTypeId.GREATERSPIRE,
                UnitTypeId.INFESTATIONPIT,
                UnitTypeId.LURKERDEN,
            }

            if structure_type in tech_buildings:
                # 🚨 CRITICAL: Spawning Pool은 게임 진행의 필수 건물이므로 별도 처리
                if structure_type == UnitTypeId.SPAWNINGPOOL:
                    # Spawning Pool: 임계값 체크 완화 (게임 게막 방지)
                    # 최소 100 미네랄만 남으면 건설 허가 (200-100=100)
                    if remaining_minerals < 100:
                        return False
                    # 가스 요구사항 없음
                else:
                    # 다른 테크 건물은 건설 후에도 최소 자원이 남아야 함
                    # 하지만 미네랄이 2000 이상이면 자원 과잉 상태이므로 임계값 체크 완화
                    emergency_build = b.minerals >= 2000
                    if emergency_build:
                        # 긴급 상황: 미네랄이 2000 이상이면 임계값 체크 완화 (최소 100만 남으면 됨)
                        if remaining_minerals < 100:
                            return False
                    else:
                        # 일반 상황: 기본 임계값 체크
                        if remaining_minerals < self.mineral_reserve_threshold:
                            return False
                    if remaining_vespene < self.vespene_reserve_threshold:
                        return False
        except (AttributeError, KeyError, TypeError):
            # 건물 비용을 가져올 수 없는 경우 기본 체크만 수행
            pass

        # 4. 건설 명령 실행 (자율적 일꾼 선택: 봇이 스스로 최적의 일꾼을 선택)
        try:
            # 자율적 일꾼 선택: 봇이 스스로 건설에 가장 적합한 일꾼을 판단하여 선택
            available_workers = []
            if b.workers.exists:
                # 건설 중이 아닌 일꾼 중에서 선택 (채취 중인 일꾼 포함)
                for worker in b.workers:
                    # 건설 중인지 확인 (orders를 통해 확인)
                    is_constructing = False
                    if worker.orders:
                        # 건설 명령이 있는지 확인
                        for order in worker.orders:
                            # 건물 생성 능력인지 확인
                            try:
                                if hasattr(order, "ability") and order.ability:
                                    # 건물 생성 능력 ID 확인
                                    creation_ability = b.game_data.units[
                                        structure_type.value
                                    ].creation_ability
                                    if creation_ability and order.ability.id == creation_ability.id:
                                        is_constructing = True
                                        break
                            except (AttributeError, KeyError):
                                pass

                    # 건설 중이 아닌 일꾼만 선택
                    if not is_constructing:
                        # 건설 명령이 없는 일꾼 우선 선택
                        if not worker.orders or len(worker.orders) == 0:
                            available_workers.insert(0, worker)  # 우선순위 높음
                        elif hasattr(worker, "is_gathering") and worker.is_gathering:
                            available_workers.append(worker)  # 채취 중이지만 사용 가능

            # 일꾼 선택: 사용 가능한 일꾼이 있으면 사용, 없으면 자동 선택
            selected_worker = available_workers[0] if available_workers else None

            # Intelligent worker assignment: If worker is selected, move to build location and construct
            if selected_worker:
                # 선택된 일꾼의 현재 명령 취소 (채취 중단)
                try:
                    if selected_worker.orders:
                        selected_worker.stop()
                except Exception:
                    pass

                # 건설 위치 결정
                build_position = (
                    near
                    if near
                    else (
                        townhalls_list[0].position
                        if b.townhalls.exists and (townhalls_list := list(b.townhalls))
                        else None
                    )
                )

                if build_position:
                    try:
                        # Move worker to build location, then issue build
                        # python-sc2 b.build() auto-selects the closest worker;
                        # moving the worker first helps ensure selection
                        selected_worker.move(build_position)
                        # Issue build after moving
                        await b.build(structure_type, near=build_position)
                        # Duplicate prevention: set recent-build flag immediately
                        if hasattr(b, 'just_built_structures'):
                            b.just_built_structures[structure_type] = b.iteration
                        return True
                    except Exception:
                        # Fallback: generic build command (auto worker selection)
                        try:
                            await b.build(structure_type, near=build_position)
                            # Duplicate prevention: set recent-build flag immediately
                            if hasattr(b, 'just_built_structures'):
                                b.just_built_structures[structure_type] = b.iteration
                            return True
                        except Exception:
                            return False
            else:
                # Auto worker selection (default behavior)
                try:
                    if near:
                        await b.build(structure_type, near=near)
                    else:
                        # Build near main base
                        if b.townhalls.exists:
                            townhalls_list = list(b.townhalls)
                            if townhalls_list:
                                await b.build(structure_type, near=townhalls_list[0].position)

                    # Duplicate prevention: set recent-build flag immediately
                    if hasattr(b, 'just_built_structures'):
                        b.just_built_structures[structure_type] = b.iteration
                    return True
                except Exception:
                    return False
        except Exception:
            # 메인 try-except 블록: 일꾼 선택 및 건설 명령 실패 시 처리
            return False

    def _calculate_tech_priority_score(self) -> float:
        """
        가치 기반 의사결정: 테크 건물 건설의 가치를 계산

        봇이 스스로 "지금 테크를 올리는 것이 유닛을 뽑는 것보다 가치 있는가?"를 판단합니다.

        Returns:
            float: 테크 건물 건설의 가치 점수 (0.0 ~ 100.0)
        """
        b = self.bot

        score = 0.0

        # 1. 누락된 핵심 테크 건물이 있으면 가치 상승
        # 🚨 CRITICAL: Spawning Pool이 없으면 절대적 우선순위 부여 (100점)
        if not b.structures(UnitTypeId.SPAWNINGPOOL).exists:
            score += 100.0  # 산란못이 없으면 최우선 (100점 = 절대 우선)
        if not b.structures(UnitTypeId.ROACHWARREN).exists and b.time > 120:
            score += 30.0  # 2분 이후 로치 워렌이 없으면 높은 가치
        if not b.structures(UnitTypeId.HYDRALISKDEN).exists and b.time > 300:
            score += 25.0  # 5분 이후 히드라 덴이 없으면 높은 가치

        # 2. 자원이 충분할수록 테크 건설 가치 상승 - Use learned parameters

        tech_build_mineral_threshold_1 = get_learned_parameter(
            "tech_build_mineral_threshold_1", 200
        )
        tech_build_mineral_threshold_2 = get_learned_parameter(
            "tech_build_mineral_threshold_2", 300
        )

        if b.minerals >= tech_build_mineral_threshold_1:
            score += 20.0
        if b.minerals >= tech_build_mineral_threshold_2:
            score += 10.0

        # 3. 상대의 공격 위협이 낮을수록 테크 건설 가치 상승
        enemy_units_nearby = 0
        if hasattr(b, "enemy_units") and b.enemy_units:
            for enemy in b.enemy_units:
                if b.townhalls.exists:
                    closest_base = b.townhalls.closest_to(enemy.position)
                    if enemy.distance_to(closest_base) < 30:
                        enemy_units_nearby += 1

        if enemy_units_nearby == 0:
            score += 15.0  # 안전할 때 테크 건설 가치 상승
        elif enemy_units_nearby > 3:
            score -= 20.0  # 위험할 때 테크 건설 가치 하락

        # 4. 현재 병력이 충분하면 테크 건설 가치 상승
        army_supply = b.supply_army
        if army_supply >= 20:
            score += 10.0
        elif army_supply < 5:
            score -= 15.0  # 병력이 부족하면 유닛 생산 우선

        return max(0.0, min(100.0, score))

    def _calculate_production_priority_score(self) -> float:
        """
        가치 기반 의사결정: 유닛 생산의 가치를 계산

        Returns:
            float: 유닛 생산의 가치 점수 (0.0 ~ 100.0)
        """
        b = self.bot

        score = 50.0  # 기본값

        # 1. 병력이 부족하면 유닛 생산 가치 상승
        army_supply = b.supply_army
        if army_supply < 10:
            score += 30.0
        elif army_supply < 20:
            score += 15.0

        # 2. 상대의 공격 위협이 높으면 유닛 생산 가치 상승
        enemy_units_nearby = 0
        if hasattr(b, "enemy_units") and b.enemy_units:
            for enemy in b.enemy_units:
                if b.townhalls.exists:
                    closest_base = b.townhalls.closest_to(enemy.position)
                    if enemy.distance_to(closest_base) < 30:
                        enemy_units_nearby += 1

        if enemy_units_nearby > 0:
            score += 25.0  # 적이 근처에 있으면 유닛 생산 가치 상승

        # 3. 자원이 많으면 유닛 생산 가치 상승 - Use learned parameters

        production_mineral_threshold_high = get_learned_parameter(
            "production_mineral_threshold_high", 500
        )
        production_mineral_threshold_low = get_learned_parameter(
            "production_mineral_threshold_low", 100
        )

        if b.minerals >= production_mineral_threshold_high:
            score += 20.0
        elif b.minerals < production_mineral_threshold_low:
            score -= 10.0  # 자원이 부족하면 생산 가치 하락

        return max(0.0, min(100.0, score))

    async def _autonomous_tech_progression(self) -> bool:
        """
        자율적 테크 진행: 가치 기반 의사결정 시스템

        봇이 스스로 "지금 테크를 올리는 것이 유닛을 뽑는 것보다 가치 있는가?"를 판단하여
        가장 가치 있는 행동을 선택합니다.

        Returns:
            bool: 테크 건물 건설이 시작되거나 자원을 보존 중이면 True
        """
        b = self.bot

        # NOTE: Spawning Pool construction is handled exclusively by EconomyManager
        # to prevent duplicate build orders. This method only ranks tech priorities
        # and reserves resources; it must not issue Spawning Pool build commands.

        # 1. 가치 점수 계산: 봇이 스스로 판단
        self.tech_priority_score = self._calculate_tech_priority_score()
        self.production_priority_score = self._calculate_production_priority_score()

        # 2. 자율적 자원 저축 결정: 봇이 스스로 "저축"해야 할 금액을 결정
        # 건물이 없으면 승률이 낮아지니 위험하다는 인식을 부여
        self.autonomous_reserve_minerals = 0.0
        self.autonomous_reserve_vespene = 0.0

        # 누락된 핵심 테크 건물이 있으면 자원을 저축하기로 '결심'
        # Use learned parameters for reserve amounts

        current_iteration = getattr(b, "iteration", 0)

        # Get learned parameters for tech building costs (defaults match game costs)
        spawning_pool_cost = get_learned_parameter("spawning_pool_cost", 200)
        roach_warren_cost = get_learned_parameter("roach_warren_cost", 150)
        hydralisk_den_mineral_cost = get_learned_parameter("hydralisk_den_mineral_cost", 100)
        hydralisk_den_vespene_cost = get_learned_parameter("hydralisk_den_vespene_cost", 100)
        baneling_nest_mineral_cost = get_learned_parameter("baneling_nest_mineral_cost", 100)
        baneling_nest_vespene_cost = get_learned_parameter("baneling_nest_vespene_cost", 50)
        roach_warren_time_threshold = get_learned_parameter("roach_warren_time_threshold", 120)
        hydralisk_den_time_threshold = get_learned_parameter("hydralisk_den_time_threshold", 300)

        if not b.structures(UnitTypeId.SPAWNINGPOOL).exists:
            self.autonomous_reserve_minerals = float(spawning_pool_cost)
            # 🚀 PERFORMANCE: Reduced chat frequency from 224 to 500 frames (~22 seconds)
            if current_iteration % 500 == 0:
                await b.chat_send(
                    f"💡 현재 미네랄 {int(b.minerals)}... 산란못 건설을 위해 자원을 저축 중입니다."
                )
        elif (
            not b.structures(UnitTypeId.ROACHWARREN).exists and b.time > roach_warren_time_threshold
        ):
            self.autonomous_reserve_minerals = float(roach_warren_cost)
            # 🚀 PERFORMANCE: Reduced chat frequency from 224 to 500 frames (~22 seconds)
            if current_iteration % 500 == 0:
                await b.chat_send(
                    f"💡 로치 워렌 건설을 위해 미네랄 {int(self.autonomous_reserve_minerals)} 저축 중..."
                )
        elif (
            not b.structures(UnitTypeId.HYDRALISKDEN).exists
            and b.time > hydralisk_den_time_threshold
        ):
            self.autonomous_reserve_minerals = float(hydralisk_den_mineral_cost)
            self.autonomous_reserve_vespene = float(hydralisk_den_vespene_cost)
            # 🚀 PERFORMANCE: Reduced chat frequency from 224 to 500 frames (~22 seconds)
            if current_iteration % 500 == 0:
                await b.chat_send(
                    f"💡 히드라 덴 건설을 위해 자원 저축 중 (M:{int(self.autonomous_reserve_minerals)} V:{int(self.autonomous_reserve_vespene)})..."
                )
        elif not b.structures(UnitTypeId.BANELINGNEST).exists:
            # Baneling Nest can be built anytime after Spawning Pool
            spawning_pools = b.structures(UnitTypeId.SPAWNINGPOOL).ready
            if spawning_pools.exists:
                self.autonomous_reserve_minerals = float(baneling_nest_mineral_cost)
                self.autonomous_reserve_vespene = float(baneling_nest_vespene_cost)

        # 3. 상태 머신: 가치가 높은 행동을 선택
        if self.tech_priority_score > self.production_priority_score:
            self.current_mode = "CONSTRUCTION"
        else:
            self.current_mode = "PRODUCTION"

        # 3. 건설 모드일 때만 테크 건물 건설 시도
        if self.current_mode == "CONSTRUCTION":
            # 건설이 필요한 핵심 테크 건물과 목표 자원량 (learned parameters)

            tech_queue = [
                {
                    "id": UnitTypeId.SPAWNINGPOOL,
                    "minerals": get_learned_parameter("spawning_pool_cost", 200),
                    "vespene": 0,
                    "priority": 1,
                },
                {
                    "id": UnitTypeId.ROACHWARREN,
                    "minerals": get_learned_parameter("roach_warren_cost", 150),
                    "vespene": 0,
                    "priority": 2,
                },
                {
                    "id": UnitTypeId.HYDRALISKDEN,
                    "minerals": get_learned_parameter("hydralisk_den_mineral_cost", 100),
                    "vespene": get_learned_parameter("hydralisk_den_vespene_cost", 100),
                    "priority": 3,
                },
                {
                    "id": UnitTypeId.BANELINGNEST,
                    "minerals": get_learned_parameter("baneling_nest_mineral_cost", 100),
                    "vespene": get_learned_parameter("baneling_nest_vespene_cost", 50),
                    "priority": 4,
                },
                {
                    "id": UnitTypeId.SPIRE,
                    "minerals": get_learned_parameter("spire_mineral_cost", 200),
                    "vespene": get_learned_parameter("spire_vespene_cost", 200),
                    "priority": 5,
                },
                {
                    "id": UnitTypeId.LURKERDEN,
                    "minerals": get_learned_parameter("lurker_den_mineral_cost", 200),
                    "vespene": get_learned_parameter("lurker_den_vespene_cost", 200),
                    "priority": 6,
                },
                {
                    "id": UnitTypeId.INFESTATIONPIT,
                    "minerals": get_learned_parameter("infestation_pit_mineral_cost", 100),
                    "vespene": get_learned_parameter("infestation_pit_vespene_cost", 100),
                    "priority": 7,
                },
                {
                    "id": UnitTypeId.ULTRALISKCAVERN,
                    "minerals": get_learned_parameter("ultralisk_cavern_mineral_cost", 150),
                    "vespene": get_learned_parameter("ultralisk_cavern_vespene_cost", 200),
                    "priority": 8,
                },
            ]

            # 우선순위 순으로 정렬
            tech_queue.sort(key=lambda x: x["priority"])

            for item in tech_queue:
                tid = item["id"]
                target_minerals = item["minerals"]
                target_vespene = item["vespene"]

                # CRITICAL: 이미 존재하거나 짓고 있다면 다음 건물로 (무한 건설 루프 방지)
                # Double-check with _can_build_safely for extra safety
                if b.structures(tid).exists or b.already_pending(tid) > 0:
                    continue

                # Additional safety check: _can_build_safely also checks for workers moving to build
                if not self._can_build_safely(tid, check_workers=True, reserve_on_pass=True):
                    continue

                # Prerequisites check - bot must have required buildings first
                # Spawning Pool: no prerequisites
                # Roach Warren: no prerequisites (but usually built after Spawning Pool)
                # Hydralisk Den: no prerequisites
                # Baneling Nest: requires Spawning Pool
                if tid == UnitTypeId.BANELINGNEST:
                    if not b.structures(UnitTypeId.SPAWNINGPOOL).exists:
                        continue
                # Spire: requires Lair
                if tid == UnitTypeId.SPIRE:
                    if (
                        not b.structures(UnitTypeId.LAIR).exists
                        and not b.structures(UnitTypeId.HIVE).exists
                    ):
                        continue
                # Lurker Den: requires Hydralisk Den and Lair
                if tid == UnitTypeId.LURKERDEN:
                    if not b.structures(UnitTypeId.HYDRALISKDEN).exists:
                        continue
                    if (
                        not b.structures(UnitTypeId.LAIR).exists
                        and not b.structures(UnitTypeId.HIVE).exists
                    ):
                        continue
                # Infestation Pit: requires Lair
                if tid == UnitTypeId.INFESTATIONPIT:
                    if (
                        not b.structures(UnitTypeId.LAIR).exists
                        and not b.structures(UnitTypeId.HIVE).exists
                    ):
                        continue
                # Ultralisk Cavern: requires Hive
                if tid == UnitTypeId.ULTRALISKCAVERN:
                    if not b.structures(UnitTypeId.HIVE).exists:
                        continue

                # Opportunity Cost: 봇이 스스로 "저축"해야 할 금액을 결정
                # 테크 건물을 짓기 위해 자원을 보존하는 것이 미래 승률에 더 기여한다고 판단
                # 자율적 저축량과 목표 자원량 중 더 큰 값을 사용 (더 보수적인 접근)
                reserve_minerals = max(self.autonomous_reserve_minerals, target_minerals)
                reserve_vespene = max(self.autonomous_reserve_vespene, target_vespene)

                # 가용한 자원 내에서만 건설 시도 (자원 보존 개념)
                # 봇이 스스로 "저축한 금액을 제외한 여유 자원으로만" 건설 시도
                available_minerals = b.minerals - reserve_minerals
                available_vespene = (
                    b.vespene - reserve_vespene if reserve_vespene > 0 else b.vespene
                )

                if available_minerals >= target_minerals and available_vespene >= target_vespene:
                    if b.can_afford(tid):
                        # Final safety check before building (prevent infinite loop)
                        # Safety already enforced by prior checks and _can_build_safely

                        # 건설 명령 실행 (한 번에 하나만 건설)
                        if b.townhalls.exists:
                            townhalls_list = list(b.townhalls)
                            if townhalls_list:
                                # Intelligent worker assignment: Execute construction command
                                if await self._try_build_structure(
                                    tid, near=townhalls_list[0].position
                                ):
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(
                                            f"[AUTONOMOUS TECH] [{int(b.time)}s] Building {tid.name} (Tech Score: {self.tech_priority_score:.1f} > Production Score: {self.production_priority_score:.1f})"
                                        )
                                    # 봇이 자신의 의사결정을 채팅으로 설명
                                    # 🚀 PERFORMANCE: Reduced chat frequency - only send on important events
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 500 == 0:
                                        await b.chat_send(
                                            f"🏗️ [자율 판단] {tid.name} 건설 시작! (미네랄: {int(b.minerals)}, 가스: {int(b.vespene)})"
                                        )
                                    # 시각적 피드백: 화면에 건설 상태 표시
                                    await self._visualize_tech_progression(b, tid, True)
                                    return True  # 건설 시작됨 - 즉시 리턴하여 한 번에 하나만 건설
                    else:
                        # 자원이 부족하면 보존 모드 (유닛 생산 자제)
                        # 봇이 스스로 "지금은 자원을 모아야 할 때"라고 판단
                        current_iteration = getattr(b, "iteration", 0)
                        # 🚀 PERFORMANCE: Reduced chat frequency from 224 to 500 frames (~22 seconds)
                        if current_iteration % 500 == 0:
                            await b.chat_send(
                                f"💡 테크 업그레이드를 위해 유닛 생산을 잠시 미루겠습니다. (목표: {tid.name})"
                            )
                        if current_iteration % 50 == 0:
                            await self._visualize_tech_progression(b, tid, False)
                        return True  # 자원 보존 중

        # 생산 모드로 전환 (유닛 생산 가능)
        return False

    async def _visualize_tech_progression(self, bot, tech_id: UnitTypeId, building: bool):
        """
        테크 진행 상태를 화면에 시각적으로 표시

        Args:
            bot: 봇 인스턴스
            tech_id: 건설 중인 테크 건물 ID
            building: 건설 시작 여부 (True: 건설 중, False: 자원 예약 중)
        """
        try:
            current_iteration = getattr(bot, "iteration", 0)
            # 4프레임마다 업데이트 (CPU 부담 감소)
            if current_iteration % 4 != 0:
                return

            if hasattr(bot, "client") and bot.client:
                if building:
                    status_text = f"BUILDING: {tech_id.name}"
                    color = (0, 255, 0)  # Green: 건설 중
                else:
                    status_text = f"RESERVING RESOURCES: {tech_id.name}"
                    color = (255, 255, 0)  # Yellow: 자원 예약 중

                # 화면 중앙 하단에 상태 표시
                try:
                    bot.client.debug_text_screen(status_text, pos=(0.3, 0.85), size=12, color=color)
                except Exception:
                    # debug_text_screen이 지원되지 않는 경우 무시
                    pass
        except Exception:
            # 시각화 실패는 게임 플레이에 영향을 주지 않도록 무시
            pass

    async def build_tech_structures(self):
        """
        Build tech structures - AUTONOMOUS DECISION ONLY.

        This function is now DEPRECATED - all tech building construction
        is handled by _autonomous_tech_progression() which makes decisions
        based on game state, resources, and learned parameters.

        Only handles Evolution Chamber upgrades (non-tech building).
        """
        b = self.bot

        # Tech building construction is now handled by _autonomous_tech_progression()
        # This function only handles Evolution Chamber upgrades

        # Check for idle Evolution Chambers and research upgrades
        # Use is_idle instead of is_researching for better resource management
        evolution_chambers = b.structures(UnitTypeId.EVOLUTIONCHAMBER).ready
        for evo in evolution_chambers:
            if evo.is_idle:
                # Research missile attack upgrade if affordable
                # Use correct UpgradeId name: ZERGMISSILEWEAPONSLEVEL1
                if hasattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL1"):
                    upgrade_id = UpgradeId.ZERGMISSILEWEAPONSLEVEL1  # type: ignore
                    if b.can_afford(upgrade_id):
                        if upgrade_id not in b.state.upgrades:
                            try:
                                evo.research(upgrade_id)
                            except Exception:
                                pass  # Silent fail if research fails
                # Research ground carapace upgrade if affordable
                elif hasattr(UpgradeId, "ZERGGROUNDARMORSLEVEL1"):
                    upgrade_id = UpgradeId.ZERGGROUNDARMORSLEVEL1  # type: ignore
                    if b.can_afford(upgrade_id):
                        if upgrade_id not in b.state.upgrades:
                            try:
                                evo.research(upgrade_id)
                            except Exception:
                                pass  # Silent fail if research fails

    async def _produce_mid_game_strong_build(self) -> bool:
        """
        중반 강력 빌드 생산 (러쉬 실패 시 전환)

        상대 종족에 따라 강력한 중반 빌드를 생산합니다:
        - vs Terran: Roach + Hydralisk + Ravager (강력한 지상 조합)
        - vs Protoss: Hydralisk + Lurker (가시지옥 중심)
        - vs Zerg: Roach + Hydralisk + Baneling (균형 잡힌 조합)

        Returns:
            bool: 유닛을 생산했으면 True
        """
        b = self.bot

        try:
            larvae = [u for u in b.units(UnitTypeId.LARVA)]
            if not larvae:
                return False

            # 인구수 체크
            if b.supply_left < 2:
                return False

            # 상대 종족 확인
            enemy_race = self.enemy_race
            if enemy_race == EnemyRace.UNKNOWN:
                # 상대 종족을 알 수 없으면 기본 조합 사용
                enemy_race = EnemyRace.TERRAN

            # vs Terran: Roach + Hydralisk + Ravager 조합
            # Tech building construction is now handled by _autonomous_tech_progression()
            # Only produce units if buildings already exist
            if enemy_race == EnemyRace.TERRAN:
                # Get ready structures for production
                # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                roach_warrens = list(b.structures(UnitTypeId.ROACHWARREN))
                hydra_dens = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.HYDRALISKDEN and u.is_structure
                    )
                )

                # 3. Lair 건설 확인 (Ravager 생산을 위해 필요)
                lairs = list(
                    b.units.filter(lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure)
                )
                if not lairs:
                    hatcheries = list(
                        b.units.filter(
                            lambda u: u.type_id == UnitTypeId.HATCHERY
                            and u.is_structure
                            and u.is_ready
                        )
                    )
                    if hatcheries and b.can_afford(UnitTypeId.LAIR):
                        try:
                            hatcheries[0].morph(UnitTypeId.LAIR)  # type: ignore
                            print(
                                f"[MID-GAME BUILD] [{int(b.time)}s] Lair morphing for Ravager tech"
                            )
                            return True
                        except Exception:
                            pass

                # 4. 강력한 유닛 생산 우선순위
                ready_roach_warrens = [rw for rw in roach_warrens if rw.is_ready]
                ready_hydra_dens = [hd for hd in hydra_dens if hd.is_ready]
                ready_lairs = [l for l in lairs if l.is_ready]

                # Roach 생산 (Ravager 변태용)
                roaches = b.units(UnitTypeId.ROACH)
                roach_count = roaches.amount if hasattr(roaches, "amount") else len(list(roaches))

                if ready_roach_warrens and roach_count < 12:
                    if await self._try_produce_unit(UnitTypeId.ROACH, larvae):
                        return True

                # Ravager 변태 (Roach가 3마리 이상일 때)
                if ready_lairs and roach_count >= 3:
                    roaches_ready = [r for r in b.units(UnitTypeId.ROACH) if r.is_ready]
                    if roaches_ready:
                        for roach in roaches_ready[:2]:  # 2마리씩 변태
                            if b.can_afford(AbilityId.MORPHTORAVAGER_RAVAGER):
                                try:
                                    roach(AbilityId.MORPHTORAVAGER_RAVAGER)
                                    print(
                                        f"[MID-GAME BUILD] [{int(b.time)}s] Ravager morphing vs Terran"
                                    )
                                    return True
                                except Exception:
                                    pass

                # Hydralisk 생산
                if ready_hydra_dens:
                    if await self._try_produce_unit(UnitTypeId.HYDRALISK, larvae):
                        return True

            # vs Protoss: Hydralisk + Lurker 조합
            # Tech building construction is now handled by _autonomous_tech_progression()
            # Only produce units if buildings already exist
            elif enemy_race == EnemyRace.PROTOSS:
                # Lair 건설 확인 (Lurker 생산을 위해 필요) - Lair는 Hatchery 변태이므로 허용
                lairs = list(
                    b.units.filter(lambda u: u.type_id == UnitTypeId.LAIR and u.is_structure)
                )
                if not lairs:
                    hatcheries = list(
                        b.units.filter(
                            lambda u: u.type_id == UnitTypeId.HATCHERY
                            and u.is_structure
                            and u.is_ready
                        )
                    )
                    if hatcheries and b.can_afford(UnitTypeId.LAIR):
                        try:
                            hatcheries[0].morph(UnitTypeId.LAIR)  # type: ignore
                            print(
                                f"[MID-GAME BUILD] [{int(b.time)}s] Lair morphing for Lurker tech"
                            )
                            return True
                        except Exception:
                            pass

                # Get ready structures for production
                hydra_dens = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.HYDRALISKDEN and u.is_structure
                    )
                )
                lurker_dens = list(
                    b.units.filter(lambda u: u.type_id == UnitTypeId.LURKERDEN and u.is_structure)
                )

                # 4. 강력한 유닛 생산 우선순위
                ready_hydra_dens = [hd for hd in hydra_dens if hd.is_ready]
                ready_lurker_dens = [ld for ld in lurker_dens if ld.is_ready]

                # Hydralisk 생산 (Lurker 변태용)
                hydralisks = b.units(UnitTypeId.HYDRALISK)
                hydra_count = (
                    hydralisks.amount if hasattr(hydralisks, "amount") else len(list(hydralisks))
                )

                if ready_hydra_dens and hydra_count < 10:
                    if await self._try_produce_unit(UnitTypeId.HYDRALISK, larvae):
                        return True

                # Lurker 변태 (Hydralisk가 3마리 이상일 때)
                if ready_lurker_dens and hydra_count >= 3:
                    hydralisks_ready = [
                        h for h in b.units(UnitTypeId.HYDRALISK) if h.is_ready and not h.is_burrowed
                    ]
                    if hydralisks_ready:
                        for hydra in hydralisks_ready[:3]:  # 3마리씩 변태
                            if b.can_afford(AbilityId.MORPH_LURKER):
                                try:
                                    hydra(AbilityId.MORPH_LURKER)
                                    print(
                                        f"[MID-GAME BUILD] [{int(b.time)}s] Lurker morphing vs Protoss"
                                    )
                                    return True
                                except Exception:
                                    pass

            # vs Zerg: Roach + Hydralisk + Baneling 조합
            # Tech building construction is now handled by _autonomous_tech_progression()
            # Only produce units if buildings already exist
            elif enemy_race == EnemyRace.ZERG:
                # Get ready structures for production
                # 🚀 성능 최적화: b.structures 사용 (더 빠름)
                roach_warrens = list(b.structures(UnitTypeId.ROACHWARREN))
                hydra_dens = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.HYDRALISKDEN and u.is_structure
                    )
                )
                baneling_nests = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.BANELINGNEST and u.is_structure
                    )
                )

                # 4. 강력한 유닛 생산 우선순위
                ready_roach_warrens = [rw for rw in roach_warrens if rw.is_ready]
                ready_hydra_dens = [hd for hd in hydra_dens if hd.is_ready]
                ready_baneling_nests = [bn for bn in baneling_nests if bn.is_ready]

                # Roach 생산
                roaches = b.units(UnitTypeId.ROACH)
                roach_count = roaches.amount if hasattr(roaches, "amount") else len(list(roaches))

                if ready_roach_warrens and roach_count < 10:
                    if await self._try_produce_unit(UnitTypeId.ROACH, larvae):
                        return True

                # Hydralisk 생산
                hydralisks = b.units(UnitTypeId.HYDRALISK)
                hydra_count = (
                    hydralisks.amount if hasattr(hydralisks, "amount") else len(list(hydralisks))
                )

                if ready_hydra_dens and hydra_count < 8:
                    if await self._try_produce_unit(UnitTypeId.HYDRALISK, larvae):
                        return True

                # Baneling 변태 (Zergling이 6마리 이상일 때)
                if ready_baneling_nests:
                    zerglings_ready = [z for z in b.units(UnitTypeId.ZERGLING) if z.is_ready]
                    if len(zerglings_ready) >= 6:
                        for zergling in zerglings_ready[:3]:  # 3마리씩 변태
                            if b.can_afford(AbilityId.MORPHZERGLINGTOBANELING_BANELING):
                                try:
                                    zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)
                                    print(
                                        f"[MID-GAME BUILD] [{int(b.time)}s] Baneling morphing vs Zerg"
                                    )
                                    return True
                                except Exception:
                                    pass

            return False

        except Exception as e:
            # 중반 강력 빌드 생산 오류는 조용히 무시
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[WARNING] Mid-game strong build production error: {e}")
            return False

    async def _try_produce_unit(self, unit_type: UnitTypeId, larvae) -> bool:
        """
        특정 유닛 생산 시도 (건설 우선순위 시스템 통합)

        Args:
            unit_type: 생산할 유닛 타입
            larvae: 사용 가능한 애벌레

        Returns:
            bool: 생산 성공 여부
        """
        # 가치 기반 의사결정: 생산 모드일 때만 유닛 생산
        # 봇이 스스로 "지금은 유닛을 뽑을 때인가?"를 판단
        if self.current_mode == "CONSTRUCTION":
            return False  # 건설 모드일 때는 유닛 생산 자제 (자율적 판단)

        # 레거시 플래그는 제거됨 - current_mode만 사용하여 자율적으로 판단

        b = self.bot

        # 유닛별 필요 건물 체크 (산란못은 메인 루프의 sticky 플래그도 참조)
        required_building = self._get_required_building(unit_type)

        if required_building and not self._has_required_building(required_building):
            # Focused debug for spawning pool detection issues
            if required_building == UnitTypeId.SPAWNINGPOOL:
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 50 == 0:
                    try:
                        pool_structs = b.structures(UnitTypeId.SPAWNINGPOOL)
                        progress = (
                            pool_structs.first.build_progress if pool_structs.exists else None
                        )
                    except Exception:
                        progress = None

                    print(
                        f"[REQ] Spawning Pool not ready (iter={current_iteration}, "
                        f"flag={getattr(b, 'spawning_pool_ready_flag', False)}, "
                        f"progress={progress})"
                    )
            return False

        if b.can_afford(unit_type) and larvae and len(larvae) > 0:
            random.choice(larvae).train(unit_type)

            # 첫 저글링 시간 기록
            if unit_type == UnitTypeId.ZERGLING and self.first_zergling_time is None:
                self.first_zergling_time = b.time
                print(f"[ZERGLING] [{int(b.time)}초] 첫 저글링 생산!")

            return True

        return False

    def _get_required_building(self, unit_type: UnitTypeId) -> Optional[UnitTypeId]:
        """유닛 생산에 필요한 건물 반환"""
        requirements = {
            UnitTypeId.ZERGLING: UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.BANELING: UnitTypeId.BANELINGNEST,
            UnitTypeId.ROACH: UnitTypeId.ROACHWARREN,
            UnitTypeId.RAVAGER: UnitTypeId.ROACHWARREN,
            UnitTypeId.HYDRALISK: UnitTypeId.HYDRALISKDEN,
            UnitTypeId.LURKER: UnitTypeId.LURKERDEN,
            UnitTypeId.MUTALISK: UnitTypeId.SPIRE,
            UnitTypeId.CORRUPTOR: UnitTypeId.SPIRE,
            UnitTypeId.ULTRALISK: UnitTypeId.ULTRALISKCAVERN,
            UnitTypeId.INFESTOR: UnitTypeId.INFESTATIONPIT,
        }
        return requirements.get(unit_type)

    def _has_required_building(self, building: UnitTypeId) -> bool:
        """필수 건물 보유 여부를 확인 (sticky 플래그와 진행률 허용)"""
        b = self.bot

        try:
            # Sticky flag from wicked_zerg_bot_pro avoids flip-flop when visibility hiccups
            if building == UnitTypeId.SPAWNINGPOOL and getattr(
                b, "spawning_pool_ready_flag", False
            ):
                return True

            structures = b.structures(building)
            if structures.ready.exists:
                return True

            # Treat near-complete spawning pool as ready to unblock production
            if building == UnitTypeId.SPAWNINGPOOL and structures.exists:
                try:
                    if structures.first.build_progress >= 0.99:
                        return True
                except Exception:
                    pass
        except Exception:
            pass

        # Fallback to units() query in case structures cache is stale
        try:
            candidates = b.units(building)
            for s in candidates:
                if s.is_structure and getattr(s, "is_ready", False):
                    return True
        except Exception:
            pass

        return False

    # 📊 생산 상태 조회
    def get_production_status(self) -> dict:
        """현재 생산 상태 반환"""
        b = self.bot
        larvae = [u for u in b.units(UnitTypeId.LARVA)]
        zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]
        roaches = [u for u in b.units(UnitTypeId.ROACH)]
        hydras = [u for u in b.units(UnitTypeId.HYDRALISK)]
        queens = [u for u in b.units(UnitTypeId.QUEEN)]
        return {
            "larvae": len(larvae),
            "zerglings": len(zerglings),
            "roaches": len(roaches),
            "hydras": len(hydras),
            "queens": len(queens),
            "first_zergling_time": self.first_zergling_time,
            "supply_blocks": self.supply_block_count,
        }

    # 0️⃣ Serral 빌드 오더 (16-18-17)
    async def _execute_serral_opening(self) -> bool:
        """
        Serral 스타일 초반 빌드 오더 실행

        빌드 시퀀스:
            13: 대군주 (인구수 막힘 방지)
            16: 앞마당 해처리 (Natural Expansion)
            18: 추출장 (Extractor) - 가스 수급 시작
            17: 산란못 (Spawning Pool) - 수비 및 여왕 준비
            20: 일벌레 2마리 + 여왕 2마리 + 저글링 1~2쌍
            28: 세 번째 해처리 (3rd Hatchery)
            30: 대군주 + 발업 (저글링 이동속도 업그레이드)

        Returns:
            bool: 빌드 오더를 실행했으면 True (다른 생산 중단)
        """
        b = self.bot

        try:
            units = [u for u in b.units]
            minerals = b.minerals
            vespene = b.vespene
            # 🚀 성능 최적화: IntelManager 캐시 사용
            intel = getattr(b, "intel", None)
            if intel and intel.cached_townhalls is not None:
                townhalls = list(intel.cached_townhalls) if intel.cached_townhalls.exists else []
            else:
                townhalls = [th for th in b.townhalls]
            larvae = [u for u in b.units(UnitTypeId.LARVA)]

            # 1. 앞마당 해처리 (Natural Expansion) - Use learned parameter instead of hardcoded supply

            natural_expansion_supply = get_learned_parameter("natural_expansion_supply", 16)

            if (
                b.supply_used >= natural_expansion_supply
                and not self.serral_build_completed["natural_expansion"]
            ):
                if len(townhalls) < 2:
                    if b.already_pending(UnitTypeId.HATCHERY) == 0:
                        if b.can_afford(UnitTypeId.HATCHERY):
                            try:
                                await b.expand_now()
                                self.serral_build_completed["natural_expansion"] = True
                                # 타이밍 기록 (신경망 학습용)
                                self.build_order_timing["natural_expansion_supply"] = float(
                                    b.supply_used
                                )  # type: ignore
                                self.build_order_timing["natural_expansion_time"] = b.time  # type: ignore
                                print(
                                    f"[SERRAL BUILD] [{int(b.time)}s] 16 Supply: Natural Expansion (앞마당)"
                                )
                                return True
                            except Exception:
                                pass

            # 2. 추출장 (Extractor) - 가스 수급 시작 - Use learned parameter
            gas_supply = get_learned_parameter("gas_supply", 18)

            if b.supply_used >= gas_supply and not self.serral_build_completed["gas"]:
                # 앞마당이 완성되었거나 건설 중이면 가스 건설
                if len(townhalls) >= 2 or b.already_pending(UnitTypeId.HATCHERY) > 0:
                    if self._can_build_safely(UnitTypeId.EXTRACTOR, reserve_on_pass=True):
                        if b.can_afford(UnitTypeId.EXTRACTOR):
                            try:
                                # 가장 가까운 가스 지점 찾기
                                if townhalls and len(townhalls) > 0:
                                    main_hatch = townhalls[0]
                                    vgs = [
                                        vg
                                        for vg in b.vespene_geyser
                                        if vg.position.distance_to(main_hatch.position) < 15
                                    ]
                                    if vgs:
                                        target_gas = vgs[0]
                                        workers = [
                                            w for w in b.workers if w.is_idle or w.is_gathering
                                        ]
                                        if workers:
                                            worker = workers[0]
                                            worker.build(UnitTypeId.EXTRACTOR, target_gas)
                                            self.serral_build_completed["gas"] = True
                                            # 타이밍 기록 (신경망 학습용)
                                            self.build_order_timing["gas_supply"] = float(
                                                b.supply_used
                                            )  # type: ignore
                                            self.build_order_timing["gas_time"] = b.time  # type: ignore
                                            print(
                                                f"[SERRAL BUILD] [{int(b.time)}s] 18 Supply: Extractor (가스)"
                                            )
                                            return True
                            except Exception:
                                pass

            # 3. 산란못 (Spawning Pool) - 수비 및 여왕 준비 - Use learned parameter
            # 강화된 중복 건설 방지: 이미 존재하거나 건설 중이면 건설 안 함
            spawning_pools_existing = list(
                b.units.filter(lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure)
            )
            spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 17)

            if (
                b.supply_used >= spawning_pool_supply
                and not self.serral_build_completed["spawning_pool"]
            ):
                if not spawning_pools_existing and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0:
                    if self._can_build_safely(UnitTypeId.SPAWNINGPOOL, reserve_on_pass=True):
                        if b.can_afford(UnitTypeId.SPAWNINGPOOL):
                            try:
                                if townhalls and len(townhalls) > 0:
                                    main_hatch = townhalls[0]
                                    # Use _try_build_structure for duplicate prevention
                                    if await self._try_build_structure(
                                        UnitTypeId.SPAWNINGPOOL,
                                        near=main_hatch.position,
                                    ):
                                        self.serral_build_completed["spawning_pool"] = True
                                        # 타이밍 기록 (신경망 학습용)
                                        self.build_order_timing["spawning_pool_supply"] = float(
                                            b.supply_used
                                        )  # type: ignore
                                        self.build_order_timing["spawning_pool_time"] = b.time  # type: ignore
                                        print(
                                            f"[SERRAL BUILD] [{int(b.time)}s] 17 Supply: Spawning Pool (산란못)"
                                        )
                                        # 봇이 자신의 판단을 채팅으로 설명
                                        current_iteration = getattr(b, "iteration", 0)
                                        # 🚀 PERFORMANCE: Reduced chat frequency from 224 to 500 frames (~22 seconds)
                                        if current_iteration % 500 == 0:
                                            await b.chat_send(
                                                "🏗️ [신중함] 기본 방어를 위해 산란못 건설을 시작합니다."
                                            )
                                        return True
                            except Exception:
                                pass
                else:
                    # 이미 건설 중이거나 존재함 - 완료 플래그만 설정
                    if spawning_pools_existing:
                        self.serral_build_completed["spawning_pool"] = True

            # 4. 일벌레 2마리 + 여왕 2마리 + 저글링 1~2쌍 - Use learned parameter
            queen_production_supply = get_learned_parameter("queen_production_supply", 20)

            if b.supply_used >= queen_production_supply:
                # 여왕 생산 (기지당 1마리)
                queens = [u for u in b.units(UnitTypeId.QUEEN)]
                queens_count = len(queens) + b.already_pending(UnitTypeId.QUEEN)
                if queens_count < len(townhalls):
                    ready_townhalls = [th for th in townhalls if th.is_ready and th.is_idle]
                    for hatch in ready_townhalls:
                        if b.can_afford(UnitTypeId.QUEEN):
                            hatch.train(UnitTypeId.QUEEN)
                            print(f"[SERRAL BUILD] [{int(b.time)}s] 20 Supply: Queen (여왕)")
                            return True

                # 저글링 생산 (산란못 완성 후)
                spawning_pools = [
                    s for s in b.units(UnitTypeId.SPAWNINGPOOL) if s.is_structure and s.is_ready
                ]
                if spawning_pools:
                    zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]
                    if len(zerglings) < 4:  # 1~2쌍 (2~4마리)
                        if larvae and len(larvae) > 0:
                            if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 2:
                                random.choice(larvae).train(UnitTypeId.ZERGLING)
                                print(
                                    f"[SERRAL BUILD] [{int(b.time)}s] 20 Supply: Zergling (저글링)"
                                )
                                return True

            # 5. 세 번째 해처리 (3rd Hatchery) - Use learned parameter
            third_hatchery_supply = get_learned_parameter("third_hatchery_supply", 28)

            if (
                b.supply_used >= third_hatchery_supply
                and not self.serral_build_completed["third_hatchery"]
            ):
                if len(townhalls) < 3:
                    if b.already_pending(UnitTypeId.HATCHERY) == 0:
                        if b.can_afford(UnitTypeId.HATCHERY):
                            try:
                                await b.expand_now()
                                self.serral_build_completed["third_hatchery"] = True
                                # 타이밍 기록 (신경망 학습용)
                                self.build_order_timing["third_hatchery_supply"] = float(
                                    b.supply_used
                                )  # type: ignore
                                self.build_order_timing["third_hatchery_time"] = b.time  # type: ignore
                                print(
                                    f"[SERRAL BUILD] [{int(b.time)}s] 28 Supply: 3rd Hatchery (세 번째 해처리)"
                                )
                                return True
                            except Exception:
                                pass

            # 6. 대군주 + 발업 (저글링 이동속도 업그레이드) - Use learned parameter
            speed_upgrade_supply = get_learned_parameter("speed_upgrade_supply", 30)

            if b.supply_used >= speed_upgrade_supply:
                # 대군주 생산 (인구수 막힘 방지)
                if b.supply_left < 4:
                    if larvae and len(larvae) > 0:
                        if b.can_afford(UnitTypeId.OVERLORD):
                            random.choice(larvae).train(UnitTypeId.OVERLORD)
                            print(f"[SERRAL BUILD] [{int(b.time)}s] 30 Supply: Overlord (대군주)")
                            return True

                # 발업 연구 (가스 100 모이자마자)
                if vespene >= 100 and not self.serral_build_completed["speed_upgrade"]:
                    spawning_pools = [
                        s for s in b.units(UnitTypeId.SPAWNINGPOOL) if s.is_structure and s.is_ready
                    ]
                    if spawning_pools:
                        pool = spawning_pools[0]
                        if pool.is_ready and pool.is_idle:
                            # 발업이 이미 연구되었는지 확인
                            if UpgradeId.ZERGLINGMOVEMENTSPEED not in b.state.upgrades:
                                if b.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) == 0:
                                    try:
                                        pool.research(UpgradeId.ZERGLINGMOVEMENTSPEED)
                                        self.serral_build_completed["speed_upgrade"] = True
                                        # 타이밍 기록 (신경망 학습용)
                                        self.build_order_timing["speed_upgrade_supply"] = float(
                                            b.supply_used
                                        )  # type: ignore
                                        self.build_order_timing["speed_upgrade_time"] = b.time  # type: ignore
                                        print(
                                            f"[SERRAL BUILD] [{int(b.time)}s] 30 Supply: Metabolic Boost (발업) - 주도권 확보!"
                                        )
                                        return True
                                    except Exception:
                                        pass
        except Exception as e:
            # 에러 발생 시 로그만 출력 (게임 중단 방지)
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _execute_serral_opening 오류: {e}")

        return False

    def set_enemy_race(self, race: EnemyRace):
        """상대 종족 설정"""
        # 종족이 변경되었을 때만 출력
        if self.enemy_race != race:
            self.enemy_race = race
            print(f"[TARGET] 상대 종족 감지: {race.name}")

    def get_build_order_timing(self) -> dict:
        """
        빌드 오더 타이밍 정보 반환 (신경망 학습용)

        Returns:
            dict: 빌드 오더 타이밍 정보
        """
        return self.build_order_timing.copy()

    # 6️⃣ 가스 확보용 빠른 멀티 확장
    async def _expand_for_gas(self):
        """
        가스 확보용 빠른 멀티 확장

        가스는 한 베이스당 2개로 제한되어 있습니다.
        즉, 가스를 많이 얻으려면 부화장(Hatchery) 개수를 늘리는 것이 유일한 길입니다.

        봇이 스스로 판단하여 미네랄이 300 이상 모이고, 가스통을 더 지을 곳이 없다면 확장
        """
        b = self.bot

        # 이미 확장 중이면 대기
        if b.already_pending(UnitTypeId.HATCHERY) > 0:
            return

        townhalls = [th for th in b.townhalls]
        current_base_count = len(townhalls)

        # 최대 8멀티까지 빠르게 확장 (가스 수입 극대화)
        if current_base_count >= 8:
            return

        # 가스통 건설 가능 여부 체크
        ready_extractors = list(
            b.units.filter(
                lambda u: u.type_id == UnitTypeId.EXTRACTOR and u.is_structure and u.is_ready
            )
        )

        # 모든 부화장의 가스통이 건설되었는지 확인
        all_gas_built = True
        for th in townhalls:
            if th.is_ready:
                try:
                    vgs = b.vespene_geyser.closer_than(15, th)
                    for vg in vgs:
                        nearby_extractors = b.structures(UnitTypeId.EXTRACTOR).closer_than(1, vg)
                        if not nearby_extractors.exists:
                            all_gas_built = False
                            break
                    if not all_gas_built:
                        break
                except:
                    pass

        # 조건 1: 미네랄이 학습된 임계값 이상이고, 모든 가스통이 건설되었으면 확장

        gas_expand_mineral_threshold = get_learned_parameter("gas_expand_mineral_threshold", 300)

        if b.minerals >= gas_expand_mineral_threshold and all_gas_built:
            if b.can_afford(UnitTypeId.HATCHERY):
                try:
                    await b.expand_now()
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(
                            f"[GAS EXPAND] [{int(b.time)}s] 가스 확보용 멀티 확장: {current_base_count + 1}멀티"
                        )
                except Exception:
                    pass

        # 조건 2: 가스가 학습된 임계값 이상 남는다면 즉시 확장 (가스가 남는 상황)
        gas_expand_vespene_threshold = get_learned_parameter("gas_expand_vespene_threshold", 1000)
        gas_expand_mineral_threshold_2 = get_learned_parameter(
            "gas_expand_mineral_threshold_2", 300
        )
        if (
            b.vespene >= gas_expand_vespene_threshold
            and b.minerals >= gas_expand_mineral_threshold_2
        ):
            if b.can_afford(UnitTypeId.HATCHERY):
                try:
                    await b.expand_now()
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(
                            f"[GAS EXPAND] [{int(b.time)}s] 가스 과다 보유 → 멀티 확장: {current_base_count + 1}멀티"
                        )
                except Exception:
                    pass

        # 조건 3: 미네랄이 학습된 임계값 이상이고 기지가 학습된 개수 미만이면 적극 확장
        aggressive_expand_mineral_threshold = get_learned_parameter(
            "aggressive_expand_mineral_threshold", 400
        )
        max_base_count = get_learned_parameter("max_base_count", 5)
        if (
            b.minerals >= aggressive_expand_mineral_threshold
            and current_base_count < max_base_count
        ):
            if b.can_afford(UnitTypeId.HATCHERY):
                try:
                    await b.expand_now()
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(
                            f"[GAS EXPAND] [{int(b.time)}s] 적극적 멀티 확장: {current_base_count + 1}멀티"
                        )
                except Exception:
                    pass

    # 7️⃣ 필수 업그레이드 자동 연구 (자원이 남을 때) - 강화 버전
    async def _research_mandatory_upgrades(self) -> bool:
        """
        자원이 남을 때 필수 업그레이드를 자동으로 연구 (GPU 가속 최적화)

        우선순위:
            1. 저글링 발업 (Metabolic Boost) - 최우선
            2. 맹독충 속업 (Centrifugal Hooks) - 테란 대응 필수
            3. 진화장 업그레이드 (공격/방어) - 진화장 2개로 동시 연구
            4. 유닛별 속도 업그레이드

        Returns:
            bool: 업그레이드 연구를 시작했으면 True
        """
        b = self.bot

        # 가스 수입 확인 (GasMaximizer 연동)
        gas_income_sufficient = True
        if hasattr(b, "gas_maximizer") and b.gas_maximizer:
            # 가스 수입이 충분한지 확인 (초당 30 이상 권장)
            if hasattr(b.gas_maximizer, "gas_income_rate"):
                if b.gas_maximizer.gas_income_rate < 20.0 and b.vespene < 200:
                    gas_income_sufficient = False

        # 자원이 충분히 남아있을 때만 업그레이드 수행
        # (미네랄 200 이상 또는 가스 100 이상 남을 때)
        # 가스 수입이 부족하면 더 엄격한 조건 적용
        min_minerals = 200 if gas_income_sufficient else 300
        min_gas = 100 if gas_income_sufficient else 150

        if b.minerals < min_minerals and b.vespene < min_gas:
            return False

        # 🔍 GAS WASTE DETECTOR: 가스가 500 이상인데 업그레이드가 진행/대기 중이 없으면 경고
        candidate_upgrades = [
            getattr(UpgradeId, "ZERGLINGMOVEMENTSPEED", None),
            getattr(UpgradeId, "GROOVEDSPINES", None) or getattr(UpgradeId, "GROOVED_SPINES", None),
            getattr(UpgradeId, "MUSCULARAUGMENTS", None) or getattr(UpgradeId, "HYDRALISKSPEED", None),
            getattr(UpgradeId, "GLIALRECONSTITUTION", None),
            getattr(UpgradeId, "CENTRIFUGALHOOKS", None) or getattr(UpgradeId, "CENTRIFUGAL_HOOKS", None),
            getattr(UpgradeId, "ZERGMISSILEWEAPONSLEVEL1", None),
            getattr(UpgradeId, "ZERGGROUNDARMORSLEVEL1", None),
        ]
        pending_any = False
        for upg in candidate_upgrades:
            if upg and b.already_pending_upgrade(upg) > 0:
                pending_any = True
                break
        if b.vespene >= 500 and not pending_any:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(
                    f"[UPGRADE][WARN] [{int(b.time)}s] Gas= {int(b.vespene)} but no upgrades pending/researching. Consider starting upgrades now."
                )

        # 1. 저글링 발업 (Metabolic Boost) - 최우선 (1순위)
        if UpgradeId.ZERGLINGMOVEMENTSPEED not in b.state.upgrades:
            spawning_pools = [s for s in b.structures(UnitTypeId.SPAWNINGPOOL) if s.is_ready]
            if spawning_pools:
                pool = spawning_pools[0]
                # Check if pool is idle AND upgrade not pending
                if pool.is_idle and b.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) == 0:
                    if b.can_afford(UpgradeId.ZERGLINGMOVEMENTSPEED):
                        try:
                            pool.research(UpgradeId.ZERGLINGMOVEMENTSPEED)
                            print(
                                f"[UPGRADE] [{int(b.time)}s] ⚡ Zergling Metabolic Boost research started (Priority 1)"
                            )
                            return True
                        except Exception as e:
                            print(f"[UPGRADE][ERROR] Failed to research Metabolic Boost: {e}")
                            pass

        # 1.5. 히드라 사업 (Grooved Spines) - 히드라 사거리 +1 (Priority 1.5, parallel with zergling speed)
        # This upgrade is critical for hydralisks - increases range from 5 to 6
        try:
            # Check if Grooved Spines upgrade is available
            grooved_spines_upgrade_id = None
            if hasattr(UpgradeId, "GROOVEDSPINES"):
                grooved_spines_upgrade_id = UpgradeId.GROOVEDSPINES  # type: ignore
            elif hasattr(UpgradeId, "GROOVED_SPINES"):
                grooved_spines_upgrade_id = UpgradeId.GROOVED_SPINES  # type: ignore

            if grooved_spines_upgrade_id and grooved_spines_upgrade_id not in b.state.upgrades:
                hydra_dens = [s for s in b.structures(UnitTypeId.HYDRALISKDEN) if s.is_ready]
                if hydra_dens:
                    hydra_den = hydra_dens[0]
                    # Check if we have hydralisks or are planning to produce them
                    hydralisks = b.units(UnitTypeId.HYDRALISK)
                    if hydralisks.exists or len(hydralisks) > 0:
                        if (
                            hydra_den.is_idle
                            and b.already_pending_upgrade(grooved_spines_upgrade_id) == 0
                        ):
                            if b.can_afford(grooved_spines_upgrade_id):
                                try:
                                    hydra_den.research(grooved_spines_upgrade_id)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(
                                            f"[UPGRADE] [{int(b.time)}s] ⚡ Hydralisk Grooved Spines research started (Priority 1.5, Range +1)"
                                        )
                                    return True
                                except Exception:
                                    pass
        except (AttributeError, KeyError):
            # Grooved Spines upgrade not available in this SC2 version
            pass

        # 2. 맹독충 속업 (Centrifugal Hooks) - 테란 대응 필수 (2순위)
        # Note: Upgrade ID may vary by SC2 version
        try:
            # Try CENTRIFUGALHOOKS first (most common)
            centrifugal_upgrade_id = None
            if hasattr(UpgradeId, "CENTRIFUGALHOOKS"):
                centrifugal_upgrade_id = UpgradeId.CENTRIFUGALHOOKS  # type: ignore
            elif hasattr(UpgradeId, "CENTRIFUGAL_HOOKS"):
                centrifugal_upgrade_id = UpgradeId.CENTRIFUGAL_HOOKS  # type: ignore

            if centrifugal_upgrade_id and centrifugal_upgrade_id not in b.state.upgrades:
                baneling_nests = [s for s in b.structures(UnitTypeId.BANELINGNEST) if s.is_ready]
                if baneling_nests:
                    nest = baneling_nests[0]
                    if nest.is_idle and b.already_pending_upgrade(centrifugal_upgrade_id) == 0:
                        if b.can_afford(centrifugal_upgrade_id):
                            try:
                                nest.research(centrifugal_upgrade_id)
                                current_iteration = getattr(b, "iteration", 0)
                                if current_iteration % 50 == 0:
                                    print(
                                        f"[UPGRADE] [{int(b.time)}s] ⚡ Baneling Centrifugal Hooks research started (Priority 2)"
                                    )
                                return True
                            except Exception:
                                pass
        except (AttributeError, KeyError):
            # Centrifugal Hooks upgrade not available in this SC2 version
            pass

        # 3. 진화장 업그레이드 (공격/방어 업그레이드) - 진화장 2개로 동시 연구
        evolution_chambers = [s for s in b.structures(UnitTypeId.EVOLUTIONCHAMBER) if s.is_ready]

        # 봇이 스스로 판단하여 진화장이 1개만 있으면 2번째 건설 (동시 업그레이드가 승률에 기여한다고 판단)
        # 자원이 남는다면 학습된 임계값에 따라 진화장 2개 건설 (공방업 동시 진행)
        evolution_chamber_mineral_threshold_1 = get_learned_parameter(
            "evolution_chamber_mineral_threshold_1", 150
        )
        evolution_chamber_mineral_threshold_2 = get_learned_parameter(
            "evolution_chamber_mineral_threshold_2", 200
        )
        evolution_chamber_vespene_threshold = get_learned_parameter(
            "evolution_chamber_vespene_threshold", 100
        )

        if len(evolution_chambers) < 2:
            # 미네랄이 학습된 임계값 이상이면 즉시 건설
            if b.minerals >= evolution_chamber_mineral_threshold_1:
                if self._can_build_safely(UnitTypeId.EVOLUTIONCHAMBER, reserve_on_pass=True):
                    if b.can_afford(UnitTypeId.EVOLUTIONCHAMBER):
                        try:
                            await self._try_build_structure(UnitTypeId.EVOLUTIONCHAMBER)
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[UPGRADE] [{int(b.time)}s] ⚡ Building 2nd Evolution Chamber for parallel upgrades (MANDATORY)"
                                )
                            return True  # 건설 시작했으면 우선순위 반환
                        except Exception:
                            pass
            # 가스가 부족한데 미네랄이 학습된 임계값 이상이면 진화장 건설 우선 (가스 확보 후 업그레이드)
            elif (
                b.minerals >= evolution_chamber_mineral_threshold_2
                and b.vespene < evolution_chamber_vespene_threshold
            ):
                if self._can_build_safely(UnitTypeId.EVOLUTIONCHAMBER, reserve_on_pass=True):
                    if b.can_afford(UnitTypeId.EVOLUTIONCHAMBER):
                        try:
                            await self._try_build_structure(UnitTypeId.EVOLUTIONCHAMBER)
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[UPGRADE] [{int(b.time)}s] ⚡ Building 2nd Evolution Chamber (preparing for upgrades)"
                                )
                            return True
                        except Exception:
                            pass

        # 진화장 업그레이드 수행 (여러 진화장이 있으면 동시에 다른 업그레이드 연구)
        if evolution_chambers:
            # 상대 종족 + 우리 조합에 따라 우선순위 결정
            enemy_race = getattr(b, "opponent_race", None)
            prioritize_ranged = False
            if enemy_race and enemy_race in [Race.Terran, Race.Protoss]:
                prioritize_ranged = True

            # 아군 조합 기반 우선순위: 바퀴/히드라 비중이 저글링/울트라보다 크면 원거리 우선
            roach_count = b.units(UnitTypeId.ROACH).amount if hasattr(b.units(UnitTypeId.ROACH), "amount") else len(b.units(UnitTypeId.ROACH))
            hydra_count = b.units(UnitTypeId.HYDRALISK).amount if hasattr(b.units(UnitTypeId.HYDRALISK), "amount") else len(b.units(UnitTypeId.HYDRALISK))
            ravager_count = b.units(UnitTypeId.RAVAGER).amount if hasattr(b.units(UnitTypeId.RAVAGER), "amount") else len(b.units(UnitTypeId.RAVAGER))
            ling_count = b.units(UnitTypeId.ZERGLING).amount if hasattr(b.units(UnitTypeId.ZERGLING), "amount") else len(b.units(UnitTypeId.ZERGLING))
            ultra_count = b.units(UnitTypeId.ULTRALISK).amount if hasattr(b.units(UnitTypeId.ULTRALISK), "amount") else len(b.units(UnitTypeId.ULTRALISK))

            ranged_weight = roach_count + hydra_count + ravager_count
            melee_weight = ling_count + ultra_count
            if ranged_weight >= melee_weight and ranged_weight >= 8:
                prioritize_ranged = True

            # 각 진화장에서 다른 업그레이드 연구 (동시 연구)
            for idx, evo in enumerate(evolution_chambers):
                if not evo.is_idle:
                    continue

                # 첫 번째 진화장: 공격 업그레이드 우선
                if idx == 0:
                    if prioritize_ranged:
                        # 원거리 공격 업그레이드 (로치, 히드라)
                        if UpgradeId.ZERGMISSILEWEAPONSLEVEL1 not in b.state.upgrades:
                            if (
                                b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
                                and b.already_pending_upgrade(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
                                == 0
                            ):
                                try:
                                    evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(
                                            f"[UPGRADE] [{int(b.time)}s] Missile Weapons Level 1 research started (Evo 1)"
                                        )
                                    return True
                                except Exception:
                                    pass
                    else:
                        # 근접 공격 업그레이드 (저글링)
                        if UpgradeId.ZERGMELEEWEAPONSLEVEL1 not in b.state.upgrades:
                            if (
                                b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL1)
                                and b.already_pending_upgrade(UpgradeId.ZERGMELEEWEAPONSLEVEL1) == 0
                            ):
                                try:
                                    evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL1)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(
                                            f"[UPGRADE] [{int(b.time)}s] Melee Weapons Level 1 research started (Evo 1)"
                                        )
                                    return True
                                except Exception:
                                    pass

                # 두 번째 진화장: 방어 업그레이드 우선
                elif idx == 1:
                    if UpgradeId.ZERGGROUNDARMORSLEVEL1 not in b.state.upgrades:
                        if (
                            b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL1)
                            and b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL1) == 0
                        ):
                            try:
                                evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL1)
                                current_iteration = getattr(b, "iteration", 0)
                                if current_iteration % 50 == 0:
                                    print(
                                        f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 1 research started (Evo 2)"
                                    )
                                return True
                            except Exception:
                                pass

            # 진화장이 1개만 있으면 공격/방어 순차적으로 연구
            if len(evolution_chambers) == 1:
                evo = evolution_chambers[0]
                if evo.is_idle:
                    # 공격 업그레이드 우선 (상대 종족에 따라)
                    if prioritize_ranged:
                        # 원거리 공격 업그레이드
                        if UpgradeId.ZERGMISSILEWEAPONSLEVEL1 not in b.state.upgrades:
                            if (
                                b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
                                and b.already_pending_upgrade(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
                                == 0
                            ):
                                try:
                                    evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(
                                            f"[UPGRADE] [{int(b.time)}s] Missile Weapons Level 1 research started"
                                        )
                                    return True
                                except Exception:
                                    pass
                    else:
                        # 근접 공격 업그레이드
                        if UpgradeId.ZERGMELEEWEAPONSLEVEL1 not in b.state.upgrades:
                            if (
                                b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL1)
                                and b.already_pending_upgrade(UpgradeId.ZERGMELEEWEAPONSLEVEL1) == 0
                            ):
                                try:
                                    evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL1)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(
                                            f"[UPGRADE] [{int(b.time)}s] Melee Weapons Level 1 research started"
                                        )
                                    return True
                                except Exception:
                                    pass

                    # 방어 업그레이드 (공격 업그레이드가 완료되면)
                    if UpgradeId.ZERGGROUNDARMORSLEVEL1 not in b.state.upgrades:
                        # 공격 업그레이드가 완료되었거나 레벨 2 이상이면 방어 업그레이드 시작
                        if (
                            UpgradeId.ZERGMELEEWEAPONSLEVEL1 in b.state.upgrades
                            or UpgradeId.ZERGMISSILEWEAPONSLEVEL1 in b.state.upgrades
                        ):
                            if (
                                b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL1)
                                and b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL1) == 0
                            ):
                                try:
                                    evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL1)
                                    current_iteration = getattr(b, "iteration", 0)
                                    if current_iteration % 50 == 0:
                                        print(
                                            f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 1 research started"
                                        )
                                    return True
                                except Exception:
                                    pass

                    # 레벨 2/3 업그레이드 (레어/하이브 필요)
                    has_lair = (
                        b.structures(UnitTypeId.LAIR).ready.exists
                        or b.structures(UnitTypeId.HIVE).ready.exists
                    )
                    has_hive = b.structures(UnitTypeId.HIVE).ready.exists

                    # 레벨 2 업그레이드
                    if has_lair:
                        if prioritize_ranged:
                            if UpgradeId.ZERGMISSILEWEAPONSLEVEL2 not in b.state.upgrades:
                                if UpgradeId.ZERGMISSILEWEAPONSLEVEL1 in b.state.upgrades:
                                    if (
                                        b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL2)
                                        and b.already_pending_upgrade(
                                            UpgradeId.ZERGMISSILEWEAPONSLEVEL2
                                        )
                                        == 0
                                    ):
                                        try:
                                            evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL2)
                                            current_iteration = getattr(b, "iteration", 0)
                                            if current_iteration % 50 == 0:
                                                print(
                                                    f"[UPGRADE] [{int(b.time)}s] Missile Weapons Level 2 research started"
                                                )
                                            return True
                                        except Exception:
                                            pass
                        else:
                            if UpgradeId.ZERGMELEEWEAPONSLEVEL2 not in b.state.upgrades:
                                if UpgradeId.ZERGMELEEWEAPONSLEVEL1 in b.state.upgrades:
                                    if (
                                        b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL2)
                                        and b.already_pending_upgrade(
                                            UpgradeId.ZERGMELEEWEAPONSLEVEL2
                                        )
                                        == 0
                                    ):
                                        try:
                                            evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL2)
                                            current_iteration = getattr(b, "iteration", 0)
                                            if current_iteration % 50 == 0:
                                                print(
                                                    f"[UPGRADE] [{int(b.time)}s] Melee Weapons Level 2 research started"
                                                )
                                            return True
                                        except Exception:
                                            pass

                        if UpgradeId.ZERGGROUNDARMORSLEVEL2 not in b.state.upgrades:
                            if UpgradeId.ZERGGROUNDARMORSLEVEL1 in b.state.upgrades:
                                if (
                                    b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL2)
                                    and b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL2)
                                    == 0
                                ):
                                    try:
                                        evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL2)
                                        current_iteration = getattr(b, "iteration", 0)
                                        if current_iteration % 50 == 0:
                                            print(
                                                f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 2 research started"
                                            )
                                        return True
                                    except Exception:
                                        pass

                    # 레벨 3 업그레이드 (하이브 필요)
                    if has_hive:
                        if prioritize_ranged:
                            if UpgradeId.ZERGMISSILEWEAPONSLEVEL3 not in b.state.upgrades:
                                if UpgradeId.ZERGMISSILEWEAPONSLEVEL2 in b.state.upgrades:
                                    if (
                                        b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL3)
                                        and b.already_pending_upgrade(
                                            UpgradeId.ZERGMISSILEWEAPONSLEVEL3
                                        )
                                        == 0
                                    ):
                                        try:
                                            evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL3)
                                            current_iteration = getattr(b, "iteration", 0)
                                            if current_iteration % 50 == 0:
                                                print(
                                                    f"[UPGRADE] [{int(b.time)}s] Missile Weapons Level 3 research started"
                                                )
                                            return True
                                        except Exception:
                                            pass
                        else:
                            if UpgradeId.ZERGMELEEWEAPONSLEVEL3 not in b.state.upgrades:
                                if UpgradeId.ZERGMELEEWEAPONSLEVEL2 in b.state.upgrades:
                                    if (
                                        b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL3)
                                        and b.already_pending_upgrade(
                                            UpgradeId.ZERGMELEEWEAPONSLEVEL3
                                        )
                                        == 0
                                    ):
                                        try:
                                            evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL3)
                                            current_iteration = getattr(b, "iteration", 0)
                                            if current_iteration % 50 == 0:
                                                print(
                                                    f"[UPGRADE] [{int(b.time)}s] Melee Weapons Level 3 research started"
                                                )
                                            return True
                                        except Exception:
                                            pass

                        if UpgradeId.ZERGGROUNDARMORSLEVEL3 not in b.state.upgrades:
                            if UpgradeId.ZERGGROUNDARMORSLEVEL2 in b.state.upgrades:
                                if (
                                    b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL3)
                                    and b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL3)
                                    == 0
                                ):
                                    try:
                                        evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL3)
                                        current_iteration = getattr(b, "iteration", 0)
                                        if current_iteration % 50 == 0:
                                            print(
                                                f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 3 research started"
                                            )
                                        return True
                                    except Exception:
                                        pass
                # 공격 업그레이드 (저글링, 로치, 히드라 공통)
                if UpgradeId.ZERGMELEEWEAPONSLEVEL1 not in b.state.upgrades:
                    if (
                        b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL1)
                        and b.already_pending_upgrade(UpgradeId.ZERGMELEEWEAPONSLEVEL1) == 0
                    ):
                        try:
                            evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL1)
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[UPGRADE] [{int(b.time)}s] Melee Weapons Level 1 research started"
                                )
                            return True
                        except Exception:
                            pass
                elif UpgradeId.ZERGMELEEWEAPONSLEVEL2 not in b.state.upgrades:
                    # 레어 필요
                    if (
                        b.structures(UnitTypeId.LAIR).ready.exists
                        or b.structures(UnitTypeId.HIVE).ready.exists
                    ):
                        if (
                            b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL2)
                            and b.already_pending_upgrade(UpgradeId.ZERGMELEEWEAPONSLEVEL2) == 0
                        ):
                            try:
                                evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL2)
                                current_iteration = getattr(b, "iteration", 0)
                                if current_iteration % 50 == 0:
                                    print(
                                        f"[UPGRADE] [{int(b.time)}s] Melee Weapons Level 2 research started"
                                    )
                                return True
                            except Exception:
                                pass
                elif UpgradeId.ZERGMELEEWEAPONSLEVEL3 not in b.state.upgrades:
                    # 하이브 필요
                    if b.structures(UnitTypeId.HIVE).ready.exists:
                        if (
                            b.can_afford(UpgradeId.ZERGMELEEWEAPONSLEVEL3)
                            and b.already_pending_upgrade(UpgradeId.ZERGMELEEWEAPONSLEVEL3) == 0
                        ):
                            try:
                                evo.research(UpgradeId.ZERGMELEEWEAPONSLEVEL3)
                                current_iteration = getattr(b, "iteration", 0)
                                if current_iteration % 50 == 0:
                                    print(
                                        f"[UPGRADE] [{int(b.time)}s] Melee Weapons Level 3 research started"
                                    )
                                return True
                            except Exception:
                                pass

                # 방어 업그레이드 (모든 지상 유닛 공통)
                if UpgradeId.ZERGGROUNDARMORSLEVEL1 not in b.state.upgrades:
                    if (
                        b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL1)
                        and b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL1) == 0
                    ):
                        try:
                            evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL1)
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 1 research started"
                                )
                            return True
                        except Exception:
                            pass
                elif UpgradeId.ZERGGROUNDARMORSLEVEL2 not in b.state.upgrades:
                    # 레어 필요
                    if (
                        b.structures(UnitTypeId.LAIR).ready.exists
                        or b.structures(UnitTypeId.HIVE).ready.exists
                    ):
                        if (
                            b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL2)
                            and b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL2) == 0
                        ):
                            try:
                                evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL2)
                                current_iteration = getattr(b, "iteration", 0)
                                if current_iteration % 50 == 0:
                                    print(
                                        f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 2 research started"
                                    )
                                return True
                            except Exception:
                                pass
                elif UpgradeId.ZERGGROUNDARMORSLEVEL3 not in b.state.upgrades:
                    # 하이브 필요
                    if b.structures(UnitTypeId.HIVE).ready.exists:
                        if (
                            b.can_afford(UpgradeId.ZERGGROUNDARMORSLEVEL3)
                            and b.already_pending_upgrade(UpgradeId.ZERGGROUNDARMORSLEVEL3) == 0
                        ):
                            try:
                                evo.research(UpgradeId.ZERGGROUNDARMORSLEVEL3)
                                current_iteration = getattr(b, "iteration", 0)
                                if current_iteration % 50 == 0:
                                    print(
                                        f"[UPGRADE] [{int(b.time)}s] Ground Armor Level 3 research started"
                                    )
                                return True
                            except Exception:
                                pass

                # 미사일 업그레이드 (로치, 히드라 공통)
                if UpgradeId.ZERGMISSILEWEAPONSLEVEL1 not in b.state.upgrades:
                    if (
                        b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
                        and b.already_pending_upgrade(UpgradeId.ZERGMISSILEWEAPONSLEVEL1) == 0
                    ):
                        try:
                            evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[UPGRADE] [{int(b.time)}s] Missile Weapons Level 1 research started"
                                )
                            return True
                        except Exception:
                            pass
                elif UpgradeId.ZERGMISSILEWEAPONSLEVEL2 not in b.state.upgrades:
                    # 레어 필요
                    if (
                        b.structures(UnitTypeId.LAIR).ready.exists
                        or b.structures(UnitTypeId.HIVE).ready.exists
                    ):
                        if (
                            b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL2)
                            and b.already_pending_upgrade(UpgradeId.ZERGMISSILEWEAPONSLEVEL2) == 0
                        ):
                            try:
                                evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL2)
                                current_iteration = getattr(b, "iteration", 0)
                                if current_iteration % 50 == 0:
                                    print(
                                        f"[UPGRADE] [{int(b.time)}s] Missile Weapons Level 2 research started"
                                    )
                                return True
                            except Exception:
                                pass
                elif UpgradeId.ZERGMISSILEWEAPONSLEVEL3 not in b.state.upgrades:
                    # 하이브 필요
                    if b.structures(UnitTypeId.HIVE).ready.exists:
                        if (
                            b.can_afford(UpgradeId.ZERGMISSILEWEAPONSLEVEL3)
                            and b.already_pending_upgrade(UpgradeId.ZERGMISSILEWEAPONSLEVEL3) == 0
                        ):
                            try:
                                evo.research(UpgradeId.ZERGMISSILEWEAPONSLEVEL3)
                                current_iteration = getattr(b, "iteration", 0)
                                if current_iteration % 50 == 0:
                                    print(
                                        f"[UPGRADE] [{int(b.time)}s] Missile Weapons Level 3 research started"
                                    )
                                return True
                            except Exception:
                                pass

        # 3. 로치 속도 업그레이드 (Glial Reconstitution)
        if UpgradeId.GLIALRECONSTITUTION not in b.state.upgrades:
            roach_warrens = [s for s in b.structures(UnitTypeId.ROACHWARREN) if s.is_ready]
            if roach_warrens:
                warren = roach_warrens[0]
                if warren.is_idle and b.already_pending_upgrade(UpgradeId.GLIALRECONSTITUTION) == 0:
                    if b.can_afford(UpgradeId.GLIALRECONSTITUTION):
                        try:
                            warren.research(UpgradeId.GLIALRECONSTITUTION)
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[UPGRADE] [{int(b.time)}s] Roach Glial Reconstitution research started"
                                )
                            return True
                        except Exception:
                            pass

        # 4. 히드라 속도 업그레이드 (Muscular Augments, fallback HYDRALISKSPEED)
        hydra_speed_id = None
        if hasattr(UpgradeId, "MUSCULARAUGMENTS"):
            hydra_speed_id = UpgradeId.MUSCULARAUGMENTS  # type: ignore
        elif hasattr(UpgradeId, "HYDRALISKSPEED"):
            hydra_speed_id = UpgradeId.HYDRALISKSPEED  # type: ignore

        if hydra_speed_id and hydra_speed_id not in b.state.upgrades:
            hydra_dens = [s for s in b.structures(UnitTypeId.HYDRALISKDEN) if s.is_ready]
            if hydra_dens:
                den = hydra_dens[0]
                if den.is_idle and b.already_pending_upgrade(hydra_speed_id) == 0:
                    if b.can_afford(hydra_speed_id):
                        try:
                            den.research(hydra_speed_id)
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(
                                    f"[UPGRADE] [{int(b.time)}s] Hydralisk Speed research started"
                                )
                            return True
                        except Exception:
                            pass

        # 5. 대군주 속도 업그레이드 (Overlord Speed) - 레어 필요
        if UpgradeId.OVERLORDSPEED not in b.state.upgrades:
            lairs = [s for s in b.structures(UnitTypeId.LAIR) if s.is_ready]
            hives = [s for s in b.structures(UnitTypeId.HIVE) if s.is_ready]
            if lairs or hives:
                lair_or_hive = lairs[0] if lairs else hives[0]
                if lair_or_hive.is_idle and b.already_pending_upgrade(UpgradeId.OVERLORDSPEED) == 0:
                    if b.can_afford(UpgradeId.OVERLORDSPEED):
                        try:
                            lair_or_hive.research(UpgradeId.OVERLORDSPEED)
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(f"[UPGRADE] [{int(b.time)}s] Overlord Speed research started")
                            return True
                        except Exception:
                            pass

        # 6. 여왕 범위 증가 (Queen Range) - 산란못 필요
        # Note: QUEENRANGE upgrade may not be available in all SC2 versions
        # Skip if upgrade ID doesn't exist
        try:
            queen_range_upgrade = getattr(UpgradeId, "QUEENRANGE", None)
            if queen_range_upgrade and queen_range_upgrade not in b.state.upgrades:
                spawning_pools = [s for s in b.structures(UnitTypeId.SPAWNINGPOOL) if s.is_ready]
                if spawning_pools:
                    pool = spawning_pools[0]
                    if pool.is_idle and b.already_pending_upgrade(queen_range_upgrade) == 0:
                        if b.can_afford(queen_range_upgrade):
                            try:
                                pool.research(queen_range_upgrade)
                                current_iteration = getattr(b, "iteration", 0)
                                if current_iteration % 50 == 0:
                                    print(
                                        f"[UPGRADE] [{int(b.time)}s] Queen Range research started"
                                    )
                                return True
                            except Exception:
                                pass
        except (AttributeError, KeyError):
            # QUEENRANGE upgrade not available in this SC2 version
            pass

        # 7. 땅굴 (Burrow) - 해처리/레어/하이브 필요
        if UpgradeId.BURROW not in b.state.upgrades:
            hatcheries = [s for s in b.structures(UnitTypeId.HATCHERY) if s.is_ready]
            lairs = [s for s in b.structures(UnitTypeId.LAIR) if s.is_ready]
            hives = [s for s in b.structures(UnitTypeId.HIVE) if s.is_ready]
            if hatcheries or lairs or hives:
                structure = hives[0] if hives else (lairs[0] if lairs else hatcheries[0])
                if structure.is_idle and b.already_pending_upgrade(UpgradeId.BURROW) == 0:
                    if b.can_afford(UpgradeId.BURROW):
                        try:
                            structure.research(UpgradeId.BURROW)
                            current_iteration = getattr(b, "iteration", 0)
                            if current_iteration % 50 == 0:
                                print(f"[UPGRADE] [{int(b.time)}s] Burrow research started")
                            return True
                        except Exception:
                            pass

        return False

    async def display_matchup_win_rate(self):
        """
        Display matchup win rate comparison in chat (called every 10 seconds)

        Calculates win probability based on enemy tech and bot's unit composition,
        then displays the result in chat for debugging and strategy analysis.
        """
        try:
            b = self.bot

            # Skip if iteration is not available
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 224 != 0:  # Every 10 seconds (approximately 224 iterations)
                return

            # 1. Get enemy tech safely (multiple fallback sources)
            enemy_tech = "UNKNOWN"
            if hasattr(b, "enemy_tech"):
                enemy_tech = b.enemy_tech
            elif hasattr(b, "enemy_tech_detected"):
                tech_detected = getattr(b, "enemy_tech_detected", {})
                if tech_detected.get("air_tech", False):
                    enemy_tech = "AIR"
                elif tech_detected.get("mech_tech", False):
                    enemy_tech = "MECHANIC"
                elif tech_detected.get("bio_tech", False):
                    enemy_tech = "BIO"
            elif hasattr(b, "intel") and b.intel:
                enemy_tech = getattr(b.intel, "enemy_tech", "UNKNOWN")

            # Skip if tech is not detected yet
            if enemy_tech == "UNKNOWN" or enemy_tech == "GROUND" or enemy_tech == "SCANNING":
                return

            # 2. Count bot's units
            hydra_count = (
                b.units(UnitTypeId.HYDRALISK).amount
                if hasattr(b.units(UnitTypeId.HYDRALISK), "amount")
                else len(list(b.units(UnitTypeId.HYDRALISK)))
            )
            ravager_count = (
                b.units(UnitTypeId.RAVAGER).amount
                if hasattr(b.units(UnitTypeId.RAVAGER), "amount")
                else len(list(b.units(UnitTypeId.RAVAGER)))
            )
            baneling_count = (
                b.units(UnitTypeId.BANELING).amount
                if hasattr(b.units(UnitTypeId.BANELING), "amount")
                else len(list(b.units(UnitTypeId.BANELING)))
            )
            zergling_count = (
                b.units(UnitTypeId.ZERGLING).amount
                if hasattr(b.units(UnitTypeId.ZERGLING), "amount")
                else len(list(b.units(UnitTypeId.ZERGLING)))
            )
            queen_count = (
                b.units(UnitTypeId.QUEEN).amount
                if hasattr(b.units(UnitTypeId.QUEEN), "amount")
                else len(list(b.units(UnitTypeId.QUEEN)))
            )

            # 3. Calculate win rate based on matchup (heuristic)
            win_rate = 50  # Base 50%
            advice = ""

            if enemy_tech == "AIR":
                # Against air: Hydralisks and Queens are key
                base_rate = 30
                hydra_bonus = min(hydra_count * 5, 50)  # Max 50% bonus
                win_rate = base_rate + hydra_bonus

                # Queen bonus (anti-air support)
                queen_bonus = min(queen_count * 2, 10)  # Max 10% bonus
                win_rate += queen_bonus

                if win_rate < 50:
                    advice = "💡 Need more Hydralisks/Queens"
                elif win_rate >= 70:
                    advice = "✅ Excellent counter (Hydra vs Air)"
                else:
                    advice = "⚠️ Building Hydralisks..."

            elif enemy_tech == "MECHANIC":
                # Against mech: Ravagers and Roaches are key
                base_rate = 40
                ravager_bonus = min(ravager_count * 7, 45)  # Max 45% bonus
                win_rate = base_rate + ravager_bonus

                # Roach bonus (tanky frontline)
                roach_count = (
                    b.units(UnitTypeId.ROACH).amount
                    if hasattr(b.units(UnitTypeId.ROACH), "amount")
                    else len(list(b.units(UnitTypeId.ROACH)))
                )
                roach_bonus = min(roach_count * 1, 10)  # Max 10% bonus
                win_rate += roach_bonus

                if win_rate < 50:
                    advice = "💡 Need more Ravagers/Roaches"
                elif win_rate >= 65:
                    advice = "✅ Excellent counter (Ravager vs Mech)"
                else:
                    advice = "⚠️ Building Ravagers..."

            elif enemy_tech == "BIO":
                # Against bio: Banelings and Zerglings are key
                base_rate = 35
                baneling_bonus = min(baneling_count * 4, 40)  # Max 40% bonus
                win_rate = base_rate + baneling_bonus

                # Zergling bonus (swarm)
                win_rate += min(zergling_count * 0.5, 15)  # Max 15% bonus

                # Check for Baneling speed upgrade
                has_baneling_speed = False
                if hasattr(b, "state") and hasattr(b.state, "upgrades"):
                    upgrades = b.state.upgrades
                    # Try both possible upgrade IDs
                    centrifugal_upgrade_id = getattr(UpgradeId, "CENTRIFUGALHOOKS", None)
                    if not centrifugal_upgrade_id:
                        centrifugal_upgrade_id = getattr(UpgradeId, "CENTRIFUGAL_HOOKS", None)
                    if centrifugal_upgrade_id and centrifugal_upgrade_id in upgrades:
                        has_baneling_speed = True

                if has_baneling_speed:
                    win_rate += 15  # Speed upgrade adds 15% bonus

                if win_rate < 50:
                    advice = "💡 Need more Banelings + Speed Upgrade"
                elif win_rate >= 60:
                    advice = "✅ Excellent counter (Baneling vs Bio)"
                else:
                    advice = "⚠️ Building Banelings..."

            # 4. Limit win rate between 10% and 95%
            win_rate = max(10, min(95, int(win_rate)))

            # 5. 승률을 클래스 변수에 저장 (CombatManager에서 사용)
            self.last_calculated_win_rate = float(win_rate)

            # 6. Send win rate comparison to chat (reduced frequency for CPU optimization)
            current_iteration = getattr(b, "iteration", 0)
            # 🚀 PERFORMANCE: Reduced chat frequency - only send every 500 frames (~22 seconds)
            if current_iteration % 500 == 0:
                compare_msg = f"🔍 VS_{enemy_tech} | Win Rate: {win_rate}% vs {100 - win_rate}%"
                await b.chat_send(compare_msg)
                await b.chat_send(advice)

        except Exception as e:
            # Silent fail - don't interrupt game flow
            current_iteration = getattr(self.bot, "iteration", 0)
            if current_iteration % 500 == 0:
                print(f"[WARNING] Failed to display matchup win rate: {e}")
