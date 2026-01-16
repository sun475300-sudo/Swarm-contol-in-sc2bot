#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified API Gateway

Proxy for local training and arena battle monitoring
Enables mobile app and web to access both servers
"""

import requests
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse as StarletteJSONResponse
import json
from typing import Optional, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

# Server ports
LOCAL_SERVER_PORT = 8001
ARENA_SERVER_PORT = 8002

app = FastAPI(
    title="SC2 AI Unified Monitoring Gateway",
    description="Unified API Gateway for Local Training and Arena Battle Monitoring",
    version="1.0.0"
)

# Configure default JSON encoder for UTF-8
class UTF8JSONResponse(StarletteJSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":")
        ).encode("utf-8")

app.default_response_class = UTF8JSONResponse

# CORS middleware - Allow all origins for mobile/web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_server_health(port: int) -> bool:
    """Check server health"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def proxy_request(server_type: str, endpoint: str, method: str = "GET", params: Optional[Dict] = None) -> Dict:
    """Proxy request to appropriate server"""
    port = LOCAL_SERVER_PORT if server_type == "local" else ARENA_SERVER_PORT

    if not check_server_health(port):
        raise HTTPException(status_code=503, detail=f"{server_type.upper()} server is not available on port {port}")

    url = f"http://localhost:{port}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=params, timeout=10)
        else:
            raise HTTPException(status_code=405, detail=f"Method {method} not supported")

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Failed to connect to {server_type} server: {e}")


@app.get("/")
async def root():
    """Gateway root"""
    local_available = check_server_health(LOCAL_SERVER_PORT)
    arena_available = check_server_health(ARENA_SERVER_PORT)

    return {
        "message": "SC2 AI Unified Monitoring Gateway",
        "version": "1.0.0",
        "servers": {
            "local": {
                "available": local_available,
                "port": LOCAL_SERVER_PORT,
                "url": f"http://localhost:{LOCAL_SERVER_PORT}" if local_available else None,
                "description": "Local training monitoring server"
            },
            "arena": {
                "available": arena_available,
                "port": ARENA_SERVER_PORT,
                "url": f"http://localhost:{ARENA_SERVER_PORT}" if arena_available else None,
                "description": "Arena battle monitoring server"
            }
        },
        "endpoints": {
            "local_api": "/api/local/*",
            "arena_api": "/api/arena/*",
            "unified_api": "/api/unified/*"
        },
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check"""
    local_health = check_server_health(LOCAL_SERVER_PORT)
    arena_health = check_server_health(ARENA_SERVER_PORT)

    return {
        "status": "healthy" if (local_health or arena_health) else "degraded",
        "gateway": "running",
        "servers": {
            "local": "available" if local_health else "unavailable",
            "arena": "available" if arena_health else "unavailable"
        }
    }


# Local Server Proxy Endpoints
@app.get("/api/local/{endpoint:path}")
async def proxy_local(endpoint: str, **params):
    """Proxy to local server"""
    return proxy_request("local", f"/api/{endpoint}", "GET", params)


@app.post("/api/local/{endpoint:path}")
async def proxy_local_post(endpoint: str, data: Optional[Dict] = None):
    """Proxy to local server (POST)"""
    return proxy_request("local", f"/api/{endpoint}", "POST", data)


# Arena Server Proxy Endpoints
@app.get("/api/arena/{endpoint:path}")
async def proxy_arena(endpoint: str, **params):
    """Proxy to arena server"""
    return proxy_request("arena", f"/api/{endpoint}", "GET", params)


@app.post("/api/arena/{endpoint:path}")
async def proxy_arena_post(endpoint: str, data: Optional[Dict] = None):
    """Proxy to arena server (POST)"""
    return proxy_request("arena", f"/api/{endpoint}", "POST", data)


# Unified Endpoints - automatically select active server
@app.get("/api/unified/game-state")
async def unified_game_state():
    """Unified game state - get from active server"""
    # Prefer local server, fallback to arena server
    if check_server_health(LOCAL_SERVER_PORT):
        return proxy_request("local", "/api/game-state")
    elif check_server_health(ARENA_SERVER_PORT):
        return proxy_request("arena", "/api/game-state")
    else:
        raise HTTPException(status_code=503, detail="No monitoring servers available")


@app.get("/api/unified/stats")
async def unified_stats():
    """Unified stats - get from both servers"""
    result = {
        "local": None,
        "arena": None
    }

    if check_server_health(LOCAL_SERVER_PORT):
        try:
            result["local"] = proxy_request("local", "/api/combat-stats")
        except Exception as e:
            logger.warning(f"Failed to get local stats: {e}")

    if check_server_health(ARENA_SERVER_PORT):
        try:
            result["arena"] = proxy_request("arena", "/api/stats")
        except Exception as e:
            logger.warning(f"Failed to get arena stats: {e}")

    return result


@app.get("/api/unified/status")
async def unified_status():
    """Unified status information"""
    return {
        "local_server": {
            "available": check_server_health(LOCAL_SERVER_PORT),
            "port": LOCAL_SERVER_PORT,
            "url": f"http://localhost:{LOCAL_SERVER_PORT}"
        },
        "arena_server": {
            "available": check_server_health(ARENA_SERVER_PORT),
            "port": ARENA_SERVER_PORT,
            "url": f"http://localhost:{ARENA_SERVER_PORT}"
        },
        "gateway_port": 8000
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,  # Gateway uses port 8000
        log_level="info"
    )
