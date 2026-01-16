#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC2 AI Arena Dashboard API

SC2 AI Arena에 배포된 봇을 위한 전용 대시보드 API
랭킹, ELO, 경기 결과 등을 모니터링
"""

import asyncio
import json
import requests
from datetime import datetime, timedelta
import logging
from pathlib import Path
import os
from typing import List, Dict, Any, Optional
import time

# FastAPI imports
try:
    from fastapi import FastAPI, HTTPException, Depends, WebSocket, status
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import HTTPBasic, HTTPBasicCredentials
    from starlette.responses import JSONResponse as StarletteJSONResponse
except ImportError:
    raise ImportError("fastapi is required. Install with: pip install fastapi uvicorn")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SC2 AI Arena Dashboard API",
    description="SC2 AI Arena 배포 봇 전용 대시보드 API",
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Arena 대시보드는 공개적으로 접근 가능하도록 설정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Arena API Integration
# ============================================================================

# Arena API 설정 (환경 변수 또는 기본값)
ARENA_API_BASE_URL = os.environ.get("ARENA_API_URL", "https://aiarena.net/api/v2")
ARENA_BOT_NAME = os.environ.get("ARENA_BOT_NAME", "WickedZerg")
ARENA_BOT_ID = os.environ.get("ARENA_BOT_ID", None)

# Arena 데이터 캐시
arena_data_cache = {
    "bot_info": None,
    "matches": [],
    "stats": {},
    "ranking": None,
    "elo_history": [],
    "last_update": None
}

# ============================================================================
# Helper Functions
# ============================================================================

def fetch_arena_bot_info() -> Optional[Dict[str, Any]]:
    """
    Arena API에서 봇 정보 가져오기
    
    Returns:
        봇 정보 또는 None
    """
    try:
        url = f"{ARENA_API_BASE_URL}/bots/{ARENA_BOT_NAME}/"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Arena API 호출 실패: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Arena 봇 정보 가져오기 실패: {e}")
        return None

def fetch_arena_matches(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Arena API에서 경기 기록 가져오기
    
    Args:
        limit: 최대 경기 수
        
    Returns:
        경기 기록 리스트
    """
    try:
        if ARENA_BOT_ID:
            url = f"{ARENA_API_BASE_URL}/matches/?bot1={ARENA_BOT_ID}&limit={limit}"
        else:
            url = f"{ARENA_API_BASE_URL}/matches/?bot1_name={ARENA_BOT_NAME}&limit={limit}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
        else:
            logger.warning(f"Arena 경기 기록 가져오기 실패: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Arena 경기 기록 가져오기 실패: {e}")
        return []

def fetch_arena_ranking() -> Optional[Dict[str, Any]]:
    """
    Arena 랭킹 정보 가져오기
    
    Returns:
        랭킹 정보 또는 None
    """
    try:
        url = f"{ARENA_API_BASE_URL}/ladders/"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            # 봇의 랭킹 찾기
            for ladder in results:
                if ARENA_BOT_NAME.lower() in ladder.get("bot_name", "").lower():
                    return ladder
            
            return None
        else:
            logger.warning(f"Arena 랭킹 정보 가져오기 실패: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Arena 랭킹 정보 가져오기 실패: {e}")
        return None

