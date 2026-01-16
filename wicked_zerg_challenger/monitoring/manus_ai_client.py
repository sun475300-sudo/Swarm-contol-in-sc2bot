#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manus AI API Client

Manus AI (api.manus.ai) API Ŭ���̾�Ʈ
Projects, Tasks, Files, Webhooks ����
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


class ManusAIClient:
    """Manus AI API Ŭ���̾�Ʈ"""

    def __init__(
        self,
        base_url: str = "https://api.manus.ai",
        api_key: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Manus AI Ŭ���̾�Ʈ �ʱ�ȭ

        Args:
            base_url: Manus AI API �⺻ URL
            api_key: API ���� Ű (������, �켱����: ���� > ȯ�� ���� > ����)
            enabled: ���� ���� Ȱ��ȭ ����
        """
        self.base_url = base_url.rstrip('/')
        # API Ű �ε� �켱����: 1) ����, 2) ȯ�� ����, 3) ����
        self.api_key = api_key or self._load_api_key()
        self.enabled = enabled and os.environ.get("MANUS_AI_ENABLED", "1") == "1"

        # HTTP ����
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })

        if self.api_key:
            self.session.headers.update({
                "API_KEY": self.api_key
            })

        # ��õ� ����
        self.max_retries = 3
        self.retry_delay = 2

        logger.info(f"[MANUS AI] Ŭ���̾�Ʈ �ʱ�ȭ: {self.base_url} (Ȱ��ȭ: {self.enabled})")

    def _load_api_key(self) -> Optional[str]:
        """
        API Ű �ε� (ȯ�� ���� �켱, ���� fallback)

        Returns:
            API Ű �Ǵ� None
        """
        # 1. ȯ�� ���� �켱
        key = os.environ.get("MANUS_AI_API_KEY")
        if key:
            return key

        # 2. ���Ͽ��� �б� (fallback)
        try:
            # ���� ������ ��� �õ�
            possible_paths = [
                Path("monitoring/api_keys/manus_ai_api_key.txt"),
                Path("api_keys/manus_ai_api_key.txt"),
                Path("secrets/manus_ai_api_key.txt"),
            ]

            for key_file in possible_paths:
                if key_file.exists():
                    # Try multiple encodings to handle different file encodings
                    for encoding in ["utf-8", "cp949", "latin-1", "utf-8-sig"]:
                        try:
                            key = key_file.read_text(encoding=encoding).strip()
                            if key:
                                logger.info(f"[MANUS AI] API Ű�� ���Ͽ��� �ε�: {key_file}")
                                return key
                            break
                        except UnicodeDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"[MANUS AI] API Ű ���� �б� ����: {e}")

        return None

    def _call_api(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        retry: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Manus AI API ȣ��

        Args:
            method: HTTP �޼��� (GET, POST, PUT, DELETE)
            endpoint: API ��������Ʈ (��: "/v1/tasks")
            data: ��û ������ (POST/PUT��)
            retry: ��õ� ����

        Returns:
            ���� ������ �Ǵ� None
        """
        if not self.enabled:
            return None

        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries if retry else 1):
            try:
                # CRITICAL FIX: Ensure all data is UTF-8 encoded before JSON serialization
                encoded_data = {}
                if data:
                    for key, value in data.items():
                        if isinstance(value, str):
                            # Ensure string is UTF-8 encoded
                            try:
                                encoded_data[key] = value.encode('utf-8').decode('utf-8')
                            except (UnicodeEncodeError, UnicodeDecodeError):
                                # If encoding fails, try to fix it
                                encoded_data[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                        else:
                            encoded_data[key] = value

                response = self.session.request(
                    method,
                    url,
                    json=encoded_data if data else None,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()

            except (UnicodeEncodeError, UnicodeDecodeError) as e:
                # Handle encoding errors gracefully
                logger.warning(f"[MANUS AI] ���ڵ� ���� (�õ� {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return None
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"[MANUS AI] ��û ���� (�õ� {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"[MANUS AI] ��û ���� ����: {e}")
                    return None

        return None

    # ============================================================================
    # Projects API
    # ============================================================================

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        ������Ʈ ��� ��ȸ

        Returns:
            ������Ʈ ���
        """
        response = self._call_api("GET", "/v1/projects")
        if response:
            return response.get("projects", [])
        return []

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        ������Ʈ ��ȸ

        Args:
            project_id: ������Ʈ ID

        Returns:
            ������Ʈ ���� �Ǵ� None
        """
        return self._call_api("GET", f"/v1/projects/{project_id}")

    def create_project(self, name: str, description: Optional[str] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        ������Ʈ ����

        Args:
            name: ������Ʈ �̸�
            description: ������Ʈ ���� (������)
            **kwargs: �߰� �ʵ�

        Returns:
            ������ ������Ʈ ���� �Ǵ� None
        """
        payload = {
            "name": name,
            **kwargs
        }
        if description:
            payload["description"] = description

        response = self._call_api("POST", "/v1/projects", payload)
        if response:
            logger.info(f"[MANUS AI] ������Ʈ ���� ����: {name}")
        else:
            logger.warning("[MANUS AI] ������Ʈ ���� ����")
        return response

    # ============================================================================
    # Tasks API
    # ============================================================================

    def list_tasks(self, project_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        �۾� ��� ��ȸ

        Args:
            project_id: ������Ʈ ID (������)
            limit: �ִ� ����

        Returns:
            �۾� ���
        """
        endpoint = "/v1/tasks"
        if project_id:
            endpoint = f"/v1/projects/{project_id}/tasks"

        response = self._call_api("GET", endpoint, {"limit": limit})
        if response:
            return response.get("tasks", [])
        return []

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        �۾� ��ȸ

        Args:
            task_id: �۾� ID

        Returns:
            �۾� ���� �Ǵ� None
        """
        return self._call_api("GET", f"/v1/tasks/{task_id}")

    def create_task(
        self,
        prompt: str,
        agent_profile: str = "manus-1.6",
        project_id: Optional[str] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        �۾� ���� (AI �۾� ����)

        Args:
            prompt: �۾� ������Ʈ
            agent_profile: ������Ʈ ������ (�⺻��: "manus-1.6")
            project_id: ������Ʈ ID (������)
            **kwargs: �߰� �ʵ�

        Returns:
            ������ �۾� ���� �Ǵ� None
        """
        payload = {
            "prompt": prompt,
            "agentProfile": agent_profile,
            **kwargs
        }

        endpoint = "/v1/tasks"
        if project_id:
            endpoint = f"/v1/projects/{project_id}/tasks"

        response = self._call_api("POST", endpoint, payload)
        if response:
            logger.info(f"[MANUS AI] �۾� ���� ����: {prompt[:50]}...")
        else:
            logger.warning("[MANUS AI] �۾� ���� ����")
        return response

    def update_task(self, task_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        �۾� ����

        Args:
            task_id: �۾� ID
            **kwargs: ������ �ʵ�

        Returns:
            ������ �۾� ���� �Ǵ� None
        """
        response = self._call_api("PUT", f"/v1/tasks/{task_id}", kwargs)
        if response:
            logger.debug(f"[MANUS AI] �۾� ���� ����: {task_id}")
        else:
            logger.warning(f"[MANUS AI] �۾� ���� ����: {task_id}")
        return response

    def delete_task(self, task_id: str) -> bool:
        """
        �۾� ����

        Args:
            task_id: �۾� ID

        Returns:
            ���� ���� ����
        """
        response = self._call_api("DELETE", f"/v1/tasks/{task_id}")
        if response:
            logger.info(f"[MANUS AI] �۾� ���� ����: {task_id}")
            return True
        else:
            logger.warning(f"[MANUS AI] �۾� ���� ����: {task_id}")
            return False

    # ============================================================================
    # Files API
    # ============================================================================

    def upload_file(self, file_path: str, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        ���� ���ε�

        Args:
            file_path: ���ε��� ���� ���
            project_id: ������Ʈ ID (������)

        Returns:
            ���ε�� ���� ���� �Ǵ� None
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.error(f"[MANUS AI] ������ �������� �ʽ��ϴ�: {file_path}")
            return None

        try:
            endpoint = "/v1/files"
            if project_id:
                endpoint = f"/v1/projects/{project_id}/files"

            with open(file_path_obj, 'rb') as f:
                files = {'file': (file_path_obj.name, f, 'application/octet-stream')}
                headers = {}
                if self.api_key:
                    headers["API_KEY"] = self.api_key

                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    files=files,
                    headers=headers,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"[MANUS AI] ���� ���ε� ����: {file_path_obj.name}")
                return result
        except Exception as e:
            logger.error(f"[MANUS AI] ���� ���ε� ����: {e}")
            return None

    def list_files(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        ���� ��� ��ȸ

        Args:
            project_id: ������Ʈ ID (������)

        Returns:
            ���� ���
        """
        endpoint = "/v1/files"
        if project_id:
            endpoint = f"/v1/projects/{project_id}/files"

        response = self._call_api("GET", endpoint)
        if response:
            return response.get("files", [])
        return []

    # ============================================================================
    # Webhooks API
    # ============================================================================

    def create_webhook(
        self,
        url: str,
        events: List[str],
        project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        ���� ����

        Args:
            url: ���� URL
            events: �̺�Ʈ ����Ʈ (��: ["task.completed", "task.failed"])
            project_id: ������Ʈ ID (������)

        Returns:
            ������ ���� ���� �Ǵ� None
        """
        payload = {
            "url": url,
            "events": events
        }

        endpoint = "/v1/webhooks"
        if project_id:
            endpoint = f"/v1/projects/{project_id}/webhooks"

        response = self._call_api("POST", endpoint, payload)
        if response:
            logger.info(f"[MANUS AI] ���� ���� ����: {url}")
        else:
            logger.warning("[MANUS AI] ���� ���� ����")
        return response

    def list_webhooks(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        ���� ��� ��ȸ

        Args:
            project_id: ������Ʈ ID (������)

        Returns:
            ���� ���
        """
        endpoint = "/v1/webhooks"
        if project_id:
            endpoint = f"/v1/projects/{project_id}/webhooks"

        response = self._call_api("GET", endpoint)
        if response:
            return response.get("webhooks", [])
        return []

    # ============================================================================
    # Health Check
    # ============================================================================

    def health_check(self) -> bool:
        """
        API ���� ���� Ȯ��

        Returns:
            ���� ���� ����
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"[MANUS AI] �ｺ üũ ����: {e}")
            return False


def create_client_from_env() -> Optional[ManusAIClient]:
    """
    ȯ�� �������� Ŭ���̾�Ʈ ����

    ȯ�� ����:
        MANUS_AI_API_URL: Manus AI API URL (�⺻��: https://api.manus.ai)
        MANUS_AI_API_KEY: API Ű (������)
        MANUS_AI_ENABLED: Ȱ��ȭ ���� (1 �Ǵ� 0)

    Returns:
        ManusAIClient �ν��Ͻ� �Ǵ� None
    """
    base_url = os.environ.get("MANUS_AI_API_URL", "https://api.manus.ai")
    api_key = os.environ.get("MANUS_AI_API_KEY")
    enabled = os.environ.get("MANUS_AI_ENABLED", "1") == "1"

    return ManusAIClient(
        base_url=base_url,
        api_key=api_key,
        enabled=enabled
    )


# �׽�Ʈ �ڵ�
if __name__ == "__main__":
    client = create_client_from_env()

    if not client:
        print("ȯ�� ������ �����ϼ���:")
        print("  MANUS_AI_API_URL = https://api.manus.ai")
        print("  MANUS_AI_API_KEY = your_api_key")
        print("  MANUS_AI_ENABLED = 1")
        exit(1)

    # �ｺ üũ
    print("Manus AI API ���� Ȯ�� ��...")
    if client.health_check():
        print("? ���� ���� ����")
    else:
        print("? ���� ���� ����")

    # �׽�Ʈ �۾� ����
    print("\n�׽�Ʈ �۾� ���� ��...")
    if client.create_task(
        prompt="Write a function to calculate fibonacci numbers",
        agent_profile="manus-1.6"
    ):
        print("? �۾� ���� ����")
    else:
        print("? �۾� ���� ����")
