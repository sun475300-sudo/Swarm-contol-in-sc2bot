# -*- coding: utf-8 -*-
"""
Drive File Auto Classification Script
- Classify files by extension across drives
- Organize by category: coding, documents, games, etc.
- Date-based folder structure
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
import json

# Classification rules by file extension
CLASSIFICATION_RULES = {
    "Coding": {
        "extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".cs",
                      ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".sh", ".ps1", ".bat"],
        "target_dir": "Coding"
    },
    "Documents": {
        "extensions": [".md", ".txt", ".json", ".xml", ".yaml", ".yml", ".toml",
                      ".html", ".css", ".scss", ".sql", ".csv", ".ini", ".cfg"],
        "target_dir": "Documents"
    },
    "GameReplays": {
        "extensions": [".SC2Replay"],
        "target_dir": "replays"  # Project replays folder
    },
    "Images": {
        "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp"],
        "target_dir": "Images"
    },
    "Archives": {
        "extensions": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
        "target_dir": "Archives"
    }
}

# Directories to exclude from search
EXCLUDE_DIRS = {
    "Windows", "Program Files", "Program Files (x86)", "ProgramData",
    "$Recycle.Bin", "System Volume Information", "$WinREinstall",
    "WindowsApps", "AppData", "node_modules", ".git", ".venv", "venv",
    "__pycache__", "dist", "build", "target"
}

# System file extensions to exclude
EXCLUDE_EXTENSIONS = {
    ".exe", ".dll", ".sys", ".tmp", ".temp", ".log", ".bak"
}

class DriveClassifier:
    def __init__(self, drives=["C:", "D:"], target_base="D:/wicked_zerg_challenger/data", dry_run=False):
        self.drives = drives
        self.target_base = Path(target_base)
        self.dry_run = dry_run
        self.stats = {
            "scanned": 0,
            "classified": 0,
            "skipped": 0,
            "errors": []
        }

    def log(self, message):
        """Logging with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def should_skip(self, path: Path) -> bool:
        """Check if path should be skipped"""
        # Check excluded directories
        if any(exclude in path.parts for exclude in EXCLUDE_DIRS):
            return True

        # Check excluded extensions
        if path.suffix.lower() in EXCLUDE_EXTENSIONS:
            return True

        # Skip hidden files/folders
        try:
            if path.name.startswith('.') and path.name not in ['.env', '.gitignore']:
                return True
        except:
            return True

        return False

    def get_category(self, file_path: Path) -> str:
        """Determine file category"""
        ext = file_path.suffix.lower()

        for category, rules in CLASSIFICATION_RULES.items():
            if ext in rules["extensions"]:
                return category

        return None

    def classify_file(self, file_path: Path):
        """Classify and move file"""
        category = self.get_category(file_path)

        if not category:
            return False

        try:
            # Build target path
            target_subdir = CLASSIFICATION_RULES[category]["target_dir"]

            # Game replays go to project root replays folder
            if category == "GameReplays":
                target_dir = Path("D:/wicked_zerg_challenger") / target_subdir
            else:
                # Date-based folder
                date_folder = datetime.now().strftime("%Y%m")
                target_dir = self.target_base / target_subdir / date_folder

            target_path = target_dir / file_path.name

            # Handle duplicate files
            if target_path.exists():
                # Skip if same size (duplicate)
                if target_path.stat().st_size == file_path.stat().st_size:
                    self.log(f"Skip duplicate: {file_path.name}")
                    self.stats["skipped"] += 1
                    return False

                # Add timestamp if different size
                timestamp = datetime.now().strftime("%H%M%S")
                target_path = target_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"

            # Execute move
            if self.dry_run:
                self.log(f"[DRY-RUN] {file_path} -> {target_path}")
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(target_path))
                self.log(f"OK {category}: {file_path.name} -> {target_dir.name}")

            self.stats["classified"] += 1
            return True

        except Exception as e:
            self.stats["errors"].append(f"{file_path}: {e}")
            self.log(f"Error: {file_path.name} - {e}")
            return False

    def scan_and_classify(self, max_depth=3):
        """Scan drives and classify files"""
        self.log("Starting drive scan...")

        for drive in self.drives:
            drive_path = Path(drive + "/")

            if not drive_path.exists():
                self.log(f"Drive not found: {drive}")
                continue

            self.log(f"\nScanning: {drive}")

            # Limited depth scan (performance optimization)
            for root, dirs, files in os.walk(drive_path):
                # Depth limit
                depth = len(Path(root).relative_to(drive_path).parts)
                if depth > max_depth:
                    dirs.clear()  # Don't go deeper
                    continue

                # Filter excluded directories
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS
                          and not d.startswith('.') and not d.startswith('$')]

                # Process files
                for filename in files:
                    file_path = Path(root) / filename

                    self.stats["scanned"] += 1

                    # Progress indicator every 100 files
                    if self.stats["scanned"] % 100 == 0:
                        self.log(f"  ... {self.stats['scanned']} files scanned")

                    # Skip check
                    if self.should_skip(file_path):
                        continue

                    # Classify attempt
                    self.classify_file(file_path)

    def generate_report(self):
        """Generate classification report"""
        self.log("\n" + "="*60)
        self.log("=== Drive Classification Complete ===")
        self.log("="*60)
        self.log(f"Scanned files: {self.stats['scanned']:,}")
        self.log(f"Classified files: {self.stats['classified']:,}")
        self.log(f"Skipped files: {self.stats['skipped']:,}")

        if self.stats['errors']:
            self.log(f"\nErrors: {len(self.stats['errors'])}")
            for err in self.stats['errors'][:10]:  # Show max 10
                self.log(f"  - {err}")

        # Save JSON report
        report_file = self.target_base / f"classification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "drives": self.drives,
                "dry_run": self.dry_run,
                "statistics": self.stats
            }, f, indent=2, ensure_ascii=False)

        self.log(f"\nReport: {report_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Drive File Auto Classification Tool")
    parser.add_argument("--drives", nargs="+", default=["D:"], help="Drives to scan (e.g., C: D:)")
    parser.add_argument("--depth", type=int, default=3, help="Scan depth (default: 3)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no actual moves")
    parser.add_argument("--target", default="D:/wicked_zerg_challenger/data", help="Target base path")
    args = parser.parse_args()

    classifier = DriveClassifier(
        drives=args.drives,
        target_base=args.target,
        dry_run=args.dry_run
    )

    classifier.scan_and_classify(max_depth=args.depth)
    classifier.generate_report()


if __name__ == "__main__":
    main()
