# -*- coding: utf-8 -*-
"""
Advanced Building Manager - 건설 로직 고도화 모듈

개선 사항:
1. 중복 코드 블록 공통 함수화 (가시지옥 굴, 맹독충 변태 로직)
2. 방어 타워 건설 위치 개선 (적 공격 경로 분석하여 길목에 건설)
3. 자원 적체 시(3000+) 테크 건물 공격적 건설 로직
"""

from typing import Optional, List, Tuple, Dict, Callable
import math

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
    from sc2.unit import Unit
except ImportError:
    class UnitTypeId:
        LURKERDENMP = "LURKERDENMP"
        BANELINGNEST = "BANELINGNEST"
        ULTRALISKCAVERN = "ULTRALISKCAVERN"
        SPINECRAWLER = "SPINECRAWLER"
        SPORECRAWLER = "SPORECRAWLER"
        HYDRA = "HYDRALISK"
        ZERGLING = "ZERGLING"
        LURKERMP = "LURKERMP"
        BANELING = "BANELING"
        HATCHERY = "HATCHERY"
        LAIR = "LAIR"
        HIVE = "HIVE"
    
    class AbilityId:
        MORPH_LURKER = "MORPH_LURKER"
        MORPHZERGLINGTOBANELING_BANELING = "MORPHZERGLINGTOBANELING_BANELING"
    
    Point2 = tuple
    Unit = object


