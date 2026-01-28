# -*- coding: utf-8 -*-
"""
Creep Highway Manager - 기지 간 연결 우선 점막 확장

기지 간 "고속도로"를 먼저 건설하여:
- 퀸 이동 속도 향상 (수비/합류)
- 병력 기동성 확보
- 빠른 증원 및 재배치
"""

from typing import List, Dict, Set, Tuple, Optional
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        QUEEN = "QUEEN"
        CREEPTUMOR = "CREEPTUMOR"
        CREEPTUMORQUEEN = "CREEPTUMORQUEEN"
        CREEPTUMORBURROWED = "CREEPTUMORBURROWED"
    class AbilityId:
        BUILD_CREEPTUMOR_QUEEN = "BUILD_CREEPTUMOR_QUEEN"
        BUILD_CREEPTUMOR_TUMOR = "BUILD_CREEPTUMOR_TUMOR"
    Point2 = tuple


class CreepHighwayManager:
    """
    ★ Creep Highway Manager ★

    기지 간 연결을 최우선으로 점막을 확장합니다.
    적 기지 방향보다 아군 기지 연결이 우선입니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("CreepHighway")

        # ★ 체크 주기 ★
        self.last_check = 0
        self.check_interval = 44  # 약 2초마다

        # ★ 고속도로 계획 ★
        self.highways: List[Dict] = []  # [{from: pos, to: pos, progress: 0-100, waypoints: []}]
        self.highway_waypoints: Set[Tuple[int, int]] = set()  # 고속도로 경유지

        # ★ 우선순위 ★
        self.priority_mode = "HIGHWAY"  # HIGHWAY, ENEMY, BALANCED

        # ★ 통계 ★
        self.highways_completed = 0
        self.total_creep_tumors = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration - self.last_check < self.check_interval:
                return

            self.last_check = iteration

            # ★ 1. 기지 간 고속도로 계획 업데이트 ★
            await self._update_highway_plan()

            # ★ 2. 고속도로 건설 ★
            await self._build_highways(iteration)

            # ★ 3. 적 방향 점막 확장 (고속도로 완료 후) ★
            if self._are_highways_complete():
                await self._expand_toward_enemy(iteration)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[CREEP_HIGHWAY] Error: {e}")

    async def _update_highway_plan(self):
        """
        기지 간 고속도로 계획 수립
        """
        if not hasattr(self.bot, "townhalls"):
            return

        townhalls = self.bot.townhalls
        if townhalls.amount < 2:
            return

        # ★ 기존 고속도로 목록 ★
        existing_highways = set()
        for highway in self.highways:
            key = (highway["from"], highway["to"])
            existing_highways.add(key)

        # ★ 모든 기지 쌍에 대해 고속도로 계획 ★
        bases = list(townhalls)
        new_highways = []

        for i, base1 in enumerate(bases):
            for base2 in bases[i+1:]:
                pos1 = base1.position
                pos2 = base2.position

                # 이미 계획된 고속도로인지 확인
                key1 = (pos1, pos2)
                key2 = (pos2, pos1)

                if key1 not in existing_highways and key2 not in existing_highways:
                    # 새 고속도로 계획
                    waypoints = self._calculate_waypoints(pos1, pos2)
                    highway = {
                        "from": pos1,
                        "to": pos2,
                        "progress": 0,
                        "waypoints": waypoints,
                        "completed": False,
                    }
                    new_highways.append(highway)

        if new_highways:
            self.highways.extend(new_highways)
            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ NEW HIGHWAYS PLANNED: {len(new_highways)} ★"
            )

    def _calculate_waypoints(self, start: Point2, end: Point2, spacing: float = 8.0) -> List[Point2]:
        """
        두 지점 사이의 경유지 계산

        Args:
            start: 시작 위치
            end: 종료 위치
            spacing: 경유지 간격

        Returns:
            경유지 리스트
        """
        distance = start.distance_to(end)
        num_waypoints = int(distance / spacing)

        if num_waypoints < 1:
            return []

        waypoints = []
        for i in range(1, num_waypoints):
            ratio = i / num_waypoints
            x = start.x + (end.x - start.x) * ratio
            y = start.y + (end.y - start.y) * ratio
            waypoints.append(Point2((x, y)))

        return waypoints

    async def _build_highways(self, iteration: int):
        """
        고속도로 건설 실행
        """
        if not self.highways:
            return

        # 완료되지 않은 고속도로 중 우선순위가 높은 것 선택
        incomplete_highways = [h for h in self.highways if not h["completed"]]
        if not incomplete_highways:
            return

        # 가장 가까운 고속도로 우선 (본진 근처)
        main_base = self.bot.townhalls.first if self.bot.townhalls else None
        if not main_base:
            return

        sorted_highways = sorted(
            incomplete_highways,
            key=lambda h: main_base.position.distance_to(h["from"])
        )

        # 최대 2개 고속도로 동시 건설
        for highway in sorted_highways[:2]:
            await self._build_single_highway(highway, iteration)

    async def _build_single_highway(self, highway: Dict, iteration: int):
        """
        단일 고속도로 건설

        Args:
            highway: 고속도로 정보
            iteration: 현재 iteration
        """
        waypoints = highway["waypoints"]
        if not waypoints:
            highway["completed"] = True
            return

        # ★ 점막 확산 퀸 찾기 ★
        creep_queens = self._get_creep_queens()
        if not creep_queens:
            return

        # ★ 경유지 중 점막이 없는 곳 찾기 ★
        for i, waypoint in enumerate(waypoints):
            # 점막 확인
            if self.bot.has_creep(waypoint):
                continue

            # 가장 가까운 퀸 선택
            queen = creep_queens.closest_to(waypoint)
            if not queen:
                continue

            # 퀸 에너지 확인
            if queen.energy < 25:
                continue

            # Tumor 배치
            if queen.distance_to(waypoint) < 8:
                # 가까우면 즉시 배치
                abilities = await self.bot.get_available_abilities(queen)
                if AbilityId.BUILD_CREEPTUMOR_QUEEN in abilities:
                    self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, waypoint))
                    self.total_creep_tumors += 1

                    game_time = getattr(self.bot, "time", 0)
                    self.logger.info(
                        f"[{int(game_time)}s] ★ HIGHWAY TUMOR: {i+1}/{len(waypoints)} ★"
                    )
                    break
            else:
                # 멀면 이동
                self.bot.do(queen.move(waypoint))
                break

        # ★ 진행률 업데이트 ★
        covered = sum(1 for wp in waypoints if self.bot.has_creep(wp))
        progress = int((covered / len(waypoints)) * 100) if waypoints else 100
        highway["progress"] = progress

        if progress >= 100:
            highway["completed"] = True
            self.highways_completed += 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★★★ HIGHWAY COMPLETED! ★★★\n"
                f"  From: {highway['from']}\n"
                f"  To: {highway['to']}\n"
                f"  Total Highways: {self.highways_completed}"
            )

    def _get_creep_queens(self) -> List:
        """
        점막 확산 전용 퀸 반환

        Returns:
            퀸 리스트
        """
        if not hasattr(self.bot, "units"):
            return []

        queens = self.bot.units(UnitTypeId.QUEEN)

        # 에너지 25 이상인 퀸만
        creep_queens = [q for q in queens if q.energy >= 25]

        return creep_queens

    async def _expand_toward_enemy(self, iteration: int):
        """
        고속도로 완료 후 적 방향으로 점막 확장

        Args:
            iteration: 현재 iteration
        """
        if not self.bot.enemy_start_locations:
            return

        enemy_pos = self.bot.enemy_start_locations[0]
        creep_queens = self._get_creep_queens()

        if not creep_queens:
            return

        # 점막 최전선 찾기
        main_base = self.bot.townhalls.first if self.bot.townhalls else None
        if not main_base:
            return

        # 적 방향으로 8거리씩 전진
        direction = enemy_pos - main_base.position
        distance_to_enemy = main_base.position.distance_to(enemy_pos)

        if distance_to_enemy < 1:
            return

        normalized = Point2((direction.x / distance_to_enemy, direction.y / distance_to_enemy))

        # 본진에서 적 방향으로 8거리씩 경유지 생성
        for i in range(1, int(distance_to_enemy / 8)):
            offset = 8 * i
            target_pos = Point2((
                main_base.position.x + normalized.x * offset,
                main_base.position.y + normalized.y * offset
            ))

            # 이미 점막이 있으면 스킵
            if self.bot.has_creep(target_pos):
                continue

            # 가장 가까운 퀸으로 tumor 설치
            queen = creep_queens.closest_to(target_pos)
            if queen and queen.energy >= 25:
                if queen.distance_to(target_pos) < 8:
                    abilities = await self.bot.get_available_abilities(queen)
                    if AbilityId.BUILD_CREEPTUMOR_QUEEN in abilities:
                        self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, target_pos))
                        break
                else:
                    self.bot.do(queen.move(target_pos))
                    break

    def _are_highways_complete(self) -> bool:
        """
        모든 고속도로가 완료되었는지 확인

        Returns:
            True if all highways completed
        """
        if not self.highways:
            return False

        return all(h["completed"] for h in self.highways)

    def get_highway_progress(self) -> Dict:
        """
        고속도로 건설 진행 상황 반환

        Returns:
            진행 상황 딕셔너리
        """
        if not self.highways:
            return {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "average_progress": 0,
            }

        total = len(self.highways)
        completed = sum(1 for h in self.highways if h["completed"])
        in_progress = total - completed

        avg_progress = sum(h["progress"] for h in self.highways) / total if total > 0 else 0

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "average_progress": int(avg_progress),
        }
