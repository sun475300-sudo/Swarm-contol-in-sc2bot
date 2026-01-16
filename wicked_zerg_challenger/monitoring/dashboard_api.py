#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard API Server - sc2AIagent Integration
Real-time game state, combat stats, and AI control API
"""

import asyncio
import json
import requests  # type: ignore
from datetime import datetime
import logging
from pathlib import Path
import os
import secrets
from typing import List, Any, Dict

# Logging setup
logging.basicConfig(
 level = logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import bot connector if available
try:
    logger.info("? bot_api_connector imported successfully")
except ImportError:
    logger.warning("?? bot_api_connector not found - using fallback cache mode")
bot_connector = None

# Import FastAPI components
try:
 from fastapi import FastAPI, HTTPException, Depends, WebSocket, status
 from fastapi.responses import HTMLResponse
 from fastapi.security import HTTPBasic, HTTPBasicCredentials
 from fastapi.middleware.cors import CORSMiddleware
 from starlette.responses import JSONResponse as StarletteJSONResponse
except ImportError:
    raise ImportError("fastapi is required. Install with: pip install fastapi uvicorn")

# Create FastAPI app with UTF-8 JSON encoding
app = FastAPI(
    title="SC2 AI Dashboard API",
    description="StarCraft II AI agent monitoring and control API",
    version="1.0.0"
)

# Configure default JSON encoder for UTF-8
class UTF8JSONResponse(StarletteJSONResponse):
    def render(self, content: Any) -> bytes:  # type: ignore
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":")
        ).encode("utf-8")

# Override default JSONResponse
app.default_response_class = UTF8JSONResponse  # type: ignore

# Basic Auth 설정 (선택적)
# 환경변수로 활성화: MONITORING_AUTH_ENABLED = true
# 환경변수로 ID/PW 설정: MONITORING_AUTH_USER, MONITORING_AUTH_PASSWORD
_auth_enabled = os.environ.get("MONITORING_AUTH_ENABLED", "false").lower() == "true"
_auth_user = os.environ.get("MONITORING_AUTH_USER", "admin")
# Get auth credential from environment variable (avoid hardcoding)
_auth_cred = os.environ.get("MONITORING_AUTH_PASSWORD", None)
if _auth_cred is None:
    import warnings
    warnings.warn("MONITORING_AUTH_PASSWORD environment variable not set. Please set it for production use.")
    _auth_cred = ""  # Empty string - must be set via environment variable

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Basic Auth 인증 검증"""
    if not _auth_enabled:
        return True  # 인증 비활성화 시 항상 통과

    correct_username = secrets.compare_digest(credentials.username, _auth_user)
    correct_cred = secrets.compare_digest(credentials.password, _auth_cred or "")  # type: ignore

    if not (correct_username and correct_cred):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

# Add CORS middleware
# Configurable CORS: MONITORING_ALLOWED_ORIGINS (comma-separated)
_origins_env = os.environ.get("MONITORING_ALLOWED_ORIGINS")
if _origins_env:
    _allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
else:
    # Safer defaults limited to local dev
    # Android 에뮬레이터 접근 허용 (10.0.2.2는 에뮬레이터의 localhost)
    _allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://10.0.2.2:8000",  # Android 에뮬레이터
    ]

    # Ngrok 도메인 자동 추가 (동적)
    try:
        ngrok_url_file = Path(__file__).parent / ".ngrok_url.txt"
        if ngrok_url_file.exists():
            with open(ngrok_url_file, 'r', encoding='utf-8') as f:
                ngrok_url = f.read().strip()
                if ngrok_url:
                    _allowed_origins.append(ngrok_url)
                    logger.info(f"Ngrok URL added: {ngrok_url}")
    except Exception:
        pass  # Ngrok URL 파일이 없어도 계속 진행

# CORS 보안 강화: 개발 환경에서는 제한적, 프로덕션에서는 더 엄격하게
_is_production = os.environ.get("MONITORING_PRODUCTION", "false").lower() == "true"

if _is_production:
    # 프로덕션: 더 엄격한 CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,  # 명시적으로 허용된 origin만
        allow_credentials=True,
        allow_methods=["GET", "POST"],  # 필요한 메서드만
        allow_headers=["Content-Type", "Authorization"],  # 필요한 헤더만
    )
    logger.info("✅ 프로덕션 모드: 엄격한 CORS 설정 적용")
