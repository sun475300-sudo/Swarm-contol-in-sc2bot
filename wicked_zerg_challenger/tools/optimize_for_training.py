# -*- coding: utf-8 -*-
"""
훈련 최적화 도구

훈련에 필요한 핵심 파일만 남기고 불필요한 파일들을 정리합니다.
"""

import os
import shutil
import sys
from pathlib import Path
from typing import List, Set, Dict
import json

# 인코딩 설정
if sys.platform == "win32":
 import locale
 try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
 except AttributeError:
 pass

PROJECT_ROOT = Path(__file__).parent.parent


class TrainingOptimizer:
    """훈련 최적화기"""
 
 def __init__(self, dry_run: bool = True):
 self.dry_run = dry_run
 self.files_to_keep: Set[Path] = set()
 self.files_to_remove: List[Path] = []
 self.dirs_to_remove: List[Path] = []
 self.stats = {
            "files_kept": 0,
            "files_removed": 0,
            "dirs_removed": 0,
            "space_freed_mb": 0
 }
 
 def identify_essential_files(self):
        """훈련에 필수적인 파일 식별"""
 
 # 1. 핵심 실행 파일
 essential_files = [
            "run.py",
            "run_with_training.py",
            "wicked_zerg_bot_pro.py",
            "zerg_net.py",
            "config.py",
            "requirements.txt",
            "LICENSE",
            "pyrightconfig.json",
 ]
 
 # 2. 매니저 파일들
 manager_files = [
            "combat_manager.py",
            "economy_manager.py",
            "production_manager.py",
            "intel_manager.py",
            "scouting_system.py",
            "queen_manager.py",
            "micro_controller.py",
            "telemetry_logger.py",
            "rogue_tactics_manager.py",
            "unit_factory.py",
            "spell_unit_manager.py",
            "map_manager.py",
            "chat_manager.py",
            "genai_self_healing.py",
 ]
 
 # 3. 필수 디렉토리
 essential_dirs = [
            "combat/",
            "core/",
            "sc2_env/",
            "utils/",
            "config/",
            "local_training/",
            "models/",
            "data/",
            "bat/",
 ]
 
 # 4. local_training 필수 파일
 local_training_essential = [
            "local_training/main_integrated.py",
            "local_training/curriculum_manager.py",
            "local_training/combat_tactics.py",
            "local_training/production_resilience.py",
            "local_training/personality_manager.py",
            "local_training/strategy_audit.py",
            "local_training/scripts/",
 ]
 
 # 5. tools 필수 파일 (훈련에 사용되는 것만)
 tools_essential = [
            "tools/integrated_pipeline.py",
            "tools/hybrid_learning.py",
 ]
 
 # 모든 필수 파일 추가
 for file in essential_files + manager_files:
 path = PROJECT_ROOT / file
 if path.exists():
 self.files_to_keep.add(path)
 
 for file in local_training_essential + tools_essential:
 path = PROJECT_ROOT / file
 if path.exists():
 if path.is_dir():
 # 디렉토리면 내부 파일들도 추가
                    for subfile in path.rglob("*"):
                        if subfile.is_file() and not subfile.name.endswith('.bak'):
 self.files_to_keep.add(subfile)
 else:
 self.files_to_keep.add(path)
 
 # 필수 디렉토리 내부 파일들 추가
 for dir_path in essential_dirs:
 full_path = PROJECT_ROOT / dir_path
 if full_path.exists() and full_path.is_dir():
                for file in full_path.rglob("*"):
                    if file.is_file() and not file.name.endswith('.bak'):
 self.files_to_keep.add(file)
 
 def scan_for_removal(self):
        """제거할 파일 스캔"""
 
 # 1. .bak 파일들
        for bak_file in PROJECT_ROOT.rglob("*.bak"):
 if bak_file not in self.files_to_keep:
 self.files_to_remove.append(bak_file)
 
 # 2. 불필요한 .md 파일들 (README는 유지)
 keep_md = {
            "README.md", "README_BOT.md", "README_ko.md", "README_한국어.md",
            "SETUP_GUIDE.md", "LICENSE"
 }
 
        for md_file in PROJECT_ROOT.rglob("*.md"):
 if md_file.name not in keep_md and md_file not in self.files_to_keep:
 # local_training/설명서는 유지
                if "local_training/설명서" not in str(md_file):
 self.files_to_remove.append(md_file)
 
 # 3. backup_before_refactoring 폴더
        backup_dir = PROJECT_ROOT / "backup_before_refactoring"
 if backup_dir.exists():
 self.dirs_to_remove.append(backup_dir)
 
 # 4. monitoring 폴더 (훈련에는 불필요)
        monitoring_dir = PROJECT_ROOT / "monitoring"
 if monitoring_dir.exists():
 self.dirs_to_remove.append(monitoring_dir)
 
 # 5. static, services 폴더 (훈련에는 불필요)
        for dir_name in ["static", "services"]:
 dir_path = PROJECT_ROOT / dir_name
 if dir_path.exists():
 self.dirs_to_remove.append(dir_path)
 
 # 6. tools 폴더에서 훈련에 불필요한 파일들
        tools_dir = PROJECT_ROOT / "tools"
 if tools_dir.exists():
 for tool_file in tools_dir.iterdir():
 if tool_file.is_file():
 # 필수 파일이 아니고 .bak이 아니면 제거 대상
                    if tool_file not in self.files_to_keep and not tool_file.name.endswith('.bak'):
 # 일부 유용한 도구는 유지
 keep_tools = {
                            "integrated_pipeline.py",
                            "hybrid_learning.py",
                            "optimize_for_training.py",  # 자기 자신
 }
 if tool_file.name not in keep_tools:
 self.files_to_remove.append(tool_file)
 
 # 7. 설명서 폴더 (일부는 유지)
        설명서_dir = PROJECT_ROOT / "설명서"
 if 설명서_dir.exists():
            for md_file in 설명서_dir.rglob("*.md"):
 # FILE_STRUCTURE.md 같은 중요한 문서는 유지
                keep_docs = {"FILE_STRUCTURE.md", "README.md"}
 if md_file.name not in keep_docs:
 self.files_to_remove.append(md_file)
 
 # 8. docs 폴더 (일부는 유지)
        docs_dir = PROJECT_ROOT / "docs"
 if docs_dir.exists():
            for doc_file in docs_dir.rglob("*"):
 if doc_file.is_file():
 # API_DOCUMENTATION.md 같은 중요한 문서는 유지
                    keep_docs = {"API_DOCUMENTATION.md", "README.md"}
 if doc_file.name not in keep_docs:
 self.files_to_remove.append(doc_file)
 
 def calculate_space(self) -> float:
        """제거할 파일들의 총 크기 계산 (MB)"""
 total_size = 0
 
 for file_path in self.files_to_remove:
 try:
 if file_path.exists():
 total_size += file_path.stat().st_size
 except (OSError, PermissionError):
 pass
 
 for dir_path in self.dirs_to_remove:
 try:
 if dir_path.exists():
                    for file_path in dir_path.rglob("*"):
 try:
 if file_path.is_file():
 total_size += file_path.stat().st_size
 except (OSError, PermissionError):
 pass
 except (OSError, PermissionError):
 pass
 
 return total_size / (1024 * 1024) # MB
 
 def generate_report(self) -> str:
        """최적화 리포트 생성"""
 report = []
        report.append("=" * 70)
        report.append("훈련 최적화 리포트")
        report.append("=" * 70)
        report.append("")
 
        report.append(f"유지할 파일: {len(self.files_to_keep)}개")
        report.append(f"제거할 파일: {len(self.files_to_remove)}개")
        report.append(f"제거할 디렉토리: {len(self.dirs_to_remove)}개")
        report.append(f"절약할 공간: {self.calculate_space():.2f} MB")
        report.append("")
 
 if self.files_to_remove:
            report.append("제거할 파일 목록 (상위 20개):")
 for i, file_path in enumerate(self.files_to_remove[:20], 1):
 try:
 rel_path = file_path.relative_to(PROJECT_ROOT)
 size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0
                    report.append(f"  {i}. {rel_path} ({size_mb:.2f} MB)")
 except (OSError, ValueError):
                    report.append(f"  {i}. {file_path} (크기 확인 불가)")
 if len(self.files_to_remove) > 20:
                report.append(f"  ... 외 {len(self.files_to_remove) - 20}개 파일")
            report.append("")
 
 if self.dirs_to_remove:
            report.append("제거할 디렉토리:")
 for dir_path in self.dirs_to_remove:
 rel_path = dir_path.relative_to(PROJECT_ROOT)
                report.append(f"  - {rel_path}")
            report.append("")
 
        return "\n".join(report)
 
 def execute_optimization(self):
        """최적화 실행"""
 if self.dry_run:
            print("[DRY RUN] 최적화를 실행하지 않습니다.")
 return
 
        print("최적화 실행 중...")
 
 # 파일 제거
 for file_path in self.files_to_remove:
 try:
 if file_path.exists():
 size = file_path.stat().st_size
 file_path.unlink()
                    self.stats["files_removed"] += 1
                    self.stats["space_freed_mb"] += size / (1024 * 1024)
 except (OSError, PermissionError) as e:
                print(f"[WARNING] 파일 제거 실패: {file_path} - {e}")
 
 # 디렉토리 제거
 for dir_path in self.dirs_to_remove:
 try:
 if dir_path.exists():
 # 디렉토리 크기 계산
 dir_size = sum(
                        f.stat().st_size for f in dir_path.rglob("*") if f.is_file()
 )
 shutil.rmtree(dir_path)
 self.dirs_to_remove.append(dir_path)
                    self.stats["dirs_removed"] += 1
                    self.stats["space_freed_mb"] += dir_size / (1024 * 1024)
 except Exception as e:
                print(f"[WARNING] 디렉토리 제거 실패: {dir_path} - {e}")
 
        print(f"\n최적화 완료!")
        print(f"  제거된 파일: {self.stats['files_removed']}개")
        print(f"  제거된 디렉토리: {self.stats['dirs_removed']}개")
        print(f"  절약된 공간: {self.stats['space_freed_mb']:.2f} MB")


