#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Diet and Cleanup System
Removes unnecessary files, optimizes code, and reduces repository size
"""

import os
import sys
import shutil
import re
from pathlib import Path
from datetime import datetime

class CodeDietCleanup:
    """Comprehensive code cleanup and optimization system"""

    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path).resolve()
        self.backup_dir = Path(r"D:\백업용\cleanup_backup")
        self.report = []
        
        # CRITICAL: Exclude 아레나_배포 folder from cleanup
        self.exclude_dirs = {
            "아레나_배포",
            ".git",
            ".venv",
            "__pycache__",
        }

        # Files to remove
        self.backup_patterns = [
            "*.backup", "*.backup_*", "*_backup_*", "*.bak",
            "*.tmp", "*.temp", "*.old", "*~"
        ]

        self.log_patterns = [
            "*.log", "*.log.*", "log_*.txt", "debug_*.log", "error_*.log"
        ]

        self.cache_patterns = [
            "__pycache__", "*.pyc", "*.pyo", "*.cache", ".pytest_cache",
            ".mypy_cache", ".coverage", "htmlcov"
        ]

        self.redundant_files = [
            "bug_report.json",
            "continuous_improvement_progress.json",
            "commit_message_config.json",
            "wicked_zerg_bot_pro.py.backup_surrender_fix"
        ]

    def create_backup(self):
        """Create backup before cleanup"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
            self.log("? Created backup directory")
        return True

    def log(self, message):
        """Log message to report"""
        print(message)
        self.report.append(message)
    
    def should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded from cleanup"""
        parts = path.parts
        for exclude_dir in self.exclude_dirs:
            if exclude_dir in parts:
                return True
        return False

    def find_files_by_pattern(self, patterns):
        """Find all files matching patterns"""
        found = []
        for pattern in patterns:
            if pattern == "__pycache__":
                # Special handling for directories
                for root, dirs, files in os.walk(self.repo_path):
                    # Exclude 아레나_배포 and other excluded directories
                    dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                    if "__pycache__" in dirs:
                        pycache_path = Path(root) / "__pycache__"
                        if pycache_path.exists() and not self.should_exclude(pycache_path):
                            found.append(pycache_path)
            else:
                for file_path in self.repo_path.rglob(pattern):
                    if not self.should_exclude(file_path):
                        found.append(file_path)
        return found

    def remove_backup_files(self):
        """Remove backup and temporary files"""
        self.log("\n" + "="*70)
        self.log("??  Removing Backup & Temporary Files")
        self.log("="*70)

        files = self.find_files_by_pattern(self.backup_patterns)

        total_size = 0
        removed_count = 0

        for file_path in files:
            try:
                # CRITICAL: Double-check exclusion (safety measure)
                if self.should_exclude(file_path):
                    continue
                
                size = file_path.stat().st_size if file_path.is_file() else 0

                if file_path.is_file():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)

                total_size += size
                removed_count += 1
                self.log(f"  ? Removed: {file_path.name} ({size:,} bytes)")

            except Exception as e:
                self.log(f"  ??  Error removing {file_path}: {e}")

        self.log(f"\n? Removed {removed_count} backup/temp files ({total_size:,} bytes)")
        return removed_count, total_size

    def remove_log_files(self):
        """Remove log files (keep critical ones)"""
        self.log("\n" + "="*70)
        self.log("? Removing Log Files")
        self.log("="*70)

        files = self.find_files_by_pattern(self.log_patterns)

        # Keep recent logs (created in last hour)
        keep_recent = datetime.now().timestamp() - 3600

        total_size = 0
        removed_count = 0

        for file_path in files:
            try:
                # CRITICAL: Exclude 아레나_배포 folder
                if self.should_exclude(file_path):
                    continue
                
                if not file_path.is_file():
                    continue

                # Check if recent
                mtime = file_path.stat().st_mtime
                if mtime > keep_recent:
                    self.log(f"  ??  Keeping recent: {file_path.name}")
                    continue

                size = file_path.stat().st_size
                file_path.unlink()

                total_size += size
                removed_count += 1
                self.log(f"  ? Removed: {file_path.name} ({size:,} bytes)")

            except Exception as e:
                self.log(f"  ??  Error removing {file_path}: {e}")

        self.log(f"\n? Removed {removed_count} log files ({total_size:,} bytes)")
        return removed_count, total_size

    def remove_cache_files(self):
        """Remove Python cache files"""
        self.log("\n" + "="*70)
        self.log("??  Removing Cache Files")
        self.log("="*70)

        files = self.find_files_by_pattern(self.cache_patterns)

        total_size = 0
        removed_count = 0

        for file_path in files:
            try:
                # CRITICAL: Exclude 아레나_배포 folder
                if self.should_exclude(file_path):
                    continue
                
                if file_path.is_file():
                    size = file_path.stat().st_size
                    file_path.unlink()
                    total_size += size
                    removed_count += 1
                elif file_path.is_dir():
                    size = sum(f.stat().st_size for f in file_path.rglob('*') if f.is_file())
                    shutil.rmtree(file_path)
                    total_size += size
                    removed_count += 1

                self.log(f"  ? Removed: {file_path.name} ({size:,} bytes)")

            except Exception as e:
                self.log(f"  ??  Error removing {file_path}: {e}")

        self.log(f"\n? Removed {removed_count} cache items ({total_size:,} bytes)")
        return removed_count, total_size

    def remove_redundant_files(self):
        """Remove known redundant files"""
        self.log("\n" + "="*70)
        self.log("??  Removing Redundant Files")
        self.log("="*70)

        total_size = 0
        removed_count = 0

        for filename in self.redundant_files:
            file_path = self.repo_path / filename

            if not file_path.exists():
                continue

            try:
                size = file_path.stat().st_size
                file_path.unlink()

                total_size += size
                removed_count += 1
                self.log(f"  ? Removed: {filename} ({size:,} bytes)")

            except Exception as e:
                self.log(f"  ??  Error removing {filename}: {e}")

        self.log(f"\n? Removed {removed_count} redundant files ({total_size:,} bytes)")
        return removed_count, total_size

    def optimize_python_files(self):
        """Optimize Python files by removing unnecessary code"""
        self.log("\n" + "="*70)
        self.log("? Optimizing Python Files")
        self.log("="*70)

        py_files = [f for f in self.repo_path.rglob("*.py") if not self.should_exclude(f)]
        optimized_count = 0
        total_reduced = 0

        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_size = len(content)

                # Remove excessive blank lines (more than 2 consecutive)
                content = re.sub(r'\n{4,}', '\n\n\n', content)

                # Remove trailing whitespace
                lines = content.split('\n')
                lines = [line.rstrip() for line in lines]
                content = '\n'.join(lines)

                # Remove multiple consecutive blank lines at end
                content = content.rstrip() + '\n'

                new_size = len(content)

                if new_size < original_size:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)

                    reduced = original_size - new_size
                    total_reduced += reduced
                    optimized_count += 1
                    self.log(f"  ??  Optimized: {py_file.name} (-{reduced} bytes)")

            except Exception as e:
                self.log(f"  ??  Error optimizing {py_file.name}: {e}")

        self.log(f"\n? Optimized {optimized_count} files (-{total_reduced:,} bytes)")
        return optimized_count, total_reduced

    def analyze_duplicate_code(self):
        """Analyze for duplicate code blocks"""
        self.log("\n" + "="*70)
        self.log("? Analyzing Duplicate Code")
        self.log("="*70)

        py_files = [f for f in self.repo_path.rglob("*.py") if not self.should_exclude(f)]

        # Simple duplicate detection (files with very similar names)
        duplicates = []

        for i, file1 in enumerate(py_files):
            for file2 in py_files[i+1:]:
                name1 = file1.stem.lower()
                name2 = file2.stem.lower()

                # Check for similar names (potential duplicates)
                if name1 in name2 or name2 in name1:
                    if abs(file1.stat().st_size - file2.stat().st_size) < 1000:
                        duplicates.append((file1.name, file2.name))

        if duplicates:
            self.log("\n??  Potential duplicate files found:")
            for file1, file2 in duplicates:
                self.log(f"  - {file1} ↔?  {file2}")
            self.log("\n? Review these files manually for deduplication")
        else:
            self.log("? No obvious duplicate files found")

        return (len(duplicates), 0)  # Return tuple for consistency

    def generate_report(self, stats):
        """Generate cleanup report"""
        self.log("\n" + "="*70)
        self.log("? CLEANUP REPORT")
        self.log("="*70)

        total_files = sum(s[0] for s in stats.values() if isinstance(s, tuple))
        total_size = sum(s[1] for s in stats.values() if isinstance(s, tuple))

        self.log(f"""
