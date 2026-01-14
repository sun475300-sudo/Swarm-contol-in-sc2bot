# -*- coding: utf-8 -*-
"""
GitHub sc2AIagent Integration Guide
Complete instructions for integrating sc2AIagent files
"""

INTEGRATION_GUIDE = """
================================================================================
WICKED ZERG CHALLENGER - GitHub sc2AIagent Integration Guide
================================================================================

PROJECT STATUS:
? Core features implemented (5 major features)
? Mobile dashboard infrastructure ready
? Backend API operational (mobile_dashboard_backend_fixed.py)
? Web server ready (dashboard.py on port 5000/8000)
? sc2AIagent accessible via MCP tool

CURRENT STATE:
- Local bot: wicked_zerg_bot_pro.py (exists in workspace)
- GitHub bot: sun475300-sudo/sc2AIagent (4900+ line main bot)
- Config: Unified via sc2_integration_config.py

================================================================================
INTEGRATION APPROACH (Recommended: Light Touch)
================================================================================

DO NOT do full clone (git won't work - private/auth issue).
Instead: Use existing local files + MCP-extracted utilities

LOCAL FILES (Keep As-Is):
  ? wicked_zerg_bot_pro.py - Main bot implementation
  ? production_manager.py - Production logic
  ? combat_manager.py - Combat management
  ? economy_manager.py - Resource management
  ? intel_manager.py - Information sharing (Blackboard)
  ? scouting_system.py - Enemy detection
  ? micro_controller.py - Unit micro (Potential Fields)
  ? queen_manager.py - Queen control

NEW (Just Added):
  ? sc2_integration_config.py - Unified config from sc2AIagent
  ? dashboard.py - Web dashboard on port 8000
  ? cleanup_project.py - Project maintenance script

GITHUB-EXTRACTED (Ready to Use):
  ? From sun475300-sudo/sc2AIagent via MCP:
    - unit_factory.py (production specialist)
    - telemetry_logger.py (metrics collection)
    - curriculum_manager.py (RL training rewards)
    - zerg_net.py (neural network model)
    - parallel_train_integrated.py (multi-instance training)

================================================================================
WHY THIS APPROACH?
================================================================================

1. COMPATIBILITY
   - Your existing bot is fully functional
   - sc2AIagent provides battle-tested manager patterns
   - No need to rewrite working code

2. SIMPLICITY
   - No git clone headaches (private repo issue)
   - Mix and match what you need
   - Gradual integration possible

3. MODULARITY
   - Managers are independent
   - Easy to swap/upgrade individual modules
   - Test each change incrementally

================================================================================
INTEGRATION STEPS (If Needed in Future)
================================================================================

IF you want advanced features from sc2AIagent later:

Step 1: Identify Needed Module
  Example: "I want better unit production"
  ⊥ Extract: unit_factory.py + curriculum_manager.py

Step 2: Extract via MCP Tool
  Already available in context (github_repo MCP)
  Returns code snippets directly

Step 3: Adapt to Your Code
  - Map enums (GamePhase, StrategyMode, etc.)
  - Use unified config (sc2_integration_config.py)
  - Test in isolation first

Step 4: Integrate into Main Loop
  - Add to on_step() with iteration modulo
  - Update managers list
  - Test with shorter training runs

================================================================================
TESTING THE INTEGRATION
================================================================================

Quick Test (No Training):
  python test_startup.py

This verifies:
  ? All imports resolve
  ? Config loads correctly
  ? No encoding issues
  ? Manager initialization works

Test Web Dashboard:
  python dashboard.py
  
Open browser: http://localhost:8000
Verify: Dashboard loads without errors

Test Backend API:
  Already running (mobile_dashboard_backend_fixed.py)
  API endpoints at: http://localhost:5000

Full Training Test (10 minutes):
  python main_integrated.py
  OR
  bash train.bat (Windows)

================================================================================
CURRENT PROJECT STRUCTURE
================================================================================

Core Bot:
  /                           (root directory)
  戍式 wicked_zerg_bot_pro.py  ? Main bot (4000+ lines)
  戍式 main_integrated.py       ? Training orchestrator
  戍式 config.py                ? Local config
  戍式 sc2_integration_config.py ? GitHub-compatible config

Managers (All Working):
  戍式 production_manager.py    ? Unit spawning
  戍式 economy_manager.py       ? Resource management
  戍式 combat_manager.py        ? Battle tactics
  戍式 intel_manager.py         ? Information (Blackboard)
  戍式 scouting_system.py       ? Enemy detection
  戍式 micro_controller.py      ? Unit spreading
  戌式 queen_manager.py         ? Queen control

Web/Mobile:
  戍式 dashboard.py             ? Web server (port 8000)
  戍式 mobile_app/
  弛  戍式 public/
  弛  弛  戌式 index.html        ? Dashboard UI
  弛  戌式 twa-manifest.json    ? Android config
  戍式 build.bat               ? APK build script
  戌式 build.sh                ? Shell build script

Infrastructure:
  戍式 mobile_dashboard_backend_fixed.py  ? API backend (port 5000)
  戍式 telemetry_logger.py      ? Metrics collection
  戍式 zerg_net.py              ? Neural network
  戌式 cleanup_project.py       ? Maintenance tool

================================================================================
WHAT'S READY TO DEPLOY?
================================================================================

? PRODUCTION READY:
  1. Bot Core (wicked_zerg_bot_pro.py)
  2. Training System (main_integrated.py)
  3. Web Dashboard (dashboard.py)
  4. Backend API (mobile_dashboard_backend_fixed.py)
  5. Configuration (sc2_integration_config.py)

? INFRASTRUCTURE READY (Needs User Build Execution):
  1. Android Build (setup complete, run: build.bat)
  2. PWA Deployment (all files ready)

? TRAINING READY (Can run anytime):
  1. Single Instance: python main_integrated.py
  2. Multi-Instance: python parallel_train_integrated.py

================================================================================
NEXT STEPS (Recommended Order)
================================================================================

1. TEST CURRENT SETUP (5-10 min)
   ? python test_startup.py       # Verify imports
   ? python dashboard.py          # Test web server
   ? Check backend at localhost:5000/api/health

2. VERIFY BOT WORKS (20-30 min)
   ? python main_integrated.py     # Train 1 instance for 5-10 min
   ? Monitor: Check logs for errors
   ? Expected: Bot plays 5-10 games, logs statistics

3. BUILD APK (Optional, 10-15 min build time)
   ? build.bat                    # Windows
   ? bash build.sh                # Linux/Mac
   ? Expected output: app-release-signed.apk

4. SCALE TRAINING (Optional, uses more GPU)
   ? python parallel_train_integrated.py
   ? Monitor: Check GPU memory (RTX 2060: 6GB limit)

================================================================================
TROUBLESHOOTING
================================================================================

Problem: "ModuleNotFoundError: No module named 'X'"
Solution: Run: pip install -r requirements.txt

Problem: "UTF-8 encoding error"
Solution: Use sc2_integration_config.py (ASCII-safe)
         Check mobile_dashboard_backend_fixed.py (uses ASCII only)

Problem: "Dashboard not loading"
Solution: Check port 8000 is free: netstat -ano | find "8000"
         Kill process if needed: taskkill /PID <PID> /F

Problem: "Bot not learning"
Solution: Check training_stats.json for convergence
         Run: python test_startup.py to verify config loads

Problem: "APK build fails"
Solution: Check: Node.js installed? npm installed?
         Check: Android SDK path in build.bat
         See: MOBILE_BUILD_GUIDE.md

================================================================================
FILE CLEANUP SUMMARY
================================================================================

DELETED (Redundant):
  ? mobile_dashboard_backend.py (corrupted, replaced by _fixed version)
  ? [Other obsolete files auto-removed]

REMAINING STRUCTURE: Clean, lean codebase ready for production

================================================================================
QUICK COMMAND REFERENCE
================================================================================

Development:
  python test_startup.py              # Verify setup
  python dashboard.py                 # Start web dashboard
  python main_integrated.py           # Train bot (1 instance)
  python parallel_train_integrated.py # Train bot (multi-instance)

Maintenance:
  python cleanup_project.py           # Remove obsolete files
  python check_gpu.py                 # Check CUDA availability

Deployment:
  build.bat                           # Build APK (Windows)
  bash build.sh                       # Build APK (Linux/Mac)

Monitoring:
  curl http://localhost:5000/api/health  # Check API
  curl http://localhost:8000/             # Check dashboard

================================================================================
SUCCESS CRITERIA
================================================================================

Your setup is complete when:

? test_startup.py runs without errors
? dashboard.py starts and serves http://localhost:8000
? Backend API responds at http://localhost:5000/api/health
? main_integrated.py trains for 5+ minutes without crashes
? Training statistics saved to training_stats.json

All criteria met: READY FOR PRODUCTION & DEPLOYMENT

================================================================================
SUPPORT RESOURCES
================================================================================

Documentation Files:
  - README.md - Project overview
  - QUICK_START.md - Getting started guide
  - QUICK_REFERENCE.md - Command reference
  - MOBILE_BUILD_GUIDE.md - APK building
  - OPTIMIZATION_GUIDE.md - Performance tuning

Code Examples in Managers:
  - production_manager.py (line ~2000-2500)
  - combat_manager.py (line ~500-1000)
  - intel_manager.py (line ~600-800)
  - scouting_system.py (line ~200-400)

============================================================= ===== END FILE =====
"""

if __name__ == "__main__":
    print(INTEGRATION_GUIDE)
