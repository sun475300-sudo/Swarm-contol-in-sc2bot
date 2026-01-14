#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitoring utilities for file-based data access.

Centralizes base directory resolution and JSON file loading used by
both dashboard.py (HTTP server) and dashboard_api.py (FastAPI).
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from glob import glob
from typing import Optional, Dict, Any


def get_base_dir() -> Path:
    """Resolve the base directory for monitoring data.

    Precedence:
    1) MONITORING_BASE_DIR env var (absolute or relative to CWD)
    2) Current working directory (training process location)
    """
    env_path = os.environ.get("MONITORING_BASE_DIR")
    if env_path:
        try:
            return Path(env_path).expanduser().resolve()
        except Exception:
            # Fallback to CWD if env path invalid
            return Path.cwd()
    return Path.cwd()


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def find_latest_instance_status(base_dir: Path) -> Optional[Dict[str, Any]]:
    """Find latest instance_*_status.json.

    Looks under stats/ first, then falls back to root directory.
    Returns parsed JSON dict or None.
    """
    try:
        # Prefer stats/ folder
        files = glob(str(base_dir / "stats" / "instance_*_status.json"))
        if not files:
            # Optional: also consider root as fallback
            files = glob(str(base_dir / "instance_*_status.json"))
        if files:
            latest = max(files, key=lambda p: Path(p).stat().st_mtime)
            return load_json(Path(latest))
    except Exception:
        pass
    return None


def load_training_stats(base_dir: Path) -> Optional[Dict[str, Any]]:
    """Load training_stats.json from data/ or root directory."""
    data_file = base_dir / "data" / "training_stats.json"
    if data_file.exists():
        return load_json(data_file)
    root_file = base_dir / "training_stats.json"
    if root_file.exists():
        return load_json(root_file)
    return None
