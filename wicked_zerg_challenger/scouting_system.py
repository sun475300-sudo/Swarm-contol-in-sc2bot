#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scouting System - Overlord sensor network + scouting.
"""

from typing import Dict, List
from pathlib import Path
import json
import csv
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        OVERLORD = "OVERLORD"
        OVERSEER = "OVERSEER"
        ZERGLING = "ZERGLING"
        HATCHERY = "HATCHERY"
        LAIR = "LAIR"
        HIVE = "HIVE"
    class AbilityId:
        MORPH_OVERSEER = "MORPH_OVERSEER"
    Point2 = tuple


class ScoutingSystem:
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("ScoutingSystem")
        self.intel_manager = None
        self.last_scout_update = 0
        self.last_overseer_morph = 0
        self.scout_assignments: Dict[int, Point2] = {}
        self.scout_zerglings: List[int] = []
        self.last_sensor_log = 0
        self.log_interval = 220
        self.sensor_csv_path = "logs/sensor_network.csv"
        self.sensor_json_path = "logs/sensor_network.json"

        # ★★★ 주기 정찰 강화 ★★★
        self.expansion_scout_index = 0  # 확장 기지 정찰 순번
        self.last_expansion_scout = 0  # 마지막 확장 정찰 시간
        self.scouted_expansions = set()  # 정찰한 확장 위치
        self.last_proxy_check = 0  # 프록시 체크 시간
        self.proxy_check_locations: List[Point2] = []  # 프록시 의심 위치
        self.army_tracking_positions: List[Point2] = []  # 적 군대 추적 위치

        params = getattr(self.bot, "scout_params", None)
        if isinstance(params, dict):
            self.log_interval = params.get("log_interval", self.log_interval)
            self.sensor_csv_path = params.get("sensor_csv_path", self.sensor_csv_path)
            self.sensor_json_path = params.get("sensor_json_path", self.sensor_json_path)

    async def on_step(self, iteration: int):
        try:
            if not self.intel_manager and hasattr(self.bot, "intel"):
                self.intel_manager = self.bot.intel

            # ★ 개선: 70 → 50 (정찰 빈도 더욱 증가, 약 2초마다)
            if iteration - self.last_scout_update > 50:
                await self._update_overlord_network()
                await self._assign_ling_scouts()
                await self._maybe_morph_overseer()
                self.last_scout_update = iteration

            # ★★★ 새로운 정찰 기능 ★★★
            # 확장 기지 순환 정찰 (15초마다)
            if iteration - self.last_expansion_scout > 330:
                await self._scout_expansions()
                self.last_expansion_scout = iteration

            # 프록시/숨겨진 건물 체크 (30초마다, 초반 5분간)
            if self.bot.time < 300 and iteration - self.last_proxy_check > 660:
                await self._check_proxy_locations()
                self.last_proxy_check = iteration

            # 오버로드 희생 정찰 (3분 30초 ~ 4분 사이)
            if 210 < self.bot.time < 270:
                await self._sacrifice_overlord_scout()

            await self._move_scouts()
            self._log_sensor_snapshot(iteration)
        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"Scouting system error: {e}")

    async def _sacrifice_overlord_scout(self):
        """★ 오버로드 희생 정찰 (Sacrifice Scout) ★"""
        if getattr(self, "_sacrifice_scout_performed", False):
            return

        if not self.bot.enemy_start_locations:
            return

        enemy_main = self.bot.enemy_start_locations[0]
        
        # 적 본진과 가장 가까운 오버로드 선택
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        if not overlords.exists:
            return
            
        scout = overlords.closest_to(enemy_main)
        
        # 너무 멀면(100 이상) 아직 도착 안한거라 판단하고 일단 보냄 (또는 가장 가까운 놈)
        # 희생 정찰 명령
        if hasattr(scout, "tag"):
            self.scout_assignments[scout.tag] = enemy_main
            # 강제로 이동 명령 (move scouts에서 처리하지만 확실하게)
            self.bot.do(scout.move(enemy_main))
            self.bot.do(scout.hold_position(queue=True)) # 도착 후 홀드? 아니면 계속 이동? 보통 move면 충분.
            
            print(f"[SCOUT] ★★★ SACRIFICE OVERLORD SENT to {enemy_main} ★★★")
            self._sacrifice_scout_performed = True

    async def _update_overlord_network(self):
        if not hasattr(self.bot, "units"):
            return
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        if not overlords.exists:
            return
        if not self.bot.enemy_start_locations or not self.bot.townhalls.exists:
            return

        enemy_start = self.bot.enemy_start_locations[0]
        our_base = self.bot.townhalls.first.position
        map_center = getattr(self.bot.game_info, "map_center", our_base)

        # Perimeter radar points
        perimeter = self._compute_perimeter_points(map_center, 0.55)
        drop_watch = self._compute_drop_watch_points(our_base, enemy_start)
        path_points = [our_base.towards(enemy_start, d) for d in (20.0, 35.0)]
        targets = perimeter[:4] + drop_watch + path_points

        for overlord, target in zip(overlords, targets):
            self.scout_assignments[overlord.tag] = target

    async def _assign_ling_scouts(self):
        """저글링 정찰 배정 - ★ 개선: 2마리 → 4마리로 증가 ★"""
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if not zerglings.exists or not self.bot.enemy_start_locations:
            return

        # ★ 게임 시간대별 정찰 저글링 수 조정
        game_time = getattr(self.bot, "time", 0)
        if game_time < 180:  # 초반 3분
            max_scouts = 2
        elif game_time < 360:  # 3-6분
            max_scouts = 3
        else:  # 6분 이후
            max_scouts = 4

        active = [z for z in zerglings if z.tag in self.scout_zerglings]
        if len(active) >= max_scouts:
            return

        available = [z for z in zerglings if z.tag not in self.scout_zerglings]
        
        # 적 기지 위치를 아직 모르면 모든 스타팅 포인트 정찰
        enemy_base_found = False
        if self.intel_manager:
             enemy_base_found = self.intel_manager.enemy_main_base_location is not None

        start_locations = self.bot.enemy_start_locations
        
        for i, z in enumerate(available[:max_scouts - len(active)]):
            self.scout_zerglings.append(z.tag)
            
            if not enemy_base_found:
                # 적 발견 전: 스타팅 포인트 순회
                loc_index = (iteration // 100 + i) % len(start_locations)
                self.scout_assignments[z.tag] = start_locations[loc_index]
            else:
                # 적 발견 후: 기존 로직 (메인, 센터, 멀티)
                if len(self.scout_zerglings) == 1:
                    self.scout_assignments[z.tag] = start_locations[0]
                elif len(self.scout_zerglings) == 2:
                    map_center = getattr(self.bot.game_info, "map_center", start_locations[0])
                    self.scout_assignments[z.tag] = map_center
                else:
                    expansions = getattr(self.bot, "expansion_locations_list", [])
                    if expansions and len(expansions) > len(self.scout_zerglings) - 3:
                        self.scout_assignments[z.tag] = expansions[len(self.scout_zerglings) - 3]
                    else:
                        self.scout_assignments[z.tag] = start_locations[0]

    async def _maybe_morph_overseer(self):
        if self.bot.time < 240 or self.bot.vespene < 50:
            return
        if self.bot.structures(UnitTypeId.LAIR).exists or self.bot.structures(UnitTypeId.HIVE).exists:
            overlords = self.bot.units(UnitTypeId.OVERLORD)
            if overlords.exists and self.bot.time - self.last_overseer_morph > 60:
                target = overlords.closest_to(self.bot.townhalls.first.position)
                try:
                    self.bot.do(target(AbilityId.MORPH_OVERSEER))
                    self.last_overseer_morph = self.bot.time
                except Exception as e:
                    self.logger.warning(f"Failed to morph overseer: {e}")

    async def _move_scouts(self):
        # Get nearby enemy detection to avoid interfering with combat
        enemy_units = getattr(self.bot, "enemy_units", [])

        for unit_tag, target_pos in list(self.scout_assignments.items()):
            unit = self.bot.units.find_by_tag(unit_tag)
            if not unit:
                self.scout_assignments.pop(unit_tag, None)
                continue

            # Skip if unit is in combat (enemies nearby)
            has_enemies_nearby = False
            for enemy in enemy_units:
                try:
                    if unit.distance_to(enemy) < 15:
                        has_enemies_nearby = True
                        break
                except Exception:
                    pass

            # Only move if idle AND not in combat
            if unit.is_idle and not has_enemies_nearby:
                try:
                    self.bot.do(unit.move(target_pos))
                except Exception as e:
                    self.logger.warning(f"Failed to move scout {unit.tag}: {e}")

    def _compute_perimeter_points(self, center: Point2, ratio: float) -> List[Point2]:
        if not hasattr(self.bot, "game_info"):
            return []
        map_size = getattr(self.bot.game_info, "map_size", None)
        if not map_size:
            return []
        max_x, max_y = map_size
        radius_x = max_x * ratio
        radius_y = max_y * ratio
        points = []
        for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            points.append(Point2((center.x + dx * radius_x * 0.5, center.y + dy * radius_y * 0.5)))
        return points

    def _compute_drop_watch_points(self, base: Point2, enemy_start: Point2) -> List[Point2]:
        back = base.towards(enemy_start, -12.0)
        base_side = base.towards(enemy_start, -8.0)
        side1 = Point2((base_side.x + 6.0, base_side.y))
        side2 = Point2((base_side.x - 6.0, base_side.y))
        return [back, side1, side2]

    async def _scout_expansions(self):
        """
        ★★★ 확장 기지 순환 정찰 ★★★

        모든 확장 위치를 주기적으로 정찰하여 적의 확장을 파악합니다.
        """
        if not hasattr(self.bot, "expansion_locations_list"):
            return

        expansions = self.bot.expansion_locations_list
        if not expansions:
            return

        # 오버로드 중 정찰에 사용할 유닛 선택
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        if not overlords.exists:
            return

        # 확장 위치를 순환하며 정찰
        if self.expansion_scout_index >= len(expansions):
            self.expansion_scout_index = 0

        target_expansion = expansions[self.expansion_scout_index]
        self.expansion_scout_index += 1

        # 가장 가까운 오버로드를 해당 확장으로 보냄
        if overlords.exists:
            closest_overlord = overlords.closest_to(target_expansion)
            # 기존 할당이 없거나, 우선순위가 낮은 경우에만 재할당
            if closest_overlord.tag not in self.scout_assignments or closest_overlord.is_idle:
                self.scout_assignments[closest_overlord.tag] = target_expansion
                self.scouted_expansions.add(target_expansion)

                # 인텔 매니저에 정보 전달
                if self.intel_manager:
                    try:
                        # 확장 위치 정찰 정보 기록
                        self.intel_manager.record_scouted_location(target_expansion)
                    except Exception as e:
                        self.logger.warning(f"Failed to record scouted location: {e}")

    async def _check_proxy_locations(self):
        """
        ★★★ 프록시/숨겨진 건물 탐색 ★★★

        초반에 프록시 건물이 있을 만한 위치를 체크합니다.
        """
        if not hasattr(self.bot, "enemy_start_locations") or not self.bot.enemy_start_locations:
            return

        enemy_start = self.bot.enemy_start_locations[0]
        our_base = self.bot.townhalls.first.position if self.bot.townhalls.exists else None
        if not our_base:
            return

        # 프록시 의심 위치 계산 (우리 기지와 적 기지 사이)
        if not self.proxy_check_locations:
            # 우리 기지 주변
            for angle in range(0, 360, 45):
                import math
                rad = math.radians(angle)
                offset_x = 15 * math.cos(rad)
                offset_y = 15 * math.sin(rad)
                proxy_pos = Point2((our_base.x + offset_x, our_base.y + offset_y))
                self.proxy_check_locations.append(proxy_pos)

            # 중간 지점
            mid_point = Point2(((our_base.x + enemy_start.x) / 2, (our_base.y + enemy_start.y) / 2))
            for angle in range(0, 360, 90):
                rad = math.radians(angle)
                offset_x = 10 * math.cos(rad)
                offset_y = 10 * math.sin(rad)
                proxy_pos = Point2((mid_point.x + offset_x, mid_point.y + offset_y))
                self.proxy_check_locations.append(proxy_pos)

        # 저글링 또는 오버로드를 프록시 체크 위치로 보냄
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        overlords = self.bot.units(UnitTypeId.OVERLORD)

        available_scouts = []
        if zerglings.exists:
            # 정찰 중이 아닌 저글링
            available_scouts.extend([z for z in zerglings if z.tag not in self.scout_zerglings and z.is_idle])

        if overlords.exists and len(available_scouts) < 2:
            # idle 오버로드
            available_scouts.extend([o for o in overlords if o.is_idle])

        # 프록시 체크 위치에 정찰 유닛 배정
        for i, scout in enumerate(available_scouts[:min(3, len(self.proxy_check_locations))]):
            if i < len(self.proxy_check_locations):
                target = self.proxy_check_locations[i]
                self.scout_assignments[scout.tag] = target
                try:
                    self.bot.do(scout.move(target))
                except Exception as e:
                    self.logger.warning(f"Failed to move proxy scout: {e}")

    def _log_sensor_snapshot(self, iteration: int) -> None:
        if iteration - self.last_sensor_log < self.log_interval:
            return
        self.last_sensor_log = iteration
        game_time = getattr(self.bot, "time", 0.0)
        game_id = getattr(self.bot, "game_id", None) or "unknown"

        rows = []
        for unit_tag, target in self.scout_assignments.items():
            unit = self.bot.units.find_by_tag(unit_tag)
            if not unit:
                continue
            rows.append(
                {
                    "time": f"{game_time:.2f}",
                    "iteration": iteration,
                    "game_id": game_id,
                    "unit_tag": unit_tag,
                    "unit_type": getattr(unit.type_id, "name", str(unit.type_id)),
                    "pos_x": getattr(unit.position, "x", 0.0),
                    "pos_y": getattr(unit.position, "y", 0.0),
                    "target_x": getattr(target, "x", 0.0),
                    "target_y": getattr(target, "y", 0.0),
                }
            )

        if rows:
            try:
                csv_path = Path(self.sensor_csv_path)
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                write_header = not csv_path.exists()
                with csv_path.open("a", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            "time",
                            "iteration",
                            "game_id",
                            "unit_tag",
                            "unit_type",
                            "pos_x",
                            "pos_y",
                            "target_x",
                            "target_y",
                        ],
                    )
                    if write_header:
                        writer.writeheader()
                    writer.writerows(rows)
            except Exception as e:
                self.logger.warning(f"Failed to write sensor CSV: {e}")

            try:
                json_path = Path(self.sensor_json_path)
                json_path.parent.mkdir(parents=True, exist_ok=True)
                json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
            except Exception as e:
                self.logger.warning(f"Failed to write sensor JSON: {e}")
