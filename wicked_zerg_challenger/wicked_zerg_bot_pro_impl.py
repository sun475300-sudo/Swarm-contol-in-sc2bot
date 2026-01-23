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

        # === 0. ProductionResilience (안전한 유닛 생산) ===
        try:
            from local_training.production_resilience import ProductionResilience
            self.production = ProductionResilience(self)
            print("[BOT] ProductionResilience initialized")
        except ImportError as e:
            print(f"[BOT_WARN] ProductionResilience not available: {e}")
            self.production = None

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

                # RL agent: end episode and perform learning (CRITICAL!)
                if hasattr(self, 'rl_agent') and self.rl_agent:
                    # End episode triggers backpropagation and weight update
                    training_stats = self.rl_agent.end_episode(final_reward=game_outcome_reward)
                    print(f"[TRAINING] Episode ended - Loss: {training_stats.get('loss', 0):.4f}, "
                          f"Avg Reward: {training_stats.get('avg_reward', 0):.3f}, "
                          f"Steps: {training_stats.get('steps', 0)}")

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
