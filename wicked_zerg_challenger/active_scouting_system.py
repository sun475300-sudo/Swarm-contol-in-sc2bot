# -*- coding: utf-8 -*-
"""
Active Scouting System - 능동형 정찰 시스템

주기적으로 저글링을 파견하여:
- 적 멀티 타이밍 확인
- 적 병력 구성 파악
- 적 테크 진행 상황 감시
"""

from typing import List, Set, Dict, Tuple
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        ZERGLING = "ZERGLING"
    Point2 = tuple


class ActiveScoutingSystem:
    """
    ★ Active Scouting System ★

    저글링을 이용한 능동형 정찰로
    적 정보를 지속적으로 수집합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("ActiveScout")

        # ★ 정찰 주기 ★
        self.last_scout_sent = 0
        self.scout_interval = 880  # 약 40초마다

        # ★ 정찰 목표 ★
        self.scout_targets: List[Point2] = []
        self.scouted_locations: Set[Tuple[int, int]] = set()
        self.active_scouts: Dict[int, Dict] = {}  # {unit_tag: {target: pos, sent_time: time}}

        # ★ 정찰 정보 ★
        self.enemy_expansion_timings: Dict[Point2, float] = {}
        self.enemy_army_composition: Dict[str, int] = {}
        self.enemy_tech_progress: Dict[str, float] = {}

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = getattr(self.bot, "time", 0)

            # ★ 1. 정찰 목표 업데이트 ★
            if iteration % 100 == 0:
                self._update_scout_targets()

            # ★ 2. 정찰 파견 ★
            if game_time - self.last_scout_sent > self.scout_interval:
                await self._send_scout()
                self.last_scout_sent = game_time

            # ★ 3. 활성 정찰 모니터링 ★
            await self._monitor_active_scouts()

            # ★ 4. 정찰 정보 분석 ★
            if iteration % 220 == 0:  # 10초마다
                await self._analyze_scouted_info()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[ACTIVE_SCOUT] Error: {e}")

    def _update_scout_targets(self):
        """
        정찰 목표 위치 업데이트
        """
        if not hasattr(self.bot, "expansion_locations_list"):
            return

        # ★ 확장 위치들을 정찰 목표로 ★
        self.scout_targets = []

        # 1. 적 본진
        if self.bot.enemy_start_locations:
            self.scout_targets.append(self.bot.enemy_start_locations[0])

        # 2. 모든 확장 위치
        for exp_pos in self.bot.expansion_locations_list:
            self.scout_targets.append(exp_pos)

        # 3. 맵 중앙
        if hasattr(self.bot, "game_info") and hasattr(self.bot.game_info, "map_center"):
            self.scout_targets.append(self.bot.game_info.map_center)

    async def _send_scout(self):
        """
        정찰 저글링 파견
        """
        if not hasattr(self.bot, "units"):
            return

        # ★ 여유 저글링 찾기 ★
        zerglings = self.bot.units(UnitTypeId.ZERGLING).idle
        if not zerglings:
            # Idle이 없으면 전체에서 선택
            zerglings = self.bot.units(UnitTypeId.ZERGLING)

        if not zerglings:
            return

        # ★ 정찰 목표 선택 ★
        if not self.scout_targets:
            return

        # 아직 정찰하지 않은 위치 우선
        unscouted = [
            t for t in self.scout_targets
            if (int(t.x), int(t.y)) not in self.scouted_locations
        ]

        if not unscouted:
            # 모두 정찰했으면 처음부터 다시
            unscouted = self.scout_targets

        # 가장 가까운 미정찰 위치 선택
        scout = zerglings.first
        target = min(unscouted, key=lambda pos: scout.position.distance_to(pos))

        # ★ 정찰 파견 ★
        self.bot.do(scout.move(target))
        self.active_scouts[scout.tag] = {
            "target": target,
            "sent_time": getattr(self.bot, "time", 0),
        }

        game_time = getattr(self.bot, "time", 0)
        self.logger.info(
            f"[{int(game_time)}s] ★ SCOUT SENT: {target} ★"
        )

    async def _monitor_active_scouts(self):
        """
        활성 정찰 모니터링
        """
        if not self.active_scouts:
            return

        game_time = getattr(self.bot, "time", 0)

        # 정찰 완료 확인
        completed = []

        for scout_tag, scout_info in self.active_scouts.items():
            # 유닛 존재 확인
            scout = self.bot.units.find_by_tag(scout_tag)
            if not scout:
                completed.append(scout_tag)
                continue

            target = scout_info["target"]

            # 목표 도달 확인 (5거리 이내)
            if scout.position.distance_to(target) < 5:
                # 정찰 완료 기록
                self.scouted_locations.add((int(target.x), int(target.y)))
                completed.append(scout_tag)

                self.logger.info(
                    f"[{int(game_time)}s] ★ SCOUT ARRIVED: {target} ★"
                )

                # 정찰 정보 수집
                await self._collect_scout_info(scout, target)

            # 타임아웃 (60초)
            elif game_time - scout_info["sent_time"] > 60:
                completed.append(scout_tag)

        # 완료된 정찰 제거
        for tag in completed:
            del self.active_scouts[tag]

    async def _collect_scout_info(self, scout, location: Point2):
        """
        정찰 정보 수집

        Args:
            scout: 정찰 유닛
            location: 정찰 위치
        """
        if not hasattr(self.bot, "enemy_structures") or not hasattr(self.bot, "enemy_units"):
            return

        game_time = getattr(self.bot, "time", 0)

        # ★ 1. 적 확장 확인 ★
        enemy_bases = self.bot.enemy_structures.filter(
            lambda s: s.position.distance_to(location) < 10 and
            getattr(s.type_id, "name", "").upper() in {
                "COMMANDCENTER", "NEXUS", "HATCHERY", "LAIR", "HIVE"
            }
        )

        if enemy_bases:
            self.enemy_expansion_timings[location] = game_time
            self.logger.info(
                f"[{int(game_time)}s] ★ ENEMY BASE FOUND: {location} ★"
            )

        # ★ 2. 적 유닛 구성 확인 ★
        nearby_enemies = self.bot.enemy_units.closer_than(15, scout)
        for enemy in nearby_enemies:
            type_name = getattr(enemy.type_id, "name", "").upper()
            self.enemy_army_composition[type_name] = self.enemy_army_composition.get(type_name, 0) + 1

        # ★ 3. 적 테크 건물 확인 ★
        tech_buildings = {
            "FACTORY", "STARPORT", "ARMORY",
            "ROBOTICSFACILITY", "STARGATE", "TWILIGHTCOUNCIL",
            "SPIRE", "HYDRALISKDEN", "ROACHWARREN"
        }

        enemy_tech = self.bot.enemy_structures.closer_than(15, scout)
        for building in enemy_tech:
            type_name = getattr(building.type_id, "name", "").upper()
            if type_name in tech_buildings:
                if type_name not in self.enemy_tech_progress:
                    self.enemy_tech_progress[type_name] = game_time
                    self.logger.info(
                        f"[{int(game_time)}s] ★ ENEMY TECH: {type_name} ★"
                    )

    async def _analyze_scouted_info(self):
        """
        정찰 정보 분석 및 보고
        """
        if not self.enemy_expansion_timings and not self.enemy_army_composition:
            return

        game_time = getattr(self.bot, "time", 0)

        # ★ 1. 적 확장 수 ★
        enemy_base_count = len(self.enemy_expansion_timings)

        # ★ 2. 적 주력 유닛 ★
        if self.enemy_army_composition:
            main_unit = max(self.enemy_army_composition.items(), key=lambda x: x[1])
        else:
            main_unit = ("UNKNOWN", 0)

        # ★ 3. 적 테크 진행 ★
        tech_buildings = len(self.enemy_tech_progress)

        # ★ 4. Blackboard에 정보 등록 ★
        blackboard = getattr(self.bot, "blackboard", None)
        if blackboard:
            blackboard.set("enemy_base_count_scout", enemy_base_count)
            blackboard.set("enemy_main_unit", main_unit[0])
            blackboard.set("enemy_tech_buildings_scout", tech_buildings)

        # ★ 5. 정기 보고 ★
        if int(game_time) % 60 == 0:  # 1분마다
            self.logger.info(
                f"[{int(game_time)}s] ★ SCOUT REPORT ★\n"
                f"  Enemy Bases: {enemy_base_count}\n"
                f"  Main Unit: {main_unit[0]} ({main_unit[1]})\n"
                f"  Tech Buildings: {tech_buildings}\n"
                f"  Army Composition: {dict(list(self.enemy_army_composition.items())[:5])}"
            )

    def get_enemy_info(self) -> Dict:
        """
        적 정보 반환

        Returns:
            적 정보 딕셔너리
        """
        return {
            "base_count": len(self.enemy_expansion_timings),
            "base_timings": self.enemy_expansion_timings,
            "army_composition": self.enemy_army_composition,
            "tech_buildings": self.enemy_tech_progress,
            "scouted_locations": len(self.scouted_locations),
        }
