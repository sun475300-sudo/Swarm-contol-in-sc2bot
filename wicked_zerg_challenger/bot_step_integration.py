# -*- coding: utf-8 -*-
"""
Bot Step Integration - on_step 구현 통합 모듈

이 모듈은 WickedZergBotPro의 on_step 메서드를 구현하여
실제 게임 로직과 훈련 로직을 통합합니다.
"""

import asyncio
from typing import Any, Dict, Optional

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
    """

    def __init__(self, bot):
        self.bot = bot
        self._managers_initialized = False

    async def initialize_managers(self):
        """매니저들 초기화 (lazy loading)"""
        if self._managers_initialized:
            return

        try:
            # Economy Manager
            if self.bot.economy is None:
                try:
                    from economy_manager import EconomyManager

                    self.bot.economy = EconomyManager(self.bot)
                except ImportError:
                    pass

            # Production Manager
            if self.bot.production is None:
                try:
                    from local_training.production_resilience import (
                        ProductionResilience,
                    )

                    self.bot.production = ProductionResilience(self.bot)
                except ImportError:
                    pass

            # Combat Manager
            if self.bot.combat is None:
                try:
                    from combat_manager import CombatManager

                    self.bot.combat = CombatManager(self.bot)
                except ImportError:
                    pass

            # Intel Manager
            if self.bot.intel is None:
                try:
                    from intel_manager import IntelManager

                    self.bot.intel = IntelManager(self.bot)
                except ImportError:
                    pass

            # Scouting System
            if self.bot.scout is None:
                try:
                    from scouting_system import ScoutingSystem

                    self.bot.scout = ScoutingSystem(self.bot)
                except ImportError:
                    pass

            # Creep Manager
            if not hasattr(self.bot, "creep_manager"):
                try:
                    from creep_manager import CreepManager

                    self.bot.creep_manager = CreepManager(self.bot)
                except ImportError:
                    pass

            # Upgrade Manager
            if not hasattr(self.bot, "upgrade_manager"):
                try:
                    from upgrade_manager import EvolutionUpgradeManager

                    self.bot.upgrade_manager = EvolutionUpgradeManager(self.bot)
                except ImportError:
                    pass

            # Unit Factory (fallback production)
            if not hasattr(self.bot, "unit_factory"):
                try:
                    from unit_factory import UnitFactory

                    self.bot.unit_factory = UnitFactory(self.bot)
                except ImportError:
                    pass

            # Micro Controller
            if self.bot.micro is None:
                try:
                    from micro_controller import BoidsController

                    self.bot.micro = BoidsController(self.bot)
                except ImportError:
                    pass

            # Spell Unit Manager
            if not hasattr(self.bot, "spell_manager"):
                try:
                    from spell_unit_manager import SpellUnitManager

                    self.bot.spell_manager = SpellUnitManager(self.bot)
                except ImportError:
                    pass

            # Queen Manager
            if self.bot.queen_manager is None:
                try:
                    from queen_manager import QueenManager

                    self.bot.queen_manager = QueenManager(self.bot)
                except ImportError:
                    pass

            # Advanced Building Manager (최신 개선 사항)
            if not hasattr(self.bot, "advanced_building_manager"):
                try:
                    from local_training.advanced_building_manager import (
                        AdvancedBuildingManager,
                    )

                    self.bot.advanced_building_manager = AdvancedBuildingManager(
                        self.bot
                    )
                except ImportError:
                    pass

            # Aggressive Tech Builder (최신 개선 사항)
            if not hasattr(self.bot, "aggressive_tech_builder"):
                try:
                    from local_training.aggressive_tech_builder import (
                        AggressiveTechBuilder,
                    )

                    self.bot.aggressive_tech_builder = AggressiveTechBuilder(self.bot)
                except ImportError:
                    pass

            # Reward System (훈련 모드용)
            if self.bot.train_mode and not hasattr(self.bot, "_reward_system"):
                try:
                    from local_training.reward_system import ZergRewardSystem

                    self.bot._reward_system = ZergRewardSystem()
                except ImportError:
                    pass

            # RL Agent (훈련 모드용)
            if self.bot.train_mode and not hasattr(self.bot, "rl_agent"):
                try:
                    # RL Agent 클래스를 찾아서 초기화
                    # 실제 RL Agent 클래스 경로는 프로젝트 구조에 따라 다를 수 있음
                    from local_training.rl_agent import RLAgent

                    self.bot.rl_agent = RLAgent()
                except ImportError:
                    # RL Agent가 없으면 경고만 출력하고 계속 진행
                    iteration = getattr(self.bot, "iteration", 0)
                    if iteration % 500 == 0:
                        print(
                            "[WARNING] RL Agent not available, training will continue without RL updates"
                        )

            self._managers_initialized = True

        except Exception as e:
            iteration = getattr(self.bot, "iteration", 0)
            if iteration % 100 == 0:
                print(f"[WARNING] Failed to initialize some managers: {e}")

    async def execute_game_logic(self, iteration: int):
        """게임 로직 실행"""
        try:
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
                try:
                    # ProductionResilience의 메서드 호출
                    if hasattr(self.bot.production, "fix_production_bottleneck"):
                        await self.bot.production.fix_production_bottleneck()
                except Exception as e:
                    if iteration % 200 == 0:
                        print(f"[WARNING] Production error: {e}")

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
                    if iteration % 200 == 0:
                        print(f"[WARNING] Advanced Building Manager error: {e}")

            # 6. Aggressive Tech Builder (최신 개선 사항)
            if hasattr(self.bot, "aggressive_tech_builder"):
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
                    if iteration % 200 == 0:
                        print(f"[WARNING] Aggressive Tech Builder error: {e}")

            # 7. Queen Manager (여왕 관리)
            await self._safe_manager_step(self.bot.queen_manager, iteration, "Queen Manager")

            # 8. Combat (전투)
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

        except Exception as e:
            if iteration % 100 == 0:
                print(f"[WARNING] Game logic execution error: {e}")

    async def _safe_manager_step(
        self, manager, iteration: int, label: str, method_name: str = "on_step"
    ) -> None:
        if not manager:
            return
        method = getattr(manager, method_name, None)
        if not method:
            return
        try:
            await method(iteration)
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] {label} error: {e}")

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
