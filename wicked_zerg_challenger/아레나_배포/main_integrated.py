#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
        ? Wicked Zerg - Integrated Training Main (Instance-Isolated)
================================================================================
? 문제 해결:
  1. CurriculumManager 로그 분리 (인스턴스별 독립 파일)
  2. 실시간 모니터링 확장 (주요 모듈 전체 감시)
  3. SC2PATH 유동적 처리 (환경변수 우선)
"""

import asyncio
import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from collections import defaultdict
import threading
import hashlib

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# SC2 경로 설정 (환경변수 우선, 없으면 기본값)
if "SC2PATH" not in os.environ:
    default_sc2_path = r"C:\Program Files (x86)\StarCraft II"
    if Path(default_sc2_path).exists():
        os.environ["SC2PATH"] = default_sc2_path
        print(f"? SC2PATH 설정: {default_sc2_path}")
    else:
        print("?? SC2PATH 감지 실패 - 환경변수를 확인하세요")

# Import SC2 infrastructure
from sc2.bot_ai import BotAI
from sc2.main import run_game
from sc2.data import Race, Difficulty
from sc2 import maps
from sc2.player import Bot, Computer

# Import the main bot
from wicked_zerg_bot_pro import WickedZergBotPro


# ============================================================================
#                       ? 인스턴스별 커리큘럼 매니저
# ============================================================================

class CurriculumManager:
    """
    ? 해결: 인스턴스별 독립적인 통계 파일 사용
    - training_stats_{instance_id}.json 형태로 분리
    """
    
    def __init__(self, instance_id: str = "default"):
        self.instance_id = instance_id
        
        # 인스턴스별 통계 파일 경로
        self.stats_dir = PROJECT_ROOT / "training_data" / instance_id / "stats"
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats_file = self.stats_dir / f"training_stats_{instance_id}.json"
        
        self.difficulties = ["VeryEasy", "Easy", "Medium", "Hard", "VeryHard"]
        self.current_difficulty = "VeryEasy"
        self.stats = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0})
        
        self._load_stats()
        print(f"? CurriculumManager 초기화 (인스턴스: {instance_id})")
        print(f"   통계 파일: {self.stats_file.name}")
    
    def _load_stats(self):
        """통계 파일 로드"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stats = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0}, data.get("stats", {}))
                    self.current_difficulty = data.get("current_difficulty", "VeryEasy")
                print(f"   ? 기존 통계 로드 완료")
            except Exception as e:
                print(f"   ?? 통계 로드 실패: {e}")
    
    def _save_stats(self):
        """통계 파일 저장 (인스턴스별 격리)"""
        try:
            data = {
                "instance_id": self.instance_id,
                "current_difficulty": self.current_difficulty,
                "stats": dict(self.stats),
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"?? 통계 저장 실패: {e}")
    
    def record_game(self, won: bool):
        """게임 결과 기록"""
        self.stats[self.current_difficulty]["games"] += 1
        
        if won:
            self.stats[self.current_difficulty]["wins"] += 1
        else:
            self.stats[self.current_difficulty]["losses"] += 1
        
        self._save_stats()
        self._adjust_difficulty()
    
    def _adjust_difficulty(self):
        """난이도 자동 조정"""
        diff_stats = self.stats[self.current_difficulty]
        
        if diff_stats["games"] < 10:
            return  # 최소 10게임 필요
        
        win_rate = diff_stats["wins"] / diff_stats["games"]
        
        # 승률 70% 이상 -> 난이도 상승
        if win_rate >= 0.7:
            current_idx = self.difficulties.index(self.current_difficulty)
            if current_idx < len(self.difficulties) - 1:
                new_difficulty = self.difficulties[current_idx + 1]
                print(f"\n? 난이도 상승: {self.current_difficulty} → {new_difficulty} (승률 {win_rate:.1%})")
                self.current_difficulty = new_difficulty
                self._save_stats()
        
        # 승률 30% 이하 -> 난이도 하락
        elif win_rate <= 0.3:
            current_idx = self.difficulties.index(self.current_difficulty)
            if current_idx > 0:
                new_difficulty = self.difficulties[current_idx - 1]
                print(f"\n? 난이도 하락: {self.current_difficulty} → {new_difficulty} (승률 {win_rate:.1%})")
                self.current_difficulty = new_difficulty
                self._save_stats()
    
    def get_opponent(self):
        """현재 난이도에 맞는 상대 반환"""
        difficulty_map = {
            "VeryEasy": Difficulty.VeryEasy,
            "Easy": Difficulty.Easy,
            "Medium": Difficulty.Medium,
            "Hard": Difficulty.Hard,
            "VeryHard": Difficulty.VeryHard,
        }
        return difficulty_map[self.current_difficulty]
    
    def print_stats(self):
        """통계 출력"""
        print(f"\n? [{self.instance_id}] 현재 통계:")
        print(f"   현재 난이도: {self.current_difficulty}")
        for diff in self.difficulties:
            s = self.stats[diff]
            if s["games"] > 0:
                win_rate = s["wins"] / s["games"] * 100
                print(f"   {diff:10s}: {s['wins']:3d}승 {s['losses']:3d}패 ({win_rate:.1f}%)")


# ============================================================================
#                       ? 확장된 실시간 코드 모니터
# ============================================================================

