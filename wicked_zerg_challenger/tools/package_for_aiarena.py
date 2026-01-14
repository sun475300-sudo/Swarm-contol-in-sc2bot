# -*- coding: utf-8 -*-
"""
================================================================================
                AI Arena Á¦Ãâ¿ë ÆÐÅ°Â¡ ÀÚµ¿È­ (package_for_aiarena.py)
================================================================================

·ÎÄÃ¿¡¼­ ÈÆ·ÃµÈ ¸ðµ¨°ú ¼Ò½ºÄÚµå¸¦ AI Arena Á¦Ãâ¿ë ÆÐÅ°Áö·Î ÀÚµ¿ »ý¼ºÇÕ´Ï´Ù.

±â´É:
    1. ÈÆ·ÃµÈ ¸ðµ¨ °¡ÁßÄ¡(.pt) Æ÷ÇÔ
    2. ÇÊ¼ö ¼Ò½ºÄÚµå ÀÚµ¿ ¼öÁý
    3. arena_deploy/ Æú´õ·Î ÀÚµ¿ º¹»ç
    4. Ã¼Å©¼¶ °ËÁõ (¸ðµ¨ ¼Õ»ó ¹æÁö)

»ç¿ë¹ý:
    python package_for_aiarena.py

Ãâ·Â:
    - arena_deploy/bot_package/ (Á¦Ãâ¿ë ¿ÏÀü ÆÐÅ°Áö)
    - arena_deploy/verification_report.txt (°ËÁõ º¸°í¼­)

================================================================================
"""

