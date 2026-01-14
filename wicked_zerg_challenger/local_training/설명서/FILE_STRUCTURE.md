# File Structure Organization

## local_training/ (Root Folder)

Core bot logic and execution files that are directly imported by the bot.

### Main Execution Files
- `main_integrated.py` - Main entry point for training
- `wicked_zerg_bot_pro.py` - Main bot class integrating all managers

### Core Manager Modules
- `combat_manager.py` - Combat strategy and unit control
- `combat_tactics.py` - Specific combat behaviors
- `economy_manager.py` - Resource and building management
- `intel_manager.py` - Enemy intelligence and data caching
- `production_manager.py` - Unit production logic
- `production_resilience.py` - Emergency production and bottlenecks
- `queen_manager.py` - Queen management
- `scouting_system.py` - Scouting and map exploration
- `micro_controller.py` - Detailed unit micro-control
- `personality_manager.py` - Personality and chat system
- `strategy_analyzer.py` - Strategy analysis and adaptation
- `telemetry_logger.py` - Game data logging

### Learning and Neural Network
- `zerg_net.py` - Neural network model (ZergNet) and reinforcement learning
- `curriculum_manager.py` - Curriculum learning system
- `replay_build_order_learner.py` - Build order extraction from replays
- `replay_quality_analyzer.py` - Replay quality assessment
- `learning_accelerator.py` - Learning optimization
- `performance_monitor.py` - Performance monitoring
- `error_handler.py` - Error handling and recovery

### Configuration
- `config.py` - Global configuration values
- `integrated_pipeline.py` - Integrated training pipeline

### Scripts (Bot Runtime Scripts)
- `scripts/replay_learning_manager.py` - Learning iteration tracking
- `scripts/learning_logger.py` - Learning log recording
- `scripts/strategy_database.py` - Strategy database management
- `scripts/replay_quality_filter.py` - Replay quality filtering
- `scripts/parallel_train_integrated.py` - Parallel training execution
- `scripts/run_hybrid_supervised.py` - Hybrid supervised learning

### Data Directories
- `models/` - Trained model weights (`.pt` files)
- `data/` - Training data
  - `build_orders/` - Extracted build orders from replays

---

## Documentation Structure

### local_training/설명서/
This folder contains documentation specific to the `local_training` folder logic and implementation:
- File structure organization
- Code fixes and improvements
- Logic implementation details
- Module-specific documentation

### Project Root 설명서/
The root `설명서/` folder contains project-wide documentation:
- Project setup and configuration
- Deployment guides
- Training pipeline guides
- Project structure overview
- General project documentation

---

**Note**: 
- `local_training/설명서/` - Documentation for local_training logic
- Root `설명서/` - Project-wide documentation
