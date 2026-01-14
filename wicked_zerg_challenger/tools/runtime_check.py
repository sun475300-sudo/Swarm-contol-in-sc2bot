"""tools/runtime_check.py
Comprehensive runtime & static-check tool for Wicked Zerg Challenger
- Environment checks (Python, optional packages, nvidia-smi, SC2PATH)
- Static syntax scan across .py files using ast.parse
- Optional dry-run import checks (spawns subprocess to import modules)
- Writes a timestamped log to logs/runtime_check_<timestamp>.log

Usage:
    python tools/runtime_check.py [--no-import] [--modules wicked_zerg_bot_pro,main_integrated]
"""

from __future__ import annotations

import argparse
import ast
import datetime
import logging
import os
import subprocess
import sys
from typing import List, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGS_DIR = os.path.join(ROOT, "logs")
EXCLUDE_DIRS = {"venv", ".venv", "__pycache__", "models", "Maps", "replays"}

RECOMMENDED_PY_MIN = (3, 10)
RECOMMENDED_PY_SUGGEST = (3, 12)


def setup_logger() -> logging.Logger:
    if not os.path.isdir(LOGS_DIR):
        os.makedirs(LOGS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(LOGS_DIR, f"runtime_check_{ts}.log")

    logger = logging.getLogger("runtime_check")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info(f"Log file: {log_path}")
    return logger


def find_py_files(root: str) -> List[str]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # skip excluded dirs
        parts = {p for p in dirpath.split(os.sep)}
        if parts & EXCLUDE_DIRS:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                files.append(os.path.join(dirpath, fn))
    return sorted(files)


def check_syntax(file_path: str) -> Tuple[bool, str]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        ast.parse(source)
        return True, ""
    except SyntaxError as e:
        text = e.text.strip() if e.text else "N/A"
        msg = f"SyntaxError: {e.msg} at line {e.lineno}: {text}"
        return False, msg
    except Exception as e:
        return False, f"Exception parsing AST: {type(e).__name__}: {e}"


def run_env_checks(logger: logging.Logger) -> int:
    logger.info("Running environment checks...")
    exit_code = 0

    py_ver = sys.version_info
    logger.info(f"Python version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < RECOMMENDED_PY_MIN:
        logger.warning(
            f"Python < {RECOMMENDED_PY_MIN[0]}.{RECOMMENDED_PY_MIN[1]} detected - some features may fail"
        )
        exit_code = max(exit_code, 1)
    elif py_ver < RECOMMENDED_PY_SUGGEST:
        logger.info(
            f"Consider using Python {RECOMMENDED_PY_SUGGEST[0]}.{RECOMMENDED_PY_SUGGEST[1]} for best compatibility"
        )

    # Check recommended packages
    for module in ("burnysc2", "torch", "loguru"):
        try:
            __import__(module)
            logger.info(f"[OK] {module} module available")
        except Exception:
            logger.warning(f"[MISSING] {module} module not found")
            exit_code = max(exit_code, 1)

    # Check nvidia-smi
    try:
        cp = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if cp.returncode == 0 and cp.stdout.strip():
            logger.info("nvidia-smi found. GPU info:\n" + cp.stdout.strip())
        else:
            logger.info(
                "nvidia-smi not available or returned no data (may be CPU-only or driver not installed)"
            )
    except Exception as e:
        logger.info("nvidia-smi not available: %s" % e)

    # SC2PATH
    sc2path = os.environ.get("SC2PATH")
    if sc2path:
        if os.path.exists(sc2path):
            logger.info(f"SC2PATH set: {sc2path} (path exists)")
        else:
            logger.warning(f"SC2PATH set: {sc2path} (path does not exist)")
            exit_code = max(exit_code, 1)
    else:
        logger.warning("SC2PATH environment variable is not set")
        exit_code = max(exit_code, 1)

    return exit_code


def run_syntax_scan(root: str, logger: logging.Logger) -> int:
    logger.info("Starting static syntax scan (AST parse) across repository...")
    py_files = find_py_files(root)
    logger.info(
        f"Found {len(py_files)} Python files to scan (excluding venv/models/Maps/replays)..."
    )

    errors = []
    for p in py_files:
        ok, msg = check_syntax(p)
        if not ok:
            logger.error(f"[SYNTAX ERROR] {p}: {msg}")
            errors.append((p, msg))
    if errors:
        logger.warning(f"Syntax scan completed with {len(errors)} file(s) reporting errors.")
        return 2
    logger.info("Syntax scan completed: no syntax errors found.")
    return 0


def import_check(module_name: str, timeout: int = 12) -> Tuple[bool, str]:
    """Attempt to import a module in a subprocess to detect import-time errors without running in-process."""
    python = sys.executable
    cmd = [
        python,
        "-c",
        f"import importlib,sys; importlib.invalidate_caches(); import {module_name}",
    ]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if cp.returncode == 0:
            return True, cp.stdout.strip()
        else:
            # Prefer stderr message
            out = cp.stderr.strip() or cp.stdout.strip()
            return False, out
    except subprocess.TimeoutExpired:
        return False, "Import check timed out"
    except Exception as e:
        return False, f"Import check exception: {e}"


def run_dry_imports(modules: List[str], logger: logging.Logger) -> int:
    logger.info("Running dry-run import checks for modules: %s" % ", ".join(modules))
    errors = []
    for m in modules:
        ok, msg = import_check(m)
        if ok:
            logger.info(f"[OK] Imported {m} (subprocess)")
        else:
            logger.error(f"[IMPORT ERROR] {m}: {msg}")
            errors.append((m, msg))
    if errors:
        logger.warning(
            f"Dry-run import check finished with {len(errors)} module(s) failing to import."
        )
        return 3
    logger.info("Dry-run import checks successful.")
    return 0


def parse_args():
    p = argparse.ArgumentParser(description="Runtime & static checker for Wicked Zerg Challenger")
    p.add_argument("--no-import", action="store_true", help="Skip dry-run import checks")
    p.add_argument(
        "--modules",
        type=str,
        default="wicked_zerg_bot_pro,main_integrated",
        help="Comma-separated modules for dry-run import (default: wicked_zerg_bot_pro,main_integrated)",
    )
    p.add_argument("--root", type=str, default=ROOT, help="Project root (defaults to repo root)")
    return p.parse_args()


def main():
    args = parse_args()
    logger = setup_logger()

    overall_code = 0

    overall_code = max(overall_code, run_env_checks(logger))

    overall_code = max(overall_code, run_syntax_scan(args.root, logger))

    if not args.no_import:
        modules = [m.strip() for m in args.modules.split(",") if m.strip()]
        overall_code = max(overall_code, run_dry_imports(modules, logger))
    else:
        logger.info("Skipping dry-run import checks (--no-import)")

    if overall_code == 0:
        logger.info("\n[SUCCESS] Runtime check completed with no critical issues detected.")
    else:
        logger.warning("\n[NOTICE] Runtime check completed with issues. See log for details.")

    # Exit with code for automation
    sys.exit(overall_code)


if __name__ == "__main__":
    main()