else:
    # 개발 환경: 더 관대한 설정 (개발 편의성)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("✅ 개발 모드: 관대한 CORS 설정 적용")

if _auth_enabled:
    logger.info(f"? Basic Auth 활성화됨 (사용자: {_auth_user})")
else:
    logger.warning("?? Basic Auth 비활성화됨 - 보안 위험 가능")

# Game state cache (will be updated by bot connector)
game_state_cache = {
    "current_frame": 0,
    "game_status": "READY",
    "is_running": False,
    "minerals": 50,
    "vespene": 0,
    "supply_used": 12,
    "supply_cap": 15,
    "units": {
        "zerglings": 0,
        "roaches": 0,
        "hydralisks": 0,
        "queens": 2
 },
    "threat_level": "NONE",
    "strategy_mode": "OPENING",
    "map_name": "AbyssalReefLE",
    "last_update": datetime.now().isoformat()
}

# Combat stats cache
combat_stats_cache = {
    "wins": 45,
    "losses": 44,
    "win_rate": 50.6,
    "kda_ratio": 1.96,
    "avg_army_supply": 67.3,
    "enemy_killed_supply": 4230,
    "supply_lost": 2156,
    "recent_battles": []
}

# Learning progress cache
learning_progress_cache = {
    "episode": 428,
    "total_episodes": 1000,
    "progress_percent": 42.8,
    "win_rate_trend": [35.2, 38.1, 41.5, 42.8, 45.3],
    "average_reward": 187.5,
    "loss": 0.0342,
    "training_hours": 48.5,
    "training_logs": [
        {"time": "09:45:32", "message": "Episode 428 completed"},
        {"time": "09:44:18", "message": "Loss decreased to 0.0342"},
        {"time": "09:43:05", "message": "Model checkpoint saved"}
 ]
}

# Bot config cache
bot_config_cache = {
    "strategy_mode": "OPENING",
    "auto_mode": True,
    "aggressive_mode": False,
    "build_order": ["12/12 Pool", "Zerglings"],
    "settings": {}
}

# Connected WebSocket clients
connected_clients: List[WebSocket] = []

# -----------------------------
# Shared data loading helpers
# -----------------------------
try:
    from monitoring_utils import (
        get_base_dir,
        load_json as _load_json,
        find_latest_instance_status as _find_latest_instance_status,
        load_training_stats as _load_training_stats,
    )
