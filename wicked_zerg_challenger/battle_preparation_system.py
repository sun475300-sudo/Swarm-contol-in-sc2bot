# -*- coding: utf-8 -*-
"""
Battle Preparation System - 교전 대비 시스템

교전을 능동적으로 감지하고 준비:
1. 교전 조기 감지 (적 이동 패턴)
2. 병력 자동 집결
3. 유리한 포지션 선점
4. 교전 전 버프/힐 준비
5. 교전 중 실시간 지원
6. 교전 후 처리 (추격/철수)
"""

from typing import List, Dict, Optional, Set, Tuple
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from utils.logger import get_logger
import time


class BattleZone:
    """교전 지역 정보"""

    def __init__(self, center: Point2, enemy_count: int, our_count: int):
        self.center = center
        self.enemy_count = enemy_count
        self.our_count = our_count
        self.detected_time = time.time()
        self.is_active = True
        self.reinforcements_requested = False


class BattlePreparationSystem:
    """
    교전 대비 시스템

    교전을 미리 감지하고 능동적으로 대비합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("BattlePrep")

        # 교전 지역 추적
        self.battle_zones: Dict[str, BattleZone] = {}
        self.last_check_time = 0
        self.check_interval = 2.0  # 2초마다 체크

        # 설정
        self.ENGAGEMENT_DETECTION_RADIUS = 15  # 교전 감지 반경
        self.REINFORCEMENT_RADIUS = 20  # 지원 병력 소집 반경
        self.RALLY_DISTANCE = 8  # 집결 거리
        self.MIN_ENEMY_FOR_BATTLE = 3  # 교전으로 간주할 최소 적 수

        # 통계
        self.battles_detected = 0
        self.battles_won = 0
        self.battles_lost = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 주기적 체크 (2초마다)
            if game_time - self.last_check_time >= self.check_interval:
                await self._detect_battles(game_time)
                await self._prepare_for_battles(game_time)
                self.last_check_time = game_time

            # 활성 교전 처리 (매 프레임)
            if self.battle_zones:
                await self._manage_active_battles()

            # 디버그 출력
            if iteration % 440 == 0 and self.battle_zones:  # 20초마다
                self._print_battle_status(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[BATTLE_PREP] Error: {e}")

    async def _detect_battles(self, game_time: float):
        """교전 감지"""
        enemy_army = self.bot.enemy_units.filter(
            lambda u: not u.is_structure and u.type_id not in {
                UnitTypeId.LARVA, UnitTypeId.EGG, UnitTypeId.OVERLORD,
                UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE
            }
        )

        if not enemy_army:
            return

        # 적 병력 클러스터 찾기
        clusters = self._find_enemy_clusters(enemy_army)

        for cluster_center, enemy_units in clusters:
            # 근처 아군 확인
            our_units = self.bot.units.filter(
                lambda u: u.distance_to(cluster_center) < self.ENGAGEMENT_DETECTION_RADIUS and
                u.type_id not in {UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.LARVA, UnitTypeId.EGG}
            )

            enemy_count = len(enemy_units)
            our_count = len(our_units)

            # 교전 발생 조건
            if enemy_count >= self.MIN_ENEMY_FOR_BATTLE:
                zone_key = f"{int(cluster_center.x)}_{int(cluster_center.y)}"

                if zone_key not in self.battle_zones:
                    # 새 교전 발견!
                    self.battle_zones[zone_key] = BattleZone(
                        cluster_center, enemy_count, our_count
                    )
                    self.battles_detected += 1

                    power_ratio = our_count / max(enemy_count, 1)
                    self.logger.warning(
                        f"[{int(game_time)}s] BATTLE DETECTED at {cluster_center}! "
                        f"Enemy: {enemy_count}, Our: {our_count} (Ratio: {power_ratio:.2f})"
                    )
                else:
                    # 기존 교전 업데이트
                    zone = self.battle_zones[zone_key]
                    zone.enemy_count = enemy_count
                    zone.our_count = our_count

    def _find_enemy_clusters(self, enemy_units) -> List[Tuple[Point2, List]]:
        """적 병력 클러스터 찾기"""
        if not enemy_units:
            return []

        clusters = []
        processed = set()

        for unit in enemy_units:
            if unit.tag in processed:
                continue

            # 이 유닛 근처의 적들 찾기
            nearby = [
                u for u in enemy_units
                if u.distance_to(unit) < 10 and u.tag not in processed
            ]

            if nearby:
                # 클러스터 중심 계산
                center_x = sum(u.position.x for u in nearby) / len(nearby)
                center_y = sum(u.position.y for u in nearby) / len(nearby)
                center = Point2((center_x, center_y))

                clusters.append((center, nearby))

                for u in nearby:
                    processed.add(u.tag)

        return clusters

    async def _prepare_for_battles(self, game_time: float):
        """교전 준비"""
        for zone_key, zone in list(self.battle_zones.items()):
            if not zone.is_active:
                continue

            power_ratio = zone.our_count / max(zone.enemy_count, 1)

            # 1. 병력 부족 시 지원 요청
            if power_ratio < 1.2 and not zone.reinforcements_requested:
                await self._request_reinforcements(zone, game_time)
                zone.reinforcements_requested = True

            # 2. 병력 우위 시 적극 공격
            elif power_ratio > 1.5:
                await self._order_aggressive_attack(zone)

            # 3. 병력 열세 시 후퇴 준비
            elif power_ratio < 0.7:
                await self._prepare_retreat(zone)

    async def _request_reinforcements(self, zone: BattleZone, game_time: float):
        """지원 병력 요청"""
        self.logger.info(
            f"[{int(game_time)}s] REINFORCEMENTS requested for battle at {zone.center}"
        )

        # 근처 아군 병력 집결
        our_army = self.bot.units.filter(
            lambda u: u.distance_to(zone.center) < self.REINFORCEMENT_RADIUS * 2 and
            u.type_id not in {UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.LARVA, UnitTypeId.EGG}
        )

        # 집결 포인트 (교전 지역 약간 뒤)
        our_base = self.bot.start_location
        rally_point = zone.center.towards(our_base, self.RALLY_DISTANCE)

        for unit in our_army:
            if unit.distance_to(zone.center) > self.ENGAGEMENT_DETECTION_RADIUS:
                # 아직 교전 중이 아닌 유닛들 집결
                self.bot.do(unit.move(rally_point))

        self.logger.info(f"  Rallying {our_army.amount} units to {rally_point}")

    async def _order_aggressive_attack(self, zone: BattleZone):
        """적극 공격 명령"""
        our_units = self.bot.units.filter(
            lambda u: u.distance_to(zone.center) < self.ENGAGEMENT_DETECTION_RADIUS + 5 and
            u.type_id not in {UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.LARVA, UnitTypeId.EGG}
        )

        if not our_units:
            return

        # 가장 가까운 적 찾기
        enemy_units = self.bot.enemy_units.filter(
            lambda u: u.distance_to(zone.center) < self.ENGAGEMENT_DETECTION_RADIUS and
            not u.is_structure
        )

        if enemy_units:
            target = enemy_units.closest_to(zone.center)
            for unit in our_units:
                self.bot.do(unit.attack(target.position))

    async def _prepare_retreat(self, zone: BattleZone):
        """후퇴 준비"""
        our_units = self.bot.units.filter(
            lambda u: u.distance_to(zone.center) < self.ENGAGEMENT_DETECTION_RADIUS and
            u.type_id not in {UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.LARVA, UnitTypeId.EGG}
        )

        if not our_units:
            return

        # 가장 가까운 아군 기지로 후퇴
        retreat_pos = self.bot.townhalls.closest_to(zone.center).position

        for unit in our_units:
            # 체력 낮은 유닛 우선 후퇴
            if unit.health_percentage < 0.5:
                self.bot.do(unit.move(retreat_pos))

    async def _manage_active_battles(self):
        """활성 교전 관리"""
        for zone_key, zone in list(self.battle_zones.items()):
            # 교전 종료 확인 (적이 사라짐)
            enemy_nearby = self.bot.enemy_units.filter(
                lambda u: u.distance_to(zone.center) < self.ENGAGEMENT_DETECTION_RADIUS and
                not u.is_structure
            )

            if not enemy_nearby:
                # 교전 종료
                zone.is_active = False
                self._evaluate_battle_result(zone)
                del self.battle_zones[zone_key]

    def _evaluate_battle_result(self, zone: BattleZone):
        """교전 결과 평가"""
        # 간단한 평가: 아군이 많이 남았으면 승리
        our_remaining = self.bot.units.filter(
            lambda u: u.distance_to(zone.center) < self.ENGAGEMENT_DETECTION_RADIUS and
            u.type_id not in {UnitTypeId.DRONE, UnitTypeId.OVERLORD}
        ).amount

        if our_remaining > zone.enemy_count * 0.5:
            self.battles_won += 1
            self.logger.info(f"[BATTLE] Victory at {zone.center}! (Our units: {our_remaining})")
        else:
            self.battles_lost += 1
            self.logger.info(f"[BATTLE] Defeat at {zone.center}")

    def _print_battle_status(self, game_time: float):
        """교전 상태 출력"""
        active_count = len([z for z in self.battle_zones.values() if z.is_active])

        if active_count > 0:
            self.logger.info(
                f"[BATTLE_STATUS] [{int(game_time)}s] "
                f"Active: {active_count}, Won: {self.battles_won}, Lost: {self.battles_lost}"
            )

            for zone in self.battle_zones.values():
                if zone.is_active:
                    ratio = zone.our_count / max(zone.enemy_count, 1)
                    self.logger.info(
                        f"  @ {zone.center}: Enemy {zone.enemy_count} vs Our {zone.our_count} "
                        f"(Ratio: {ratio:.2f})"
                    )

    def get_statistics(self) -> Dict:
        """통계 반환"""
        total_battles = self.battles_won + self.battles_lost
        win_rate = (self.battles_won / total_battles * 100) if total_battles > 0 else 0

        return {
            "total_battles": total_battles,
            "battles_won": self.battles_won,
            "battles_lost": self.battles_lost,
            "win_rate": f"{win_rate:.1f}%",
            "active_battles": len([z for z in self.battle_zones.values() if z.is_active])
        }
