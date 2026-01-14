# -*- coding: utf-8 -*-
"""
Project Cleanup and Organization Script
- Consolidate data files
- Log cleanup
- Remove duplicate folders
- Remove empty directories
"""
import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "node_modules", "models", "replays", "AI_Arena_Updates",
    "AI_Arena_Deploy", "aiarena_submission"
}

class ProjectCleaner:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.stats = {
            "files_moved": 0,
            "folders_deleted": 0,
            "space_freed": 0,
            "errors": []
        }

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def safe_delete(self, path: Path):
        if self.dry_run:
            self.log(f"[DRY-RUN] Will delete: {path}")
            return

        try:
            if path.is_file():
                size = path.stat().st_size
                path.unlink()
                self.stats["space_freed"] += size
                self.log(f"Deleted: {path.name}")
            elif path.is_dir():
                shutil.rmtree(path)
                self.stats["folders_deleted"] += 1
                self.log(f"Removed folder: {path.name}")
        except Exception as e:
            self.stats["errors"].append(f"Delete failed {path}: {e}")
            self.log(f"Error: {e}")

    def safe_move(self, src: Path, dst: Path):
        if self.dry_run:
            self.log(f"[DRY-RUN] Will move: {src} -> {dst}")
            return

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)

            if dst.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dst = dst.with_stem(f"{dst.stem}_{timestamp}")

            shutil.move(str(src), str(dst))
            self.stats["files_moved"] += 1
            self.log(f"Moved: {src.name} -> {dst}")
        except Exception as e:
            self.stats["errors"].append(f"Move failed {src}: {e}")
            self.log(f"Error: {e}")

    def consolidate_data_files(self):
        self.log("\n=== Step 1: Consolidate Data Files ===")

        patterns = [
            "training_stats*.json",
            "pro_players*.json",
            "telemetry*.json",
            "telemetry*.csv",
            "*.csv"
        ]

        for pattern in patterns:
            for file in PROJECT_ROOT.glob(pattern):
                if file.parent == PROJECT_ROOT:
                    dst = DATA_DIR / file.name
                    self.safe_move(file, dst)

    def cleanup_logs(self, keep_count=2):
        self.log(f"\n=== Step 2: Log Cleanup (keep latest {keep_count}) ===")

        if not LOGS_DIR.exists():
            self.log("No logs directory")
            return

        log_files = []
        for f in LOGS_DIR.glob("log_*.txt"):
            try:
                match = re.search(r'log_(\d{8})_(\d{6})', f.name)
                if match:
                    date_str = match.group(1) + match.group(2)
                    timestamp = datetime.strptime(date_str, "%Y%m%d%H%M%S")
                    log_files.append((timestamp, f))
            except:
                continue

        log_files.sort(key=lambda x: x[0], reverse=True)

        for _, log_file in log_files[keep_count:]:
            self.safe_delete(log_file)

        self.log(f"Kept logs: {min(keep_count, len(log_files))}")

    def remove_duplicate_folders(self):
        self.log("\n=== Step 3: Remove Duplicate Folders ===")

        folders_to_remove = [
            PROJECT_ROOT / "AI_Arena_Deploy",
            PROJECT_ROOT / "aiarena_submission"
        ]

        for folder in folders_to_remove:
            if folder.exists():
                self.safe_delete(folder)
            else:
                self.log(f"Folder not found: {folder.name}")

    def remove_empty_folders(self, base_path=None):
        self.log("\n=== Step 4: Remove Empty Folders ===")

        if base_path is None:
            base_path = PROJECT_ROOT

        removed_count = 0
        for root, dirs, files in os.walk(base_path, topdown=False):
            if any(ex in Path(root).parts for ex in EXCLUDE_DIRS):
                continue

            for dirname in dirs:
                dir_path = Path(root) / dirname
                if dir_path.exists() and not any(dir_path.iterdir()):
                    self.safe_delete(dir_path)
                    removed_count += 1

        self.log(f"Removed empty folders: {removed_count}")

    def cleanup_old_archives(self, days=30):
        self.log(f"\n=== Step 5: Cleanup Old Archives (>{days} days) ===")

        archive_dir = PROJECT_ROOT / "AI_Arena_Updates"
        if not archive_dir.exists():
            self.log("No archive directory")
            return

        cutoff_date = datetime.now() - timedelta(days=days)

        for item in archive_dir.iterdir():
            if item.is_dir():
                try:
                    match = re.search(r'(\d{8})', item.name)
                    if match:
                        date_str = match.group(1)
                        folder_date = datetime.strptime(date_str, "%Y%m%d")

                        if folder_date < cutoff_date:
                            self.safe_delete(item)
                except:
                    pass

    def generate_report(self):
        self.log("\n" + "="*50)
        self.log("=== Cleanup Complete ===")
        self.log("="*50)
        self.log(f"Files moved: {self.stats['files_moved']}")
        self.log(f"Folders deleted: {self.stats['folders_deleted']}")
        self.log(f"Space freed: {self.stats['space_freed'] / (1024*1024):.2f} MB")

        if self.stats['errors']:
            self.log(f"\nErrors: {len(self.stats['errors'])}")
            for err in self.stats['errors']:
                self.log(f"  - {err}")

        report_file = DATA_DIR / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "dry_run": self.dry_run,
                "statistics": self.stats
            }, f, indent=2, ensure_ascii=False)

        self.log(f"\nReport saved: {report_file}")

    def run_full_cleanup(self):
        self.log("Starting project cleanup...")

        self.consolidate_data_files()
        self.cleanup_logs(keep_count=2)
        self.remove_duplicate_folders()
        self.cleanup_old_archives(days=30)
        self.remove_empty_folders()

        self.generate_report()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Project Cleanup Tool")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no actual changes")
    parser.add_argument("--keep-logs", type=int, default=2, help="Number of log files to keep")
    args = parser.parse_args()

    cleaner = ProjectCleaner(dry_run=args.dry_run)
    cleaner.run_full_cleanup()


if __name__ == "__main__":
    main()