import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class PackageBuilder:
    """AI Arena Á¦Ãâ¿ë ÆÐÅ°Áö ºô´õ"""

    # ÇÊ¼ö ¼Ò½ºÄÚµå ÆÄÀÏ (·ÎÁ÷, ¸Å´ÏÀú, ½Å°æ¸Á)
    ESSENTIAL_SOURCES: List[str] = [
        "run.py",                           # ? AI Arena ÁøÀÔÁ¡
        "main_integrated.py",               # ? ·ÎÄÃ ÈÆ·Ã ÁøÀÔÁ¡
        "wicked_zerg_bot_pro.py",          # ? ¸ÞÀÎ º¿ Å¬·¡½º
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

    # ÇÊ¼ö ¸ðµ¨ ÆÄÀÏ (ÈÆ·Ã °¡ÁßÄ¡)
    ESSENTIAL_MODELS: List[str] = [
        "models/zerg_net_model.pt",          # ? ½Å°æ¸Á ¸ðµ¨ (°¡Àå Áß¿ä!)
    ]

    # ÇÊ¼ö µ¥ÀÌÅÍ ÆÄÀÏ
    ESSENTIAL_DATA: List[str] = [
        "data/",                            # ? Ä¿¸®Å§·³ ÈÆ·Ã Åë°è
    ]

    # AI Arena ¹èÆ÷ Æú´õ
    DEPLOY_DIR = Path("arena_deploy")
    PACKAGE_DIR = DEPLOY_DIR / "bot_package"
    BACKUP_DIR = DEPLOY_DIR / "backups"

    def __init__(self, project_root: Optional[Path] = None):
        """
        Args:
            project_root: ÇÁ·ÎÁ§Æ® ·çÆ® °æ·Î (±âº»°ª: ÇöÀç ÆÄÀÏ µð·ºÅä¸®)
        """
        self.project_root = project_root or Path(__file__).parent.absolute()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report: List[str] = []

    def log(self, message: str, level: str = "INFO"):
        """·Î±× ¸Þ½ÃÁö Ãâ·Â ¹× ÀúÀå"""
        formatted = f"[{level}] {message}"
        print(formatted)
        self.report.append(formatted)

    def verify_file_exists(self, file_path: Path) -> bool:
        """ÆÄÀÏ Á¸Àç ¿©ºÎ È®ÀÎ"""
        if file_path.exists():
            self.log(f"? Found: {file_path.name}", "OK")
            return True
        else:
            self.log(f"??  Missing: {file_path.name}", "WARNING")
            return False

    def calculate_checksum(self, file_path: Path) -> str:
        """ÆÄÀÏ Ã¼Å©¼¶ °è»ê (¹«°á¼º °ËÁõ)"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def copy_sources(self) -> bool:
        """ÇÊ¼ö ¼Ò½ºÄÚµå ÆÄÀÏ º¹»ç"""
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
        """ÈÆ·ÃµÈ ¸ðµ¨ °¡ÁßÄ¡ º¹»ç (°¡Àå Áß¿ä!)"""
        self.log("\n? Step 2: Copying trained model weights...")
        success_count = 0

        for model_file in self.ESSENTIAL_MODELS:
            src = self.project_root / model_file
            dst = self.PACKAGE_DIR / model_file

            if self.verify_file_exists(src):
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                
                # Ã¼Å©¼¶ °ËÁõ
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
        """µ¥ÀÌÅÍ ÆÄÀÏ º¹»ç (Ä¿¸®Å§·³ Åë°è µî)"""
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
        """ÆÐÅ°Áö ¸Å´ÏÆä½ºÆ® ÆÄÀÏ »ý¼º (°ËÁõ¿ë)"""
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
                "bot_package/": "AI Arena Á¦Ãâ ÆÐÅ°Áö (½ÇÇà °¡´É)",
                "backups/": "ÀÌÀü ÆÐÅ°Áö ¹é¾÷",
                "verification_report.txt": "°ËÁõ º¸°í¼­",
            }
        }

        # ¸ðµ¨ Ã¼Å©¼¶ ±â·Ï
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
        """AI Arena Á¦Ãâ¿ë README »ý¼º"""
        self.log("\n? Step 5: Creating AI Arena README...")

        readme_content = f"""# Wicked Zerg Challenger - AI Arena Edition

## ÆÐÅ°Áö Á¤º¸
- »ý¼º ½Ã°¢: {self.timestamp}
- º¿ ÀÌ¸§: Wicked Zerg Challenger
- Å¸ÀÔ: StarCraft II Zerg Bot

## Æ÷ÇÔ ÆÄÀÏ
? **¼Ò½ºÄÚµå**: {len(self.ESSENTIAL_SOURCES)}°³ ÆÄÀÏ
? **¸ðµ¨ °¡ÁßÄ¡**: {len(self.ESSENTIAL_MODELS)}°³ ÆÄÀÏ (½Å°æ¸Á ¸ðµ¨ Æ÷ÇÔ)
? **µ¥ÀÌÅÍ**: Ä¿¸®Å§·³ ÈÆ·Ã Åë°è

## Áß¿ä Á¤º¸

### ¸ðµ¨ °¡ÁßÄ¡ (ÈÆ·Ã °á°ú)
ÀÌ ÆÐÅ°Áö¿¡´Â ·ÎÄÃ¿¡¼­ ¼öÃµ ¹øÀÇ ÀÚ±â°­È­ÇÐ½À(RL)À¸·Î ÈÆ·ÃµÈ ½Å°æ¸Á ¸ðµ¨ÀÌ Æ÷ÇÔµÇ¾î ÀÖ½À´Ï´Ù.
- ÆÄÀÏ: `models/zerg_net_model.pt`
- Å©±â: È®ÀÎ ÇÊ¿ä
- »óÅÂ: ? Æ÷ÇÔµÊ

### Á¦Ãâ ¹æ¹ý
1. `bot_package/` Æú´õ ÀüÃ¼¸¦ AI Arena À¥»çÀÌÆ®¿¡ ¾÷·Îµå
2. `run.py`°¡ ÀÚµ¿À¸·Î ÁøÀÔÁ¡À¸·Î ¼³Á¤µÊ
3. AI Arena ¼­¹ö°¡ `python run.py` ½ÇÇà

### ÁÖÀÇ»çÇ×
?? ÀÌ ÆÐÅ°Áö´Â **Windows ·ÎÄÃ È¯°æ¿¡¼­ »ý¼º**µÇ¾ú½À´Ï´Ù.
AI Arena Á¦Ãâ Àü¿¡ ´ÙÀ½À» È®ÀÎÇÏ¼¼¿ä:
- run.pyÀÇ SC2 °æ·Î°¡ Linux/¸ÖÆ¼ÇÃ·§Æû È¯°æ¿¡ È£È¯µÇ´ÂÁö È®ÀÎ
- Àý´ë °æ·Î ´ë½Å »ó´ë °æ·Î »ç¿ë È®ÀÎ
- ÆÄÀÌ½ã ÀÇÁ¸¼ºÀÌ requirements.txt¿¡ ¸í½ÃµÇ¾î ÀÖ´ÂÁö È®ÀÎ

### ÈÆ·Ã Åë°è
- Ä¿¸®Å§·³ ³­ÀÌµµ: VeryEasy ¡æ CheatInsane
- ÈÆ·Ã ¸ðµå: ÀÚ±â°­È­ÇÐ½À(REINFORCE) + ÁöµµÇÐ½À(Supervised)
- ÃÖÀûÈ­: ´ÙÁß ÀÎ½ºÅÏ½º º´·Ä ÈÆ·Ã

---
Generated by package_for_aiarena.py
"""

        readme_file = self.DEPLOY_DIR / "README_AI_ARENA.md"
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)

        self.log(f"? README created: {readme_file.name}")

    def backup_previous_package(self):
        """ÀÌÀü ÆÐÅ°Áö ¹é¾÷"""
        if self.PACKAGE_DIR.exists():
            self.log("\n? Backing up previous package...")
            self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            
            backup_name = f"bot_package_backup_{self.timestamp}"
            backup_path = self.BACKUP_DIR / backup_name
            
            shutil.move(str(self.PACKAGE_DIR), str(backup_path))
            self.log(f"? Backup created: {backup_name}")

    def build(self) -> bool:
        """ÀüÃ¼ ÆÐÅ°Â¡ ÇÁ·Î¼¼½º ½ÇÇà"""
        self.log("=" * 80)
        self.log("? Wicked Zerg Challenger - AI Arena Packager")
        self.log("=" * 80)

        try:
            # ¹èÆ÷ µð·ºÅä¸® ÃÊ±âÈ­
            self.DEPLOY_DIR.mkdir(exist_ok=True)
            
            # ÀÌÀü ÆÐÅ°Áö ¹é¾÷
            if self.PACKAGE_DIR.exists():
                self.backup_previous_package()
            
            self.PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

            # Step 1: ¼Ò½ºÄÚµå º¹»ç
            sources_ok = self.copy_sources()

            # Step 2: ¸ðµ¨ °¡ÁßÄ¡ º¹»ç (°¡Àå Áß¿ä!)
            models_ok = self.copy_models()

            # Step 3: µ¥ÀÌÅÍ º¹»ç
            data_ok = self.copy_data()

            # Step 4: ¸Å´ÏÆä½ºÆ® »ý¼º
            self.create_manifest()

            # Step 5: README »ý¼º
            self.create_readme()

            # ÃÖÁ¾ º¸°í¼­ »ý¼º
            self.save_report()

            # ÃÖÁ¾ °á°ú
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
        """°ËÁõ º¸°í¼­ ÀúÀå"""
        report_file = self.DEPLOY_DIR / "verification_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.report))
        self.log(f"\n? Verification report saved: {report_file.name}")


def main():
    """¸ÞÀÎ ÁøÀÔÁ¡"""
    builder = PackageBuilder()
    success = builder.build()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
