# -*- coding: utf-8 -*-
"""
이병렬(Rogue) 선수 전술 구현 매니저

핵심 전술:
1. 맹독충 드랍 (Baneling Drop): 적 병력이 전진하는 타이밍에 드랍
2. 시야 밖 우회 기동: 적의 시야 범위를 피해 드랍 지점까지 이동
3. 라바 세이빙: 교전 직전 라바를 모아두었다가 드랍 후 폭발적 생산
4. 후반 운영: 점막 감지 기반 의사결정
"""

from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from wicked_zerg_bot_pro import WickedZergBotPro

from sc2.ids.ability_id import AbilityId  # type: ignore
from sc2.ids.unit_typeid import UnitTypeId  # type: ignore
from sc2.ids.upgrade_id import UpgradeId  # type: ignore
from sc2.position import Point2  # type: ignore
from sc2.unit import Unit  # type: ignore


class RogueTacticsManager:
    """
    이병렬(Rogue) 선수 전술 구현 매니저
    
    주요 기능:
    - 맹독충 드랍 타이밍 감지 및 실행
    - 시야 밖 우회 기동 경로 탐색
    - 라바 세이빙 패턴 관리
    - 점막 기반 적 병력 감지
    """

    def __init__(self, bot: "WickedZergBotPro"):
        self.bot = bot
        
        # 드랍 상태
        self.drop_squad: List[Unit] = []  # 드랍용 대군주 + 맹독충
        self.drop_target: Optional[Point2] = None
        self.drop_in_progress: bool = False
        self.last_drop_time: float = 0.0
        self.drop_cooldown: float = 30.0  # 드랍 쿨다운 (30초)
        
        # 라바 세이빙 상태
        self.larva_saving_mode: bool = False
        self.saved_larva_count: int = 0
        self.larva_save_start_time: float = 0.0
        self.larva_save_duration: float = 10.0  # 라바 세이빙 지속 시간 (10초)
        
        # 적 병력 감지 (점막 기반)
        self.enemy_on_creep: bool = False
        self.enemy_advancing: bool = False
        self.last_enemy_on_creep_time: float = 0.0
        
        # 대군주 속업 상태
        self.overlord_speed_researched: bool = False
        self.overlord_speed_research_time: float = 0.0
        
        # 시야 범위 계산용
        self.vision_range: float = 11.0  # 대군주 시야 범위
        self.enemy_vision_range: float = 9.0  # 적 유닛 평균 시야 범위

    async def update(self):
        """매 프레임 업데이트"""
        b = self.bot
        
        # 대군주 속업 상태 확인
        self._check_overlord_speed_upgrade()
        
        # 적 병력이 점막에 닿았는지 감지
        self._detect_enemy_on_creep()
        
        # 드랍 실행
        await self._execute_baneling_drop()
        
        # 라바 세이빙 관리
        await self._manage_larva_saving()
        
        # 드랍 유닛 관리
        await self._manage_drop_units()

    def _check_overlord_speed_upgrade(self):
        """대군주 속업 상태 확인"""
        b = self.bot
        
        if UpgradeId.OVERLORDSPEED in b.state.upgrades:
            if not self.overlord_speed_researched:
                self.overlord_speed_researched = True
                self.overlord_speed_research_time = b.time
                print(f"[ROGUE TACTICS] [{int(b.time)}s] Overlord Speed researched - Drop tactics enabled")
        else:
            self.overlord_speed_researched = False

    def _detect_enemy_on_creep(self):
        """
        적 병력이 점막에 닿았는지 감지
        
        Rogue 전술: 적 병력이 내 기지 앞마당 점막 끝에 도달했을 때 드랍 유닛 출발
        """
        b = self.bot
        
        # 점막이 있는 지역 확인
        if not b.townhalls.exists:
            self.enemy_on_creep = False
            self.enemy_advancing = False
            return
        
        main_hatch = b.townhalls.first
        if not main_hatch:
            return
        
        # 점막 반경 내 적 유닛 확인 (점막은 대략 15-20 유닛 반경)
        creep_radius = 20.0
        enemy_units = b.enemy_units.closer_than(creep_radius, main_hatch.position)
        
        if enemy_units.exists:
            self.enemy_on_creep = True
            self.last_enemy_on_creep_time = b.time
            
            # 적이 전진 중인지 확인 (이전 프레임 대비 위치 변화)
            if hasattr(self, "_last_enemy_positions"):
                advancing_count = 0
                for enemy in enemy_units:
                    if enemy.tag in self._last_enemy_positions:
                        last_pos = self._last_enemy_positions[enemy.tag]
                        current_pos = enemy.position
                        # 적이 우리 기지 방향으로 이동 중인지 확인
                        to_base = main_hatch.position - last_pos
                        movement = current_pos - last_pos
                        if to_base.dot(movement) > 0:  # 내적이 양수면 같은 방향
                            advancing_count += 1
                
                self.enemy_advancing = advancing_count >= 3  # 3기 이상 전진 중
            else:
                self.enemy_advancing = True
            
            # 적 위치 저장
            self._last_enemy_positions = {enemy.tag: enemy.position for enemy in enemy_units}
        else:
            self.enemy_on_creep = False
            # 5초 이상 적이 점막에 없으면 전진 상태 해제
            if b.time - self.last_enemy_on_creep_time > 5.0:
                self.enemy_advancing = False

    async def _execute_baneling_drop(self):
        """
        맹독충 드랍 실행
        
        Rogue 전술:
        1. 적 병력이 전진하는 타이밍 감지
        2. 대군주 속업 완료 확인
        3. 맹독충 준비 확인
        4. 시야 밖 우회 기동으로 드랍 지점 이동
        5. 적 본진/확장 기지에 드랍
        
        주의: 드랍 진행 중이면 계속 실행, 아니면 새 드랍 시작
        """
        b = self.bot
        
        # 드랍 진행 중이면 계속 실행
        if self.drop_in_progress:
            # 드랍 유닛 상태 확인
            overlords = b.units(UnitTypeId.OVERLORD)
            drop_overlord = None
            for overlord in overlords:
                if overlord.passengers:  # 유닛을 태운 대군주
                    drop_overlord = overlord
                    break
            
            if drop_overlord and self.drop_target:
                # 드랍 시퀀스 계속 실행
                banelings = list(b.units(UnitTypeId.BANELING).ready)
                path = self._calculate_stealth_path(drop_overlord.position, self.drop_target) or [self.drop_target]
                await self._execute_drop_sequence(drop_overlord, banelings, path, self.drop_target)
            else:
                # 드랍 유닛이 없으면 드랍 중단
                self.drop_in_progress = False
            return
        
        # 새 드랍 시작 조건 확인
        if not self._can_execute_drop():
            return
        
        # 드랍 유닛 준비
        drop_overlord, banelings = await self._prepare_drop_units()
        if not drop_overlord or not banelings:
            return
        
        # 드랍 타겟 결정
        drop_target = self._find_drop_target()
        if not drop_target:
            return
        
        # 시야 밖 우회 경로 계산
        path = self._calculate_stealth_path(drop_overlord.position, drop_target)
        if not path:
            # 우회 경로가 없으면 직접 이동 (위험하지만 시도)
            path = [drop_target]
        
        # 드랍 실행 시작
        await self._execute_drop_sequence(drop_overlord, banelings, path, drop_target)

    def _can_execute_drop(self) -> bool:
        """드랍 실행 가능 여부 확인"""
        b = self.bot
        
        # 1. 대군주 속업 완료 확인
        if not self.overlord_speed_researched:
            return False
        
        # 2. 쿨다운 확인
        if b.time - self.last_drop_time < self.drop_cooldown:
            return False
        
        # 3. 이미 드랍 진행 중이면 스킵
        if self.drop_in_progress:
            return False
        
        # 4. 적이 점막에 있고 전진 중인지 확인 (Rogue 전술 핵심)
        if not (self.enemy_on_creep and self.enemy_advancing):
            return False
        
        # 5. 맹독충이 준비되어 있는지 확인
        banelings = b.units(UnitTypeId.BANELING).ready
        if not banelings.exists or banelings.amount < 4:  # 최소 4기 필요
            return False
        
        # 6. 드랍용 대군주 확인
        overlords = b.units(UnitTypeId.OVERLORD).ready
        if not overlords.exists:
            return False
        
        return True

    async def _prepare_drop_units(self) -> Tuple[Optional[Unit], List[Unit]]:
        """드랍 유닛 준비"""
        b = self.bot
        
        # 맹독충 선택 (최대 8기)
        banelings = list(b.units(UnitTypeId.BANELING).ready)[:8]
        if len(banelings) < 4:
            return None, []
        
        # 드랍용 대군주 선택 (가장 가까운 대군주)
        overlords = b.units(UnitTypeId.OVERLORD).ready
        if not overlords.exists:
            return None, []
        
        # 이미 유닛을 태운 대군주가 있으면 우선 사용
        for overlord in overlords:
            if overlord.passengers:
                return overlord, banelings
        
        # 빈 대군주 선택
        drop_overlord = overlords.closest_to(b.townhalls.first.position)
        return drop_overlord, banelings

    def _find_drop_target(self) -> Optional[Point2]:
        """
        드랍 타겟 결정
        
        우선순위:
        1. 적 본진 일꾼 집중 지역
        2. 적 확장 기지 일꾼
        3. 적 주요 건물 (공성 전차 라인 등)
        """
        b = self.bot
        
        # 적 본진 위치 확인
        if b.enemy_start_locations:
            enemy_main = b.enemy_start_locations[0]
            
            # 적 일꾼 위치 확인
            enemy_workers = b.enemy_units.filter(
                lambda u: u.type_id in [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
            )
            
            if enemy_workers.exists:
                # 일꾼이 가장 많은 지역 찾기
                worker_positions = [w.position for w in enemy_workers]
                if worker_positions:
                    # 일꾼들의 중심점 계산
                    center_x = sum(p.x for p in worker_positions) / len(worker_positions)
                    center_y = sum(p.y for p in worker_positions) / len(worker_positions)
                    return Point2((center_x, center_y))
            
            # 일꾼이 보이지 않으면 본진 중심
            return enemy_main
        
        # 적 본진을 모르면 맵 중심
        return b.game_info.map_center

    def _calculate_stealth_path(
        self, start: Point2, target: Point2
    ) -> Optional[List[Point2]]:
        """
        시야 밖 우회 기동 경로 계산
        
        Rogue 전술: 적의 시야 범위를 피해 맵 가장자리를 이용하여 이동
        
        알고리즘:
        1. 적 유닛의 시야 범위 확인
        2. 직접 경로상에 적 시야가 있으면 우회 경로 계산
        3. 맵 가장자리를 따라 이동하여 적 시야 회피
        """
        b = self.bot
        
        # 1. 맵 경계 확인
        map_width = b.game_info.map_size.width
        map_height = b.game_info.map_size.height
        
        # 2. 적 유닛의 시야 범위 확인
        enemy_units = b.enemy_units
        if not enemy_units.exists:
            # 적이 보이지 않으면 직접 경로
            return [target]
        
        # 3. 직접 경로상에 적 시야가 있는지 확인
        direct_path_blocked = False
        for enemy in enemy_units:
            # 적과 직접 경로의 최단 거리 계산
            enemy_pos = enemy.position
            # 간단한 거리 체크: 적 시야 범위 내에 경로가 있는지
            to_target = target - start
            to_enemy = enemy_pos - start
            
            # 내적을 사용하여 경로가 적 시야 범위 내에 있는지 확인
            if to_target.length > 0:
                projection = (to_enemy.dot(to_target) / to_target.length) / to_target.length
                if 0 < projection < 1:  # 경로상에 있음
                    closest_point = start + to_target * projection
                    if closest_point.distance_to(enemy_pos) < self.enemy_vision_range:
                        direct_path_blocked = True
                        break
        
        # 직접 경로가 막혀있지 않으면 직접 경로 사용
        if not direct_path_blocked:
            return [target]
        
        # 4. 우회 경로 계산: 맵 가장자리를 따라 이동
        waypoints = []
        
        # 시작점에서 맵 가장자리로
        # 왼쪽/오른쪽 가장자리 중 타겟에 더 가까운 쪽 선택
        left_edge = Point2((0, start.y))
        right_edge = Point2((map_width, start.y))
        
        # 타겟 방향의 가장자리 선택
        if abs(start.x - left_edge.x) < abs(start.x - right_edge.x):
            waypoints.append(left_edge)
        else:
            waypoints.append(right_edge)
        
        # 타겟 방향의 가장자리를 따라 이동
        waypoints.append(Point2((waypoints[0].x, target.y)))
        waypoints.append(target)
        
        return waypoints

    async def _execute_drop_sequence(
        self,
        overlord: Unit,
        banelings: List[Unit],
        path: List[Point2],
        target: Point2,
    ):
        """
        드랍 시퀀스 실행
        
        Rogue 전술: 맹독충을 대군주에 태워 적 본진/확장 기지에 드랍
        
        주의: 이 메서드는 매 프레임 호출되며, 드랍 상태에 따라 단계별로 실행됩니다.
        """
        b = self.bot
        
        # 드랍 상태 초기화 (첫 실행 시)
        if not self.drop_in_progress:
            self.drop_in_progress = True
            self.drop_target = target
            self.drop_squad = [overlord] + banelings[:8]
            print(f"[ROGUE DROP] [{int(b.time)}s] Drop sequence started - Target: {target}")
        
        try:
            # 1. 맹독충을 대군주에 태우기 (아직 태우지 않았으면)
            if not overlord.passengers or len(overlord.passengers) < len(banelings):
                for baneling in banelings[:8]:  # 최대 8기
                    if baneling.is_ready and overlord.cargo_space_left > 0:
                        # python-sc2: load 명령 사용
                        try:
                            # LOAD ability는 유닛 타입에 따라 자동 선택됨
                            await b.do(overlord(AbilityId.LOAD, baneling))
                        except Exception:
                            # 대체 방법 시도
                            try:
                                if hasattr(overlord, "load"):
                                    overlord.load(baneling)
                            except Exception:
                                pass
                return  # 다음 프레임에 계속
            
            # 2. 경로를 따라 이동
            if path and len(path) > 0:
                # 현재 waypoint 확인
                current_waypoint_idx = getattr(self, "_current_waypoint_idx", 0)
                if current_waypoint_idx < len(path):
                    next_waypoint = path[current_waypoint_idx]
                    
                    # waypoint에 도달했는지 확인
                    if overlord.distance_to(next_waypoint) < 3.0:
                        # 다음 waypoint로 이동
                        current_waypoint_idx += 1
                        self._current_waypoint_idx = current_waypoint_idx
                    
                    # 다음 waypoint로 이동 명령
                    if current_waypoint_idx < len(path):
                        overlord.move(path[current_waypoint_idx])
                    else:
                        # 모든 waypoint를 지나쳤으면 타겟으로 직접 이동
                        overlord.move(target)
                else:
                    # 경로가 없으면 타겟으로 직접 이동
                    overlord.move(target)
            
            # 3. 타겟 지점에 도달했는지 확인하고 드랍
            if overlord.distance_to(target) < 8.0:  # 8 유닛 이내면 드랍 가능
                # 드랍 실행
                try:
                    # python-sc2: unload_all 명령 사용 (위치 지정)
                    # UNLOADALL_AT 또는 UNLOADALL 사용
                    try:
                        await b.do(overlord(AbilityId.UNLOADALL_AT, target))
                    except (AttributeError, KeyError):
                        # 대체 방법: UNLOADALL 사용
                        try:
                            await b.do(overlord(AbilityId.UNLOADALL, target))
                        except (AttributeError, KeyError):
                            # 최종 대체: 직접 메서드 호출
                            if hasattr(overlord, "unload_all"):
                                overlord.unload_all(target)
                except Exception as unload_error:
                    # 드랍 실패 시 로그만 출력 (다음 프레임에 재시도)
                    if b.iteration % 50 == 0:
                        print(f"[ROGUE DROP] Unload attempt failed: {unload_error}")
                
                print(f"[ROGUE DROP] [{int(b.time)}s] Baneling drop executed at {target}")
                self.last_drop_time = b.time
                
                # 라바 세이빙 해제 (드랍 후 폭발적 생산)
                self.larva_saving_mode = False
                
                # 드랍 완료
                self.drop_in_progress = False
                self._current_waypoint_idx = 0  # waypoint 인덱스 초기화
                
        except Exception as e:
            print(f"[ROGUE DROP ERROR] Drop execution failed: {e}")
            import traceback
            traceback.print_exc()
            # 에러 발생 시 드랍 중단
            self.drop_in_progress = False

    async def _manage_larva_saving(self):
        """
        라바 세이빙 관리
        
        Rogue 전술: 교전 직전 라바를 소모하지 않고 모아두었다가,
        드랍으로 적 일꾼이나 주요 병력을 솎아낸 직후 한꺼번에 폭발적으로 병력을 찍어냄
        """
        b = self.bot
        
        # 적이 점막에 있고 전진 중이면 라바 세이빙 시작
        if self.enemy_on_creep and self.enemy_advancing and not self.larva_saving_mode:
            self.larva_saving_mode = True
            self.larva_save_start_time = b.time
            larvae = b.units(UnitTypeId.LARVA)
            self.saved_larva_count = larvae.amount if larvae.exists else 0
            print(f"[ROGUE LARVA SAVE] [{int(b.time)}s] Larva saving started ({self.saved_larva_count} larvae)")
        
        # 라바 세이빙 모드 해제 조건
        if self.larva_saving_mode:
            # 1. 드랍 완료 후
            if b.time - self.last_drop_time < 2.0 and self.last_drop_time > 0:
                self.larva_saving_mode = False
                print(f"[ROGUE LARVA SAVE] [{int(b.time)}s] Larva saving ended - Drop completed, explosive production enabled")
            
            # 2. 시간 초과 (10초)
            elif b.time - self.larva_save_start_time > self.larva_save_duration:
                self.larva_saving_mode = False
                print(f"[ROGUE LARVA SAVE] [{int(b.time)}s] Larva saving ended - Timeout")
            
            # 3. 적이 점막에서 벗어남
            elif not self.enemy_on_creep and b.time - self.last_enemy_on_creep_time > 3.0:
                self.larva_saving_mode = False
                print(f"[ROGUE LARVA SAVE] [{int(b.time)}s] Larva saving ended - Enemy retreated")

    async def _manage_drop_units(self):
        """
        드랍 유닛 관리 (대군주 + 맹독충)
        
        드랍 진행 중인 대군주의 상태를 확인하고 관리
        (현재는 _execute_drop_sequence에서 처리하므로 여기서는 추가 관리만 수행)
        """
        b = self.bot
        
        # 드랍 진행 중이 아니면 스킵
        if not self.drop_in_progress:
            return
        
        # 드랍 유닛 상태 확인 (추가 로직 필요 시 구현)
        # 현재는 _execute_drop_sequence에서 모든 드랍 로직을 처리

    def should_save_larva(self) -> bool:
        """라바 세이빙 모드 여부 반환"""
        return self.larva_saving_mode

    def get_enemy_on_creep_status(self) -> Tuple[bool, bool]:
        """적이 점막에 있는지, 전진 중인지 반환"""
        return self.enemy_on_creep, self.enemy_advancing

    def get_drop_readiness(self) -> bool:
        """드랍 준비 상태 반환"""
        return (
            self.overlord_speed_researched
            and not self.drop_in_progress
            and (self.bot.time - self.last_drop_time) >= self.drop_cooldown
        )
