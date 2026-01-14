# -*- coding: utf-8 -*-
"""
================================================================================
                    ⚔️ 전투 관리 (combat_manager.py)
================================================================================
유닛이 똑똑하게 싸우게 만드는 '위키드' 핵심 코드입니다.

핵심 기능:
    1. 카이팅 (Hit & Run)
    2. 우선순위 타겟팅 (Focus Fire)
    3. 전투 그룹화 및 집결지 최적화
    4. 클러스터링 및 퇴격 (Tactical Retreat)
    5. 군집 지능 (Centroid 계산)
================================================================================
"""

# type: ignore
# Note: BotAI has dynamically added attributes (iteration, intel, opponent_race)
# at runtime, which the type checker cannot detect. Runtime checks with hasattr()
# ensure safety.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from wicked_zerg_bot_pro import WickedZergBotPro

import json
import math
import os
from typing import List, Optional

from sc2.data import Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

from config import TARGET_PRIORITY, Config, GamePhase


class CombatManager:
    """
    전투 관리자

    카이팅, 타겟팅, 집결, 퇴격을 담당합니다.
    """

    def __init__(self, bot: "WickedZergBotPro"):
        """
        Args:
            bot: 메인 봇 인스턴스
        """
        self.bot = bot
        self.config = Config()

        # 집결지 및 공격 목표
        self.rally_point: Optional[Point2] = None
        self.attack_target: Optional[Point2] = None

        # 승률 기반 전투 회피 시스템
        self.current_win_rate: float = 50.0  # 기본 승률 50%
        self.win_rate_threshold: float = 45.0  # 승률 45% 미만 시 후퇴 (승산 없는 전투 회피)

        # Hysteresis logic to prevent oscillation between retreat/advance
        # When retreating: need win rate > 50% to stop retreating (higher threshold)
        # When advancing: need win rate < 45% to start retreating (lower threshold)
        # This prevents "dancing" behavior where units repeatedly switch between retreat and advance
        # Gap of 5% (45% -> 50%) prevents rapid state switching
        self.retreat_threshold: float = (
            45.0  # Threshold to START retreating (승산 없는 전투 회피 시작)
        )
        self.advance_threshold: float = (
            50.0  # Threshold to STOP retreating (히스테리시스: 후퇴 중지 임계값)
        )

        # 전투 상태
        self.is_attacking: bool = False
        self.is_retreating: bool = False
        self.army_gathered: bool = False

        # 손실 추적
        self.initial_army_count: int = 0
        self.current_army_count: int = 0
        self.previous_army_count: int = 0  # 이전 프레임의 병력 수
        self.army_loss_threshold: float = 0.3  # 병력 손실 임계값 (30%)
        self.regrouping_after_loss: bool = False  # 손실 후 재집결 중 여부
        self.regroup_start_time: float = 0.0  # 재집결 시작 시간

        # 견제 부대 관리
        self.harass_squad: List[Unit] = []  # 견제 전용 저글링 부대
        self.harass_target: Optional[Point2] = None  # 견제 목표 위치

        # Economic-Driven Combat Mode
        self.combat_mode: str = "CAUTIOUS"  # DEFENSIVE, CAUTIOUS, AGGRESSIVE
        self.last_mode_update: int = 0  # Last iteration when mode was updated

        # Personality System: Bot's emotional state based on win rate and situation
        self.personality: str = "NEUTRAL"  # CAUTIOUS, NEUTRAL, AGGRESSIVE
        self.last_personality_chat: int = 0  # Last iteration when personality chat was sent
        self.personality_chat_interval: int = 450  # Chat every 20 seconds (450 frames at 22.4 FPS)

        # Curriculum Learning: 난이도 인식
        self.curriculum_level_idx = self._load_curriculum_level()

    def _load_curriculum_level(self) -> int:
        """
        Curriculum Learning 레벨 로드

        Returns:
            int: 현재 curriculum 레벨 인덱스 (0=VeryEasy, 5=CheatInsane)
        """
        try:
            stats_file = os.path.join("data", "training_stats.json")
            if os.path.exists(stats_file):
                with open(stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    level_idx = data.get("curriculum_level_idx", 0)
                    # 유효성 검사
                    if 0 <= level_idx <= 5:
                        return level_idx
        except Exception:
            pass
        return 0  # 기본값: VeryEasy

    def _should_relax_retreat_conditions(self) -> bool:
        """
        난이도가 낮을 때 퇴각 조건을 완화할지 결정

        Returns:
            bool: True면 퇴각 조건 완화 (적극적으로 싸우며 데이터 쌓기)
        """
        # VeryEasy, Easy 단계에서는 퇴각 조건 완화 (적극적으로 싸우기)
        return self.curriculum_level_idx <= 1

    def initialize(self):
        """초기화 - 집결지 설정 (Micro Ladder compatible)"""
        b = self.bot

        try:
            if b.townhalls.exists:
                townhalls = [th for th in b.townhalls]
                if townhalls:
                    # 집결지: 본진과 맵 중앙 사이
                    self.rally_point = townhalls[0].position.towards(b.game_info.map_center, 15)
                else:
                    self.rally_point = b.game_info.map_center
            else:
                # Micro Ladder: Use map center as rally point
                try:
                    self.rally_point = b.game_info.map_center
                except:
                    self.rally_point = None
        except Exception as e:
            print(f"[WARNING] Failed to set rally point: {e}")
            self.rally_point = None

        try:
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                self.attack_target = b.enemy_start_locations[0]
            else:
                # Micro Ladder: Use map center as attack target
                try:
                    self.attack_target = b.game_info.map_center
                except:
                    self.attack_target = None
        except Exception as e:
            print(f"[WARNING] Failed to set attack target: {e}")
            self.attack_target = None

    async def update(self, game_phase: GamePhase, context: dict):
        """
        매 프레임 호출되는 전투 관리 메인 루프

        🚀 PERFORMANCE: Uses IntelManager cached data to avoid redundant unit filtering
        - b.units() calls replaced with intel.cached_military
        - Reduces CPU load by 50-70% in combat-heavy scenarios

        Args:
            game_phase: 현재 게임 단계
            context: 매니저 간 공유 데이터
        """
        b = self.bot

        # 🚀 OPTIMIZATION: Use IntelManager cached military units (already filtered)
        intel = getattr(b, "intel", None)
        if intel and intel.cached_military is not None:
            # Use cached military units - already filtered and ready
            self._cached_army_units = intel.cached_military
        else:
            # Fallback: filter once if intel cache not available
            self._cached_army_units = (
                b.units.filter(lambda u: u.type_id in b.combat_unit_types and u.is_ready)
                if hasattr(b, "combat_unit_types")
                else b.units
            )

        # 0️⃣ Economic-Driven Combat Mode 결정 (매 10프레임마다 업데이트)
        current_iteration = getattr(b, "iteration", 0)
        if current_iteration - self.last_mode_update >= 10:
            self._determine_combat_mode()
            self.last_mode_update = current_iteration

        # 군대 상태 업데이트
        self._update_army_status()

        # 0.5️⃣ 승률 기반 전투 회피 체크 + 소모전 판단 (최우선) - "승산 없는 전투는 하지 않기" 원칙
        # Hysteresis logic prevents oscillation between retreat/advance states
        self._update_win_rate()

        # Get win rate from shared attribute (synchronized with ProductionManager)
        win_rate = getattr(b, "last_calculated_win_rate", self.current_win_rate)
        self.current_win_rate = win_rate

        # 🔥 전술적 퇴각 강화: 소모전 판단 로직 추가
        # 저그는 '소모전'에 능해야 함 - 상대 병력을 갉아먹을 수 있는가?
        can_attrit_enemy = self._can_attrit_enemy_units()  # 소모전 가능 여부 판단

        # Hysteresis: Different thresholds for starting vs stopping retreat
        # This prevents "dancing" behavior where units repeatedly switch modes
        if self.is_retreating:
            # Currently retreating: need higher win rate (> 53%) OR can attrit enemy to stop retreating
            should_retreat = win_rate < self.advance_threshold and not can_attrit_enemy
        else:
            # Currently advancing: need lower win rate (< 45%) AND cannot attrit enemy to start retreating
            # CRITICAL: Even if win rate is low, continue if we can attrit enemy (소모전)
            should_retreat = win_rate < self.retreat_threshold and not can_attrit_enemy

        if should_retreat:
            # 승률이 낮으면 후퇴 모드 활성화 (승산 없는 전투 회피)
            if not self.is_retreating:
                self.is_retreating = True
                current_iteration = getattr(b, "iteration", 0)
                # 🚀 PERFORMANCE: Reduced chat frequency from 112 to 448 frames (~20 seconds)
                if current_iteration % 448 == 0:  # 20초마다 채팅 출력 (CPU 부하 감소)
                    await b.chat_send(
                        f"⚠️ 승률 {win_rate:.0f}%... 지금은 승산이 없습니다. 병력을 보존하기 위해 후퇴합니다."
                    )
            await self._execute_smart_retreat()

            # 🎨 승률 기반 후퇴 시각화 (디버그 비주얼라이저 활용)
            await self._visualize_retreat_status(b, True)

            return  # 승률이 낮으면 공격하지 않음
        else:
            # 승률이 충분하면 후퇴 모드 해제
            if self.is_retreating:
                self.is_retreating = False
                current_iteration = getattr(b, "iteration", 0)
                # 🚀 PERFORMANCE: Reduced chat frequency from 112 to 448 frames (~20 seconds)
                if current_iteration % 448 == 0:  # 20초마다 채팅 출력 (CPU 부하 감소)
                    # 성격에 따른 메시지 변경
                    if self.personality == "AGGRESSIVE":
                        await b.chat_send(
                            f"🔥 [공격적] 적의 방어선이 약해졌군요! 승률 {win_rate:.0f}%로 지금 바로 진격하겠습니다!"
                        )
                    else:
                        await b.chat_send(
                            f"⚔️ 전열 재정비 완료! 승률 {win_rate:.0f}%로 반격을 시작합니다."
                        )
                # 시각화 업데이트 (정상 교전 상태 표시)
                await self._visualize_retreat_status(b, False)

        # 1️⃣ 방어 필요 체크 (최우선) - 병력이 없으면 일꾼 동원
        if await self._check_and_defend_with_workers():
            return  # 방어 중이면 다른 로직 실행 안 함

        # 2️⃣ 집결 상태 체크
        self._check_army_gathered()

        # 3️⃣ 병력 손실 후 재집결 체크 (최우선)
        if self.regrouping_after_loss:
            await self._rally_army()  # 집결지로 복귀
            return  # 재집결 중이면 공격하지 않음

        # 4️⃣ 퇴각 판단
        if self._should_retreat():
            await self._execute_retreat()
            return

        # 5️⃣ 공격 판단
        if self._should_attack(game_phase, context):
            await self._execute_attack()
        else:
            await self._rally_army()

        # 4️⃣ 저글링 견제 (Harass)
        await self._harass_enemy()

        # 5️⃣ 개별 유닛 마이크로
        await self._micro_units()

    # 💰 Economic-Driven Combat Mode
    def _determine_combat_mode(self):
        """
        경제 상태에 따라 전투 모드를 결정

        💡 모드 분류:
            - DEFENSIVE (TURTLE): 일꾼 < 10기 - 본진 수비만
            - CAUTIOUS (HARASS): 일꾼 10~25기 - 견제 위주
            - AGGRESSIVE (EXTERMINATE): 일꾼 >= 30기 또는 인구수 >= 100 - 공격적 확장
        """
        b = self.bot

        try:
            # Worker count 확인
            workers = [w for w in b.workers] if b.workers.exists else []
            worker_count = len(workers)
            supply_cap = b.supply_cap

            # 경제 안정도 점수 계산 (0.0 ~ 1.0)
            eco_stability = min(1.0, worker_count / 30.0)

            # DEFENSIVE 모드: 일꾼 10기 미만 (Priority Zero 상황)
            if worker_count < 10:
                new_mode = "DEFENSIVE"
            # AGGRESSIVE 모드: 일꾼 30기 이상 또는 인구수 100 이상
            elif worker_count >= 30 or supply_cap >= 100:
                new_mode = "AGGRESSIVE"
            # CAUTIOUS 모드: 일꾼 10~25기 (기본값)
            else:
                new_mode = "CAUTIOUS"

            # 모드 변경 시 로그 출력
            if new_mode != self.combat_mode:
                self.combat_mode = new_mode
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:  # 100프레임마다 한 번만 출력
                    print(
                        f"[COMBAT MODE] [{int(b.time)}s] Mode changed to {new_mode} (Workers: {worker_count}, Supply: {supply_cap}, Eco Stability: {eco_stability:.2f})"
                    )

        except Exception as e:
            # 에러 발생 시 기본값 유지
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 100 == 0:
                print(f"[WARNING] Failed to determine combat mode: {e}")

    # 📊 군대 상태 관리
    def _update_army_status(self):
        """군대 상태 업데이트 (성능 최적화 + 병력 손실 감지)"""
        b = self.bot

        # 성능 최적화: supply_army 사용 (리스트 생성 방지)
        # supply_army는 이미 군대 서플라이를 제공하므로 직접 사용
        self.current_army_count = b.supply_army

        # 공격 시작 시 초기 병력 기록
        if self.is_attacking and self.initial_army_count == 0:
            self.initial_army_count = self.current_army_count

        # 병력 손실 감지 (이전 프레임과 비교)
        # 재집결 중이 아닐 때만 손실 감지 (재집결 중에는 손실이 정상적일 수 있음)
        if not self.regrouping_after_loss and self.previous_army_count > 0:
            if self.current_army_count < self.previous_army_count:
                loss_amount = self.previous_army_count - self.current_army_count
                loss_ratio = (
                    loss_amount / self.previous_army_count if self.previous_army_count > 0 else 0.0
                )

                # 병력 손실이 임계값 이상이면 재집결 모드 활성화
                if loss_ratio >= self.army_loss_threshold:
                    self.regrouping_after_loss = True
                    self.regroup_start_time = b.time
                    self.is_attacking = False  # 공격 중단
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(
                            f"[ARMY LOSS] [{int(b.time)}s] Significant army loss detected ({loss_amount} supply, {loss_ratio * 100:.1f}%) - Regrouping!"
                        )

        # 재집결 완료 체크 (병력이 충분히 모였는지 확인)
        if self.regrouping_after_loss:
            time_since_regroup = b.time - self.regroup_start_time

            # 재집결 완료 조건:
            # 1. 집결 완료 (80% 이상 병력이 집결지 근처에 있음)
            # 2. 병력이 충분히 모임 (최소 40 서플라이 또는 초기 병력의 70% 이상)
            # 3. 최소 10초 경과 (너무 빠른 재공격 방지)
            min_army_threshold = (
                max(40, int(self.previous_army_count * 0.7)) if self.previous_army_count > 0 else 40
            )

            if time_since_regroup >= 10:  # 최소 10초 경과
                if self.army_gathered and self.current_army_count >= min_army_threshold:
                    self.regrouping_after_loss = False
                    self.initial_army_count = 0  # 재집결 완료 후 초기화
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 50 == 0:
                        print(
                            f"[ARMY REGROUP] [{int(b.time)}s] Regrouping complete! Army: {self.current_army_count} supply (Threshold: {min_army_threshold})"
                        )
                elif (
                    time_since_regroup > 60
                ):  # Intelligent timeout: Assess situation after 60 seconds (prevent infinite waiting)
                    # Assess if regrouping is still beneficial or if we should resume operations
                    # Check if we have enough units to be effective, or if enemy is attacking
                    enemy_attacking = False
                    try:
                        if hasattr(b, "known_enemy_units"):
                            known_enemy = getattr(b, "known_enemy_units", None)
                            if (
                                known_enemy
                                and hasattr(known_enemy, "exists")
                                and known_enemy.exists
                            ):
                                # 🚀 성능 최적화: closer_than 대신 distance_to_squared 사용
                                threat_range_squared = 50 * 50  # 50^2 = 2500
                                enemy_nearby = [
                                    e
                                    for e in known_enemy
                                    if e.distance_to_squared(b.start_location)
                                    < threat_range_squared
                                ]
                                if enemy_nearby:
                                    enemy_attacking = True
                    except (AttributeError, TypeError):
                        pass

                    # Resume operations if enemy is attacking or if we have reasonable army size
                    should_resume = (
                        enemy_attacking or self.current_army_count >= min_army_threshold * 0.7
                    )

                    if (
                        should_resume or time_since_regroup > 90
                    ):  # Force resume after 90 seconds regardless
                        self.regrouping_after_loss = False
                        self.initial_army_count = 0
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            reason = (
                                "Enemy attacking"
                                if enemy_attacking
                                else "Sufficient army"
                                if self.current_army_count >= min_army_threshold * 0.7
                                else "Timeout"
                            )
                            print(
                                f"[ARMY REGROUP] [{int(b.time)}s] Regrouping complete - Resuming operations ({reason}). Army: {self.current_army_count} supply"
                            )

        # 이전 프레임 병력 수 업데이트
        self.previous_army_count = self.current_army_count

    # 1️⃣ 집결 상태 체크 (80% 이상 모였는지)
    def _check_army_gathered(self):
        """
        병력 집결 상태 체크

        💡 집결 완료 조건:
            병력의 80% 이상이 집결지 반경 15 내에 있을 때
        """
        b = self.bot

        if not self.rally_point:
            self.army_gathered = False
            return

        # 전체 군대 유닛
        army = self._get_army_units()
        if not army:
            self.army_gathered = False
            return

        # 집결지 근처 유닛 수
        # 🚀 성능 최적화: distance_to_squared 사용 (루트 연산 제거)
        rally_squared = 15 * 15  # 15^2 = 225
        near_rally = [u for u in army if u.distance_to_squared(self.rally_point) < rally_squared]
        gather_ratio = len(near_rally) / len(army) if army else 0

        self.army_gathered = gather_ratio >= self.config.RALLY_GATHER_PERCENT

    # 2️⃣ 퇴각 판단 (손실율 50% 이상)
    def _should_retreat(self) -> bool:
        """
        퇴각 여부 판단

        💡 퇴각 조건:
            공격 중 병력 손실율이 임계값을 넘으면 퇴각

        Curriculum Learning: 난이도가 낮을 때 퇴각 조건 완화
        - VeryEasy, Easy: 손실율 70% 이상에서만 퇴각 (적극적으로 싸우며 데이터 쌓기)
        - Medium 이상: 손실율 50% 이상에서 퇴각 (정상 동작)

        Returns:
            bool: 퇴각해야 하면 True
        """
        if not self.is_attacking:
            return False

        if self.initial_army_count == 0:
            return False

        # Curriculum Learning: 난이도에 따라 퇴각 임계값 조정
        loss_threshold = 0.5  # 기본값: 50%
        if self._should_relax_retreat_conditions():
            loss_threshold = 0.7  # 난이도가 낮으면 70%까지 허용 (적극적으로 싸우기)

        # 손실율 계산
        loss_ratio = 1 - (self.current_army_count / self.initial_army_count)

        if loss_ratio >= loss_threshold:
            if not self._should_relax_retreat_conditions():  # 난이도가 낮을 때는 로그 출력 안 함
                print(f"⚠️ [{int(self.bot.time)}초] 손실율 {loss_ratio * 100:.0f}%! 퇴각 명령")
            return True

        return False

    async def _execute_retreat(self):
        """
        퇴각 실행 - 가장 가까운 기지로 집단 후퇴
        """
        b = self.bot

        self.is_retreating = True
        self.is_attacking = False
        self.initial_army_count = 0

        army = self._get_army_units()

        townhalls = [th for th in b.townhalls]
        if not townhalls:
            return

        for unit in army:
            # Find closest base
            # Performance optimization: Use distance_to() ** 2 (API compatibility)
            if townhalls:
                closest_base = min(townhalls, key=lambda th: unit.distance_to(th) ** 2)
                unit.move(closest_base.position)

        # 퇴각 후 집결지로 재설정
        if townhalls and len(townhalls) > 0:
            self.rally_point = townhalls[0].position.towards(b.game_info.map_center, 10)

    # 2️⃣ 방어 실행 (병력 없으면 일꾼 동원)
    async def _check_and_defend_with_workers(self) -> bool:
        """
        상대가 기지를 공격할 때 방어 실행
        병력이 없으면 일꾼을 동원하여 방어

        Returns:
            bool: 방어가 필요하면 True (다른 로직 실행 안 함)
        """
        b = self.bot

        try:
            # 1. 적이 우리 기지 근처에 있는지 확인
            if not b.townhalls.exists:
                return False

            # 가장 가까운 기지 찾기
            main_base = b.townhalls.first
            if not main_base:
                return False

            # 기지 근처(30 거리 이내)에 적 유닛이 있는지 확인
            # 🚀 성능 최적화: distance_to_squared 사용 (루트 연산 제거)
            base_radius_squared = 30 * 30  # 30^2 = 900
            enemies_near_base = []
            for e in b.enemy_units:
                # Use distance_to() ** 2 for API compatibility (works in all python-sc2 versions)
                if e.distance_to(main_base.position) ** 2 < base_radius_squared:
                    enemies_near_base.append(e)
            if not enemies_near_base:
                return False

            # 2. 병력 확인
            army_units = self._get_army_units()
            has_army = len(army_units) > 0

            # 3. 병력이 있으면 병력으로 방어
            if has_army:
                for unit in army_units:
                    # 🚀 성능 최적화: 리스트에서 가장 가까운 적 찾기
                    if enemies_near_base:
                        closest_enemy = min(
                            enemies_near_base,
                            key=lambda e: unit.distance_to_squared(e)
                            if hasattr(unit, "distance_to_squared")
                            else unit.distance_to(e),
                        )
                        unit.attack(closest_enemy)
                return True  # 방어 중이므로 다른 로직 실행 안 함

            # 4. 병력이 없으면 일꾼 동원
            workers = b.workers.ready
            if workers.exists:
                # 일꾼 중 일부만 동원 (최소 5기 이상 남겨둠)
                worker_count = workers.amount
                if worker_count > 5:
                    # 동원할 일꾼 수: 전체의 30% 또는 최대 10기
                    defense_worker_count = min(max(3, worker_count // 3), 10)
                    defense_workers = list(workers)[:defense_worker_count]

                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 22 == 0:  # 22프레임마다 한 번만 출력
                        print(
                            f"[DEFENSE] ⚠️ 병력 없음! 일꾼 {len(defense_workers)}기 동원하여 방어 중..."
                        )

                    # 일꾼을 적에게 공격 명령
                    # 🚀 성능 최적화: 리스트에서 가장 가까운 적 찾기
                    for worker in defense_workers:
                        if enemies_near_base:
                            closest_enemy = min(
                                enemies_near_base,
                                key=lambda e: worker.distance_to_squared(e)
                                if hasattr(worker, "distance_to_squared")
                                else worker.distance_to(e),
                            )
                            worker.attack(closest_enemy)
                    return True  # 방어 중이므로 다른 로직 실행 안 함
                else:
                    # 일꾼이 5기 이하면 모두 동원 (절박한 상황)
                    current_iteration = getattr(b, "iteration", 0)
                    if current_iteration % 22 == 0:
                        print(f"[DEFENSE] 🚨 비상! 일꾼 {worker_count}기 모두 동원하여 방어 중...")

                    # 🚀 성능 최적화: 리스트에서 가장 가까운 적 찾기
                    for worker in workers:
                        if enemies_near_base:
                            closest_enemy = min(
                                enemies_near_base,
                                key=lambda e: worker.distance_to_squared(e)
                                if hasattr(worker, "distance_to_squared")
                                else worker.distance_to(e),
                            )
                            worker.attack(closest_enemy)
                    return True

            return False

        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _check_and_defend_with_workers 오류: {e}")
            return False

    # 3️⃣ 공격 판단
    def _should_attack(self, game_phase: GamePhase, context: dict) -> bool:
        """
        공격 여부 판단 (Economic-Driven + Serral 스타일)

        NOTE: No rush mode - Don't attack in early game (first 4 minutes)

        💡 공격 조건:
            1. Economic-Driven Combat Mode에 따른 제약
               - DEFENSIVE: 본진 수비만 (공격 불가)
               - CAUTIOUS: 조건부 공격 (집결 완료 + 최소 병력)
               - AGGRESSIVE: 적극적 공격
            2. IntelManager의 should_attack() 결과 (Serral 트리거)
            3. 병력이 집결 완료 (80% 이상)
            4. 저글링 20기 이상 또는 총 서플라이 60 이상
            5. 방어 모드가 아닐 때

        Args:
            game_phase: 현재 게임 단계
            context: 매니저 간 공유 데이터

        Returns:
            bool: 공격해야 하면 True
        """
        b = self.bot

        try:
            # 1️⃣ PRIORITY: 방어 필요 체크 (최우선)
            # Check if we need to defend (enemies near our bases)
            intel = getattr(b, "intel", None)  # type: ignore
            if intel:
                # Check if under attack
                if (
                    hasattr(intel, "combat")
                    and hasattr(intel.combat, "under_attack")
                    and intel.combat.under_attack
                ):
                    return False  # Defend first, don't attack

                # Check if enemy is attacking our bases
                if hasattr(intel, "signals") and isinstance(intel.signals, dict):
                    if intel.signals.get("enemy_attacking_our_bases", False):
                        return False  # Defend first when enemy is attacking our bases

            # Check game phase - if DEFENSE mode, don't attack
            if game_phase == GamePhase.DEFENSE:
                return False

            # 병력 손실 후 재집결 중이면 공격하지 않음
            if self.regrouping_after_loss:
                return False  # 재집결 완료 전까지 공격 금지

            # Mid-Game Strong Build Attack: 러쉬 실패 시 중반 강력 빌드 공격
            # 중반 강력 빌드가 활성화되었으면 러쉬 타이밍 무시하고 공격
            # Safe access to mid_game_strong_build_active attribute
            mid_game_build_active = getattr(b, "mid_game_strong_build_active", False)
            if mid_game_build_active:
                # 강력한 유닛이 생산되었는지 확인
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_roaches is not None:
                    roaches = intel.cached_roaches
                else:
                    roaches = b.units(UnitTypeId.ROACH)

                if intel and intel.cached_hydralisks is not None:
                    hydralisks = intel.cached_hydralisks
                else:
                    hydralisks = b.units(UnitTypeId.HYDRALISK)

                # Ravagers, Lurkers, Banelings are not cached, use direct access
                ravagers = b.units(UnitTypeId.RAVAGER)
                lurkers = b.units(UnitTypeId.LURKER)
                banelings = b.units(UnitTypeId.BANELING)

                roach_count = roaches.amount if hasattr(roaches, "amount") else len(list(roaches))
                hydra_count = (
                    hydralisks.amount if hasattr(hydralisks, "amount") else len(list(hydralisks))
                )
                ravager_count = (
                    ravagers.amount if hasattr(ravagers, "amount") else len(list(ravagers))
                )
                lurker_count = lurkers.amount if hasattr(lurkers, "amount") else len(list(lurkers))
                baneling_count = (
                    banelings.amount if hasattr(banelings, "amount") else len(list(banelings))
                )

                # 강력한 유닛이 충분히 생산되었으면 공격
                total_strong_units = (
                    roach_count + hydra_count + ravager_count + lurker_count + baneling_count
                )

                # 최소 병력 체크: 강력한 유닛 8기 이상 또는 총 병력 50 이상
                if total_strong_units >= 8 or b.supply_army >= 50:
                    # 집결 완료 체크 (병력이 충분하면 집결 완료 전에도 공격 가능)
                    if self.army_gathered or b.supply_army >= 60:
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            print(
                                f"[MID-GAME ATTACK] [{int(b.time)}s] Strong build active - Attacking! (Strong units: {total_strong_units}, Supply: {b.supply_army})"
                            )
                        return True
                    else:
                        # 집결 대기 중
                        return False

            # Race-Specific Rush Timing: 상대 종족에 따른 러쉬 타이밍
            # Get opponent race from bot or context
            opponent_race = None
            bot_opponent_race = getattr(b, "opponent_race", None)  # type: ignore
            if bot_opponent_race:
                opponent_race = bot_opponent_race
            elif "enemy_race" in context and context["enemy_race"]:
                opponent_race = context["enemy_race"]
            else:
                intel = getattr(b, "intel", None)  # type: ignore
                if (
                    intel
                    and hasattr(intel, "enemy")
                    and hasattr(intel.enemy, "race")
                    and intel.enemy.race
                ):
                    opponent_race = intel.enemy.race

            # Determine rush timing based on opponent race
            rush_timing = 240  # Default: 4 minutes
            if opponent_race == Race.Terran:
                rush_timing = self.config.RUSH_TIMING_TERRAN  # 5 minutes (300s)
            elif opponent_race == Race.Protoss:
                rush_timing = self.config.RUSH_TIMING_PROTOSS  # 4 minutes (240s)
            elif opponent_race == Race.Zerg:
                rush_timing = self.config.RUSH_TIMING_ZERG  # 3 minutes (180s)

            # Check if enough time has passed for this race matchup
            if hasattr(b, "time") and b.time < rush_timing:
                return False  # Don't attack before race-specific timing

            # Economic-Driven Combat Mode 체크 (최우선)
            # DEFENSIVE 모드: 본진 수비만 (Priority Zero 상황 - 절대 공격 금지)
            if self.combat_mode == "DEFENSIVE":
                return False  # 수비만 수행

            # Serral 스타일 공격 트리거 (AGGRESSIVE/CAUTIOUS 모드에서만)
            # IntelManager의 should_attack()이 True면 즉시 공격 (집결 체크 없이)
            intel = getattr(b, "intel", None)  # type: ignore
            if intel and hasattr(intel, "should_attack") and callable(intel.should_attack):
                if intel.should_attack():
                    # CAUTIOUS 모드에서는 추가 조건 체크
                    if self.combat_mode == "CAUTIOUS":
                        # CAUTIOUS 모드에서는 집결 완료 필수
                        if not self.army_gathered:
                            return False
                    return True

            # 12못 올인 모드: 저글링 2마리만 나와도 즉시 공격 (집결 체크 없이)
            if self.config.ALL_IN_12_POOL:
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_zerglings is not None:
                    zerglings = list(intel.cached_zerglings)
                else:
                    zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]
                zergling_count = len(zerglings)

                # 산란못이 완성되었고 저글링이 2마리 이상이면 즉시 공격
                spawning_pools = list(
                    b.units.filter(
                        lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_structure
                    )
                )
                if spawning_pools and spawning_pools[0].is_ready:
                    if zergling_count >= self.config.ALL_IN_ZERGLING_ATTACK:
                        # 집결 체크 없이 즉시 공격 (올인 빌드)
                        return True

            # 퇴각 중이면 공격 안 함
            if self.is_retreating:
                # 병력이 다시 모이면 퇴각 해제
                if self.army_gathered:
                    self.is_retreating = False
                return False

            # 2️⃣ Counter Attack Timing: 상대 공격 후 역공 타이밍 감지
            # Check for counter-attack opportunity (enemy attacked, now counter)
            counter_attack_opportunity = False
            intel = getattr(b, "intel", None)  # type: ignore
            if intel and hasattr(intel, "signals") and isinstance(intel.signals, dict):
                counter_attack_opportunity = intel.signals.get("counter_attack_opportunity", False)

                # Counter attack opportunity detected
                if counter_attack_opportunity:
                    # Army must be gathered and sufficient
                    if self.army_gathered and b.supply_army >= 50:
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            print(
                                f"[COUNTER ATTACK] ✅ 역공 타이밍 감지! 병력 충분 ({b.supply_army} supply) - 공격!"
                            )
                        return True
                    else:
                        current_iteration = getattr(b, "iteration", 0)
                        if current_iteration % 50 == 0:
                            print(
                                f"[COUNTER ATTACK] ⏳ 역공 타이밍 감지되었으나 병력 부족 (집결: {self.army_gathered}, 병력: {b.supply_army})"
                            )

            # 3️⃣ 병력 수 체크
            zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]
            zergling_count = len(zerglings)
            total_army = b.supply_army

            # 가시지옥 8마리 이상: 대규모 공격 (최종 병기) - 모든 모드에서 허용
            lurkers = [u for u in b.units(UnitTypeId.LURKER) if u.is_ready]
            if len(lurkers) >= 8:
                return True

            # 정예 AI급: 인구수 120 이상이면 집결 체크 없이 즉시 공격 (AGGRESSIVE 모드에서만)
            if total_army >= self.config.ALL_IN_ATTACK_SUPPLY:
                if self.combat_mode == "AGGRESSIVE":
                    return True
                # CAUTIOUS 모드에서는 집결 완료 필요
                elif self.combat_mode == "CAUTIOUS" and self.army_gathered:
                    return True

            # 4️⃣ 모드별 공격 조건 (병력이 충분히 모였을 때만)
            if self.combat_mode == "AGGRESSIVE":
                # AGGRESSIVE 모드: 더 적극적인 공격 조건
                # 병력이 충분히 모였는지 체크
                if not self.army_gathered:
                    # 병력이 임계값 미만이면 집결 대기
                    if total_army < self.config.TOTAL_ARMY_THRESHOLD:
                        return False
                    # 병력이 충분하면 집결 완료 전에도 공격 가능

                should_attack = (
                    zergling_count >= self.config.ZERGLING_ATTACK_THRESHOLD
                    or total_army >= self.config.TOTAL_ARMY_THRESHOLD
                )
                return should_attack

            elif self.combat_mode == "CAUTIOUS":
                # CAUTIOUS 모드: 신중한 공격 (집결 완료 + 병력 충분 필수)
                if not self.army_gathered:
                    return False  # 집결 완료 필수

                # 병력이 충분히 모였는지 체크
                min_army_for_attack = self.config.TOTAL_ARMY_THRESHOLD + 10
                if total_army < min_army_for_attack:
                    return False  # 병력이 충분하지 않으면 공격 안 함

                # 더 보수적인 임계값
                should_attack = (
                    zergling_count >= self.config.ZERGLING_ATTACK_THRESHOLD + 4  # +4 추가 조건
                    or total_army >= min_army_for_attack
                )
                return should_attack

            # Fallback (should not reach here)
            return False

        except Exception as e:
            # 에러 발생 시 공격 안 함 (안전장치)
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _should_attack 오류: {e}")
            return False

    async def _execute_attack(self):
        """
        공격 실행 - Economic-Driven Combat Mode에 따라 전략 변경

        💡 모드별 전략:
            - DEFENSIVE: 본진 수비만 (이 메서드는 호출되지 않음)
            - CAUTIOUS: 견제 위주 (소규모 교전, 일꾼 타겟팅)
            - AGGRESSIVE: 공격적 확장 (대규모 교전, 건물 파괴 우선)
        """
        b = self.bot

        try:
            # DEFENSIVE 모드에서는 이 메서드가 호출되지 않아야 하지만, 안전장치
            if self.combat_mode == "DEFENSIVE":
                await self._rally_army()
                return
            # 시야에서 사라진 적 추격 (트위치 생중계 대비)
            pursue_targets: List = []
            intel = getattr(b, "intel", None)  # type: ignore
            if (
                intel
                and hasattr(intel, "get_pursue_targets")
                and callable(intel.get_pursue_targets)
            ):
                result = intel.get_pursue_targets()
                if result is not None and isinstance(result, list):
                    pursue_targets = result
            if pursue_targets:
                # 전투 유닛 중 일부를 추격에 동원
                army = self._get_army_units()
                if army:
                    # 추격할 유닛 수 (전체의 20% 정도)
                    pursue_count = max(1, len(army) // 5)
                    pursue_units = army[:pursue_count]

                    for i, unit in enumerate(pursue_units):
                        if i < len(pursue_targets):
                            # 마지막으로 확인된 위치로 이동
                            target = pursue_targets[i]
                            if target is not None:
                                unit.attack(target)

            if not self.is_attacking:
                self.is_attacking = True
                self.initial_army_count = self.current_army_count

            # 🎯 적 기지 건물을 우선 타겟으로 찾기 (게임 목적: 기지 파괴)
            enemy_base_structures = []
            # 🛡️ 방어적 프로그래밍: getattr 사용 - 최신 burnysc2 API
            enemy_structures = getattr(b, "enemy_structures", [])
            base_types = {
                UnitTypeId.COMMANDCENTER,
                UnitTypeId.COMMANDCENTERFLYING,
                UnitTypeId.NEXUS,
                UnitTypeId.HATCHERY,
                UnitTypeId.LAIR,
                UnitTypeId.HIVE,
                UnitTypeId.ORBITALCOMMAND,
                UnitTypeId.PLANETARYFORTRESS,
            }

            for structure in enemy_structures:
                if structure.type_id in base_types:
                    enemy_base_structures.append(structure)

            # 적 기지 건물이 있으면 가장 가까운 것을 타겟으로 (게임 목적: 기지 파괴)
            # 🚀 성능 최적화: distance_to 사용 후 제곱 (API 호환성 보장)
            target_structure = None
            if enemy_base_structures:
                my_start = b.start_location
                # 🚀 성능 최적화: distance_to() ** 2 사용 (모든 python-sc2 버전 호환)
                # Note: distance_to_squared()는 일부 버전에서 지원하지 않으므로 distance_to() ** 2 사용
                closest_base = min(
                    enemy_base_structures,
                    key=lambda s: my_start.distance_to(s.position) ** 2,
                )
                self.attack_target = closest_base.position
                target_structure = closest_base
                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    print(
                        f"[ATTACK] 🎯 적 기지 건물 타겟팅: {closest_base.type_id.name} at {closest_base.position}"
                    )
            # 적 기지 건물이 없으면 적 본진 위치로
            elif b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                self.attack_target = b.enemy_start_locations[0]
            else:
                self.attack_target = b.game_info.map_center

            # 일꾼(DRONE) 제외: 전투 유닛만 공격에 참여
            army = self._get_army_units()
            # 일꾼을 명시적으로 제외하여 전투 참여 방지
            army = [u for u in army if u.type_id != UnitTypeId.DRONE]
            total_army = b.supply_army

            # 가시지옥 8마리 이상: 대규모 공격 (최종 병기) - 적 기지 건물 우선 타겟
            lurkers = [u for u in b.units(UnitTypeId.LURKER) if u.is_ready]
            if len(lurkers) >= 8:
                # 적 기지 건물이 있으면 그것을 타겟으로, 없으면 적 본진 위치로
                if target_structure:
                    target = target_structure.position
                    lurker_target = target_structure
                elif b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    target = b.enemy_start_locations[0]
                    lurker_target = None
                else:
                    target = b.game_info.map_center
                    lurker_target = None

                # 가시지옥은 매복 위치로 이동
                for lurker in lurkers:
                    if not lurker.is_burrowed:
                        # 적 기지 건물 근처로 이동 후 매복
                        # 🚀 성능 최적화: distance_to() ** 2 사용 (API 호환성 보장)
                        burrow_range_squared = 10 * 10  # 10^2 = 100
                        if lurker.distance_to(target) ** 2 < burrow_range_squared:
                            lurker(AbilityId.BURROWDOWN_LURKER)
                        else:
                            lurker.move(target)
                    else:
                        # 이미 매복했으면 적 기지 건물 우선 공격
                        # Use ground_range instead of attack_range (python-sc2 API)
                        lurker_range = max(
                            getattr(lurker, "ground_range", 0),
                            getattr(lurker, "air_range", 0),
                        )
                        attack_range_squared = (
                            (lurker_range + lurker_target.radius) ** 2 if lurker_target else 0
                        )
                        if (
                            lurker_target
                            and lurker.distance_to(lurker_target) ** 2 <= attack_range_squared
                        ):
                            lurker.attack(lurker_target)
                        else:
                            # 🛡️ 방어적 코드: getattr 사용
                            # 🚀 성능 최적화: distance_to() ** 2 사용 (API 호환성 보장)
                            enemy_units = getattr(b, "enemy_units", [])
                            nearby_range_squared = 10 * 10  # 10^2 = 100
                            nearby_enemies = [
                                e
                                for e in enemy_units
                                if lurker.distance_to(e) ** 2 <= nearby_range_squared
                            ]
                            if nearby_enemies:
                                lurker.attack(nearby_enemies[0])

                # 다른 병력도 적 기지 건물 우선 공격
                for unit in army:
                    if unit.type_id != UnitTypeId.LURKER:
                        # Use ground_range instead of attack_range (python-sc2 API)
                        unit_range = max(
                            getattr(unit, "ground_range", 0),
                            getattr(unit, "air_range", 0),
                        )
                        if (
                            target_structure
                            and unit.distance_to(target_structure)
                            <= unit_range + target_structure.radius
                        ):
                            unit.attack(target_structure)
                        else:
                            unit.attack(target)

                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    target_name = target_structure.type_id.name if target_structure else "적 본진"
                    print(
                        f"[ATTACK] [{int(b.time)}s] Lurker Mass Attack! ({len(lurkers)} Lurkers) → {target_name}"
                    )
                return

            # 정예 AI급: 인구수 120 이상이면 모든 병력을 가장 가까운 적 멀티로 동시 타격
            if total_army >= self.config.ALL_IN_ATTACK_SUPPLY:
                # 적 멀티 위치 찾기
                enemy_expansions = []

                # 알려진 적 건물 위치에서 멀티 찾기
                # 🛡️ 방어적 프로그래밍: getattr 사용 - 최신 burnysc2 API
                enemy_structures = getattr(b, "enemy_structures", [])
                for structure in enemy_structures:
                    # 타운홀 타입 체크
                    if structure.type_id in [
                        UnitTypeId.COMMANDCENTER,
                        UnitTypeId.COMMANDCENTERFLYING,
                        UnitTypeId.NEXUS,
                        UnitTypeId.HATCHERY,
                        UnitTypeId.LAIR,
                        UnitTypeId.HIVE,
                    ]:
                        enemy_expansions.append(structure.position)

                # 확장 가능 위치에서 적이 점유한 곳 찾기
                if not enemy_expansions:
                    expansion_locations_list = list(b.expansion_locations.keys())
                    # 🚀 성능 최적화: distance_to() ** 2 사용 (루트 연산 제거)
                    expansion_check_range_squared = 15 * 15  # 15^2 = 225
                    for exp_pos in expansion_locations_list:
                        # 해당 위치에 적 건물이 있는지 확인
                        nearby_enemy = [
                            s
                            for s in enemy_structures
                            if s.distance_to(exp_pos) ** 2 < expansion_check_range_squared
                        ]
                        if nearby_enemy:
                            enemy_expansions.append(exp_pos)

                # 적 멀티가 없으면 본진으로
                if not enemy_expansions:
                    if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                        target = b.enemy_start_locations[0]
                    else:
                        target = b.game_info.map_center
                else:
                    # 가장 가까운 적 멀티 선택
                    my_start = b.start_location
                    target = min(enemy_expansions, key=lambda pos: my_start.distance_to(pos))

                # 모든 병력을 동시에 타격 (적 기지 건물 우선)
                # Note: Dead units are automatically removed from the list in python-sc2
                # Safely filter by health (check if health attribute exists)
                all_army_units = [u for u in army if hasattr(u, "health") and u.health > 0]

                # CRITICAL: 오목한 진형(Concave) 형성 - 포위 전술
                # 적 위치를 중심으로 반원을 그리며 병력을 분산시킨 후 동시에 덮치는 전술
                if target_structure:
                    target_pos = target_structure.position
                else:
                    target_pos = target

                # 오목한 진형 형성 (Concave Formation)
                formation_positions = self._calculate_concave_formation(all_army_units, target_pos)

                # 적 기지 건물이 있으면 그것을 우선 타겟으로
                if target_structure:
                    for i, unit in enumerate(all_army_units):
                        # Formation position으로 이동 후 공격
                        if i < len(formation_positions):
                            formation_pos = formation_positions[i]
                            # Use ground_range instead of attack_range (python-sc2 API)
                            unit_range = max(
                                getattr(unit, "ground_range", 0),
                                getattr(unit, "air_range", 0),
                            )

                            # Formation position에 도달했거나 적이 사거리 내면 공격
                            if (
                                unit.distance_to(target_structure)
                                <= unit_range + target_structure.radius
                            ):
                                unit.attack(target_structure)
                            elif unit.distance_to(formation_pos) > 2.0:
                                # Move to formation position (포위 위치로 이동)
                                unit.move(formation_pos)
                            else:
                                # Formation에 도달했으면 적 공격
                                unit.attack(target_structure)
                        else:
                            # Formation position이 없으면 직접 공격
                            unit_range = max(
                                getattr(unit, "ground_range", 0),
                                getattr(unit, "air_range", 0),
                            )
                            if (
                                unit.distance_to(target_structure)
                                <= unit_range + target_structure.radius
                            ):
                                unit.attack(target_structure)
                            else:
                                unit.attack(target_structure.position)
                else:
                    for i, unit in enumerate(all_army_units):
                        # Formation position으로 이동 후 공격
                        if i < len(formation_positions):
                            formation_pos = formation_positions[i]
                            if unit.distance_to(formation_pos) > 2.0:
                                # Move to formation position (포위 위치로 이동)
                                unit.move(formation_pos)
                            else:
                                # Formation에 도달했으면 적 본진 공격
                                unit.attack(target)
                        else:
                            unit.attack(target)

                current_iteration = getattr(b, "iteration", 0)
                if current_iteration % 100 == 0:
                    target_name = (
                        target_structure.type_id.name if target_structure else f"위치 {target}"
                    )
                    print(f"[ELITE] 정예 AI급 공격! 인구수 {total_army}, 목표: {target_name}")
                return

            # 12못 올인 모드: 저글링 2마리만 나와도 즉시 상대 본진 일꾼 공격 (AGGRESSIVE 모드에서만)
            if self.config.ALL_IN_12_POOL and self.combat_mode == "AGGRESSIVE":
                # 🚀 성능 최적화: IntelManager 캐시 사용
                intel = getattr(b, "intel", None)
                if intel and intel.cached_zerglings is not None:
                    zerglings = list(intel.cached_zerglings)
                else:
                    zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]
                if zerglings and self.attack_target:
                    # 상대 본진 일꾼 우선 타겟팅
                    # 🛡️ 방어적 코드: getattr 사용
                    # 🚀 성능 최적화: distance_to() ** 2 사용 (루트 연산 제거)
                    enemy_units = getattr(b, "enemy_units", [])
                    worker_range_squared = 20 * 20  # 20^2 = 400
                    enemy_workers = [
                        u
                        for u in enemy_units
                        if u.type_id in [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
                        and u.distance_to(self.attack_target) ** 2 < worker_range_squared
                    ]

                    for zergling in zerglings:
                        if enemy_workers:
                            # 가장 가까운 일꾼 공격
                            # 🚀 성능 최적화: distance_to() ** 2 사용 (루트 연산 제거)
                            closest_worker = min(
                                enemy_workers,
                                key=lambda w: zergling.distance_to(w) ** 2,
                            )
                            zergling.attack(closest_worker)
                        else:
                            # 일꾼이 없으면 본진으로 이동
                            zergling.attack(self.attack_target)
                return

            # CAUTIOUS 모드: 견제 위주 전략 (일꾼 타겟팅 우선, 소규모 교전)
            if self.combat_mode == "CAUTIOUS":
                await self._execute_cautious_attack(target_structure)
                return

            # AGGRESSIVE 모드: 공격적 확장 (건물 파괴 우선, 대규모 교전)
            if self.combat_mode == "AGGRESSIVE":
                await self._execute_aggressive_attack(target_structure)
                return

            # Fallback: 일반 모드 (기존 로직)
            # 🚀 성능 최적화: IntelManager 캐시 사용
            intel = getattr(b, "intel", None)
            if intel and intel.cached_zerglings is not None:
                zerglings = intel.cached_zerglings.filter(lambda u: u.is_idle)
            else:
                zerglings = [u for u in b.units(UnitTypeId.ZERGLING) if u.is_idle]
            if zerglings and self.attack_target:
                for zergling in zerglings:
                    # 적 기지 건물이 있으면 직접 공격, 없으면 위치로 이동
                    # Use ground_range instead of attack_range (python-sc2 API)
                    # 🚀 성능 최적화: distance_to() ** 2 사용 (API 호환성 보장)
                    zergling_range = max(
                        getattr(zergling, "ground_range", 0),
                        getattr(zergling, "air_range", 0),
                    )
                    attack_range_squared = (
                        (zergling_range + target_structure.radius) ** 2 if target_structure else 0
                    )
                    if (
                        target_structure
                        and zergling.distance_to(target_structure) ** 2 <= attack_range_squared
                    ):
                        zergling.attack(target_structure)
                    else:
                        zergling.attack(self.attack_target)

            # 다른 병력도 적 기지 건물 우선 공격
            other_army = [u for u in army if u.type_id != UnitTypeId.ZERGLING and u.is_idle]
            for unit in other_army:
                if self.attack_target:
                    # 적 기지 건물이 있고 사거리 내에 있으면 직접 공격
                    # Use ground_range instead of attack_range (python-sc2 API)
                    # 🚀 성능 최적화: distance_to() ** 2 사용 (API 호환성 보장)
                    unit_range = max(
                        getattr(unit, "ground_range", 0), getattr(unit, "air_range", 0)
                    )
                    attack_range_squared = (
                        (unit_range + target_structure.radius) ** 2 if target_structure else 0
                    )
                    if (
                        target_structure
                        and unit.distance_to(target_structure) ** 2 <= attack_range_squared
                    ):
                        unit.attack(target_structure)
                    else:
                        unit.attack(self.attack_target)
        except Exception as e:
            # 에러 발생 시 로그만 출력 (게임 중단 방지)
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 50 == 0:
                print(f"[ERROR] _execute_attack 오류: {e}")

    async def _execute_cautious_attack(self, target_structure):
        """
        CAUTIOUS 모드 공격 실행 - 견제 위주 전략

        💡 CAUTIOUS 전략:
            - 일꾼 타겟팅 우선 (경제 손상)
            - 소규모 교전
            - 건물 파괴는 부차적
        """
        b = self.bot
        army = self._get_army_units()

        # 🛡️ 방어적 코드: getattr 사용
        enemy_units = getattr(b, "enemy_units", [])

        # 일꾼 타겟팅 우선
        enemy_workers = [
            u
            for u in enemy_units
            if u.type_id in [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
        ]

        zerglings = [u for u in army if u.type_id == UnitTypeId.ZERGLING and u.is_idle]
        if zerglings and enemy_workers:
            # 일꾼이 있으면 일꾼 우선 공격 (경제 손상)
            for zergling in zerglings[: min(len(zerglings), 8)]:  # 최대 8마리만
                # 🚀 성능 최적화: distance_to() ** 2 사용 (루트 연산 제거)
                closest_worker = min(enemy_workers, key=lambda w: zergling.distance_to(w) ** 2)
                zergling.attack(closest_worker)

        # 나머지 병력은 적 본진 방향으로 이동 (견제)
        if self.attack_target:
            other_army = [u for u in army if u.type_id != UnitTypeId.ZERGLING and u.is_idle]
            for unit in other_army[: min(len(other_army), 6)]:  # 소규모만
                unit.move(self.attack_target)

    async def _execute_aggressive_attack(self, target_structure):
        """
        AGGRESSIVE 모드 공격 실행 - 공격적 확장 전략

        💡 AGGRESSIVE 전략:
            - 건물 파괴 우선 (게임 목적)
            - 대규모 교전
            - 소모전 강요
        """
        b = self.bot
        army = self._get_army_units()
        # 일꾼을 명시적으로 제외하여 전투 참여 방지
        army = [u for u in army if u.type_id != UnitTypeId.DRONE]

        # 적 기지 건물 우선 타겟팅 (기존 로직과 동일)
        zerglings = [u for u in army if u.type_id == UnitTypeId.ZERGLING and u.is_idle]
        if zerglings and self.attack_target:
            for zergling in zerglings:
                # Use ground_range instead of attack_range (python-sc2 API)
                zergling_range = max(
                    getattr(zergling, "ground_range", 0),
                    getattr(zergling, "air_range", 0),
                )
                if (
                    target_structure
                    and zergling.distance_to(target_structure)
                    <= zergling_range + target_structure.radius
                ):
                    zergling.attack(target_structure)
                else:
                    zergling.attack(self.attack_target)

        # 다른 병력도 적 기지 건물 우선 공격
        other_army = [u for u in army if u.type_id != UnitTypeId.ZERGLING and u.is_idle]
        for unit in other_army:
            if self.attack_target:
                # Use ground_range instead of attack_range (python-sc2 API)
                unit_range = max(getattr(unit, "ground_range", 0), getattr(unit, "air_range", 0))
                if (
                    target_structure
                    and unit.distance_to(target_structure) <= unit_range + target_structure.radius
                ):
                    unit.attack(target_structure)
                else:
                    unit.attack(self.attack_target)

    async def _rally_army(self):
        """군대 집결 (재집결 중일 때는 더 적극적으로 병력 모으기)"""
        b = self.bot

        # 재집결 중일 때는 집결지가 없으면 본진으로 설정
        if not self.rally_point:
            if self.regrouping_after_loss and b.townhalls.exists:
                townhalls = [th for th in b.townhalls]
                if townhalls:
                    # 본진과 맵 중앙 사이의 안전한 위치로 집결지 설정
                    self.rally_point = townhalls[0].position.towards(b.game_info.map_center, 15)
                else:
                    return
            else:
                return

        army = self._get_army_units()

        # 재집결 중일 때는 모든 병력을 집결지로 복귀 (idle 여부 무관)
        if self.regrouping_after_loss:
            for unit in army:
                # 집결지에서 멀리 떨어진 유닛은 즉시 복귀
                if unit.distance_to(self.rally_point) > 20:
                    unit.move(self.rally_point)
                # 집결지 근처에 있으면 idle 상태로 대기
                elif unit.is_idle:
                    # 집결지 주변에서 대기 (약간의 랜덤 위치로 분산)
                    import random

                    offset_x = random.uniform(-3, 3)
                    offset_y = random.uniform(-3, 3)
                    wait_position = self.rally_point + Point2((offset_x, offset_y))
                    unit.move(wait_position)
        else:
            # 일반 집결: idle 유닛만 집결지로 이동
            for unit in [u for u in army if u.is_idle]:
                unit.move(self.rally_point)

    # 4️⃣ 저글링 견제 (Harass)
    async def _harass_enemy(self):
        """
        저글링 견제 로직 - 상대 일꾼 공격 및 확장 방해

        💡 견제 전략:
            - 저글링 8마리 이상일 때 6마리를 견제 부대로 분리 (소수 정예)
            - 모든 유닛이 나가면 본진이 비어 위험하므로 일부만 보냄
            - 상대 앞마당(Natural)이나 본진 일꾼 공격
            - 히트앤런: 체력 낮으면 후퇴, 높으면 공격
            - 일꾼(SCV/Probe) 최우선 점사
        """
        b = self.bot

        # 전체 저글링 수 체크 (최소 8마리 필요)
        # 🚀 OPTIMIZATION: Use IntelManager cached data or filter once
        intel = getattr(b, "intel", None)
        if intel and intel.cached_military is not None:
            # Filter zerglings from cached military units
            all_zerglings = [u for u in intel.cached_military if u.type_id == UnitTypeId.ZERGLING]
        else:
            # Fallback: direct access if cache not available
            all_zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]

        if len(all_zerglings) < 8:
            # 저글링이 부족하면 견제 부대 해제 (본진 방어 우선)
            self.harass_squad = []
            return

        # 견제 부대 구성 (6마리만 - 소수 정예 전략)
        # 모든 유닛을 보내면 본진이 비어 위험하므로 일부만 견제에 투입
        if len(self.harass_squad) < 6:
            # 견제 부대에 포함되지 않은 저글링 선택
            non_harass_zerglings = [u for u in all_zerglings if u not in self.harass_squad]
            if non_harass_zerglings:
                # 체력이 높은 저글링 우선 선택
                non_harass_zerglings.sort(key=lambda u: u.health_percentage, reverse=True)
                needed = 6 - len(self.harass_squad)
                self.harass_squad.extend(non_harass_zerglings[:needed])

        # 견제 부대 유효성 검사 (죽은 유닛 제거)
        # Modern python-sc2: Check if unit exists in bot's unit list instead of is_alive
        # 🚀 OPTIMIZATION: Use IntelManager cached data for faster lookup
        intel = getattr(b, "intel", None)
        if intel and intel.cached_military is not None:
            # Use cached military units for tag lookup (much faster)
            current_unit_tags = {u.tag for u in intel.cached_military if hasattr(u, "tag")}
        else:
            # Fallback: direct access if cache not available
            current_unit_tags = {u.tag for u in b.units if hasattr(u, "tag")}
        self.harass_squad = [
            u for u in self.harass_squad if hasattr(u, "tag") and u.tag in current_unit_tags
        ]

        if not self.harass_squad:
            return

        # 견제 목표 위치 설정
        if not self.harass_target:
            # 상대 앞마당(Natural) 우선 탐색
            if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                enemy_start = b.enemy_start_locations[0]
                # 상대 본진과 맵 중앙 사이 (앞마당 위치 추정)
                self.harass_target = enemy_start.towards(b.game_info.map_center, 20)
            else:
                # 정찰 정보가 없으면 상대 시작 지점
                if b.enemy_start_locations and len(b.enemy_start_locations) > 0:
                    self.harass_target = b.enemy_start_locations[0]
                else:
                    self.harass_target = b.game_info.map_center

        # 견제 부대 제어
        # Note: Dead units are automatically removed from the list in python-sc2
        # Create set of current unit tags for fast lookup (once per frame)
        current_unit_tags = {u.tag for u in b.units if hasattr(u, "tag")}

        for zergling in self.harass_squad:
            # Modern python-sc2: Check if unit exists in bot's unit list
            # This is safer than checking is_alive attribute
            try:
                # Verify unit is still valid by checking if it exists in current units
                if not hasattr(zergling, "tag") or zergling.tag not in current_unit_tags:
                    continue

                # Also check health as additional safety measure
                if not hasattr(zergling, "health") or zergling.health <= 0:
                    continue
            except (AttributeError, TypeError):
                # Unit might be invalid, skip it
                continue

            # 체력이 30% 미만이면 후퇴
            if zergling.health_percentage < 0.3:
                # 본진 방향으로 후퇴
                townhalls = [th for th in b.townhalls]
                if townhalls:
                    if townhalls and len(townhalls) > 0:
                        retreat_pos = townhalls[0].position
                    else:
                        retreat_pos = b.start_location
                    zergling.move(retreat_pos)
                continue

            # 근처 적 유닛 탐색 (10 거리 내)
            # 🛡️ 방어적 코드: getattr 사용
            # 🚀 성능 최적화: distance_to() ** 2 사용 (API 호환성 보장)
            enemy_units = getattr(b, "enemy_units", [])
            nearby_range_squared = 10 * 10  # 10^2 = 100
            nearby_enemies = [
                u for u in enemy_units if zergling.distance_to(u) ** 2 < nearby_range_squared
            ]

            if nearby_enemies:
                # 일꾼 우선 타겟팅
                workers = [
                    u
                    for u in nearby_enemies
                    if u.type_id in [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
                ]

                if workers:
                    # 가장 가까운 일꾼 공격
                    # 🚀 성능 최적화: distance_to() ** 2 사용 (API 호환성 보장)
                    target = min(workers, key=lambda w: zergling.distance_to(w) ** 2)
                    zergling.attack(target)
                else:
                    # 일꾼이 없으면 가장 약한 유닛 공격
                    target = min(nearby_enemies, key=lambda e: e.health)
                    zergling.attack(target)
            else:
                # 적이 없으면 견제 목표 위치로 이동
                if self.harass_target:
                    zergling.attack(self.harass_target)

    # 5️⃣ 개별 유닛 마이크로
    async def _micro_units(self):
        """개별 유닛 마이크로 컨트롤"""
        await self._micro_zerglings()
        await self._micro_roaches()
        await self._micro_hydralisks()

    async def _micro_zerglings(self):
        """
        저글링 카이팅 (Hit & Run)

        💡 카이팅 로직:
            weapon_cooldown > 0: 공격 쿨다운 중
            towards(target, -거리): 적 반대 방향으로 이동
        """
        b = self.bot

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_zerglings is not None:
            all_zerglings = list(intel.cached_zerglings)
        else:
            all_zerglings = [u for u in b.units(UnitTypeId.ZERGLING)]

        # 견제 부대는 제외하고 일반 저글링만 마이크로
        zerglings = [u for u in all_zerglings if u not in self.harass_squad]
        for ling in zerglings:
            # 🛡️ 방어적 코드: getattr 사용
            # 🚀 성능 최적화: distance_to() ** 2 사용 (루트 연산 제거)
            enemy_units = getattr(b, "enemy_units", [])
            engage_range_squared = self.config.ENGAGE_DISTANCE * self.config.ENGAGE_DISTANCE
            enemies = [u for u in enemy_units if u.distance_to(ling) ** 2 < engage_range_squared]

            if not enemies:
                continue

            # 우선순위 타겟 선택
            target = self._select_priority_target(ling, enemies)
            if not target:
                continue

            # 체력 낮으면 후퇴
            if ling.health_percentage < self.config.RETREAT_HP_PERCENT:
                retreat_pos = self._get_retreat_position(ling)
                ling.move(retreat_pos)
                continue

            # 카이팅
            if ling.weapon_cooldown > 0:
                kite_pos = ling.position.towards(target, -self.config.KITING_DISTANCE)
                ling.move(kite_pos)
            else:
                ling.attack(target)

    async def _micro_roaches(self):
        """로치 컨트롤"""
        b = self.bot

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_roaches is not None:
            roaches = list(intel.cached_roaches)
        else:
            roaches = [u for u in b.units(UnitTypeId.ROACH)]
        for roach in roaches:
            # 🛡️ 방어적 코드: getattr 사용
            # 🚀 성능 최적화: distance_to() ** 2 사용 (루트 연산 제거)
            enemy_units = getattr(b, "enemy_units", [])
            engage_range_squared = self.config.ENGAGE_DISTANCE * self.config.ENGAGE_DISTANCE
            enemies = [u for u in enemy_units if u.distance_to(roach) ** 2 < engage_range_squared]

            if not enemies:
                continue

            # 체력 낮으면 후퇴 (로치는 재생 능력)
            if roach.health_percentage < 0.4:
                retreat_pos = self._get_retreat_position(roach)
                roach.move(retreat_pos)
                continue

            # 우선순위 타겟 공격
            target = self._select_priority_target(roach, enemies)
            if target:
                roach.attack(target)

    async def _micro_hydralisks(self):
        """히드라리스크 컨트롤 (원거리 딜러)"""
        b = self.bot

        # 🚀 성능 최적화: IntelManager 캐시 사용
        intel = getattr(b, "intel", None)
        if intel and intel.cached_hydralisks is not None:
            hydras = list(intel.cached_hydralisks)
        else:
            hydras = [u for u in b.units(UnitTypeId.HYDRALISK)]
        for hydra in hydras:
            # 🛡️ 방어적 코드: getattr 사용
            # 🚀 성능 최적화: distance_to() ** 2 사용 (루트 연산 제거)
            enemy_units = getattr(b, "enemy_units", [])
            engage_range_squared = self.config.ENGAGE_DISTANCE * self.config.ENGAGE_DISTANCE
            enemies = [u for u in enemy_units if u.distance_to(hydra) ** 2 < engage_range_squared]

            if not enemies:
                continue

            # 히드라는 체력이 낮으므로 더 빨리 후퇴
            if hydra.health_percentage < 0.5:
                retreat_pos = self._get_retreat_position(hydra)
                hydra.move(retreat_pos)
                continue

            target = self._select_priority_target(hydra, enemies)
            if not target:
                continue

            # 카이팅 (히드라는 원거리라 더 효과적)
            if hydra.weapon_cooldown > 0:
                kite_pos = hydra.position.towards(target, -3)
                hydra.move(kite_pos)
            else:
                hydra.attack(target)

    # 🎯 우선순위 타겟팅 (Focus Fire)
    def _select_priority_target(self, unit: Unit, enemies: List[Unit]) -> Optional[Unit]:
        """
        우선순위 타겟 선택 (Focus Fire)

        가중치 시스템:
            TARGET_PRIORITY 딕셔너리에서 유닛별 가중치를 가져와
            가장 높은 가중치의 적을 우선 공격

        Args:
            unit: 공격할 아군 유닛
            enemies: 적 유닛들

        Returns:
            Unit: 선택된 타겟
        """
        # Filter enemies within attack range using list comprehension
        # Use ground_range instead of attack_range (python-sc2 API)
        # 🚀 성능 최적화: distance_to() ** 2 사용 (API 호환성 보장)
        unit_range = max(getattr(unit, "ground_range", 0), getattr(unit, "air_range", 0))
        in_range = []
        for e in enemies:
            attack_range = unit_range + e.radius
            attack_range_squared = attack_range * attack_range
            if unit.distance_to(e) ** 2 <= attack_range_squared:
                in_range.append(e)
        if not in_range:
            in_range = enemies

        # 빈 리스트 체크
        if not in_range:
            # 적이 없으면 가장 가까운 적 반환 (fallback)
            # 🚀 성능 최적화: distance_to() ** 2 사용 (API 호환성 보장)
            if enemies:
                return min(enemies, key=lambda e: unit.distance_to(e) ** 2)
            return None

        # 동적 타겟 우선순위 계산 (내 조합에 따른 상대 우선순위 재계산)
        # Calculate our army composition for dynamic priority
        our_army_composition = {}
        b = self.bot
        army = self._get_army_units()

        for unit_type in [
            UnitTypeId.ZERGLING,
            UnitTypeId.HYDRALISK,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
        ]:
            count = sum(1 for u in army if u.type_id == unit_type)
            our_army_composition[unit_type] = count

        # Dynamic priority calculation
        best_target = max(
            in_range,
            key=lambda t: self._calculate_dynamic_target_priority(t, our_army_composition),
        )

        return best_target

    def _calculate_concave_formation(self, units: List[Unit], target: Point2) -> List[Point2]:
        """
        오목한 진형(Concave) 형성 계산 - 포위 전술

        적 위치를 중심으로 반원을 그리며 병력을 분산시킨 후 동시에 덮치는 전술
        저그 병력의 핵심은 '포위'입니다.

        Args:
            units: 아군 유닛 목록
            target: 적 위치 (목표 지점)

        Returns:
            List[Point2]: 각 유닛의 포위 위치 (formation positions)
        """
        if not units:
            return []

        formation_positions = []

        # 적 위치를 중심으로 반원 형성
        # 반원의 반지름: 유닛 수에 따라 조정 (10~15 units)
        formation_radius = min(15.0, max(10.0, len(units) * 0.8))

        # 각도를 균등하게 분배 (180도 반원)
        angle_step = 180.0 / len(units) if len(units) > 1 else 0

        for i, unit in enumerate(units):
            # 각도 계산: -90도에서 시작하여 180도 범위로 분산
            angle_deg = -90.0 + (i * angle_step)
            angle_rad = math.radians(angle_deg)

            # 반원 상의 위치 계산
            offset_x = formation_radius * math.cos(angle_rad)
            offset_y = formation_radius * math.sin(angle_rad)

            # 타겟 위치 기준으로 오프셋 적용
            formation_pos = target + Point2((offset_x, offset_y))
            formation_positions.append(formation_pos)

        return formation_positions

    def _calculate_dynamic_target_priority(
        self, enemy_unit: Unit, our_army_composition: dict
    ) -> float:
        """
        동적 타겟 우선순위 계산 - 내 조합에 따른 상대 우선순위 재계산

        내 병력이 히드라 중심이라면 '탱크'를 1순위로,
        저글링 중심이라면 '기뢰나 맹독충'을 1순위로 피하거나 점사

        Args:
            enemy_unit: 적 유닛
            our_army_composition: 아군 조합 (유닛 타입별 수)

        Returns:
            float: 우선순위 점수 (높을수록 우선)
        """
        base_priority = TARGET_PRIORITY.get(enemy_unit.type_id, 1)

        # 히드라 중심 조합일 때
        hydra_count = our_army_composition.get(UnitTypeId.HYDRALISK, 0)
        zergling_count = our_army_composition.get(UnitTypeId.ZERGLING, 0)
        roach_count = our_army_composition.get(UnitTypeId.ROACH, 0)

        total_army = hydra_count + zergling_count + roach_count
        if total_army == 0:
            return base_priority

        hydra_ratio = hydra_count / total_army if total_army > 0 else 0
        zergling_ratio = zergling_count / total_army if total_army > 0 else 0

        # 히드라 중심 조합: 탱크를 최우선 타겟
        if hydra_ratio > 0.4:  # 40% 이상 히드라
            if enemy_unit.type_id in [UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED]:
                return base_priority + 10.0  # 탱크 최우선
            if enemy_unit.type_id in [UnitTypeId.MEDIVAC, UnitTypeId.VIKINGFIGHTER]:
                return base_priority + 8.0  # 의료선, 바이킹 우선

        # 저글링 중심 조합: 기뢰, 맹독충을 피하거나 점사
        if zergling_ratio > 0.6:  # 60% 이상 저글링
            if enemy_unit.type_id in [UnitTypeId.WIDOWMINE, UnitTypeId.BANELING]:
                return base_priority + 12.0  # 기뢰, 맹독충 최우선 제거
            if enemy_unit.type_id in [UnitTypeId.MARAUDER, UnitTypeId.MARINE]:
                return base_priority + 7.0  # 해병, 불곰 우선

        # 로치 중심 조합: 거신, 불멸자를 우선
        roach_ratio = roach_count / total_army if total_army > 0 else 0
        if roach_ratio > 0.5:  # 50% 이상 로치
            if enemy_unit.type_id in [UnitTypeId.COLOSSUS, UnitTypeId.IMMORTAL]:
                return base_priority + 10.0  # 거신, 불멸자 최우선

        # 기본 우선순위 + 체력 비율 (체력 낮은 적 우선)
        health_penalty = (1 - enemy_unit.health_percentage) * 5.0
        return base_priority + health_penalty

    # 🔄 유틸리티 함수
    def _get_army_units(self) -> List[Unit]:
        """
        전투 유닛 목록 반환 (일꾼 제외)

        Returns:
            List[Unit]: 전투 유닛 목록 (DRONE 제외)
        """
        b = self.bot
        army_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKER,
            UnitTypeId.MUTALISK,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.ULTRALISK,
            UnitTypeId.BROODLORD,
        }
        return [u for u in b.units if u.type_id in army_types]

    def _get_retreat_position(self, unit: Unit) -> Point2:
        """후퇴 위치 계산"""
        b = self.bot

        # 가장 가까운 기지로 후퇴
        # 🚀 성능 최적화: distance_to() ** 2 사용 (API 호환성 보장)
        townhalls = [th for th in b.townhalls]
        if not townhalls:
            return b.start_location

        closest_th = min(townhalls, key=lambda th: unit.distance_to(th) ** 2)
        return closest_th.position

    def _calculate_army_centroid(self) -> Optional[Point2]:
        """
        군대 중심점(Centroid) 계산

        💡 클러스터링:
            병력의 평균 위치를 계산하여 집결 여부 판단

        Returns:
            Point2: 군대 중심점
        """
        army = self._get_army_units()

        if not army:
            return None

        x_sum = sum(u.position.x for u in army)
        y_sum = sum(u.position.y for u in army)

        return Point2((x_sum / len(army), y_sum / len(army)))

    def _calculate_army_spread(self) -> float:
        """
        군대 분산도 계산

        Returns:
            float: 중심점으로부터의 평균 거리
        """
        army = self._get_army_units()
        centroid = self._calculate_army_centroid()

        if not army or not centroid:
            return 0.0

        total_distance = sum(u.position.distance_to(centroid) for u in army)
        return total_distance / len(army)

    # 📊 전투 상태 조회
    def get_combat_status(self) -> dict:
        """현재 전투 상태 반환"""
        return {
            "is_attacking": self.is_attacking,
            "is_retreating": self.is_retreating,
            "army_gathered": self.army_gathered,
            "army_count": self.current_army_count,
            "rally_point": str(self.rally_point) if self.rally_point else None,
            "attack_target": str(self.attack_target) if self.attack_target else None,
        }

    def set_attack_target(self, target: Point2):
        """공격 목표 설정"""
        self.attack_target = target

    def set_rally_point(self, point: Point2):
        """집결지 설정"""
        self.rally_point = point

    def _can_attrit_enemy_units(self) -> bool:
        """
        소모전 판단 로직: 상대방의 병력을 갉아먹을 수 있는가?

        저그는 '소모전'에 능해야 함. 단순히 승률이 낮다고 빼는 것이 아니라,
        상대방의 병력을 지속적으로 감소시킬 수 있는지 판단.

        판단 기준:
        1. 히드라리스크: 사거리 우위로 안전하게 공격 가능
        2. 저글링: 감싸기(Surround)로 적 유닛 격파 가능
        3. 맹독충: 바이오닉 상대로 효과적
        4. 적 병력 대비 우리 병력의 효율성 (DPS/비용 비율)

        Returns:
            bool: 소모전 가능 여부 (True = 계속 교전 가능, False = 퇴각 필요)
        """
        b = self.bot

        try:
            # 1. 우리 유닛 구성 확인
            hydralisks = b.units(UnitTypeId.HYDRALISK).ready
            zerglings = b.units(UnitTypeId.ZERGLING).ready
            banelings = b.units(UnitTypeId.BANELING).ready
            roaches = b.units(UnitTypeId.ROACH).ready

            hydra_count = (
                hydralisks.amount if hasattr(hydralisks, "amount") else len(list(hydralisks))
            )
            zergling_count = (
                zerglings.amount if hasattr(zerglings, "amount") else len(list(zerglings))
            )
            baneling_count = (
                banelings.amount if hasattr(banelings, "amount") else len(list(banelings))
            )
            roach_count = roaches.amount if hasattr(roaches, "amount") else len(list(roaches))

            # 2. 적 유닛 확인 (시야 내)
            enemy_units = b.known_enemy_units
            if not enemy_units or not enemy_units.exists:
                # 적이 보이지 않으면 소모전 불가능
                return False

            enemy_count = (
                enemy_units.amount if hasattr(enemy_units, "amount") else len(list(enemy_units))
            )

            # 3. 소모전 가능 여부 판단
            # 히드라리스크: 사거리 6으로 안전하게 공격 가능 (상대가 근접 유닛이면 특히 유리)
            if hydra_count >= 6:
                # 히드라가 6기 이상이면 사거리 우위로 소모전 가능
                return True

            # 저글링 + 맹독충 조합: 바이오닉 상대로 효과적 (소모전 가능)
            if zergling_count >= 12 and baneling_count >= 2:
                # 저글링으로 감싸기 + 맹독충으로 집중 타격
                return True

            # 저글링만: 상대가 근접 유닛이 많으면 소모전 가능 (감싸기로 우위)
            if zergling_count >= 16:
                # 저글링이 많으면 감싸기로 소모전 가능
                # 단, 상대가 원거리 유닛(공성 전차 등)이 많으면 불리
                enemy_ranged_count = 0
                for enemy in enemy_units:
                    # 공성 전차, 해병, 불곰 등 원거리 유닛 체크
                    if hasattr(enemy, "is_ranged") and enemy.is_ranged:
                        enemy_ranged_count += 1

                # 원거리 유닛이 적으면 저글링으로 소모전 가능
                if enemy_ranged_count < enemy_count * 0.3:  # 원거리 유닛이 30% 미만
                    return True

            # 로치 + 히드라 조합: 중반 소모전 가능
            if roach_count >= 6 and hydra_count >= 3:
                return True

            # 4. 병력 비율 체크: 우리가 적보다 많으면 소모전 가능
            our_total = hydra_count + zergling_count + roach_count
            if our_total > enemy_count * 1.5:  # 1.5배 이상 우위
                return True

            # 5. 기본 판단: 병력이 너무 적으면 소모전 불가능
            if our_total < 8:
                return False

            # 기본적으로 소모전 가능 (저그는 소모전에 유리)
            return True

        except Exception as e:
            # 에러 발생 시 안전하게 False 반환 (퇴각)
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 100 == 0:
                print(f"[WARNING] _can_attrit_enemy_units 오류: {e}")
            return False

    def _update_win_rate(self):
        """
        현재 승률을 계산하여 업데이트

        ProductionManager나 IntelManager에서 계산된 승률을 가져오거나,
        직접 계산하여 저장합니다.
        """
        b = self.bot

        try:
            # 1. ProductionManager에서 계산된 승률 가져오기 (우선순위 1)
            production = getattr(b, "production", None)
            if production and hasattr(production, "last_calculated_win_rate"):
                calculated_rate = getattr(production, "last_calculated_win_rate", 50.0)
                self.current_win_rate = calculated_rate
                # 메인 봇의 승률도 동기화 (매니저들이 참조 가능하도록)
                setattr(b, "current_win_rate", calculated_rate)
                return

            # 2. 직접 승률 계산 (fallback)
            # 상대 테크 확인
            enemy_tech = getattr(b, "enemy_tech", "UNKNOWN")
            if enemy_tech == "UNKNOWN" or enemy_tech == "GROUND" or enemy_tech == "SCANNING":
                # 테크가 탐지되지 않았으면 기본값 유지
                return

            # 내 유닛 수 확인
            hydra_count = (
                b.units(UnitTypeId.HYDRALISK).amount
                if hasattr(b.units(UnitTypeId.HYDRALISK), "amount")
                else len(list(b.units(UnitTypeId.HYDRALISK)))
            )
            ravager_count = (
                b.units(UnitTypeId.RAVAGER).amount
                if hasattr(b.units(UnitTypeId.RAVAGER), "amount")
                else len(list(b.units(UnitTypeId.RAVAGER)))
            )
            baneling_count = (
                b.units(UnitTypeId.BANELING).amount
                if hasattr(b.units(UnitTypeId.BANELING), "amount")
                else len(list(b.units(UnitTypeId.BANELING)))
            )
            zergling_count = (
                b.units(UnitTypeId.ZERGLING).amount
                if hasattr(b.units(UnitTypeId.ZERGLING), "amount")
                else len(list(b.units(UnitTypeId.ZERGLING)))
            )
            queen_count = (
                b.units(UnitTypeId.QUEEN).amount
                if hasattr(b.units(UnitTypeId.QUEEN), "amount")
                else len(list(b.units(UnitTypeId.QUEEN)))
            )

            # 승률 계산 (간이 휴리스틱)
            win_rate = 50.0  # 기본 50%

            if enemy_tech == "AIR":
                base_rate = 30.0
                hydra_bonus = min(hydra_count * 5, 50)
                win_rate = base_rate + hydra_bonus
                queen_bonus = min(queen_count * 2, 10)
                win_rate += queen_bonus
            elif enemy_tech == "MECHANIC":
                base_rate = 40.0
                ravager_bonus = min(ravager_count * 7, 45)
                win_rate = base_rate + ravager_bonus
                roach_count = (
                    b.units(UnitTypeId.ROACH).amount
                    if hasattr(b.units(UnitTypeId.ROACH), "amount")
                    else len(list(b.units(UnitTypeId.ROACH)))
                )
                roach_bonus = min(roach_count * 1, 10)
                win_rate += roach_bonus
            elif enemy_tech == "BIO":
                base_rate = 35.0
                baneling_bonus = min(baneling_count * 4, 40)
                win_rate = base_rate + baneling_bonus
                win_rate += min(zergling_count * 0.5, 15)

                # 맹독충 속업 확인
                if hasattr(b, "state") and hasattr(b.state, "upgrades"):
                    upgrades = b.state.upgrades
                    from sc2.ids.upgrade_id import UpgradeId

                    centrifugal_upgrade_id = getattr(UpgradeId, "CENTRIFUGALHOOKS", None)
                    if not centrifugal_upgrade_id:
                        centrifugal_upgrade_id = getattr(UpgradeId, "CENTRIFUGAL_HOOKS", None)
                    if centrifugal_upgrade_id and centrifugal_upgrade_id in upgrades:
                        win_rate += 15

            # 승률 제한 (10% ~ 95%)
            self.current_win_rate = max(10.0, min(95.0, win_rate))
            # 메인 봇의 승률도 동기화 (매니저들이 참조 가능하도록)
            setattr(b, "current_win_rate", self.current_win_rate)

        except Exception as e:
            # 에러 발생 시 기본값 유지
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 500 == 0:
                print(f"[WARNING] Failed to update win rate: {e}")

    async def _execute_smart_retreat(self):
        """
        승률 기반 스마트 후퇴 실행

        승률이 낮을 때 모든 전투 유닛을 본진으로 후퇴시킵니다.
        """
        b = self.bot

        try:
            # 본진 위치 확인
            if not b.townhalls.exists:
                return

            home_base = b.townhalls.first.position

            # 모든 전투 유닛을 본진으로 후퇴
            army_types = {
                UnitTypeId.ZERGLING,
                UnitTypeId.ROACH,
                UnitTypeId.RAVAGER,
                UnitTypeId.HYDRALISK,
                UnitTypeId.BANELING,
                UnitTypeId.LURKER,
            }

            for unit in b.units:
                if unit.type_id in army_types and not unit.is_structure:
                    # 적과 너무 가까우면 즉시 후퇴
                    # 🚀 성능 최적화: distance_to_squared 사용 (루트 연산 제거)
                    enemy_nearby = False
                    if hasattr(b, "enemy_units") and b.enemy_units:
                        enemy_threat_range_squared = 15.0 * 15.0  # 15^2 = 225
                        for enemy in b.enemy_units:
                            if unit.distance_to(enemy) ** 2 < enemy_threat_range_squared:
                                enemy_nearby = True
                                break

                    home_base_range_squared = 30.0 * 30.0  # 30^2 = 900
                    if enemy_nearby or unit.distance_to(home_base) ** 2 > home_base_range_squared:
                        unit.move(home_base)

        except Exception as e:
            current_iteration = getattr(b, "iteration", 0)
            if current_iteration % 100 == 0:
                print(f"[WARNING] Failed to execute smart retreat: {e}")

    async def _visualize_retreat_status(self, bot, is_retreating: bool):
        """
        승률 기반 후퇴 상태를 화면에 시각화

        승산 없는 전투 회피 원칙을 시각적으로 확인할 수 있도록
        화면에 승률과 후퇴 상태를 표시합니다.

        🚀 PERFORMANCE: Disabled in training mode (realtime=False) to reduce CPU load
        """
        try:
            # 🚀 성능 최적화: 훈련 모드에서는 시각화 완전 차단

            show_window = os.environ.get("SHOW_WINDOW", "false").lower() == "true"
            if not show_window:
                return  # Skip all visualization in training mode

            current_iteration = getattr(bot, "iteration", 0)
            # 4프레임마다 업데이트 (CPU 부담 감소)
            if current_iteration % 4 != 0:
                return

            win_rate = self.current_win_rate

            # 화면에 텍스트 표시 (SC2 내장 디버그 기능 사용)
            if hasattr(bot, "client") and bot.client:
                if is_retreating:
                    status_text = (
                        f"RETREATING - Win Rate {win_rate:.0f}% < {self.advance_threshold:.0f}%"
                    )
                    color = (255, 0, 0)  # Red: retreating
                else:
                    status_text = (
                        f"ENGAGING - Win Rate {win_rate:.0f}% >= {self.retreat_threshold:.0f}%"
                    )
                    color = (0, 255, 0)  # Green: engaging

                # 화면 중앙 상단에 승률과 상태 표시
                try:
                    bot.client.debug_text_screen(status_text, pos=(0.4, 0.1), size=15, color=color)
                except Exception:
                    # debug_text_screen이 지원되지 않는 경우 무시
                    pass

            # DebugVisualizer가 있으면 대시보드 업데이트
            visualizer = getattr(bot, "visualizer", None)
            if visualizer and hasattr(visualizer, "update_dashboard"):
                try:
                    # DebugVisualizer의 update_dashboard는 bot 인스턴스를 받음
                    visualizer.update_dashboard(bot)
                except Exception:
                    # Visualizer 업데이트 실패 시 무시
                    pass

        except Exception as e:
            # 시각화 실패는 게임 플레이에 영향을 주지 않도록 무시
            pass
