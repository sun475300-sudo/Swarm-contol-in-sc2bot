#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard API Server - sc2AIagent Integration
Real-time game state, combat stats, and AI control API
"""

import asyncio
import json
import requests
from datetime import datetime
import logging
from pathlib import Path
import os
import secrets

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

# Create FastAPI app with UTF-8 JSON encoding
app = FastAPI(
    title="SC2 AI Dashboard API",
    description="StarCraft II AI agent monitoring and control API",
    version="1.0.0"
)

# Configure default JSON encoder for UTF-8

class UTF8JSONResponse(StarletteJSONResponse):
 def render(self, content) -> bytes:
 return json.dumps(
 content,
 ensure_ascii = False,
 allow_nan = False,
 indent = None,
            separators=(",", ":")
        ).encode("utf-8")

# Override default JSONResponse
app.default_response_class = UTF8JSONResponse

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
_auth_password = _auth_cred  # Alias for backward compatibility

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Basic Auth 인증 검증"""
 if not _auth_enabled:
 return True # 인증 비활성화 시 항상 통과

 correct_username = secrets.compare_digest(credentials.username, _auth_user)
 correct_password = secrets.compare_digest(credentials.password, _auth_password)

 if not (correct_username and correct_password):
 raise HTTPException(
 status_code = status.HTTP_401_UNAUTHORIZED,
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
 pass # Ngrok URL 파일이 없어도 계속 진행

# CORS 보안 강화: 개발 환경에서는 제한적, 프로덕션에서는 더 엄격하게
_is_production = os.environ.get("MONITORING_PRODUCTION", "false").lower() == "true"

if _is_production:
 # 프로덕션: 더 엄격한 CORS 설정
 app.add_middleware(
 CORSMiddleware,
 allow_origins = _allowed_origins, # 명시적으로 허용된 origin만
 allow_credentials = True,
        allow_methods=["GET", "POST"],  # 필요한 메서드만
        allow_headers=["Content-Type", "Authorization"],  # 필요한 헤더만
 )
    logger.info("? 프로덕션 모드: 엄격한 CORS 설정 적용")
else:
 # 개발 환경: 더 관대한 설정 (개발 편의성)
 app.add_middleware(
 CORSMiddleware,
 allow_origins = _allowed_origins,
 allow_credentials = True,
        allow_methods=["*"],
        allow_headers=["*"],
 )
    logger.info("? 개발 모드: 관대한 CORS 설정 적용")

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
 get_base_dir,
 load_json as _load_json,
 find_latest_instance_status as _find_latest_instance_status,
 load_training_stats as _load_training_stats,
)

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
        response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout = 5)
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
    result["win_rate"] = win_rate
    result["winRate"] = win_rate
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
        raise HTTPException(status_code = 400, detail = f"Unknown command type: {cmd_type}")

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

# Simple UI route to serve dashboard.html via FastAPI
@app.get("/ui", response_class = HTMLResponse)
async def serve_dashboard_ui():
    html_path = Path(__file__).parent / "dashboard.html"
 if html_path.exists():
        with html_path.open("r", encoding="utf-8") as f:
 content = f.read()
        return HTMLResponse(content = content, media_type="text/html; charset = utf-8")
    raise HTTPException(status_code = 404, detail="dashboard.html not found")

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