except ImportError:
    # Fallback if monitoring_utils is not available
    def get_base_dir() -> Path:
        """Get base directory for monitoring data"""
        return Path.cwd()

    def _load_json(path: Path) -> dict[str, Any]:  # type: ignore
        """Load JSON file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _find_latest_instance_status(base_dir: Path) -> Any:  # type: ignore
        """Find latest instance status"""
        return None

    def _load_training_stats(base_dir: Path) -> dict[str, Any]:  # type: ignore
        """Load training stats"""
        return {}

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "SC2 AI Dashboard API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "game_state": "/api/game-state",
            "combat_stats": "/api/combat-stats",
            "learning_progress": "/api/learning-progress",
            "bot_config": "/api/bot-config",
            "control": "/api/control",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/ngrok-url")
async def get_ngrok_url():
    """Get current ngrok tunnel URL"""
    try:
        # 1. Ngrok API에서 시도
        response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get("tunnels", [])
            if tunnels:
                # HTTPS 터널 우선 선택
                for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        return {
                            "url": tunnel.get("public_url", ""),
                            "status": "active",
                            "source": "ngrok_api"
                        }
                # HTTPS가 없으면 HTTP 선택
                if tunnels:
                    return {
                        "url": tunnels[0].get("public_url", ""),
                        "status": "active",
                        "source": "ngrok_api"
                    }
    except Exception:
        pass

    # 2. 저장된 파일에서 시도
    try:
        url_file = Path(__file__).parent / ".ngrok_url.txt"
        if url_file.exists():
            with open(url_file, 'r', encoding='utf-8') as f:
                url = f.read().strip()
                if url:
                    return {
                        "url": url,
                        "status": "cached",
                        "source": "file"
                    }
    except Exception:
        pass

    return {
        "url": "",
        "status": "not_found",
        "source": "none"
    }

@app.get("/api/game-state", dependencies=[Depends(verify_credentials)] if _auth_enabled else [])
async def get_game_state():
    """Get current game state"""
    # Helper function to get win rate from training stats
    def _get_win_rate(base_dir: Path) -> float:
        """Get win rate from training stats"""
        try:
            stats_file = base_dir / "data" / "training_stats.json"
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    wins = stats.get("wins", 0)
                    total = stats.get("total_games", 0)
                    if total > 0:
                        return (wins / total) * 100.0
        except Exception:
            pass
        return 0.0

    if bot_connector:
        state = bot_connector.get_game_state()
        if state:
            base_dir = get_base_dir()
            win_rate = _get_win_rate(base_dir)
            return {
                "current_frame": state.current_frame,
                "game_status": state.game_status,
                "is_running": state.is_running,
                "minerals": state.minerals,
                "vespene": state.vespene,
                "supply_used": state.supply_used,
                "supply_cap": state.supply_cap,
                "units": state.units,
                "threat_level": state.threat_level,
                "strategy_mode": state.strategy_mode,
                "map_name": state.map_name,
                "win_rate": win_rate,  # Android 앱용
                "winRate": win_rate,   # camelCase 버전도 제공
                "timestamp": state.timestamp
            }

    # Fallback: read from JSON files in current working directory
    base_dir = get_base_dir()
    status = _find_latest_instance_status(base_dir)
    win_rate = _get_win_rate(base_dir)
    if status:
        src = status.get("game_state", status)
        return {
            "current_frame": src.get("current_frame", src.get("frame", game_state_cache["current_frame"])),
            "game_status": src.get("game_status", game_state_cache["game_status"]),
            "is_running": src.get("is_running", game_state_cache["is_running"]),
            "minerals": src.get("minerals", game_state_cache["minerals"]),
            "vespene": src.get("vespene", src.get("gas", game_state_cache["vespene"])),
            "supply_used": src.get("supply_used", src.get("supply", game_state_cache["supply_used"])),
            "supply_cap": src.get("supply_cap", src.get("supply_max", game_state_cache["supply_cap"])),
            "units": src.get("units", game_state_cache["units"]),
            "threat_level": src.get("threat_level", game_state_cache["threat_level"]),
            "strategy_mode": src.get("strategy_mode", game_state_cache["strategy_mode"]),
            "map_name": src.get("map_name", game_state_cache["map_name"]),
            "win_rate": src.get("win_rate", win_rate),  # Android 앱용
            "winRate": src.get("win_rate", src.get("winRate", win_rate)),  # camelCase 버전도 제공
            "timestamp": datetime.now().isoformat()
        }

    # Fallback to cache with win_rate
    result = game_state_cache.copy()
    result["win_rate"] = float(win_rate)  # type: ignore
    result["winRate"] = float(win_rate)  # type: ignore
    return result

@app.post("/api/game-state/update")
async def update_game_state(data: dict):
    """Update game state (internal)"""
    global game_state_cache
    game_state_cache.update(data)
    game_state_cache["last_update"] = datetime.now().isoformat()
    logger.info(f"Game state updated: frame {game_state_cache['current_frame']}")
    return {"status": "updated"}

@app.get("/api/combat-stats")
async def get_combat_stats():
    """Get combat statistics"""
    if bot_connector:
        stats = bot_connector.get_combat_stats()
        if stats:
            return {
                "wins": stats.wins,
                "losses": stats.losses,
                "win_rate": stats.win_rate,
                "kda_ratio": stats.kda_ratio,
                "avg_army_supply": stats.avg_army_supply,
                "enemy_killed_supply": stats.enemy_killed_supply,
                "supply_lost": stats.supply_lost
            }

    base_dir = get_base_dir()
    ts = _load_training_stats(base_dir)
    if ts:
        wins = ts.get("wins", combat_stats_cache["wins"])
        losses = ts.get("losses", combat_stats_cache["losses"])
        total = wins + losses
        return {
            "wins": wins,
            "losses": losses,
            "win_rate": ts.get("win_rate", round((wins / max(1, total)) * 100, 2) if total > 0 else combat_stats_cache["win_rate"]),
            "kda_ratio": ts.get("kda_ratio", combat_stats_cache["kda_ratio"]),
            "avg_army_supply": ts.get("average_army_supply", combat_stats_cache["avg_army_supply"]),
            "enemy_killed_supply": ts.get("enemy_killed_supply", combat_stats_cache["enemy_killed_supply"]),
            "supply_lost": ts.get("supply_lost", combat_stats_cache["supply_lost"])
        }
    return combat_stats_cache

@app.get("/api/combat-stats/recent")
async def get_recent_battles(limit: int = 10):
    """Get recent battle records"""
    if bot_connector:
        stats = bot_connector.get_combat_stats()
        if stats:
            return {"recent_battles": []}
    return {"recent_battles": combat_stats_cache.get("recent_battles", [])}

@app.post("/api/combat-stats/record")
async def record_battle(result: dict):
    """Record new battle result"""
    logger.info(f"Battle recorded: {result}")
    return {"status": "recorded"}

@app.get("/api/learning-progress", dependencies=[Depends(verify_credentials)] if _auth_enabled else [])
async def get_learning_progress():
    """Get learning progress"""
    if bot_connector:
        progress = bot_connector.get_learning_progress()
        if progress:
            return {
                "episode": progress.episode,
                "total_episodes": progress.total_episodes,
                "progress_percent": progress.progress_percent,
                "average_reward": progress.average_reward,
                "loss": progress.loss,
                "training_hours": progress.training_hours,
                "win_rate_trend": progress.win_rate_trend,
                "training_logs": progress.training_logs
            }

    base_dir = get_base_dir()
    ts = _load_training_stats(base_dir)
    if ts:
        return {
            "episode": ts.get("episode", learning_progress_cache["episode"]),
            "total_episodes": ts.get("total_episodes", learning_progress_cache["total_episodes"]),
            "progress_percent": ts.get("progress_percent", learning_progress_cache["progress_percent"]),
            "average_reward": ts.get("average_reward", learning_progress_cache["average_reward"]),
            "loss": ts.get("loss", learning_progress_cache["loss"]),
            "training_hours": ts.get("training_hours", learning_progress_cache["training_hours"]),
            "win_rate_trend": ts.get("win_rate_trend", learning_progress_cache["win_rate_trend"]),
            "training_logs": ts.get("training_logs", learning_progress_cache.get("training_logs", []))
        }
    return learning_progress_cache

@app.post("/api/learning-progress/update")
async def update_learning_progress(data: dict):
    """Update learning progress"""
    global learning_progress_cache
    learning_progress_cache.update(data)
    logger.info(f"Learning progress updated: {data}")
    return {"status": "updated"}

@app.get("/api/bot-config")
async def get_bot_config():
    """Get bot configuration"""
    if bot_connector:
        config = bot_connector.get_bot_config()
        if config:
            return {
                "strategy_mode": config.strategy_mode,
                "auto_mode": config.auto_mode,
                "aggressive_mode": config.aggressive_mode,
                "build_order": config.build_order,
                "max_army_supply": config.max_army_supply,
                "defense_threshold": config.defense_threshold
            }
    return bot_config_cache

@app.post("/api/bot-config/update")
async def update_bot_config(data: dict):
    """Update bot configuration"""
    global bot_config_cache
    bot_config_cache.update(data)
    logger.info(f"Bot config updated: {data}")
    return {"status": "updated"}

@app.post("/api/control")
async def send_control_command(command: dict):
    """Send control command to bot"""
    cmd_type = command.get("type")

    if cmd_type == "strategy":
        strategy = command.get("value", "OPENING")
        if bot_connector:
            bot_connector.set_strategy_mode(strategy)
        logger.info(f"Strategy changed to: {strategy}")
        return {"status": "success", "message": f"Strategy changed to {strategy}"}

    elif cmd_type == "play":
        if bot_connector:
            bot_connector.resume_game()
        logger.info("Game resumed")
        return {"status": "success", "message": "Game resumed"}

    elif cmd_type == "pause":
        if bot_connector:
            bot_connector.pause_game()
        logger.info("Game paused")
        return {"status": "success", "message": "Game paused"}

    elif cmd_type == "stop":
        logger.info("Game stopped")
        return {"status": "success", "message": "Game stopped"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown command type: {cmd_type}")

@app.websocket("/ws/game-state")
async def websocket_game_state(websocket: WebSocket):
    """WebSocket endpoint for real-time game state updates.
    Sends messages in the same structure as dashboard.py broadcast:
    { type: 'game_status', game_state: {...}, units: {...}, timestamp: 'ISO' }
    """
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            state = await get_game_state()
            units = state.get("units") or state.get("unit_count") or {}
            message = {
                "type": "game_status",
                "game_state": state,
                "units": units,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(message)
            await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_clients.remove(websocket)

# Backward-compatible alias for existing frontend (ws://.../ws/game-status)
@app.websocket("/ws/game-status")
async def websocket_game_status_alias(websocket: WebSocket):
    await websocket_game_state(websocket)

# ============================================================================
# File Browser API - local_training, sc2-mobile-app, and sc2-ai-dashboard integration
# ============================================================================

# Allowed base directories for file browsing (security)
ALLOWED_BASE_DIRS = {
    "local_training": Path(__file__).parent.parent / "local_training",
    "sc2-mobile-app": Path("D:/Swarm-contol-in-sc2bot/sc2-mobile-app"),
    "sc2-ai-dashboard": Path("D:/Swarm-contol-in-sc2bot/sc2-ai-dashboard"),
}

def _validate_path(base_key: str, relative_path: str = "") -> Path:
    """Validate and resolve file path (prevent path traversal attacks)"""
    if base_key not in ALLOWED_BASE_DIRS:
        raise HTTPException(status_code=400, detail=f"Invalid base directory: {base_key}")

    base_dir = ALLOWED_BASE_DIRS[base_key]
    if not base_dir.exists():
        raise HTTPException(status_code=404, detail=f"Base directory not found: {base_dir}")

    # Resolve relative path
    if relative_path:
        # Normalize path and prevent path traversal
        normalized = os.path.normpath(relative_path)
        if normalized.startswith("..") or normalized.startswith("/"):
            raise HTTPException(status_code=403, detail="Path traversal detected")

        full_path = base_dir / normalized
        # Ensure the resolved path is still within base directory
        try:
            full_path.resolve().relative_to(base_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Path traversal detected")
    else:
        full_path = base_dir

    return full_path

@app.get("/api/files/local-training")
async def list_local_training_files(path: str = ""):
    """List files and directories in local_training folder"""
    try:
        target_path = _validate_path("local_training", path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        items = []
        if target_path.is_dir():
            for item in sorted(target_path.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    "path": str(item.relative_to(ALLOWED_BASE_DIRS["local_training"]))
                })
        else:
            # Return file info
            items.append({
                "name": target_path.name,
                "type": "file",
                "size": target_path.stat().st_size,
                "modified": datetime.fromtimestamp(target_path.stat().st_mtime).isoformat(),
                "path": str(target_path.relative_to(ALLOWED_BASE_DIRS["local_training"]))
            })

        return {
            "base": "local_training",
            "path": path,
            "items": items,
            "count": len(items)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing local_training files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/sc2-mobile-app")
async def list_sc2_mobile_app_files(path: str = ""):
    """List files and directories in sc2-mobile-app folder"""
    try:
        target_path = _validate_path("sc2-mobile-app", path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        items = []
        if target_path.is_dir():
            for item in sorted(target_path.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    "path": str(item.relative_to(ALLOWED_BASE_DIRS["sc2-mobile-app"]))
                })
        else:
            # Return file info
            items.append({
                "name": target_path.name,
                "type": "file",
                "size": target_path.stat().st_size,
                "modified": datetime.fromtimestamp(target_path.stat().st_mtime).isoformat(),
                "path": str(target_path.relative_to(ALLOWED_BASE_DIRS["sc2-mobile-app"]))
            })

        return {
            "base": "sc2-mobile-app",
            "path": path,
            "items": items,
            "count": len(items)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing sc2-mobile-app files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/sc2-ai-dashboard")
async def list_sc2_ai_dashboard_files(path: str = ""):
    """List files and directories in sc2-ai-dashboard folder"""
    try:
        target_path = _validate_path("sc2-ai-dashboard", path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        items = []
        if target_path.is_dir():
            for item in sorted(target_path.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    "path": str(item.relative_to(ALLOWED_BASE_DIRS["sc2-ai-dashboard"]))
                })
        else:
            # Return file info
            items.append({
                "name": target_path.name,
                "type": "file",
                "size": target_path.stat().st_size,
                "modified": datetime.fromtimestamp(target_path.stat().st_mtime).isoformat(),
                "path": str(target_path.relative_to(ALLOWED_BASE_DIRS["sc2-ai-dashboard"]))
            })

        return {
            "base": "sc2-ai-dashboard",
            "path": path,
            "items": items,
            "count": len(items)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing sc2-ai-dashboard files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/content")
async def get_file_content(base: str, path: str, max_size: int = 1024 * 1024):  # 1MB limit
    """Get file content (text files only, with size limit)"""
    try:
        target_path = _validate_path(base, path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is a directory, not a file")

        # Check file size
        file_size = target_path.stat().st_size
        if file_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size} bytes). Maximum size: {max_size} bytes"
            )

        # Determine if it's a text file
        text_extensions = {'.txt', '.py', '.js', '.ts', '.tsx', '.json', '.md', '.yml', '.yaml',
                          '.xml', '.html', '.css', '.log', '.csv', '.ini', '.cfg', '.toml'}
        is_text = target_path.suffix.lower() in text_extensions

        if is_text:
            try:
                with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                return {
                    "base": base,
                    "path": path,
                    "content": content,
                    "type": "text",
                    "size": file_size,
                    "encoding": "utf-8"
                }
            except Exception as e:
                logger.error(f"Error reading text file: {e}")
                raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
        else:
            # Binary file - return metadata only
            return {
                "base": base,
                "path": path,
                "content": None,
                "type": "binary",
                "size": file_size,
                "message": "Binary file - content not available. Use download endpoint."
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/stats")
async def get_folder_stats(base: str, path: str = ""):
    """Get folder statistics (file count, total size, etc.)"""
    try:
        target_path = _validate_path(base, path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        total_files = 0
        total_dirs = 0
        total_size = 0

        for item in target_path.rglob("*"):
            if item.is_file():
                total_files += 1
                total_size += item.stat().st_size
            elif item.is_dir():
                total_dirs += 1

        return {
            "base": base,
            "path": path,
            "statistics": {
                "files": total_files,
                "directories": total_dirs,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting folder stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Simple UI route to serve dashboard.html via FastAPI
@app.get("/ui", response_class=HTMLResponse)
async def serve_dashboard_ui():
    html_path = Path(__file__).parent / "dashboard.html"
    if html_path.exists():
        with html_path.open("r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content, media_type="text/html; charset=utf-8")
    raise HTTPException(status_code=404, detail="dashboard.html not found")

# ============================================================================
# Manus.im API Integration - Enhanced Analytics & Monitoring
# ============================================================================

# Import Manus client
try:
    from monitoring.manus_dashboard_client import ManusDashboardClient, create_client_from_env  # type: ignore
    manus_client = create_client_from_env()  # type: ignore
    if manus_client and manus_client.enabled:
        logger.info("✅ Manus.im API client initialized successfully")
    else:
        manus_client = None
        logger.warning("⚠️ Manus.im API client disabled or not configured")
except ImportError:
    manus_client = None
    logger.warning("⚠️ Manus dashboard client not available")

# Manus API proxy endpoints
@app.get("/api/manus/game-sessions")
async def get_manus_game_sessions(limit: int = 20):
    """Get recent game sessions from Manus API"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        # Call Manus API to get recent sessions
        response = manus_client._call_trpc("game.getSessions", {"limit": limit}, retry=True)
        if response:
            return {
                "success": True,
                "data": response.get("sessions", []),
                "count": len(response.get("sessions", []))
            }
        return {"success": False, "data": [], "count": 0}
    except Exception as e:
        logger.error(f"Error fetching Manus game sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manus/game-stats")
