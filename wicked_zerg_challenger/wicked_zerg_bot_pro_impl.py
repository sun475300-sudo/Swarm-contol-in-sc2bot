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

        # Step integrator initialization
        self._step_integrator = None

    async def on_start(self):
        """Called when the bot starts."""
        await super().on_start()
        # Step integrator initialization
        self._step_integrator = BotStepIntegrator(self)

    async def on_step(self, iteration: int):
        """
        Called every game step.

        This method executes actual game logic and training logic.
        """
        if self._step_integrator is None:
            self._step_integrator = BotStepIntegrator(self)

        # Execute integrated on_step
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
                # Calculate final reward
                if hasattr(self, '_reward_system'):
                    final_reward = self._reward_system.calculate_step_reward(self)

                    # RL agent final update
                    if hasattr(self, 'rl_agent') and self.rl_agent:
                        self.rl_agent.update_reward(final_reward)

                        # Save model
                        if hasattr(self.rl_agent, 'save_model'):
                            model_path = "local_training/models/zerg_net_model.pt"
                            self.rl_agent.save_model(model_path)
                            print(f"[TRAINING] Model saved to {model_path}")

                # Reset reward system
                if hasattr(self, '_reward_system'):
                    self._reward_system.reset()

            except Exception as e:
                print(f"[WARNING] Training end logic error: {e}")

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
