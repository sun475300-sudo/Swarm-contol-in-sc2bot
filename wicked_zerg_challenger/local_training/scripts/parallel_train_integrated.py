# -*- coding: utf-8 -*-

"""

================================================================================

        Integrated Parallel Training System - Resource-Aware Scheduling

================================================================================

GPU-optimized parallel training system with dynamic instance count calculation.

Features:

- Resource-Aware Scheduling: Dynamic GPU memory calculation

- Staggered Launch: Prevents shader compilation spike (15s interval)

- Auto-adjustment: Instance count based on available VRAM

- Performance Optimization: realtime=False + step_multiplier support

Usage:

    python parallel_train_integrated.py

GPU Memory Formula:

    safe_instances = (total_memory - memory_reserved - 1.0GB) / 0.8GB

Expected Performance (RTX 2060 6GB):

    - Total VRAM: 6.0 GB

    - Reserved: ~1.2 GB (PyTorch model + system)

    - Available: ~4.8 GB

    - Safe Instances: (4.8 - 1.0) / 0.8 = 4.75 -> 4 instances

Notes:

    1. Graphics: Set SC2 to 'Window Mode' and 'Very Low' quality

    2. Monitor: Use 'nvidia-smi' to watch GPU memory usage

    3. Auto-exit: Each instance will exit automatically when game ends

================================================================================

"""

import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

# IMPROVED: Try C++ protobuf implementation first for better performance
# Fallback to Python if C++ is not available (for compatibility)
try:
    from config import Config
    _config = Config()
    protobuf_impl = _config.PROTOCOL_BUFFERS_IMPL
    
    # Try C++ implementation first (10x faster)
    if protobuf_impl == "cpp":
        try:
            import google.protobuf.pyext._message as _message  # type: ignore
            os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "cpp"
            print("[OK] Using C++ protobuf implementation (fast mode)")
        except ImportError:
            # Fallback to Python if C++ not available
            os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
            print("[WARNING] C++ protobuf not available, using Python implementation (slower)")
    else:
        os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = protobuf_impl
except Exception:
    # Fallback to Python on any error
    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Settings

# Allow NUM_INSTANCES to be set via environment variable (for runtime adjustment)

NUM_INSTANCES = int(os.environ.get("NUM_INSTANCES", "2"))  # Default: 2 instances

# Tip: RTX 3080(10GB) or higher GPU can increase NUM_INSTANCES to 5-8 for faster training

# Set via: $env:NUM_INSTANCES=6; python parallel_train_integrated.py

START_INTERVAL = 15  # Seconds between instance launches (prevents shader compilation spike)

MAIN_FILE = (
    "main_integrated.py"  # Use main_integrated.py (supports parallel training with RL orchestrator)
)

# Display Settings

SHOW_WINDOW = os.environ.get("SHOW_WINDOW", "false").lower() == "true"
HEADLESS_MODE = os.environ.get("HEADLESS_MODE", "true").lower() == "true"

# Note: Showing windows will reduce training speed but allows visual monitoring

# GPU memory settings (estimated usage per instance)

ESTIMATED_VRAM_PER_INSTANCE = 0.8  # GB (each instance uses ~0.8GB at Very Low settings)

MIN_SAFE_VRAM_RESERVE = 1.0  # GB (reserve for OS DWM and display output)

PROJECT_ROOT = Path(__file__).parent.absolute()

