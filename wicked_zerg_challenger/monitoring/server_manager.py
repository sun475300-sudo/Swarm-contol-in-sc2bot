#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitoring Server Manager

Automatically starts/stops monitoring servers for local training and arena battles
"""

import os
import sys
import subprocess
import threading
import time
import signal
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Server ports
LOCAL_SERVER_PORT = 8001
ARENA_SERVER_PORT = 8002


class ServerManager:
    """Monitoring server manager"""

    def __init__(self, server_type: str = "local"):
        """
        Args:
            server_type: "local" (local training) or "arena" (arena battles)
        """
        self.server_type = server_type
        self.server_process: Optional[subprocess.Popen] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False

        # Server script path
        monitoring_dir = Path(__file__).parent
        if server_type == "local":
            self.server_script = monitoring_dir / "dashboard_api.py"
            self.server_port = LOCAL_SERVER_PORT
        else:  # arena
            self.server_script = monitoring_dir / "arena_dashboard_api.py"
            self.server_port = ARENA_SERVER_PORT

        logger.info(f"ServerManager initialized: type={server_type}, port={self.server_port}")

    def start_server(self, background: bool = True) -> bool:
        """Start monitoring server"""
        if self.is_running:
            logger.warning(f"Server already running on port {self.server_port}")
            return True

        if not self.server_script.exists():
            logger.error(f"Server script not found: {self.server_script}")
            return False

        try:
            # Set environment variables
            env = os.environ.copy()
            env["MONITORING_SERVER_TYPE"] = self.server_type
            env["MONITORING_PORT"] = str(self.server_port)

            # Start server
            if background:
                self.server_process = subprocess.Popen(
                    [sys.executable, str(self.server_script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    cwd=str(self.server_script.parent)
                )
                logger.info(f"Server started in background (PID: {self.server_process.pid})")
            else:
                # Run in foreground (separate thread)
                def run_server():
                    try:
                        subprocess.run(
                            [sys.executable, str(self.server_script)],
                            env=env,
                            cwd=str(self.server_script.parent)
                        )
                    except Exception as e:
                        logger.error(f"Server error: {e}")

                self.server_thread = threading.Thread(target=run_server, daemon=True)
                self.server_thread.start()
                logger.info("Server started in background thread")

            self.is_running = True
            time.sleep(2)  # Wait for server to start

            # Check server health
            if self.check_server_health():
                logger.info(f"? {self.server_type.upper()} monitoring server is running on port {self.server_port}")
                return True
            else:
                logger.warning(f"?? Server may not be responding on port {self.server_port}")
                return False

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False

    def stop_server(self) -> bool:
        """Stop monitoring server"""
        if not self.is_running:
            return True

        try:
            if self.server_process:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
                self.server_process = None

            self.is_running = False
            logger.info(f"Server stopped on port {self.server_port}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop server: {e}")
            return False

    def check_server_health(self) -> bool:
        """Check server health"""
        try:
            import requests
            url = f"http://localhost:{self.server_port}/health"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def get_server_url(self) -> str:
        """Get server URL"""
        return f"http://localhost:{self.server_port}"

    def get_api_url(self) -> str:
        """Get API URL"""
        return f"http://localhost:{self.server_port}/api"


def start_local_monitoring(background: bool = True) -> Optional[ServerManager]:
    """Start local training monitoring server"""
    manager = ServerManager(server_type="local")
    if manager.start_server(background=background):
        print(f"\n{'='*70}")
        print("? LOCAL MONITORING SERVER STARTED")
        print("="*70)
        print(f"Server URL: {manager.get_server_url()}")
        print(f"API URL: {manager.get_api_url()}")
        print(f"Web UI: {manager.get_server_url()}/ui")
        print(f"API Docs: {manager.get_server_url()}/docs")
        print(f"Health: {manager.get_server_url()}/health")
        print("="*70 + "\n")
        return manager
    return None


def start_arena_monitoring(background: bool = True) -> Optional[ServerManager]:
    """Start arena battle monitoring server"""
    manager = ServerManager(server_type="arena")
    if manager.start_server(background=background):
        print(f"\n{'='*70}")
        print("? ARENA MONITORING SERVER STARTED")
        print("="*70)
        print(f"Server URL: {manager.get_server_url()}")
        print(f"API URL: {manager.get_api_url()}")
        print(f"Web UI: {manager.get_server_url()}/ui")
        print(f"API Docs: {manager.get_server_url()}/docs")
        print(f"Health: {manager.get_server_url()}/health")
        print("="*70 + "\n")
        return manager
    return None


def auto_start_monitoring_server() -> Optional[ServerManager]:
    """
    Automatically start appropriate monitoring server based on environment

    - If --LadderServer flag present: arena server
    - Otherwise: local server
    """
    if "--LadderServer" in sys.argv:
        return start_arena_monitoring()
    else:
        return start_local_monitoring()


if __name__ == "__main__":
    # Test
    import argparse

    parser = argparse.ArgumentParser(description="Monitoring Server Manager")
    parser.add_argument("--type", choices=["local", "arena"], default="local",
                       help="Server type: local or arena")
    parser.add_argument("--stop", action="store_true",
                       help="Stop server")

    args = parser.parse_args()

    manager = ServerManager(server_type=args.type)

    if args.stop:
        manager.stop_server()
    else:
        manager.start_server()
        try:
            print(f"Server running on port {manager.server_port}")
            print("Press Ctrl+C to stop...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping server...")
            manager.stop_server()
