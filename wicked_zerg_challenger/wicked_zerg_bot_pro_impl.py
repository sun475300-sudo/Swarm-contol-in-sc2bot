# -*- coding: utf-8 -*-
"""
WickedZergBotPro Implementation - on_step implementation

This file implements the on_step method for WickedZergBotPro.
It can be integrated into the existing wicked_zerg_bot_pro.py file,
or imported and used separately.
"""

try:
    from sc2.bot_ai import BotAI
except ImportError:
    class BotAI:
        pass

from bot_step_integration import BotStepIntegrator
from utils.logger import setup_logger

class WickedZergBotProImpl(BotAI):
    """
    WickedZergBotPro on_step implementation.

    This class extends the existing WickedZergBotPro or
    can be integrated into the existing class.
    """

    def __init__(self, train_mode: bool = False, instance_id: int = 0,
                 personality: str = "serral", opponent_race=None,
                 game_count: int = 0):
        """Initialize WickedZergBotPro."""
        super().__init__()
        self.train_mode = train_mode
        self.instance_id = instance_id
        self.personality = personality
        self.opponent_race = opponent_race
        self.game_count = game_count

        # Initialize managers (lazy loading)
        self.intel = None
        self.economy = None
        self.production = None
        self.combat = None
        self.scout = None
        self.micro = None
        self.queen_manager = None

        # Advanced managers (initialized in on_start)
        self.strategy_manager = None       # Race-specific strategies + Emergency Mode
        self.performance_optimizer = None  # Distance caching + spatial indexing
        self.formation_controller = None   # PID-based smooth movement
        self.rogue_tactics = None          # Baneling drop + larva saving
        self.transformer_model = None      # Transformer decision model
        self.hierarchical_rl = None        # Hierarchical RL agent
        self.aggressive_strategies = None  # Early game aggressive strategies

        # Step integrator initialization
        self._step_integrator = None

    async def on_start(self):
        """
        Called when the bot starts.

        Initializes all managers:
        - Strategy Manager: Race-specific strategies, Emergency Mode
        - Performance Optimizer: Distance caching, spatial indexing
        - PID Controller: Smooth unit movement
        - Rogue Tactics: Baneling drop, larva saving
        - Transformer Model: Decision making (training mode)
        - ProductionResilience: Safe unit production with retry logic
        """
        await super().on_start()

        print("[BOT] on_start: Initializing all managers...")
        self.logger = setup_logger("WickedZergBot")
        self.logger.info("Bot started. Initializing managers...")

        # === 0. ProductionResilience (안전한 유닛 생산) ===
        try:
            from local_training.production_resilience import ProductionResilience
            self.production = ProductionResilience(self)
            print("[BOT] ProductionResilience initialized")
        except ImportError as e:
            print(f"[BOT_WARN] ProductionResilience not available: {e}")
            self.production = None

        # === 0.1 Basic Managers (Economy, Combat, Intel, Scout) ===
        try:
            from economy_manager import EconomyManager
            self.economy = EconomyManager(self)
            print("[BOT] EconomyManager initialized")
        except ImportError as e:
            print(f"[BOT_WARN] EconomyManager not available: {e}")

        try:
            from combat_manager import CombatManager
            self.combat = CombatManager(self)
            print("[BOT] CombatManager initialized")
        except ImportError as e:
            print(f"[BOT_WARN] CombatManager not available: {e}")

        try:
            from intel_manager import IntelManager
            self.intel = IntelManager(self)
            print("[BOT] IntelManager initialized")
        except ImportError as e:
            print(f"[BOT_WARN] IntelManager not available: {e}")

        try:
            from scouting_system import ScoutingSystem
            self.scout = ScoutingSystem(self)
            print("[BOT] ScoutingSystem initialized")
        except ImportError as e:
            print(f"[BOT_WARN] ScoutingSystem not available: {e}")

        # === 1. Strategy Manager (종족별 전략 + Emergency Mode) ===
        try:
            from strategy_manager import StrategyManager
            self.strategy_manager = StrategyManager(self)
            print("[BOT] StrategyManager initialized")
        except ImportError as e:
            print(f"[BOT_WARN] StrategyManager not available: {e}")
            self.strategy_manager = None

        # === 2. Performance Optimizer (거리 캐싱 + 공간 인덱싱) ===
        try:
            from local_training.performance_optimizer import PerformanceOptimizer
            self.performance_optimizer = PerformanceOptimizer(self)
            print("[BOT] PerformanceOptimizer initialized")
        except ImportError as e:
            print(f"[BOT_WARN] PerformanceOptimizer not available: {e}")
            self.performance_optimizer = None

        # === 3. PID Controller (부드러운 유닛 이동) ===
        try:
            from utils.pid_controller import FormationController
            self.formation_controller = FormationController()
            print("[BOT] PID FormationController initialized")
        except ImportError as e:
            print(f"[BOT_WARN] PID Controller not available: {e}")
            self.formation_controller = None

        # === 4. Rogue Tactics Manager (맹독충 드랍 + 라바 세이빙) ===
        try:
            from rogue_tactics_manager import RogueTacticsManager
            self.rogue_tactics = RogueTacticsManager(self)
            print("[BOT] RogueTacticsManager initialized")
        except ImportError as e:
            print(f"[BOT_WARN] RogueTacticsManager not available: {e}")
            self.rogue_tactics = None

        # === 5. Transformer Model (훈련 모드에서만) ===
        if self.train_mode:
            try:
                from local_training.transformer_model import TransformerDecisionModel
                self.transformer_model = TransformerDecisionModel()
                print("[BOT] TransformerDecisionModel initialized (training mode)")
            except ImportError as e:
                print(f"[BOT_WARN] TransformerModel not available: {e}")
                self.transformer_model = None
        else:
            self.transformer_model = None

        # === 6. Hierarchical RL (훈련 모드에서만) ===
        if self.train_mode:
            try:
                from local_training.hierarchical_rl.improved_hierarchical_rl import HierarchicalRLSystem
                self.hierarchical_rl = HierarchicalRLSystem()
                print("[BOT] HierarchicalRLSystem initialized (training mode)")
            except ImportError as e:
                print(f"[BOT_WARN] HierarchicalRL not available: {e}")
                self.hierarchical_rl = None
        else:
            self.hierarchical_rl = None

        # === 7. Aggressive Strategies (초반 공격 전략) ===
        try:
            from aggressive_strategies import AggressiveStrategyExecutor
            self.aggressive_strategies = AggressiveStrategyExecutor(self)
            print("[BOT] AggressiveStrategyExecutor initialized")
        except ImportError as e:
            print(f"[BOT_WARN] AggressiveStrategies not available: {e}")
            self.aggressive_strategies = None

        # === 8. Additional Managers (Creep, Upgrade, UnitFactory, Defeat, Micro, Spell, Queen) ===
        try:
            from creep_manager import CreepManager
            self.creep_manager = CreepManager(self)
        except ImportError:
            pass

        try:
            from upgrade_manager import EvolutionUpgradeManager
            self.upgrade_manager = EvolutionUpgradeManager(self)
        except ImportError:
            pass

        try:
            from unit_factory import UnitFactory
            self.unit_factory = UnitFactory(self)
        except ImportError:
            pass

        try:
            from defeat_detection import DefeatDetection
            self.defeat_detection = DefeatDetection(self)
        except ImportError:
            pass

        try:
            from micro_controller import BoidsController
            self.micro = BoidsController(self)
        except ImportError:
            pass

        try:
            from spell_unit_manager import SpellUnitManager
            self.spell_manager = SpellUnitManager(self)
        except ImportError:
            pass

        try:
            from queen_manager import QueenManager
            self.queen_manager = QueenManager(self)
        except ImportError:
            pass

        # === 9. Latest Improvements (AdvancedBuilding, AggressiveTech) ===
        try:
            from local_training.advanced_building_manager import AdvancedBuildingManager
            self.advanced_building_manager = AdvancedBuildingManager(self)
        except ImportError:
            pass

        try:
            from local_training.aggressive_tech_builder import AggressiveTechBuilder
            self.aggressive_tech_builder = AggressiveTechBuilder(self)
        except ImportError:
            pass

        # === 10. Training Components (Reward System, RL Agent, Adaptive LR) ===
        if self.train_mode:
            try:
                from local_training.reward_system import ZergRewardSystem
                self._reward_system = ZergRewardSystem()
            except ImportError:
                pass

            try:
                from adaptive_learning_rate import AdaptiveLearningRate
                self.adaptive_lr = AdaptiveLearningRate(
                    initial_lr=0.001,
                    min_lr=0.0001,
                    max_lr=0.01,
                    patience=10
                )
                print(f"[BOT] AdaptiveLearningRate initialized - LR: {self.adaptive_lr.get_current_lr():.6f}")
            except ImportError:
                print("[BOT_WARN] AdaptiveLearningRate not available")
                self.adaptive_lr = None

            try:
                from game_analytics_system import GameAnalytics
                self.game_analytics = GameAnalytics()
                print(f"[BOT] GameAnalytics initialized - {self.game_analytics.total_games} games tracked")
            except ImportError:
                print("[BOT_WARN] GameAnalytics not available")
                self.game_analytics = None

            try:
                from local_training.rl_agent import RLAgent
                # 적응형 학습률 사용
                initial_lr = self.adaptive_lr.get_current_lr() if self.adaptive_lr else 0.001
                self.rl_agent = RLAgent(learning_rate=initial_lr)
                print(f"[BOT] RL Agent initialized with LR: {initial_lr:.6f}")
            except ImportError:
                print("[WARNING] RL Agent not available, training will continue without RL updates")

        # === Step integrator initialization ===
        self._step_integrator = BotStepIntegrator(self)

        print(f"[BOT] on_start complete. Enemy race: {self.opponent_race}")

    async def on_step(self, iteration: int):
        """
        Called every game step.

        This method executes actual game logic and training logic.

        NOTE: 모든 매니저 호출은 BotStepIntegrator에서 처리됨
        - StrategyManager: 종족별 전략 + Emergency Mode
        - RogueTacticsManager: 맹독충 드랍 + 라바 세이빙
        - AggressiveStrategies: 초반 공격 전략 (12풀, 맹독충 올인 등)
        중복 호출 방지를 위해 여기서는 호출하지 않음
        """
        # Store iteration as attribute for other modules to access
        self.iteration = iteration

        # 전략 선택 (한 번만 실행)
        if self.aggressive_strategies and not self.aggressive_strategies._strategy_decided:
            enemy_race = str(getattr(self, "enemy_race", "Unknown"))
            self.aggressive_strategies.select_strategy(enemy_race)

        if self._step_integrator is None:
            self._step_integrator = BotStepIntegrator(self)

        # Execute integrated on_step (모든 핵심 매니저 포함)
        await self._step_integrator.on_step(iteration)

    async def on_end(self, game_result):
        """
        Called when the game ends.

        Args:
            game_result: Game result (Victory, Defeat, etc.)
        """
        await super().on_end(game_result)

        # Training mode: Calculate final reward and save model
        if self.train_mode:
            try:
                # Determine final reward based on game result
                result_str = str(game_result).upper()
                if "VICTORY" in result_str or "WIN" in result_str:
                    game_outcome_reward = 10.0  # 승리 보상
                elif "DEFEAT" in result_str or "LOSS" in result_str:
                    game_outcome_reward = -5.0  # 패배 페널티
                else:
                    game_outcome_reward = 0.0  # 무승부/기타

                # CRITICAL FIX: Initialize parameters_updated counter
                self.parameters_updated = 0

                # Determine if we won
                game_won = "VICTORY" in result_str or "WIN" in result_str

                # ★★★ Adaptive Learning Rate Update (최우선) ★★★
                if hasattr(self, 'adaptive_lr') and self.adaptive_lr:
                    new_lr = self.adaptive_lr.update(game_won)

                    # 학습률이 조정되었으면 RL Agent에 적용
                    if new_lr and hasattr(self, 'rl_agent') and self.rl_agent:
                        self.rl_agent.learning_rate = new_lr
                        print(f"[ADAPTIVE_LR] ✓ RL Agent 학습률 업데이트: {new_lr:.6f}")

                    # 10게임마다 통계 출력
                    if self.adaptive_lr.total_games % 10 == 0:
                        print(self.adaptive_lr.get_summary())

                # RL agent: end episode and perform learning (CRITICAL!)
                if hasattr(self, 'rl_agent') and self.rl_agent:
                    # End episode triggers backpropagation and weight update
                    training_stats = self.rl_agent.end_episode(final_reward=game_outcome_reward)

                    # Check if learning occurred (steps > 0 means rewards were collected)
                    if training_stats.get('steps', 0) > 0:
                        self.parameters_updated = 1  # Mark that learning occurred
                        print(f"[TRAINING] ✓ Neural network updated! Loss: {training_stats.get('loss', 0):.4f}, "
                              f"Avg Reward: {training_stats.get('avg_reward', 0):.3f}, "
                              f"Steps: {training_stats.get('steps', 0)}")
                    else:
                        print(f"[TRAINING] No learning this episode (no rewards collected)")

                    # Save model
                    if hasattr(self.rl_agent, 'save_model'):
                        model_path = "local_training/models/rl_agent_model.npz"
                        self.rl_agent.save_model(model_path)
                        print(f"[TRAINING] Model saved to {model_path}")

                # Reset reward system
                if hasattr(self, '_reward_system'):
                    self._reward_system.reset()

            except Exception as e:
                print(f"[WARNING] Training end logic error: {e}")
                import traceback
                traceback.print_exc()

        # ★★★ 커리큘럼 매니저: 승리/패배 기록 (종족별 추적 포함) ★★★
        try:
            from local_training.curriculum_manager import CurriculumManager

            curriculum = CurriculumManager()
            result_str = str(game_result).upper()

            # ★ 상대 종족 감지 ★
            opponent_race = None
            try:
                if hasattr(self, 'enemy_race') and self.enemy_race:
                    opponent_race = str(self.enemy_race).replace("Race.", "")
                elif hasattr(self, '_enemy_race'):
                    opponent_race = str(self._enemy_race).replace("Race.", "")
                # 적 유닛/건물에서 종족 추론
                elif hasattr(self, 'enemy_units') and self.enemy_units:
                    enemy_unit = self.enemy_units.first
                    if hasattr(enemy_unit, 'race'):
                        opponent_race = str(enemy_unit.race).replace("Race.", "")
                elif hasattr(self, 'enemy_structures') and self.enemy_structures:
                    enemy_struct = self.enemy_structures.first
                    if hasattr(enemy_struct, 'race'):
                        opponent_race = str(enemy_struct.race).replace("Race.", "")
            except Exception:
                pass

            if opponent_race:
                print(f"[RACE] 상대 종족: {opponent_race}")

            if "VICTORY" in result_str or "WIN" in result_str:
                promoted = curriculum.record_win(opponent_race)
                if promoted:
                    print("[CURRICULUM] ★★★ 다음 단계로 승격! ★★★")
            elif "DEFEAT" in result_str or "LOSS" in result_str:
                demoted = curriculum.record_loss(opponent_race)
                if demoted:
                    print("[CURRICULUM] 난이도 하향 - 연습 더 필요")

            # 현재 진행 상황 출력
            progress = curriculum.get_progress_info()
            print(f"[CURRICULUM] 현재 단계: {progress['level_name']} "
                  f"({progress['wins_at_current_level']}/{progress['wins_required']}승)")
            print(f"[CURRICULUM] 최종 목표: CheatInsane AI 격파!")

            # ★ 종족별 승률 출력 ★
            curriculum.print_race_stats()

        except Exception as e:
            print(f"[WARNING] Curriculum manager error: {e}")

        # ★★★ Game Analytics - 게임 결과 상세 분석 ★★★
        if hasattr(self, 'game_analytics') and self.game_analytics and self.train_mode:
            try:
                # 추가 통계 수집
                additional_stats = {
                    "worker_count": self.workers.amount if hasattr(self, 'workers') else 0,
                    "army_count": self.units.amount if hasattr(self, 'units') else 0,
                    "base_count": self.townhalls.amount if hasattr(self, 'townhalls') else 0,
                    "pool_timing": getattr(self, 'pool_timing', 0),
                    "first_expand_timing": getattr(self, 'first_expand_timing', 0),
                    "minerals": self.minerals if hasattr(self, 'minerals') else 0,
                    "vespene": self.vespene if hasattr(self, 'vespene') else 0,
                }

                # 게임 분석 기록
                self.game_analytics.record_game(
                    game_id=getattr(self, 'game_count', 0),
                    map_name=str(getattr(self, 'game_info', {}).get('map_name', 'Unknown')) if hasattr(self, 'game_info') else 'Unknown',
                    opponent_race=str(getattr(self, 'enemy_race', 'Unknown')).replace('Race.', ''),
                    difficulty='Easy',  # TODO: 실제 난이도 가져오기
                    result=str(game_result),
                    game_time=getattr(self, 'time', 0.0) if hasattr(self, 'time') else 0.0,
                    additional_stats=additional_stats
                )

                # 10게임마다 통계 요약 출력
                if self.game_analytics.total_games % 10 == 0:
                    print(self.game_analytics.get_summary())

                # 종족별 조언 (20게임마다)
                if self.game_analytics.total_games % 20 == 0:
                    opponent_race = str(getattr(self, 'enemy_race', 'Unknown')).replace('Race.', '')
                    advice = self.game_analytics.get_race_specific_advice(opponent_race)
                    if advice:
                        print(advice)

            except Exception as e:
                print(f"[WARNING] Game analytics error: {e}")

        # Store training result for run_with_training.py
        self._training_result = {
            "game_result": str(game_result),
            "game_time": getattr(self, 'time', 0.0) if hasattr(self, 'time') else 0.0,
            "build_order_score": getattr(self, 'build_order_score', None),
            "loss_reason": getattr(self, 'loss_reason', None),
            "parameters_updated": getattr(self, 'parameters_updated', 0)
        }


# How to integrate into existing WickedZergBotPro class:
#
# 1. Integrate into existing class:
#    from bot_step_integration import BotStepIntegrator
#
#    class WickedZergBotPro(BotAI):
#        def __init__(self, ...):
#            ...
#            self._step_integrator = None
#
#        async def on_step(self, iteration: int):
#            if self._step_integrator is None:
#                self._step_integrator = BotStepIntegrator(self)
#            await self._step_integrator.on_step(iteration)
#
# 2. Or inherit this class:
#    class WickedZergBotPro(WickedZergBotProImpl):
#        # Additional methods...
