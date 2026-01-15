#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manus Dashboard Client

SC2 AI 봇의 데이터를 Manus 웹 호스팅 대시보드(tRPC API)로 전송하는 클라이언트
"""

try:
    import requests
except ImportError:
    raise ImportError(
        "The 'requests' package is required. Install it with: pip install requests>=2.31.0"
    )

import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManusDashboardClient:
    """Manus 대시보드 tRPC API 클라이언트"""
    
    def __init__(
        self,
        base_url: str = "https://sc2aidash-bncleqgg.manus.space",
        api_key: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Manus 대시보드 클라이언트 초기화
        
        Args:
            base_url: Manus 대시보드 URL
            api_key: API 인증 키 (선택적, 우선순위: 인자 > 환경 변수 > 파일)
            enabled: 원격 전송 활성화 여부
        """
        self.base_url = base_url.rstrip('/')
        # API 키 로드 우선순위: 1) 인자, 2) 환경 변수, 3) 파일
        self.api_key = api_key or self._load_api_key()
        self.enabled = enabled and os.environ.get("MANUS_DASHBOARD_ENABLED", "1") == "1"
        
        # tRPC API 엔드포인트
        self.trpc_url = f"{self.base_url}/api/trpc"
        
        # HTTP 세션
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
        
        # 재시도 설정
        self.max_retries = 3
        self.retry_delay = 2
        
        logger.info(f"[MANUS] 클라이언트 초기화: {self.base_url} (활성화: {self.enabled})")
    
    def _load_api_key(self) -> Optional[str]:
        """
        API 키 로드 (환경 변수 우선, 파일 fallback)
        
        Returns:
            API 키 또는 None
        """
        # 1. 환경 변수 우선
        key = os.environ.get("MANUS_DASHBOARD_API_KEY")
        if key:
            return key
        
        # 2. 파일에서 읽기 (fallback)
        try:
            from pathlib import Path
            # 여러 가능한 경로 시도
            possible_paths = [
                Path("monitoring/api_keys/manus_api_key.txt"),
                Path("api_keys/manus_api_key.txt"),
                Path("secrets/manus_api_key.txt"),
            ]
            
            for key_file in possible_paths:
                if key_file.exists():
                    key = key_file.read_text(encoding="utf-8").strip()
                    if key:
                        logger.info(f"[MANUS] API 키를 파일에서 로드: {key_file}")
                        return key
        except Exception as e:
            logger.warning(f"[MANUS] API 키 파일 읽기 실패: {e}")
        
        return None
    
    def _call_trpc(
        self,
        procedure: str,
        input_data: Dict[str, Any],
        retry: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        tRPC 프로시저 호출
        
        Args:
            procedure: tRPC 프로시저 이름 (예: "game.createSession")
            input_data: 입력 데이터
            retry: 재시도 여부
            
        Returns:
            응답 데이터 또는 None
        """
        if not self.enabled:
            return None
        
        # tRPC URL 형식: /api/trpc/{procedure}
        url = f"{self.trpc_url}/{procedure}"
        
        for attempt in range(self.max_retries if retry else 1):
            try:
                response = self.session.post(
                    url,
                    json=input_data,
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"[MANUS] 요청 실패 (시도 {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"[MANUS] 요청 최종 실패: {e}")
                    return None
        
        return None
    
    def create_game_session(
        self,
        map_name: str,
        enemy_race: str,
        final_minerals: int,
        final_gas: int,
        final_supply: int,
        units_killed: int,
        units_lost: int,
        duration: int,
        result: str,  # "Victory" or "Defeat"
        personality: Optional[str] = None,
        loss_reason: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        게임 세션 생성 (게임 종료 시 호출)
        
        Args:
            map_name: 맵 이름
            enemy_race: 상대 종족
            final_minerals: 최종 미네랄
            final_gas: 최종 가스
            final_supply: 최종 인구수
            units_killed: 처치한 유닛 수
            units_lost: 잃은 유닛 수
            duration: 게임 시간 (초)
            result: 게임 결과 ("Victory" or "Defeat")
            personality: 봇 성격 (선택적)
            loss_reason: 패배 이유 (선택적)
            **kwargs: 추가 필드
            
        Returns:
            전송 성공 여부
        """
        payload = {
            "mapName": map_name,
            "enemyRace": enemy_race,
            "finalMinerals": final_minerals,
            "finalGas": final_gas,
            "finalSupply": final_supply,
            "unitsKilled": units_killed,
            "unitsLost": units_lost,
            "duration": duration,
            "result": result,
        }
        
        # 선택적 필드 추가
        if personality:
            payload["personality"] = personality
        if loss_reason:
            payload["lossReason"] = loss_reason
        
        # 추가 필드 병합
        payload.update(kwargs)
        
        response = self._call_trpc("game.createSession", payload)
        
        if response:
            logger.info(f"[MANUS] 게임 세션 생성 성공: {result} vs {enemy_race}")
            return True
        else:
            logger.warning("[MANUS] 게임 세션 생성 실패")
            return False
    
    def create_training_episode(
        self,
        episode: int,
        reward: float,
        loss: float,
        win_rate: float,
        games: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        학습 에피소드 생성
        
        Args:
            episode: 에피소드 번호
            reward: 보상
            loss: 손실
            win_rate: 승률 (0.0 ~ 1.0)
            games: 게임 수 (선택적)
            **kwargs: 추가 필드
            
        Returns:
            전송 성공 여부
        """
        payload = {
            "episode": episode,
            "reward": reward,
            "loss": loss,
            "winRate": win_rate,
            **kwargs
        }
        
        if games is not None:
            payload["games"] = games
        
        response = self._call_trpc("training.createEpisode", payload)
        
        if response:
            logger.debug(f"[MANUS] 학습 에피소드 생성 성공: Episode {episode}")
            return True
        else:
            logger.warning("[MANUS] 학습 에피소드 생성 실패")
            return False
    
    def update_bot_config(
        self,
        config_name: str,
        strategy: str,
        build_order: Optional[List[str]] = None,
        description: Optional[str] = None,
        traits: Optional[List[str]] = None,
        is_active: bool = False,
        **kwargs
    ) -> bool:
        """
        봇 설정 업데이트
        
        Args:
            config_name: 설정 이름
            strategy: 전략
            build_order: 빌드 오더 (선택적)
            description: 빌드오더 설명 (선택적)
            traits: 특성 리스트 (선택적)
            is_active: 활성화 여부
            **kwargs: 추가 필드
            
        Returns:
            전송 성공 여부
        """
        payload = {
            "name": config_name,
            "strategy": strategy,
            "isActive": is_active,
            **kwargs
        }
        
        if build_order:
            payload["buildOrder"] = build_order
        if description:
            payload["description"] = description
        if traits:
            payload["traits"] = traits
        
        response = self._call_trpc("botConfig.update", payload)
        
        if response:
            logger.debug(f"[MANUS] 봇 설정 업데이트 성공: {config_name}")
            return True
        else:
            logger.warning("[MANUS] 봇 설정 업데이트 실패")
            return False
    
    def create_arena_match(
        self,
        opponent: str,
        result: str,
        elo_change: int,
        elo_after: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        AI Arena 경기 생성
        
        Args:
            opponent: 상대 봇 이름
            result: 경기 결과 ("Victory" or "Defeat")
            elo_change: ELO 변화
            elo_after: 경기 후 ELO (선택적)
            **kwargs: 추가 필드
            
        Returns:
            전송 성공 여부
        """
        payload = {
            "opponent": opponent,
            "result": result,
            "eloChange": elo_change,
            **kwargs
        }
        
        if elo_after is not None:
            payload["eloAfter"] = elo_after
        
        response = self._call_trpc("arena.createMatch", payload)
        
        if response:
            logger.info(f"[MANUS] Arena 경기 생성 성공: {result} vs {opponent}")
            return True
        else:
            logger.warning("[MANUS] Arena 경기 생성 실패")
            return False
    
    def update_game_state(
        self,
        minerals: int,
        vespene: int,
        supply_used: int,
        supply_cap: int,
        units: Dict[str, int],
        map_name: Optional[str] = None,
        game_time: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        실시간 게임 상태 업데이트
        
        Args:
            minerals: 미네랄
            vespene: 가스
            supply_used: 사용 인구수
            supply_cap: 최대 인구수
            units: 유닛 딕셔너리
            map_name: 맵 이름 (선택적)
            game_time: 게임 시간 (선택적)
            **kwargs: 추가 필드
            
        Returns:
            전송 성공 여부
        """
        payload = {
            "minerals": minerals,
            "vespene": vespene,
            "supplyUsed": supply_used,
            "supplyCap": supply_cap,
            "units": units,
            **kwargs
        }
        
        if map_name:
            payload["mapName"] = map_name
        if game_time is not None:
            payload["gameTime"] = game_time
        
        response = self._call_trpc("game.updateState", payload)
        
        if response:
            logger.debug("[MANUS] 게임 상태 업데이트 성공")
            return True
        else:
            logger.warning("[MANUS] 게임 상태 업데이트 실패")
            return False
    
    def health_check(self) -> bool:
        """
        대시보드 연결 상태 확인
        
        Returns:
            서버 응답 여부
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"[MANUS] 헬스 체크 실패: {e}")
            return False


def create_client_from_env() -> Optional[ManusDashboardClient]:
    """
    환경 변수에서 클라이언트 생성
    
    환경 변수:
        MANUS_DASHBOARD_URL: Manus 대시보드 URL
        MANUS_DASHBOARD_API_KEY: API 키 (선택적)
        MANUS_DASHBOARD_ENABLED: 활성화 여부 (1 또는 0)
    
    Returns:
        ManusDashboardClient 인스턴스 또는 None
    """
    base_url = os.environ.get("MANUS_DASHBOARD_URL", "https://sc2aidash-bncleqgg.manus.space")
    api_key = os.environ.get("MANUS_DASHBOARD_API_KEY")
    enabled = os.environ.get("MANUS_DASHBOARD_ENABLED", "1") == "1"
    
    return ManusDashboardClient(
        base_url=base_url,
        api_key=api_key,
        enabled=enabled
    )


# 테스트 코드
if __name__ == "__main__":
    client = create_client_from_env()
    
    if not client:
        print("환경 변수를 설정하세요:")
        print("  MANUS_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space")
        print("  MANUS_DASHBOARD_API_KEY=your_api_key (선택적)")
        print("  MANUS_DASHBOARD_ENABLED=1")
        exit(1)
    
    # 헬스 체크
    print("Manus 대시보드 연결 확인 중...")
    if client.health_check():
        print("? 서버 연결 성공")
    else:
        print("? 서버 연결 실패")
    
    # 테스트 게임 세션 생성
    print("\n테스트 게임 세션 생성 중...")
    if client.create_game_session(
        map_name="AbyssalReefLE",
        enemy_race="Terran",
        final_minerals=200,
        final_gas=100,
        final_supply=150,
        units_killed=50,
        units_lost=30,
        duration=600,
        result="Victory",
        personality="serral"
    ):
        print("? 게임 세션 생성 성공")
    else:
        print("? 게임 세션 생성 실패")
