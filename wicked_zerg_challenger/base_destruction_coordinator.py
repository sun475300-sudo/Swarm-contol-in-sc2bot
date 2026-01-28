# -*- coding: utf-8 -*-
"""
Base Destruction Coordinator - 적 기지 완전 파괴 시스템

모든 적 기지를 체계적으로 파괴:
1. 적 확장 기지 추적
2. 우선순위 결정 (거리, 방어력, 중요도)
3. 순차적 파괴 (한 기지씩)
4. 완전 승리 보장
"""

from typing import List, Dict, Optional, Set, Tuple
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger
import time


class EnemyBase:
    """적 기지 정보"""

    def __init__(self, position: Point2, discovered_time: float):
        self.position = position
        self.discovered_time = discovered_time
        self.last_seen_time = discovered_time
        self.is_destroyed = False
        self.destruction_time = None
        self.priority = 0  # 공격 우선순위
        self.structure_count = 0  # 건물 수
        self.worker_count = 0  # 일꾼 수
        self.defense_strength = 0  # 방어력


class BaseDestructionCoordinator:
    """
    적 기지 완전 파괴 코디네이터

    모든 적 확장 기지를 추적하고 체계적으로 파괴합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("BaseDestruction")

        # 적 기지 추적
        self.enemy_bases: Dict[str, EnemyBase] = {}  # key: "x_y" position
        self.current_target_base: Optional[str] = None
        self.attack_start_time = 0

        # 설정
        self.base_detection_radius = 10  # 기지로 인식할 반경
        self.base_destroyed_threshold = 2  # 건물 2개 이하면 파괴됨으로 간주
        self.attack_timeout = 180  # 3분 동안 파괴 안 되면 다음 기지로

        # 통계
        self.bases_destroyed = 0
        self.total_bases_discovered = 0

    def _position_to_key(self, pos: Point2) -> str:
        """위치를 키로 변환"""
        return f"{int(pos.x)}_{int(pos.y)}"

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 1. 적 기지 발견 및 업데이트
            self._discover_enemy_bases(game_time)

            # 2. 파괴된 기지 확인
            self._check_destroyed_bases(game_time)

            # 3. 현재 타겟 평가
            if iteration % 22 == 0:  # 1초마다
                self._evaluate_current_target(game_time)

            # 4. 디버그 출력
            if iteration % 440 == 0:  # 20초마다
                self._print_status(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[BASE_DESTRUCTION] Error: {e}")

    def _discover_enemy_bases(self, game_time: float):
        """적 기지 발견"""
        enemy_structures = self.bot.enemy_structures

        # 타운홀류 건물 찾기
        townhall_types = {
            UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS,
            UnitTypeId.NEXUS,
            UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE
        }

        for structure in enemy_structures:
            if structure.type_id in townhall_types:
                key = self._position_to_key(structure.position)

                if key not in self.enemy_bases:
                    # 새 기지 발견
                    self.enemy_bases[key] = EnemyBase(structure.position, game_time)
                    self.total_bases_discovered += 1
                    self.logger.info(
                        f"[{int(game_time)}s] NEW ENEMY BASE discovered at {structure.position} "
                        f"(Total: {self.total_bases_discovered})"
                    )
                else:
                    # 기존 기지 업데이트
                    self.enemy_bases[key].last_seen_time = game_time

        # 모든 기지의 정보 업데이트
        self._update_base_info()

    def _update_base_info(self):
        """기지 정보 업데이트 (건물 수, 일꾼 수, 방어력)"""
        for key, base in self.enemy_bases.items():
            if base.is_destroyed:
                continue

            # 근처 건물 카운트
            nearby_structures = [
                s for s in self.bot.enemy_structures
                if s.distance_to(base.position) < self.base_detection_radius
            ]
            base.structure_count = len(nearby_structures)

            # 근처 일꾼 카운트
            worker_types = {UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE}
            nearby_workers = [
                u for u in self.bot.enemy_units
                if u.type_id in worker_types and u.distance_to(base.position) < 15
            ]
            base.worker_count = len(nearby_workers)

            # 방어력 계산 (방어 건물 + 군대)
            defense_buildings = {
                UnitTypeId.PHOTONCANNON, UnitTypeId.SHIELDBATTERY,
                UnitTypeId.BUNKER, UnitTypeId.MISSILETURRET,
                UnitTypeId.SPORECRAWLER, UnitTypeId.SPINECRAWLER
            }

            nearby_defense = [
                s for s in nearby_structures
                if s.type_id in defense_buildings
            ]

            nearby_army = [
                u for u in self.bot.enemy_units
                if u.distance_to(base.position) < 20 and not u.type_id in worker_types
            ]

            base.defense_strength = len(nearby_defense) * 10 + len(nearby_army)

    def _check_destroyed_bases(self, game_time: float):
        """파괴된 기지 확인"""
        for key, base in self.enemy_bases.items():
            if base.is_destroyed:
                continue

            # 건물이 거의 없으면 파괴됨
            if base.structure_count <= self.base_destroyed_threshold:
                base.is_destroyed = True
                base.destruction_time = game_time
                self.bases_destroyed += 1

                self.logger.info(
                    f"[{int(game_time)}s] ENEMY BASE DESTROYED at {base.position}! "
                    f"({self.bases_destroyed}/{self.total_bases_discovered})"
                )

                # 현재 타겟이었다면 클리어
                if self.current_target_base == key:
                    self.current_target_base = None

    def _evaluate_current_target(self, game_time: float):
        """현재 타겟 평가 및 선정"""
        # 모든 적 기지 파괴됨?
        active_bases = [b for b in self.enemy_bases.values() if not b.is_destroyed]

        if not active_bases:
            # 승리!
            if self.total_bases_discovered > 0:
                self.logger.info(f"[{int(game_time)}s] ALL ENEMY BASES DESTROYED! VICTORY!")
            return

        # 현재 타겟 체크
        if self.current_target_base:
            current_base = self.enemy_bases.get(self.current_target_base)

            if current_base and not current_base.is_destroyed:
                # 타임아웃 체크
                elapsed = game_time - self.attack_start_time
                if elapsed > self.attack_timeout:
                    self.logger.warning(
                        f"[{int(game_time)}s] Attack timeout on base at {current_base.position}. "
                        f"Switching target..."
                    )
                    self.current_target_base = None
                else:
                    # 현재 타겟 유지
                    return

        # 새 타겟 선정
        self._select_next_target(active_bases, game_time)

    def _select_next_target(self, active_bases: List[EnemyBase], game_time: float):
        """다음 공격 타겟 선정"""
        if not active_bases:
            return

        # 우선순위 계산
        for base in active_bases:
            score = 0

            # 1. 거리 (가까울수록 높은 점수)
            our_pos = self.bot.start_location
            distance = base.position.distance_to(our_pos)
            distance_score = max(0, 100 - distance)  # 거리가 가까울수록 높음

            # 2. 방어력 (약할수록 높은 점수)
            defense_score = max(0, 100 - base.defense_strength)

            # 3. 중요도 (일꾼이 많으면 중요)
            importance_score = base.worker_count * 2

            # 4. 시간 (오래된 기지일수록 우선)
            age_score = (game_time - base.discovered_time) / 10

            # 종합 점수
            score = (
                distance_score * 0.3 +
                defense_score * 0.3 +
                importance_score * 0.2 +
                age_score * 0.2
            )

            base.priority = score

        # 가장 높은 우선순위 선택
        target_base = max(active_bases, key=lambda b: b.priority)
        key = self._position_to_key(target_base.position)

        if key != self.current_target_base:
            self.current_target_base = key
            self.attack_start_time = game_time

            self.logger.info(
                f"[{int(game_time)}s] NEW TARGET: Enemy base at {target_base.position} "
                f"(Priority: {target_base.priority:.1f}, Defense: {target_base.defense_strength}, "
                f"Workers: {target_base.worker_count})"
            )

    def get_target_base_position(self) -> Optional[Point2]:
        """
        현재 공격해야 할 적 기지 위치 반환

        Returns:
            타겟 기지 위치, 없으면 None
        """
        if not self.current_target_base:
            return None

        base = self.enemy_bases.get(self.current_target_base)
        if base and not base.is_destroyed:
            return base.position

        return None

    def get_all_active_bases(self) -> List[Point2]:
        """
        모든 활성 적 기지 위치 반환

        Returns:
            활성 기지 위치 리스트
        """
        return [
            base.position
            for base in self.enemy_bases.values()
            if not base.is_destroyed
        ]

    def is_all_bases_destroyed(self) -> bool:
        """
        모든 적 기지가 파괴되었는지 확인

        Returns:
            True if all bases destroyed
        """
        if not self.enemy_bases:
            return False

        return all(base.is_destroyed for base in self.enemy_bases.values())

    def _print_status(self, game_time: float):
        """상태 출력"""
        active_count = len([b for b in self.enemy_bases.values() if not b.is_destroyed])

        if active_count > 0 or self.bases_destroyed > 0:
            self.logger.info(
                f"[BASE_STATUS] [{int(game_time)}s] "
                f"Active: {active_count}, Destroyed: {self.bases_destroyed}/{self.total_bases_discovered}"
            )

            if self.current_target_base:
                target = self.enemy_bases[self.current_target_base]
                self.logger.info(
                    f"  Current Target: {target.position} "
                    f"(Structures: {target.structure_count}, Defense: {target.defense_strength})"
                )

    def get_statistics(self) -> Dict:
        """통계 반환"""
        active_bases = [b for b in self.enemy_bases.values() if not b.is_destroyed]

        return {
            "total_discovered": self.total_bases_discovered,
            "destroyed": self.bases_destroyed,
            "active": len(active_bases),
            "current_target": self.current_target_base is not None,
            "all_destroyed": self.is_all_bases_destroyed()
        }
