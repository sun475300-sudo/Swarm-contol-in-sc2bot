# -*- coding: utf-8 -*-
"""
Replay Learning Data Comparison Analysis and Learning - 5 Iterations

This script runs:
1. Replay comparison analysis (strategy_audit.py)
2. Replay build order learning (replay_build_order_learner.py)
3. Repeat 5 times
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple, List

def run_command(cmd: List[str], cwd: Path, description: str, timeout: int = 1800) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    print(f"\n{'='*70}")
    print(f"[STEP] {description}")
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
    print("? REPLAY LEARNING DATA COMPARISON ANALYSIS & LEARNING - 5 ITERATIONS")
    print("=" * 70)
    print("\nThis workflow will execute:")
    print("  1. Replay comparison analysis (strategy_audit.py)")
    print("  2. Replay build order learning (replay_build_order_learner.py)")
    print("  3. Repeat 5 times")
    print("=" * 70)
    
    strategy_audit = project_root / "local_training" / "strategy_audit.py"
    replay_learner = project_root / "local_training" / "scripts" / "replay_build_order_learner.py"
    
    if not strategy_audit.exists():
        print(f"[ERROR] Strategy audit script not found: {strategy_audit}")
        sys.exit(1)
    
    if not replay_learner.exists():
        print(f"[ERROR] Replay learner script not found: {replay_learner}")
        sys.exit(1)
    
    successful_iterations = 0
    
    for iteration in range(1, 6):
        print(f"\n\n{'#'*70}")
        print(f"# ITERATION {iteration} / 5")
        print(f"{'#'*70}\n")
        
        # Step 1: Replay comparison analysis
        print(f"\n[STEP 1] Running replay comparison analysis...")
        success1, _ = run_command(
            [sys.executable, str(strategy_audit)],
            project_root,
            f"Iteration {iteration} - Strategy Audit (Comparison Analysis)",
            timeout=1800  # 30 minutes
        )
        
        if success1:
            print(f"[SUCCESS] Comparison analysis completed for iteration {iteration}")
        else:
            print(f"[WARNING] Comparison analysis had issues in iteration {iteration}, continuing...")
        
        # Step 2: Replay build order learning
        print(f"\n[STEP 2] Running replay build order learning...")
        success2, _ = run_command(
            [sys.executable, str(replay_learner)],
            project_root,
            f"Iteration {iteration} - Replay Build Order Learning",
            timeout=1800  # 30 minutes
        )
        
        if success2:
            print(f"[SUCCESS] Build order learning completed for iteration {iteration}")
            print("[INFO] Learned parameters will be automatically applied via config.py")
        else:
            print(f"[WARNING] Build order learning had issues in iteration {iteration}, continuing...")
        
        if success1 and success2:
            successful_iterations += 1
        
        print(f"\n{'='*70}")
        print(f"? ITERATION {iteration} / 5 COMPLETED")
        print(f"   Comparison Analysis: {'?' if success1 else '??'}")
        print(f"   Build Order Learning: {'?' if success2 else '??'}")
        print(f"{'='*70}")
        
        if iteration < 5:
            print(f"\nWaiting 5 seconds before next iteration...")
            time.sleep(5)
    
    print(f"\n\n{'#'*70}")
    print("# ALL 5 ITERATIONS COMPLETED")
    print(f"{'#'*70}")
    print(f"\nSummary:")
    print(f"  - Successful iterations: {successful_iterations} / 5")
    print(f"  - Comparison analysis reports: local_training/comparison_reports/")
    print(f"  - Learned build orders: local_training/scripts/learned_build_orders.json")
    print(f"\nCheck results:")
    print(f"  python tools\\show_learning_rate.py")
    print(f"  python tools\\monitor_training_progress.py")
    print(f"\n{'#'*70}")

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