async def get_manus_game_stats():
    """Get game statistics from Manus API"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        response = manus_client._call_trpc("game.getStats", {}, retry=True)
        if response:
            return {"success": True, "data": response}
        return {"success": False, "data": {}}
    except Exception as e:
        logger.error(f"Error fetching Manus game stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manus/training-episodes")
async def get_manus_training_episodes(limit: int = 20):
    """Get recent training episodes from Manus API"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        response = manus_client._call_trpc("training.getEpisodes", {"limit": limit}, retry=True)
        if response:
            return {
                "success": True,
                "data": response.get("episodes", []),
                "count": len(response.get("episodes", []))
            }
        return {"success": False, "data": [], "count": 0}
    except Exception as e:
        logger.error(f"Error fetching Manus training episodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manus/training-stats")
async def get_manus_training_stats():
    """Get training statistics from Manus API"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        response = manus_client._call_trpc("training.getStats", {}, retry=True)
        if response:
            return {"success": True, "data": response}
        return {"success": False, "data": {}}
    except Exception as e:
        logger.error(f"Error fetching Manus training stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manus/arena-stats")
async def get_manus_arena_stats():
    """Get Arena statistics from Manus API"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        response = manus_client._call_trpc("arena.getStats", {}, retry=True)
        if response:
            return {"success": True, "data": response}
        return {"success": False, "data": {}}
    except Exception as e:
        logger.error(f"Error fetching Manus arena stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manus/bot-configs")
