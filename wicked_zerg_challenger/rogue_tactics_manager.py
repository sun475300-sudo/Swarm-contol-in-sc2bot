# -*- coding: utf-8 -*-
"""
이병렬(Rogue) 선수 전술 구현 매니저

핵심 전술:
1. 맹독충 드랍 (Baneling Drop): 적 병력이 전진하는 타이밍에 드랍
2. 시야 밖 우회 기동: 적의 시야 범위를 피해 드랍 지점까지 이동
3. 라바 세이빙: 교전 직전 라바를 모아두었다가 드랍 후 폭발적 생산
4. 후반 운영: 점막 감지 기반 의사결정
"""

from typing import List, Optional, Set, Tuple
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


class RogueTacticsManager:
    """
    이병렬(Rogue) 선수 전술 구현 매니저

    주요 기능:
    - 맹독충 드랍 타이밍 감지 및 실행
    - 시야 밖 우회 기동 경로 탐색
    - 라바 세이빙 패턴 관리
    - 점막 기반 적 병력 감지
    """

    def __init__(self, bot):
        self.bot = bot

        # 드랍 상태 관리
        self._drop_cooldown = 0
        self._drop_cooldown_duration = 60  # 60초 쿨다운
        self._last_drop_time = 0
        self._drop_in_progress = False
        self._drop_overlords: Set[int] = set()  # 드랍 중인 수송 대군주 태그

        # 라바 세이빙 상태
        self._larva_saving_mode = False
        self._larva_save_start_time = 0
        self._larva_save_duration = 30  # 30초 동안 라바 저장
        self._min_larva_for_burst = 10  # 최소 10라바 저장 후 폭발 생산

        # 점막 감지 상태
        self._enemy_on_creep = False
        self._enemy_creep_position = None
        self._enemy_advancing = False

        # 드랍 타겟 캐시
        self._cached_drop_target = None
        self._drop_target_update_time = 0

        # 우회 경로 캐시
        self._stealth_path_cache = None
        self._stealth_path_update_time = 0

    async def update(self, iteration: int = 0) -> None:
        """
        매 프레임 호출되는 업데이트 메서드

        Args:
            iteration: 현재 게임 반복 횟수
        """
        if not UnitTypeId or not hasattr(self.bot, 'units'):
            return

        game_time = getattr(self.bot, 'time', 0)

        try:
            # 1. 점막 위 적 병력 감지 업데이트
            self._detect_enemy_on_creep()

            # 2. 드랍 쿨다운 업데이트
            if self._drop_cooldown > 0:
                self._drop_cooldown = max(0, self._drop_cooldown_duration - (game_time - self._last_drop_time))

            # 3. 드랍 가능 여부 확인 및 실행
            if self._can_execute_drop():
                await self._execute_baneling_drop()

            # 4. 진행 중인 드랍 관리
            if self._drop_in_progress:
                await self._manage_active_drops()

            # 5. 라바 세이빙 모드 관리
            self._update_larva_saving_mode(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] RogueTacticsManager error: {e}")

    def _check_overlord_speed_upgrade(self) -> bool:
        """대군주 속업 상태 확인"""
        if not UpgradeId or not hasattr(self.bot, 'already_pending_upgrade'):
            return False
        try:
            return self.bot.already_pending_upgrade(UpgradeId.OVERLORDSPEED) > 0
        except Exception:
            return False

    def _detect_enemy_on_creep(self) -> None:
        """
        적 병력이 점막에 닿았는지 감지

        Rogue 전술: 적 병력이 내 기지 앞마당 점막 끝에 도달했을 때 드랍 유닛
        """
        if not hasattr(self.bot, 'enemy_units') or not hasattr(self.bot, 'townhalls'):
            return

        enemy_units = self.bot.enemy_units
        if not enemy_units:
            self._enemy_on_creep = False
            self._enemy_advancing = False
            return

        # 전투 유닛만 필터링
        combat_enemy = [u for u in enemy_units
                       if not getattr(u, 'is_structure', False)
                       and getattr(u.type_id, 'name', '') not in ['SCV', 'PROBE', 'DRONE']]

        if not combat_enemy:
            self._enemy_on_creep = False
            self._enemy_advancing = False
            return

        # 점막 위 적 확인
        for enemy in combat_enemy:
            try:
                if hasattr(self.bot, 'is_visible') and hasattr(self.bot, 'has_creep'):
                    pos = enemy.position
                    if self.bot.has_creep(pos):
                        self._enemy_on_creep = True
                        self._enemy_creep_position = pos

                        # 적이 전진 중인지 확인 (우리 기지 방향으로)
                        if self.bot.townhalls.exists:
                            our_base = self.bot.townhalls.first.position
                            distance_to_base = pos.distance_to(our_base)
                            if distance_to_base < 40:  # 기지 40 거리 내
                                self._enemy_advancing = True
                        return
            except Exception:
                continue

        self._enemy_on_creep = False
        self._enemy_advancing = False

    def _can_execute_drop(self) -> bool:
        """드랍 실행 가능 여부 확인"""
        if not UnitTypeId or not hasattr(self.bot, 'units'):
            return False

        # 쿨다운 중이면 불가
        if self._drop_cooldown > 0:
            return False

        # 이미 드랍 중이면 불가
        if self._drop_in_progress:
            return False

        # 수송 대군주 확인
        overlord_transports = self.bot.units(UnitTypeId.OVERLORDTRANSPORT)
        if not overlord_transports.exists:
            return False

        # 맹독충 확인 (최소 4기 이상)
        banelings = self.bot.units(UnitTypeId.BANELING)
        if not banelings.exists or banelings.amount < 4:
            return False

        # 적 병력이 점막 위에 있고 전진 중일 때만 드랍
        if self._enemy_on_creep and self._enemy_advancing:
            return True

        # 게임 시간 8분 이후 적 본진 드랍도 고려
        game_time = getattr(self.bot, 'time', 0)
        if game_time > 480:  # 8분
            return True

        return False

    def _find_drop_target(self) -> Optional[Point2]:
        """
        드랍 타겟 결정

        우선순위:
        1. 적 본진 일꾼 집중 지역
        2. 적 확장 기지 일꾼
        3. 적 주요 건물 (공성 전차 등)
        """
        if not Point2 or not hasattr(self.bot, 'enemy_structures'):
            return None

        game_time = getattr(self.bot, 'time', 0)

        # 캐시 확인 (5초마다 업데이트)
        if self._cached_drop_target and game_time - self._drop_target_update_time < 5:
            return self._cached_drop_target

        target = None

        # 1. 적 일꾼 위치 확인
        if hasattr(self.bot, 'enemy_units'):
            enemy_workers = [u for u in self.bot.enemy_units
                           if getattr(u.type_id, 'name', '') in ['SCV', 'PROBE', 'DRONE']]
            if len(enemy_workers) >= 5:
                # 일꾼 중심점
                worker_positions = [w.position for w in enemy_workers]
                avg_x = sum(p.x for p in worker_positions) / len(worker_positions)
                avg_y = sum(p.y for p in worker_positions) / len(worker_positions)
                target = Point2((avg_x, avg_y))

        # 2. 적 타운홀 위치
        if not target:
            townhall_types = ['NEXUS', 'COMMANDCENTER', 'ORBITALCOMMAND',
                            'PLANETARYFORTRESS', 'HATCHERY', 'LAIR', 'HIVE']
            enemy_townhalls = [s for s in self.bot.enemy_structures
                              if getattr(s.type_id, 'name', '') in townhall_types]
            if enemy_townhalls:
                target = enemy_townhalls[0].position

        # 3. 적 시작 위치
        if not target:
            if hasattr(self.bot, 'enemy_start_locations') and self.bot.enemy_start_locations:
                target = self.bot.enemy_start_locations[0]

        # 캐시 업데이트
        self._cached_drop_target = target
        self._drop_target_update_time = game_time

        return target

    def _calculate_stealth_path(self, start: Point2, end: Point2) -> List[Point2]:
        """
        시야 밖 우회 기동 경로 계산

        Rogue 전술: 적의 시야 범위를 피해 맵 가장자리를 이용하여 이동

        알고리즘:
        1. 맵 모서리 4개 중 적 시야에서 가장 먼 곳 선택
        2. 해당 모서리를 경유하여 이동
        """
        if not Point2 or not hasattr(self.bot, 'game_info'):
            return [end]

        try:
            map_size = self.bot.game_info.map_size

            # 맵 코너 포인트들
            corners = [
                Point2((5, 5)),  # 좌하단
                Point2((map_size.x - 5, 5)),  # 우하단
                Point2((5, map_size.y - 5)),  # 좌상단
                Point2((map_size.x - 5, map_size.y - 5)),  # 우상단
            ]

            # 적 유닛 위치 수집
            enemy_positions = []
            if hasattr(self.bot, 'enemy_units'):
                enemy_positions = [u.position for u in self.bot.enemy_units]

            # 적에서 가장 먼 코너 선택
            best_corner = corners[0]
            best_distance = 0

            for corner in corners:
                if enemy_positions:
                    min_enemy_dist = min(corner.distance_to(ep) for ep in enemy_positions)
                else:
                    min_enemy_dist = float('inf')

                if min_enemy_dist > best_distance:
                    best_distance = min_enemy_dist
                    best_corner = corner

            # 경유지 포함 경로 생성
            path = [start, best_corner, end]

            return path

        except Exception:
            return [end]

    async def _execute_baneling_drop(self) -> None:
        """맹독충 드랍 실행"""
        if not UnitTypeId or not AbilityId:
            return

        target = self._find_drop_target()
        if not target:
            return

        try:
            # 수송 대군주 선택
            overlord_transports = self.bot.units(UnitTypeId.OVERLORDTRANSPORT)
            if not overlord_transports.exists:
                return

            transport = overlord_transports.first

            # 맹독충 선택 (최대 8기)
            banelings = self.bot.units(UnitTypeId.BANELING)
            if not banelings.exists:
                return

            # 수송 대군주에 맹독충 탑승
            loaded_count = 0
            max_load = 8  # 대군주는 최대 8 슬롯

            for baneling in banelings:
                if loaded_count >= max_load:
                    break
                try:
                    # 맹독충이 수송기 근처에 있으면 탑승
                    if baneling.distance_to(transport) < 5:
                        self.bot.do(baneling(AbilityId.SMART, transport))
                        loaded_count += 1
                    else:
                        # 수송기로 이동
                        self.bot.do(baneling.move(transport.position))
                except Exception:
                    continue

            # 탑승 완료 확인 후 드랍 위치로 이동
            cargo = getattr(transport, 'cargo_used', 0)
            if cargo >= 4:  # 최소 4기 이상 탑승
                # 우회 경로 계산
                path = self._calculate_stealth_path(transport.position, target)

                # 경유지 순서대로 이동 명령
                for waypoint in path:
                    self.bot.do(transport.move(waypoint, queue=True))

                # 목표 지점 도착 후 하차
                self.bot.do(transport(AbilityId.UNLOADALLAT, target, queue=True))

                self._drop_in_progress = True
                self._drop_overlords.add(transport.tag)
                self._last_drop_time = getattr(self.bot, 'time', 0)

                game_time = getattr(self.bot, 'time', 0)
                print(f"[ROGUE DROP] [{int(game_time)}s] Baneling drop initiated with {cargo} banelings")

        except Exception as e:
            print(f"[WARNING] Baneling drop execution error: {e}")

    async def _manage_active_drops(self) -> None:
        """진행 중인 드랍 관리"""
        if not UnitTypeId:
            return

        try:
            # 드랍 오버로드 확인
            overlord_transports = self.bot.units(UnitTypeId.OVERLORDTRANSPORT)

            for tag in list(self._drop_overlords):
                transport = overlord_transports.find_by_tag(tag)

                if not transport:
                    # 수송기가 죽었으면 제거
                    self._drop_overlords.discard(tag)
                    continue

                # 화물이 비었으면 드랍 완료
                cargo = getattr(transport, 'cargo_used', 0)
                if cargo == 0:
                    self._drop_overlords.discard(tag)

                    # 수송기 복귀
                    if self.bot.townhalls.exists:
                        retreat_pos = self.bot.townhalls.first.position
                        self.bot.do(transport.move(retreat_pos))

            # 모든 드랍이 완료되면 상태 리셋
            if not self._drop_overlords:
                self._drop_in_progress = False
                self._drop_cooldown = self._drop_cooldown_duration

        except Exception as e:
            print(f"[WARNING] Active drop management error: {e}")

    def _update_larva_saving_mode(self, game_time: float) -> None:
        """라바 세이빙 모드 업데이트"""
        # 드랍 준비 중이면 라바 저장
        if self._can_execute_drop() and not self._larva_saving_mode:
            self._larva_saving_mode = True
            self._larva_save_start_time = game_time
            print(f"[ROGUE] [{int(game_time)}s] Larva saving mode activated")

        # 드랍 후 또는 시간 초과 시 라바 저장 해제
        if self._larva_saving_mode:
            if game_time - self._larva_save_start_time > self._larva_save_duration:
                self._larva_saving_mode = False
                print(f"[ROGUE] [{int(game_time)}s] Larva saving mode deactivated")

    def should_save_larva(self) -> bool:
        """라바 세이빙 모드 여부 반환"""
        return self._larva_saving_mode

    @property
    def larva_saving_active(self) -> bool:
        """라바 세이빙 모드 여부 (속성으로 접근)"""
        return self._larva_saving_mode

    @property
    def preparing_baneling_drop(self) -> bool:
        """맹독충 드랍 준비 중인지 여부"""
        return self._can_execute_drop() and not self._drop_in_progress

    def get_enemy_on_creep_status(self) -> Tuple[bool, bool, Optional[Point2]]:
        """
        적이 점막에 있는지, 전진 중인지 반환

        Returns:
            Tuple[bool, bool, Optional[Point2]]: (점막 위 여부, 전진 여부, 위치)
        """
        return self._enemy_on_creep, self._enemy_advancing, self._enemy_creep_position

    def get_drop_readiness(self) -> dict:
        """드랍 준비 상태 반환"""
        return {
            "can_drop": self._can_execute_drop(),
            "cooldown_remaining": max(0, self._drop_cooldown),
            "drop_in_progress": self._drop_in_progress,
            "larva_saving": self._larva_saving_mode,
            "enemy_on_creep": self._enemy_on_creep,
            "enemy_advancing": self._enemy_advancing,
        }

    async def on_step(self, iteration: int) -> None:
        """on_step 호환 메서드"""
        await self.update(iteration)
