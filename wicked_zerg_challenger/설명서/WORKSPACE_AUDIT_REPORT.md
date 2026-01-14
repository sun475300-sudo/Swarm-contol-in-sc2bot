# Workspace Audit Report

Date: 2026-01-12
Repository: sc2AIagent (sun475300-sudo)
Root: d:/wicked_zerg_challenger

## 1) Summary
- Project is well-structured with clear separation: local training (로컬 훈련 실행), arena deployment (아레나_배포), monitoring (모니터링), docs (설명서).
- Static diagnostics: No Python analysis errors detected by editor diagnostics.
- Multiple runnable entry points detected across training, deployment, and monitoring scripts.
- Two separate requirements files exist (local vs arena) with overlapping but divergent dependencies.
- Many modules are duplicated across local and arena folders, creating drift risk.
- Non-ASCII paths and some mojibake-like text found in a few files; ensure UTF-8 everywhere.

## 2) Structure Inventory (key folders)
- Root: configs (pyrightconfig.json), virtual env (.venv/), data/logs/models/stats/tools, aiarena_submission (packaged copy), scripts, static.
- 로컬 훈련 실행/: training and integration code, reports, tools, environment checks.
- 아레나_배포/: lean deployment set, packaging/upload scripts, arena-specific requirements.
- 모니터링/: dashboard API, web assets, mobile app folder.
- 설명서/: comprehensive guides and reports.

## 3) Diagnostics
- Editor diagnostics: No errors reported (pyright type checking mode is off; missing import checks disabled).
- Note: Lack of type-checking may hide issues; consider enabling at least basic checks in CI.

## 4) Entry Points (selection)
- Local training: main_integrated.py, parallel_train_integrated.py, hybrid_learning.py, self_evolution.py, sc2_environment_checker.py, verify_integrity.py, tools/run.py
- Arena: run.py, main_integrated.py, package_for_aiarena.py, package_for_aiarena_clean.py, parallel_train_integrated.py, arena_update.py, upload_to_aiarena.py
- Monitoring: dashboard.py, dashboard_api.py, test_endpoints.py

## 5) Dependencies
- Local requirements (로컬 훈련 실행/requirements.txt): burnysc2, pysc2, torch, numpy, scipy, pandas, loguru, python-dotenv, fastapi, uvicorn, websockets, mpyq, pytest, black.
- Arena requirements (아레나_배포/requirements.txt): burnysc2, torch, numpy, loguru, sc2reader, requests, python-dotenv, fastapi, uvicorn[standard], flask, google-genai, google API clients, rich.
- Observations:
  - Both use burnysc2; imports are from `sc2.*` throughout code?ensure burnysc2 is installed in runtime.
  - Local adds pysc2 and scientific stack; Arena adds sc2reader and Google APIs.
  - Consider consolidating into a base requirements + extras (e.g., `[training]`, `[arena]`, `[monitoring]`).

## 6) Duplicate Modules (drift risk)
- Files duplicated between 로컬 훈련 실행/ and 아레나_배포/: combat_manager.py, combat_tactics.py, config.py, economy_manager.py, intel_manager.py, main_integrated.py, map_manager.py, micro_controller.py, parallel_train_integrated.py, personality_manager.py, production_manager.py, production_resilience.py, queen_manager.py, scouting_system.py, telemetry_logger.py, unit_factory.py, wicked_zerg_bot_pro.py, zerg_net.py.
- Recommendation: Centralize shared modules into a single package directory and have environment-specific shims (or a build/pack script) to copy/version them to arena package to prevent divergence.

## 7) TODO/FIXME markers
- Minimal in own code (primarily formatted comment lines). Numerous TODOs exist in vendor-like `aiarena_submission/sc2/` which is acceptable.

## 8) Encoding & i18n
- Non-ASCII folder/file names are present (Korean). Ensure all source files are UTF-8.
- Found garbled Korean text fragments in some large files (e.g., wicked_zerg_bot_pro.py), likely due to legacy encoding or copy-paste. Consider running an encoding audit and ensuring `# -*- coding: utf-8 -*-` is consistent (Python 3 defaults to UTF-8, but editors may vary).

## 9) Configuration
- pyrightconfig.json disables type checks and import warnings; excludes aiarena_submission.
- .venv/ present at root and inside 로컬 훈련 실행/.venv; prefer single env at repo root to avoid confusion.

## 10) Recommendations (actionable)
1. Dependencies
   - Unify requirements using a single `pyproject.toml` or `requirements/` folder with `base.txt`, `training.txt`, `arena.txt`, `monitoring.txt`.
   - Pin key libs to compatible minors (torch, fastapi, uvicorn, burnysc2) to ensure reproducibility.
2. Code sharing
   - Move shared modules to `src/` (e.g., `src/wicked_zerg/`) and import from both environments; update arena packaging to copy from this source.
3. Encoding hygiene
   - Run a quick UTF-8 audit; re-save any mojibake files in UTF-8. Configure `.editorconfig` with `charset = utf-8`.
4. Type safety & CI
   - Enable `pyright` in `basic` or `standard` mode in CI (keep local relaxed if desired). At minimum, enable `reportMissingImports`.
5. Tooling
   - Add `pre-commit` with `black`, `isort`, `ruff` for consistent style, and `pyproject.toml` to configure tools.
6. Environment
   - Prefer a single `.venv` at repo root; document activation/install commands.
7. Scripts
   - Add top-level `Makefile` or `scripts/` wrappers: `make train`, `make arena-package`, `make monitor`.

## 11) Quick Start (proposed)
```bash
# Create/activate a single venv at repo root (Windows PowerShell)
python -m venv .venv
./.venv/Scripts/Activate.ps1

# Install local training deps
pip install -r "로컬 훈련 실행/requirements.txt"

# Or install arena deps
pip install -r "아레나_배포/requirements.txt"

# Optional: run environment checker
python "로컬 훈련 실행/sc2_environment_checker.py"

# Run local training
python "로컬 훈련 실행/main_integrated.py"

# Run arena entry
python "아레나_배포/run.py"

# Run monitoring API
python "모니터링/dashboard_api.py"
```

## 12) Notable Files
- Training: 로컬 훈련 실행/main_integrated.py, parallel_train_integrated.py, hybrid_learning.py
- Arena: 아레나_배포/run.py, package_for_aiarena.py
- Monitoring: 모니터링/dashboard_api.py, dashboard.py
- Config: pyrightconfig.json, 로컬 훈련 실행/sc2_integration_config.py

---
End of report.
