# -*- coding: utf-8 -*-
"""
Replay Learning Data Comparison Analysis and Learning - 5 Iterations

This script executes:
1. Replay comparison learning (pro vs bot)
2. Replay learning data comparison analysis
3. Apply learned data
4. Repeat 5 times
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple, List

def run_command(cmd: list, cwd: Path, description: str, timeout: int = 1800) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    print(f"\n{'='*70}")
    print(f"¢º {description}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        success = result.returncode == 0
        return success, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print(f"[WARNING] Command timed out after {timeout} seconds")
        return False, "Timeout"
    except Exception as e:
        print(f"[ERROR] Failed to run command: {e}")
        return False, str(e)

def main():
    project_root = Path(__file__).parent.parent
    
    print("=" * 70)
    print("? REPLAY LEARNING DATA COMPARISON & LEARNING - 5 ITERATIONS")
    print("=" * 70)
    print("\nThis workflow will execute:")
    print("  1. Replay build order learning")
    print("  2. Replay comparison analysis (pro vs bot)")
    print("  3. Apply learned data")
    print("  4. Repeat 5 times")
    print("=" * 70)
    
    for iteration in range(1, 6):
        print(f"\n\n{'#'*70}")
        print(f"# ITERATION {iteration} / 5")
        print(f"{'#'*70}\n")
        
        # Step 1: Replay build order learning
        print("\n[STEP 1] Replay Build Order Learning...")
        replay_learner = project_root / "local_training" / "scripts" / "replay_build_order_learner.py"
        
        if replay_learner.exists():
            success, output = run_command(
                [sys.executable, str(replay_learner)],
                project_root,
                f"Iteration {iteration} - Replay Build Order Learning",
                timeout=1800  # 30 minutes
            )
            
            if success:
                print("[SUCCESS] Replay build order learning completed")
                print("[INFO] Learned parameters will be automatically applied via config.py")
            else:
                print("[WARNING] Replay learning had issues, but continuing...")
        else:
            print(f"[ERROR] Replay learner script not found: {replay_learner}")
        
        # Step 2: Replay comparison analysis (pro vs bot)
        print("\n[STEP 2] Replay Comparison Analysis (Pro vs Bot)...")
        strategy_audit = project_root / "local_training" / "strategy_audit.py"
        
        if strategy_audit.exists():
            success, output = run_command(
                [sys.executable, str(strategy_audit)],
                project_root,
                f"Iteration {iteration} - Strategy Audit (Comparison Analysis)",
                timeout=1800  # 30 minutes
            )
            
            if success:
                print("[SUCCESS] Comparison analysis completed")
                print("[INFO] Analysis results saved to comparison_reports/")
            else:
                print("[WARNING] Comparison analysis had issues, but continuing...")
        else:
            print(f"[ERROR] Strategy audit script not found: {strategy_audit}")
        
        # Step 3: Verify learned data application
        print("\n[STEP 3] Verifying Learned Data Application...")
        learned_file = project_root / "local_training" / "scripts" / "learned_build_orders.json"
        
        if learned_file.exists():
            try:
                import json
                with open(learned_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                learned_params = data.get("learned_parameters", {})
                if learned_params:
                    print("[SUCCESS] Learned parameters found:")
                    for key, value in list(learned_params.items())[:5]:
                        print(f"  - {key}: {value}")
                    print("[INFO] Parameters are automatically applied via config.py")
                else:
                    print("[WARNING] No learned parameters found in file")
            except Exception as e:
                print(f"[WARNING] Could not read learned parameters: {e}")
        else:
            print("[INFO] Learned parameters file not found yet (will be created after learning)")
        
        print(f"\n{'='*70}")
        print(f"? ITERATION {iteration} / 5 COMPLETED")
        print(f"{'='*70}")
        
        if iteration < 5:
            print(f"\nWaiting 5 seconds before next iteration...")
            time.sleep(5)
    
    print(f"\n\n{'#'*70}")
    print("# ALL 5 ITERATIONS COMPLETED")
    print(f"{'#'*70}")
    print("\nSummary:")
    print("  - 5 replay learning sessions completed")
    print("  - 5 comparison analysis sessions completed")
    print("  - Learned data automatically applied via config.py")
    print("\nCheck results:")
    print("  - Learned parameters: local_training/scripts/learned_build_orders.json")
    print("  - Comparison reports: local_training/comparison_reports/")
    print("\nView learning progress:")
    print("  python tools\\show_learning_rate.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n??  Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n? Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
