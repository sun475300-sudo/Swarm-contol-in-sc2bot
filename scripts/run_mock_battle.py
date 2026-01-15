# -*- coding: utf-8 -*-
"""
Run a mock battle simulation using BasicZergAgent and MockSC2Env.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.bot.agents.basic_zerg_agent import BasicZergAgent
from src.sc2_env.mock_env import MockSC2Env


def main() -> None:
    """Run mock battle simulation."""
    print("="*70)
    print("Mock Battle Simulation")
    print("="*70)
    print()
    
    env = MockSC2Env(initial_minerals=100, initial_gas=0)
    agent = BasicZergAgent()

    obs = env.reset()
    
    print(f"[Step {obs['step']:3d}] Initial State:")
    print(f"  Minerals: {obs['minerals']:3d} | Gas: {obs['gas']:3d}")
    print(f"  Supply: {obs['food_used']:2d}/{obs['food_cap']:2d} | Army: {obs['army_size']:2d}")
    print()
    
    for step in range(20):
        action = agent.on_step(obs)
        obs = env.step(action)
        
        print(f"[Step {obs['step']:3d}] Action: {action:15s} | "
              f"Minerals: {obs['minerals']:3d} | Gas: {obs['gas']:3d} | "
              f"Supply: {obs['food_used']:2d}/{obs['food_cap']:2d} | "
              f"Army: {obs['army_size']:2d}")
    
    print()
    print("="*70)
    print("Simulation Complete")
    print("="*70)


if __name__ == "__main__":
    main()
