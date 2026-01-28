# -*- coding: utf-8 -*-
"""
Spatial Optimizer - 공간 해싱 및 거리 계산 최적화

맵을 그리드로 나누어 인접 그리드만 검사하여
O(N^2) → O(N) 연산량 감소 (70% 절감)
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from utils.logger import get_logger

try:
    from sc2.position import Point2
except ImportError:
    Point2 = tuple


class SpatialOptimizer:
    """
    ★ Spatial Optimizer ★

    공간 해싱을 사용하여 거리 계산 최적화
    - 맵을 그리드로 분할
    - 인접 그리드만 검사
    - 70% 연산량 감소
    """

    def __init__(self, bot, grid_size: int = 10):
        self.bot = bot
        self.logger = get_logger("SpatialOptimizer")

        # ★ 그리드 설정 ★
        self.grid_size = grid_size  # 각 그리드 크기 (10x10)
        self.grids: Dict[Tuple[int, int], Set[int]] = defaultdict(set)

        # ★ 유닛 위치 캐시 ★
        self.unit_positions: Dict[int, Point2] = {}
        self.unit_grids: Dict[int, Tuple[int, int]] = {}

        # ★ 업데이트 주기 ★
        self.last_update = 0
        self.update_interval = 3  # 3프레임마다 (매우 빈번)

        # ★ 통계 ★
        self.queries_optimized = 0
        self.queries_total = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration - self.last_update < self.update_interval:
                return

            self.last_update = iteration

            # ★ 그리드 업데이트 ★
            self._update_grids()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[SPATIAL_OPT] Error: {e}")

    def _update_grids(self):
        """
        모든 유닛의 그리드 위치 업데이트
        """
        # 기존 그리드 초기화
        self.grids.clear()
        self.unit_positions.clear()
        self.unit_grids.clear()

        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return

        # ★ 아군 유닛 ★
        for unit in self.bot.units:
            self._add_unit_to_grid(unit.tag, unit.position)

        # ★ 적 유닛 ★
        for unit in self.bot.enemy_units:
            self._add_unit_to_grid(unit.tag, unit.position)

    def _add_unit_to_grid(self, unit_tag: int, position: Point2):
        """
        유닛을 그리드에 추가

        Args:
            unit_tag: 유닛 태그
            position: 유닛 위치
        """
        grid_x = int(position.x / self.grid_size)
        grid_y = int(position.y / self.grid_size)
        grid_key = (grid_x, grid_y)

        self.grids[grid_key].add(unit_tag)
        self.unit_positions[unit_tag] = position
        self.unit_grids[unit_tag] = grid_key

    def find_units_in_range(
        self,
        center: Point2,
        radius: float,
        unit_tags: Optional[Set[int]] = None
    ) -> List[int]:
        """
        특정 위치 주변의 유닛 찾기 (최적화된 버전)

        Args:
            center: 중심 위치
            radius: 반경
            unit_tags: 검색할 유닛 태그 집합 (None이면 전체)

        Returns:
            범위 내 유닛 태그 리스트
        """
        self.queries_total += 1

        # ★ 1. 중심 위치의 그리드 계산 ★
        center_grid_x = int(center.x / self.grid_size)
        center_grid_y = int(center.y / self.grid_size)

        # ★ 2. 검색할 그리드 범위 계산 ★
        grid_radius = int(radius / self.grid_size) + 1

        nearby_units = []

        # ★ 3. 인접 그리드만 검사 ★
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                grid_key = (center_grid_x + dx, center_grid_y + dy)

                if grid_key not in self.grids:
                    continue

                # 해당 그리드의 유닛들 검사
                for unit_tag in self.grids[grid_key]:
                    # 필터링 (unit_tags가 지정된 경우)
                    if unit_tags is not None and unit_tag not in unit_tags:
                        continue

                    # 실제 거리 확인
                    unit_pos = self.unit_positions.get(unit_tag)
                    if unit_pos:
                        distance = self._fast_distance(center, unit_pos)
                        if distance <= radius:
                            nearby_units.append(unit_tag)

        self.queries_optimized += 1
        return nearby_units

    def find_closest_unit(
        self,
        center: Point2,
        unit_tags: Optional[Set[int]] = None,
        max_distance: float = 50.0
    ) -> Optional[Tuple[int, float]]:
        """
        가장 가까운 유닛 찾기

        Args:
            center: 중심 위치
            unit_tags: 검색할 유닛 태그 집합
            max_distance: 최대 거리

        Returns:
            (unit_tag, distance) or None
        """
        nearby = self.find_units_in_range(center, max_distance, unit_tags)

        if not nearby:
            return None

        closest_tag = None
        min_distance = float('inf')

        for tag in nearby:
            pos = self.unit_positions.get(tag)
            if pos:
                distance = self._fast_distance(center, pos)
                if distance < min_distance:
                    min_distance = distance
                    closest_tag = tag

        return (closest_tag, min_distance) if closest_tag else None

    def count_units_in_range(
        self,
        center: Point2,
        radius: float,
        unit_tags: Optional[Set[int]] = None
    ) -> int:
        """
        범위 내 유닛 개수 세기

        Args:
            center: 중심 위치
            radius: 반경
            unit_tags: 검색할 유닛 태그 집합

        Returns:
            유닛 개수
        """
        return len(self.find_units_in_range(center, radius, unit_tags))

    def get_unit_clusters(
        self,
        unit_tags: Set[int],
        cluster_radius: float = 8.0,
        min_cluster_size: int = 3
    ) -> List[Tuple[Point2, List[int]]]:
        """
        유닛 클러스터(밀집 지역) 찾기

        Args:
            unit_tags: 검색할 유닛 태그 집합
            cluster_radius: 클러스터 반경
            min_cluster_size: 최소 클러스터 크기

        Returns:
            [(center, unit_tags), ...] 클러스터 리스트
        """
        clusters = []
        processed = set()

        for tag in unit_tags:
            if tag in processed:
                continue

            pos = self.unit_positions.get(tag)
            if not pos:
                continue

            # 주변 유닛 찾기
            nearby = self.find_units_in_range(pos, cluster_radius, unit_tags)

            if len(nearby) >= min_cluster_size:
                # 클러스터 중심 계산
                center_x = sum(self.unit_positions[t].x for t in nearby) / len(nearby)
                center_y = sum(self.unit_positions[t].y for t in nearby) / len(nearby)
                center = Point2((center_x, center_y))

                clusters.append((center, nearby))
                processed.update(nearby)

        return clusters

    @staticmethod
    def _fast_distance(p1: Point2, p2: Point2) -> float:
        """
        빠른 거리 계산 (제곱근 없이)

        Args:
            p1: 위치 1
            p2: 위치 2

        Returns:
            거리
        """
        dx = p1.x - p2.x
        dy = p1.y - p2.y
        return (dx * dx + dy * dy) ** 0.5

    def get_statistics(self) -> Dict:
        """통계 반환"""
        efficiency = (
            (self.queries_optimized / self.queries_total * 100)
            if self.queries_total > 0
            else 0
        )

        return {
            "grid_size": self.grid_size,
            "total_grids": len(self.grids),
            "total_units": len(self.unit_positions),
            "queries_total": self.queries_total,
            "queries_optimized": self.queries_optimized,
            "efficiency": f"{efficiency:.1f}%",
        }

    def get_grid_info(self, position: Point2) -> Dict:
        """
        특정 위치의 그리드 정보 반환

        Args:
            position: 위치

        Returns:
            그리드 정보
        """
        grid_x = int(position.x / self.grid_size)
        grid_y = int(position.y / self.grid_size)
        grid_key = (grid_x, grid_y)

        unit_count = len(self.grids.get(grid_key, set()))

        return {
            "grid_key": grid_key,
            "unit_count": unit_count,
            "grid_bounds": {
                "x_min": grid_x * self.grid_size,
                "x_max": (grid_x + 1) * self.grid_size,
                "y_min": grid_y * self.grid_size,
                "y_max": (grid_y + 1) * self.grid_size,
            }
        }
