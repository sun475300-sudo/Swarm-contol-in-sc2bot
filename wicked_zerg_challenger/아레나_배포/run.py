#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
        ? Wicked Zerg Challenger - AI Arena Entry Point
================================================================================
?? AI Arena 서버 전용 파일 ??

이 파일은 AI Arena 서버가 봇을 실행하기 위해 사용합니다.
서버는 다음과 같이 봇을 로드합니다:
    from run import Bot

? 이 파일에는:
   - run_game() 호출이 없습니다
   - Computer() 상대 지정이 없습니다
   - 맵 지정이 없습니다
   
? 서버가 제공하는 환경:
   - 서버가 상대방 봇을 연결
   - 서버가 맵을 지정
   - 서버가 게임을 실행
"""

import sys
from pathlib import Path

# ?? CRITICAL: 현재 디렉토리를 sys.path에 추가 (모든 모듈이 Flat하게 배치됨)
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# Import the main bot class
from wicked_zerg_bot_pro import WickedZergBotPro


# ? AI Arena 표준: "Bot" 클래스 이름 사용
# 서버는 "from run import Bot"으로 봇을 임포트합니다
class Bot(WickedZergBotPro):
    """
    AI Arena 경쟁용 봇 클래스
    
    ?? 중요 설정:
    - train_mode=False: 학습 모드 완전 비활성화
    - epsilon=0.0: 무작위 행동 제거 (자동 설정됨)
    - instance_id=0: 단일 인스턴스 실행
    
    서버 환경:
    - 상대방: 서버가 자동으로 연결
    - 맵: 서버가 자동으로 선택
    - 게임 루프: 서버가 관리
    """
    def __init__(self):
        # ?? train_mode=False: 아레나에서는 절대 학습하지 않음!
        super().__init__(
            train_mode=False,    # 학습 모드 OFF
            instance_id=0,       # 메인 인스턴스
            personality="serral", # 기본 성격
        )
        print("=" * 70)
        print("? [AI ARENA] Wicked Zerg Bot - Competition Mode")
        print("   Train Mode: OFF (Inference Only)")
        print("   Waiting for server to start match...")
        print("=" * 70)


# ?? 이 파일을 직접 실행하면 안됩니다!
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("? ERROR: This file is for AI Arena server only!")
    print("=" * 70)
    print()
    print("This file should NOT be executed directly.")
    print("The AI Arena server will import the Bot class automatically.")
    print()
    print("For local testing, use:")
    print("  → python main_integrated.py")
    print()
    print("=" * 70)
    sys.exit(1)

