# -*- coding: utf-8 -*-
"""
Aggressive Early Game Strategies - 초반 공격 전략 모음

전략 목록:
1. 12 Pool (12드론 저글링 러시)
2. Baneling Bust (13/12 맹독충 올인)
3. Ravager Rush (궤멸충 담즙 러시)
4. Tunneling Claws (잠복 바퀴 이동)
5. Proxy Hatchery (전진 해처리)
6. Nydus All-In (땅굴망 올인)
7. ★ Overlord Drop (대군주 드랍 견제) ★
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import math

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
except ImportError:
    UnitTypeId = None
    AbilityId = None
    UpgradeId = None
    Point2 = None

try:
    from .building_placement_helper import BuildingPlacementHelper
except ImportError:
    BuildingPlacementHelper = None


class AggressiveStrategyType(Enum):
    """공격 전략 타입"""
    NONE = "none"
    TWELVE_POOL = "12pool"           # 12드론 저글링 러시
    BANELING_BUST = "baneling_bust"  # 맹독충 올인
    RAVAGER_RUSH = "ravager_rush"    # 궤멸충 담즙 러시
    TUNNELING_CLAWS = "tunneling"    # 잠복 바퀴
    PROXY_HATCH = "proxy_hatch"      # 전진 해처리
    NYDUS_ALLIN = "nydus_allin"      # 땅굴망 올인
    OVERLORD_DROP = "overlord_drop"  # ★ 대군주 드랍 견제


class AggressiveStrategyExecutor:
    """
    공격 전략 실행기

    초반 러시/올인 전략을 상황에 맞게 선택하고 실행합니다.
    """

    def __init__(self, bot):
        self.bot = bot

        # ★ Blackboard 연동 ★
        self.blackboard = getattr(bot, "blackboard", None)

        # 건물 배치 헬퍼
        if BuildingPlacementHelper:
            self.placement_helper = BuildingPlacementHelper(bot)
        else:
            self.placement_helper = None

        # 현재 활성 전략
        self.active_strategy = AggressiveStrategyType.NONE
        self._strategy_decided = False
        self._strategy_decision_time = 0

        # 전략별 상태 추적
        self._pool_started = False
        self._lings_sent = False
        self._banelings_morphing = False
        self._ravagers_ready = False
        self._tunneling_upgrade_started = False
        self._proxy_location: Optional[Point2] = None
        self._nydus_location: Optional[Point2] = None
        self._nydus_built = False
        self._nydus_worm_tag: Optional[int] = None  # ★ Worm 추적
        self._nydus_units_sent: Set[int] = set()  # ★ 투입된 유닛 추적
        self._nydus_attack_started = False  # ★ 공격 시작 여부

        # 유닛 태그 추적
        self._rush_units: Set[int] = set()
        self._proxy_drones: Set[int] = set()
        self._drop_overlords: Set[int] = set()  # ★ 드랍 대군주
        self._overlord_drop_active = False  # ★ 드랍 활성화 여부
        self._last_drop_time = 0  # ★ 마지막 드랍 시간

        # 타이밍 설정
        self.strategy_configs = {
            AggressiveStrategyType.TWELVE_POOL: {
                "drone_limit": 12,
                "pool_timing": 0,  # 즉시
                "ling_count_attack": 6,
            },
            AggressiveStrategyType.BANELING_BUST: {
                "drone_limit": 13,
                "gas_timing": 13,  # 13드론에 가스
                "pool_timing": 12,  # 12드론에 풀
                "baneling_count": 8,
            },
            AggressiveStrategyType.RAVAGER_RUSH: {
                "roach_count": 4,
                "ravager_count": 3,
                "attack_timing": 180,  # ★ 3분으로 앞당김 (기존: 4분, 5분 제한 대응)
            },
            AggressiveStrategyType.TUNNELING_CLAWS: {
                "roach_count": 8,
                "upgrade_timing": 150,  # ★ 2:30으로 앞당김 (기존: 3분)
            },
            AggressiveStrategyType.PROXY_HATCH: {
                "proxy_timing": 45,  # ★ 45초로 앞당김 (기존: 1분)
                "spine_count": 2,
            },
            AggressiveStrategyType.NYDUS_ALLIN: {
                "lair_timing": 180,  # ★ 3분으로 앞당김 (기존: 4분)
                "nydus_timing": 240,  # ★ 4분으로 앞당김 (기존: 5분)
                "queen_count": 4,
            },
            AggressiveStrategyType.OVERLORD_DROP: {
                "ventral_sacs_timing": 150,  # ★ 2분 30초로 앞당김 (기존: 3분)
                "drop_overlord_count": 2,  # ★ 드랍용 대군주 2기
                "drop_unit_count": 16,  # ★ 저글링 8마리 (2기 탑승)
                "drop_timing": 210,  # ★ 3분 30초로 앞당김 (기존: 4분, 5분 제한 대응)
            },
        }

    def select_strategy(self, enemy_race: str) -> AggressiveStrategyType:
        """
        상대 종족에 따라 전략 선택

        Args:
            enemy_race: 상대 종족 문자열

        Returns:
            선택된 전략 타입
        """
        if self._strategy_decided:
            return self.active_strategy

        game_time = getattr(self.bot, "time", 0)

        # 30초 이후에 전략 결정
        if game_time < 30:
            return AggressiveStrategyType.NONE

        import random
        roll = random.random()

        # 50% Chance: Standard Macro (No Aggressive Strategy)
        if roll < 0.5:
            self.active_strategy = AggressiveStrategyType.NONE
            print(f"[STRATEGY] Selected: STANDARD MACRO (Safe Play)")
            self._strategy_decided = True
            return self.active_strategy

        # 50% Chance: Special Tactics (Aggressive or Cheese)
        
        # 종족별 전략 선택
        if "Terran" in enemy_race:
            # 테란 상대: 맹독충 올인 / 궤멸충 러시
            if random.random() < 0.5:
                self.active_strategy = AggressiveStrategyType.BANELING_BUST
            else:
                self.active_strategy = AggressiveStrategyType.RAVAGER_RUSH
                
        elif "Protoss" in enemy_race:
            # 프로토스 상대: 궤멸충 러시 / 땅굴망 / 12풀
            r = random.random()
            if r < 0.4:
                self.active_strategy = AggressiveStrategyType.RAVAGER_RUSH
            elif r < 0.7:
                 self.active_strategy = AggressiveStrategyType.NYDUS_ALLIN
            else:
                 self.active_strategy = AggressiveStrategyType.TWELVE_POOL
                 
        elif "Zerg" in enemy_race:
            # 저그 상대: 12풀 / 맹독충 올인
            if random.random() < 0.6:
                self.active_strategy = AggressiveStrategyType.TWELVE_POOL
            else:
                self.active_strategy = AggressiveStrategyType.BANELING_BUST
        else:
            # 알 수 없는 상대: 12풀
            self.active_strategy = AggressiveStrategyType.TWELVE_POOL

        self._strategy_decided = True
        self._strategy_decision_time = game_time
        print(f"[AGGRESSIVE] Selected strategy: {self.active_strategy.value} vs {enemy_race}")

        return self.active_strategy

    async def execute(self, iteration: int) -> None:
        """
        현재 전략 실행

        Args:
            iteration: 게임 반복 횟수
        """
        if not UnitTypeId or self.active_strategy == AggressiveStrategyType.NONE:
            return

        try:
            if self.active_strategy == AggressiveStrategyType.TWELVE_POOL:
                await self._execute_12pool()
            elif self.active_strategy == AggressiveStrategyType.BANELING_BUST:
                await self._execute_baneling_bust()
            elif self.active_strategy == AggressiveStrategyType.RAVAGER_RUSH:
                await self._execute_ravager_rush()
            elif self.active_strategy == AggressiveStrategyType.TUNNELING_CLAWS:
                await self._execute_tunneling_claws()
            elif self.active_strategy == AggressiveStrategyType.PROXY_HATCH:
                await self._execute_proxy_hatch()
            elif self.active_strategy == AggressiveStrategyType.NYDUS_ALLIN:
                await self._execute_nydus_allin()
            elif self.active_strategy == AggressiveStrategyType.OVERLORD_DROP:
                await self._execute_overlord_drop()

            # ★★★ 새로운 견제 시스템 (전략과 무관하게 항상 실행) ★★★
            # 멀티 견제 (3분 이후)
            if self.bot.time > 180:
                await self._execute_multi_harass()
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Aggressive strategy error: {e}")

    # ========== 12 Pool 저글링 러시 ==========
    async def _execute_12pool(self) -> None:
        """12드론 저글링 러시 실행"""
        config = self.strategy_configs[AggressiveStrategyType.TWELVE_POOL]

        # 드론 수 제한
        if hasattr(self.bot, "workers"):
            drone_count = self.bot.workers.amount
            if drone_count >= config["drone_limit"] and not self._pool_started:
                # 스포닝 풀 건설
                await self._build_spawning_pool()

        # 저글링 생산 및 공격
        if self._pool_started:
            zerglings = self.bot.units(UnitTypeId.ZERGLING)

            # [FIX] 저글링 생산 로직 추가 (pending 체크 포함)
            pending = self.bot.already_pending(UnitTypeId.ZERGLING)
            if zerglings.amount + pending < config["ling_count_attack"]:
                if self.bot.can_afford(UnitTypeId.ZERGLING) and self.bot.larva.exists:
                     # SpawningPool이 완료되어야 생산 가능
                     if self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                        self.bot.do(self.bot.larva.first.train(UnitTypeId.ZERGLING))

            if zerglings.amount >= config["ling_count_attack"] and not self._lings_sent:
                await self._send_lings_to_attack(zerglings)

    async def _build_spawning_pool(self) -> None:
        """스포닝 풀 건설"""
        if not hasattr(self.bot, "structures"):
            return

        pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL)
        if pools.exists or self.bot.already_pending(UnitTypeId.SPAWNINGPOOL):
            self._pool_started = True
            return

        # Use TechCoordinator if available
        tech_coordinator = getattr(self.bot, "tech_coordinator", None)
        PRIORITY_STRATEGY = 75

        if self.bot.can_afford(UnitTypeId.SPAWNINGPOOL):
            if tech_coordinator:
                if not tech_coordinator.is_planned(UnitTypeId.SPAWNINGPOOL):
                    target_pos = self.bot.townhalls.first.position.towards(
                        self.bot.game_info.map_center, 5
                    )
                    tech_coordinator.request_structure(
                        UnitTypeId.SPAWNINGPOOL,
                        target_pos,
                        PRIORITY_STRATEGY,
                        "AggressiveStrategies"
                    )
                    self._pool_started = True
                    print("[12POOL] Spawning Pool requested via Coordinator!")
            else:
                workers = self.bot.workers
                if workers.exists:
                    worker = workers.random
                    pos = self.bot.townhalls.first.position.towards(
                        self.bot.game_info.map_center, 5
                    )
                    self.bot.do(worker.build(UnitTypeId.SPAWNINGPOOL, pos))
                    self._pool_started = True
                    print("[12POOL] Spawning Pool started!")

    async def _send_lings_to_attack(self, zerglings) -> None:
        """저글링 공격 명령"""
        if not self.bot.enemy_start_locations:
            return

        target = self.bot.enemy_start_locations[0]
        for ling in zerglings:
            self.bot.do(ling.attack(target))
            self._rush_units.add(ling.tag)

        self._lings_sent = True
        print(f"[12POOL] Sending {zerglings.amount} Zerglings to attack!")

    # ========== 맹독충 올인 ==========
    async def _execute_baneling_bust(self) -> None:
        """맹독충 올인 실행"""
        config = self.strategy_configs[AggressiveStrategyType.BANELING_BUST]
        game_time = getattr(self.bot, "time", 0)

        # 1. 스포닝 풀 건설
        if not self._pool_started:
            await self._build_spawning_pool()
            return

        # 2. 맹독충 둥지 건설
        baneling_nest = self.bot.structures(UnitTypeId.BANELINGNEST)
        if not baneling_nest.exists and not self.bot.already_pending(UnitTypeId.BANELINGNEST):
            if self.bot.can_afford(UnitTypeId.BANELINGNEST):
                await self._build_structure(UnitTypeId.BANELINGNEST)
                return

        # 3. 저글링 생산 (★ Blackboard 요청으로 변경 ★)
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        target_zerglings = 16

        if self.blackboard:
            # Blackboard를 통한 생산 요청
            zergling_count = self.blackboard.get_unit_count(UnitTypeId.ZERGLING)
            needed = target_zerglings - zergling_count.total

            if needed > 0:
                self.blackboard.request_production(
                    unit_type=UnitTypeId.ZERGLING,
                    count=needed,
                    requester="AggressiveStrategies"
                )
        else:
            # Blackboard 없을 때 폴백 (기존 로직)
            pending_zerglings = self.bot.already_pending(UnitTypeId.ZERGLING)
            if zerglings.amount + pending_zerglings < target_zerglings and self.bot.larva.exists:
                if self.bot.can_afford(UnitTypeId.ZERGLING):
                    self.bot.do(self.bot.larva.first.train(UnitTypeId.ZERGLING))

        # 4. 맹독충 변태
        if baneling_nest.ready.exists and not self._banelings_morphing:
            banelings = self.bot.units(UnitTypeId.BANELING)
            if banelings.amount < config["baneling_count"]:
                for ling in zerglings[:8]:
                    if self.bot.can_afford(UnitTypeId.BANELING):
                        self.bot.do(ling(AbilityId.MORPHZERGLINGTOBANELING_BANELING))
                self._banelings_morphing = True

        # 5. 공격
        banelings = self.bot.units(UnitTypeId.BANELING)
        if banelings.amount >= config["baneling_count"]:
            await self._execute_baneling_attack(banelings, zerglings)

    async def _execute_baneling_attack(self, banelings, zerglings) -> None:
        """맹독충 공격 실행 - 벽 파괴 후 난입"""
        if not self.bot.enemy_start_locations:
            return

        target = self.bot.enemy_start_locations[0]

        # 적 구조물 (벽) 찾기
        enemy_structures = getattr(self.bot, "enemy_structures", [])
        wall_structures = [
            s for s in enemy_structures
            if s.type_id in [
                UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED,
                UnitTypeId.BARRACKS, UnitTypeId.PYLON
            ]
        ]

        # 벽이 있으면 벽 공격
        if wall_structures:
            closest_wall = min(wall_structures, key=lambda s: s.distance_to(target))
            for baneling in banelings:
                self.bot.do(baneling.attack(closest_wall.position))
            print(f"[BANELING BUST] Attacking wall with {banelings.amount} banelings!")
        else:
            # 벽이 없으면 본진 공격
            for baneling in banelings:
                self.bot.do(baneling.attack(target))

        # 저글링도 따라서 공격
        for ling in zerglings:
            self.bot.do(ling.attack(target))

    # ========== 궤멸충 담즙 러시 ==========
    async def _execute_ravager_rush(self) -> None:
        """궤멸충 담즙 러시 실행"""
        config = self.strategy_configs[AggressiveStrategyType.RAVAGER_RUSH]

        # 1. 바퀴굴 건설
        roach_warren = self.bot.structures(UnitTypeId.ROACHWARREN)
        if not roach_warren.exists and not self.bot.already_pending(UnitTypeId.ROACHWARREN):
            if self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                if self.bot.can_afford(UnitTypeId.ROACHWARREN):
                    await self._build_structure(UnitTypeId.ROACHWARREN)
            return

        # 2. 바퀴 생산 (★ Blackboard 요청으로 변경 ★)
        roaches = self.bot.units(UnitTypeId.ROACH)
        target_roaches = config["roach_count"]

        if roach_warren.ready.exists:
            if self.blackboard:
                # Blackboard를 통한 생산 요청
                roach_count = self.blackboard.get_unit_count(UnitTypeId.ROACH)
                needed = target_roaches - roach_count.total

                if needed > 0:
                    self.blackboard.request_production(
                        unit_type=UnitTypeId.ROACH,
                        count=needed,
                        requester="AggressiveStrategies"
                    )
            else:
                # Blackboard 없을 때 폴백
                pending_roaches = self.bot.already_pending(UnitTypeId.ROACH)
                if roaches.amount + pending_roaches < target_roaches:
                    if self.bot.can_afford(UnitTypeId.ROACH) and self.bot.larva.exists:
                        self.bot.do(self.bot.larva.first.train(UnitTypeId.ROACH))
                        return

        # 3. 궤멸충 변태
        ravagers = self.bot.units(UnitTypeId.RAVAGER)
        if roaches.amount >= config["roach_count"] and ravagers.amount < config["ravager_count"]:
            for roach in roaches[:config["ravager_count"]]:
                if self.bot.can_afford(UnitTypeId.RAVAGER):
                    self.bot.do(roach(AbilityId.MORPHTORAVAGER_RAVAGER))
            self._ravagers_ready = True

        # 4. 궤멸충 담즙 공격
        if ravagers.amount >= config["ravager_count"]:
            await self._execute_ravager_bile_attack(ravagers)

    async def _execute_ravager_bile_attack(self, ravagers) -> None:
        """궤멸충 담즙 공격 - 벙커/역장 파괴"""
        if not self.bot.enemy_start_locations:
            return

        # 우선 타겟: 벙커, 포톤캐논, 역장
        priority_targets = []
        enemy_structures = getattr(self.bot, "enemy_structures", [])

        for structure in enemy_structures:
            if structure.type_id in [
                UnitTypeId.BUNKER, UnitTypeId.PHOTONCANNON,
                UnitTypeId.SHIELDBATTERY
            ]:
                priority_targets.append(structure)

        # 역장 체크 (임시 구조물)
        # Force Fields are effects, not units - skip for now

        for ravager in ravagers:
            # 담즙 발사 가능 여부 확인
            abilities = await self.bot.get_available_abilities(ravager)
            if AbilityId.EFFECT_CORROSIVEBILE in abilities:
                if priority_targets:
                    target = min(priority_targets, key=lambda t: ravager.distance_to(t))
                    self.bot.do(ravager(AbilityId.EFFECT_CORROSIVEBILE, target.position))
                    print(f"[RAVAGER] Bile targeting {target.type_id.name}")
                else:
                    # 타겟 없으면 적 본진 공격
                    target = self.bot.enemy_start_locations[0]
                    self.bot.do(ravager.attack(target))

    # ========== 잠복 바퀴 이동 ==========
    async def _execute_tunneling_claws(self) -> None:
        """잠복 바퀴 이동 실행"""
        config = self.strategy_configs[AggressiveStrategyType.TUNNELING_CLAWS]
        game_time = getattr(self.bot, "time", 0)

        # 1. 바퀴굴 건설
        roach_warren = self.bot.structures(UnitTypeId.ROACHWARREN)
        if not roach_warren.exists:
            return

        # 2. 레어 업그레이드 (잠복 이동에 필요)
        if not self.bot.structures(UnitTypeId.LAIR).exists:
            hatcheries = self.bot.structures(UnitTypeId.HATCHERY).ready.idle
            if hatcheries.exists and self.bot.can_afford(UnitTypeId.LAIR):
                self.bot.do(hatcheries.first(AbilityId.UPGRADETOLAIR_LAIR))
            return

        # 3. 잠복 이동 업그레이드
        if not self._tunneling_upgrade_started:
            if self.bot.structures(UnitTypeId.LAIR).ready.exists:
                if roach_warren.ready.exists:
                    if self.bot.can_afford(UpgradeId.TUNNELINGCLAWS):
                        self.bot.do(roach_warren.first.research(UpgradeId.TUNNELINGCLAWS))
                        self._tunneling_upgrade_started = True
                        print("[TUNNELING] Tunneling Claws upgrade started!")

        # 4. 바퀴 생산 (★ Blackboard 요청으로 변경 ★)
        roaches = self.bot.units(UnitTypeId.ROACH)
        target_roaches = config["roach_count"]

        if self.blackboard:
            # Blackboard를 통한 생산 요청
            roach_count = self.blackboard.get_unit_count(UnitTypeId.ROACH)
            needed = target_roaches - roach_count.total

            if needed > 0:
                self.blackboard.request_production(
                    unit_type=UnitTypeId.ROACH,
                    count=needed,
                    requester="AggressiveStrategies"
                )
        else:
            # Blackboard 없을 때 폴백
            pending_roaches = self.bot.already_pending(UnitTypeId.ROACH)
            if roaches.amount + pending_roaches < target_roaches:
                if self.bot.can_afford(UnitTypeId.ROACH) and self.bot.larva.exists:
                    self.bot.do(self.bot.larva.first.train(UnitTypeId.ROACH))
                    return

        # 5. 잠복 이동 공격
        if self._tunneling_upgrade_started and roaches.amount >= config["roach_count"]:
            await self._execute_burrow_attack(roaches)

    async def _execute_burrow_attack(self, roaches) -> None:
        """잠복 이동 공격 - 적 본진 광물라인으로"""
        if not self.bot.enemy_start_locations:
            return

        target = self.bot.enemy_start_locations[0]

        for roach in roaches:
            # 잠복 명령
            if not roach.is_burrowed:
                abilities = await self.bot.get_available_abilities(roach)
                if AbilityId.BURROWDOWN_ROACH in abilities:
                    self.bot.do(roach(AbilityId.BURROWDOWN_ROACH))
            else:
                # 잠복 상태에서 이동
                self.bot.do(roach.move(target))

        print(f"[TUNNELING] {roaches.amount} Roaches burrowing to enemy base!")

    # ========== 전진 해처리 ==========
    async def _execute_proxy_hatch(self) -> None:
        """전진 해처리 실행"""
        config = self.strategy_configs[AggressiveStrategyType.PROXY_HATCH]
        game_time = getattr(self.bot, "time", 0)

        # 1. 전진 위치 결정
        if self._proxy_location is None:
            self._proxy_location = self._find_proxy_location()
            if self._proxy_location is None:
                return

        # 2. 드론 파견
        if game_time >= config["proxy_timing"] and not self._proxy_drones:
            workers = self.bot.workers
            if workers.exists:
                drone = workers.random
                self.bot.do(drone.move(self._proxy_location))
                self._proxy_drones.add(drone.tag)
                print(f"[PROXY] Drone sent to proxy location!")

        # 3. 해처리 건설
        proxy_hatch = None
        for hatch in self.bot.structures(UnitTypeId.HATCHERY):
            if hatch.position.distance_to(self._proxy_location) < 10:
                proxy_hatch = hatch
                break

        if proxy_hatch is None and not self.bot.already_pending(UnitTypeId.HATCHERY):
            for drone_tag in self._proxy_drones:
                drone = self.bot.workers.find_by_tag(drone_tag)
                if drone and drone.distance_to(self._proxy_location) < 5:
                    if self.bot.can_afford(UnitTypeId.HATCHERY):
                        self.bot.do(drone.build(UnitTypeId.HATCHERY, self._proxy_location))
                        print(f"[PROXY] Building proxy Hatchery!")

        # 4. 가시 촉수 건설
        if proxy_hatch and proxy_hatch.is_ready:
            spines = self.bot.structures(UnitTypeId.SPINECRAWLER).closer_than(15, self._proxy_location)
            if spines.amount < config["spine_count"]:
                if self.bot.can_afford(UnitTypeId.SPINECRAWLER):
                    await self._build_spine_at_proxy(proxy_hatch.position)

    def _find_proxy_location(self) -> Optional[Point2]:
        """전진 해처리 위치 찾기"""
        if not self.bot.enemy_start_locations or not Point2:
            return None

        enemy_base = self.bot.enemy_start_locations[0]
        our_base = self.bot.townhalls.first.position if self.bot.townhalls.exists else None

        if our_base is None:
            return None

        # 적 앞마당 근처 (적 기지에서 30 거리)
        proxy_pos = enemy_base.towards(our_base, 30)

        return proxy_pos

    async def _build_spine_at_proxy(self, position: Point2) -> None:
        """전진 기지에 가시 촉수 건설"""
        workers = self.bot.workers
        if workers.exists:
            nearby_workers = workers.closer_than(20, position)
            if nearby_workers.exists:
                worker = nearby_workers.first
                build_pos = position.towards(self.bot.enemy_start_locations[0], 3)
                self.bot.do(worker.build(UnitTypeId.SPINECRAWLER, build_pos))

    # ========== 땅굴망 올인 ==========
    async def _execute_nydus_allin(self) -> None:
        """땅굴망 올인 실행"""
        config = self.strategy_configs[AggressiveStrategyType.NYDUS_ALLIN]
        game_time = getattr(self.bot, "time", 0)

        # 1. 레어 건설
        if not self.bot.structures(UnitTypeId.LAIR).exists:
            if game_time >= config["lair_timing"]:
                hatcheries = self.bot.structures(UnitTypeId.HATCHERY).ready.idle
                if hatcheries.exists and self.bot.can_afford(UnitTypeId.LAIR):
                    self.bot.do(hatcheries.first(AbilityId.UPGRADETOLAIR_LAIR))
            return

        # 2. 땅굴망 건설
        nydus_network = self.bot.structures(UnitTypeId.NYDUSNETWORK)
        if not nydus_network.exists and not self.bot.already_pending(UnitTypeId.NYDUSNETWORK):
            if game_time >= config["nydus_timing"]:
                if self.bot.structures(UnitTypeId.LAIR).ready.exists:
                    if self.bot.can_afford(UnitTypeId.NYDUSNETWORK):
                        await self._build_structure(UnitTypeId.NYDUSNETWORK)
            return

        # 3. 여왕 생산 (★ Blackboard 요청으로 변경 ★)
        queens = self.bot.units(UnitTypeId.QUEEN)
        target_queens = config["queen_count"]

        if self.blackboard:
            # Blackboard를 통한 생산 요청
            queen_count = self.blackboard.get_unit_count(UnitTypeId.QUEEN)
            needed = target_queens - queen_count.total

            if needed > 0:
                self.blackboard.request_production(
                    unit_type=UnitTypeId.QUEEN,
                    count=needed,
                    requester="AggressiveStrategies"
                )
        else:
            # Blackboard 없을 때 폴백
            pending_queens = self.bot.already_pending(UnitTypeId.QUEEN)
            if queens.amount + pending_queens < target_queens:
                for hatch in self.bot.townhalls.ready.idle:
                    if self.bot.can_afford(UnitTypeId.QUEEN):
                        self.bot.do(hatch.train(UnitTypeId.QUEEN))

        # 4. 땅굴 벌레 생성
        if nydus_network.ready.exists and not self._nydus_built:
            nydus_location = self._find_nydus_location()
            if nydus_location:
                network = nydus_network.first
                if self.bot.can_afford(UnitTypeId.NYDUSCANAL):
                    self.bot.do(network(AbilityId.BUILD_NYDUSWORM, nydus_location))
                    self._nydus_location = nydus_location
                    self._nydus_built = True
                    print(f"[NYDUS] Building Nydus Worm at enemy base!")

        # 5. 땅굴 벌레 확인 및 추적
        nydus_worms = self.bot.structures(UnitTypeId.NYDUSCANAL)
        if nydus_worms.exists and self._nydus_built:
            worm = nydus_worms.closest_to(self._nydus_location) if self._nydus_location else nydus_worms.first
            if worm and worm.is_ready:
                self._nydus_worm_tag = worm.tag

                # 6. 유닛 지속 투입
                await self._load_units_into_nydus(nydus_network.first)

                # 7. ★★★ Worm에서 나온 유닛들 공격 명령 ★★★
                await self._command_nydus_attackers(worm)

        # 8. Worm이 파괴되면 재건설 (선택적)
        if self._nydus_built and not nydus_worms.exists:
            print(f"[NYDUS] Worm destroyed! Rebuilding...")
            self._nydus_built = False
            self._nydus_worm_tag = None
            self._nydus_attack_started = False

    def _find_nydus_location(self) -> Optional[Point2]:
        """땅굴 위치 찾기 - 적 시야 밖"""
        if not self.bot.enemy_start_locations or not Point2:
            return None

        enemy_base = self.bot.enemy_start_locations[0]

        # 적 본진 뒤쪽 구석
        map_center = self.bot.game_info.map_center
        behind_enemy = enemy_base.towards(map_center, -15)

        return behind_enemy

    async def _load_units_into_nydus(self, nydus_network) -> None:
        """땅굴에 유닛 투입"""
        # 여왕과 바퀴/히드라 투입
        units_to_load = []

        queens = self.bot.units(UnitTypeId.QUEEN)
        roaches = self.bot.units(UnitTypeId.ROACH)
        hydras = self.bot.units(UnitTypeId.HYDRALISK)

        units_to_load.extend(queens)
        units_to_load.extend(roaches)
        units_to_load.extend(hydras)

        for unit in units_to_load[:20]:  # 최대 20유닛
            # 이미 투입된 유닛은 스킵
            if unit.tag in self._nydus_units_sent:
                continue

            if unit.distance_to(nydus_network) < 5:
                self.bot.do(unit(AbilityId.LOAD_NYDUSNETWORK, nydus_network))
                self._nydus_units_sent.add(unit.tag)
            else:
                self.bot.do(unit.move(nydus_network.position))

    async def _command_nydus_attackers(self, nydus_worm) -> None:
        """
        ★★★ 땅굴에서 나온 유닛들에게 공격 명령 ★★★

        Worm 근처의 아군 유닛을 찾아서 적 기지를 공격하게 합니다.
        """
        if not self._nydus_location:
            return

        # Worm 근처의 아군 유닛 찾기 (반경 15)
        our_units = self.bot.units.filter(
            lambda u: u.distance_to(nydus_worm) < 15 and
            u.type_id in {UnitTypeId.QUEEN, UnitTypeId.ROACH, UnitTypeId.HYDRALISK,
                          UnitTypeId.ZERGLING, UnitTypeId.RAVAGER}
        )

        if not our_units:
            return

        # 공격 타겟 찾기
        enemy_structures = self.bot.enemy_structures
        enemy_workers = self.bot.enemy_units.filter(
            lambda u: u.type_id in {UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE}
        )
        enemy_army = self.bot.enemy_units.filter(
            lambda u: u.type_id not in {UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE}
        )

        # 우선순위: 1. 일꾼 2. 건물 3. 군대
        if enemy_workers.exists:
            target = enemy_workers.closest_to(nydus_worm)
        elif enemy_structures.exists:
            target = enemy_structures.closest_to(nydus_worm)
        elif enemy_army.exists:
            target = enemy_army.closest_to(nydus_worm)
        else:
            # 적이 없으면 적 본진으로
            if self.bot.enemy_start_locations:
                target_pos = self.bot.enemy_start_locations[0]
                for unit in our_units:
                    self.bot.do(unit.attack(target_pos))

                if not self._nydus_attack_started:
                    print(f"[NYDUS] {our_units.amount} units attacking enemy base!")
                    self._nydus_attack_started = True
            return

        # 공격 명령
        for unit in our_units:
            self.bot.do(unit.attack(target.position))

        if not self._nydus_attack_started:
            print(f"[NYDUS] {our_units.amount} units emerging from Worm and attacking!")
            self._nydus_attack_started = True

    # ========== 공통 유틸리티 ==========
    async def _build_structure(self, structure_type) -> None:
        """구조물 건설 유틸리티 (점막 체크 포함)"""
        if not self.bot.townhalls.exists:
            return
            
        # Use TechCoordinator if available
        tech_coordinator = getattr(self.bot, "tech_coordinator", None)
        PRIORITY_STRATEGY = 75

        pos = self.bot.townhalls.first.position.towards(
            self.bot.game_info.map_center, 5
        )
        
        if tech_coordinator:
             if not tech_coordinator.is_planned(structure_type):
                tech_coordinator.request_structure(
                    structure_type,
                    pos,
                    PRIORITY_STRATEGY,
                    "AggressiveStrategies"
                )
                return

        workers = self.bot.workers
        if not workers.exists:
            return

        # 점막 체크 헬퍼 사용
        if self.placement_helper:
            success = await self.placement_helper.build_structure_safely(
                structure_type,
                pos,
                max_distance=15.0
            )
            if success:
                return

        # 폴백: 기존 방식 (점막 체크 없음)
        worker = workers.closest_to(pos)
        self.bot.do(worker.build(structure_type, pos))

    def get_drone_limit(self) -> int:
        """현재 전략의 드론 제한 반환"""
        if self.active_strategy == AggressiveStrategyType.NONE:
            return 80  # 제한 없음

        config = self.strategy_configs.get(self.active_strategy, {})
        return config.get("drone_limit", 80)

    def is_active(self) -> bool:
        """공격 전략이 활성화되어 있는지"""
        return self.active_strategy != AggressiveStrategyType.NONE

    def get_status(self) -> dict:
        """현재 상태 반환"""
        return {
            "strategy": self.active_strategy.value,
            "decided": self._strategy_decided,
            "pool_started": self._pool_started,
            "lings_sent": self._lings_sent,
            "ravagers_ready": self._ravagers_ready,
            "proxy_location": str(self._proxy_location) if self._proxy_location else None,
            "nydus_built": self._nydus_built,
            "overlord_drop_active": self._overlord_drop_active,
        }

    # ========== ★★★ 대군주 드랍 견제 (NEW) ★★★ ==========
    async def _execute_overlord_drop(self) -> None:
        """
        ★ 대군주 드랍 견제 실행 ★

        타이밍:
        - 3분: Ventral Sacs 업그레이드 시작
        - 4분: 저글링 8마리 + 대군주 2기로 드랍 시작

        목표:
        - 상대 멀티 일꾼 라인 공격
        - 테크 건물 파괴
        """
        config = self.strategy_configs[AggressiveStrategyType.OVERLORD_DROP]
        game_time = getattr(self.bot, "time", 0)

        # 1. Ventral Sacs 업그레이드 (배주머니)
        if game_time >= config["ventral_sacs_timing"] and not hasattr(self, "_ventral_sacs_started"):
            # Lair가 있어야 함
            if self.bot.structures(UnitTypeId.LAIR).ready.exists or self.bot.structures(UnitTypeId.HIVE).ready.exists:
                if self.bot.can_afford(UpgradeId.OVERLORDSPEED):  # Ventral Sacs는 UpgradeId가 다름
                    # 업그레이드 시작 (정확한 ability ID 필요)
                    try:
                        lairs = self.bot.structures(UnitTypeId.LAIR).ready
                        if lairs:
                            # OVERLORDSPEED는 pneumatized sacs (이동속도)
                            # Ventral sacs는 OVERLORDTRANSPORT
                            self.bot.do(lairs.first.research(UpgradeId.OVERLORDTRANSPORT))
                            self._ventral_sacs_started = True
                            print(f"[OVERLORD DROP] Ventral Sacs upgrade started!")
                    except Exception as e:
                        pass

        # 2. 드랍용 대군주 지정
        if game_time >= config["drop_timing"] and not self._overlord_drop_active:
            overlords = self.bot.units(UnitTypeId.OVERLORD)
            if overlords.amount >= config["drop_overlord_count"]:
                # 2기 선택
                for i, ol in enumerate(overlords[:config["drop_overlord_count"]]):
                    self._drop_overlords.add(ol.tag)

                self._overlord_drop_active = True
                print(f"[OVERLORD DROP] {len(self._drop_overlords)} Overlords designated for drop!")

        # 3. 저글링 탑승 및 드랍 실행
        if self._overlord_drop_active:
            await self._execute_drop_attack()

    async def _execute_drop_attack(self) -> None:
        """드랍 공격 실행"""
        if not self.bot.enemy_start_locations:
            return

        # 드랍용 대군주 확인
        drop_overlords = self.bot.units(UnitTypeId.OVERLORD).tags_in(self._drop_overlords)
        if not drop_overlords:
            return

        # 저글링 확인
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        
        # 목표: 적 멀티 (자연 확장)
        enemy_base = self.bot.enemy_start_locations[0]
        # 적 본진 안쪽으로 조금 더 들어가서 드랍
        drop_target = enemy_base.towards(self.bot.game_info.map_center, -5)

        for overlord in drop_overlords:
            # 탑승한 유닛 수 확인
            cargo = getattr(overlord, "cargo_used", 0) # cargo_left가 아니라 cargo_used
            max_cargo = 8  # 대군주 최대 탑승 8

            # 1. 아직 탑승 안했으면 저글링 탑승
            if cargo < max_cargo:
                # 대군주 근처의 저글링 찾기
                nearby_lings = zerglings.closer_than(10, overlord)
                if nearby_lings.exists:
                    # 빈 공간만큼 태우기
                    slots_free = max_cargo - cargo
                    for ling in nearby_lings[:slots_free]:
                        try:
                            # LOAD 명령: 대군주가 유닛을 태우도록 명령 (AbilityId.LOAD)
                            # 또는 유닛이 대군주에 타도록 (AbilityId.SMART)
                            # 여기서는 대군주가 태우는 방식 사용
                            self.bot.do(overlord(AbilityId.LOAD, ling))
                        except Exception:
                            pass
                else:
                    # 근처에 저글링이 없으면 저글링들에게 대군주로 모이라고 명령
                    available_lings = zerglings.idle
                    if available_lings.exists:
                        # 3마리씩 호출
                        for ling in available_lings[:3]:
                             self.bot.do(ling.move(overlord.position))
            
            # 2. 꽉 찼거나 적당히 찼으면 드랍 위치로 이동
            elif cargo > 0:
                if overlord.distance_to(drop_target) > 4:
                    # 이동 (무브 커맨드)
                    # 적 대공 방어 피하기 위해 could add pathing here, but simple move for now
                    self.bot.do(overlord(AbilityId.MOVE, drop_target))
                else:
                    # 3. 도착 시 하역 (UNLOAD)
                    try:
                        # 특정 위치에 모두 하역
                        self.bot.do(overlord(AbilityId.UNLOADALLAT, drop_target))
                        print(f"[DROP] Unloading units at {drop_target}")
                    except Exception as e:
                        print(f"[DROP] Unload failed: {e}")
            
        # 드랍된 유닛 제어는 별도 로직이나 기본 공격 로직이 처리할 것임

    # ========== ★★★ 멀티 견제 시스템 (NEW) ★★★ ==========
    async def _execute_multi_harass(self) -> None:
        """
        ★ 멀티 견제 시스템 ★

        전략:
        1. 상대 확장 위치 감지
        2. 저글링 4-6마리를 상대 멀티로 보내서 일꾼 견제
        3. 지속적으로 순환 견제 (멀티1 → 멀티2 → 멀티1)

        타이밍:
        - 3분 이후부터 지속
        - 30초마다 새로운 견제 유닛 파견
        """
        game_time = getattr(self.bot, "time", 0)

        # 쿨다운 체크 (30초마다)
        if not hasattr(self, "_last_multi_harass"):
            self._last_multi_harass = 0

        if game_time - self._last_multi_harass < 30:
            return  # 아직 쿨다운

        self._last_multi_harass = game_time

        # 저글링 4-6마리 선택 (idle 또는 방어 중인 유닛)
        zerglings = self.bot.units(UnitTypeId.ZERGLING).idle
        if not zerglings or zerglings.amount < 4:
            # idle이 없으면 전체에서 선택
            zerglings = self.bot.units(UnitTypeId.ZERGLING)
            if not zerglings or zerglings.amount < 4:
                return

        # 견제 유닛 선택 (4-6마리)
        harass_lings = zerglings.take(min(6, zerglings.amount))

        # 목표: 적 확장 위치 (자연 확장 우선)
        enemy_expansions = []

        # 적 건물이 있는 확장 찾기
        if hasattr(self.bot, "enemy_structures"):
            for structure in self.bot.enemy_structures:
                if structure.is_structure:
                    # 타운홀 확인
                    if structure.type_id in [UnitTypeId.COMMANDCENTER, UnitTypeId.NEXUS, UnitTypeId.HATCHERY]:
                        enemy_expansions.append(structure.position)

        # 적 확장이 없으면 예상 위치로
        if not enemy_expansions and hasattr(self.bot, "enemy_start_locations"):
            enemy_base = self.bot.enemy_start_locations[0]
            map_center = self.bot.game_info.map_center
            # 자연 확장 예상 위치
            natural_pos = enemy_base.towards(map_center, 8)
            enemy_expansions.append(natural_pos)

        if not enemy_expansions:
            return

        # 견제 목표: 가장 가까운 적 확장
        target = min(enemy_expansions, key=lambda pos: harass_lings.center.distance_to(pos))

        # 견제 명령
        for ling in harass_lings:
            self.bot.do(ling.attack(target))
            self._rush_units.add(ling.tag)

        print(f"[MULTI HARASS] [{int(game_time)}s] Sending {harass_lings.amount} Zerglings to harass enemy expansion!")