# IMPROVED: Use flexible venv path detection
def get_venv_dir() -> Path:
    """Get virtual environment directory from environment variable or use project default"""
    import os
    venv_dir = os.environ.get("VENV_DIR")
    if venv_dir and Path(venv_dir).exists():
        return Path(venv_dir)
    # Try common locations
    possible_paths = [
        PROJECT_ROOT / ".venv",
        Path.home() / ".venv",
        Path(".venv"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    # Default fallback
    return PROJECT_ROOT / ".venv"

VENV_DIR = get_venv_dir()
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe" if sys.platform == "win32" else VENV_DIR / "bin" / "python3"
PYTHON_EXECUTABLE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

def check_gpu_memory():
    """

    GPU memory check and safe instance count calculation

    GPU Memory Management and Instance Decision Algorithm:

    Core Mechanism: Real-time VRAM availability analysis

    1. Total Memory: Total video memory of the GPU

    2. Reserved Memory: Memory currently occupied by PyTorch cache or other processes

    3. Available Memory: Pure free space available for new game instances (Total - Reserved)

    Optimal Instance Count Formula:

        N_safe = floor((VRAM_available - VRAM_reserve) / VRAM_per_instance)

        Where:

        - VRAM_available: Currently available GPU memory (GB)

        - VRAM_reserve: Minimum reserve capacity for system stability (default: 1.0 GB)

        - VRAM_per_instance: Estimated usage per SC2 client (default: 0.8 GB)

        - N_safe: Final safe instance count to run

    Algorithm Features:

    - Safety First: Force reserve 1.0 GB for system stability

    - Dynamic Adaptation: Automatically adjust instance count based on GPU load at runtime

    - Staggered Launch: START_INTERVAL (15s) distributes temporary peak load during client loading

    Returns:

        tuple: (is_gpu_available, total_vram_gb, available_vram_gb, recommended_instances, gpu_name)

    """

    try:
        import torch

        if not torch.cuda.is_available():
            print("[GPU] CUDA GPU not available. Running in CPU mode.")

            return False, 0, 0, NUM_INSTANCES, "CPU"

        device = torch.cuda.current_device()

        gpu_props = torch.cuda.get_device_properties(device)

        gpu_name = gpu_props.name

        total_memory = gpu_props.total_memory / (1024**3)  # Convert to GB

        # Calculate actual available memory excluding reserved memory

        allocated = torch.cuda.memory_allocated(device) / (1024**3)  # GB

        reserved = torch.cuda.memory_reserved(device) / (1024**3)  # GB

        available = total_memory - reserved  # GB

        # Apply algorithm: (available - 1GB reserve) / 0.8GB per instance

        # Example: 8GB GPU with 2GB used: (6 - 1) / 0.8 = 6.25 -> 6 instances possible

        safe_available = max(0, available - MIN_SAFE_VRAM_RESERVE)

        safe_instances = int(safe_available / ESTIMATED_VRAM_PER_INSTANCE)

        # Compare with user setting (NUM_INSTANCES) and select minimum

        # RTX 3080(10GB) or higher GPUs can increase NUM_INSTANCES for more instances

        safe_instances = max(1, min(safe_instances, NUM_INSTANCES))

        # Print detailed GPU memory information

        print(f"[GPU] GPU Detected: {gpu_name}")

        print(f"[GPU] Total VRAM: {total_memory:.2f} GB")

        print(f"[GPU] Reserved VRAM: {reserved:.2f} GB (Allocated: {allocated:.2f} GB)")

        print(f"[GPU] Available VRAM: {available:.2f} GB")

        print(f"[GPU] Safe Reserve: {MIN_SAFE_VRAM_RESERVE:.1f} GB (OS DWM + Display)")

        print(f"[GPU] Safe Available: {safe_available:.2f} GB")

        print(
            f"[GPU] Recommended Instances: {safe_instances} (Formula: floor(({available:.2f} - {MIN_SAFE_VRAM_RESERVE:.1f}) / {ESTIMATED_VRAM_PER_INSTANCE:.1f}) = {safe_instances})"
        )

        # High-end GPU detection and recommendation

        if total_memory >= 10.0 and safe_instances < NUM_INSTANCES:
            print(
                f"[GPU] Tip: RTX 3080(10GB) or higher GPU detected! Increasing NUM_INSTANCES to {safe_instances}~{int(safe_available / ESTIMATED_VRAM_PER_INSTANCE)} will significantly improve training speed."
            )

        return True, total_memory, available, safe_instances, gpu_name

    except ImportError:
        print("[GPU] PyTorch not installed. Running in CPU mode.")

        return False, 0, 0, NUM_INSTANCES, "CPU"

    except Exception as e:
        print(f"[WARNING] GPU memory check failed: {e}")

        import traceback

        traceback.print_exc()

        # Try to check if CUDA is available even if memory check failed

        try:
            import torch

            if torch.cuda.is_available():
                print(
                    "[GPU] CUDA is available but memory check failed. Using default instance count."
                )

                return True, 0, 0, NUM_INSTANCES, "GPU (Unknown)"

        except:
            pass

        return False, 0, 0, NUM_INSTANCES, "Unknown"

def read_instance_status(instance_id):
    """

    Read instance status from JSON file

    Args:

        instance_id: Instance identifier

    Returns:

        dict: Status data or None if file not found/invalid

    """

    try:
        # IMPROVED: Use project root stats/ directory with instance subdirectory
        project_root = Path(__file__).parent.parent.parent
        status_file = project_root / "stats" / f"instance_{instance_id}" / "status.json"

        if status_file.exists():
            with open(status_file, "r", encoding="utf-8") as f:
                return json.load(f)

    except Exception:
        pass

    return None

def get_gpu_temperature():
    """

    Get GPU temperature using nvidia-smi (Windows/Linux)

    Returns:

        float: GPU temperature in Celsius, or None if unavailable

    """

    try:
        import subprocess

        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode == 0:
            temp_str = result.stdout.strip()

            return float(temp_str)

    except Exception:
        pass

    return None

def display_dashboard(processes):
    """

    Display real-time dashboard with all instance statuses

    Args:

        processes: List of process info dictionaries

    """

    try:
        # Read all instance statuses

        instance_statuses = []

        total_wins = 0

        total_losses = 0

        for proc_info in processes:
            instance_id = proc_info.get("id", 0)

            status = read_instance_status(instance_id)

            if status:
                instance_statuses.append(
                    {"id": instance_id, "status": status, "process": proc_info}
                )

                total_wins += status.get("win_count", 0)

                total_losses += status.get("loss_count", 0)

            else:
                # Process exists but status file not found (initializing)

                instance_statuses.append(
                    {
                        "id": instance_id,
                        "status": {
                            "status": "INITIALIZING",
                            "mode": "HEADLESS",
                            "current_game_time": "00:00",
                            "current_minerals": 0,
                            "current_supply": "0/0",
                            "current_units": 0,
                        },
                        "process": proc_info,
                    }
                )

        # Build dashboard display

        lines = []

        # Instance status lines

        for inst in sorted(instance_statuses, key=lambda x: x["id"]):
            inst_id = inst["id"]

            stat = inst["status"]

            mode = stat.get("mode", "HEADLESS")

            game_time = stat.get("current_game_time", "00:00")

            minerals = stat.get("current_minerals", 0)

            supply = stat.get("current_supply", "0/0")

            units = stat.get("current_units", 0)

            status_text = stat.get("status", "UNKNOWN")

            # Format: [INSTANCE #1] TIME: 05:20 | MIN: 450 | SUPPLY: 45/52 | UNITS: 45 (VISUAL)

            line = (
                f"[INSTANCE #{inst_id}] "
                f"TIME: {game_time} | "
                f"MIN: {minerals:4d} | "
                f"SUPPLY: {supply} | "
                f"UNITS: {units:3d} "
                f"({mode})"
            )

            lines.append(line)

        # Separator

        lines.append("-" * 70)

        # Total stats

        total_games = total_wins + total_losses

        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0.0

        # GPU temperature

        gpu_temp = get_gpu_temperature()

        temp_str = f" | GPU Temp: {int(gpu_temp)}Â¡Ã†C" if gpu_temp else ""

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
        # Local dashboard server
        print("[1/2] Starting local dashboard (http://localhost:8000)...")
        dashboard_proc = subprocess.Popen(
            [PYTHON_EXECUTABLE, "monitoring/dashboard.py"],
            cwd=PROJECT_ROOT.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )
        print(f"      ? Dashboard started (PID: {dashboard_proc.pid})")
        time.sleep(2)  # Wait for server to start

        # Ngrok remote access
        print("[2/2] Starting ngrok tunnel for remote access...")
        ngrok_cmd = "start_with_ngrok.bat" if sys.platform == "win32" else "./start_with_ngrok.sh"
        ngrok_proc = subprocess.Popen(
            ngrok_cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
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
        f"  Performance: realtime=False (Maximum Speed) - Window: {'Visible' if SHOW_WINDOW else 'Hidden'}"
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
                env["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = os.environ.get(
                    "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python"
                )

            sc2_path = os.environ.get("SC2PATH")
            if not sc2_path:
                from pathlib import Path
                default_paths = []
                if sys.platform == "win32":
                    default_paths = [
                        r"C:\Program Files (x86)\StarCraft II",
                        r"C:\Program Files\StarCraft II",
                    ]
                elif sys.platform == "darwin":
                    default_paths = [
                        os.path.expanduser("~/Library/Application Support/Blizzard/StarCraft II"),
                        "/Applications/StarCraft II",
                    ]
                else:
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
                try:
                    process = subprocess.Popen(
                        [PYTHON_EXECUTABLE, str(main_path)],
                        cwd=str(PROJECT_ROOT),
                        shell=False,
                        env=env,
                    )
                except:
                    process = subprocess.Popen(
                        [PYTHON_EXECUTABLE, str(main_path)],
                        cwd=str(PROJECT_ROOT),
                        shell=False,
                        env=env,
                    )
            else:
                process = subprocess.Popen(
                    [PYTHON_EXECUTABLE, str(main_path)],
                    cwd=str(PROJECT_ROOT),
                    shell=False,
                    env=env,
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

        for _ in range(actual_instances + 3):  # +3 for separator and total stats
            print()

        # Dashboard update interval (every 1 second)

        last_dashboard_update = 0

        dashboard_update_interval = 1.0

        # Wait for all processes to complete

        while processes:
            current_time = time.time()

            # Update dashboard periodically

            if current_time - last_dashboard_update >= dashboard_update_interval:
                display_dashboard(processes)

                last_dashboard_update = current_time

            for proc_info in processes[:]:
                proc = proc_info["process"]

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
                proc.terminate()

                proc.wait(timeout=5)

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

            if proc.poll() is None:  # Process still running
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

if __name__ == "__main__":
    print("\n" + "=" * 70)

    print("Integrated Parallel Training System - Resource-Aware Scheduling")

    print("=" * 70)

    print(f"  Default Instances: {NUM_INSTANCES} (auto-adjusted based on GPU memory)")

    print(f"  Start Interval: {START_INTERVAL} seconds (Staggered Launch)")

    print(f"  Project Path: {PROJECT_ROOT}")

    print("=" * 70)

    print("\nGPU Memory Safety Tips:")

    print("  RTX 2060 (6GB): Expect 4 instances maximum")

    print("  RTX 3080 (10GB): Can run 5~8 instances (set NUM_INSTANCES higher)")

    print("  Each instance uses ~0.8GB VRAM at Very Low settings")

    print("  System reserves 1.0GB for OS DWM and display output")

    print("  Formula: N_safe = floor((VRAM_available - 1.0GB) / 0.8GB)")

    print("  If VRAM is insufficient, games may crash")

    print("  Monitor with: nvidia-smi (watch GPU memory usage)")

    print("  Performance: realtime=False enables maximum training speed")

    print("  Staggered Launch: 15s interval prevents shader compilation spike")

    print("\nDisplay Options:")

    print("  Default: Headless mode (realtime=False, windows hidden)")

    print("  To show windows: Set environment variable SHOW_WINDOW=true")

    print("  Example: $env:SHOW_WINDOW='true'; python parallel_train_integrated.py")

    print("  Note: Showing windows will reduce training speed significantly")

    print("=" * 70 + "\n")

    start_parallel_training()