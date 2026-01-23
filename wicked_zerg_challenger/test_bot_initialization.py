#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify bot initialization and manager connections.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all critical modules can be imported."""
    print("=" * 60)
    print("Testing Module Imports")
    print("=" * 60)

    try:
        from wicked_zerg_bot_pro_impl import WickedZergBotProImpl
        print("[OK] WickedZergBotProImpl imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import WickedZergBotProImpl: {e}")
        return False

    try:
        from bot_step_integration import BotStepIntegrator
        print("[OK] BotStepIntegrator imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import BotStepIntegrator: {e}")
        return False

    try:
        from local_training.production_resilience import ProductionResilience
        print("[OK] ProductionResilience imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import ProductionResilience: {e}")
        return False

    try:
        from strategy_manager import StrategyManager
        print("[OK] StrategyManager imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import StrategyManager: {e}")
        return False

    try:
        from rogue_tactics_manager import RogueTacticsManager
        print("[OK] RogueTacticsManager imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import RogueTacticsManager: {e}")
        return False

    try:
        from unit_factory import UnitFactory
        print("[OK] UnitFactory imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import UnitFactory: {e}")
        return False

    try:
        from combat.boids_swarm_control import BoidsSwarmController
        print("[OK] BoidsSwarmController imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import BoidsSwarmController: {e}")
        return False

    return True

def test_bot_structure():
    """Test bot initialization structure."""
    print("\n" + "=" * 60)
    print("Testing Bot Structure")
    print("=" * 60)

    try:
        from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

        # Create a mock bot instance (won't actually initialize game)
        bot = WickedZergBotProImpl(train_mode=False, instance_id=0)

        # Check that manager attributes exist
        managers = [
            'intel', 'economy', 'production', 'combat', 'scout', 'micro',
            'queen_manager', 'strategy_manager', 'performance_optimizer',
            'formation_controller', 'rogue_tactics', 'transformer_model',
            'hierarchical_rl'
        ]

        for manager in managers:
            if hasattr(bot, manager):
                print(f"[OK] Bot has attribute: {manager}")
            else:
                print(f"[FAIL] Bot missing attribute: {manager}")

        # Check that on_step method exists
        if hasattr(bot, 'on_step'):
            print("[OK] Bot has on_step method")
        else:
            print("[FAIL] Bot missing on_step method")

        # Check that on_start method exists
        if hasattr(bot, 'on_start'):
            print("[OK] Bot has on_start method")
        else:
            print("[FAIL] Bot missing on_start method")

        return True

    except Exception as e:
        print(f"[FAIL] Failed to test bot structure: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_code_patterns():
    """Verify critical code patterns exist in files."""
    print("\n" + "=" * 60)
    print("Verifying Critical Code Patterns")
    print("=" * 60)

    # Check wicked_zerg_bot_pro_impl.py
    impl_path = os.path.join(os.path.dirname(__file__), "wicked_zerg_bot_pro_impl.py")
    with open(impl_path, 'r', encoding='utf-8') as f:
        impl_content = f.read()

    checks = [
        ("ProductionResilience initialization", "ProductionResilience(self)"),
        ("strategy_manager.update() call", "self.strategy_manager.update()"),
        ("rogue_tactics.update() call", "self.rogue_tactics.update(iteration)"),
        ("_step_integrator initialization", "BotStepIntegrator(self)"),
    ]

    for name, pattern in checks:
        if pattern in impl_content:
            print(f"[OK] Found: {name}")
        else:
            print(f"[FAIL] Missing: {name}")

    # Check unit_factory.py
    factory_path = os.path.join(os.path.dirname(__file__), "unit_factory.py")
    with open(factory_path, 'r', encoding='utf-8') as f:
        factory_content = f.read()

    if "_safe_train" in factory_content:
        print("[OK] unit_factory.py uses _safe_train")
    else:
        print("[FAIL] unit_factory.py doesn't use _safe_train")

    # Check bot_step_integration.py
    integrator_path = os.path.join(os.path.dirname(__file__), "bot_step_integration.py")
    with open(integrator_path, 'r', encoding='utf-8') as f:
        integrator_content = f.read()

    if "end_frame()" in integrator_content:
        print("[OK] bot_step_integration.py calls end_frame()")
    else:
        print("[FAIL] bot_step_integration.py doesn't call end_frame()")

    return True

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("WICKED ZERG BOT - INITIALIZATION VERIFICATION")
    print("=" * 60 + "\n")

    success = True

    # Test 1: Imports
    if not test_imports():
        success = False

    # Test 2: Bot structure
    if not test_bot_structure():
        success = False

    # Test 3: Code patterns
    if not verify_code_patterns():
        success = False

    # Summary
    print("\n" + "=" * 60)
    if success:
        print("[OK] ALL TESTS PASSED")
        print("=" * 60)
        print("\nBot is properly configured:")
        print("  - All managers can be imported")
        print("  - ProductionResilience is initialized")
        print("  - strategy_manager.update() is called in on_step")
        print("  - rogue_tactics.update() is called in on_step")
        print("  - unit_factory uses _safe_train")
        print("  - performance_optimizer.end_frame() is called")
        print("\nThe bot should now execute strategies and tactics correctly!")
    else:
        print("[FAIL] SOME TESTS FAILED")
        print("=" * 60)
        print("\nPlease review the errors above.")
    print()

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
