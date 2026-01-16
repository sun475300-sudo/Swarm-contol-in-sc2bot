#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC2 AI Arena Dashboard Client

Arena�� ������ ���� �����͸� ���÷� �����ϴ� Ŭ���̾�Ʈ
Arena API���� �����͸� ������ ��ú���� ����
"""

import requests
import time
import logging
from typing import Dict, Any, Optional, List
import os
from pathlib import Path

# �α� ����
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArenaDashboardClient:
    """Arena ��ú��� Ŭ���̾�Ʈ"""

    def __init__(
        self,
        arena_api_url: str = "https://aiarena.net/api/v2",
        bot_name: str = "WickedZerg",
        dashboard_url: str = "http://localhost:8002",
        enabled: bool = True
    ):
        """
        Arena ��ú��� Ŭ���̾�Ʈ �ʱ�ȭ

        Args:
            arena_api_url: Arena API �⺻ URL
            bot_name: �� �̸�
            dashboard_url: ��ú��� API URL
            enabled: Ȱ��ȭ ����
        """
        self.arena_api_url = arena_api_url.rstrip('/')
        self.bot_name = bot_name
        self.dashboard_url = dashboard_url.rstrip('/')
        self.enabled = enabled and os.environ.get("ARENA_DASHBOARD_ENABLED", "1") == "1"

        # Arena API ����
        self.arena_session = requests.Session()
        self.arena_session.headers.update({
            "Content-Type": "application/json"
        })

        # ��ú��� API ����
        self.dashboard_session = requests.Session()
        self.dashboard_session.headers.update({
            "Content-Type": "application/json"
        })

        logger.info(f"[ARENA] Ŭ���̾�Ʈ �ʱ�ȭ: {self.bot_name}")

    def fetch_arena_data(self) -> Optional[Dict[str, Any]]:
        """
        Arena API���� �� ������ ��������

        Returns:
            �� ������ �Ǵ� None
        """
        if not self.enabled:
            return None

        try:
            url = f"{self.arena_api_url}/bots/{self.bot_name}/"
            response = self.arena_session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[ARENA] ������ �������� ����: {e}")
            return None

    def fetch_arena_matches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Arena API���� ��� ��� ��������

        Args:
            limit: �ִ� ��� ��

        Returns:
            ��� ��� ����Ʈ
        """
        if not self.enabled:
            return []

        try:
            url = f"{self.arena_api_url}/matches/?bot1_name={self.bot_name}&limit={limit}"
            response = self.arena_session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"[ARENA] ��� ��� �������� ����: {e}")
            return []

    def sync_to_dashboard(self) -> bool:
        """
        Arena �����͸� ��ú���� ����ȭ

        Returns:
            ����ȭ ���� ����
        """
        if not self.enabled:
            return False

        try:
            # ��ú��� ������ ���ΰ�ħ ��û
            url = f"{self.dashboard_url}/api/arena/refresh"
            response = self.dashboard_session.post(url, timeout=10)
            response.raise_for_status()
            logger.info("[ARENA] ��ú��� ����ȭ ����")
            return True
        except Exception as e:
            logger.error(f"[ARENA] ��ú��� ����ȭ ����: {e}")
            return False


def create_client_from_env() -> Optional[ArenaDashboardClient]:
    """
    ȯ�� �������� Ŭ���̾�Ʈ ����

    ȯ�� ����:
        ARENA_API_URL: Arena API URL (�⺻��: https://aiarena.net/api/v2)
        ARENA_BOT_NAME: �� �̸� (�⺻��: WickedZerg)
        ARENA_DASHBOARD_URL: ��ú��� URL (�⺻��: http://localhost:8002)
        ARENA_DASHBOARD_ENABLED: Ȱ��ȭ ���� (1 �Ǵ� 0)

    Returns:
        ArenaDashboardClient �ν��Ͻ� �Ǵ� None
    """
    arena_api_url = os.environ.get("ARENA_API_URL", "https://aiarena.net/api/v2")
    bot_name = os.environ.get("ARENA_BOT_NAME", "WickedZerg")
    dashboard_url = os.environ.get("ARENA_DASHBOARD_URL", "http://localhost:8002")
    enabled = os.environ.get("ARENA_DASHBOARD_ENABLED", "1") == "1"

    return ArenaDashboardClient(
        arena_api_url=arena_api_url,
        bot_name=bot_name,
        dashboard_url=dashboard_url,
        enabled=enabled
    )


# �׽�Ʈ �ڵ�
if __name__ == "__main__":
    client = create_client_from_env()

    if not client:
        print("ȯ�� ������ �����ϼ���:")
        print("  ARENA_API_URL = https://aiarena.net/api/v2")
        print("  ARENA_BOT_NAME = WickedZerg")
        print("  ARENA_DASHBOARD_URL = http://localhost:8002")
        print("  ARENA_DASHBOARD_ENABLED = 1")
        exit(1)

    # Arena ������ ��������
    print("Arena �� ���� ��������...")
    bot_info = client.fetch_arena_data()
    if bot_info:
        print(f"? �� ����: {bot_info.get('name', 'Unknown')}")
        print(f"   ELO: {bot_info.get('elo', 'N/A')}")
    else:
        print("? �� ������ ������ �� �����ϴ�")

    # ��� ��� ��������
    print("\n�ֱ� ��� ��� ��������...")
    matches = client.fetch_arena_matches(limit=10)
    print(f"? �ֱ� {len(matches)}��� �߰�")

    # ��ú��� ����ȭ
    print("\n��ú��� ����ȭ...")
    if client.sync_to_dashboard():
        print("? ��ú��� ����ȭ ����")
    else:
        print("? ��ú��� ����ȭ ����")
