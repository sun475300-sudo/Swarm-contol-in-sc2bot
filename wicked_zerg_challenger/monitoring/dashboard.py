#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile Dashboard Server
Real-time monitoring for StarCraft 2 Wicked Zerg AI
"""

import http.server
import socketserver
import socket
import os
import json
import subprocess
import threading
import time
import struct
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from glob import glob
from monitoring_utils import (
    get_base_dir,
    load_json as _load_json,
    find_latest_instance_status as _find_latest_instance_status,
    load_training_stats as _load_training_stats,
)

PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(__file__), "mobile_app", "public")

# Game state cache
GAME_STATE = {
    "is_running": False,
    "current_frame": 0,
    "minerals": 0,
    "vespene": 0,
    "supply_used": 0,
    "supply_cap": 15,
    "unit_count": {"zerglings": 0, "roaches": 0, "hydras": 0},
    "win_rate": 45.3,
    "total_games": 42,
    "current_map": "AbyssalReefLE",
    "threat_level": "NONE",
    "strategy_mode": "OPENING"
}

# -----------------------------
# Data loading helpers are imported from monitoring_utils
# -----------------------------

def _build_game_state(base_dir: Path) -> dict:
    # Start with defaults
    state = dict(GAME_STATE)
    status = _find_latest_instance_status(base_dir)
    if status:
        # Flexible mapping: support nested or flat structures
        src = status.get("game_state", status)
        state["is_running"] = src.get("is_running", state["is_running"])
        state["current_frame"] = src.get("current_frame", src.get("frame", state["current_frame"]))
        state["minerals"] = src.get("minerals", state["minerals"])
        state["vespene"] = src.get("vespene", src.get("gas", state["vespene"]))
        state["supply_used"] = src.get("supply_used", src.get("supply", state["supply_used"]))
        state["supply_cap"] = src.get("supply_cap", src.get("supply_max", state["supply_cap"]))
        units = src.get("unit_count", src.get("units", state["unit_count"]))
        if isinstance(units, dict):
            # Merge known unit keys
            merged = dict(state["unit_count"])
            merged.update({
                "zerglings": units.get("zerglings", merged.get("zerglings", 0)),
                "roaches": units.get("roaches", merged.get("roaches", 0)),
                "hydras": units.get("hydras", units.get("hydralisks", merged.get("hydras", 0)))
            })
            state["unit_count"] = merged
        state["win_rate"] = src.get("win_rate", state["win_rate"])
        state["total_games"] = src.get("total_games", src.get("game_id", state["total_games"]))
        state["current_map"] = src.get("current_map", src.get("map_name", state["current_map"]))
        state["threat_level"] = src.get("threat_level", state["threat_level"])
        state["strategy_mode"] = src.get("strategy_mode", state["strategy_mode"])
    else:
        # Fallback to training stats
        ts = _load_training_stats(base_dir)
        if ts:
            state["win_rate"] = ts.get("win_rate", state["win_rate"])
            state["total_games"] = ts.get("total_games", state["total_games"])
    return state

def _build_combat_stats(base_dir: Path) -> dict:
    # Defaults as previously shown
    defaults = {
        "total_battles": 152,
        "wins": 89,
        "losses": 63,
        "average_army_supply": 67.3,
        "enemy_killed_supply": 4230,
        "supply_lost": 2156,
        "kda_ratio": 1.96
    }
    ts = _load_training_stats(base_dir)
    if not ts:
        return defaults
    wins = ts.get("wins", defaults["wins"])
    losses = ts.get("losses", defaults["losses"])
    total = wins + losses
    return {
        "total_battles": ts.get("total_battles", total if total > 0 else defaults["total_battles"]),
        "wins": wins,
        "losses": losses,
        "average_army_supply": ts.get("average_army_supply", defaults["average_army_supply"]),
        "enemy_killed_supply": ts.get("enemy_killed_supply", defaults["enemy_killed_supply"]),
        "supply_lost": ts.get("supply_lost", defaults["supply_lost"]),
        "kda_ratio": ts.get("kda_ratio", (wins / max(1, losses)) if total > 0 else defaults["kda_ratio"]),
        "win_rate": ts.get("win_rate", round((wins / max(1, total)) * 100, 2) if total > 0 else 0.0)
    }

def _build_learning_progress(base_dir: Path) -> dict:
    defaults = {
        "episode": 428,
        "total_episodes": 1000,
        "win_rate_trend": [35.2, 38.1, 41.5, 42.8, 45.3],
        "average_reward": 187.5,
        "loss": 0.0342,
        "training_hours": 48.5
    }
    ts = _load_training_stats(base_dir)
    if not ts:
        return defaults
    return {
        "episode": ts.get("episode", defaults["episode"]),
        "total_episodes": ts.get("total_episodes", defaults["total_episodes"]),
        "win_rate_trend": ts.get("win_rate_trend", defaults["win_rate_trend"]),
        "average_reward": ts.get("average_reward", defaults["average_reward"]),
        "loss": ts.get("loss", defaults["loss"]),
        "training_hours": ts.get("training_hours", defaults["training_hours"])
    }

# WebSocket connections registry
ws_clients = []
ws_lock = threading.Lock()

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Dashboard request handler with API endpoints"""

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    project_root = os.path.dirname(__file__)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def end_headers(self):
        """Override to add UTF-8 charset to all responses"""
        # Only add charset if Content-Type is not already set with charset
        content_type = self.headers.get('Content-Type', '')
        if not 'charset' in content_type:
            if 'text' in content_type or 'html' in content_type or 'json' in content_type:
                self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        super().end_headers()

    def translate_path(self, path):
        """Override to serve /static from project root as well as WEB_DIR"""
        # Root path defaults to index.html
        if path == '/':
            return os.path.join(WEB_DIR, 'index.html')
        # If request is for /static/*, try project root first
        if path.startswith('/static/'):
            relative_path = path[1:]
            project_static_path = os.path.join(self.project_root, relative_path)
            if os.path.isfile(project_static_path):
                return project_static_path
            return super().translate_path(path)
        return super().translate_path(path)

    def guess_type(self, path):
        """Override to force UTF-8 charset for text files"""
        mimetype = super().guess_type(path)
        if isinstance(mimetype, tuple):
            mtype, encoding = mimetype
            if mtype and ('text' in mtype or 'javascript' in mtype or 'json' in mtype):
                return mtype + '; charset=utf-8', encoding
            return mimetype
        return mimetype

    def do_GET(self):
        """Handle GET requests with API endpoints"""
        # API: Game state
        if self.path == '/api/game-state':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            # Use current working directory (training process location)
            base_dir = get_base_dir()
            payload = _build_game_state(base_dir)
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            return

        # API: Combat stats
        if self.path == '/api/combat-stats':
            base_dir = get_base_dir()
            stats = _build_combat_stats(base_dir)
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(stats, ensure_ascii=False).encode('utf-8'))
            return

        # API: Learning progress
        if self.path == '/api/learning-progress':
            base_dir = get_base_dir()
            progress = _build_learning_progress(base_dir)
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(progress, ensure_ascii=False).encode('utf-8'))
            return

        # API: Code health summary (placeholder or derived)
        if self.path == '/api/code-health':
            base_dir = get_base_dir()
            # Simple derived summary from training stats if present
            ts = _load_training_stats(base_dir) or {}
            issues = ts.get("top_issues", [])
            payload = {
                "healthy": ts.get("healthy", 0),
                "average_health": ts.get("average_health", 0.0),
                "total_issues": ts.get("total_issues", len(issues)),
                "critical": ts.get("critical", 0),
                "top_issues": issues,
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            return

        # API: Bugs list (placeholder)
        if self.path == '/api/bugs':
            payload = {"bugs": []}
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            return

        # Default: serve files
        super().do_GET()

    def log_message(self, format_str, *args):
        """Format log messages"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format_str % args}")

    def do_POST(self):
        """Handle POST endpoints"""
        if self.path == '/api/code-scan':
            # Placeholder scan trigger; return success
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "scan_started"}, ensure_ascii=False).encode('utf-8'))
            return
        # Fallback to default POST handling
        return super().do_POST()


def ensure_html_exists():
    """Create index.html if missing"""
    index_html = os.path.join(WEB_DIR, "index.html")
    if not os.path.exists(index_html):
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wicked Zerg Monitor</title>
    <style>
        body {
            background-color: #1a1a2e;
            color: #00ff00;
            font-family: monospace;
            padding: 20px;
        }
        h1 { border-bottom: 2px solid #00ff00; padding-bottom: 10px; }
        .card {
            border: 1px solid #00ff00;
            padding: 15px;
            margin: 15px 0;
            background: #16213e;
            border-radius: 5px;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
        }
    </style>
</head>
<body>
    <h1>Wicked Zerg Monitor</h1>
    <div class="card">
        <h3>System Status</h3>
        <div class="stat">
            <span>Server:</span>
            <span id="status">ONLINE</span>
        </div>
        <div class="stat">
            <span>Time:</span>
            <span id="time">--:--:--</span>
        </div>
    </div>
    <div class="card">
        <h3>Live Log</h3>
        <div id="logs">
            <p>Dashboard loaded</p>
        </div>
    </div>
    <script>
        setInterval(() => {
            document.getElementById('time').innerText = new Date().toLocaleTimeString();
        }, 1000);
    </script>
</body>
</html>"""

        os.makedirs(WEB_DIR, exist_ok=True)
        with open(index_html, "w", encoding="utf-8") as f:
            f.write(html_content)

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def find_available_server(start_port: int, handler: http.server.BaseHTTPRequestHandler, max_tries: int = 20):
    """Try to bind a server from start_port upward, returning (server, port)."""
    for p in range(start_port, start_port + max_tries):
        try:
            srv = ReusableTCPServer(("", p), handler)
            return srv, p
        except OSError:
            continue
    return None, None

def write_port_file(port: int):
    """Write the selected port to a file for other scripts (e.g., ngrok)."""
    try:
        port_file = os.path.join(os.path.dirname(__file__), ".dashboard_port")
        with open(port_file, "w", encoding="utf-8") as f:
            f.write(str(port))
    except Exception:
        # Non-fatal if writing fails
        pass

def broadcast_game_state(base_dir: Path):
    """Continuously broadcast game state to WebSocket clients."""
    while True:
        try:
            # Use current working directory for latest data
            state = _build_game_state(get_base_dir())
            message = json.dumps({
                "type": "game_status",
                "game_state": state,
                "units": state.get("unit_count", {}),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)

            payload = message.encode('utf-8')
            frame = bytearray()
            frame.append(0x81)  # FIN + TEXT frame

            if len(payload) < 126:
                frame.append(len(payload))
            elif len(payload) < 65536:
                frame.append(126)
                frame.extend(struct.pack('!H', len(payload)))
            else:
                frame.append(127)
                frame.extend(struct.pack('!Q', len(payload)))

            frame.extend(payload)

            with ws_lock:
                for client in list(ws_clients):
                    try:
                        client.write(bytes(frame))
                        client.flush()
                    except Exception:
                        if client in ws_clients:
                            ws_clients.remove(client)

            time.sleep(0.5)  # Update every 500ms
        except Exception as e:
            print(f"[WS Broadcast Error] {e}")
            time.sleep(1)


if __name__ == "__main__":
    ensure_html_exists()
    # Allow overriding via env vars
    start_port = int(os.environ.get("DASHBOARD_PORT", os.environ.get("PORT", PORT)))

    server, chosen_port = find_available_server(start_port, DashboardHandler, max_tries=50)
    if server is None:
        print("[ERROR] No available port found near", start_port)
        raise SystemExit(1)

    write_port_file(chosen_port)
    print(f"Server ready: http://localhost:{chosen_port}")
    print(f"Serving from: {WEB_DIR}")
    print(f"WebSocket: ws://localhost:{chosen_port}/ws/game-status")
    print("Press Ctrl+C to stop\n")

    # Optionally start FastAPI backend for advanced controls on port 8001
    try:
        auto_start = os.environ.get("START_FASTAPI", "0") == "1"
        if auto_start:
            # Spawn: uvicorn dashboard_api:app --host 0.0.0.0 --port 8001
            subprocess.Popen([
                "python", "-m", "uvicorn", "dashboard_api:app", "--host", "0.0.0.0", "--port", "8001"
            ], cwd=os.path.dirname(__file__))
            print("FastAPI backend (dashboard_api.py) auto-started on port 8001")
    except Exception as e:
        print(f"[WARN] Failed to auto-start FastAPI backend: {e}")

    # Start WebSocket broadcast thread
    ws_thread = threading.Thread(target=broadcast_game_state, args=(Path.cwd(),), daemon=True)
    ws_thread.start()

    try:
        with server as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
