#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
        ? Wicked Zerg - Parallel Training Script with Instance Isolation
================================================================================
각 인스턴스는 독립적인 폴더와 로그 파일을 사용하여 데이터 충돌 방지
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import time


class ParallelTrainingManager:
    """병렬 훈련 관리자 - 인스턴스별 격리"""
    
    def __init__(self, num_instances=4, base_port=8200):
        self.num_instances = num_instances
        self.base_port = base_port
        self.processes = []
        self.project_root = Path(__file__).parent.absolute()
        
    def create_instance_folders(self):
        """각 인스턴스별 격리된 폴더 구조 생성"""
        print("? 인스턴스별 격리 폴더 생성 중...")
        
        for i in range(self.num_instances):
            instance_id = f"instance_{i+1}"
            
            # 인스턴스별 폴더 생성
            instance_dirs = [
                self.project_root / "training_data" / instance_id / "logs",
                self.project_root / "training_data" / instance_id / "replays",
                self.project_root / "training_data" / instance_id / "checkpoints",
                self.project_root / "training_data" / instance_id / "stats",
            ]
            
            for dir_path in instance_dirs:
                dir_path.mkdir(parents=True, exist_ok=True)
                
            print(f"  ? {instance_id} 폴더 생성 완료")
    
    def start_training_instance(self, instance_id: str, port: int):
        """개별 훈련 인스턴스 시작"""
        print(f"\n? {instance_id} 시작 중 (Port: {port})...")
        
        # 환경변수 설정 (인스턴스별 격리)
        env = os.environ.copy()
        env["INSTANCE_ID"] = instance_id
        env["SC2_PORT"] = str(port)
        
        # Python 실행 명령
        cmd = [
            sys.executable,
            str(self.project_root / "main_integrated.py"),
            "--instance-id", instance_id,
            "--port", str(port),
        ]
        
        # 프로세스 시작
        try:
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.processes.append({
                "id": instance_id,
                "port": port,
                "process": process,
                "start_time": time.time()
            })
            
            print(f"  ? {instance_id} 시작됨 (PID: {process.pid})")
            return process
            
        except Exception as e:
            print(f"  ? {instance_id} 시작 실패: {e}")
            return None
    
    def monitor_instances(self):
        """실행 중인 인스턴스 모니터링"""
        print("\n" + "="*70)
        print("? 훈련 인스턴스 모니터링 시작")
        print("="*70)
        
        try:
            while True:
                time.sleep(10)  # 10초마다 체크
                
                active_count = 0
                for proc_info in self.processes:
                    if proc_info["process"].poll() is None:
                        active_count += 1
                    else:
                        # 종료된 프로세스 처리
                        return_code = proc_info["process"].returncode
                        print(f"\n?? {proc_info['id']} 종료됨 (코드: {return_code})")
                
                if active_count == 0:
                    print("\n? 모든 인스턴스 종료됨")
                    break
                    
                # 상태 출력
                runtime = time.time() - self.processes[0]["start_time"]
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"활성 인스턴스: {active_count}/{self.num_instances} | "
                      f"실행 시간: {runtime/60:.1f}분")
                
        except KeyboardInterrupt:
            print("\n\n?? 사용자가 중단 요청 (Ctrl+C)")
            self.stop_all_instances()
    
    def stop_all_instances(self):
        """모든 훈련 인스턴스 종료"""
        print("\n? 모든 인스턴스 종료 중...")
        
        for proc_info in self.processes:
            try:
                if proc_info["process"].poll() is None:
                    proc_info["process"].terminate()
                    proc_info["process"].wait(timeout=5)
                    print(f"  ? {proc_info['id']} 정상 종료")
            except Exception as e:
                print(f"  ?? {proc_info['id']} 강제 종료: {e}")
                proc_info["process"].kill()
    
    def run(self):
        """병렬 훈련 시작"""
        print("\n" + "="*70)
        print("? PARALLEL TRAINING MANAGER - WICKED ZERG")
        print("="*70)
        print(f"인스턴스 수: {self.num_instances}")
        print(f"시작 포트: {self.base_port}")
        print()
        
        # 1. 폴더 생성
        self.create_instance_folders()
        
        # 2. 각 인스턴스 시작
        print("\n" + "-"*70)
        for i in range(self.num_instances):
            instance_id = f"instance_{i+1}"
            port = self.base_port + i
            self.start_training_instance(instance_id, port)
            time.sleep(2)  # 각 인스턴스 시작 간격
        
        # 3. 모니터링
        self.monitor_instances()
        
        # 4. 결과 요약
        print("\n" + "="*70)
        print("? 훈련 세션 완료")
        print("="*70)
        
        for proc_info in self.processes:
            runtime = time.time() - proc_info["start_time"]
            print(f"{proc_info['id']}: {runtime/60:.1f}분 실행")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="병렬 훈련 관리자")
    parser.add_argument("--instances", type=int, default=4, 
                       help="동시 실행할 인스턴스 수 (기본: 4)")
    parser.add_argument("--base-port", type=int, default=8200,
                       help="시작 포트 번호 (기본: 8200)")
    
    args = parser.parse_args()
    
    manager = ParallelTrainingManager(
        num_instances=args.instances,
        base_port=args.base_port
    )
    
    manager.run()


if __name__ == "__main__":
    main()
