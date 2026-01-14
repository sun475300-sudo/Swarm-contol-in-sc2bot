#!/usr/bin/env python3
"""
Zerg Data Pipeline - Step 2: Replay Lifecycle Manager

Purpose: ZIP files -> Zerg filtering -> Training folder batch -> Auto cleanup

Pipeline:
  DOWNLOAD (ZIP)
    |
  EXTRACT & FILTER (Zerg only)
    |
  TRAINING SOURCE
    |
  TRAIN (Learning)
    |
  CLEANUP & ARCHIVE (Organize)

Path Configuration:
  1. DOWNLOAD_DIR: ZIP file location (usually C:\\Users\\[USER]\\Downloads)
  2. TRAINING_SOURCE_DIR: D:\\replay_folder\\replays (training input)
  3. BOT_OUTPUT_DIR: auto-detected from local_training\\replays (training output)

Usage:
  python replay_lifecycle_manager.py --extract    # Extract Zerg replays from ZIP
  python replay_lifecycle_manager.py --cleanup    # Cleanup after training
  python replay_lifecycle_manager.py --full       # Full cycle
"""

import json
import shutil
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict
import argparse

# ==================== ?   ====================
# ?? : local_training ?¢¥ local_training  ?? ?¨ö

from pathlib import Path as _Path

def _find_training_folder():
    """Auto-detect training folder (local_training or legacy)"""
    base = _Path(__file__).parent.parent
    
    # English name (new, priority)
    new_name = base / "local_training"
    if new_name.exists() and new_name.is_dir():
        return new_name
    
    # Fallback: search for any training-related folder
    try:
        for item in base.iterdir():
            if item.is_dir() and "training" in item.name.lower():
                return item
    except:
        pass
    
    # Default (fallback)
    return new_name

TRAINING_FOLDER = _find_training_folder()

# 1. ZIP file download location
DOWNLOAD_DIR = Path(r"C:\Users\sun47\Downloads")

# 2. Training source (ZIP -> Zerg filter -> moved here)
TRAINING_SOURCE_DIR = Path(r"D\replays\replays")

# 3. Bot training output (auto-detected)
BOT_OUTPUT_DIR = TRAINING_FOLDER / "replays"

# 4. Archive (stores processed files)
ARCHIVE_DIR = Path(r"D:\?¡Æ¡¾??¡¦??replay_archive")

# ========================================================================

# Zerg pro players filter (S-Tier priority)
TARGET_ZERGS = [
    # Korea
    "serral", "dark", "reynor", "solar", "soo", "life",
    "ragnarok", "shin", "drg", "dongraegu", "armani", "curious",
    "elazer", "lambo", "scarlett", "nerchio", "bly", "cham",
    # Europe
    "rogue", "stephano", "snute", "xiagu", "lowko",
    # Other Zergs
    "soulkey", "byul", "losira", "krakow",
]