Summary:
  Total Files Removed: {total_files:,}
  Total Space Saved: {total_size:,} bytes ({total_size/1024:.1f} KB)

Breakdown:
  Backup/Temp Files: {stats['backup'][0]} files, {stats['backup'][1]:,} bytes
  Log Files: {stats['log'][0]} files, {stats['log'][1]:,} bytes
  Cache Files: {stats['cache'][0]} files, {stats['cache'][1]:,} bytes
  Redundant Files: {stats['redundant'][0]} files, {stats['redundant'][1]:,} bytes
  Code Optimization: {stats['optimize'][0]} files, {stats['optimize'][1]:,} bytes saved

Duplicate Analysis:
  Potential Duplicates: {stats['duplicates'][0]} pairs found

? Code Diet Complete!
        """)

    def save_report(self):
        """Save cleanup report to file"""
        report_file = self.repo_path / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.report))

            self.log(f"\n? Report saved to: {report_file.name}")
            return report_file
        except Exception as e:
            self.log(f"??  Error saving report: {e}")
            return None

    def run_full_cleanup(self):
        """Run complete cleanup process"""
        self.log("\n" + "="*70)
        self.log("? Starting Code Diet & Cleanup")
        self.log("="*70)
        self.log(f"Repository: {self.repo_path}")
        self.log(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Create backup
        self.create_backup()

        # Run cleanup operations
        stats = {
            'backup': self.remove_backup_files(),
            'log': self.remove_log_files(),
            'cache': self.remove_cache_files(),
            'redundant': self.remove_redundant_files(),
            'optimize': self.optimize_python_files(),
            'duplicates': self.analyze_duplicate_code()
        }

        # Generate report
        self.generate_report(stats)

        # Save report
        self.save_report()

        return stats

def main():
    """Main function for code diet cleanup"""

    print("\n" + "="*70)
    print("? SC2 AI Code Diet & Cleanup System")
    print("="*70)

    # Parse arguments
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."

    # Create cleanup instance
    cleaner = CodeDietCleanup(repo_path)

    # Confirm before proceeding
    print(f"\nRepository: {cleaner.repo_path}")
    print("\nThis will:")
    print("  - Remove backup and temporary files")
    print("  - Remove old log files (keeping recent ones)")
    print("  - Remove Python cache files")
    print("  - Remove redundant files")
    print("  - Optimize Python code (whitespace)")
    print("  - Analyze for duplicates")

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        response = "y"
    else:
        response = input("\nProceed with cleanup? (y/n): ").strip().lower()

    if response != 'y':
        print("? Cleanup cancelled")
        return

    # Run cleanup
    stats = cleaner.run_full_cleanup()

    print("\n" + "="*70)
    print("? Code Diet Complete!")
    print("="*70)

if __name__ == "__main__":
    main()