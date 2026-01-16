#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Arena Deployment Preparation Tool

Optimizes and prepares source code for AI Arena deployment:
1. Error checking and fixing
2. Code optimization according to AI Arena rules
3. Package creation for deployment
4. Validation and testing
"""

import ast
import os
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import json
import subprocess

# Encoding setup
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DEPLOY_PATH = Path("D:/arena_deployment")


class ArenaDeploymentPreparer:
    """AI Arena deployment preparation system"""

    # Essential files for AI Arena submission
    ESSENTIAL_FILES = [
        # Core entry point
        "run.py",
        # Main bot class
        "wicked_zerg_bot_pro.py",
        # Configuration
        "config.py",
        # Neural network
        "zerg_net.py",
        # Game logic modules (required)
        "combat_manager.py",
        "economy_manager.py",
        "production_manager.py",
        "micro_controller.py",
        "scouting_system.py",
        "intel_manager.py",
        "queen_manager.py",
        "telemetry_logger.py",
        "rogue_tactics_manager.py",
        "unit_factory.py",
        # Dependencies
        "requirements.txt",
    ]

    # Optional files (included if they exist)
    OPTIONAL_FILES = [
        "combat_tactics.py",
        "production_resilience.py",
        "personality_manager.py",
        "strategy_analyzer.py",
        "spell_unit_manager.py",
        "map_manager.py",
        "chat_manager.py",
    ]

    # Excluded patterns (AI Arena doesn't need)
    EXCLUDE_PATTERNS = [
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '*.bak',
        '*.backup',
        '*.tmp',
        '*.log',
        '.git',
        '.venv',
        'venv',
        'node_modules',
        'training_data',
        'replays',
        'logs',
        'stats',
        'monitoring',
        'tools',
        'bat',
        'docs',
        'backup_before_refactoring',
        'backup_before_refactoring',
        '*.md',  # Documentation files (except README.md)
    ]

    def __init__(self, project_root: Path = None, deploy_path: Path = None):
        self.project_root = project_root or PROJECT_ROOT
        self.deploy_path = deploy_path or DEFAULT_DEPLOY_PATH
        self.deploy_path.mkdir(parents=True, exist_ok=True)

        self.temp_dir = self.deploy_path / "temp_package"
        self.errors = []
        self.warnings = []

        print(f"[*] AI Arena Deployment Preparer initialized")
        print(f"    Project root: {self.project_root}")
        print(f"    Deploy path: {self.deploy_path}")

    def check_syntax_errors(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Check for syntax errors in Python file"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            try:
                ast.parse(content, filename=str(file_path))
            except SyntaxError as e:
                errors.append(f"SyntaxError: {e.msg} at line {e.lineno}")
            except IndentationError as e:
                errors.append(f"IndentationError: {e.msg} at line {e.lineno}")
        except Exception as e:
            errors.append(f"File read error: {e}")

        return len(errors) == 0, errors

    def check_import_errors(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Check for import errors (basic check)"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            # Check for problematic imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and 'training' in node.module.lower():
                        # Training imports might not be available in Arena
                        if 'run_with_training' in node.module or 'main_integrated' in node.module:
                            errors.append(f"Training import found: {node.module}")
        except Exception:
            pass  # Syntax errors already checked

        return len(errors) == 0, errors

    def fix_common_errors(self, file_path: Path) -> bool:
        """Fix common errors in Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            lines = content.splitlines()
            fixed_lines = []
            changed = False

            for i, line in enumerate(lines, 1):
                # Fix common indentation issues
                stripped = line.lstrip()

                # Skip empty lines and comments
                if not stripped or stripped.startswith('#'):
                    fixed_lines.append(line)
                    continue

                # Ensure consistent 4-space indentation
                current_indent = len(line) - len(stripped)
                if current_indent % 4 != 0 and current_indent > 0:
                    # Fix to nearest 4-space multiple
                    new_indent = (current_indent // 4) * 4
                    fixed_lines.append(' ' * new_indent + stripped)
                    changed = True
                else:
                    fixed_lines.append(line)

            if changed:
                with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write('\n'.join(fixed_lines) + '\n')
                return True

            return False
        except Exception as e:
            print(f"[WARNING] Could not fix {file_path.name}: {e}")
            return False

    def validate_all_files(self) -> Dict:
        """Validate all essential files"""
        print("\n[*] Validating all files...")

        results = {
            "total": 0,
            "syntax_errors": 0,
            "import_warnings": 0,
            "files_fixed": 0,
            "missing_files": [],
        }

        # Check essential files
        for file_name in self.ESSENTIAL_FILES:
            file_path = self.project_root / file_name
            results["total"] += 1

            if not file_path.exists():
                results["missing_files"].append(file_name)
                self.errors.append(f"Missing essential file: {file_name}")
                print(f"  [!] {file_name} - MISSING")
                continue

            # Skip non-Python files (e.g., requirements.txt)
            if not file_name.endswith('.py'):
                print(f"  [OK] {file_name} - Skipped (not Python file)")
                continue

            # Check syntax
            syntax_ok, syntax_errors = self.check_syntax_errors(file_path)
            if not syntax_ok:
                results["syntax_errors"] += 1
                self.errors.extend([f"{file_name}: {e}" for e in syntax_errors])
                print(f"  [!] {file_name} - Syntax errors: {syntax_errors}")

                # Try to fix
                if self.fix_common_errors(file_path):
                    results["files_fixed"] += 1
                    print(f"      [FIXED] Attempted to fix {file_name}")
            else:
                print(f"  [OK] {file_name} - Syntax OK")

            # Check imports
            import_ok, import_warnings = self.check_import_errors(file_path)
            if not import_ok:
                results["import_warnings"] += 1
                self.warnings.extend([f"{file_name}: {w}" for w in import_warnings])
                print(f"  [~] {file_name} - Import warnings: {import_warnings}")

        return results

    def create_clean_package(self) -> Path:
        """Create clean package for AI Arena"""
        print("\n[*] Creating clean package...")

        # Clean temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Copy essential files
        print("    - Copying essential files...")
        for file_name in self.ESSENTIAL_FILES:
            src = self.project_root / file_name
            if src.exists():
                dst = self.temp_dir / src.name
                shutil.copy2(src, dst)
                print(f"      [OK] {file_name}")

        # Copy optional files
        print("    - Copying optional files...")
        for file_name in self.OPTIONAL_FILES:
            src = self.project_root / file_name
            if src.exists():
                dst = self.temp_dir / src.name
                shutil.copy2(src, dst)
                print(f"      [OK] {file_name} (optional)")

        # Copy required directories
        required_dirs = ['combat', 'core', 'utils']
        for dir_name in required_dirs:
            src_dir = self.project_root / dir_name
            if src_dir.exists() and src_dir.is_dir():
                dst_dir = self.temp_dir / dir_name
                shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns('*.pyc', '__pycache__', '*.bak'))
                print(f"      [OK] {dir_name}/")

        # Copy models (latest only)
        print("    - Copying model files...")
        models_src = self.project_root / "models"
        if models_src.exists():
            models_dst = self.temp_dir / "models"
            models_dst.mkdir(exist_ok=True)

            # Find latest model
            model_files = list(models_src.glob("*.pt"))
            if model_files:
                latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
                dst_model = models_dst / "zerg_net_model.pt"
                shutil.copy2(latest_model, dst_model)
                print(f"      [OK] models/zerg_net_model.pt")

        # Copy requirements.txt
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            shutil.copy2(req_file, self.temp_dir / "requirements.txt")
            print(f"      [OK] requirements.txt")

        print("[OK] Package structure created")
        return self.temp_dir

    def create_zip_package(self) -> Path:
        """Create ZIP package for deployment"""
        print("\n[*] Creating ZIP package...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"WickedZerg_AIArena_{timestamp}.zip"
        zip_path = self.deploy_path / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.temp_dir):
                # Exclude patterns
                dirs[:] = [d for d in dirs if not any(
                    pattern in d for pattern in ['__pycache__', '.git', '.venv']
                )]

                for file in files:
                    file_path = Path(root) / file

                    # Skip excluded files
                    if any(file.endswith(ext) for ext in ['.pyc', '.pyo', '.bak', '.log']):
                        continue

                    # Relative path for ZIP
                    arcname = file_path.relative_to(self.temp_dir)
                    zipf.write(file_path, arcname)

        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"[OK] ZIP package created: {zip_name} ({zip_size_mb:.2f} MB)")

        return zip_path

    def validate_package(self, package_dir: Path) -> Dict:
        """Validate the created package"""
        print("\n[*] Validating package...")

        validation_results = {
            "run_py_exists": False,
            "bot_class_exists": False,
            "requirements_exists": False,
            "all_essential_files": True,
            "errors": [],
        }

        # Check run.py
        run_py = package_dir / "run.py"
        validation_results["run_py_exists"] = run_py.exists()
        if not run_py.exists():
            validation_results["errors"].append("run.py not found")

        # Check bot class
        bot_py = package_dir / "wicked_zerg_bot_pro.py"
        validation_results["bot_class_exists"] = bot_py.exists()
        if not bot_py.exists():
            validation_results["errors"].append("wicked_zerg_bot_pro.py not found")

        # Check requirements.txt
        req_txt = package_dir / "requirements.txt"
        validation_results["requirements_exists"] = req_txt.exists()
        if not req_txt.exists():
            validation_results["errors"].append("requirements.txt not found")

        # Check all essential files
        for file_name in self.ESSENTIAL_FILES:
            if file_name not in ['run.py', 'wicked_zerg_bot_pro.py', 'requirements.txt']:
                file_path = package_dir / Path(file_name).name
                if not file_path.exists():
                    validation_results["all_essential_files"] = False
                    validation_results["errors"].append(f"{file_name} missing")

        if validation_results["errors"]:
            print("[!] Validation errors:")
            for error in validation_results["errors"]:
                print(f"      - {error}")
        else:
            print("[OK] Package validation passed")

        return validation_results

    def prepare_deployment(self) -> Dict:
        """Complete deployment preparation"""
        print("=" * 70)
        print("AI ARENA DEPLOYMENT PREPARATION")
        print("=" * 70)

        results = {
            "validation": None,
            "package_dir": None,
            "zip_file": None,
            "errors": [],
            "warnings": [],
        }

        # Step 1: Validate all files
        validation_results = self.validate_all_files()
        results["validation"] = validation_results

        if validation_results["missing_files"]:
            print(f"\n[!] Missing {len(validation_results['missing_files'])} essential files")
            results["errors"].extend([f"Missing: {f}" for f in validation_results["missing_files"]])
            return results

        if validation_results["syntax_errors"] > 0:
            print(f"\n[!] Found {validation_results['syntax_errors']} syntax errors")
            if validation_results["files_fixed"] > 0:
                print(f"    [FIXED] {validation_results['files_fixed']} files were auto-fixed")

        # Step 2: Create clean package
        package_dir = self.create_clean_package()
        results["package_dir"] = package_dir

        # Step 3: Validate package
        package_validation = self.validate_package(package_dir)
        if package_validation["errors"]:
            results["errors"].extend(package_validation["errors"])

        # Step 4: Create ZIP
        zip_file = self.create_zip_package()
        results["zip_file"] = zip_file

        # Summary
        print("\n" + "=" * 70)
        print("DEPLOYMENT PREPARATION COMPLETE")
        print("=" * 70)
        print(f"Package directory: {package_dir}")
        print(f"ZIP file: {zip_file}")
        if results["errors"]:
            print(f"\n[!] Errors: {len(results['errors'])}")
            for error in results["errors"]:
                print(f"      - {error}")
        if self.warnings:
            print(f"\n[~] Warnings: {len(self.warnings)}")
        print("=" * 70)

        results["errors"] = self.errors
        results["warnings"] = self.warnings

        return results


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Arena Deployment Preparation Tool")
    parser.add_argument("--deploy-path", type=str, default=None,
                       help=f"Deployment path (default: {DEFAULT_DEPLOY_PATH})")
    parser.add_argument("--skip-validation", action="store_true",
                       help="Skip file validation")

    args = parser.parse_args()

    deploy_path = Path(args.deploy_path) if args.deploy_path else DEFAULT_DEPLOY_PATH

    preparer = ArenaDeploymentPreparer(deploy_path=deploy_path)

    if not args.skip_validation:
        # Validate first
        validation = preparer.validate_all_files()
        if validation["syntax_errors"] > 0 and validation["files_fixed"] == 0:
            print("\n[!] Syntax errors found. Please fix them before deployment.")
            sys.exit(1)

    # Prepare deployment
    results = preparer.prepare_deployment()

    if results["errors"]:
        print("\n[!] Deployment preparation completed with errors.")
        print("    Please review and fix errors before uploading to AI Arena.")
        sys.exit(1)
    else:
        print("\n[OK] Deployment package is ready for AI Arena!")
        print(f"    ZIP file: {results['zip_file']}")
        sys.exit(0)


if __name__ == "__main__":
    main()
