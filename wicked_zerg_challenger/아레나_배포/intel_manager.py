# -*- coding: utf-8 -*-
"""
================================================================================
                    🧠 인텔 매니저 (intel_manager.py)
================================================================================
전역 지능 통합 - Blackboard 패턴 구현

핵심 역할:
    1. 모든 매니저가 공유하는 중앙 정보 저장소
    2. 적 정보 분석 및 위협 평가
    3. 전략적 의사결정 지원
    4. 매니저 간 신호 전달

설계 패턴:
    - Blackboard Pattern: 공유 메모리를 통한 모듈 간 통신
    - Observer Pattern: 상태 변화 시 관련 모듈에 알림
================================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from typing import TYPE_CHECKING, Dict, List, Optional, Set

if TYPE_CHECKING:
    from wicked_zerg_bot_pro import WickedZergBotPro

from dataclasses import dataclass, field
from enum import Enum, IntEnum, auto
from typing import Dict, List, Optional, Set

from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit


class StrategyMode(Enum):
    """전략 모드"""

    OPENING = auto()  # 오프닝
    MACRO = auto()  # 경제 중심
    DEFENSE = auto()  # 방어
    RUSH = auto()  # 러시 공격
    ALL_IN = auto()  # 올인
    LATE_GAME = auto()  # 후반전


class ThreatLevel(IntEnum):
    """
    위협 수준

    IntEnum을 사용하여 숫자 비교 연산(>=, <=, >, <)이 가능하도록 함
    """

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EnemyIntel:
    """적 정보 데이터 클래스"""

    race: Optional[str] = None

    # 감지된 유닛/건물
    units_seen: Set[UnitTypeId] = field(default_factory=set)
    buildings_seen: Set[UnitTypeId] = field(default_factory=set)

    # 특수 상태
    has_air: bool = False
    has_cloaked: bool = False
    is_rushing: bool = False
    is_expanding: bool = False

    # 수치 정보
    army_supply: int = 0
    worker_count: int = 0
    base_count: int = 1


@dataclass
class CombatIntel:
    """전투 정보 데이터 클래스"""

    under_attack: bool = False
    attack_location: Optional[Point2] = None

    # 아군 상태
    army_gathered: bool = False
    is_attacking: bool = False
    is_retreating: bool = False

    # 손실 추적
    initial_army_count: int = 0
    current_army_count: int = 0
    loss_ratio: float = 0.0


@dataclass
class ProductionIntel:
    """생산 정보 데이터 클래스"""

    # 필요한 유닛
    needed_unit_type: Optional[UnitTypeId] = None
    needs_detection: bool = False
    needs_anti_air: bool = False

    # 라바 배분
    larva_priority: str = "balanced"  # "army", "economy", "balanced"
    available_larva: int = 0

    # 테크 상태
    speed_upgrade_done: bool = False
    lair_done: bool = False


@dataclass
class EconomyIntel:
    """경제 정보 데이터 클래스"""

    minerals: int = 0
    vespene: int = 0
    worker_count: int = 0
    base_count: int = 1

    # 상태
    should_expand: bool = False
    gas_reduced: bool = False
    supply_blocked: bool = False


class IntelManager:
    """
    인텔 매니저 - 전역 지능 통합 (Blackboard)

    💡 설계 철학:
        모든 매니저가 이 클래스를 참조하여 정보를 공유합니다.
        CombatManager가 적의 은폐 유닛을 발견하면,
        ProductionManager가 즉시 감시군주를 생산하는 식의
        유기적인 협력이 가능해집니다.

    사용 예시:
        # 메인 봇에서 초기화
        self.intel = IntelManager(self)

        # 매니저에서 정보 읽기
        if self.bot.intel.enemy.has_cloaked:
            self._produce_overseer()

        # 매니저에서 정보 쓰기
        self.bot.intel.enemy.has_cloaked = True
    """

    def __init__(self, bot: "WickedZergBotPro"):
        """
        Args:
            bot: 메인 봇 인스턴스
        """
        self.bot = bot

        # 📊 데이터 저장소 (Blackboard)

        # 적 정보
        self.enemy = EnemyIntel()

        # 전투 정보
        self.combat = CombatIntel()

        # 생산 정보
        self.production = ProductionIntel()

        # 경제 정보
        self.economy = EconomyIntel()

        # 🎯 전략적 상태

        # 현재 전략 모드
        self.strategy_mode: StrategyMode = StrategyMode.OPENING

        # 위협 수준
        self.threat_level: ThreatLevel = ThreatLevel.NONE

        # ⏱️ 시간 추적

        # 마지막 정찰 시간
        self.last_recon_time: float = 0.0

        # 마지막 적 발견 시간
        self.last_enemy_seen_time: float = 0.0

        # 적 유닛 마지막 위치 추적 (시야에서 사라진 적 추격용)
        self.enemy_last_positions: Dict[int, Point2] = {}  # {unit_tag: last_position}
        self.enemy_last_seen_time: Dict[int, float] = {}  # {unit_tag: last_seen_time}
        self.PURSUE_TIMEOUT = 5.0  # 5초 이내에 사라진 적만 추격

        # 마지막 공격 시간
        self.last_attack_time: float = 0.0

        # 📍 위치 정보

        # 적 기지 위치들
        self.enemy_base_locations: List[Point2] = []

        # 위험 지역
        self.danger_zones: List[Point2] = []

        # 🎯 타겟팅 캐시 (CombatManager 성능 최적화)
        # 현재 구역의 주 타겟 (매 프레임 재계산 대신 캐싱)
        self.cached_primary_target: Optional[Unit] = None
        self.cached_target_priority: Dict[int, float] = {}  # enemy.tag -> priority score
        self.last_target_update: int = 0
        self.target_cache_interval: int = 4  # 4프레임마다 타겟 우선순위 재계산

        # 🔔 이벤트 플래그 (매니저 간 신호)

        self.signals: Dict[str, bool] = {
            "need_overseer": False,  # 감시군주 필요
            "need_spore": False,  # 포자 촉수 필요
            "need_spine": False,  # 가시 촉수 필요
            "stop_droning": False,  # 드론 생산 중단
            "emergency_defense": False,  # 긴급 방어
            "all_in_attack": False,  # 올인 공격
            "enemy_attacking_our_bases": False,  # 상대 주력군이 우리 멀티 공격 중
            "counter_attack_opportunity": False,  # 역습 기회 (상대 본진 공백)
        }

        # 🔍 상대 테크 정보 (맞춤형 유닛 조합용)

        self.enemy_tech_detected: Dict[str, any] = {  # type: ignore[type-arg]
            "air_tech": False,  # 공중 테크 (Starport/Stargate)
            "mech_tech": False,  # 메카닉 테크 (Factory/Robotics Facility)
            "bio_tech": False,  # 바이오 테크 (Barracks/Gateway 다수)
            "detected_time": 0.0,  # 테크 감지 시간
        }

        # 상대 테크 타입 (문자열: "AIR", "MECHANIC", "BIO", "GROUND")
        self.enemy_tech: str = "GROUND"

        # 🚀 성능 최적화: 유닛 캐싱 (중복 연산 방지)
        # 모든 매니저가 공유하는 캐시된 유닛 정보

        # 캐시된 유닛 컬렉션 (매니저들이 직접 bot.units() 호출 대신 사용)
        # 🚀 성능 최적화: 모든 매니저가 공유하는 중앙 캐시
        self.cached_workers = None
        self.cached_larva = None
        self.cached_townhalls = None
        self.cached_military = None  # 전투 유닛만 필터링된 캐시
        self.cached_enemy_units = None
        self.cached_enemy_structures = None

        # 추가 캐시: 자주 사용되는 유닛 타입별 캐시
        self.cached_zerglings = None
        self.cached_roaches = None
        self.cached_hydralisks = None
        self.cached_overlords = None
        self.cached_queens = None
        self.cached_structures = None  # 모든 건물

        # 캐시 갱신 주기 (프레임 단위)
        self.cache_refresh_interval = 8  # 8프레임마다 캐시 갱신 (기존 on_step 주기와 동일)
        self.last_cache_update = 0

    # 🔄 업데이트 메서드

    def update(self, iteration: int = 0):
        """
        매 프레임 호출 - 정보 업데이트 및 캐싱

        💡 호출 순서:
            1. on_step 시작 시 가장 먼저 호출
            2. 각 매니저가 실행되기 전에 최신 정보 확보

        Args:
            iteration: 현재 프레임 번호 (캐시 갱신 주기 계산용)
        """
        b = self.bot

        # 🚀 성능 최적화: 유닛 캐싱 (중복 연산 방지)
        # 모든 매니저가 공유하는 캐시된 유닛 정보를 한 번만 계산
        should_refresh_cache = (
            iteration - self.last_cache_update >= self.cache_refresh_interval
            or self.cached_workers is None
        )

        if should_refresh_cache:
            try:
                # 🚀 핵심 유닛 캐싱 (가장 자주 사용되는 유닛)
                # Workers 캐싱
                self.cached_workers = b.workers if hasattr(b, "workers") else None

                # Larva 캐싱
                self.cached_larva = b.larva if hasattr(b, "larva") else None

                # Townhalls 캐싱
                self.cached_townhalls = b.townhalls if hasattr(b, "townhalls") else None

                # Structures 캐싱 (모든 건물)
                self.cached_structures = b.structures if hasattr(b, "structures") else None

                # Military units 캐싱 (전투 유닛만 필터링)
                # bot.combat_unit_types가 정의되어 있다면 사용, 없으면 기본 전투 유닛 타입 사용
                combat_types = getattr(
                    b,
                    "combat_unit_types",
                    {
                        UnitTypeId.ZERGLING,
                        UnitTypeId.ROACH,
                        UnitTypeId.HYDRALISK,
                        UnitTypeId.MUTALISK,
                        UnitTypeId.CORRUPTOR,
                        UnitTypeId.ULTRALISK,
                        UnitTypeId.BANELING,
                        UnitTypeId.RAVAGER,
                        UnitTypeId.LURKER,
                        UnitTypeId.VIPER,
                        UnitTypeId.BROODLORD,
                        UnitTypeId.SWARMHOSTMP,
                    },
                )
                if hasattr(b, "units"):
                    self.cached_military = b.units.filter(
                        lambda u: u.type_id in combat_types and u.is_ready
                    )
                else:
                    self.cached_military = None

                # 🚀 자주 사용되는 유닛 타입별 캐싱 (중복 필터링 방지)
                # 모든 매니저가 공유하는 유닛 타입별 캐시 - 한 번만 계산하고 재사용
                if hasattr(b, "units"):
                    # 전투 유닛 캐싱
                    self.cached_zerglings = b.units(UnitTypeId.ZERGLING).ready
                    self.cached_roaches = b.units(UnitTypeId.ROACH).ready
                    self.cached_hydralisks = b.units(UnitTypeId.HYDRALISK).ready
                    self.cached_ravagers = b.units(UnitTypeId.RAVAGER).ready
                    self.cached_lurkers = b.units(UnitTypeId.LURKER).ready
                    self.cached_banelings = b.units(UnitTypeId.BANELING).ready
                    self.cached_mutalisks = b.units(UnitTypeId.MUTALISK).ready
                    # 지원 유닛 캐싱
                    self.cached_overlords = b.units(UnitTypeId.OVERLORD)
                    self.cached_queens = b.units(UnitTypeId.QUEEN).ready
                else:
                    self.cached_zerglings = None
                    self.cached_roaches = None
                    self.cached_hydralisks = None
                    self.cached_overlords = None
                    self.cached_queens = None
                    self.cached_ravagers = None
                    self.cached_lurkers = None
                    self.cached_banelings = None
                    self.cached_mutalisks = None
                    self.cached_spine_crawlers = None

                # 🚀 건물 캐싱 (자주 체크되는 건물들) - ProductionManager에서 자주 사용
                if hasattr(b, "structures"):
                    self.cached_spawning_pools = b.structures(UnitTypeId.SPAWNINGPOOL).ready
                    self.cached_roach_warrens = b.structures(UnitTypeId.ROACHWARREN).ready
                    self.cached_hydralisk_dens = b.structures(UnitTypeId.HYDRALISKDEN).ready
                    self.cached_baneling_nests = b.structures(UnitTypeId.BANELINGNEST).ready
                    self.cached_evolution_chambers = b.structures(UnitTypeId.EVOLUTIONCHAMBER).ready
                    self.cached_spore_crawlers = b.structures(UnitTypeId.SPORECRAWLER).ready
                    self.cached_spine_crawlers = b.structures(UnitTypeId.SPINECRAWLER).ready
                    # 테크 건물 캐싱
                    self.cached_lairs = b.structures(UnitTypeId.LAIR).ready
                    self.cached_hives = b.structures(UnitTypeId.HIVE).ready
                else:
                    self.cached_spawning_pools = None
                    self.cached_roach_warrens = None
                    self.cached_hydralisk_dens = None
                    self.cached_baneling_nests = None
                    self.cached_evolution_chambers = None
                    self.cached_spore_crawlers = None
                    self.cached_spine_crawlers = None
                    self.cached_lairs = None
                    self.cached_hives = None

                # Enemy units 캐싱
                self.cached_enemy_units = getattr(b, "enemy_units", None)

                # Enemy structures 캐싱
                self.cached_enemy_structures = getattr(b, "enemy_structures", None)

                self.last_cache_update = iteration
            except Exception:
                # 캐싱 실패 시 기본값 유지 (안전장치)
                pass

        # 경제 정보 업데이트
        self._update_economy()

        # 적 정보 업데이트
        self._update_enemy_intel()

        # 전투 정보 업데이트
        self._update_combat_intel()

        # 상대 테크 정보 업데이트 (ScoutManager에서 감지한 정보 반영)
        self._update_enemy_tech()

        # 위협 수준 평가
        self._evaluate_threat()

        # 전략 모드 결정
        self._decide_strategy()

        # 신호 처리
        self._process_signals()

    def _update_economy(self):
        """경제 정보 업데이트"""
        b = self.bot

        # 🛡️ 안전장치: townhalls가 없으면 기본값 설정
        try:
            self.economy.minerals = b.minerals
            self.economy.vespene = b.vespene
        except Exception:
            self.economy.minerals = 0
            self.economy.vespene = 0

        try:
            # 🚀 캐시된 workers 사용 (중복 연산 방지)
            workers = self.cached_workers if self.cached_workers else b.workers
            if workers and hasattr(workers, "exists") and workers.exists:
                self.economy.worker_count = (
                    workers.amount if hasattr(workers, "amount") else len(list(workers))
                )
            else:
                self.economy.worker_count = 0
        except Exception:
            self.economy.worker_count = 0

        try:
            # 🚀 캐시된 townhalls 사용 (중복 연산 방지)
            townhalls = self.cached_townhalls if self.cached_townhalls else b.townhalls
            if townhalls and hasattr(townhalls, "exists") and townhalls.exists:
                self.economy.base_count = (
                    townhalls.amount if hasattr(townhalls, "amount") else len(list(townhalls))
                )
            else:
                self.economy.base_count = 0
                self.economy.should_expand = False
                return  # Micro Ladder: 경제 정보 업데이트 중단
        except Exception:
            self.economy.base_count = 0
            self.economy.should_expand = False
            return

        # 확장 필요 여부 (townhalls가 있을 때만)
        if self.economy.base_count > 0:
            if self.economy.worker_count >= 16 * self.economy.base_count:
                self.economy.should_expand = True
            else:
                self.economy.should_expand = False
        else:
            self.economy.should_expand = False

        # 서플라이 블록 체크
        self.economy.supply_blocked = b.supply_left <= 0

    def _update_enemy_tech(self):
        """상대 테크 정보 업데이트 (ScoutManager에서 감지한 정보 반영 및 직접 스캔)"""
        b = self.bot

        # 기본값 설정
        self.enemy_tech = "GROUND"

        # 1. ScoutManager에서 테크 정보 가져오기
        if hasattr(b, "scout") and b.scout:
            scout_tech_info = getattr(b.scout, "enemy_tech_detected", {})
            if scout_tech_info:
                # ScoutManager의 테크 정보를 IntelManager에 반영
                self.enemy_tech_detected["air_tech"] = scout_tech_info.get("air_tech", False)
                self.enemy_tech_detected["mech_tech"] = scout_tech_info.get("mech_tech", False)
                self.enemy_tech_detected["bio_tech"] = scout_tech_info.get("bio_tech", False)
                self.enemy_tech_detected["detected_time"] = scout_tech_info.get(
                    "detected_time", 0.0
                )

        # 2. 직접 적 건물 스캔하여 테크 분류
        try:
            enemy_structures = getattr(b, "enemy_structures", [])
            if enemy_structures:
                # 공중 테크 감지
                has_stargate = any(s.type_id == UnitTypeId.STARGATE for s in enemy_structures)
                has_starport = any(s.type_id == UnitTypeId.STARPORT for s in enemy_structures)
                if has_stargate or has_starport:
                    self.enemy_tech = "AIR"
                    self.enemy_tech_detected["air_tech"] = True
                    # bot.enemy_tech도 업데이트
                    if hasattr(b, "enemy_tech"):
                        setattr(b, "enemy_tech", "AIR")
                    return

                # 메카닉 테크 감지
                has_robotics = any(
                    s.type_id == UnitTypeId.ROBOTICSFACILITY for s in enemy_structures
                )
                has_factory = any(s.type_id == UnitTypeId.FACTORY for s in enemy_structures)
                if has_robotics or has_factory:
                    self.enemy_tech = "MECHANIC"
                    self.enemy_tech_detected["mech_tech"] = True
                    # bot.enemy_tech도 업데이트
                    if hasattr(b, "enemy_tech"):
                        setattr(b, "enemy_tech", "MECHANIC")
                    return

                # 바이오 테크 감지 (병영/관문 다수)
                barracks_count = sum(
                    1 for s in enemy_structures if s.type_id == UnitTypeId.BARRACKS
                )
                gateway_count = sum(1 for s in enemy_structures if s.type_id == UnitTypeId.GATEWAY)
                if barracks_count + gateway_count >= 2:
                    self.enemy_tech = "BIO"
                    self.enemy_tech_detected["bio_tech"] = True
                    # bot.enemy_tech도 업데이트
                    if hasattr(b, "enemy_tech"):
                        setattr(b, "enemy_tech", "BIO")
                    return
        except Exception:
            # 에러 발생 시 기본값 유지
            pass

        # 3. enemy_tech_detected 기반으로 enemy_tech 설정
        if self.enemy_tech_detected.get("air_tech", False):
            self.enemy_tech = "AIR"
        elif self.enemy_tech_detected.get("mech_tech", False):
            self.enemy_tech = "MECHANIC"
        elif self.enemy_tech_detected.get("bio_tech", False):
            self.enemy_tech = "BIO"

        # 4. bot.enemy_tech와 bot.enemy_tech_detected도 동기화
        if hasattr(b, "enemy_tech"):
            setattr(b, "enemy_tech", self.enemy_tech)
        if hasattr(b, "enemy_tech_detected"):
            setattr(b, "enemy_tech_detected", self.enemy_tech_detected)

    def _update_enemy_intel(self):
        """적 정보 업데이트"""
        b = self.bot

        # 적 유닛 감지 - 최신 burnysc2 API 사용
        # 🛡️ 방어적 프로그래밍: getattr 사용
        enemy_units = getattr(b, "enemy_units", [])
        current_enemy_tags = set()

        for enemy in enemy_units:
            current_enemy_tags.add(enemy.tag)
            self.enemy.units_seen.add(enemy.type_id)
            self.last_enemy_seen_time = b.time

            # 적 유닛의 마지막 위치 업데이트 (추격용)
            try:
                self.enemy_last_positions[enemy.tag] = enemy.position
                self.enemy_last_seen_time[enemy.tag] = b.time
            except Exception:
                pass

            # 공중 유닛 체크
            if enemy.is_flying:
                self.enemy.has_air = True
                self.signals["need_spore"] = True

            # 은폐 유닛 체크
            if enemy.type_id in [
                UnitTypeId.DARKTEMPLAR,
                UnitTypeId.BANSHEE,
                UnitTypeId.GHOST,
                UnitTypeId.LURKER,
                UnitTypeId.WIDOWMINE,
            ]:
                self.enemy.has_cloaked = True
                self.signals["need_overseer"] = True

        # 시야에서 사라진 적 유닛 정리 (오래된 것만)
        tags_to_remove = []
        for tag in self.enemy_last_positions:
            if tag not in current_enemy_tags:
                # 5초 이상 사라진 적은 추격 목록에서 제거
                if b.time - self.enemy_last_seen_time.get(tag, 0) > self.PURSUE_TIMEOUT:
                    tags_to_remove.append(tag)

        for tag in tags_to_remove:
            self.enemy_last_positions.pop(tag, None)
            self.enemy_last_seen_time.pop(tag, None)

        # 적 건물 감지 - 최신 burnysc2 API 사용
        # 🛡️ 방어적 프로그래밍: getattr 사용
        enemy_structures = getattr(b, "enemy_structures", [])
        for building in enemy_structures:
            self.enemy.buildings_seen.add(building.type_id)
            self.last_enemy_seen_time = b.time

        # 적 기지 수
        base_types = {
            UnitTypeId.COMMANDCENTER,
            UnitTypeId.NEXUS,
            UnitTypeId.HATCHERY,
            UnitTypeId.ORBITALCOMMAND,
            UnitTypeId.PLANETARYFORTRESS,
            UnitTypeId.LAIR,
            UnitTypeId.HIVE,
        }
        # 🛡️ 방어적 코드: getattr 사용
        enemy_structures = getattr(b, "enemy_structures", [])
        enemy_bases = [s for s in enemy_structures if s.type_id in base_types]
        self.enemy.base_count = max(1, len(enemy_bases))
        self.enemy.is_expanding = len(enemy_bases) >= 2

        # 상대 병력 공백 감지 (Serral 스타일 역습)
        # 상대 주력군이 우리 멀티를 치러 나온 것을 감지
        if enemy_units:
            # 우리 멀티 근처에 적 병력이 있는지 확인
            townhalls = [th for th in b.townhalls]
            enemies_at_our_bases = []
            for th in townhalls:
                enemies_near_base = [e for e in enemy_units if e.distance_to(th.position) < 25]
                if len(enemies_near_base) >= 5:  # 5기 이상이면 주력군으로 판단
                    enemies_at_our_bases.extend(enemies_near_base)

            # 상대 주력군이 우리 멀티에 있으면 신호 설정
            if enemies_at_our_bases:
                self.signals["enemy_attacking_our_bases"] = True
                # 상대 본진에 적 병력이 적은지 확인 (공백 감지)
                if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    enemy_main = b.enemy_start_locations[0]
                    enemies_at_enemy_main = [
                        e for e in enemy_units if e.distance_to(enemy_main) < 30
                    ]

                    # 상대 본진에 적 병력이 적으면 (우리보다 적으면) 역습 신호
                    if len(enemies_at_enemy_main) < b.supply_army // 2:
                        self.signals["counter_attack_opportunity"] = True
            else:
                self.signals["enemy_attacking_our_bases"] = False
                self.signals["counter_attack_opportunity"] = False

        # 🎯 타겟팅 우선순위 캐싱 (CombatManager 성능 최적화)
        # 매 프레임 모든 적 유닛의 우선순위를 계산하는 대신, 캐싱하여 재사용
        current_iteration = getattr(b, "iteration", 0)
        if current_iteration - self.last_target_update >= self.target_cache_interval:
            self._update_target_priority_cache(enemy_units, b)
            self.last_target_update = current_iteration

    def _update_combat_intel(self):
        """전투 정보 업데이트"""
        b = self.bot

        # 공격 받는 중인지 체크
        # 🛡️ 방어적 코드: getattr 사용
        enemy_units = getattr(b, "enemy_units", [])
        enemies_near_base = [u for u in enemy_units if u.distance_to(b.start_location) < 30]
        self.combat.under_attack = len(enemies_near_base) >= 3

        if self.combat.under_attack and enemies_near_base:
            # 중심점 계산
            x_sum = sum(u.position.x for u in enemies_near_base)
            y_sum = sum(u.position.y for u in enemies_near_base)
            self.combat.attack_location = Point2(
                (x_sum / len(enemies_near_base), y_sum / len(enemies_near_base))
            )
            self.signals["emergency_defense"] = True
        else:
            self.signals["emergency_defense"] = False

        # 아군 병력 수
        self.combat.current_army_count = b.supply_army

    def _evaluate_threat(self):
        """위협 수준 평가"""
        b = self.bot

        threat_score = 0

        # 공격 받는 중
        if self.combat.under_attack:
            threat_score += 3

        # 러시 감지
        if self.enemy.is_rushing:
            threat_score += 2

        # 은폐 유닛
        if self.enemy.has_cloaked:
            threat_score += 1

        # 공중 유닛
        if self.enemy.has_air:
            threat_score += 1

        # 위협 수준 결정
        if threat_score >= 4:
            self.threat_level = ThreatLevel.CRITICAL
        elif threat_score >= 3:
            self.threat_level = ThreatLevel.HIGH
        elif threat_score >= 2:
            self.threat_level = ThreatLevel.MEDIUM
        elif threat_score >= 1:
            self.threat_level = ThreatLevel.LOW
        else:
            self.threat_level = ThreatLevel.NONE

    def get_pursue_targets(self) -> List[Point2]:
        """
        시야에서 사라진 적 유닛의 마지막 위치 반환 (추격용)

        Returns:
            List[Point2]: 추격할 적 유닛의 마지막 위치 리스트
        """
        b = self.bot
        pursue_targets = []

        # 5초 이내에 사라진 적만 추격
        for tag, last_pos in self.enemy_last_positions.items():
            last_seen = self.enemy_last_seen_time.get(tag, 0)
            if b.time - last_seen <= self.PURSUE_TIMEOUT:
                pursue_targets.append(last_pos)

        return pursue_targets

    def _decide_strategy(self):
        """전략 모드 결정"""
        b = self.bot

        # 긴급 방어
        if self.threat_level == ThreatLevel.CRITICAL:
            self.strategy_mode = StrategyMode.DEFENSE
            self.signals["stop_droning"] = True
            return

        # 시간 기반 기본 전략
        if b.time < 120:  # 2분
            self.strategy_mode = StrategyMode.OPENING
        elif b.time < 300:  # 5분
            if self.threat_level >= ThreatLevel.MEDIUM:
                self.strategy_mode = StrategyMode.DEFENSE
            else:
                self.strategy_mode = StrategyMode.MACRO
        elif b.time < 600:  # 10분
            if self.enemy.is_expanding and b.supply_army >= 60:
                self.strategy_mode = StrategyMode.RUSH
            else:
                self.strategy_mode = StrategyMode.MACRO
        else:
            self.strategy_mode = StrategyMode.LATE_GAME

        # 드론 생산 재개
        if self.threat_level <= ThreatLevel.LOW:
            self.signals["stop_droning"] = False

    def _process_signals(self):
        """신호 처리 - 매니저 간 협력"""
        b = self.bot

        # 감시군주 필요 → 생산 우선순위 설정
        if self.signals["need_overseer"]:
            self.production.needs_detection = True
            self.production.needed_unit_type = UnitTypeId.OVERSEER

        # 대공 필요
        if self.enemy.has_air:
            self.production.needs_anti_air = True
            if UnitTypeId.HYDRALISK not in self.enemy.units_seen:
                self.production.needed_unit_type = UnitTypeId.HYDRALISK

        # 라바 우선순위 결정
        if self.signals["stop_droning"] or self.combat.under_attack:
            self.production.larva_priority = "army"
        elif self.economy.worker_count < 50:
            self.production.larva_priority = "economy"
        else:
            self.production.larva_priority = "balanced"

    # 📊 상태 조회 메서드

    def get_status_report(self) -> str:
        """현재 상태 보고서 반환"""
        return f"""
