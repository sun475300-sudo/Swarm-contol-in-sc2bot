# -*- coding: utf-8 -*-
"""
Combat Manager - 전투 관리자

타겟팅 시스템과 마이크로 전투를 통합한 전투 관리자
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.units import Units
    from sc2.unit import Unit
    from sc2.position import Point2
else:
    try:
        from sc2.units import Units
        from sc2.unit import Unit
        from sc2.position import Point2
    except ImportError:
        Units = object
        Unit = object
        Point2 = tuple


class CombatManager:
    """
    전투 관리자
    
    기능:
    1. 타겟팅 시스템과 연동
    2. 마이크로 전투 (키팅, 스플릿, 집중 사격)
    3. Boids 알고리즘 기반 군집 제어
    4. 진형 형성 (Concave, 길목 차단)
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.targeting = None
        self.micro_combat = None
        self.boids = None
        
        # 매니저 초기화
        self._initialize_managers()
    
    def _initialize_managers(self):
        """매니저들 초기화"""
        try:
            from combat.targeting import Targeting
            self.targeting = Targeting(self.bot)
        except ImportError:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 500 == 0:
                print("[WARNING] Targeting system not available")
        
        try:
            from combat.micro_combat import MicroCombat
            self.micro_combat = MicroCombat(self.bot)
        except ImportError:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 500 == 0:
                print("[WARNING] Micro combat not available")
        
        try:
            from combat.boids_swarm_control import BoidsSwarmController
            self.boids = BoidsSwarmController()
        except ImportError:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 500 == 0:
                print("[WARNING] Boids controller not available")
    
    async def on_step(self, iteration: int):
        """
        매 프레임 호출되는 전투 로직
        
        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            # 아군 유닛과 적 유닛 확인
            if not hasattr(self.bot, 'units') or not hasattr(self.bot, 'enemy_units'):
                return
            
            army_units = self._filter_army_units(getattr(self.bot, "units", []))

            enemy_units = getattr(self.bot, "enemy_units", [])

            if not self._has_units(army_units) or not self._has_units(enemy_units):
                return
            
            # 전투 로직 실행
            await self._execute_combat(army_units, enemy_units)
            
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Combat manager error: {e}")
    
    async def _execute_combat(self, units: Units, enemy_units):
        """
        전투 실행
        
        CRITICAL IMPROVEMENT: 진형 형성 로직 통합
        
        Args:
            units: 아군 유닛들
            enemy_units: 적 유닛들
        """
        try:
            # 0. 진형 형성 (원거리 유닛만)
            await self._form_formation(units, enemy_units)
            
            # 1. 오버킬 분산 타겟 할당
            if self.targeting and self.micro_combat:
                assignments = self.targeting.assign_targets(units, enemy_units)
                if assignments:
                    await self.micro_combat.attack_assigned_targets(units, assignments)
                    return

            # 2. 집중 사격 (타겟팅 시스템 사용)
            if self.targeting:
                focus_target = None
                if hasattr(self.targeting, "get_focus_fire_target"):
                    focus_target = self.targeting.get_focus_fire_target(units, enemy_units)
                elif hasattr(self.targeting, "select_focus_fire_target"):
                    focus_target = self.targeting.select_focus_fire_target(units, enemy_units)
                if focus_target:
                    if self.micro_combat:
                        await self.micro_combat.focus_fire(units, focus_target)
                    return
            
            # 3. 타겟팅 시스템 없으면 기본 공격
            if self.micro_combat:
                await self.micro_combat.kiting(units, enemy_units)
            else:
                # 마이크로 전투도 없으면 기본 공격
                await self._basic_attack(units, enemy_units)
        
        except Exception as e:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 200 == 0:
                print(f"[WARNING] Combat execution error: {e}")
            # 에러 발생 시 기본 공격
            await self._basic_attack(units, enemy_units)
    
    async def _form_formation(self, units: Units, enemy_units):
        """
        진형 형성
        
        CRITICAL IMPROVEMENT: Concave 진형 및 길목 차단 로직
        
        Args:
            units: 아군 유닛들
            enemy_units: 적 유닛들
        """
        try:
            from combat.formation_manager import FormationManager
            
            formation_manager = FormationManager(self.bot)
            
            if not self._has_units(enemy_units) or not self._has_units(units):
                return
            
            # 적 중심 계산
            enemy_center = self._get_enemy_center(enemy_units)
            if enemy_center is None:
                return
            
            # 원거리 유닛만 진형 형성 (히드라리스크, 로ach, Ravager)
            ranged_units = self._filter_units_by_type(
                units, ["HYDRALISK", "ROACH", "RAVAGER"]
            )
            
            if self._has_units(ranged_units) and self._units_amount(ranged_units) >= 3:
                # Concave 진형 형성
                formation_positions = formation_manager.form_concave(
                    ranged_units, enemy_center, formation_radius=8.0
                )
                
                # 유닛들을 진형 위치로 이동
                for unit, target_pos in formation_positions[:10]:  # 최대 10개만
                    try:
                        await self.bot.do(unit.move(target_pos))
                    except Exception:
                        pass
            
            # 길목 회피 확인
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                our_base = self.bot.townhalls.first.position
                chokepoint = formation_manager.find_chokepoint(enemy_units, our_base)
                
                if chokepoint and formation_manager.should_avoid_chokepoint(units, chokepoint, enemy_units):
                    # 넓은 곳으로 후퇴
                    retreat_pos = formation_manager.get_retreat_position(units, enemy_units, our_base)
                    if retreat_pos:
                        for unit in units[:10]:  # 최대 10개만
                            try:
                                await self.bot.do(unit.move(retreat_pos))
                            except Exception:
                                pass
        
        except Exception as e:
            if hasattr(self.bot, 'iteration') and self.bot.iteration % 200 == 0:
                print(f"[WARNING] Formation error: {e}")
    
    async def _basic_attack(self, units: Units, enemy_units):
        """
        기본 공격 (에러 발생 시)
        
        Args:
            units: 아군 유닛들
            enemy_units: 적 유닛들
        """
        try:
            for unit in list(units)[:20]:  # 최대 20개만 처리
                closest_enemy = self._closest_enemy(enemy_units, unit)
                if closest_enemy:
                    await self.bot.do(unit.attack(closest_enemy))
        except Exception:
            pass

    def _filter_army_units(self, units):
        return self._filter_units_by_type(
            units, ["ZERGLING", "ROACH", "HYDRALISK", "MUTALISK"]
        )

    def _filter_units_by_type(self, units, names):
        if hasattr(units, "filter"):
            return units.filter(lambda u: u.type_id.name in names)
        return [u for u in units if getattr(u.type_id, "name", "") in names]

    @staticmethod
    def _has_units(units) -> bool:
        if hasattr(units, "exists"):
            return bool(units.exists)
        return bool(units)

    @staticmethod
    def _units_amount(units) -> int:
        if hasattr(units, "amount"):
            return int(units.amount)
        return len(units)

    def _get_enemy_center(self, enemy_units):
        if not Point2:
            return None
        items = list(enemy_units)
        if not items:
            return None
        count = len(items)
        x_sum = sum(u.position.x for u in items)
        y_sum = sum(u.position.y for u in items)
        return Point2((x_sum / count, y_sum / count))

    def _closest_enemy(self, enemy_units, unit):
        if hasattr(enemy_units, "closest_to"):
            try:
                return enemy_units.closest_to(unit.position)
            except Exception:
                return None
        closest = None
        closest_dist = None
        for enemy in enemy_units:
            try:
                dist = unit.distance_to(enemy)
            except Exception:
                continue
            if closest_dist is None or dist < closest_dist:
                closest = enemy
                closest_dist = dist
        return closest
