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


class AggressiveStrategyType(Enum):
    """공격 전략 타입"""
    NONE = "none"
    TWELVE_POOL = "12pool"           # 12드론 저글링 러시
    BANELING_BUST = "baneling_bust"  # 맹독충 올인
    RAVAGER_RUSH = "ravager_rush"    # 궤멸충 담즙 러시
    TUNNELING_CLAWS = "tunneling"    # 잠복 바퀴
    PROXY_HATCH = "proxy_hatch"      # 전진 해처리
    NYDUS_ALLIN = "nydus_allin"      # 땅굴망 올인


class AggressiveStrategyExecutor:
    """
    공격 전략 실행기

    초반 러시/올인 전략을 상황에 맞게 선택하고 실행합니다.
    """

    def __init__(self, bot):
        self.bot = bot

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

        # 유닛 태그 추적
        self._rush_units: Set[int] = set()
        self._proxy_drones: Set[int] = set()

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
                "attack_timing": 240,  # 4분
            },
            AggressiveStrategyType.TUNNELING_CLAWS: {
                "roach_count": 8,
                "upgrade_timing": 180,  # 3분에 업그레이드 시작
            },
            AggressiveStrategyType.PROXY_HATCH: {
                "proxy_timing": 60,  # 1분에 드론 파견
                "spine_count": 2,
            },
            AggressiveStrategyType.NYDUS_ALLIN: {
                "lair_timing": 240,  # 4분에 레어
                "nydus_timing": 300,  # 5분에 땅굴
                "queen_count": 4,
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

        # 종족별 전략 선택
        if "Terran" in enemy_race:
            # 테란 상대: 맹독충 올인 (서플라이 벽 파괴)
            self.active_strategy = AggressiveStrategyType.BANELING_BUST
        elif "Protoss" in enemy_race:
            # 프로토스 상대: 궤멸충 러시 (역장 파괴)
            self.active_strategy = AggressiveStrategyType.RAVAGER_RUSH
        elif "Zerg" in enemy_race:
            # 저그 상대: 12풀 저글링 러시
            self.active_strategy = AggressiveStrategyType.TWELVE_POOL
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

        if self.bot.can_afford(UnitTypeId.SPAWNINGPOOL):
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

        # 3. 저글링 생산
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if zerglings.amount < 16 and self.bot.larva.exists:
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

        # 2. 바퀴 생산
        roaches = self.bot.units(UnitTypeId.ROACH)
        if roach_warren.ready.exists and roaches.amount < config["roach_count"]:
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

        # 4. 바퀴 생산
        roaches = self.bot.units(UnitTypeId.ROACH)
        if roaches.amount < config["roach_count"]:
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

        # 3. 여왕 생산
        queens = self.bot.units(UnitTypeId.QUEEN)
        if queens.amount < config["queen_count"]:
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

        # 5. 유닛 투입
        if self._nydus_built:
            await self._load_units_into_nydus(nydus_network.first)

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
            if unit.distance_to(nydus_network) < 5:
                self.bot.do(unit(AbilityId.LOAD_NYDUSNETWORK, nydus_network))
            else:
                self.bot.do(unit.move(nydus_network.position))

    # ========== 공통 유틸리티 ==========
    async def _build_structure(self, structure_type) -> None:
        """구조물 건설 유틸리티"""
        if not self.bot.townhalls.exists:
            return

        workers = self.bot.workers
        if not workers.exists:
            return

        pos = self.bot.townhalls.first.position.towards(
            self.bot.game_info.map_center, 5
        )
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
        }
