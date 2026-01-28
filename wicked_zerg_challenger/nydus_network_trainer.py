# -*- coding: utf-8 -*-
"""
Nydus Network Trainer - 땅굴망 사용법 학습 시스템

땅굴망을 효율적으로 사용하는 방법을 학습하고 실행:
1. 최적 Worm 위치 학습
2. 투입 타이밍 최적화
3. 멀티 드랍 전략
4. 상황별 활용법
"""

from typing import List, Dict, Optional, Set, Tuple
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from utils.logger import get_logger
import random


class NydusWormSpot:
    """땅굴벌레 위치 정보"""

    def __init__(self, position: Point2, purpose: str):
        self.position = position
        self.purpose = purpose  # "main_attack", "multi_harass", "escape_route"
        self.success_count = 0
        self.failure_count = 0
        self.last_used_time = 0
        self.is_active = False
        self.worm_tag: Optional[int] = None


class NydusNetworkTrainer:
    """
    땅굴망 사용법 학습 시스템

    땅굴망을 전략적으로 사용하는 방법을 학습합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("NydusTrainer")

        # 땅굴벌레 위치 추적
        self.worm_spots: List[NydusWormSpot] = []
        self.active_worms: Dict[int, NydusWormSpot] = {}

        # 투입 병력 추적
        self.units_in_transit: Set[int] = set()
        self.units_deployed: Set[int] = set()

        # 학습 데이터
        self.strategies_tried: List[Dict] = []
        self.successful_attacks = 0
        self.failed_attacks = 0

        # 설정
        self.MIN_ARMY_FOR_ATTACK = 8  # 최소 공격 병력
        self.MAX_UNITS_PER_WORM = 15  # Worm당 최대 투입 유닛
        self.WORM_BUILD_COOLDOWN = 60  # Worm 재건설 쿨다운 (초)

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # Nydus Network가 있는지 확인
            networks = self.bot.structures(UnitTypeId.NYDUSNETWORK).ready
            if not networks:
                return

            network = networks.first

            # 주기적 체크 (5초마다)
            if iteration % 110 == 0:
                await self._manage_nydus_operations(network, game_time)

            # 활성 Worm 관리 (매 프레임)
            if self.active_worms:
                await self._manage_active_worms()

            # 디버그 출력
            if iteration % 440 == 0 and self.active_worms:  # 20초마다
                self._print_status(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[NYDUS_TRAINER] Error: {e}")

    async def _manage_nydus_operations(self, network, game_time: float):
        """땅굴망 운영 관리"""
        # 1. 새 Worm 건설 필요 여부
        if not self.active_worms:
            await self._plan_new_worm(network, game_time)

        # 2. 병력 투입
        await self._load_units_into_network(network)

        # 3. 배치된 유닛 관리
        await self._command_deployed_units()

    async def _plan_new_worm(self, network, game_time: float):
        """새 Worm 계획"""
        # 쿨다운 체크
        if hasattr(self, '_last_worm_time'):
            if game_time - self._last_worm_time < self.WORM_BUILD_COOLDOWN:
                return

        # 충분한 병력이 있는지 확인
        our_army = self.bot.units.filter(
            lambda u: u.type_id in {
                UnitTypeId.ROACH, UnitTypeId.HYDRALISK, UnitTypeId.QUEEN,
                UnitTypeId.RAVAGER, UnitTypeId.ZERGLING
            }
        )

        if our_army.amount < self.MIN_ARMY_FOR_ATTACK:
            return

        # Worm 위치 결정
        best_spot = await self._find_best_worm_location(game_time)
        if not best_spot:
            return

        # Worm 건설
        if self.bot.can_afford(UnitTypeId.NYDUSCANAL):
            self.bot.do(network(AbilityId.BUILD_NYDUSWORM, best_spot.position))
            self._last_worm_time = game_time

            self.logger.info(
                f"[{int(game_time)}s] NYDUS WORM building at {best_spot.position} "
                f"(Purpose: {best_spot.purpose})"
            )

            # 위치 기록
            self.worm_spots.append(best_spot)

    async def _find_best_worm_location(self, game_time: float) -> Optional[NydusWormSpot]:
        """최적 Worm 위치 찾기"""
        # 상황별 전략 결정
        strategy = self._decide_strategy(game_time)

        if strategy == "main_attack":
            return await self._find_main_attack_spot()
        elif strategy == "multi_harass":
            return await self._find_multi_harass_spot()
        elif strategy == "backdoor":
            return await self._find_backdoor_spot()
        else:
            return None

    def _decide_strategy(self, game_time: float) -> str:
        """전략 결정"""
        # 게임 단계별 전략
        if game_time < 300:
            # 5분 이전: 주공격
            return "main_attack"
        elif game_time < 600:
            # 10분 이전: 멀티 견제
            return "multi_harass"
        else:
            # 10분 이후: 백도어
            return "backdoor"

    async def _find_main_attack_spot(self) -> Optional[NydusWormSpot]:
        """주공격 위치 (적 본진 후방)"""
        if not self.bot.enemy_start_locations:
            return None

        enemy_base = self.bot.enemy_start_locations[0]
        map_center = self.bot.game_info.map_center

        # 적 본진에서 맵 중앙 반대편으로 15거리
        behind_enemy = enemy_base.towards(map_center, -15)

        return NydusWormSpot(behind_enemy, "main_attack")

    async def _find_multi_harass_spot(self) -> Optional[NydusWormSpot]:
        """멀티 견제 위치 (적 확장 기지)"""
        # 적 확장 기지 찾기
        enemy_expansions = self.bot.enemy_structures.filter(
            lambda s: s.type_id in {
                UnitTypeId.HATCHERY, UnitTypeId.NEXUS, UnitTypeId.COMMANDCENTER,
                UnitTypeId.LAIR, UnitTypeId.HIVE, UnitTypeId.ORBITALCOMMAND,
                UnitTypeId.PLANETARYFORTRESS
            }
        )

        if not enemy_expansions:
            # 적 확장이 없으면 예상 위치
            expansion_locations = list(self.bot.expansion_locations_list)
            if len(expansion_locations) > 2:
                # 적이 갈 만한 2번째 멀티
                target = expansion_locations[2]
                return NydusWormSpot(target, "multi_harass")
            return None

        # 본진이 아닌 확장 기지
        enemy_main = self.bot.enemy_start_locations[0] if self.bot.enemy_start_locations else None
        for expansion in enemy_expansions:
            if enemy_main and expansion.distance_to(enemy_main) > 20:
                # 확장 기지 근처
                spot = expansion.position.towards(self.bot.start_location, 8)
                return NydusWormSpot(spot, "multi_harass")

        return None

    async def _find_backdoor_spot(self) -> Optional[NydusWormSpot]:
        """백도어 위치 (측면 공격)"""
        if not self.bot.enemy_start_locations:
            return None

        enemy_base = self.bot.enemy_start_locations[0]
        our_base = self.bot.start_location

        # 적 본진과 우리 본진 사이의 수직 방향
        direction = (enemy_base - our_base).normalized
        perpendicular = Point2((-direction.y, direction.x))  # 90도 회전

        # 측면 위치
        side_spot = enemy_base + perpendicular * 20

        # 맵 경계 확인
        if not self._is_valid_position(side_spot):
            side_spot = enemy_base - perpendicular * 20

        return NydusWormSpot(side_spot, "backdoor")

    def _is_valid_position(self, pos: Point2) -> bool:
        """유효한 위치인지 확인"""
        playable_area = self.bot.game_info.playable_area
        return (playable_area.x <= pos.x <= playable_area.x + playable_area.width and
                playable_area.y <= pos.y <= playable_area.y + playable_area.height)

    async def _load_units_into_network(self, network):
        """유닛을 Network에 탑승"""
        # 투입할 유닛 선택
        loadable_units = self.bot.units.filter(
            lambda u: u.type_id in {
                UnitTypeId.ROACH, UnitTypeId.HYDRALISK, UnitTypeId.QUEEN,
                UnitTypeId.RAVAGER, UnitTypeId.ZERGLING
            } and u.tag not in self.units_in_transit
        )

        if not loadable_units:
            return

        # 우선순위: Queen > Ravager > Roach > Hydra > Zergling
        priority_units = []
        priority_units.extend(loadable_units(UnitTypeId.QUEEN).take(3))
        priority_units.extend(loadable_units(UnitTypeId.RAVAGER).take(4))
        priority_units.extend(loadable_units(UnitTypeId.ROACH).take(8))
        priority_units.extend(loadable_units(UnitTypeId.HYDRALISK).take(5))
        priority_units.extend(loadable_units(UnitTypeId.ZERGLING).take(10))

        # 최대 15유닛만
        units_to_load = priority_units[:self.MAX_UNITS_PER_WORM]

        loaded_count = 0
        for unit in units_to_load:
            if unit.distance_to(network) < 5:
                # 탑승
                self.bot.do(unit(AbilityId.LOAD_NYDUSNETWORK, network))
                self.units_in_transit.add(unit.tag)
                loaded_count += 1
            else:
                # 이동
                self.bot.do(unit.move(network.position))

        if loaded_count > 0:
            self.logger.info(f"[NYDUS] Loading {loaded_count} units into Network")

    async def _manage_active_worms(self):
        """활성 Worm 관리"""
        # Worm 확인
        worms = self.bot.structures(UnitTypeId.NYDUSCANAL)

        for worm in worms:
            if worm.tag not in self.active_worms:
                # 새 Worm 발견
                spot = self._find_matching_spot(worm.position)
                if spot:
                    spot.worm_tag = worm.tag
                    spot.is_active = True
                    self.active_worms[worm.tag] = spot

                    self.logger.info(
                        f"[NYDUS] Worm activated at {worm.position} ({spot.purpose})"
                    )

            # Worm 근처 유닛 공격 명령
            if worm.is_ready:
                await self._command_worm_units(worm)

        # 파괴된 Worm 제거
        destroyed_worms = []
        for worm_tag in self.active_worms.keys():
            exists = any(w.tag == worm_tag for w in worms)
            if not exists:
                destroyed_worms.append(worm_tag)

        for tag in destroyed_worms:
            spot = self.active_worms[tag]
            spot.is_active = False
            del self.active_worms[tag]
            self.logger.info(f"[NYDUS] Worm at {spot.position} destroyed")

    def _find_matching_spot(self, position: Point2) -> Optional[NydusWormSpot]:
        """위치와 일치하는 spot 찾기"""
        for spot in self.worm_spots:
            if spot.position.distance_to(position) < 5:
                return spot
        return None

    async def _command_worm_units(self, worm):
        """Worm 근처 유닛 명령"""
        # Worm 근처 아군 찾기 (반경 15)
        nearby_units = self.bot.units.filter(
            lambda u: u.distance_to(worm) < 15 and
            u.type_id in {
                UnitTypeId.ROACH, UnitTypeId.HYDRALISK, UnitTypeId.QUEEN,
                UnitTypeId.RAVAGER, UnitTypeId.ZERGLING
            }
        )

        if not nearby_units:
            return

        # 공격 타겟 찾기
        target = await self._find_best_target(worm.position)
        if not target:
            return

        # 공격 명령
        for unit in nearby_units:
            if unit.tag not in self.units_deployed:
                self.bot.do(unit.attack(target))
                self.units_deployed.add(unit.tag)

        # 처음 공격 시 로그
        spot = self.active_worms.get(worm.tag)
        if spot and nearby_units.amount > 0:
            self.logger.info(
                f"[NYDUS] {nearby_units.amount} units attacking from Worm "
                f"(Purpose: {spot.purpose})"
            )

    async def _find_best_target(self, worm_position: Point2):
        """최적 공격 타겟"""
        # 우선순위: 일꾼 > 건물 > 군대
        enemy_workers = self.bot.enemy_units.filter(
            lambda u: u.type_id in {UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE}
        )

        if enemy_workers:
            return enemy_workers.closest_to(worm_position).position

        enemy_structures = self.bot.enemy_structures
        if enemy_structures:
            return enemy_structures.closest_to(worm_position).position

        enemy_units = self.bot.enemy_units
        if enemy_units:
            return enemy_units.closest_to(worm_position).position

        # 타겟 없으면 적 본진
        if self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]

        return None

    def _print_status(self, game_time: float):
        """상태 출력"""
        if self.active_worms:
            self.logger.info(
                f"[NYDUS_STATUS] [{int(game_time)}s] "
                f"Active Worms: {len(self.active_worms)}, "
                f"Units in Transit: {len(self.units_in_transit)}, "
                f"Units Deployed: {len(self.units_deployed)}"
            )

            for spot in self.active_worms.values():
                self.logger.info(
                    f"  @ {spot.position}: {spot.purpose}"
                )

    def get_statistics(self) -> Dict:
        """통계 반환"""
        total_attempts = self.successful_attacks + self.failed_attacks
        success_rate = (self.successful_attacks / total_attempts * 100) if total_attempts > 0 else 0

        return {
            "total_worms_built": len(self.worm_spots),
            "active_worms": len(self.active_worms),
            "successful_attacks": self.successful_attacks,
            "failed_attacks": self.failed_attacks,
            "success_rate": f"{success_rate:.1f}%",
            "units_deployed": len(self.units_deployed)
        }
