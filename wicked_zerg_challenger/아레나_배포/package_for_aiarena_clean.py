#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Arena Packaging Script for Wicked Zerg Bot
Includes model files and creates clean deployment package
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
import json


class AIArenaPackager:
    """AI Arena deployment packaging system"""

    # Essential files for AI Arena submission
    # Only files needed to run the bot (no training scripts)
    ESSENTIAL_FILES = [
        # Core files
        "wicked_zerg_bot_pro.py",
        "run.py",  # AI Arena entry point
        "config.py",

        # Neural network
        "zerg_net.py",

        # Game logic modules
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

        # Configuration
        "requirements.txt",
    ]

    # Model files (latest only)
    MODEL_FILES = [
        "models/zerg_net_model.pt",
    ]

    def __init__(self, project_root: Path = None, include_checkpoints: bool = False):
        self.project_root = project_root or Path(__file__).parent.absolute()
        self.include_checkpoints = include_checkpoints

        self.output_dir = self.project_root / "deployment"
        self.temp_dir = self.output_dir / "temp_package"

        print("[*] AI Arena Packager initialized")
        print(f"    Project root: {self.project_root}")
        print(f"    Output dir: {self.output_dir}")

    def validate_project(self):
        """Validate project files"""
        print("\n[*] Validating project...")

        missing_files = []
        for file_name in self.ESSENTIAL_FILES:
            file_path = self.project_root / file_name
            if not file_path.exists():
                missing_files.append(file_name)

        if missing_files:
            print(f"[!] Missing files: {', '.join(missing_files)}")
            return False

        print("[OK] All required files found")
        return True

    def find_latest_model(self):
        """Find latest model file"""
        models_dir = self.project_root / "models"

        if not models_dir.exists():
            print("[!] models/ folder not found")
            return None

        model_files = list(models_dir.glob("*.pt"))

        if not model_files:
            print("[!] No model files (.pt) found")
            return None

        latest_model = max(model_files, key=lambda p: p.stat().st_mtime)

        model_size_mb = latest_model.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(latest_model.stat().st_mtime)

        print(f"\n[*] Latest model found:")
        print(f"    File: {latest_model.name}")
        print(f"    Size: {model_size_mb:.2f} MB")
        print(f"    Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")

        return latest_model

    def create_package_structure(self):
        """Create package structure - Flat layout for AI Arena"""
        print("\n[*] Creating package structure...")

        # Clean temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy essential files (FLAT structure - all in root)
        print("    - Copying essential files (Flat structure)...")
        for file_name in self.ESSENTIAL_FILES:
            src = self.project_root / file_name
            # Extract filename only to place in root (remove path depth)
            dst = self.temp_dir / Path(file_name).name

            if src.exists():
                shutil.copy2(src, dst)
                print(f"      [OK] {file_name} -> {dst.name}")
            else:
                print(f"      [!] {file_name} missing")

        # 2. Copy model files (keep models/ subfolder)
        print("    - Copying model files...")
        models_temp_dir = self.temp_dir / "models"
        models_temp_dir.mkdir(exist_ok=True)

        latest_model = self.find_latest_model()
        if latest_model:
            # Copy to standard name: models/zerg_net_model.pt
            dst_model = models_temp_dir / "zerg_net_model.pt"
            shutil.copy2(latest_model, dst_model)
            print(f"    [OK] Model: {latest_model.name} -> models/zerg_net_model.pt")
        else:
            print("    [!] No model file (submitting untrained bot)")

        # 3. Create metadata
        self._create_metadata()

        print("[OK] Package structure created")

    def _create_metadata(self):
        """Create package metadata"""
        metadata = {
            "bot_name": "Wicked Zerg Challenger",
            "version": "1.0.0",
            "race": "Zerg",
            "packaged_at": datetime.now().isoformat(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "has_model": (self.project_root / "models").exists(),
        }

        metadata_file = self.temp_dir / "package_info.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def create_zip(self):
        """Create ZIP file with filtering"""
        print("\n[*] Creating ZIP file...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"WickedZerg_AIArena_{timestamp}.zip"
        zip_path = self.output_dir / zip_name

        # Exclude patterns (training data, cache, temp files)
        EXCLUDE_PATTERNS = [
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '*.backup',
            '*.pt.backup',
            '.git',
            'training_data',
            'replays',
            'logs',
            'package_for_aiarena.py',
            'upload_to_aiarena.py',
            'parallel_train_integrated.py',
            'main_integrated.py',
            'arena_update.py',
        ]

        def should_exclude(file_path: Path) -> bool:
            """Check if file should be excluded"""
            file_str = str(file_path)
            for pattern in EXCLUDE_PATTERNS:
                if pattern in file_str or file_path.name == pattern:
                    return True
            return False

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.temp_dir):
                # Exclude directories matching patterns
                dirs[:] = [d for d in dirs if d not in EXCLUDE_PATTERNS]

                for file in files:
                    file_path = Path(root) / file

                    if should_exclude(file_path):
                        print(f"      [SKIP] {file}")
                        continue

                    arcname = file_path.relative_to(self.temp_dir)
                    zipf.write(file_path, arcname)

        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)

        print(f"[OK] ZIP created:")
        print(f"    File: {zip_name}")
        print(f"    Size: {zip_size_mb:.2f} MB")
        print(f"    Path: {zip_path}")

        # Size warning
        if zip_size_mb > 50:
            print(f"\n[!] WARNING: ZIP size is {zip_size_mb:.1f}MB")
            print(f"    AI Arena typically recommends under 50MB")

        return zip_path

    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        print("\n[OK] Temporary files cleaned")

    def _verify_package(self, zip_path: Path):
        """Verify ZIP package contents"""
        print("\n[*] Verifying package...")

        with zipfile.ZipFile(zip_path, 'r') as zipf:
            file_list = zipf.namelist()

            # Check critical files
            print("    Critical files:")
            critical_files = ['run.py', 'wicked_zerg_bot_pro.py', 'config.py', 'zerg_net.py']
            for cfile in critical_files:
                if cfile in file_list:
                    print(f"      [OK] {cfile}")
                else:
                    print(f"      [!] {cfile} MISSING!")

            # Check model
            model_found = any('models/zerg_net_model.pt' in f for f in file_list)
            if model_found:
                print(f"      [OK] models/zerg_net_model.pt")
            else:
                print(f"      [!] Model file missing (untrained)")

            # Check for unwanted files
            print("\n    Unwanted files check:")
            unwanted_patterns = ['parallel_train', 'main_integrated', '__pycache__',
                               'upload_to_aiarena', 'package_for_aiarena', '.backup']
            found_unwanted = False
            for pattern in unwanted_patterns:
                unwanted = [f for f in file_list if pattern in f]
                if unwanted:
                    found_unwanted = True
                    print(f"      [!] {pattern}: {len(unwanted)} found")

            if not found_unwanted:
                print(f"      [OK] Clean package (no unwanted files)")

            # Statistics
            py_files = [f for f in file_list if f.endswith('.py')]
            pt_files = [f for f in file_list if f.endswith('.pt')]

            print(f"\n    Package statistics:")
            print(f"      Total files: {len(file_list)}")
            print(f"      Python files: {len(py_files)}")
            print(f"      Model files: {len(pt_files)}")

        print("[OK] Verification complete")

    def package(self):
        """Complete packaging process"""
        print("\n" + "="*70)
        print("[*] AI ARENA PACKAGING - WICKED ZERG")
        print("="*70)

        try:
            # 1. Validation
            if not self.validate_project():
                print("\n[!] Packaging failed: validation error")
                return None

            # 2. Create structure
            self.create_package_structure()

            # 3. Create ZIP
            zip_path = self.create_zip()

            # 4. Verify
            self._verify_package(zip_path)

            # 5. Cleanup
            self.cleanup()

            # 6. Summary
            print("\n" + "="*70)
            print("[OK] PACKAGING COMPLETE!")
            print("="*70)
            print(f"\n[*] Submission file: {zip_path.name}")
            print(f"    Location: {zip_path}")
            print(f"\n[*] Next steps:")
            print(f"    1. Verify ZIP contents")
            print(f"    2. Upload to https://aiarena.net")
            print(f"    3. Monitor first match results")
            print("\n[OK] Ready for AI Arena upload!")

            return zip_path

        except Exception as e:
            print(f"\n[!] Packaging error: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()
            return None


def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Arena packaging tool")
    parser.add_argument("--include-checkpoints", action="store_true",
                       help="Include checkpoint files")
    parser.add_argument("--project-root", type=str,
                       help="Project root path (default: current directory)")

    args = parser.parse_args()

    project_root = Path(args.project_root) if args.project_root else None

    packager = AIArenaPackager(
        project_root=project_root,
        include_checkpoints=args.include_checkpoints
    )

    packager.package()


if __name__ == "__main__":
    main()
