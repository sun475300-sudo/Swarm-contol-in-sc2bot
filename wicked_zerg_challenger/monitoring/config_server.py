#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config Server - Dynamic URL Management System
Ngrok URL을 외부 저장소(Github Gist/Pastebin)에 저장하여
앱을 다시 빌드하지 않고도 URL을 업데이트할 수 있게 합니다.

사용 방법:
1. Github Gist 사용 (권장):
   - https://gist.github.com 에서 새 Gist 생성
   - 파일명: server_url.txt
   - Gist ID를 환경변수에 설정: export GIST_ID="your-gist-id"
   - Personal Access Token 설정: export GITHUB_TOKEN="your-token"

2. Pastebin 사용 (대안):
   - https://pastebin.com 에서 API 키 발급
   - 환경변수 설정: export PASTEBIN_API_KEY="your-api-key"

3. 로컬 파일 사용 (개발용):
   - .config_server_url.txt 파일에 URL 저장
"""

import os
import json
import requests
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ConfigServer:
    """동적 URL 관리 서버"""
    
    def __init__(self):
        self.gist_id = os.environ.get("GIST_ID")
        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.pastebin_api_key = os.environ.get("PASTEBIN_API_KEY")
        self.local_config_file = Path(__file__).parent / ".config_server_url.txt"
        
    def _get_ngrok_url(self) -> Optional[str]:
        """Ngrok URL 가져오기"""
        try:
            # Ngrok API에서 URL 가져오기
            response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get("tunnels", [])
                if tunnels:
                    for tunnel in tunnels:
                        if tunnel.get("proto") == "https":
                            return tunnel.get("public_url", "")
                    if tunnels:
                        return tunnels[0].get("public_url", "")
        except Exception as e:
            logger.debug(f"Ngrok API 접근 실패: {e}")
        
        # 파일에서 시도
        try:
            ngrok_url_file = Path(__file__).parent / ".ngrok_url.txt"
            if ngrok_url_file.exists():
                with open(ngrok_url_file, 'r', encoding='utf-8') as f:
                    url = f.read().strip()
                    if url:
                        return url
        except Exception:
            pass
        
        return None
    
    def _update_github_gist(self, url: str) -> bool:
        """Github Gist에 URL 업데이트"""
        if not self.gist_id or not self.github_token:
            return False
        
        try:
            # Gist 정보 가져오기
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            get_url = f"https://api.github.com/gists/{self.gist_id}"
            response = requests.get(get_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Gist 정보 가져오기 실패: {response.status_code}")
                return False
            
            gist_data = response.json()
            files = gist_data.get("files", {})
            
            # server_url.txt 파일 찾기 또는 생성
            filename = "server_url.txt"
            file_content = {
                filename: {
                    "content": url
                }
            }
            
            # 기존 파일이 있으면 업데이트, 없으면 새로 생성
            if filename not in files:
                logger.info(f"새 파일 생성: {filename}")
            
            # Gist 업데이트
            update_url = f"https://api.github.com/gists/{self.gist_id}"
            update_data = {
                "files": file_content,
                "description": "SC2 Bot Server URL (Auto-updated)"
            }
            
            response = requests.patch(update_url, headers=headers, json=update_data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Github Gist 업데이트 성공: {url}")
                return True
            else:
                logger.error(f"Gist 업데이트 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Github Gist 업데이트 중 오류: {e}")
            return False
    
    def _update_pastebin(self, url: str) -> bool:
        """Pastebin에 URL 업데이트"""
        if not self.pastebin_api_key:
            return False
        
        try:
            # Pastebin API를 사용하여 새 paste 생성
            # 참고: Pastebin API는 업데이트가 제한적이므로 새 paste를 생성합니다
            paste_url = "https://pastebin.com/api/api_post.php"
            
            data = {
                "api_dev_key": self.pastebin_api_key,
                "api_option": "paste",
                "api_paste_code": url,
                "api_paste_name": "SC2 Bot Server URL",
                "api_paste_private": "1",  # 비공개
                "api_paste_expire_date": "N"  # 만료 없음
            }
            
            response = requests.post(paste_url, data=data, timeout=10)
            
            if response.status_code == 200 and response.text.startswith("http"):
                paste_url = response.text.strip()
                logger.info(f"✅ Pastebin 생성 성공: {paste_url}")
                # Pastebin URL을 로컬 파일에 저장 (앱에서 읽을 수 있도록)
                with open(self.local_config_file, 'w', encoding='utf-8') as f:
                    f.write(paste_url)
                return True
            else:
                logger.error(f"Pastebin 생성 실패: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Pastebin 업데이트 중 오류: {e}")
            return False
    
    def _update_local_file(self, url: str) -> bool:
        """로컬 파일에 URL 저장 (개발용)"""
        try:
            with open(self.local_config_file, 'w', encoding='utf-8') as f:
                f.write(url)
            logger.info(f"✅ 로컬 파일 업데이트: {url}")
            return True
        except Exception as e:
            logger.error(f"로컬 파일 업데이트 실패: {e}")
            return False
    
    def update_server_url(self) -> bool:
        """서버 URL 업데이트 (우선순위: Gist > Pastebin > 로컬 파일)"""
        url = self._get_ngrok_url()
        if not url:
            logger.warning("Ngrok URL을 찾을 수 없습니다.")
            return False
        
        # Github Gist 시도
        if self._update_github_gist(url):
            return True
        
        # Pastebin 시도
        if self._update_pastebin(url):
            return True
        
        # 로컬 파일 사용 (개발용)
        return self._update_local_file(url)
    
    def get_server_url(self) -> Optional[str]:
        """저장된 서버 URL 가져오기"""
        # 로컬 파일에서 읽기
        if self.local_config_file.exists():
            try:
                with open(self.local_config_file, 'r', encoding='utf-8') as f:
                    url = f.read().strip()
                    if url:
                        return url
            except Exception:
                pass
        
        return None


def main():
    """메인 함수"""
    import sys
    
    print("=" * 70)
    print("Config Server - 동적 URL 관리 시스템")
    print("=" * 70)
    print()
    
    config_server = ConfigServer()
    
    # 환경변수 확인
    print("환경변수 확인:")
    print(f"  GIST_ID: {'설정됨' if config_server.gist_id else '❌ 미설정'}")
    print(f"  GITHUB_TOKEN: {'설정됨' if config_server.github_token else '❌ 미설정'}")
    print(f"  PASTEBIN_API_KEY: {'설정됨' if config_server.pastebin_api_key else '❌ 미설정'}")
    print()
    
    # URL 업데이트
    print("서버 URL 업데이트 중...")
    if config_server.update_server_url():
        print("✅ 업데이트 완료!")
        url = config_server.get_server_url()
        if url:
            print(f"  저장된 URL: {url}")
    else:
        print("❌ 업데이트 실패")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