def calculate_arena_stats(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    경기 기록에서 통계 계산
    
    Args:
        matches: 경기 기록 리스트
        
    Returns:
        통계 딕셔너리
    """
    if not matches:
        return {
            "total_matches": 0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "win_rate": 0.0,
            "current_elo": 0,
            "peak_elo": 0,
            "elo_change": 0
        }
    
    wins = 0
    losses = 0
    ties = 0
    elo_values = []
    
    for match in matches:
        result = match.get("result", "").lower()
        if "win" in result or result == "1":
            wins += 1
        elif "loss" in result or result == "0":
            losses += 1
        else:
            ties += 1
        
        elo = match.get("bot1_elo_after", match.get("elo_after", None))
        if elo:
            elo_values.append(elo)
    
    total_matches = wins + losses + ties
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0.0
    
    current_elo = elo_values[0] if elo_values else 0
    peak_elo = max(elo_values) if elo_values else 0
    elo_change = elo_values[0] - elo_values[-1] if len(elo_values) > 1 else 0
    
    return {
        "total_matches": total_matches,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": round(win_rate, 2),
        "current_elo": current_elo,
        "peak_elo": peak_elo,
        "elo_change": elo_change
    }

async def update_arena_cache():
    """Arena 데이터 캐시 업데이트"""
    try:
        logger.info("Arena 데이터 캐시 업데이트 중...")
        
        # 봇 정보 가져오기
        bot_info = fetch_arena_bot_info()
        if bot_info:
            arena_data_cache["bot_info"] = bot_info
            if not ARENA_BOT_ID and bot_info.get("id"):
                global ARENA_BOT_ID
                ARENA_BOT_ID = bot_info.get("id")
        
        # 경기 기록 가져오기
        matches = fetch_arena_matches(limit=100)
        arena_data_cache["matches"] = matches
        
        # 통계 계산
        arena_data_cache["stats"] = calculate_arena_stats(matches)
        
        # 랭킹 정보 가져오기
        ranking = fetch_arena_ranking()
        arena_data_cache["ranking"] = ranking
        
        # ELO 히스토리 생성 (최근 50경기)
        recent_matches = matches[:50] if len(matches) > 50 else matches
        elo_history = []
        for match in reversed(recent_matches):  # 오래된 순서대로
            elo_after = match.get("bot1_elo_after", match.get("elo_after", None))
            if elo_after:
                elo_history.append({
                    "elo": elo_after,
                    "date": match.get("created", match.get("date", datetime.now().isoformat())),
                    "result": match.get("result", "Unknown"),
                    "opponent": match.get("bot2_name", "Unknown")
                })
        arena_data_cache["elo_history"] = elo_history
        
        arena_data_cache["last_update"] = datetime.now().isoformat()
        logger.info("Arena 데이터 캐시 업데이트 완료")
        
    except Exception as e:
        logger.error(f"Arena 캐시 업데이트 실패: {e}")

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "SC2 AI Arena Dashboard API",
        "version": "1.0.0",
        "bot_name": ARENA_BOT_NAME,
        "bot_id": ARENA_BOT_ID,
        "arena_api_url": ARENA_API_BASE_URL,
        "endpoints": {
            "bot_info": "/api/arena/bot-info",
            "stats": "/api/arena/stats",
            "matches": "/api/arena/matches",
            "ranking": "/api/arena/ranking",
            "elo_history": "/api/arena/elo-history",
            "refresh": "/api/arena/refresh"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_updated": arena_data_cache.get("last_update")
    }

@app.get("/api/arena/bot-info")
async def get_arena_bot_info():
    """Arena 봇 정보 조회"""
    bot_info = arena_data_cache.get("bot_info")
    
    if not bot_info:
        # 캐시가 없으면 직접 가져오기
        bot_info = fetch_arena_bot_info()
        if bot_info:
            arena_data_cache["bot_info"] = bot_info
    
    if not bot_info:
        return {
            "success": False,
            "message": "봇 정보를 가져올 수 없습니다. Arena API URL과 봇 이름을 확인하세요.",
            "config": {
                "arena_api_url": ARENA_API_BASE_URL,
                "bot_name": ARENA_BOT_NAME,
                "bot_id": ARENA_BOT_ID
            }
        }
    
    return {
        "success": True,
        "data": bot_info,
        "cached": arena_data_cache.get("bot_info") is not None
    }

@app.get("/api/arena/stats")
async def get_arena_stats():
    """Arena 통계 조회"""
    stats = arena_data_cache.get("stats")
    
    if not stats or not arena_data_cache.get("last_update"):
        # 캐시가 없으면 업데이트
        matches = fetch_arena_matches(limit=100)
        stats = calculate_arena_stats(matches)
        arena_data_cache["stats"] = stats
    
    return {
        "success": True,
        "data": stats,
        "last_update": arena_data_cache.get("last_update")
    }

@app.get("/api/arena/matches")
async def get_arena_matches(limit: int = 50, offset: int = 0):
    """Arena 경기 기록 조회"""
    matches = arena_data_cache.get("matches", [])
    
    # 페이지네이션
    total = len(matches)
    paginated_matches = matches[offset:offset + limit]
    
    return {
        "success": True,
        "data": paginated_matches,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        },
        "last_update": arena_data_cache.get("last_update")
    }

@app.get("/api/arena/ranking")
async def get_arena_ranking():
    """Arena 랭킹 정보 조회"""
    ranking = arena_data_cache.get("ranking")
    
    if not ranking:
        # 캐시가 없으면 직접 가져오기
        ranking = fetch_arena_ranking()
        if ranking:
            arena_data_cache["ranking"] = ranking
    
    if not ranking:
        return {
            "success": False,
            "message": "랭킹 정보를 가져올 수 없습니다.",
            "data": None
        }
    
    return {
        "success": True,
        "data": ranking
    }

@app.get("/api/arena/elo-history")
async def get_arena_elo_history(limit: int = 50):
    """ELO 레이팅 히스토리 조회"""
    elo_history = arena_data_cache.get("elo_history", [])
    
    if not elo_history:
        # 캐시가 없으면 생성
        matches = fetch_arena_matches(limit=limit)
        elo_history = []
        for match in reversed(matches):
            elo_after = match.get("bot1_elo_after", match.get("elo_after", None))
            if elo_after:
                elo_history.append({
                    "elo": elo_after,
                    "date": match.get("created", match.get("date", datetime.now().isoformat())),
                    "result": match.get("result", "Unknown"),
                    "opponent": match.get("bot2_name", "Unknown")
                })
        arena_data_cache["elo_history"] = elo_history
    
    return {
        "success": True,
        "data": elo_history[:limit],
        "last_update": arena_data_cache.get("last_update")
    }

@app.post("/api/arena/refresh")
async def refresh_arena_data():
    """Arena 데이터 캐시 강제 새로고침"""
    await update_arena_cache()
    return {
        "success": True,
        "message": "Arena 데이터가 새로고침되었습니다.",
        "last_update": arena_data_cache.get("last_update")
    }

@app.get("/api/arena/opponents")
async def get_arena_opponents():
    """상대 봇별 성적 조회"""
    matches = arena_data_cache.get("matches", [])
    
    opponent_stats = {}
    
    for match in matches:
        opponent = match.get("bot2_name", "Unknown")
        result = match.get("result", "").lower()
        
        if opponent not in opponent_stats:
            opponent_stats[opponent] = {
                "opponent_name": opponent,
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "total": 0,
                "win_rate": 0.0
            }
        
        if "win" in result or result == "1":
            opponent_stats[opponent]["wins"] += 1
        elif "loss" in result or result == "0":
            opponent_stats[opponent]["losses"] += 1
        else:
            opponent_stats[opponent]["ties"] += 1
        
        opponent_stats[opponent]["total"] += 1
    
    # 승률 계산
    for opponent, stats in opponent_stats.items():
        if stats["total"] > 0:
            stats["win_rate"] = round((stats["wins"] / stats["total"]) * 100, 2)
    
    # 승률 순으로 정렬
    sorted_opponents = sorted(
        opponent_stats.values(),
        key=lambda x: x["win_rate"],
        reverse=True
    )
    
    return {
        "success": True,
        "data": sorted_opponents,
        "total_opponents": len(sorted_opponents)
    }

@app.get("/api/arena/recent-performance")
async def get_recent_performance(days: int = 7):
    """최근 성적 조회 (기간별)"""
    matches = arena_data_cache.get("matches", [])
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    recent_matches = []
    for match in matches:
        match_date_str = match.get("created", match.get("date", ""))
        if match_date_str:
            try:
                match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                if match_date.replace(tzinfo=None) >= cutoff_date:
                    recent_matches.append(match)
            except Exception:
                continue
    
    stats = calculate_arena_stats(recent_matches)
    
    return {
        "success": True,
        "data": {
            "period_days": days,
            "stats": stats,
            "matches_count": len(recent_matches)
        },
        "last_update": arena_data_cache.get("last_update")
    }

# ============================================================================
# WebSocket for real-time updates
# ============================================================================

connected_arena_clients: List[WebSocket] = []

@app.websocket("/ws/arena-updates")
async def websocket_arena_updates(websocket: WebSocket):
    """실시간 Arena 업데이트 WebSocket"""
    await websocket.accept()
    connected_arena_clients.append(websocket)
    
    try:
        while True:
            # 캐시된 데이터 전송
            data = {
                "type": "arena_update",
                "stats": arena_data_cache.get("stats", {}),
                "ranking": arena_data_cache.get("ranking"),
                "last_update": arena_data_cache.get("last_update"),
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(data)
            await asyncio.sleep(30)  # 30초마다 업데이트
    except Exception as e:
        logger.error(f"WebSocket 에러: {e}")
    finally:
        connected_arena_clients.remove(websocket)

# ============================================================================
# Background Tasks
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info("SC2 AI Arena Dashboard API 시작")
    logger.info(f"봇 이름: {ARENA_BOT_NAME}")
    logger.info(f"Arena API URL: {ARENA_API_BASE_URL}")
    
    # 초기 캐시 업데이트
    await update_arena_cache()
    
    # 주기적으로 캐시 업데이트 (5분마다)
    async def periodic_update():
        while True:
            await asyncio.sleep(300)  # 5분
            await update_arena_cache()
    
    # 백그라운드 태스크 시작
    asyncio.create_task(periodic_update())

# ============================================================================
# Server startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,  # Arena 대시보드는 다른 포트 사용
        log_level="info"
    )