class AdvancedBuildingManager:
    """
    고도화된 건설 관리자
    
    기능:
    1. 중복 코드 제거: 가시지옥 굴, 맹독충 변태 로직 공통화
    2. 방어 건물 위치 최적화: 적 공격 경로 분석
    3. 자원 적체 시 테크 건물 공격적 건설
    """
    
    def __init__(self, bot):
        self.bot = bot
        # 자원 적체 기준값
        self.resource_surplus_threshold = 3000  # 미네랄 3000 이상
        self.gas_surplus_threshold = 500         # 가스 500 이상
        
        # 방어 건물 건설 관련
        self.defense_buildings_cache = {}  # 캐시된 방어 건물 위치
        
    # ==================== 1. 중복 코드 제거: 공통 변태 로직 ====================
    
    async def morph_unit_safely(
        self,
        source_units: List[Unit],
        target_unit_type: UnitTypeId,
        morph_ability: AbilityId,
        required_building: UnitTypeId,
        min_units: int = 1,
        max_units: Optional[int] = None
    ) -> int:
        """
        공통 변태 로직 (가시지옥, 맹독충 등)
        
        Args:
            source_units: 변태할 유닛 리스트
            target_unit_type: 변태할 유닛 타입
            morph_ability: 변태 능력 ID
            required_building: 필요한 건물 타입
            min_units: 최소 변태할 유닛 수
            max_units: 최대 변태할 유닛 수 (None이면 제한 없음)
            
        Returns:
            변태 성공한 유닛 수
        """
        if not source_units:
            return 0
        
        # 필수 건물 확인
        if hasattr(self.bot, "structures"):
            required_buildings = self.bot.structures(required_building)
            if not required_buildings.ready.exists:
                return 0
        
        # 이미 변태된 유닛 제외
        ready_units = [u for u in source_units if u.is_ready and not u.is_morphing]
        
        if len(ready_units) < min_units:
            return 0
        
        # 최대 변태 수 제한
        if max_units is not None:
            ready_units = ready_units[:max_units]
        
        morphed_count = 0
        
        for unit in ready_units:
            try:
                # 변태 가능 여부 확인
                if hasattr(unit, 'can_morph') and not unit.can_morph:
                    continue
                
                # 변태 실행
                result = self.bot.do(unit(morph_ability))
                if hasattr(result, '__await__'):
                    await result
                
                morphed_count += 1
                
                # 한 번에 하나씩만 변태 (안정성)
                if morphed_count >= min_units:
                    break
                    
            except Exception as e:
                if self.bot.iteration % 100 == 0:
                    print(f"[MORPH] Failed to morph {target_unit_type}: {e}")
                continue
        
        return morphed_count
    
    async def morph_lurkers(self, max_count: Optional[int] = None) -> int:
        """
        가시지옥 변태 (공통 함수 사용)
        
        Args:
            max_count: 최대 변태할 수 (None이면 제한 없음)
            
        Returns:
            변태 성공한 가시지옥 수
        """
        hydralisks = self.bot.units(UnitTypeId.HYDRA).ready
        if not hydralisks.exists:
            return 0
        
        return await self.morph_unit_safely(
            source_units=list(hydralisks),
            target_unit_type=UnitTypeId.LURKERMP,
            morph_ability=AbilityId.MORPH_LURKER,
            required_building=UnitTypeId.LURKERDENMP,
            min_units=1,
            max_units=max_count
        )
    
    async def morph_banelings(self, max_count: Optional[int] = None) -> int:
        """
        맹독충 변태 (공통 함수 사용)
        
        Args:
            max_count: 최대 변태할 수 (None이면 제한 없음)
            
        Returns:
            변태 성공한 맹독충 수
        """
        zerglings = self.bot.units(UnitTypeId.ZERGLING).ready
        if not zerglings.exists:
            return 0
        
        return await self.morph_unit_safely(
            source_units=list(zerglings),
            target_unit_type=UnitTypeId.BANELING,
            morph_ability=AbilityId.MORPHZERGLINGTOBANELING_BANELING,
            required_building=UnitTypeId.BANELINGNEST,
            min_units=1,
            max_units=max_count
        )
    
    # ==================== 2. 방어 건물 위치 최적화 ====================
    
    def analyze_enemy_attack_paths(self) -> List[Point2]:
        """
        적의 공격 경로 분석
        
        Returns:
            적이 자주 지나가는 길목 위치 리스트
        """
        if not hasattr(self.bot, "enemy_units"):
            return []
        
        enemy_units = getattr(self.bot, "enemy_units", [])
        if not enemy_units:
            return []
        
        # 본진 위치
        if not self.bot.townhalls.exists:
            return []
        
        main_base = self.bot.townhalls.first
        base_position = main_base.position
        
        # 적 유닛들의 위치를 분석하여 공격 경로 추정
        enemy_positions = []
        for enemy in enemy_units:
            if hasattr(enemy, 'position'):
                enemy_positions.append(enemy.position)
        
        if not enemy_positions:
            return []
        
        # 적 유닛들이 모이는 지점 찾기 (길목)
        chokepoints = self._find_chokepoints(enemy_positions, base_position)
        
        return chokepoints
    
    def _find_chokepoints(self, enemy_positions: List[Point2], base_position: Point2) -> List[Point2]:
        """
        적 유닛들의 위치를 분석하여 길목 찾기
        
        Args:
            enemy_positions: 적 유닛 위치 리스트
            base_position: 본진 위치
            
        Returns:
            길목 위치 리스트
        """
        if len(enemy_positions) < 2:
            return []
        
        # 적 유닛들의 중심점 계산
        center_x = sum(p.x for p in enemy_positions) / len(enemy_positions)
        center_y = sum(p.y for p in enemy_positions) / len(enemy_positions)
        enemy_center = Point2((center_x, center_y))
        
        # 본진과 적 중심점 사이의 중간 지점들 (길목 후보)
        chokepoints = []
        
        # 본진에서 적 중심점 방향으로 여러 지점 생성
        direction = enemy_center - base_position
        distance = math.sqrt(direction.x**2 + direction.y**2)
        
        if distance > 0:
            # 본진에서 30%, 50%, 70% 지점을 길목 후보로
            for ratio in [0.3, 0.5, 0.7]:
                chokepoint = base_position + Point2((
                    direction.x * ratio,
                    direction.y * ratio
                ))
                chokepoints.append(chokepoint)
        
        return chokepoints
    
    async def build_defense_building_at_chokepoint(
        self,
        building_type: UnitTypeId,
        chokepoint: Point2,
        min_distance_from_base: float = 5.0,
        max_distance_from_base: float = 15.0
    ) -> bool:
        """
        길목에 방어 건물 건설
        
        Args:
            building_type: 건설할 건물 타입
            chokepoint: 길목 위치
            min_distance_from_base: 본진으로부터 최소 거리
            max_distance_from_base: 본진으로부터 최대 거리
            
        Returns:
            건설 성공 여부
        """
        if not self.bot.townhalls.exists:
            return False
        
        main_base = self.bot.townhalls.first
        base_position = main_base.position
        
        # 길목과 본진 사이의 거리 확인
        distance = math.sqrt(
            (chokepoint.x - base_position.x)**2 + 
            (chokepoint.y - base_position.y)**2
        )
        
        if distance < min_distance_from_base or distance > max_distance_from_base:
            return False
        
        # 이미 건설된 건물 확인
        if hasattr(self.bot, "structures"):
            existing = self.bot.structures(building_type)
            if existing.exists:
                # 기존 건물이 길목 근처에 있는지 확인
                for building in existing:
                    if building.distance_to(chokepoint) < 5.0:
                        return False  # 이미 근처에 있음
        
        # 건설 가능 여부 확인
        if not self.bot.can_afford(building_type):
            return False
        
        # 건설 실행
        try:
            result = await self.bot.build(building_type, near=chokepoint)
            if result:
                print(f"[DEFENSE BUILD] Built {building_type} at chokepoint "
                      f"(distance: {distance:.1f} from base)")
                return True
        except Exception as e:
            if self.bot.iteration % 100 == 0:
                print(f"[DEFENSE BUILD] Failed to build {building_type} at chokepoint: {e}")
        
        return False
    
    async def build_defense_buildings_optimally(self) -> Dict[UnitTypeId, int]:
        """
        적 공격 경로를 분석하여 최적 위치에 방어 건물 건설
        
        Returns:
            {building_type: built_count} 딕셔너리
        """
        results = {}
        
        # 적 공격 경로 분석
        chokepoints = self.analyze_enemy_attack_paths()
        
        if not chokepoints:
            # 적이 보이지 않으면 본진 근처에 건설 (기본 로직)
            if self.bot.townhalls.exists:
                main_base = self.bot.townhalls.first
                for building_type in [UnitTypeId.SPINECRAWLER, UnitTypeId.SPORECRAWLER]:
                    if self.bot.can_afford(building_type):
                        try:
                            result = await self.bot.build(
                                building_type,
                                near=main_base.position.towards(
                                    self.bot.game_info.map_center, 8
                                )
                            )
                            if result:
                                results[building_type] = 1
                                break
                        except Exception:
                            pass
            return results
        
        # 길목에 방어 건물 건설
        for chokepoint in chokepoints[:3]:  # 최대 3개 길목
            for building_type in [UnitTypeId.SPINECRAWLER, UnitTypeId.SPORECRAWLER]:
                if building_type in results:
                    continue  # 이미 건설됨
                
                if self.bot.can_afford(building_type):
                    success = await self.build_defense_building_at_chokepoint(
                        building_type,
                        chokepoint
                    )
                    if success:
                        results[building_type] = 1
                        break  # 한 번에 하나씩만
        
        return results
    
    # ==================== 3. 자원 적체 시 테크 건물 공격적 건설 ====================
    
    def has_resource_surplus(self) -> Tuple[bool, float, float]:
        """
        자원이 적체되었는지 확인 (3000+ 미네랄, 500+ 가스)
        
        Returns:
            (has_surplus, mineral_surplus, gas_surplus)
        """
        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)
        
        mineral_surplus = max(0, minerals - self.resource_surplus_threshold)
        gas_surplus = max(0, gas - self.gas_surplus_threshold)
        
        has_surplus = (minerals >= self.resource_surplus_threshold or 
                      gas >= self.gas_surplus_threshold)
        
        return has_surplus, mineral_surplus, gas_surplus
    
    async def build_tech_buildings_aggressively(self) -> Dict[UnitTypeId, bool]:
        """
        자원이 적체되었을 때 테크 건물을 공격적으로 건설
        
        Returns:
            {tech_type: success} 딕셔너리
        """
        has_surplus, mineral_surplus, gas_surplus = self.has_resource_surplus()
        
        if not has_surplus:
            return {}
        
        results = {}
        
        # 자원이 많이 적체되었을 때 건설할 테크 건물 우선순위
        tech_buildings = []
        
        # 가스가 많이 적체되었을 때: 고테크 건물 우선
        if gas_surplus > 200:
            # 가시지옥 굴 (Lurker Den)
            if not self.bot.structures(UnitTypeId.LURKERDENMP).exists:
                tech_buildings.append((UnitTypeId.LURKERDENMP, 100, 200, 1))
            
            # 울트라리스크 동굴
            if (self.bot.structures(UnitTypeId.HIVE).ready.exists and
                not self.bot.structures(UnitTypeId.ULTRALISKCAVERN).exists):
                tech_buildings.append((UnitTypeId.ULTRALISKCAVERN, 300, 200, 2))
        
        # 미네랄이 많이 적체되었을 때: 중간 테크 건물
        if mineral_surplus > 500:
            # 맹독충 둥지
            if (self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.exists and
                not self.bot.structures(UnitTypeId.BANELINGNEST).exists):
                tech_buildings.append((UnitTypeId.BANELINGNEST, 100, 50, 3))
        
        # 우선순위 순으로 정렬
        tech_buildings.sort(key=lambda x: x[3])
        
        # 건설 실행
        for tech_type, mineral_cost, gas_cost, priority in tech_buildings:
            if (self.bot.minerals >= mineral_cost and 
                self.bot.vespene >= gas_cost):
                
                try:
                    if self.bot.townhalls.exists:
                        main_base = self.bot.townhalls.first
                        result = await self.bot.build(
                            tech_type,
                            near=main_base.position.towards(
                                self.bot.game_info.map_center, 5
                            )
                        )
                        
                        if result:
                            results[tech_type] = True
                            print(f"[AGGRESSIVE TECH] Built {tech_type} "
                                  f"(surplus: M:{int(mineral_surplus)}+ G:{int(gas_surplus)}+)")
                            # 한 번에 하나씩만 건설
                            break
                except Exception as e:
                    if self.bot.iteration % 100 == 0:
                        print(f"[AGGRESSIVE TECH] Failed to build {tech_type}: {e}")
                    results[tech_type] = False
        
        return results
    
    async def handle_resource_surplus(self) -> Dict[str, int]:
        """
        자원 적체 시 종합 처리 (테크 건물 건설 + 유닛 변태)
        
        Returns:
            처리 결과 딕셔너리
        """
        has_surplus, mineral_surplus, gas_surplus = self.has_resource_surplus()
        
        if not has_surplus:
            return {}
        
        results = {
            "tech_buildings_built": 0,
            "lurkers_morphed": 0,
            "banelings_morphed": 0
        }
        
        # 1. 테크 건물 건설
        tech_results = await self.build_tech_buildings_aggressively()
        results["tech_buildings_built"] = sum(1 for v in tech_results.values() if v)
        
        # 2. 가시지옥 변태 (가스가 많이 적체되었을 때)
        if gas_surplus > 200:
            lurkers = await self.morph_lurkers(max_count=5)
            results["lurkers_morphed"] = lurkers
        
        # 3. 맹독충 변태 (미네랄이 많이 적체되었을 때)
        if mineral_surplus > 500:
            banelings = await self.morph_banelings(max_count=10)
            results["banelings_morphed"] = banelings
        
        return results