========== Intel Report ==========
Strategy: {self.strategy_mode.name}
Threat Level: {self.threat_level.name}

[Enemy]
- Race: {self.enemy.race}
- Has Air: {self.enemy.has_air}
- Has Cloaked: {self.enemy.has_cloaked}
- Is Rushing: {self.enemy.is_rushing}
- Bases: {self.enemy.base_count}

[Combat]
- Under Attack: {self.combat.under_attack}
- Army Gathered: {self.combat.army_gathered}
- Loss Ratio: {self.combat.loss_ratio:.1%}

[Economy]
- Workers: {self.economy.worker_count}
- Bases: {self.economy.base_count}
- Should Expand: {self.economy.should_expand}

[Signals]
- Need Overseer: {self.signals["need_overseer"]}
- Emergency Defense: {self.signals["emergency_defense"]}
- Stop Droning: {self.signals["stop_droning"]}
==================================
"""

    def should_attack(self) -> bool:
        """
        공격 시작 여부 판단 (Serral 스타일)

        Serral의 공격 트리거 조건:
            1. 인구수 150-160 법칙: 일벌레 66기 이상, 전체 인구수 160 도달
            2. 업그레이드 완료 시점: 발업 또는 가시지옥 사거리 업 완료 직후
            3. 상대 병력 공백 감지: 상대 주력군이 멀티 공격 중이면 역습
            4. 상대 종족별 다른 공격 임계값
        """
        b = self.bot

        # 1. 인구수 150-160 법칙 (The 160 Rule)
        workers = [w for w in b.workers]
        worker_count = len(workers)
        total_supply = b.supply_used

        # 일벌레 66기 이상 (3개 베이스 최적화) + 전체 인구수 160 도달
        if worker_count >= 66 and total_supply >= 160:
            if getattr(b, "iteration", 0) % 100 == 0:
                print(
                    f"[SERRAL ATTACK] ✅ 인구수 160 법칙 트리거! 일벌레: {worker_count}, 인구수: {total_supply}"
                )
            return True

        # 2. 업그레이드 완료 시점 (Upgrade Spike)
        # 저글링 발업 완료 직후
        from sc2.ids.upgrade_id import UpgradeId

        if UpgradeId.ZERGLINGMOVEMENTSPEED in b.state.upgrades:
            # 발업이 방금 완료되었는지 확인 (이전 프레임에 없었고 지금 있으면)
            if not hasattr(self, "_speed_upgrade_triggered"):
                self._speed_upgrade_triggered = True
                if getattr(b, "iteration", 0) % 100 == 0:
                    print(f"[SERRAL ATTACK] ✅ 발업 완료! 모든 병력 전진!")
                return True

        # 가시지옥 사거리 업그레이드 완료 직후
        if UpgradeId.LURKERRANGE in b.state.upgrades:
            # 사거리 업이 방금 완료되었는지 확인
            if not hasattr(self, "_lurker_range_triggered"):
                self._lurker_range_triggered = True
                lurkers = [u for u in b.units(UnitTypeId.LURKER) if u.is_ready]
                if len(lurkers) >= 3:  # 가시지옥 3마리 이상일 때만
                    if getattr(b, "iteration", 0) % 100 == 0:
                        print(
                            f"[SERRAL ATTACK] ✅ 가시지옥 사거리 업 완료! ({len(lurkers)}마리) 전진!"
                        )
                    return True

        # 3. 상대 병력 공백 감지 (Intel-based Counter Attack)
        # 상대 주력군이 우리 멀티를 치러 나온 것을 감지
        enemy_units = getattr(b, "enemy_units", [])
        if enemy_units:
            # 우리 멀티 근처에 적 병력이 있는지 확인
            townhalls = [th for th in b.townhalls]
            enemies_at_our_bases = []
            for th in townhalls:
                enemies_near_base = [e for e in enemy_units if e.distance_to(th.position) < 25]
                if len(enemies_near_base) >= 5:  # 5기 이상이면 주력군으로 판단
                    enemies_at_our_bases.extend(enemies_near_base)

            # 상대 주력군이 우리 멀티에 있고, 우리 병력이 충분하면 역습
            if enemies_at_our_bases and b.supply_army >= 50:
                # 상대 본진에 적 병력이 적은지 확인 (공백 감지)
                if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    enemy_main = b.enemy_start_locations[0]
                    enemies_at_enemy_main = [
                        e for e in enemy_units if e.distance_to(enemy_main) < 30
                    ]

                    # 상대 본진에 적 병력이 적으면 (우리보다 적으면) 역습
                    if len(enemies_at_enemy_main) < b.supply_army // 2:
                        if getattr(b, "iteration", 0) % 100 == 0:
                            print(
                                f"[SERRAL ATTACK] ✅ 역습 타이밍! 상대 주력군이 멀티 공격 중, 본진 공백 감지!"
                            )
                        return True

        # 4. 상대 종족별 다른 공격 임계값
        enemy_race = self.enemy.race
        army_supply = b.supply_army

        # vs 테란: 바퀴/궤멸충 위주 시 인구수 150 이상
        if enemy_race == "Terran" or enemy_race == "TERRAN":
            roaches = [u for u in b.units(UnitTypeId.ROACH)]
            ravagers = [u for u in b.units(UnitTypeId.RAVAGER)]
            if len(roaches) + len(ravagers) >= 10 and army_supply >= 150:
                if getattr(b, "iteration", 0) % 100 == 0:
                    print(
                        f"[SERRAL ATTACK] ✅ vs 테란: 바퀴/궤멸충 타이밍! (인구수: {army_supply})"
                    )
                return True

        # vs 프로토스: 히드라/가시지옥 위주 시 인구수 140 이상
        elif enemy_race == "Protoss" or enemy_race == "PROTOSS":
            hydras = [u for u in b.units(UnitTypeId.HYDRALISK)]
            lurkers = [u for u in b.units(UnitTypeId.LURKER) if u.is_ready]
            if (len(hydras) >= 8 or len(lurkers) >= 5) and army_supply >= 140:
                if getattr(b, "iteration", 0) % 100 == 0:
                    print(
                        f"[SERRAL ATTACK] ✅ vs 프로토스: 히드라/가시지옥 타이밍! (인구수: {army_supply})"
                    )
                return True

        # vs 저그: 저글링/맹독충 위주 시 인구수 130 이상
        elif enemy_race == "Zerg" or enemy_race == "ZERG":
            zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]
            banelings = [u for u in b.units(UnitTypeId.BANELING)]
            if (len(zerglings) >= 20 or len(banelings) >= 5) and army_supply >= 130:
                if getattr(b, "iteration", 0) % 100 == 0:
                    print(
                        f"[SERRAL ATTACK] ✅ vs 저그: 저글링/맹독충 타이밍! (인구수: {army_supply})"
                    )
                return True

        # 기존 조건 (하위 호환성)
        # 적이 확장 중이고 병력이 충분하면 공격
        if self.enemy.is_expanding and army_supply >= 60:
            return True

        # 병력이 많으면 공격
        if army_supply >= 100:
            return True

        # 올인 신호
        if self.signals.get("all_in_attack", False):
            return True

        return False

    def should_defend(self) -> bool:
        """방어 모드 여부 판단"""
        return (
            self.combat.under_attack
            or self.threat_level >= ThreatLevel.HIGH
            or self.signals["emergency_defense"]
        )

    def get_priority_unit(self) -> Optional[UnitTypeId]:
        """우선 생산 유닛 반환"""
        if self.production.needs_detection:
            return UnitTypeId.OVERSEER
        if self.production.needs_anti_air:
            return UnitTypeId.HYDRALISK
        return self.production.needed_unit_type

    def _update_target_priority_cache(self, enemy_units: List, bot):
        """
        타겟팅 우선순위 캐시 업데이트

        🚀 성능 최적화: 매 프레임 모든 적 유닛의 우선순위를 계산하는 대신,
        4프레임마다 한 번만 계산하여 캐싱

        Args:
            enemy_units: 적 유닛 리스트
            bot: 봇 인스턴스 (TARGET_PRIORITY 접근용)
        """
        try:
            from config import TARGET_PRIORITY

            # 타겟 우선순위 딕셔너리 초기화
            self.cached_target_priority = {}

            if not enemy_units:
                self.cached_primary_target = None
                return

            # 각 적 유닛의 우선순위 점수 계산
            for enemy in enemy_units:
                try:
                    # 기본 우선순위 (TARGET_PRIORITY에서 가져옴)
                    base_priority = TARGET_PRIORITY.get(enemy.type_id, 1)

                    # 체력 비율 보너스 (체력이 낮을수록 우선순위 높음)
                    health_bonus = (1 - enemy.health_percentage) * 5

                    # 최종 우선순위 점수
                    priority_score = base_priority + health_bonus

                    self.cached_target_priority[enemy.tag] = priority_score
                except Exception:
                    # 유닛 정보 접근 실패 시 기본값
                    self.cached_target_priority[enemy.tag] = 1.0

            # 가장 높은 우선순위의 적을 주 타겟으로 설정
            if self.cached_target_priority:
                best_target_tag = max(
                    self.cached_target_priority.keys(),
                    key=lambda tag: self.cached_target_priority[tag],
                )
                self.cached_primary_target = next(
                    (e for e in enemy_units if e.tag == best_target_tag), None
                )
            else:
                self.cached_primary_target = None

        except Exception:
            # 에러 발생 시 기본값 유지
            self.cached_primary_target = None
            self.cached_target_priority = {}
