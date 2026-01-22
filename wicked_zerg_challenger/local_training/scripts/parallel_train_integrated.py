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


if __name__ == "__main__":
    main()
