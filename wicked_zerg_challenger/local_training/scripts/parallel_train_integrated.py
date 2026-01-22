#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrated parallel training launcher (simplified).

Launches multiple training instances with staggered starts.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def get_python_executable() -> str:
    venv_dir = os.environ.get("VENV_DIR")
    if venv_dir:
        candidate = Path(venv_dir)
        py = candidate / ("Scripts" if sys.platform == "win32" else "bin") / "python"
        if py.exists():
            return str(py)
    return sys.executable


def launch_instances(
    instances: int,
    main_file: str,
    start_interval: int,
    show_window: bool,
    headless: bool,
) -> None:
    python_exec = get_python_executable()
    processes = []

    for idx in range(instances):
        env = os.environ.copy()
        env["INSTANCE_ID"] = str(idx)
        env["SHOW_WINDOW"] = "true" if show_window else "false"
        env["HEADLESS_MODE"] = "true" if headless else "false"

        cmd = [python_exec, main_file]
        processes.append(subprocess.Popen(cmd, env=env))
        print(f"[LAUNCH] Instance {idx} -> {main_file}")

        if idx < instances - 1:
            time.sleep(start_interval)

    for proc in processes:
        proc.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel training launcher")
    parser.add_argument("--instances", type=int, default=1, help="Number of instances")
    parser.add_argument(
        "--main-file", default="main_integrated.py", help="Training entry file"
    )
    parser.add_argument(
        "--start-interval", type=int, default=15, help="Seconds between launches"
    )
    parser.add_argument("--show-window", action="store_true", help="Show game windows")
    parser.add_argument("--headless", action="store_true", help="Headless mode")
    args = parser.parse_args()

    launch_instances(
        instances=max(1, args.instances),
        main_file=args.main_file,
        start_interval=max(0, args.start_interval),
        show_window=args.show_window,
        headless=args.headless,
    )

<<<<<<< Current (Your changes)
 # Total stats

 total_games = total_wins + total_losses

 win_rate = (total_wins / total_games * 100) if total_games > 0 else 0.0

 # GPU temperature

 gpu_temp = get_gpu_temperature()

     temp_str = f" | GPU Temp: {int(gpu_temp)}Â¡ÃC" if gpu_temp else ""

 total_line = (
     f"TOTAL STATS: {total_wins}W / {total_losses}L (Win Rate: {win_rate:.1f}%){temp_str}"
 )

 lines.append(total_line)

 # Clear previous lines and display new dashboard

 # Move cursor up (one line per instance + separator + total)

 num_lines = len(lines)

     dashboard_text = "\n".join(lines) + "\n"

 # Use ANSI escape codes to clear and redraw

     sys.stdout.write(f"\033[{num_lines}A")  # Move up

     sys.stdout.write("\033[J")  # Clear from cursor to end

 sys.stdout.write(dashboard_text)

 sys.stdout.flush()

 except Exception as e:
     # Silently fail - dashboard is optional

 pass

def check_requirements():
    """

 Check system requirements and adjust instance count

 Returns:

 tuple: (requirements_ok, safe_instance_count, gpu_name)

    """

    print("\n" + "=" * 70)

    print("[CHECK] Checking system requirements...")

    print("=" * 70)

 # Check GPU memory

 is_gpu, total_vram, available_vram, recommended, gpu_name = check_gpu_memory()

 if is_gpu:
     print(f"\n[GPU] GPU Available: {gpu_name}")

     print(f"[GPU] Total VRAM: {total_vram:.2f} GB")

     print(f"[GPU] Available VRAM: {available_vram:.2f} GB")

     print(f"[GPU] Recommended Instances: {recommended}")

 if recommended < NUM_INSTANCES:
     print(f"\n[WARNING] GPU memory insufficient for {NUM_INSTANCES} instances")

     print(f"[INFO] Adjusting to {recommended} instances for safety")

     print(f"[INFO] Each instance uses ~{ESTIMATED_VRAM_PER_INSTANCE:.1f}GB VRAM")

 return True, recommended, gpu_name

 else:
     print(f"\n[SUCCESS] GPU memory sufficient for {NUM_INSTANCES} instances")

 return True, NUM_INSTANCES, gpu_name

 else:
     print("\n[INFO] Running in CPU mode - using default instance count")

     return True, NUM_INSTANCES, "CPU"

