# -*- coding: utf-8 -*-
"""
================================================================================
                AI Arena 제출용 패키징 자동화 (package_for_aiarena.py)
================================================================================

로컬에서 훈련된 모델과 소스코드를 AI Arena 제출용 패키지로 자동 생성합니다.

기능:
    1. 훈련된 모델 가중치(.pt) 포함
    2. 필수 소스코드 자동 수집
    3. arena_deploy/ 폴더로 자동 복사
    4. 체크섬 검증 (모델 손상 방지)

사용법:
    python package_for_aiarena.py

출력:
    - arena_deploy/bot_package/ (제출용 완전 패키지)
    - arena_deploy/verification_report.txt (검증 보고서)

================================================================================
"""

import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class PackageBuilder:
    """AI Arena 제출용 패키지 빌더"""

    # 필수 소스코드 파일 (로직, 매니저, 신경망)
    ESSENTIAL_SOURCES: List[str] = [
        "run.py",                           # ? AI Arena 진입점
        "main_integrated.py",               # ? 로컬 훈련 진입점
        "wicked_zerg_bot_pro.py",          # ? 메인 봇 클래스
        # Core Managers
        "combat_manager.py",
        "production_manager.py",
        "economy_manager.py",
        "intel_manager.py",
        "micro_controller.py",
        "scouting_system.py",
        "queen_manager.py",
        "personality_manager.py",
        # Support
        "config.py",
        "sc2_integration_config.py",
        "curriculum_manager.py",
        "map_manager.py",
        # Learning
        "zerg_net.py",
        "hybrid_learning.py",
        "self_evolution.py",
        # Utilities
        "unit_factory.py",
        "combat_tactics.py",
        "production_resilience.py",
        "telemetry_logger.py",
        "arena_update.py",
    ]

    # 필수 모델 파일 (훈련 가중치)
    ESSENTIAL_MODELS: List[str] = [
        "models/zerg_net_model.pt",          # ? 신경망 모델 (가장 중요!)
    ]

    # 필수 데이터 파일
    ESSENTIAL_DATA: List[str] = [
        "data/",                            # ? 커리큘럼 훈련 통계
    ]

    # AI Arena 배포 폴더
    DEPLOY_DIR = Path("arena_deploy")
    PACKAGE_DIR = DEPLOY_DIR / "bot_package"
    BACKUP_DIR = DEPLOY_DIR / "backups"

    def __init__(self, project_root: Optional[Path] = None):
        """
        Args:
            project_root: 프로젝트 루트 경로 (기본값: 현재 파일 디렉토리)
        """
        self.project_root = project_root or Path(__file__).parent.absolute()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report: List[str] = []

    def log(self, message: str, level: str = "INFO"):
        """로그 메시지 출력 및 저장"""
        formatted = f"[{level}] {message}"
        print(formatted)
        self.report.append(formatted)

    def verify_file_exists(self, file_path: Path) -> bool:
        """파일 존재 여부 확인"""
        if file_path.exists():
            self.log(f"? Found: {file_path.name}", "OK")
            return True
        else:
            self.log(f"??  Missing: {file_path.name}", "WARNING")
            return False

    def calculate_checksum(self, file_path: Path) -> str:
        """파일 체크섬 계산 (무결성 검증)"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def copy_sources(self) -> bool:
        """필수 소스코드 파일 복사"""
        self.log("\n? Step 1: Copying source code files...")
        success_count = 0

        for source_file in self.ESSENTIAL_SOURCES:
            src = self.project_root / source_file
            dst = self.PACKAGE_DIR / source_file

            if self.verify_file_exists(src):
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                success_count += 1
            else:
                self.log(f"??  Skipped: {source_file} (not found)", "WARNING")

        self.log(f"? Copied {success_count}/{len(self.ESSENTIAL_SOURCES)} source files")
        return success_count > 0

    def copy_models(self) -> bool:
        """훈련된 모델 가중치 복사 (가장 중요!)"""
        self.log("\n? Step 2: Copying trained model weights...")
        success_count = 0

        for model_file in self.ESSENTIAL_MODELS:
            src = self.project_root / model_file
            dst = self.PACKAGE_DIR / model_file

            if self.verify_file_exists(src):
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                
                # 체크섬 검증
                src_checksum = self.calculate_checksum(src)
                dst_checksum = self.calculate_checksum(dst)
                
                if src_checksum == dst_checksum:
                    self.log(f"? Model verified: {model_file} (SHA256: {src_checksum[:16]}...)", "OK")
                    success_count += 1
                else:
                    self.log(f"? Checksum mismatch: {model_file}", "ERROR")
            else:
                self.log(
                    f"??  WARNING: Model not found: {model_file}\n"
                    f"   This model file is CRITICAL for AI Arena submission!\n"
                    f"   Without it, the bot will run with untrained weights.",
                    "CRITICAL"
                )

        if success_count == 0:
            self.log(
                "\n? CRITICAL: No model weights found!\n"
                "   You MUST train the model first: python main_integrated.py\n"
                "   Expected location: models/zerg_net_model.pt",
                "ERROR"
            )
        
        self.log(f"? Copied {success_count}/{len(self.ESSENTIAL_MODELS)} model files")
        return success_count > 0

    def copy_data(self) -> bool:
        """데이터 파일 복사 (커리큘럼 통계 등)"""
        self.log("\n? Step 3: Copying data files...")
        success_count = 0

        for data_item in self.ESSENTIAL_DATA:
            src = self.project_root / data_item
            dst = self.PACKAGE_DIR / data_item

            if src.is_dir():
                if src.exists():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    self.log(f"? Copied directory: {data_item}", "OK")
                    success_count += 1
                else:
                    self.log(f"??  Missing directory: {data_item}", "WARNING")
            else:
                if self.verify_file_exists(src):
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    success_count += 1

        self.log(f"? Copied {success_count}/{len(self.ESSENTIAL_DATA)} data directories")
        return success_count > 0

    def create_manifest(self) -> None:
        """패키지 매니페스트 파일 생성 (검증용)"""
        self.log("\n? Step 4: Creating package manifest...")

        manifest: Dict[str, object] = {
            "package_version": "1.0",
            "creation_timestamp": self.timestamp,
            "bot_name": "Wicked Zerg Challenger",
            "files": {
                "sources": self.ESSENTIAL_SOURCES,
                "models": self.ESSENTIAL_MODELS,
                "data": self.ESSENTIAL_DATA,
            },
            "model_checksums": {},
            "package_structure": {
                "bot_package/": "AI Arena 제출 패키지 (실행 가능)",
                "backups/": "이전 패키지 백업",
                "verification_report.txt": "검증 보고서",
            }
        }

        # 모델 체크섬 기록
        checksums = manifest.get("model_checksums")
        if isinstance(checksums, dict):
            for model_file in self.ESSENTIAL_MODELS:
                model_path = self.PACKAGE_DIR / model_file
                if model_path.exists():
                    checksum = self.calculate_checksum(model_path)
                    checksums[model_file] = checksum

        manifest_file = self.DEPLOY_DIR / "package_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        self.log(f"? Manifest created: {manifest_file.name}")

    def create_readme(self):
        """AI Arena 제출용 README 생성"""
        self.log("\n? Step 5: Creating AI Arena README...")

        readme_content = f"""# Wicked Zerg Challenger - AI Arena Edition