async def get_manus_bot_configs():
    """Get bot configurations from Manus API"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        response = manus_client._call_trpc("botConfig.getAll", {}, retry=True)
        if response:
            return {
                "success": True,
                "data": response.get("configs", []),
                "count": len(response.get("configs", []))
            }
        return {"success": False, "data": [], "count": 0}
    except Exception as e:
        logger.error(f"Error fetching Manus bot configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manus/active-config")
async def get_manus_active_config():
    """Get active bot configuration from Manus API"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        response = manus_client._call_trpc("botConfig.getActive", {}, retry=True)
        if response:
            return {"success": True, "data": response.get("activeConfig")}
        return {"success": False, "data": None}
    except Exception as e:
        logger.error(f"Error fetching Manus active config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics & Insights endpoints
@app.get("/api/analytics/performance-trends")
async def get_performance_trends(days: int = 7):
    """Get performance trends from Manus API data"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        # Get recent sessions
        sessions_response = manus_client._call_trpc("game.getSessions", {"limit": 100}, retry=True)
        if not sessions_response:
            return {"success": False, "data": {}}

        sessions = sessions_response.get("sessions", [])

        # Calculate trends
        wins = sum(1 for s in sessions if s.get("result") == "Victory")
        losses = sum(1 for s in sessions if s.get("result") == "Defeat")
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0

        avg_duration = sum(s.get("duration", 0) for s in sessions) / len(sessions) if sessions else 0
        avg_minerals = sum(s.get("finalMinerals", 0) for s in sessions) / len(sessions) if sessions else 0

        # Race-based statistics
        race_stats = {}
        for session in sessions:
            race = session.get("enemyRace", "Unknown")
            if race not in race_stats:
                race_stats[race] = {"wins": 0, "losses": 0, "total": 0}
            if session.get("result") == "Victory":
                race_stats[race]["wins"] += 1
            else:
                race_stats[race]["losses"] += 1
            race_stats[race]["total"] += 1

        # Calculate win rates per race
        race_win_rates = {}
        for race, stats in race_stats.items():
            if stats["total"] > 0:
                race_win_rates[race] = {
                    "winRate": stats["wins"] / stats["total"] * 100,
                    "wins": stats["wins"],
                    "losses": stats["losses"],
                    "total": stats["total"]
                }

        return {
            "success": True,
            "data": {
                "overall": {
                    "winRate": round(win_rate, 2),
                    "wins": wins,
                    "losses": losses,
                    "total": total,
                    "avgDuration": round(avg_duration, 2),
                    "avgMinerals": round(avg_minerals, 2)
                },
                "byRace": race_win_rates,
                "period": f"Last {days} days",
                "sampleSize": len(sessions)
            }
        }
    except Exception as e:
        logger.error(f"Error calculating performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/training-trends")
async def get_training_trends(limit: int = 50):
    """Get training trends and insights from Manus API"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        # Get training stats
        stats_response = manus_client._call_trpc("training.getStats", {}, retry=True)
        episodes_response = manus_client._call_trpc("training.getEpisodes", {"limit": limit}, retry=True)

        if not stats_response or not episodes_response:
            return {"success": False, "data": {}}

        episodes = episodes_response.get("episodes", [])

        # Calculate trends
        if episodes:
            rewards = [e.get("reward", 0) for e in episodes]
            win_rates = [e.get("winRate", 0) * 100 for e in episodes]
            losses = [e.get("loss", 0) for e in episodes]

            reward_trend = "improving" if len(rewards) > 1 and rewards[-1] > rewards[0] else "declining"
            win_rate_trend = "improving" if len(win_rates) > 1 and win_rates[-1] > win_rates[0] else "declining"
            loss_trend = "decreasing" if len(losses) > 1 and losses[-1] < losses[0] else "increasing"
        else:
            reward_trend = "unknown"
            win_rate_trend = "unknown"
            loss_trend = "unknown"
            rewards = []
            win_rates = []
            losses = []

        return {
            "success": True,
            "data": {
                "stats": stats_response,
                "trends": {
                    "reward": reward_trend,
                    "winRate": win_rate_trend,
                    "loss": loss_trend
                },
                "recentEpisodes": {
                    "count": len(episodes),
                    "avgReward": round(sum(rewards) / len(rewards), 2) if rewards else 0,
                    "avgWinRate": round(sum(win_rates) / len(win_rates), 2) if win_rates else 0,
                    "avgLoss": round(sum(losses) / len(losses), 6) if losses else 0
                }
            }
        }
    except Exception as e:
        logger.error(f"Error calculating training trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/insights")
async def get_insights():
    """Get AI-powered insights and recommendations"""
    if not manus_client:
        raise HTTPException(status_code=503, detail="Manus API client not available")

    try:
        # Get all relevant data
        game_stats = manus_client._call_trpc("game.getStats", {}, retry=True)
        training_stats = manus_client._call_trpc("training.getStats", {}, retry=True)
        arena_stats = manus_client._call_trpc("arena.getStats", {}, retry=True)

        insights = []
        recommendations = []

        # Analyze game performance
        if game_stats:
            total_games = game_stats.get("totalGames", 0)
            wins = game_stats.get("wins", 0)
            win_rate = game_stats.get("winRate", 0)

            if total_games > 10:
                if win_rate < 0.5:
                    insights.append({
                        "type": "warning",
                        "category": "performance",
                        "message": f"승률이 {win_rate*100:.1f}%로 낮습니다. 전략 개선이 필요합니다."
                    })
                    recommendations.append({
                        "priority": "high",
                        "category": "strategy",
                        "action": "현재 전략을 재검토하고 더 효과적인 빌드 오더를 시도해보세요."
                    })
                elif win_rate > 0.6:
                    insights.append({
                        "type": "success",
                        "category": "performance",
                        "message": f"승률이 {win_rate*100:.1f}%로 우수합니다!"
                    })

        # Analyze training progress
        if training_stats:
            total_episodes = training_stats.get("totalEpisodes", 0)
            avg_reward = training_stats.get("averageReward", 0)

            if total_episodes > 100:
                if avg_reward < 100:
                    insights.append({
                        "type": "info",
                        "category": "training",
                        "message": "평균 보상이 낮습니다. 학습 파라미터 조정을 고려해보세요."
                    })
                    recommendations.append({
                        "priority": "medium",
                        "category": "training",
                        "action": "학습률(learning rate)을 조정하거나 보상 함수를 최적화해보세요."
                    })

        # Analyze Arena performance
        if arena_stats:
            current_elo = arena_stats.get("currentELO", 0)
            arena_win_rate = arena_stats.get("winRate", 0)

            if current_elo > 0:
                if current_elo < 1400:
                    insights.append({
                        "type": "info",
                        "category": "arena",
                        "message": f"현재 ELO: {current_elo}. 더 높은 레이팅을 위해 실력 향상이 필요합니다."
                    })
                elif current_elo > 1800:
                    insights.append({
                        "type": "success",
                        "category": "arena",
                        "message": f"현재 ELO: {current_elo}. 우수한 성적입니다!"
                    })

        return {
            "success": True,
            "data": {
                "insights": insights,
                "recommendations": recommendations,
                "generatedAt": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manus/health")
async def check_manus_health():
    """Check Manus API connection health"""
    if not manus_client:
        return {
            "available": False,
            "status": "disabled",
            "message": "Manus API client not configured"
        }

    try:
        is_healthy = manus_client.health_check()
        return {
            "available": True,
            "status": "healthy" if is_healthy else "unhealthy",
            "baseUrl": manus_client.base_url,
            "enabled": manus_client.enabled,
            "hasApiKey": bool(manus_client.api_key)
        }
    except Exception as e:
        logger.error(f"Error checking Manus health: {e}")
        return {
            "available": False,
            "status": "error",
            "message": str(e)
        }

# ============================================================================
# Server startup
# ============================================================================

if __name__ == "__main__":
 import uvicorn
 uvicorn.run(
 app,
        host="0.0.0.0",
 port = 8001,
        log_level="info"
 )