def main():
    """메인 함수"""
 import argparse
 
    parser = argparse.ArgumentParser(description="훈련 최적화 도구")
    parser.add_argument("--execute", action="store_true", help="실제로 최적화 실행 (기본값: dry-run)")
    parser.add_argument("--report-only", action="store_true", help="리포트만 생성")
 
 args = parser.parse_args()
 
 optimizer = TrainingOptimizer(dry_run=not args.execute)
 
    print("훈련 필수 파일 식별 중...")
 optimizer.identify_essential_files()
 
    print("제거 대상 파일 스캔 중...")
 optimizer.scan_for_removal()
 
 # 리포트 생성
 report = optimizer.generate_report()
 print(report)
 
 # 리포트 파일로 저장
    report_path = PROJECT_ROOT / "TRAINING_OPTIMIZATION_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
 f.write(report)
    print(f"\n리포트 저장: {report_path}")
 
 if args.execute and not args.report_only:
        print("\n최적화를 실행하시겠습니까? (y/N): ", end="")
 response = input().strip().lower()
        if response == 'y':
 optimizer.dry_run = False
 optimizer.execute_optimization()
 else:
            print("최적화가 취소되었습니다.")
 elif args.report_only:
        print("\n[REPORT ONLY] 리포트만 생성되었습니다.")


if __name__ == "__main__":
 main()