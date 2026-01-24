# -*- coding: utf-8 -*-
"""
Bot Step Integration - on_step 구현 통합 모듈

이 모듈은 WickedZergBotPro의 on_step 메서드를 구현하여
실제 게임 로직과 훈련 로직을 통합합니다.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional


class LogicActivityTracker:
    """실시간 로직 활성화 추적기"""

    def __init__(self):
        self.active_logics: Dict[str, Dict] = {}
        self.last_report_time = 0
        self.report_interval = 10.0  # 10초마다 보고
        self.execution_counts: Dict[str, int] = {}
        self.execution_times: Dict[str, float] = {}

    def start_logic(self, name: str) -> float:
        """로직 시작 시간 기록"""
        start_time = time.time()
        self.active_logics[name] = {
            "start_time": start_time,
            "status": "running"
        }
        return start_time

    def end_logic(self, name: str, start_time: float, success: bool = True):
        """로직 종료 및 실행 시간 기록"""
        elapsed = time.time() - start_time
        if name in self.active_logics:
            self.active_logics[name]["status"] = "done" if success else "error"
            self.active_logics[name]["elapsed"] = elapsed

        # 통계 업데이트
        self.execution_counts[name] = self.execution_counts.get(name, 0) + 1
        self.execution_times[name] = self.execution_times.get(name, 0) + elapsed

    def get_activity_report(self, game_time: float) -> str:
        """활성화된 로직 보고서 생성"""
        current_time = time.time()
        if current_time - self.last_report_time < self.report_interval:
            return ""

        self.last_report_time = current_time

        lines = [f"\n[LOGIC ACTIVITY] 게임 시간: {int(game_time)}초"]
        lines.append("=" * 50)

        # 실행 횟수 및 시간 출력
        for name, count in sorted(self.execution_counts.items()):
            total_time = self.execution_times.get(name, 0)
            avg_time = (total_time / count * 1000) if count > 0 else 0
            lines.append(f"  {name}: {count}회 실행, 평균 {avg_time:.2f}ms")

        lines.append("=" * 50)

        # 카운터 리셋
        self.execution_counts.clear()
        self.execution_times.clear()

        return "\n".join(lines)

    def get_current_status(self) -> List[str]:
        """현재 활성화된 로직 목록 반환"""
        return [name for name, info in self.active_logics.items()
                if info.get("status") == "running"]

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:

    class BotAI:
        pass

    class UnitTypeId:
        pass


class BotStepIntegrator:
    """
    Bot의 on_step 메서드를 구현하는 통합 클래스

    기능:
    1. 매니저들 초기화 (lazy loading)
    2. 게임 로직 실행 (economy, production, combat 등)
    3. 훈련 모드: 보상 계산 및 RL 업데이트
    4. 최신 개선 사항 통합 (advanced_building_manager 등)
    5. 실시간 로직 활성화 보고
    """

    def __init__(self, bot):
        self.bot = bot
        self._managers_initialized = False
        self._logic_tracker = LogicActivityTracker()

    async def initialize_managers(self):
        """
        매니저들 초기화 (lazy loading)
        NOTE: 메인 봇 클래스(WickedZergBotProImpl)에서 초기화가 수행되므로
        여기서는 추가적인 초기화 로직을 수행하지 않습니다.
        """
        self._managers_initialized = True
        return

    async def execute_game_logic(self, iteration: int):
        """게임 로직 실행"""
        try:
            # 0. Performance Optimizer 프레임 시작
            if hasattr(self.bot, "performance_optimizer") and self.bot.performance_optimizer:
                self.bot.performance_optimizer.start_frame()

            # 0.03 ★★★ Build Order System (빌드 오더 - 최최우선) ★★★
            if self.bot.time < 180.0:  # 3분 이내
                if not hasattr(self.bot, "build_order_system"):
                    try:
                        from build_order_system import BuildOrderSystem
                        self.bot.build_order_system = BuildOrderSystem(self.bot)
                        print("[BUILD_ORDER] 빌드 오더 시스템 활성화!")
                    except ImportError as e:
                        print(f"[WARNING] Build order system not available: {e}")
                        self.bot.build_order_system = None

                if hasattr(self.bot, "build_order_system") and self.bot.build_order_system:
                    start_time = self._logic_tracker.start_logic("BuildOrder")
                    try:
                        await self.bot.build_order_system.execute(iteration)
                        # 주기적으로 진행도 출력
                        if iteration % 150 == 0:
                            progress = self.bot.build_order_system.get_progress()
                            print(f"[BUILD_ORDER] {progress}")
                    except Exception as e:
                        if iteration % 200 == 0:
                            print(f"[WARNING] Build Order error: {e}")
                    finally:
                        self._logic_tracker.end_logic("BuildOrder", start_time)

            # 0.05 ★★★ Early Defense System (초반 방어 - 최우선) ★★★
            if self.bot.time < 180.0:  # 3분 이내
                if not hasattr(self.bot, "early_defense"):
                    try:
                        from early_defense_system import EarlyDefenseSystem
                        self.bot.early_defense = EarlyDefenseSystem(self.bot)
                        print("[EARLY_DEFENSE] 초반 방어 시스템 활성화!")
                    except ImportError as e:
                        print(f"[WARNING] Early defense system not available: {e}")
                        self.bot.early_defense = None

                if hasattr(self.bot, "early_defense") and self.bot.early_defense:
                    start_time = self._logic_tracker.start_logic("EarlyDefense")
                    try:
                        await self.bot.early_defense.execute(iteration)
                        # 주기적으로 상태 출력
                        if iteration % 100 == 0:
                            status = self.bot.early_defense.get_status()
                            print(f"[EARLY_DEFENSE] {status}")
                    except Exception as e:
                        if iteration % 200 == 0:
                            print(f"[WARNING] Early Defense error: {e}")
                    finally:
                        self._logic_tracker.end_logic("EarlyDefense", start_time)

            # 0.06 ★★★ Early Scout System (초반 정찰) ★★★
            if self.bot.time < 300.0:  # 5분 이내
                if not hasattr(self.bot, "early_scout"):
                    try:
                        from early_scout_system import EarlyScoutSystem
                        self.bot.early_scout = EarlyScoutSystem(self.bot)
                        print("[EARLY_SCOUT] 초반 정찰 시스템 활성화!")
                    except ImportError as e:
                        print(f"[WARNING] Early scout system not available: {e}")
                        self.bot.early_scout = None

                if hasattr(self.bot, "early_scout") and self.bot.early_scout:
                    start_time = self._logic_tracker.start_logic("EarlyScout")
                    try:
                        await self.bot.early_scout.execute(iteration)
                        # 주기적으로 상태 출력
                        if iteration % 150 == 0:
                            status = self.bot.early_scout.get_scout_status()
                            print(f"[EARLY_SCOUT] {status}")
                    except Exception as e:
                        if iteration % 200 == 0:
                            print(f"[WARNING] Early Scout error: {e}")
                    finally:
                        self._logic_tracker.end_logic("EarlyScout", start_time)

            # 0.1 Strategy Manager 업데이트 (종족별 전략 + Emergency Mode)
            if hasattr(self.bot, "strategy_manager") and self.bot.strategy_manager:
                start_time = self._logic_tracker.start_logic("Strategy")
                try:
                    # Debug: 매니저 호출 확인
                    if iteration == 1 or iteration % 500 == 0:
                        print(f"[DEBUG] Calling strategy_manager.update() at iteration {iteration}")
                    self.bot.strategy_manager.update()
                except Exception as e:
                    if iteration % 200 == 0:
                        print(f"[WARNING] Strategy Manager error: {e}")
                finally:
                    self._logic_tracker.end_logic("Strategy", start_time)
            else:
                if iteration == 1:
                    print(f"[WARNING] strategy_manager not found! hasattr={hasattr(self.bot, 'strategy_manager')}, value={getattr(self.bot, 'strategy_manager', None)}")

            # 0.15 ★ Defeat Detection (패배 직감 시스템) ★
            if hasattr(self.bot, "defeat_detection") and self.bot.defeat_detection:
                start_time = self._logic_tracker.start_logic("DefeatDetection")
                try:
                    defeat_status = await self.bot.defeat_detection.on_step(iteration)

                    # 패배 직전이면 마지막 방어 시도
                    if defeat_status.get("last_stand_required", False):
                        if iteration % 200 == 0:  # 주기적으로 출력
                            print(f"[DEFEAT DETECTION] ★ 패배 직전! 마지막 방어 시도! ★")
                            print(f"  - 패배 수준: {self.bot.defeat_detection.get_defeat_level_name()}")
                            print(f"  - 이유: {defeat_status.get('defeat_reason', '알 수 없음')}")

                        # Combat Manager에게 마지막 방어 위치 전달
                        if hasattr(self.bot, "combat") and self.bot.combat:
                            last_stand_pos = defeat_status.get("last_stand_position")
                            if last_stand_pos and hasattr(self.bot.combat, "_defense_rally_point"):
                                self.bot.combat._defense_rally_point = last_stand_pos
                                self.bot.combat._base_defense_active = True

                    # 패배 불가피하면 항복 고려 (훈련 모드에서는 빠른 게임 종료)
                    elif defeat_status.get("should_surrender", False):
                        if iteration % 200 == 0:
                            print(f"[DEFEAT DETECTION] 패배 불가피 - {defeat_status.get('defeat_reason', '알 수 없음')}")

                    # 위기 상황이면 경고
                    elif defeat_status.get("defeat_level", 0) >= 2:  # CRITICAL
                        if iteration % 300 == 0:
                            print(f"[DEFEAT DETECTION] 위기 상황! - {defeat_status.get('defeat_reason', '알 수 없음')}")

                except Exception as e:
                    if iteration % 200 == 0:
                        print(f"[WARNING] Defeat Detection error: {e}")
                finally:
                    self._logic_tracker.end_logic("DefeatDetection", start_time)

            # 0.2 Aggressive Strategies (초반 공격 전략 - 12풀, 맹독충 올인 등)
            if iteration % 4 == 0:  # 4프레임마다 실행
                await self._safe_manager_step(
                    getattr(self.bot, "aggressive_strategies", None),
                    iteration,
                    "Aggressive Strategies",
                    method_name="execute",
                )

            # 1. Intel (정보 수집)
            await self._safe_manager_step(self.bot.intel, iteration, "Intel")

            # 2. Scouting (정찰)
            await self._safe_manager_step(self.bot.scout, iteration, "Scouting")

            # 2.2. Creep Manager (점막 계획)
            await self._safe_manager_step(
                getattr(self.bot, "creep_manager", None),
                iteration,
                "Creep manager",
            )

            # 3. Economy (경제)
            await self._safe_manager_step(self.bot.economy, iteration, "Economy")

            # 4. Production (생산)
            if self.bot.production:
                start_time = self._logic_tracker.start_logic("Production")
                success = True
                try:
                    # ProductionResilience의 메서드 호출
                    if hasattr(self.bot.production, "fix_production_bottleneck"):
                        await self.bot.production.fix_production_bottleneck()
                except Exception as e:
                    success = False
                    if iteration % 200 == 0:
                        print(f"[WARNING] Production error: {e}")
                finally:
                    self._logic_tracker.end_logic("Production", start_time, success)

            # 4.2. Unit Factory (fallback when production manager missing)
            if hasattr(self.bot, "unit_factory") and self.bot.production is None:
                try:
                    await self.bot.unit_factory.on_step(iteration)
                except Exception as e:
                    if iteration % 200 == 0:
                        print(f"[WARNING] Unit factory error: {e}")

            # 4.5. Evolution Upgrades (공방 업그레이드)
            await self._safe_manager_step(
                getattr(self.bot, "upgrade_manager", None),
                iteration,
                "Upgrade manager",
            )

            # 5. Advanced Building Manager (최신 개선 사항)
            if hasattr(self.bot, "advanced_building_manager"):
                start_time = self._logic_tracker.start_logic("AdvancedBuilding")
                success = True
                try:
                    # 자원 적체 시 처리
                    if iteration % 22 == 0:  # 매 1초마다
                        surplus_results = (
                            await self.bot.advanced_building_manager.handle_resource_surplus()
                        )
                        if surplus_results and iteration % 100 == 0:
                            print(f"[RESOURCE SURPLUS] Handled: {surplus_results}")

                    # 방어 건물 최적 위치에 건설
                    if iteration % 44 == 0:  # 매 2초마다
                        await self.bot.advanced_building_manager.build_defense_buildings_optimally()
                except Exception as e:
                    success = False
                    if iteration % 200 == 0:
                        print(f"[WARNING] Advanced Building Manager error: {e}")
                finally:
                    self._logic_tracker.end_logic("AdvancedBuilding", start_time, success)

            # 6. Aggressive Tech Builder (최신 개선 사항)
            if hasattr(self.bot, "aggressive_tech_builder"):
                start_time = self._logic_tracker.start_logic("AggressiveTech")
                success = True
                try:
                    # 자원이 넘칠 때 테크 건설
                    if iteration % 22 == 0:  # 매 1초마다
                        has_excess, _, _ = (
                            self.bot.aggressive_tech_builder.has_excess_resources()
                        )
                        if has_excess:
                            recommendations = (
                                await self.bot.aggressive_tech_builder.recommend_tech_builds()
                            )
                            for tech_type, base_supply, priority in recommendations:
                                await self.bot.aggressive_tech_builder.build_tech_aggressively(
                                    tech_type,
                                    lambda: self._build_tech(tech_type),
                                    base_supply,
                                    priority,
                                )
                except Exception as e:
                    success = False
                    if iteration % 200 == 0:
                        print(f"[WARNING] Aggressive Tech Builder error: {e}")
                finally:
                    self._logic_tracker.end_logic("AggressiveTech", start_time, success)

            # 6.5. 긴급 방어 로직 (Strategy Manager 연동)
            await self._handle_emergency_defense(iteration)

            # 7. Queen Manager (여왕 관리)
            await self._safe_manager_step(self.bot.queen_manager, iteration, "Queen Manager")

            # 8. Combat (전투) - 단일 호출 (방어 모드 자동 감지)
            await self._safe_manager_step(self.bot.combat, iteration, "Combat")

            # 9. Spell Units (Infestor/Viper)
            await self._safe_manager_step(
                getattr(self.bot, "spell_manager", None),
                iteration,
                "Spell manager",
                method_name="update",
            )

            # 10. Micro Control (마이크로 컨트롤)
            await self._safe_manager_step(self.bot.micro, iteration, "Micro")

            # 11. Rogue Tactics (이병렬 선수 전술 - 맹독충 드랍 등)
            if iteration % 8 == 0:  # 8프레임마다 실행
                await self._safe_manager_step(
                    getattr(self.bot, "rogue_tactics", None),
                    iteration,
                    "Rogue Tactics",
                    method_name="update",
                )

            # 12. Hierarchical RL System (계층적 강화학습 - 전략 결정)
            if iteration % 22 == 0:  # 매 1초마다 전략 결정
                await self._safe_hierarchical_rl_step(iteration)

            # 13. Transformer Decision (트랜스포머 의사결정 - 고급 패턴 인식)
            if iteration % 44 == 0:  # 매 2초마다
                await self._safe_transformer_step(iteration)

            # 14. 실시간 로직 활성화 보고
            game_time = getattr(self.bot, "time", 0)
            report = self._logic_tracker.get_activity_report(game_time)
            if report:
                print(report)

        except Exception as e:
            if iteration % 100 == 0:
                print(f"[WARNING] Game logic execution error: {e}")
        finally:
            # Performance Optimizer 프레임 종료
            if hasattr(self.bot, "performance_optimizer") and self.bot.performance_optimizer:
                try:
                    self.bot.performance_optimizer.end_frame()
                except Exception:
                    pass  # Silently ignore end_frame errors

    async def _safe_manager_step(
        self, manager, iteration: int, label: str, method_name: str = "on_step"
    ) -> None:
        if not manager:
            return
        method = getattr(manager, method_name, None)
        if not method:
            return

        start_time = self._logic_tracker.start_logic(label)
        success = True
        try:
            await method(iteration)
        except Exception as e:
            success = False
            if iteration % 200 == 0:
                print(f"[WARNING] {label} error: {e}")
        finally:
            self._logic_tracker.end_logic(label, start_time, success)

    async def _safe_hierarchical_rl_step(self, iteration: int) -> None:
        """계층적 강화학습 시스템 실행"""
        if not hasattr(self.bot, "hierarchical_rl") or self.bot.hierarchical_rl is None:
            return

        start_time = self._logic_tracker.start_logic("HierarchicalRL")
        success = True
        try:
            result = self.bot.hierarchical_rl.step(self.bot)

            # 전략 모드 저장 (다른 매니저에서 참조 가능)
            if result and "strategy_mode" in result:
                self.bot._current_strategy = result["strategy_mode"]

                # RLAgent 연동: 게임 상태와 선택된 전략을 기록
                if hasattr(self.bot, "rl_agent") and self.bot.rl_agent:
                    try:
                        import numpy as np
                        # 게임 상태 추출
                        game_state = np.array([
                            getattr(self.bot, "minerals", 0) / 2000.0,
                            getattr(self.bot, "vespene", 0) / 1000.0,
                            getattr(self.bot, "supply_used", 0) / 200.0,
                            getattr(self.bot, "supply_cap", 0) / 200.0,
                            len(getattr(self.bot, "workers", [])) / 100.0,
                            len(getattr(self.bot, "units", [])) / 100.0,
                            len(getattr(self.bot, "enemy_units", [])) / 100.0,
                            len(getattr(self.bot, "townhalls", [])) / 10.0,
                            getattr(self.bot, "time", 0) / 1000.0,
                            # 패딩 (15차원 맞추기)
                            0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                        ], dtype=np.float32)

                        # RLAgent에 상태와 행동 기록
                        self.bot.rl_agent.get_action(game_state)
                    except Exception as e:
                        if iteration % 500 == 0:
                            print(f"[WARNING] RLAgent state recording error: {e}")

                # 주기적으로 전략 로그 출력
                if iteration % 220 == 0:  # 10초마다
                    print(f"[HIERARCHICAL RL] Strategy: {result['strategy_mode']}")
        except Exception as e:
            success = False
            if iteration % 200 == 0:
                print(f"[WARNING] Hierarchical RL error: {e}")
        finally:
            self._logic_tracker.end_logic("HierarchicalRL", start_time, success)

    async def _safe_transformer_step(self, iteration: int) -> None:
        """트랜스포머 의사결정 모델 실행"""
        if not hasattr(self.bot, "transformer_model") or self.bot.transformer_model is None:
            return

        start_time = self._logic_tracker.start_logic("Transformer")
        success = True
        try:
            # 게임 상태를 시퀀스로 변환하여 트랜스포머에 입력
            game_state = self._extract_game_state_sequence()
            if game_state:
                prediction = self.bot.transformer_model.predict(game_state)

                # 예측 결과 저장
                if prediction:
                    self.bot._transformer_prediction = prediction
        except Exception as e:
            success = False
            if iteration % 200 == 0:
                print(f"[WARNING] Transformer model error: {e}")
        finally:
            self._logic_tracker.end_logic("Transformer", start_time, success)

    def _extract_game_state_sequence(self) -> list:
        """게임 상태를 시퀀스로 추출 (트랜스포머 입력용)"""
        try:
            sequence = []

            # 자원 상태
            sequence.append(getattr(self.bot, "minerals", 0) / 1000.0)
            sequence.append(getattr(self.bot, "vespene", 0) / 1000.0)

            # 서플라이 상태
            sequence.append(getattr(self.bot, "supply_used", 0) / 200.0)
            sequence.append(getattr(self.bot, "supply_cap", 0) / 200.0)

            # 유닛 수
            if hasattr(self.bot, "units"):
                sequence.append(len(self.bot.units) / 100.0)
            else:
                sequence.append(0.0)

            # 적 유닛 수
            if hasattr(self.bot, "enemy_units"):
                sequence.append(len(self.bot.enemy_units) / 100.0)
            else:
                sequence.append(0.0)

            # 게임 시간
            sequence.append(getattr(self.bot, "time", 0) / 1000.0)

            # 기지 수
            if hasattr(self.bot, "townhalls"):
                sequence.append(len(self.bot.townhalls) / 10.0)
            else:
                sequence.append(0.0)

            return sequence
        except Exception:
            return []

    def _is_defense_mode(self) -> bool:
        """방어 모드 여부 확인"""
        # Strategy Manager 확인
        if hasattr(self.bot, "strategy_manager") and self.bot.strategy_manager:
            from strategy_manager import StrategyMode
            if self.bot.strategy_manager.current_mode in [StrategyMode.EMERGENCY, StrategyMode.DEFENSIVE]:
                return True

        # Intel Manager 확인
        if hasattr(self.bot, "intel") and self.bot.intel:
            if hasattr(self.bot.intel, "is_major_attack") and self.bot.intel.is_major_attack():
                return True
            if hasattr(self.bot.intel, "is_under_attack") and self.bot.intel.is_under_attack():
                return True

        return False

    async def _handle_emergency_defense(self, iteration: int) -> None:
        """
        긴급 방어 로직 처리

        Strategy Manager가 Emergency/Defense 모드일 때:
        1. 긴급 스파인 크롤러 건설
        2. 긴급 스포어 크롤러 건설
        3. 방어 유닛 우선 생산 신호

        패배 직감 시스템 연동:
        - 패배 직전: 스파인 크롤러 최대 6개까지 긴급 건설
        - 위기 상황: 스파인 크롤러 4개까지 건설
        - 일반: 스파인 크롤러 3개까지 건설
        """
        if iteration % 22 != 0:  # 1초마다 확인
            return

        # Strategy Manager 확인
        strategy = getattr(self.bot, "strategy_manager", None)
        if not strategy:
            return

        game_time = getattr(self.bot, "time", 0)

        # ★ 패배 직감 시스템 연동 ★
        defeat_level = 0
        last_stand_mode = False
        if hasattr(self.bot, "defeat_detection") and self.bot.defeat_detection:
            defeat_status = self.bot.defeat_detection._get_current_status()
            defeat_level = defeat_status.get("defeat_level", 0)
            last_stand_mode = defeat_status.get("last_stand_required", False)

        try:
            # ★ 패배 직전: 스파인 크롤러 최대 6개 ★
            if last_stand_mode or defeat_level >= 3:
                max_spines = 6
                force_build = True
            # ★ 위기 상황: 스파인 크롤러 4개 ★
            elif defeat_level >= 2:
                max_spines = 4
                force_build = True
            # ★ 일반: 스파인 크롤러 3개 ★
            else:
                max_spines = 3
                force_build = False

            # 긴급 스파인 크롤러 건설
            if getattr(strategy, "emergency_spine_requested", False) or force_build:
                if hasattr(self.bot, "structures") and hasattr(self.bot, "townhalls"):
                    from sc2.ids.unit_typeid import UnitTypeId

                    # 스파인 크롤러 현재 수 확인
                    spines = self.bot.structures(UnitTypeId.SPINECRAWLER)
                    spine_count = spines.amount if hasattr(spines, 'amount') else 0
                    pending = self.bot.already_pending(UnitTypeId.SPINECRAWLER)

                    # 스포닝 풀 필요
                    pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
                    if pools.exists and spine_count + pending < max_spines and self.bot.can_afford(UnitTypeId.SPINECRAWLER):
                        if self.bot.townhalls.exists:
                            main_base = self.bot.townhalls.first
                            defense_pos = main_base.position.towards(self.bot.game_info.map_center, 7)
                            await self.bot.build(UnitTypeId.SPINECRAWLER, near=defense_pos)

                            if last_stand_mode:
                                print(f"[LAST STAND] [{int(game_time)}s] ★ 긴급 스파인 크롤러 건설! ({spine_count + pending + 1}/{max_spines}) ★")
                            else:
                                print(f"[EMERGENCY] [{int(game_time)}s] Building emergency Spine Crawler ({spine_count + pending + 1}/{max_spines})")

                            if hasattr(strategy, "emergency_spine_requested"):
                                strategy.emergency_spine_requested = False

            # 긴급 스포어 크롤러 건설 (대공)
            if getattr(strategy, "emergency_spore_requested", False):
                if hasattr(self.bot, "structures") and hasattr(self.bot, "townhalls"):
                    from sc2.ids.unit_typeid import UnitTypeId

                    spores = self.bot.structures(UnitTypeId.SPORECRAWLER)
                    spore_count = spores.amount if hasattr(spores, 'amount') else 0
                    pending = self.bot.already_pending(UnitTypeId.SPORECRAWLER)

                    pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
                    if pools.exists and spore_count + pending < 2 and self.bot.can_afford(UnitTypeId.SPORECRAWLER):
                        if self.bot.townhalls.exists:
                            main_base = self.bot.townhalls.first
                            await self.bot.build(UnitTypeId.SPORECRAWLER, near=main_base.position)
                            print(f"[EMERGENCY] [{int(game_time)}s] Building emergency Spore Crawler!")
                            strategy.emergency_spore_requested = False

            # === 공중 위협 대응: 히드라리스크 굴 건설 ===
            if hasattr(strategy, "is_air_threat_detected") and strategy.is_air_threat_detected():
                await self._build_anti_air_tech(iteration, game_time)

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Emergency defense error: {e}")

    async def _build_anti_air_tech(self, iteration: int, game_time: float) -> None:
        """
        공중 위협 대응 테크 건설 (강화 버전)

        우선순위:
        1. 스포어 크롤러 (모든 기지에 최소 1개, 위협시 2개)
        2. 레어 진화 (히드라 굴 전제 조건)
        3. 히드라리스크 굴 건설
        4. 퀸 추가 생산 요청
        """
        if not hasattr(self.bot, "structures"):
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId

            # === 0. 공중 위협 레벨 계산 ===
            air_threat_level = self._calculate_air_threat_level()

            # === 1. 스포어 크롤러 긴급 건설 (최우선) ===
            spore_target = 2 if air_threat_level >= 2 else 1  # 위협 높으면 기지당 2개

            # 성능 최적화: 루프 외부에서 한 번만 쿼리
            all_spores = self.bot.structures(UnitTypeId.SPORECRAWLER)
            pending_spores = self.bot.already_pending(UnitTypeId.SPORECRAWLER)
            pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready

            for th in self.bot.townhalls:
                # 캐싱된 spore 구조물에서 가까운 것만 필터링
                nearby_spores = all_spores.closer_than(15, th)
                spore_count = nearby_spores.amount if hasattr(nearby_spores, 'amount') else 0

                if spore_count + pending_spores < spore_target and self.bot.can_afford(UnitTypeId.SPORECRAWLER):
                    # 스포닝 풀 확인 (캐싱된 결과 사용)
                    if pools.exists:
                        # 미네랄 라인 근처에 배치 (일꾼 보호)
                        minerals = self.bot.mineral_field.closer_than(10, th)
                        if minerals:
                            mineral_center = minerals.center
                            defense_pos = th.position.towards(mineral_center, 4)
                        else:
                            defense_pos = th.position

                        await self.bot.build(UnitTypeId.SPORECRAWLER, near=defense_pos)
                        print(f"[ANTI-AIR] [{int(game_time)}s] ★ Building Spore Crawler (threat level: {air_threat_level}) ★")
                        return

            # === 2. 레어 진화 확인 (히드라 굴 전제 조건) ===
            lair = self.bot.structures(UnitTypeId.LAIR)
            hive = self.bot.structures(UnitTypeId.HIVE)
            has_lair_or_higher = lair.ready.exists or hive.ready.exists
            lair_pending = self.bot.already_pending(UnitTypeId.LAIR) > 0

            if not has_lair_or_higher and not lair_pending:
                # 해처리에서 레어 진화 시작
                hatcheries = self.bot.structures(UnitTypeId.HATCHERY).ready
                pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
                if hatcheries.exists and pools.exists and self.bot.can_afford(UnitTypeId.LAIR):
                    # idle 해처리 찾기
                    for hatch in hatcheries:
                        if hasattr(hatch, "is_idle") and hatch.is_idle:
                            self.bot.do(hatch(UnitTypeId.LAIR))
                            print(f"[ANTI-AIR] [{int(game_time)}s] ★ Upgrading to Lair for Hydralisk Den ★")
                            return

            # === 3. 히드라리스크 굴 건설 ===
            hydra_dens = self.bot.structures(UnitTypeId.HYDRALISKDEN)
            hydra_pending = self.bot.already_pending(UnitTypeId.HYDRALISKDEN)

            if not hydra_dens.exists and hydra_pending == 0:
                if has_lair_or_higher and self.bot.can_afford(UnitTypeId.HYDRALISKDEN):
                    if self.bot.townhalls.exists:
                        await self.bot.build(UnitTypeId.HYDRALISKDEN, near=self.bot.townhalls.first.position)
                        print(f"[ANTI-AIR] [{int(game_time)}s] ★★ Building Hydralisk Den for anti-air! ★★")
                        return

            # === 4. 히드라 우선 생산 플래그 설정 ===
            if hydra_dens.ready.exists:
                # Unit Factory에 히드라 우선 생산 신호
                if hasattr(self.bot, "unit_factory"):
                    self.bot.unit_factory._force_hydra = True

            # === 5. 퀸 추가 생산 요청 (대공 유닛) ===
            if air_threat_level >= 2:
                if hasattr(self.bot, "queen_manager"):
                    # 퀸 보너스 증가
                    self.bot.queen_manager.creep_queen_bonus = 4  # 3 → 4

        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Anti-air tech build error: {e}")

    def _calculate_air_threat_level(self) -> int:
        """
        공중 위협 레벨 계산

        Returns:
            0: 없음
            1: 낮음 (1-2 공중 유닛)
            2: 중간 (3-5 공중 유닛 또는 캐리어/무리군주)
            3: 높음 (6+ 공중 유닛 또는 다수 고위협 유닛)
        """
        if not hasattr(self.bot, "enemy_units"):
            return 0

        air_count = 0
        high_threat_air_count = 0

        high_threat_air = {"CARRIER", "TEMPEST", "MOTHERSHIP", "BATTLECRUISER", "BROODLORD", "VOIDRAY"}

        for enemy in self.bot.enemy_units:
            try:
                if getattr(enemy, "is_flying", False):
                    air_count += 1
                    enemy_type = getattr(enemy.type_id, "name", "").upper()
                    if enemy_type in high_threat_air:
                        high_threat_air_count += 1
            except Exception:
                continue

        # 위협 레벨 결정
        if air_count == 0:
            return 0
        elif high_threat_air_count >= 1 or air_count >= 6:
            return 3
        elif air_count >= 3:
            return 2
        else:
            return 1

    async def _build_tech(self, tech_type):
        """테크 건물 건설 헬퍼 함수"""
        if not hasattr(self.bot, "townhalls"):
            return False
        if not self.bot.townhalls.exists:
            return False

        main_base = self.bot.townhalls.first
        map_center = None
        if hasattr(self.bot, "game_info"):
            map_center = getattr(self.bot.game_info, "map_center", None)
        if map_center is None:
            map_center = main_base.position
        try:
            return await self.bot.build(
                tech_type,
                near=main_base.position.towards(map_center, 5),
            )
        except Exception:
            return False

    async def execute_training_logic(self, iteration: int):
        """훈련 로직 실행 (train_mode=True일 때만)"""
        if not self.bot.train_mode:
            return

        try:
            # 보상 시스템 계산
            if hasattr(self.bot, "_reward_system"):
                try:
                    step_reward = self.bot._reward_system.calculate_step_reward(
                        self.bot
                    )

                    # RL 에이전트 업데이트
                    if hasattr(self.bot, "rl_agent") and self.bot.rl_agent:
                        self.bot.rl_agent.update_reward(step_reward)

                    # 주기적으로 보상 로그 출력
                    if iteration % 500 == 0:
                        print(f"[TRAINING] Step reward: {step_reward:.3f}")

                except Exception as e:
                    if iteration % 200 == 0:
                        print(f"[WARNING] Training logic error: {e}")
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] Training execution error: {e}")

    async def on_step(self, iteration: int):
        """
        통합 on_step 메서드

        이 메서드는 WickedZergBotPro의 on_step에서 호출됩니다.
        """
        try:
            # 1. 매니저들 초기화 (첫 호출 시)
            await self.initialize_managers()

            # 2. 게임 로직 실행
            await self.execute_game_logic(iteration)

            # 3. 훈련 로직 실행 (train_mode=True일 때만)
            await self.execute_training_logic(iteration)

        except Exception as e:
            if iteration % 100 == 0:
                print(f"[ERROR] on_step execution error: {e}")
                import traceback

                traceback.print_exc()


def create_on_step_implementation(bot):
    """
    on_step 구현을 생성하는 팩토리 함수

    Usage:
        integrator = create_on_step_implementation(self)
        async def on_step(self, iteration: int):
            await integrator.on_step(iteration)
    """
    return BotStepIntegrator(bot)