## 패키지 정보
- 생성 시각: {self.timestamp}
- 봇 이름: Wicked Zerg Challenger
- 타입: StarCraft II Zerg Bot

## 포함 파일
? **소스코드**: {len(self.ESSENTIAL_SOURCES)}개 파일
? **모델 가중치**: {len(self.ESSENTIAL_MODELS)}개 파일 (신경망 모델 포함)
? **데이터**: 커리큘럼 훈련 통계

## 중요 정보

### 모델 가중치 (훈련 결과)
이 패키지에는 로컬에서 수천 번의 자기강화학습(RL)으로 훈련된 신경망 모델이 포함되어 있습니다.
- 파일: `models/zerg_net_model.pt`
- 크기: 확인 필요
- 상태: ? 포함됨

### 제출 방법
1. `bot_package/` 폴더 전체를 AI Arena 웹사이트에 업로드
2. `run.py`가 자동으로 진입점으로 설정됨
3. AI Arena 서버가 `python run.py` 실행

### 주의사항
?? 이 패키지는 **Windows 로컬 환경에서 생성**되었습니다.
AI Arena 제출 전에 다음을 확인하세요:
- run.py의 SC2 경로가 Linux/멀티플랫폼 환경에 호환되는지 확인
- 절대 경로 대신 상대 경로 사용 확인
- 파이썬 의존성이 requirements.txt에 명시되어 있는지 확인

### 훈련 통계
- 커리큘럼 난이도: VeryEasy → CheatInsane
- 훈련 모드: 자기강화학습(REINFORCE) + 지도학습(Supervised)
- 최적화: 다중 인스턴스 병렬 훈련

---
Generated by package_for_aiarena.py
"""

        readme_file = self.DEPLOY_DIR / "README_AI_ARENA.md"
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)

        self.log(f"? README created: {readme_file.name}")

    def backup_previous_package(self):
        """이전 패키지 백업"""
        if self.PACKAGE_DIR.exists():
            self.log("\n? Backing up previous package...")
            self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            
            backup_name = f"bot_package_backup_{self.timestamp}"
            backup_path = self.BACKUP_DIR / backup_name
            
            shutil.move(str(self.PACKAGE_DIR), str(backup_path))
            self.log(f"? Backup created: {backup_name}")

    def build(self) -> bool:
        """전체 패키징 프로세스 실행"""
        self.log("=" * 80)
        self.log("? Wicked Zerg Challenger - AI Arena Packager")
        self.log("=" * 80)

        try:
            # 배포 디렉토리 초기화
            self.DEPLOY_DIR.mkdir(exist_ok=True)
            
            # 이전 패키지 백업
            if self.PACKAGE_DIR.exists():
                self.backup_previous_package()
            
            self.PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

            # Step 1: 소스코드 복사
            sources_ok = self.copy_sources()

            # Step 2: 모델 가중치 복사 (가장 중요!)
            models_ok = self.copy_models()

            # Step 3: 데이터 복사
            data_ok = self.copy_data()

            # Step 4: 매니페스트 생성
            self.create_manifest()

            # Step 5: README 생성
            self.create_readme()

            # 최종 보고서 생성
            self.save_report()

            # 최종 결과
            self.log("\n" + "=" * 80)
            if models_ok:
                self.log("? SUCCESS: Package created successfully with trained model!", "SUCCESS")
                self.log(f"   ? Location: {self.PACKAGE_DIR.absolute()}", "SUCCESS")
                self.log(f"   Ready for AI Arena submission! ?", "SUCCESS")
            else:
                self.log("??  WARNING: Package created but model weights may be missing!", "WARNING")
                self.log("   ? This package may not work properly on AI Arena!", "WARNING")
            
            self.log("=" * 80)

            return sources_ok and models_ok and data_ok

        except Exception as e:
            self.log(f"? ERROR: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

    def save_report(self):
        """검증 보고서 저장"""
        report_file = self.DEPLOY_DIR / "verification_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.report))
        self.log(f"\n? Verification report saved: {report_file.name}")


def main():
    """메인 진입점"""
    builder = PackageBuilder()
    success = builder.build()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
