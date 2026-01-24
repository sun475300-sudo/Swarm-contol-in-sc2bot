"""
저그 건물 배치 헬퍼 모듈
저그 건물의 점막(Creep) 요구사항을 관리하고 안전한 건물 배치를 지원합니다.
"""

from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from typing import Optional, List
import random


# 점막 없이 지을 수 있는 저그 건물
CREEP_NOT_REQUIRED = {
    UnitTypeId.HATCHERY,
    UnitTypeId.LAIR,
    UnitTypeId.HIVE,
    UnitTypeId.EXTRACTOR,
    UnitTypeId.SPINECRAWLER,  # 초기 배치 후 이동 가능
    UnitTypeId.SPORECRAWLER,  # 초기 배치 후 이동 가능
}

# 반드시 점막 위에 지어야 하는 건물
CREEP_REQUIRED = {
    UnitTypeId.SPAWNINGPOOL,
    UnitTypeId.EVOLUTIONCHAMBER,
    UnitTypeId.ROACHWARREN,
    UnitTypeId.BANELINGNEST,
    UnitTypeId.HYDRALISKDEN,
    UnitTypeId.LURKERDENMP,
    UnitTypeId.SPIRE,
    UnitTypeId.GREATERSPIRE,
    UnitTypeId.INFESTATIONPIT,
    UnitTypeId.ULTRALISKCAVERN,
    UnitTypeId.NYDUSNETWORK,
}


def requires_creep(building_type: UnitTypeId) -> bool:
    """
    건물이 점막을 필요로 하는지 확인합니다.

    Args:
        building_type: 건물 타입

    Returns:
        bool: 점막이 필요하면 True, 아니면 False
    """
    return building_type in CREEP_REQUIRED


def can_build_off_creep(building_type: UnitTypeId) -> bool:
    """
    건물을 점막 없이 지을 수 있는지 확인합니다.

    Args:
        building_type: 건물 타입

    Returns:
        bool: 점막 없이 지을 수 있으면 True, 아니면 False
    """
    return building_type in CREEP_NOT_REQUIRED


class BuildingPlacementHelper:
    """저그 건물 배치를 위한 헬퍼 클래스"""

    def __init__(self, bot):
        """
        Args:
            bot: BotAI 인스턴스
        """
        self.bot = bot

    def has_creep(self, position: Point2) -> bool:
        """
        특정 위치에 점막이 있는지 확인합니다.

        Args:
            position: 확인할 위치

        Returns:
            bool: 점막이 있으면 True, 없으면 False
        """
        try:
            if hasattr(self.bot, "has_creep"):
                return self.bot.has_creep(position)
            # 대체 방법: 점막 확인 불가 시 False 반환
            return False
        except Exception:
            return False

    def find_creep_positions(
        self,
        near: Point2,
        search_radius: float = 15.0,
        max_candidates: int = 20
    ) -> List[Point2]:
        """
        주어진 위치 근처의 점막 위치를 찾습니다.

        Args:
            near: 검색 시작 위치
            search_radius: 검색 반경
            max_candidates: 최대 후보 위치 수

        Returns:
            List[Point2]: 점막이 있는 위치 리스트 (거리 순으로 정렬)
        """
        candidates = []

        # 점막이 있는 위치 검색
        for _ in range(max_candidates * 3):  # 충분한 샘플링
            # 랜덤 오프셋 생성
            angle = random.uniform(0, 6.28)  # 0 ~ 2π
            distance = random.uniform(3.0, search_radius)

            offset_x = distance * (2 * random.random() - 1)
            offset_y = distance * (2 * random.random() - 1)

            test_pos = Point2((near.x + offset_x, near.y + offset_y))

            # 맵 범위 내인지 확인
            if not (0 <= test_pos.x < self.bot.game_info.map_size.x and
                    0 <= test_pos.y < self.bot.game_info.map_size.y):
                continue

            # 점막 확인
            if self.has_creep(test_pos):
                candidates.append(test_pos)

            if len(candidates) >= max_candidates:
                break

        # 거리 순으로 정렬
        candidates.sort(key=lambda p: near.distance_to(p))
        return candidates

    async def find_placement_on_creep(
        self,
        building_type: UnitTypeId,
        near: Point2,
        max_distance: float = 15.0,
        placement_step: int = 2
    ) -> Optional[Point2]:
        """
        점막 위에서 건물 배치 가능한 위치를 찾습니다.

        Args:
            building_type: 건물 타입
            near: 검색 시작 위치
            max_distance: 최대 검색 거리
            placement_step: 배치 검색 간격

        Returns:
            Optional[Point2]: 배치 가능한 위치, 없으면 None
        """
        # 점막 필수 건물이 아니면 일반 find_placement 사용
        if not requires_creep(building_type):
            return await self.bot.find_placement(
                building_type,
                near,
                max_distance=max_distance,
                placement_step=placement_step
            )

        # 점막 위치 찾기
        creep_positions = self.find_creep_positions(near, search_radius=max_distance)

        if not creep_positions:
            # 점막을 찾지 못한 경우
            print(f"[WARNING] No creep found near {near} for {building_type.name}")
            return None

        # 각 점막 위치에서 배치 가능 여부 확인
        for pos in creep_positions:
            if await self.bot.can_place(building_type, pos):
                return pos

        # 배치 가능한 위치를 찾지 못함
        print(f"[WARNING] No valid placement on creep near {near} for {building_type.name}")
        return None

    async def build_structure_safely(
        self,
        building_type: UnitTypeId,
        near: Point2,
        max_distance: float = 15.0
    ) -> bool:
        """
        안전하게 건물을 배치합니다 (점막 체크 포함).

        Args:
            building_type: 건물 타입
            near: 건설 위치
            max_distance: 최대 검색 거리

        Returns:
            bool: 건설 명령이 성공했으면 True, 아니면 False
        """
        # 자원 확인
        if not self.bot.can_afford(building_type):
            return False

        # 일꾼 확인
        workers = self.bot.workers
        if not workers.exists:
            return False

        # 배치 위치 찾기
        location = await self.find_placement_on_creep(
            building_type,
            near,
            max_distance=max_distance
        )

        if not location:
            return False

        # 가장 가까운 일꾼 선택
        worker = workers.closest_to(location)
        if not worker:
            return False

        # 건설 명령
        try:
            worker.build(building_type, location)
            print(f"[BUILD] {building_type.name} at {location} (creep: {self.has_creep(location)})")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to build {building_type.name}: {e}")
            return False

    def get_closest_creep_position(self, near: Point2, min_distance: float = 5.0) -> Optional[Point2]:
        """
        가장 가까운 점막 위치를 찾습니다.

        Args:
            near: 검색 시작 위치
            min_distance: 최소 거리

        Returns:
            Optional[Point2]: 점막 위치, 없으면 None
        """
        creep_positions = self.find_creep_positions(near, search_radius=20.0)

        for pos in creep_positions:
            if near.distance_to(pos) >= min_distance:
                return pos

        return creep_positions[0] if creep_positions else None