class ReplayLifecycleManager:
    """Replay lifecycle management"""

    def __init__(self):
        self.stats = {
            "extracted": 0,
            "filtered": 0,
            "deleted": 0,
            "moved": 0,
            "total_size_mb": 0,
        }
        self.log_dir = Path(__file__).parent / "logs"
        self.log_dir.mkdir(exist_ok=True)

    def extract_and_filter_zips(self, dry_run: bool = False) -> Tuple[int, int]:
        """
        ?¢¯??  ZIP  ??  ?¡¤?¢¬ 
        
        Returns:
            (_?¡¤_, ??__?¡¤_)
        """
        print(f"\n{'='*80}")
        print("STEP 1: EXTRACT & FILTER ZIPS")
        print(f"{'='*80}\n")

        print(f"? DOWNLOAD  ??: {DOWNLOAD_DIR}")
        TRAINING_SOURCE_DIR.mkdir(parents=True, exist_ok=True)

        zip_files = sorted(DOWNLOAD_DIR.glob("*.zip"))
        if not zip_files:
            print(f"??  ZIP  ??  ?¢¥: {DOWNLOAD_DIR}\n")
            print("?  ?¢ç?¨ù:")
            print(f"   1. {DOWNLOAD_DIR}  ?¢¥?¡Æ?")
            print(f"   2. ZIP  ?¢¥?¡Æ?")
            print(f"   3. ?¢¬ .zip ?¢ç?¡Æ ?¢¥?¡Æ?\n")
            return 0, 0

        print(f"? {len(zip_files)} ZIP  ©¬¡Æ\n")

        total_extracted = 0
        total_filtered = 0

        for zip_idx, zip_path in enumerate(zip_files, 1):
            print(f"[{zip_idx}/{len(zip_files)}] ? {zip_path.name}")

            try:
                with zipfile.ZipFile(zip_path, "r") as z:
                    all_files = [f for f in z.namelist() if f.endswith(".SC2Replay")]
                    print(f"         {len(all_files)} ?¡¤ ©¬¡Æ")

                    for file_in_zip in all_files:
                        fname_lower = Path(file_in_zip).name.lower()
                        total_extracted += 1

                        #  ?¡Æ?¢¬ ?¢ç
                        is_zerg_pro = any(zname in fname_lower for zname in TARGET_ZERGS)

                        # ©¬¡Æ : ?¢¬ Zerg, ZvT, ZvP, ZvZ  ???¨ú ?¢¥?¡Æ?
                        has_zerg_tag = any(
                            tag in fname_lower
                            for tag in ["zerg", "zvt", "zvp", "zvz", "z_", "_z", "zergv"]
                        )

                        is_target = is_zerg_pro or has_zerg_tag

                        if is_target:
                            # ©¬¨¬   ?¢¬ ?¡©
                            new_name = Path(file_in_zip).name.replace(" ", "_")
                            target_path = TRAINING_SOURCE_DIR / new_name

                            if not target_path.exists():
                                if not dry_run:
                                    with z.open(file_in_zip) as source:
                                        target_path.write_bytes(source.read())
                                    self.stats["total_size_mb"] += target_path.stat().st_size / (1024 * 1024)
                                
                                total_filtered += 1
                                print(f"        ? {new_name[:60]}")
                            else:
                                print(f"        ??  (already exists) {new_name[:60]}")

            except zipfile.BadZipFile:
                print(f"        ? ?? ZIP ")
            except Exception as e:
                print(f"        ? : {e}")

        self.stats["extracted"] = total_extracted
        self.stats["filtered"] = total_filtered

        print(f"\n{''*80}")
        print(f"?  ?¡¤:")
        print(f"   ?  ?¡¤: {total_extracted}")
        print(f"   ?  ??: {total_filtered}")
        print(f"   ?  ?¢®: {TRAINING_SOURCE_DIR}")
        print(f"   ? ?¨ù ??: {self.stats['total_size_mb']:.1f} MB")

        if dry_run:
            print(f"   (DRY RUN -    )")

        return total_extracted, total_filtered

    def cleanup_after_training(self, dry_run: bool = False) -> Dict:
        """
        ¨¡¡¤  ?¡¤ :
        1.   ?¡¤  BOT_OUTPUT_DIR ??
        2.   ?¡¤  archive ??
        """
        print(f"\n{'='*80}")
        print("STEP 2: CLEANUP AFTER TRAINING")
        print(f"{'='*80}\n")

        BOT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

        moved_bot_replays = 0
        moved_pro_replays = 0
        deleted_replays = 0

        print(f"? ¨¡¡¤  ??: {TRAINING_SOURCE_DIR}")

        if not TRAINING_SOURCE_DIR.exists():
            print(f"??  ¨¡¡¤  ?¢¥: {TRAINING_SOURCE_DIR}\n")
            return self.stats

        replays = list(TRAINING_SOURCE_DIR.glob("*.SC2Replay"))
        if not replays:
            print(f"??  ?¡¤?¡Æ ?¢¥.\n")
            return self.stats

        print(f"? {len(replays)} ?¡¤ ?©ø \n")

        # CRITICAL: Load learning tracking from multiple sources for hard requirement enforcement
        learning_counts = {}
        tracker = None
        status_manager = None
        
        try:
            # Try to import and use ReplayLearningTracker
            import sys
            training_scripts_path = TRAINING_FOLDER / "scripts"
            if training_scripts_path.exists():
                sys.path.insert(0, str(training_scripts_path))
                try:
                    from replay_learning_manager import ReplayLearningTracker
                    from learning_status_manager import LearningStatusManager
                    
                    tracking_file = TRAINING_SOURCE_DIR / ".learning_tracking.json"
                    status_file = TRAINING_SOURCE_DIR / "learning_status.json"
                    
                    # Load both trackers for redundancy
                    if tracking_file.exists():
                        tracker = ReplayLearningTracker(tracking_file, min_iterations=5)
                    
                    if status_file.exists():
                        status_manager = LearningStatusManager(status_file, min_iterations=5)
                    
                    # Get learning counts for all replays (use status_manager if available, fallback to tracker)
                    for rep in replays:
                        count = 0
                        if status_manager:
                            count = status_manager.get_learning_count(rep)
                        elif tracker:
                            count = tracker.get_learning_count(rep)
                        
                        replay_hash = hashlib.md5(f"{rep.name}_{rep.stat().st_size}_{rep.stat().st_mtime}".encode()).hexdigest()
                        learning_counts[replay_hash] = count
                except ImportError as e:
                    print(f"[WARNING] Learning tracking modules not available: {e}")
        except Exception as e:
            print(f"[WARNING] Could not load learning tracker: {e}")

        MIN_LEARNING_ITERATIONS = 5
        
        for rep in replays:
            fname = rep.name.lower()
            
            # CRITICAL: Check learning count before any move/delete operation
            # This is a hard requirement - files with < 5 learning iterations MUST NOT be moved/deleted
            learning_count = 0
            can_move = False
            
            try:
                # Priority 1: Use status_manager (most reliable - hard requirement enforcement)
                if status_manager:
                    learning_count = status_manager.get_learning_count(rep)
                    can_move = status_manager.can_move_or_delete(rep)
                    if not can_move:
                        print(f"  [SKIP] {rep.name[:50]} - Insufficient learning: {learning_count}/{MIN_LEARNING_ITERATIONS} (NOT MOVED/DELETED)")
                        print(f"         ??  CRITICAL: Hard requirement - This file will NOT be moved/deleted until it reaches {MIN_LEARNING_ITERATIONS} iterations")
                        continue
                # Priority 2: Use tracker
                elif tracker:
                    learning_count = tracker.get_learning_count(rep)
                    can_move = tracker.is_completed(rep)
                # Priority 3: Fallback to loaded counts
                else:
                    replay_hash = hashlib.md5(f"{rep.name}_{rep.stat().st_size}_{rep.stat().st_mtime}".encode()).hexdigest()
                    learning_count = learning_counts.get(replay_hash, 0)
                    can_move = learning_count >= MIN_LEARNING_ITERATIONS
            except Exception as e:
                learning_count = 0
                can_move = False
                print(f"  [WARNING] Could not get learning count for {rep.name}: {e}")
            
            # CRITICAL: Hard requirement check - NEVER move/delete files with < 5 iterations
            if not can_move or learning_count < MIN_LEARNING_ITERATIONS:
                print(f"  [SKIP] {rep.name[:50]} - Insufficient learning: {learning_count}/{MIN_LEARNING_ITERATIONS} (NOT MOVED/DELETED)")
                print(f"         ??  CRITICAL: Hard requirement - This file will NOT be moved/deleted until it reaches {MIN_LEARNING_ITERATIONS} iterations")
                continue

            # 1. Bot replays -> BOT OUTPUT
            if any(bot_marker in fname for bot_marker in ["wickedzerg", "dark_zerg", "integrated"]):
                dest = BOT_OUTPUT_DIR / rep.name
                if not dry_run:
                    shutil.move(str(rep), str(dest))
                moved_bot_replays += 1
                print(f"  [MOVE] BOT OUTPUT: {rep.name[:50]} (learning: {learning_count}/{MIN_LEARNING_ITERATIONS})")

            # 2. Pro replays (with sufficient learning) -> archive
            elif any(zname in fname for zname in TARGET_ZERGS):
                dest = ARCHIVE_DIR / rep.name
                if not dry_run:
                    shutil.move(str(rep), str(dest))
                moved_pro_replays += 1
                print(f"  [ARCHIVE] {rep.name[:50]} (learning: {learning_count}/{MIN_LEARNING_ITERATIONS})")

            # 3. Unknown replays (but with sufficient learning)
            else:
                print(f"  [UNKNOWN] {rep.name[:50]} (learning: {learning_count}/{MIN_LEARNING_ITERATIONS})")

        self.stats["moved"] = moved_bot_replays + moved_pro_replays
        self.stats["deleted"] = moved_pro_replays  # ???¨¬ = 

        print(f"\n{''*80}")
        print(f"?  ?¡¤:")
        print(f"   ?  ?¡¤ ??: {moved_bot_replays}  {BOT_OUTPUT_DIR}")
        print(f"   ?  ?¡¤ ??: {moved_pro_replays}  {ARCHIVE_DIR}")

        if dry_run:
            print(f"   (DRY RUN -   ?? )")

        return self.stats

    def validate_replays(self) -> Dict:
        """
        ?¡¤  (sc2reader ,  ?¨¬???)
        """
        print(f"\n{'='*80}")
        print("STEP 3: VALIDATE REPLAYS")
        print(f"{'='*80}\n")

        try:
            import sc2reader
            HAS_SC2READER = True
        except ImportError:
            HAS_SC2READER = False
            print("??  sc2reader  (pip install sc2reader)")
            print("   ?¨¬? ?¢¥?¢¥.\n")

        validation_stats = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "errors": [],
        }

        replays = list(TRAINING_SOURCE_DIR.glob("*.SC2Replay"))
        if not replays:
            print(f"??  ?¡¤?¡Æ ?¢¥.\n")
            return validation_stats

        print(f"? {len(replays)} ?¡¤  \n")

        for i, rep in enumerate(replays, 1):
            validation_stats["total"] += 1
            valid = True
            error = None

            # ?¨¬???
            try:
                if rep.stat().st_size < 10_000:  # 10KB ?¢¬
                    valid = False
                    error = " ?©ö  (<10KB)"

                # sc2reader 
                if HAS_SC2READER and valid:
                    try:
                        replay = sc2reader.load_replay(str(rep), load_map=False)
                        if not replay:
                            valid = False
                            error = "sc2reader ?? "
                    except Exception as e:
                        valid = False
                        error = str(e)[:50]

            except Exception as e:
                valid = False
                error = str(e)[:50]

            if valid:
                validation_stats["valid"] += 1
                status = "?"
            else:
                validation_stats["invalid"] += 1
                validation_stats["errors"].append(rep.name)
                status = "?"

            if i % 50 == 0 or not valid:
                msg = f"[{i}/{len(replays)}] {status} {rep.name[:50]}"
                if error:
                    msg += f" ({error})"
                print(msg)

        print(f"\n{''*80}")
        print(f"?  ?¡¤:")
        print(f"   ? : {validation_stats['total']}")
        print(f"   ? ?¢¯: {validation_stats['valid']}")
        print(f"   ? ?¢¯: {validation_stats['invalid']}")

        if validation_stats["errors"]:
            print(f"\n??  ?¢¯ :")
            for err in validation_stats["errors"][:5]:
                print(f"   ? {err}")
            if len(validation_stats["errors"]) > 5:
                print(f"   ...  {len(validation_stats['errors']) - 5}")

        return validation_stats

    def generate_report(self, validation_stats: Dict = None):
        """ """
        print(f"\n{'='*80}")
        print("STEP 4: GENERATE REPORT")
        print(f"{'='*80}\n")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.log_dir / f"lifecycle_report_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "validation": validation_stats or {},
            "paths": {
                "download": str(DOWNLOAD_DIR),
                "training_source": str(TRAINING_SOURCE_DIR),
                "bot_output": str(BOT_OUTPUT_DIR),
                "archive": str(ARCHIVE_DIR),
            }
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"?  : {report_file}")
        print(f"\n? :")
        print(f"   ? : {self.stats['extracted']}")
        print(f"   ? ??: {self.stats['filtered']}")
        print(f"   ? ??: {self.stats['moved']}")
        print(f"   ? ??: {self.stats['total_size_mb']:.1f} MB")