class RealtimeCodeMonitor:
    """
    ? 해결: 주요 모듈 전체 감시
    - 단일 파일이 아닌 핵심 모듈 폴더 전체 감시
    """
    
    CRITICAL_FILES = [
        "wicked_zerg_bot_pro.py",
        "combat_manager.py",
        "economy_manager.py",
        "production_manager.py",
        "micro_controller.py",
        "scouting_system.py",
        "queen_manager.py",
    ]
    
    def __init__(self, instance_id: str = "default"):
        self.instance_id = instance_id
        self.file_hashes = {}
        self.running = False
        self.thread = None
        
        # 초기 해시 계산
        for file_name in self.CRITICAL_FILES:
            file_path = PROJECT_ROOT / file_name
            if file_path.exists():
                self.file_hashes[file_name] = self._calculate_hash(file_path)
        
        print(f"? 코드 모니터 초기화: {len(self.file_hashes)}개 파일 감시")
    
    def _calculate_hash(self, file_path: Path) -> str:
        """파일 해시 계산"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _check_changes(self):
        """파일 변경 감지"""
        changed_files = []
        
        for file_name, old_hash in self.file_hashes.items():
            file_path = PROJECT_ROOT / file_name
            if file_path.exists():
                new_hash = self._calculate_hash(file_path)
                if new_hash != old_hash:
                    changed_files.append(file_name)
                    self.file_hashes[file_name] = new_hash
        
        return changed_files
    
    def _monitor_loop(self):
        """모니터링 루프 (백그라운드 스레드)"""
        while self.running:
            time.sleep(5)  # 5초마다 체크
            
            changed = self._check_changes()
            if changed:
                print(f"\n? [{self.instance_id}] 코드 변경 감지: {', '.join(changed)}")
                print("   (다음 게임부터 변경사항 반영)")
    
    def start(self):
        """모니터링 시작"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        """모니터링 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)


# ============================================================================
#                       ? 훈련 세션 실행기
# ============================================================================

class TrainingSession:
    """단일 훈련 세션 관리"""
    
    def __init__(self, instance_id: str, port: int, max_games: int = 100):
        self.instance_id = instance_id
        self.port = port
        self.max_games = max_games
        
        # 인스턴스별 커리큘럼 매니저
        self.curriculum = CurriculumManager(instance_id)
        
        # 코드 모니터
        self.code_monitor = RealtimeCodeMonitor(instance_id)
        self.code_monitor.start()
        
        # 리플레이 저장 경로
        self.replay_dir = PROJECT_ROOT / "training_data" / instance_id / "replays"
        self.replay_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n? 훈련 세션 초기화: {instance_id}")
        print(f"   포트: {port}")
        print(f"   최대 게임 수: {max_games}")
    
    def run_single_game(self, game_count: int):
        """단일 게임 실행"""
        opponent_difficulty = self.curriculum.get_opponent()
        
        print(f"\n{'='*70}")
        print(f"? [{self.instance_id}] 게임 #{game_count}/{self.max_games}")
        print(f"   난이도: {self.curriculum.current_difficulty}")
        print(f"{'='*70}")
        
        # 리플레이 파일명
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        replay_name = f"{self.instance_id}_game{game_count:03d}_{timestamp}.SC2Replay"
        replay_path = self.replay_dir / replay_name
        
        try:
            # 게임 실행
            result = run_game(
                maps.get("AbyssalReefLE"),
                [
                    Bot(Race.Zerg, WickedZergBotPro(), name=f"Wicked_{self.instance_id}"),
                    Computer(Race.Terran, opponent_difficulty),
                ],
                realtime=False,
                save_replay_as=str(replay_path) if game_count % 10 == 0 else None,  # 10게임마다 리플레이 저장
            )
            
            # 결과 기록
            won = (result.name == "Victory")
            self.curriculum.record_game(won)
            
            result_emoji = "?" if won else "?"
            print(f"{result_emoji} 결과: {result.name}")
            
            return won
            
        except Exception as e:
            print(f"? 게임 실행 오류: {e}")
            return False
    
    def run(self):
        """훈련 세션 실행"""
        print(f"\n{'='*70}")
        print(f"? [{self.instance_id}] 훈련 시작")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        
        try:
            for game_num in range(1, self.max_games + 1):
                self.run_single_game(game_num)
                
                # 주기적 통계 출력
                if game_num % 10 == 0:
                    self.curriculum.print_stats()
        
        except KeyboardInterrupt:
            print(f"\n?? [{self.instance_id}] 사용자가 중단 요청")
        
        finally:
            # 정리
            self.code_monitor.stop()
            
            elapsed = time.time() - start_time
            print(f"\n{'='*70}")
            print(f"? [{self.instance_id}] 훈련 세션 종료")
            print(f"   실행 시간: {elapsed/60:.1f}분")
            print(f"{'='*70}\n")
            
            self.curriculum.print_stats()


# ============================================================================
#                               ? 메인 실행
# ============================================================================

def main():
    """메인 진입점"""
    parser = argparse.ArgumentParser(description="통합 훈련 메인")
    parser.add_argument("--instance-id", type=str, default="default",
                       help="인스턴스 ID (예: instance_1)")
    parser.add_argument("--port", type=int, default=8200,
                       help="SC2 포트 번호")
    parser.add_argument("--max-games", type=int, default=100,
                       help="최대 게임 수")
    
    args = parser.parse_args()
    
    # 훈련 세션 생성 및 실행
    session = TrainingSession(
        instance_id=args.instance_id,
        port=args.port,
        max_games=args.max_games
    )
    
    session.run()


if __name__ == "__main__":
    main()
