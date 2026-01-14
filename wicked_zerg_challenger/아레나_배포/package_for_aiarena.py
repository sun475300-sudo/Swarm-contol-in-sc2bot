#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
        [Wicked Zerg] AI Arena Packaging Script with Model Files
================================================================================
Problem Solved:
  1. Include reinforcement learning model files (.pt)
  2. Auto-select latest weights
  3. Optional checkpoint inclusion
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
import json


class AIArenaPackager:
    """AI Arena 제출용 패키징 시스템"""
    
    # ? AI Arena 제출용 필수 파일만 포함
    # ? 로컬 훈련용 파일 제외: parallel_train_integrated.py, main_integrated.py, upload_to_aiarena.py, arena_update.py
    ESSENTIAL_FILES = [
        # 핵심 코어
        "wicked_zerg_bot_pro.py",
        "run.py",  # ?? AI Arena 표준 규격으로 수정됨
        "config.py",
        
        # 신경망 모델 정의
        "zerg_net.py",
        
        # 게임 로직 모듈
        "combat_manager.py",
        "combat_tactics.py",
        "economy_manager.py",
        "production_manager.py",
        "production_resilience.py",
        "micro_controller.py",
        "scouting_system.py",
        "intel_manager.py",
        "map_manager.py",
        "queen_manager.py",
        "unit_factory.py",
        "personality_manager.py",
        "telemetry_logger.py",
        
        # 설정 파일
        "requirements.txt",
    ]
    
    # ? 모델 관련 파일 (최종 모델만 포함)
    MODEL_FILES = [
        "models/zerg_net_model.pt",  # 메인 모델 가중치
    ]
    
    def __init__(self, project_root: Path = None, include_checkpoints: bool = False):
        self.project_root = project_root or Path(__file__).parent.absolute()
        self.include_checkpoints = include_checkpoints
        
        # 출력 디렉토리
        self.output_dir = self.project_root / "deployment"
        self.temp_dir = self.output_dir / "temp_package"
        
        print("[*] AI Arena Packager 초기화")
        print(f"   프로젝트 루트: {self.project_root}")
        print(f"   출력 디렉토리: {self.output_dir}")
    
    def validate_project(self):
        """프로젝트 유효성 검사"""
        print("\n[*] 프로젝트 유효성 검사 중...")
        
        missing_files = []
        for file_name in self.ESSENTIAL_FILES:
            file_path = self.project_root / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            print(f"[!] 누락된 필수 파일: {', '.join(missing_files)}")
            return False
        
        print("[OK] 모든 필수 파일 확인 완료")
        return True
    
    def find_latest_model(self):
        """
        ? 최신 모델 파일 찾기
        - models/ 폴더에서 .pt 파일 검색
        - 가장 최근 수정된 파일 선택
        """
        models_dir = self.project_root / "models"
        
        if not models_dir.exists():
            print("?? models/ 폴더가 없습니다. 모델 파일 없이 패키징됩니다.")
            return None
        
        # .pt 파일 검색
        model_files = list(models_dir.glob("*.pt"))
        
        if not model_files:
            print("?? 모델 파일(.pt)이 없습니다.")
            return None
        
        # 최신 파일 선택
        latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
        
        model_size_mb = latest_model.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(latest_model.stat().st_mtime)
        
        print(f"\n? 최신 모델 파일 발견:")
        print(f"   파일명: {latest_model.name}")
        print(f"   크기: {model_size_mb:.2f} MB")
        print(f"   수정 시간: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return latest_model
    
    def find_checkpoints(self):
        """체크포인트 파일들 찾기"""
        checkpoints = []
        
        # 각 인스턴스의 체크포인트 폴더 검색
        training_data_dir = self.project_root / "training_data"
        
        if not training_data_dir.exists():
            return checkpoints
        
        for instance_dir in training_data_dir.iterdir():
            if instance_dir.is_dir():
                checkpoint_dir = instance_dir / "checkpoints"
                if checkpoint_dir.exists():
                    checkpoints.extend(checkpoint_dir.glob("*.pt"))
        
        return checkpoints
    
    def create_package_structure(self):
        """패키지 구조 생성 - AI Arena 규격에 맞춰 Flat 구조로 배치"""
        print("\n? 패키지 구조 생성 중...")
        
        # 임시 디렉토리 초기화
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 필수 파일 복사 (ZIP 루트에 Flat하게 배치)
        print("   - 필수 파일 복사 중 (Flat 구조)...")
        for file_name in self.ESSENTIAL_FILES:
            src = self.project_root / file_name
            # ?? 중요: 파일명만 추출하여 루트에 직접 배치 (경로 깊이 제거)
            dst = self.temp_dir / Path(file_name).name
            
            if src.exists():
                shutil.copy2(src, dst)
                print(f"      ? {file_name} → {dst.name}")
            else:
                print(f"      ? {file_name} 누락")
        
        # 2. 모델 파일 복사 (models/ 하위 폴더 유지 - 봇 코드에서 참조)
        print("   - 모델 파일 복사 중...")
        models_temp_dir = self.temp_dir / "models"
        models_temp_dir.mkdir(exist_ok=True)
        
        latest_model = self.find_latest_model()
        if latest_model:
            # ?? 표준 이름으로 복사: models/zerg_net_model.pt
            # 봇 코드에서 이 경로로 로드해야 함!
            dst_model = models_temp_dir / "zerg_net_model.pt"
            shutil.copy2(latest_model, dst_model)
            print(f"   ? 모델 포함: {latest_model.name} → models/zerg_net_model.pt")
        else:
            print("   ? 모델 파일 없음 (초기 상태로 제출)")
        
        # 3. 체크포인트 포함 (옵션)
        if self.include_checkpoints:
            print("   - 체크포인트 복사 중...")
            checkpoints = self.find_checkpoints()
            
            if checkpoints:
                checkpoint_dir = self.temp_dir / "checkpoints"
                checkpoint_dir.mkdir(exist_ok=True)
                
                for cp in checkpoints[:5]:  # 최대 5개만
                    shutil.copy2(cp, checkpoint_dir / cp.name)
                
                print(f"   ? {len(checkpoints)} 개 체크포인트 포함")
        
        # 4. 메타데이터 생성
        self._create_metadata()
        
        print("? 패키지 구조 생성 완료")
    
    def _create_metadata(self):
        """패키지 메타데이터 생성"""
        metadata = {
            "bot_name": "Wicked Zerg Challenger",
            "version": "1.0.0",
            "race": "Zerg",
            "packaged_at": datetime.now().isoformat(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "has_model": (self.project_root / "models").exists(),
            "has_checkpoints": self.include_checkpoints,
        }
        
        metadata_file = self.temp_dir / "package_info.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def create_zip(self):
        """ZIP 파일 생성 (불필요한 파일 필터링 포함)"""
        print("\n? ZIP 파일 생성 중...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"WickedZerg_AIArena_{timestamp}.zip"
        zip_path = self.output_dir / zip_name
        
        # ? 제외할 파일 패턴 (로컬 훈련 데이터, 캐시, 임시 파일)
        EXCLUDE_PATTERNS = [
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '*.backup',
            '*.pt.backup',
            '.git',
            '.gitignore',
            'training_data',
            'replays',
            'stats',
            'logs',
            'package_for_aiarena.py',  # 패키징 도구 자체
            'upload_to_aiarena.py',    # 업로드 도구
            'parallel_train_integrated.py',  # 로컬 훈련 스크립트
            'main_integrated.py',      # 로컬 훈련 스크립트
            'arena_update.py',         # 업데이트 스크립트
        ]
        
        def should_exclude(file_path: Path) -> bool:
            """파일이 제외 대상인지 확인"""
            file_str = str(file_path)
            for pattern in EXCLUDE_PATTERNS:
                if pattern in file_str or file_path.name == pattern:
                    return True
            return False
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.temp_dir):
                # __pycache__ 등 제외 디렉토리는 순회하지 않음
                dirs[:] = [d for d in dirs if d not in EXCLUDE_PATTERNS]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # 제외 대상 확인
                    if should_exclude(file_path):
                        print(f"      ? 제외: {file}")
                        continue
                    
                    arcname = file_path.relative_to(self.temp_dir)
                    zipf.write(file_path, arcname)
        
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        
        print(f"? ZIP 생성 완료:")
        print(f"   파일명: {zip_name}")
        print(f"   크기: {zip_size_mb:.2f} MB")
        print(f"   경로: {zip_path}")
        
        # ?? 용량 경고
        if zip_size_mb > 50:
            print(f"\n??  경고: ZIP 크기가 {zip_size_mb:.1f}MB입니다.")
            print(f"   AI Arena는 일반적으로 50MB 이하를 권장합니다.")
            print(f"   모델 파일이나 불필요한 데이터가 포함되었는지 확인하세요.")
        
        return zip_path
    
    def cleanup(self):
        """임시 파일 정리"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        print("\n? 임시 파일 정리 완료")
    
    def package(self):
        """전체 패키징 프로세스 실행"""
        print("\n" + "="*70)
        print("? AI ARENA PACKAGING - WICKED ZERG")
        print("="*70)
        
        try:
            # 1. 유효성 검사
            if not self.validate_project():
                print("\n? 패키징 실패: 프로젝트 유효성 검사 실패")
                return None
            
            # 2. 패키지 구조 생성
            self.create_package_structure()
            
            # 3. ZIP 생성
            zip_path = self.create_zip()
            
            # 4. 최종 검증
            self._verify_package(zip_path)
            
            # 5. 정리
            self.cleanup()
            
            # 6. 요약
            print("\n" + "="*70)
            print("? 패키징 완료!")
            print("="*70)
            print(f"\n? 제출 파일: {zip_path.name}")
            print(f"   위치: {zip_path}")
            print(f"\n? 다음 단계:")
            print(f"   1. ZIP 파일 내용 확인")
            print(f"   2. https://aiarena.net 업로드")
            print(f"   3. 첫 대전 결과 모니터링")
            print("\n? AI Arena에 업로드할 준비가 완료되었습니다!")
            
            return zip_path
            
        except Exception as e:
            print(f"\n? 패키징 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()
            return None
    
    def _verify_package(self, zip_path: Path):
        """ZIP 패키지 최종 검증"""
        print("\n? 패키지 내용 검증 중...")
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            file_list = zipf.namelist()
            
            # 필수 파일 확인
            print("   필수 파일 확인:")
            critical_files = ['run.py', 'wicked_zerg_bot_pro.py', 'config.py', 'zerg_net.py']
            for cfile in critical_files:
                if cfile in file_list:
                    print(f"      ? {cfile}")
                else:
                    print(f"      ? {cfile} 누락!")
            
            # 모델 파일 확인
            model_found = any('models/zerg_net_model.pt' in f for f in file_list)
            if model_found:
                print(f"      ? models/zerg_net_model.pt")
            else:
                print(f"      ??  모델 파일 없음 (초기 상태)")
            
            # 불필요한 파일 경고
            print("\n   불필요한 파일 검사:")
            unwanted_patterns = ['parallel_train', 'main_integrated', '__pycache__', 
                               'upload_to_aiarena', 'package_for_aiarena', '.backup']
            found_unwanted = False
            for pattern in unwanted_patterns:
                unwanted = [f for f in file_list if pattern in f]
                if unwanted:
                    found_unwanted = True
                    print(f"      ??  {pattern}: {len(unwanted)}개 발견")
                    for uf in unwanted[:3]:  # 최대 3개만 표시
                        print(f"         - {uf}")
            
            if not found_unwanted:
                print(f"      ? 깨끗한 패키지 (불필요한 파일 없음)")
            
            # 파일 개수 및 통계
            py_files = [f for f in file_list if f.endswith('.py')]
            pt_files = [f for f in file_list if f.endswith('.pt')]
            
            print(f"\n   ? 패키지 통계:")
            print(f"      전체 파일: {len(file_list)}개")
            print(f"      Python 파일: {len(py_files)}개")
            print(f"      모델 파일: {len(pt_files)}개")
        
        print("? 검증 완료")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Arena 패키징 도구")
    parser.add_argument("--include-checkpoints", action="store_true",
                       help="체크포인트 파일 포함")
    parser.add_argument("--project-root", type=str,
                       help="프로젝트 루트 경로 (기본: 현재 디렉토리)")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root) if args.project_root else None
    
    packager = AIArenaPackager(
        project_root=project_root,
        include_checkpoints=args.include_checkpoints
    )
    
    packager.package()


if __name__ == "__main__":
    main()