def main():
    parser = argparse.ArgumentParser(
        description="Zerg Data Pipeline - Step 2: Replay Lifecycle Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python replay_lifecycle_manager.py --extract     # ZIP  ?¡¤ 
  python replay_lifecycle_manager.py --cleanup     # ¨¡¡¤  
  python replay_lifecycle_manager.py --validate    # ?¡¤ 
  python replay_lifecycle_manager.py --full        # ?¨ù ??
  python replay_lifecycle_manager.py --dry-run     #   ?¢¬
        """
    )

    parser.add_argument("--extract", action="store_true", help="ZIP ")
    parser.add_argument("--cleanup", action="store_true", help="¨¡¡¤  ")
    parser.add_argument("--validate", action="store_true", help="")
    parser.add_argument("--full", action="store_true", help="?¨ù ?? (extract + cleanup)")
    parser.add_argument("--dry-run", action="store_true", help="  ?¢¬ (   )")

    args = parser.parse_args()

    # ?¨¬?: --extract 
    if not any([args.extract, args.cleanup, args.validate, args.full]):
        args.extract = True

    manager = ReplayLifecycleManager()

    print(f"\n{'='*80}")
    print("? Zerg Data Pipeline - Step 2: Replay Lifecycle Manager")
    print(f"{'='*80}")

    validation_stats = None

    if args.extract or args.full:
        manager.extract_and_filter_zips(dry_run=args.dry_run)

    if args.cleanup or args.full:
        manager.cleanup_after_training(dry_run=args.dry_run)

    if args.validate or args.full:
        validation_stats = manager.validate_replays()

    manager.generate_report(validation_stats)

    print(f"\n{'='*80}")
    print("? Step 2 COMPLETE:  ¨¡¡¤ ?¨ù")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()


