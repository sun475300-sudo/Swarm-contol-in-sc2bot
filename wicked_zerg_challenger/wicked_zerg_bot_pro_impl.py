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
from typing import Optional
from blackboard import Blackboard

class WickedZergBotProImpl(BotAI):
    """
    WickedZergBotPro on_step implementation.

    This class extends the existing WickedZergBotPro or
    can be integrated into the existing class.
    """

    def __init__(self, train_mode: bool = False, instance_id: int = 0,
                 personality: str = "serral", opponent_race=None,
                 game_count: int = 0, learning_rate: Optional[float] = None):
        """Initialize WickedZergBotPro."""
        super().__init__()
        self.train_mode = train_mode
        self.instance_id = instance_id
        self.personality = personality
        self.opponent_race = opponent_race
        self.game_count = game_count
        self.learning_rate = learning_rate

        # Initialize managers (lazy loading)
        self.blackboard = Blackboard()     # ★ Blackboard (Single Source of Truth) ★
        self.defense_coordinator = None    # ★ DefenseCoordinator (Unified Defense) ★
        self.production_controller = None  # ★ ProductionController (Dynamic Authority) ★
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

        # === 0. Blackboard (Central State) ===
        # Already initialized in __init__, but logging here
        if self.blackboard:
             print("[BOT] ★ Blackboard active")

        # === 0.1 ProductionResilience (안전한 유닛 생산) ===
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
            
            # ★ NEW: Load previous intel data if available
            self.intel.load_data()
            
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
            from game_config import config
            # Blackboard와 Config 통합
            self.unit_factory = UnitFactory(self, blackboard=self.blackboard, config=config)
            print("[BOT] UnitFactory initialized with Blackboard integration")

        except ImportError as e:
            print(f"[BOT_WARN] UnitFactory not available: {e}")
            self.unit_factory = None

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

        # ★ NEW: Unit Morph Manager ★
        try:
            from unit_morph_manager import UnitMorphManager
            self.morph_manager = UnitMorphManager(self)
        except ImportError:
            pass

        # ★ NEW: RL Tech Adapter (적 테크 기반 강화학습 적응) ★
        try:
            from rl_tech_adapter import RLTechAdapter
            self.rl_tech_adapter = RLTechAdapter(self, intel_manager=self.intel, knowledge_manager=None)
            print("[BOT] ★ RLTechAdapter initialized (Enemy Tech RL Response)")
        except ImportError as e:
            print(f"[BOT_WARN] RLTechAdapter not available: {e}")
            self.rl_tech_adapter = None

        # ★ NEW: Micro Focus Mode (전투 상황 우선순위 동적 할당) ★
        try:
            from micro_focus_mode import MicroFocusMode
            self.micro_focus = MicroFocusMode(self)
            print("[BOT] ★ MicroFocusMode initialized (Combat Priority System)")
        except ImportError as e:
            print(f"[BOT_WARN] MicroFocusMode not available: {e}")
            self.micro_focus = None

        # ★ NEW: Dynamic Resource Balancer (자원 불균형 자동 조정) ★
        try:
            from dynamic_resource_balancer import DynamicResourceBalancer
            self.resource_balancer = DynamicResourceBalancer(self)
            print("[BOT] ★ DynamicResourceBalancer initialized (Auto Resource Balance)")
        except ImportError as e:
            print(f"[BOT_WARN] DynamicResourceBalancer not available: {e}")
            self.resource_balancer = None

        # ★ NEW: Protoss Counter System ★
        try:
            from protoss_counter_system import ProtossCounterSystem
            self.protoss_counter = ProtossCounterSystem(self)
        except ImportError:
            pass

        # ★ NEW: Multi-Base Defense System ★
        try:
            from multi_base_defense import MultiBaseDefense
            self.multi_base_defense = MultiBaseDefense(self)
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

            # ★★★ NEW: Victory/Defeat Conditions Learner ★★★
            try:
                from local_training.victory_conditions import VictoryConditionsLearner
                self._victory_learner = VictoryConditionsLearner()
                print("[BOT] VictoryConditionsLearner initialized")
            except ImportError as e:
                print(f"[BOT_WARN] VictoryConditionsLearner not available: {e}")
                self._victory_learner = None

            # ★★★ NEW: Defeat Analysis ★★★
            try:
                from local_training.defeat_analysis import DefeatAnalysis
                self._defeat_analyzer = DefeatAnalysis()
                print("[BOT] DefeatAnalysis initialized")
            except ImportError as e:
                print(f"[BOT_WARN] DefeatAnalysis not available: {e}")
                self._defeat_analyzer = None

            try:
                from adaptive_learning_rate import AdaptiveLearningRate
                
                # Determine LR settings
                initial_lr = 0.001
                max_lr = 0.01
                if self.learning_rate is not None:
                    initial_lr = self.learning_rate
                    max_lr = max(max_lr, self.learning_rate)
                    print(f"[BOT] Helper: Using manual learning rate: {self.learning_rate}")

                self.adaptive_lr = AdaptiveLearningRate(
                    initial_lr=initial_lr,
                    min_lr=0.0001,
                    max_lr=max_lr,
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

            # RL Agent - Re-enabled with Epsilon-Greedy (2026-01-25 FIXED)
            try:
                from local_training.rl_agent import RLAgent
                # 적응형 학습률 사용
                initial_lr = self.adaptive_lr.get_current_lr() if self.adaptive_lr else 0.001
                self.rl_agent = RLAgent(learning_rate=initial_lr)

                # 배포 가능 여부 확인
                ready, reason = self.rl_agent.is_ready_for_deployment()
                if ready:
                    print(f"[BOT] RL Agent READY (Episodes: {self.rl_agent.episode_count}, ε={self.rl_agent.epsilon:.3f})")
                else:
                    print(f"[BOT] RL Agent TRAINING (Episodes: {self.rl_agent.episode_count}, ε={self.rl_agent.epsilon:.3f})")
                    print(f"[BOT]   Status: {reason}")
            except ImportError as e:
                print(f"[WARNING] RL Agent not available: {e}")
                self.rl_agent = None

        # === DefenseCoordinator (통합 방어 시스템) ===
        # === DefenseCoordinator (통합 방어 시스템) ===
        try:
            from local_training.defense_coordinator import DefenseCoordinator
            self.defense_coordinator = DefenseCoordinator(self)
            print("[BOT] ★ DefenseCoordinator initialized (Unified Defense)")
        except ImportError as e:
            print(f"[BOT_WARN] DefenseCoordinator not available: {e}")
            self.defense_coordinator = None

        # === ProductionController (통합 생산 관리) ===
        try:
            from production_controller import ProductionController
            self.production_controller = ProductionController(self, self.blackboard)
            print("[BOT] ★ ProductionController initialized (Dynamic Authority)")
        except ImportError as e:
            print(f"[BOT_WARN] ProductionController not available: {e}")
            self.production_controller = None

        # === Step integrator initialization ===
        self._step_integrator = BotStepIntegrator(self)

        # ★★★ 학습된 데이터 적용 (모든 매니저 초기화 완료 후) ★★★
        try:
            if hasattr(self, 'economy') and hasattr(self.economy, 'balancer'):
                self.economy.balancer.apply_learned_economy_weights()
                print("[BOT] [OK] Applied learned economy fundamentals to EconomyCombatBalancer")
        except Exception as e:
            print(f"[BOT] [WARNING] Failed to apply learned economy weights: {e}")

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
        # ★★★ 시간 제한: 5분(300초) 강제 종료 (빠른 학습) ★★★
        if self.time > 300:
            if not hasattr(self, '_game_ended'):
                self._game_ended = True
                print(f"[GAME] Time limit reached ({int(self.time)}s). Surrendering for fast training.")
                await self.client.leave()
            return

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
        Handles result logging, reward calculation, and curriculum updates.
        """
        print(f"[BOT] Game ended with result: {game_result}")

        # ★ NEW: Save intel data for next game
        if self.intel:
             self.intel.save_data()

        # Performance Optimizer cleanup
        # if self.performance_optimizer:
        #     self.performance_optimizer.on_end(game_result)  # Method doesn't exist

        await super().on_end(game_result)

        # Training mode: Calculate final reward and save model
        if self.train_mode:
            try:
                # ★★★ NEW: Analyze victory/defeat conditions for detailed reward ★★★
                result_str = str(game_result).upper()
                game_won = "VICTORY" in result_str or "WIN" in result_str
                game_lost = "DEFEAT" in result_str or "LOSS" in result_str

                # Default rewards
                game_outcome_reward = 0.0

                # Use VictoryConditionsLearner for detailed analysis
                if hasattr(self, '_victory_learner') and self._victory_learner:
                    if game_won:
                        conditions, reward = self._victory_learner.analyze_game_result(self, "Victory")
                        game_outcome_reward = reward
                        print(f"\n[VICTORY] Conditions met: {', '.join(conditions)}")
                        print(f"[VICTORY] Total reward: {reward:.1f}")
                    elif game_lost:
                        conditions, penalty = self._victory_learner.analyze_game_result(self, "Defeat")
                        game_outcome_reward = penalty
                        print(f"\n[DEFEAT] Conditions: {', '.join(conditions)}")
                        print(f"[DEFEAT] Total penalty: {penalty:.1f}")

                    # 통계 출력 (10게임마다)
                    total_games = len(self._victory_learner.victory_patterns) + len(self._victory_learner.defeat_patterns)
                    if total_games % 10 == 0 and total_games > 0:
                        self._victory_learner.print_analysis()
                else:
                    # Fallback: Simple reward
                    if game_won:
                        game_outcome_reward = 10.0
                    elif game_lost:
                        game_outcome_reward = -5.0

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
                        print(f"[ADAPTIVE_LR] [OK] RL Agent 학습률 업데이트: {new_lr:.6f}")

                    # 10게임마다 통계 출력
                    if self.adaptive_lr.total_games % 10 == 0:
                        print(self.adaptive_lr.get_summary())

                # RL agent: end episode and perform learning (CRITICAL!)
                if hasattr(self, 'rl_agent') and self.rl_agent:
                    # End episode triggers backpropagation and weight update
                    # (경험 데이터는 end_episode 내부에서 자동 저장)
                    training_stats = self.rl_agent.end_episode(final_reward=game_outcome_reward, save_experience=True)

                    # Check if learning occurred (steps > 0 means rewards were collected)
                    if training_stats.get('steps', 0) > 0:
                        self.parameters_updated = 1  # Mark that learning occurred
                        print(f"[TRAINING] [OK] Neural network updated!")
                        print(f"  Loss: {training_stats.get('loss', 0):.4f}, Avg Reward: {training_stats.get('avg_reward', 0):.3f}")
                        print(f"  Steps: {training_stats.get('steps', 0)}, ε={training_stats.get('epsilon', 0):.3f}, LR={training_stats.get('learning_rate', 0):.6f}")
                    else:
                        print(f"[TRAINING] No learning this episode (no rewards collected)")

                    # 모델 검증 (게임 결과 기록)
                    game_time = getattr(self, 'time', 0)
                    self.rl_agent.validate(game_won, game_time)

                    # 배포 가능 여부 확인 (10 게임마다)
                    if self.rl_agent.episode_count % 10 == 0:
                        ready, reason = self.rl_agent.is_ready_for_deployment()
                        if ready:
                            print(f"[RL_AGENT] ★ MODEL READY FOR DEPLOYMENT ★")
                        else:
                            print(f"[RL_AGENT] Training progress: {reason}")

                    # Save model
                    if hasattr(self.rl_agent, 'save_model'):
                        model_path = "local_training/models/rl_agent_model.npz"
                        self.rl_agent.save_model(model_path)

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