def start_parallel_training():
    """

 Start parallel training with Resource-Aware Scheduling

 Launch multiple game instances sequentially (Staggered Launch) to prevent:

 - Shader compilation spikes (1.5-2x resource usage during initial loading)

 - System thrashing (CPU/RAM/GPU bottleneck)

 - GPU memory overflow

 GPU memory is dynamically calculated and instance count is automatically adjusted.

    """

 # ============================================================================
 # 0. AUTO-START MONITORING (·ÎÄÃ + ¿ø°Ý)
 # ============================================================================
    print("\n" + "="*70)
    print("? Starting monitoring systems...")
    print("="*70)

 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     # Local dashboard server
     print("[1/2] Starting local dashboard (http://localhost:8000)...")
 dashboard_proc = subprocess.Popen(
     [PYTHON_EXECUTABLE, "monitoring/dashboard.py"],
 cwd = PROJECT_ROOT.parent,
 stdout = subprocess.DEVNULL,
 stderr = subprocess.DEVNULL,
     creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
 )
     print(f"      ? Dashboard started (PID: {dashboard_proc.pid})")
 time.sleep(2) # Wait for server to start

 # Ngrok remote access
     print("[2/2] Starting ngrok tunnel for remote access...")
     ngrok_cmd = "start_with_ngrok.bat" if sys.platform == "win32" else "./start_with_ngrok.sh"
 ngrok_proc = subprocess.Popen(
 ngrok_cmd,
 cwd = PROJECT_ROOT,
 stdout = subprocess.DEVNULL,
 stderr = subprocess.DEVNULL,
 shell = True,
     creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
 )
     print(f"      ? Ngrok tunnel started (PID: {ngrok_proc.pid})")
     print("\n" + "="*70)
     print("? Monitoring active!")
     print("   Local:  http://localhost:8000")
     print("   Remote: Check .dashboard_port file or ngrok web UI")
     print("="*70 + "\n")
 except Exception as e:
     print(f"??  Failed to start monitoring: {e}")
     print("   Continuing with training without remote access...\n")

 requirements_ok, safe_instance_count, gpu_name = check_requirements()

 if not requirements_ok:
     print("[ERROR] Requirements check failed. Aborting.")

 return

 # Use safe instance count

 actual_instances = safe_instance_count

 processes = []

    print("\n" + "=" * 70)

    print(f"[PARALLEL TRAINING] Starting {actual_instances} game sessions")

    print("=" * 70)

    print(f"  Bot: WickedZergBotPro vs Computer (CheatInsane)")

    print(f"  GPU: {gpu_name}")

    print(f"  Start Interval: {START_INTERVAL} seconds (Staggered Launch)")

    print(f"  VRAM per Instance: ~{ESTIMATED_VRAM_PER_INSTANCE:.1f} GB")

    print(f"  Mode: Continuous training (infinite loop)")

 # Note: realtime is always False in main_integrated.py for maximum training speed

 # SHOW_WINDOW only controls window visibility, not realtime mode

 print(
     f"  Performance: realtime = False (Maximum Speed) - Window: {'Visible' if SHOW_WINDOW else 'Hidden'}"
 )

    print(f"  Display: {'Windows Visible' if SHOW_WINDOW else 'Headless (Hidden)'}")

 if actual_instances != NUM_INSTANCES:
     print(f"  GPU Memory Safety: Adjusted from {NUM_INSTANCES} to {actual_instances} instances")

    print("=" * 70 + "\n")

 # Get absolute path to main file

 main_path = PROJECT_ROOT / MAIN_FILE

 if not main_path.exists():
     print(f"[ERROR] {MAIN_FILE} not found at {main_path}")

 return

 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     for i in range(actual_instances):
         print(f"[{i + 1}/{actual_instances}] Launching instance #{i + 1}...")

 # Prepare environment variables

 env = os.environ.copy()

 # Pass instance ID for status file naming

     env["INSTANCE_ID"] = str(i + 1)

 # RTX 2060 optimization: First instance visual, rest headless (unless all visual requested)

 if i == 0 and actual_instances > 1:
     # First instance: Visual mode (for monitoring)

     env["SHOW_WINDOW"] = "true"

 else:
 # Other instances: Headless (for performance)

     env["SHOW_WINDOW"] = "true" if SHOW_WINDOW else "false"

 # Fix protobuf compatibility issue (Python 3.14+)

     if os.environ.get("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "").lower() != "cpp":
         pass
     env["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = os.environ.get(
     "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python"
 )

     sc2_path = os.environ.get("SC2PATH")
 if not sc2_path:
     from pathlib import Path
 default_paths = []
     if sys.platform == "win32":
         pass
     default_paths = [
     r"C:\Program Files (x86)\StarCraft II",
     r"C:\Program Files\StarCraft II",
 ]
     elif sys.platform == "darwin":
         pass
     default_paths = [
     os.path.expanduser("~/Library/Application Support/Blizzard/StarCraft II"),
     "/Applications/StarCraft II",
 ]
 else:
     pass
 default_paths = [
     os.path.expanduser("~/StarCraft II"),
     "/opt/StarCraft II",
 ]
 for path in default_paths:
     if os.path.exists(path):
         sc2_path = path
 break
 if sc2_path:
     env["SC2PATH"] = sc2_path

     if sys.platform == "win32":
         pass
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     process = subprocess.Popen(
 [PYTHON_EXECUTABLE, str(main_path)],
 cwd = str(PROJECT_ROOT),
 shell = False,
 env = env,
 )
 except:
     process = subprocess.Popen(
 [PYTHON_EXECUTABLE, str(main_path)],
 cwd = str(PROJECT_ROOT),
 shell = False,
 env = env,
 )
 else:
     pass
 process = subprocess.Popen(
 [PYTHON_EXECUTABLE, str(main_path)],
 cwd = str(PROJECT_ROOT),
 shell = False,
 env = env,
 )

     processes.append({"process": process, "id": i + 1, "start_time": time.time()})

     print(f"[OK] Instance #{i + 1} PID: {process.pid}")

 # Staggered Launch: Wait before launching next instance (except for the last one)

 # This prevents shader compilation spike (1.5-2x resource usage during initial loading)

 if i < actual_instances - 1:
     print(
     f"[WAIT] Waiting {START_INTERVAL} seconds... (Staggered Launch - prevents shader compilation spike)\n"
 )

 time.sleep(START_INTERVAL)

     print("\n" + "=" * 70)

     print("[SUCCESS] All instances launched!")

     print("=" * 70)

     print("\n[INFO] Games in progress...")

     print("[INFO] Real-time dashboard will display below.")

     print("[INFO] Monitor GPU memory: nvidia-smi")

     print("[INFO] Each instance will exit automatically when game ends.")

     print("[INFO] Press Ctrl+C to stop all instances.\n")

 # Initial dashboard space (will be overwritten)

 for _ in range(actual_instances + 3): # +3 for separator and total stats
 print()

 # Dashboard update interval (every 1 second)

 last_dashboard_update = 0

 dashboard_update_interval = 1.0

 # Wait for all processes to complete
 # CRITICAL IMPROVEMENT: 게임 엔진 프리징 타임아웃 처리
 GAME_TIMEOUT_SECONDS = 3600  # 1시간 (게임이 이보다 오래 실행되면 프리징으로 간주)
 FRAME_TIMEOUT_SECONDS = 300  # 5분 (프레임 업데이트가 없으면 프리징으로 간주)

 while processes:
     pass
     current_time = time.time()

     # Update dashboard periodically
     if current_time - last_dashboard_update >= dashboard_update_interval:
         display_dashboard(processes)
         last_dashboard_update = current_time

     for proc_info in processes[:]:
         proc = proc_info["process"]
         elapsed = current_time - proc_info["start_time"]
         
         # CRITICAL IMPROVEMENT: 게임 엔진 프리징 감지 및 타임아웃 처리
         # 1. 전체 실행 시간 타임아웃 (1시간)
         if elapsed > GAME_TIMEOUT_SECONDS:
             print(f"\n[TIMEOUT] Instance #{proc_info['id']} exceeded timeout ({GAME_TIMEOUT_SECONDS}s) - possible freeze, terminating...")
             try:
                 proc.terminate()
                 proc.wait(timeout=5)
                 print(f"[OK] Instance #{proc_info['id']} terminated due to timeout")
             except Exception:
                 try:
                     proc.kill()
                     print(f"[FORCE] Instance #{proc_info['id']} force killed due to timeout")
                 except Exception:
                     print(f"[ERROR] Failed to terminate instance #{proc_info['id']}")
             
             processes.remove(proc_info)
             display_dashboard(processes)
             continue
         
         # 2. 프레임 업데이트 타임아웃 체크 (프로세스가 살아있지만 응답 없음)
         # 마지막 업데이트 시간 추적
         if "last_update_time" not in proc_info:
             proc_info["last_update_time"] = current_time
         
         # 프로세스가 살아있지만 오랫동안 업데이트가 없으면 프리징으로 간주
         time_since_update = current_time - proc_info["last_update_time"]
         if time_since_update > FRAME_TIMEOUT_SECONDS:
             return_code = proc.poll()
             if return_code is None:  # 프로세스가 여전히 실행 중
                 print(f"\n[FREEZE] Instance #{proc_info['id']} appears frozen (no update for {FRAME_TIMEOUT_SECONDS}s) - terminating...")
                 try:
                     proc.terminate()
                     proc.wait(timeout=5)
                     print(f"[OK] Instance #{proc_info['id']} terminated due to freeze detection")
                 except Exception:
                     try:
                         proc.kill()
                         print(f"[FORCE] Instance #{proc_info['id']} force killed due to freeze detection")
                     except Exception:
                         print(f"[ERROR] Failed to terminate frozen instance #{proc_info['id']}")
                 
                 processes.remove(proc_info)
                 display_dashboard(processes)
                 continue
         
         # Check process status
         return_code = proc.poll()

         if return_code is not None:
             # Process finished
             elapsed = time.time() - proc_info["start_time"]

             if return_code == 0:
                 print(
                 f"\n[COMPLETE] Instance #{proc_info['id']} finished successfully (runtime: {elapsed:.1f}s)"
             )
             else:
                 print(
                 f"\n[EXIT] Instance #{proc_info['id']} exited (code: {return_code}, runtime: {elapsed:.1f}s)"
             )

             processes.remove(proc_info)

             # Update dashboard after process removal
             display_dashboard(processes)
         else:
             # 프로세스가 실행 중이면 마지막 업데이트 시간 갱신
             proc_info["last_update_time"] = current_time

     # Check every 0.1 seconds for faster dashboard updates
     if processes:
         time.sleep(0.1)

     print("\n" + "=" * 70)

     print("[SUCCESS] All instances finished!")

     print("=" * 70)

 except KeyboardInterrupt:
     print("\n\n[INTERRUPT] Stopped by user.")

     print("[INFO] Terminating all processes...")

 # Zombie process prevention: Force terminate after 5 seconds

 for proc_info in processes:
     proc = proc_info["process"]

 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     proc.terminate()

 proc.wait(timeout = 5)

     print(f"[OK] Instance #{proc_info['id']} terminated")

 except:
     try:
         proc.kill()

         print(f"[FORCE] Instance #{proc_info['id']} force killed (zombie prevention)")

 except:
     print(f"[ERROR] Failed to terminate instance #{proc_info['id']}")

 # Additional cleanup: Wait 1 second and check for remaining processes

 time.sleep(1)

 # Force kill any remaining processes (zombie prevention)

 for proc_info in processes:
     proc = proc_info["process"]

 if proc.poll() is None: # Process still running
 try:
     proc.kill()

     print(f"[CLEANUP] Instance #{proc_info['id']} force killed (zombie cleanup)")

 except:
     pass

     print("[INFO] All processes terminated (zombie prevention active)")

 except Exception as e:
     print(f"\n[ERROR] Error during parallel training: {e}")

 traceback.print_exc()

 # Terminate running processes

 for proc_info in processes:
     try:
         proc_info["process"].terminate()

 except:
     pass
=======
>>>>>>> Incoming (Background Agent changes)

if __name__ == "__main__":
    main()
