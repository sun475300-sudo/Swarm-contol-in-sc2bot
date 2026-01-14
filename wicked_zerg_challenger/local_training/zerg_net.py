# -*- coding: utf-8 -*-

import os
import time
from collections import deque
from enum import Enum
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


# Auto-detect project root directory
def get_project_root():
    """
    Automatically finds the project root directory.
    Searches for project root based on current file location.
    """
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)

    # Project root is the directory containing main.py
    # Search in current directory or parent directory
    search_dirs = [current_dir] + [os.path.dirname(current_dir)]

    for dir_path in search_dirs:
        main_py = os.path.join(dir_path, "main.py")
        if os.path.exists(main_py):
            return dir_path

    # Return current directory if not found
    return current_dir


# Project root path
PROJECT_ROOT = get_project_root()

# Model storage directory (in local_training folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")


class Action(Enum):
    """Action type"""

    ATTACK = 0
    DEFENSE = 1
    ECONOMY = 2
    TECH_FOCUS = 3  # Focus on tech buildings and upgrades


class ZergNet(nn.Module):
    """
    Simple neural network model

    IMPROVED: Enhanced input with comprehensive enemy intelligence
    Input: [Self(5), Enemy(10)] (15-dimensional):
        Self (5): Minerals, Gas, Supply Used, Drone Count, Army Count
        Enemy (10):
            - Enemy Army Count
            - Enemy Tech Level (0-2)
            - Enemy Threat Level (0-4)
            - Enemy Unit Diversity (0-1)
            - Scout Coverage (0-1)
            - Enemy Main Distance (0-1, normalized)
            - Enemy Expansion Count (0-1, normalized)
            - Enemy Resource Estimate (0-1, normalized)
            - Enemy Upgrade Count (0-1, normalized)
            - Enemy Air/Ground Ratio (0-1)
    Output: [Attack Probability, Defense Probability, Economy Probability, Tech Focus] (4-dimensional)

    Note: Model structure updated to 15 inputs for context-aware decision making
    This allows learning strategies like "Baneling drop timing" based on enemy position, tech, and resources
    """

    def __init__(self, input_size: int = 15, hidden_size: int = 64, output_size: int = 4):
        """
        Args:
            input_size: Input dimension (default 15: Self(5) + Enemy(10))
                - Self (5): Minerals, Gas, Supply, Workers, Army
                - Enemy (10): Army Count, Tech Level, Threat Level, Unit Diversity, Scout Coverage,
                             Main Distance, Expansion Count, Resource Estimate, Upgrade Count, Air/Ground Ratio
            hidden_size: Hidden layer size
            output_size: Output dimension (default 4: Attack, Defense, Economy, Tech Focus)
        """
        super(ZergNet, self).__init__()

        # CRITICAL: Ensure input_size matches state vector dimension
        # Default to 15 for enhanced enemy intelligence
        self.input_size = input_size if input_size > 0 else 15
        self.hidden_size = hidden_size
        self.output_size = output_size

        # Simple 2-layer MLP
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)

        # Dropout (prevent overfitting)
        self.dropout = nn.Dropout(0.2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass

        Args:
            x: Input tensor [batch_size, input_size]

        Returns:
            Output tensor [batch_size, output_size] (softmax applied)
        """
        try:
            # Normalized input
            x = F.relu(self.fc1(x))
            x = self.dropout(x)
            x = F.relu(self.fc2(x))
            x = self.dropout(x)
            x = self.fc3(x)

            # Convert to probability distribution with softmax
            return F.softmax(x, dim=-1)
        except Exception as e:
            # Return uniform distribution on error
            print(f"[ERROR] ZergNet.forward error: {e}")
            return torch.ones_like(x) / self.output_size


class ReinforcementLearner:
    """
    Reinforcement Learning Learner

    Uses REINFORCE algorithm for policy gradient learning.
    """

    def __init__(
        self,
        model: ZergNet,
        learning_rate: float = 0.001,
        model_path: Optional[str] = None,
        instance_id: Optional[str] = None,
    ):
        """
        Args:
            model: Neural network model to train
            learning_rate: Learning rate
            model_path: Model save path (auto-generated if None)
            instance_id: Unique instance identifier to prevent file conflicts in parallel training
        """
        # GPU Full Power: Device auto-detection and model placement
        # Get detailed device information (prints GPU info)
        self.device = self._get_device()
        print(f"[DEVICE] Using device: {self.device}")

        # Move model to appropriate device (ensures all operations on GPU)
        self.model = model.to(self.device)
        print(f"[DEVICE] Model moved to: {self.device}")
        self.learning_rate = learning_rate

        # Model path setting (relative to project root)
        # IMPROVED: Use unique filename per instance to prevent file conflicts
        if model_path is None:
            # Create model directory
            os.makedirs(MODELS_DIR, exist_ok=True)
            if instance_id:
                model_path = os.path.join(MODELS_DIR, f"zerg_net_model_{instance_id}.pt")
            else:
                model_path = os.path.join(MODELS_DIR, "zerg_net_model.pt")
        else:
            # Convert relative path to project root based
            if not os.path.isabs(model_path):
                os.makedirs(MODELS_DIR, exist_ok=True)
                if instance_id and "zerg_net_model" in model_path:
                    base_name = os.path.basename(model_path)
                    name, ext = os.path.splitext(base_name)
                    model_path = os.path.join(MODELS_DIR, f"{name}_{instance_id}{ext}")
                else:
                    model_path = os.path.join(MODELS_DIR, os.path.basename(model_path))

        self.model_path = model_path
        self.instance_id = instance_id

        # Optimizer (Adam)
        try:
            self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        except Exception as e:
            print(f"[ERROR] Optimizer initialization error: {e}")
            self.optimizer = None

        # Episode records (Memory optimization: maxlen limits memory usage)
        # maxlen=50000: Limits to approximately 2~3GB (without this, memory grows infinitely)
        self.episode_states = deque(maxlen=50000)
        self.episode_actions = deque(maxlen=50000)
        self.episode_rewards = deque(maxlen=50000)

        # Attempt to load model
        self._load_model()

    def _get_device(self):
        """
        CPU/GPU auto-detection

        GPU Priority: Automatically uses CUDA if NVIDIA GPU is available
        Falls back to CPU if GPU is not available

        Returns:
            torch.device: Available device (cuda, mps, cpu)
        """
        try:
            # Check CUDA (NVIDIA GPU) availability - Priority 1
            if torch.cuda.is_available():
                device = torch.device("cuda")
                gpu_name = torch.cuda.get_device_name(0)
                gpu_props = torch.cuda.get_device_properties(0)
                total_memory = gpu_props.total_memory / (1024**3)  # GB

                # Check current memory usage
                allocated = torch.cuda.memory_allocated(0) / (1024**3)  # GB
                reserved = torch.cuda.memory_reserved(0) / (1024**3)  # GB
                available = total_memory - reserved  # GB

                print(f"[DEVICE] CUDA GPU detected: {gpu_name} ({total_memory:.1f} GB total VRAM)")
                print(
                    f"[DEVICE] Current GPU memory: {reserved:.2f} GB used / {available:.2f} GB available"
                )
                print(
                    f"[DEVICE] GPU training mode activated - all tensor operations will run on GPU"
                )

                # Memory shortage warning
                if available < 0.5:
                    print(
                        f"[DEVICE] WARNING: GPU memory is low ({available:.2f} GB). Game may crash."
                    )
                    print(f"[DEVICE] Recommendation: Reduce instance count in parallel_train.py")

                return device

            # Check MPS (Apple Silicon GPU) availability - Priority 2
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = torch.device("mps")
                print(f"[DEVICE] MPS (Apple Silicon GPU) detected")
                print(
                    f"[DEVICE] GPU training mode activated - all tensor operations will run on GPU"
                )
                return device

            # Use CPU - only when GPU is not available
            device = torch.device("cpu")
            print(f"[DEVICE] GPU not available. Running in CPU mode.")
            print(f"[DEVICE] Training speed may be slower. Install CUDA if you have an NVIDIA GPU.")
            return device

        except Exception as e:
            print(f"[WARNING] Device detection error: {e}. Using CPU.")
            import traceback

            traceback.print_exc()
            return torch.device("cpu")

    def _load_model(self):
        """
        Load model if saved (with file locking handling)

        Enhanced error reporting for model loading failures
        """
        max_retries = 3
        retry_delay = 0.5

        # Check PyTorch and CUDA availability before loading
        try:

            cuda_available = torch.cuda.is_available()
            print(f"[MODEL] PyTorch version: {torch.__version__}")
            print(f"[MODEL] CUDA available: {cuda_available}")
            if cuda_available:
                try:
                    # type: ignore[attr-defined] - torch.version may not be available in all PyTorch versions
                    cuda_version = getattr(torch.version, "cuda", "Unknown")  # type: ignore[attr-defined]
                    print(f"[MODEL] CUDA version: {cuda_version}")
                except (AttributeError, TypeError):
                    print(f"[MODEL] CUDA version: Unknown")
                print(f"[MODEL] GPU device: {torch.cuda.get_device_name(0)}")
        except Exception as e:
            print(f"[WARNING] PyTorch/CUDA check failed: {e}")

        for attempt in range(max_retries):
            try:
                # Create model directory if it doesn't exist
                model_dir = os.path.dirname(self.model_path)
                if model_dir:
                    os.makedirs(model_dir, exist_ok=True)

                if os.path.exists(self.model_path):
                    # Attempt to read file (may be in use by another process)
                    # Set map_location to auto-detected device
                    print(f"[MODEL] Attempting to load model from: {self.model_path}")
                    print(f"[MODEL] Target device: {self.device}")

                    # weights_only=True: Security warning removed and performance optimized
                    loaded_state = torch.load(
                        self.model_path,
                        map_location=str(self.device),
                        weights_only=True,
                    )
                    self.model.load_state_dict(loaded_state)
                    print(
                        f"[OK] Model loaded successfully: {self.model_path} (device: {self.device})"
                    )
                    return
                else:
                    print(f"[INFO] Model file not found: {self.model_path}")
                    print(f"[INFO] Starting with a new model (will be saved after first game)")
                    return
            except (IOError, OSError, PermissionError) as e:
                # File locking error: retry
                print(
                    f"[WARNING] Model load attempt {attempt + 1}/{max_retries} failed (file locking): {e}"
                )
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[INFO] Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[ERROR] Model load failed after {max_retries} retries: {e}")
                    print(f"[ERROR] Error type: {type(e).__name__}")
                    print(f"[INFO] Starting with a new model")
            except RuntimeError as e:
                # Model structure mismatch or other runtime errors
                error_msg = str(e)
                print(f"[ERROR] Model load failed (RuntimeError): {e}")
                print(f"[ERROR] This usually means the model structure doesn't match")
                print(f"[ERROR] Model path: {self.model_path}")
                print(f"[ERROR] Device: {self.device}")

                # Check for size mismatch errors
                if "size mismatch" in error_msg.lower():
                    print(f"[ERROR] Model structure mismatch detected!")
                    print(f"[ERROR] Current model structure:")
                    print(f"[ERROR]   Input size: {self.model.input_size}")
                    print(f"[ERROR]   Output size: {self.model.output_size}")
                    print(f"[ERROR]   Hidden size: {self.model.hidden_size}")
                    print(f"[ERROR] Saved model has different structure (input/output dimensions)")
                    print(f"[ERROR] Solution: Starting with a new model matching current structure")
                    print(f"[ERROR] Old model will be backed up if it exists")

                    # Backup old model if it exists
                    try:
                        if os.path.exists(self.model_path):
                            # Create backup directory if not exists
                            # IMPROVED: Use flexible backup directory
                            backup_dir = os.environ.get("BACKUP_DIR")
                            if not backup_dir or not os.path.exists(backup_dir):
                                # Try common locations
                                possible_paths = [
                                    Path.home() / "backup",
                                    Path(__file__).parent.parent / "backup",
                                    Path("backup"),
                                ]
                                for path in possible_paths:
                                    if path.exists():
                                        backup_dir = str(path)
                                        break
                                else:
                                    backup_dir = str(Path.home() / "backup")  # Default fallback
                            else:
                                backup_dir = str(Path(backup_dir))
                            os.makedirs(backup_dir, exist_ok=True)

                            backup_filename = os.path.basename(self.model_path) + ".backup_mismatch"
                            backup_path = os.path.join(backup_dir, backup_filename)
                            import shutil

                            shutil.copy2(self.model_path, backup_path)
                            print(f"[INFO] Old model backed up to: {backup_path}")
                    except Exception as backup_error:
                        print(f"[WARNING] Failed to backup old model: {backup_error}")

                    # CRITICAL: Delete the mismatched model file so it doesn't keep trying to load it
                    try:
                        if os.path.exists(self.model_path):
                            os.remove(self.model_path)
                            print(
                                f"[INFO] Removed mismatched model file to prevent repeated load attempts"
                            )
                    except Exception as delete_error:
                        print(f"[WARNING] Failed to delete mismatched model: {delete_error}")


                traceback.print_exc()
                print(
                    f"[INFO] Starting with a new model matching current structure (5 input, 4 output)"
                )
                print(f"[INFO] Model will learn from scratch with current architecture")
                return
            except Exception as e:
                # Other error: don't retry
                print(f"[ERROR] Model load failed (unexpected error): {e}")
                print(f"[ERROR] Error type: {type(e).__name__}")
                print(f"[ERROR] Model path: {self.model_path}")
                print(f"[ERROR] Device: {self.device}")

                traceback.print_exc()
                print(f"[INFO] Starting with a new model")
                return

    def save_model(self):
        """
        Save model (auto-create directory + file locking handling)

        To prevent file conflicts when multiple instances try to save simultaneously:
        1. Save to a temporary file first
        2. Move to the original file after saving (atomic operation)
        3. Retry on file locking errors
        """

        max_retries = 5
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                # Create model directory if it doesn't exist
                model_dir = os.path.dirname(self.model_path)
                if model_dir:
                    os.makedirs(model_dir, exist_ok=True)

                # Temporary file path (for atomic saving)
                temp_path = self.model_path + ".tmp"

                # Step 1: Save to temporary file
                torch.save(self.model.state_dict(), temp_path)

                # Step 2: Move to original file (atomic operation)
                # shutil.move may not be atomic on Windows, so use os.replace (Python 3.3+)
                if os.path.exists(self.model_path):
                    # Create backup file (safety measure)
                    # IMPROVED: Use flexible backup directory
                    backup_dir = os.environ.get("BACKUP_DIR")
                    if not backup_dir or not os.path.exists(backup_dir):
                        # Try common locations
                        from pathlib import Path
                        possible_paths = [
                            Path.home() / "backup",
                            Path(__file__).parent.parent / "backup",
                            Path("backup"),
                        ]
                        for path in possible_paths:
                            if path.exists():
                                backup_dir = str(path)
                                break
                        else:
                            backup_dir = str(Path.home() / "backup")  # Default fallback
                    else:
                        backup_dir = str(Path(backup_dir))
                    os.makedirs(backup_dir, exist_ok=True)
                    backup_filename = os.path.basename(self.model_path) + ".backup"
                    backup_path = os.path.join(backup_dir, backup_filename)
                    try:
                        shutil.copy2(self.model_path, backup_path)
                    except Exception:
                        pass

                # Atomic replacement (supports Windows/Linux)
                if hasattr(os, "replace"):
                    os.replace(temp_path, self.model_path)
                else:
                    # Python < 3.3: use shutil.move
                    shutil.move(temp_path, self.model_path)

                print(f"[OK] Model saved: {self.model_path}")
                return

            except (IOError, OSError, PermissionError) as e:
                # File locking error: retry
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[ERROR] Model save failed (retries {max_retries} failed): {e}")
                    print(f"[WARNING] Will retry on next game end.")
            except Exception as e:
                # Other error: don't retry
                print(f"[ERROR] Model save failed: {e}")

                traceback.print_exc()
                return

    def select_action(self, state: np.ndarray) -> Tuple[Action, float]:
        """
        Select action based on state

        Args:
            state: Game state [Minerals, Gas, Supply Used, Drone Count, Army Count, Tech Level]

        Returns:
            (Selected action, Action probability)
        """
        try:
            # GPU Full Power: Ensure all tensors are on the same device
            # Step 1: Convert NumPy array to tensor with explicit device placement
            if not isinstance(state, torch.Tensor):
                # Ensure state is a numpy array with correct dtype
                if not isinstance(state, np.ndarray):
                    state = np.array(state, dtype=np.float32)
                else:
                    state = state.astype(np.float32)

                # Create tensor directly on target device (non_blocking for async transfer)
                # CPU prepares data while GPU processes previous inference
                state_tensor = (
                    torch.from_numpy(state).unsqueeze(0).to(self.device, non_blocking=True)
                )  # [1, 6]
            else:
                # Already a tensor: ensure it's on the correct device
                state_tensor = state.unsqueeze(0) if state.dim() == 1 else state
                # Force move to device (handles device mismatch)
                if state_tensor.device != self.device:
                    state_tensor = state_tensor.to(self.device)

            # Step 2: Normalize (0~1 range) - normalization creates tensors on same device
            state_tensor = self._normalize_state(state_tensor)

            # Step 3: Model inference (model is already on self.device)
            # Enable GPU optimizations for inference
            with torch.no_grad():
                # Model forward pass (GPU processes while CPU prepares next state)
                action_probs = self.model(state_tensor)

                # Note: We don't synchronize here to allow CPU to prepare next state
                # Synchronization happens only when we need the result (CPU conversion)

            # Step 4: Move results to CPU for numpy conversion (single transfer)
            # Synchronize GPU operations before CPU transfer (only when needed)
            if self.device.type == "cuda":
                torch.cuda.synchronize()  # Ensure GPU operations complete before CPU transfer
            action_probs_np = action_probs.cpu().numpy()[0]

            # Step 5: Select action with max probability
            action_idx = int(np.argmax(action_probs_np))
            action = Action(action_idx)

            # Probability of selected action
            action_prob = float(action_probs_np[action_idx])

            return action, action_prob

        except RuntimeError as e:
            if "Expected all tensors to be on the same device" in str(e):
                print(f"[ERROR] Device mismatch in select_action: {e}")
                print(
                    f"[ERROR] State device: {state_tensor.device if 'state_tensor' in locals() else 'N/A'}"
                )
                print(f"[ERROR] Model device: {self.device}")
                print(f"[ERROR] Attempting to fix device mismatch...")
                # Retry with explicit device placement
                try:
                    state_tensor = state_tensor.to(self.device)
                    state_tensor = self._normalize_state(state_tensor)
                    with torch.no_grad():
                        action_probs = self.model(state_tensor)
                    action_probs_np = action_probs.cpu().numpy()[0]
                    action_idx = int(np.argmax(action_probs_np))
                    return Action(action_idx), float(action_probs_np[action_idx])
                except Exception as retry_error:
                    print(f"[ERROR] Retry failed: {retry_error}")
            else:
                print(f"[ERROR] select_action RuntimeError: {e}")
            # Default action on error (economy focus)
            return Action.ECONOMY, 0.33
        except Exception as e:
            print(f"[ERROR] select_action error: {e}")

            traceback.print_exc()
            # Default action on error (economy focus)
            return Action.ECONOMY, 0.33

    def _normalize_state(self, state: torch.Tensor) -> torch.Tensor:
        """
        Normalize state with improved scaling for Self(5) + Enemy(10) balance

        CRITICAL IMPROVEMENT: Enhanced normalization to prevent Self data from
        overwhelming Enemy data. Uses weighted normalization to ensure Enemy
        information (unit counts, tech level) is as important as Self resources.

        Args:
            state: Original state tensor (15-dimensional: Self(5) + Enemy(10))

        Returns:
            Normalized state tensor with balanced Self/Enemy importance
        """
        try:
            # CRITICAL: Enhanced normalization with importance weighting
            # Problem: Self values (minerals 0-2000) vs Enemy values (units 0-200)
            # Solution: Apply importance weights to ensure Enemy data is not ignored

            if state.shape[-1] == 15:
                # 15-dimensional state (Self(5) + Enemy(10)) - PREFERRED
                # IMPROVED: Weighted normalization to balance Self vs Enemy importance

                # Step 1: Min-Max normalization with appropriate ranges
                max_values = torch.tensor([
                    # Self (5) - Large scale values
                    2000.0,  # Minerals (0-2000)
                    2000.0,  # Gas (0-2000)
                    200.0,   # Supply Used (0-200)
                    100.0,   # Drone Count (0-100)
                    200.0,   # Army Count (0-200)
                    # Enemy (10) - Mixed scale values
                    200.0,   # Enemy Army Count (0-200, same scale as our army)
                    2.0,     # Enemy Tech Level (0-2, discrete)
                    4.0,     # Enemy Threat Level (0-4, discrete)
                    1.0,     # Enemy Unit Diversity (0-1, normalized)
                    1.0,     # Scout Coverage (0-1, normalized)
                    1.0,     # Enemy Main Distance (0-1, normalized)
                    1.0,     # Enemy Expansion Count (0-1, normalized)
                    1.0,     # Enemy Resource Estimate (0-1, normalized)
                    1.0,     # Enemy Upgrade Count (0-1, normalized)
                    1.0      # Enemy Air/Ground Ratio (0-1, normalized)
                ], device=self.device)

                # Step 2: Min-Max normalization (0-1 range)
                normalized = torch.clamp(state / max_values, 0.0, 1.0)

                # Step 3: Apply importance weights to balance Self vs Enemy
                # Enemy features get higher weight to compensate for smaller raw values
                importance_weights = torch.tensor([
                    # Self (5) - Standard weight
                    1.0, 1.0, 1.0, 1.0, 1.0,
                    # Enemy (10) - Enhanced weight to match Self importance
                    1.5,  # Enemy Army Count (critical for decision making)
                    2.0,  # Enemy Tech Level (very important - discrete 0-2)
                    1.5,  # Enemy Threat Level (important - discrete 0-4)
                    1.2,  # Enemy Unit Diversity
                    1.2,  # Scout Coverage
                    1.3,  # Enemy Main Distance
                    1.3,  # Enemy Expansion Count
                    1.2,  # Enemy Resource Estimate
                    1.2,  # Enemy Upgrade Count
                    1.2   # Enemy Air/Ground Ratio
                ], device=self.device)

                # Apply weights (element-wise multiplication)
                weighted_normalized = normalized * importance_weights

                # Step 4: Re-normalize to 0-1 range after weighting
                # This ensures all features contribute equally to the decision
                max_weighted = importance_weights.max()
                final_normalized = torch.clamp(weighted_normalized / max_weighted, 0.0, 1.0)

                return final_normalized

            elif state.shape[-1] == 10:
                # Legacy 10-dimensional state (backward compatibility)
                max_values = torch.tensor([
                    2000.0, 2000.0, 200.0, 100.0, 200.0,  # Self (5)
                    200.0, 2.0, 4.0, 1.0, 1.0  # Enemy (5)
                ], device=self.device)
                normalized = torch.clamp(state / max_values, 0.0, 1.0)
                # Apply importance weights for 10-dim state
                importance_weights = torch.tensor([
                    1.0, 1.0, 1.0, 1.0, 1.0,  # Self (5)
                    1.5, 2.0, 1.5, 1.2, 1.2   # Enemy (5)
                ], device=self.device)
                weighted_normalized = normalized * importance_weights
                max_weighted = importance_weights.max()
                final_normalized = torch.clamp(weighted_normalized / max_weighted, 0.0, 1.0)
                return final_normalized

            elif state.shape[-1] == 5:
                # Legacy 5-dimensional state (backward compatibility)
                max_values = torch.tensor([2000.0, 2000.0, 200.0, 100.0, 200.0], device=self.device)
                normalized = torch.clamp(state / max_values, 0.0, 1.0)
                return normalized
            else:
                # Unknown dimension - use default normalization
                print(f"[WARNING] Unknown state dimension: {state.shape[-1]}, using default normalization")
                max_values = torch.ones(state.shape[-1], device=self.device) * 2000.0
                normalized = torch.clamp(state / max_values, 0.0, 1.0)
                return normalized

        except Exception as e:
            print(f"[ERROR] _normalize_state error: {e}")
            traceback.print_exc()
            return state

    def record_step(self, state: np.ndarray, action: Action, reward: float = 0.0):
        """
        Record one step (episode collection)

        Args:
            state: Game state
            action: Selected action
            reward: Immediate reward (usually 0, only given at episode end)
        """
        try:
            self.episode_states.append(state)
            self.episode_actions.append(action.value)
            self.episode_rewards.append(reward)
        except Exception as e:
            print(f"[ERROR] record_step error: {e}")

    def finish_episode(self, final_reward: float):
        """
        Finish episode and update model (REINFORCE)

        Optimized for GPU/CPU load balancing:
        - Batch processing for efficient GPU utilization
        - Asynchronous data transfer (pin_memory equivalent)
        - CPU prepares data while GPU processes previous batch

        Args:
            final_reward: Final reward (Victory: +1.0, Defeat: -1.0)
        """
        try:
            if len(self.episode_states) == 0:
                return

            if self.optimizer is None:
                print("[WARNING] Optimizer is None, skipping learning.")
                return

            # Assign final reward to all steps (Monte Carlo)
            discounted_rewards = [final_reward] * len(self.episode_states)

            # GPU/CPU Load Balancing: Batch Processing Optimization
            # Step 1: CPU prepares data (while GPU may be processing previous batch)
            # Convert deque to numpy arrays on CPU (fast)
            states_array = np.array(list(self.episode_states), dtype=np.float32)
            actions_array = np.array(list(self.episode_actions), dtype=np.int64)
            rewards_array = np.array(discounted_rewards, dtype=np.float32)

            # Step 2: Batch processing for large episodes (reduce GPU memory spikes)
            # Process in batches if episode is very long (>1000 steps)
            batch_size = 1000  # Process 1000 steps at a time
            total_steps = len(states_array)

            if total_steps > batch_size:
                # Large episode: Process in batches to avoid GPU memory overflow
                total_loss = 0.0
                num_batches = (total_steps + batch_size - 1) // batch_size

                for batch_idx in range(num_batches):
                    start_idx = batch_idx * batch_size
                    end_idx = min(start_idx + batch_size, total_steps)

                    # Extract batch
                    batch_states = states_array[start_idx:end_idx]
                    batch_actions = actions_array[start_idx:end_idx]
                    batch_rewards = rewards_array[start_idx:end_idx]

                    # Transfer batch to GPU (asynchronous if possible)
                    batch_states_tensor = torch.from_numpy(batch_states).to(
                        self.device, non_blocking=True
                    )
                    batch_actions_tensor = torch.from_numpy(batch_actions).to(
                        self.device, non_blocking=True
                    )
                    batch_rewards_tensor = torch.from_numpy(batch_rewards).to(
                        self.device, non_blocking=True
                    )

                    # Normalize states
                    batch_states_tensor = self._normalize_state(batch_states_tensor)

                    # Normalize rewards (per batch)
                    batch_rewards_tensor = (batch_rewards_tensor - batch_rewards_tensor.mean()) / (
                        batch_rewards_tensor.std() + 1e-8
                    )

                    # Forward pass
                    batch_action_probs = self.model(batch_states_tensor)

                    # Calculate log probabilities
                    batch_log_probs = torch.log(
                        batch_action_probs.gather(1, batch_actions_tensor.unsqueeze(1)).squeeze(1)
                        + 1e-8
                    )

                    # Loss for this batch
                    batch_loss = -(batch_log_probs * batch_rewards_tensor).mean()
                    total_loss += batch_loss.item()

                    # Backward pass (accumulate gradients)
                    batch_loss.backward()

                # Gradient clipping (prevent explosion)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

                # Single optimizer step for all batches
                self.optimizer.step()
                self.optimizer.zero_grad()

                avg_loss = total_loss / num_batches
                print(
                    f"[LEARN] Batch learning complete - Avg Loss: {avg_loss:.4f}, Reward: {final_reward:.2f}, Steps: {total_steps}, Batches: {num_batches}"
                )
            else:
                # Small episode: Process all at once (faster for small episodes)
                # GPU Full Power: Ensure all tensors are on the same device
                # Transfer to GPU (non_blocking=True for async transfer)
                states = torch.from_numpy(states_array).to(self.device, non_blocking=True)
                states = self._normalize_state(states)

                actions = torch.from_numpy(actions_array).to(self.device, non_blocking=True)
                rewards = torch.from_numpy(rewards_array).to(self.device, non_blocking=True)

                # Normalize (reward scaling) - all operations on same device
                rewards = (rewards - rewards.mean()) / (rewards.std() + 1e-8)

                # Policy gradient update
                self.optimizer.zero_grad()

                # Forward pass
                action_probs = self.model(states)

                # Log probability of selected action
                log_probs = torch.log(
                    action_probs.gather(1, actions.unsqueeze(1)).squeeze(1) + 1e-8
                )

                # Loss function: -log_prob * reward (REINFORCE)
                loss = -(log_probs * rewards).mean()

                # Backpropagation
                loss.backward()

                # Gradient clipping (prevent explosion)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

                # Weight update
                self.optimizer.step()

                print(
                    f"[LEARN] Learning complete - Loss: {loss.item():.4f}, Reward: {final_reward:.2f}, Steps: {total_steps}"
                )

            # GPU synchronization (ensure all operations complete)
            if self.device.type == "cuda":
                torch.cuda.synchronize()

        except Exception as e:
            print(f"[ERROR] update error: {e}")

            traceback.print_exc()
        finally:
            # Reset episode records (deque automatically removes old data, so just clear)
            self.episode_states.clear()
            self.episode_actions.clear()
            self.episode_rewards.clear()

    def reset_episode(self):
        """Reset episode records"""
        self.episode_states.clear()
        self.episode_actions.clear()
        self.episode_rewards.clear()
