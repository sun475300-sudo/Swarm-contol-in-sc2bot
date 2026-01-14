# -*- coding: utf-8 -*-
"""
Bot Runtime Scripts Package

This package contains scripts that are imported and used by the bot during runtime.
These are NOT management utilities - those belong in tools/ folder.

CRITICAL: Only bot runtime scripts should be in this folder.
Management scripts (cleanup, optimize, test, download) belong in tools/ folder.

Bot Runtime Scripts (? Correctly placed):
- replay_learning_manager.py: Learning iteration tracking
- learning_logger.py: Learning log recording
- strategy_database.py: Strategy database management
- replay_quality_filter.py: Replay quality filtering
- parallel_train_integrated.py: Parallel training execution
- run_hybrid_supervised.py: Hybrid supervised learning
- learning_status_manager.py: Learning status tracking (hard requirement)
- replay_crash_handler.py: Crash handling and bad replay detection
- replay_build_order_learner.py: Build order extraction from replays

Management Scripts (? Should be moved to tools/):
- cleanup_*.py, optimize_*.py, test_*.py, download_and_train.py, etc.
"""
