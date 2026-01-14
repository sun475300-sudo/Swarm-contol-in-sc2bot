#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Quality Check Script
Á¤±âÀûÀ¸·Î ¼Ò½ºÄÚµå Ç°ÁúÀ» Á¡°ËÇÏ´Â ½ºÅ©¸³Æ®

Á¡°Ë Ç×¸ñ:
1. await ´©¶ô ¹®Á¦ (Async Trap)
2. ¿¹¿Ü Ã³¸® ÆÐÅÏ (bare except)
3. ¸ÅÁ÷ ³Ñ¹ö/¹®ÀÚ¿­ ÇÏµåÄÚµù
4. Import °æ·Î °ËÁõ
5. TODO/FIXME ÁÖ¼®
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# ÇÁ·ÎÁ§Æ® ·çÆ® µð·ºÅä¸®
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Á¡°Ë ´ë»ó ÆÄÀÏ ÆÐÅÏ
PYTHON_FILES_PATTERN = r"\.py$"

# Á¦¿ÜÇÒ µð·ºÅä¸®
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "venv",
    "local_training/venv",
    "node_modules",
    "models",
    "logs",
    "data",
    "replays",
    "backups",
    "static",
    "stats",
}


class CodeQualityChecker:
    """ÄÚµå Ç°Áú Á¡°Ë Å¬·¡½º"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or PROJECT_ROOT
        self.issues: Dict[str, List[Tuple[int, str, str]]] = {
            "await_missing": [],
            "bare_except": [],
            "magic_numbers": [],
            "todo_comments": [],
        }
        self.file_count = 0
        self.total_lines = 0

    def find_python_files(self) -> List[Path]:
        """Python ÆÄÀÏ Ã£±â"""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Á¦¿ÜÇÒ µð·ºÅä¸® ÇÊÅÍ¸µ
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            if any(exclude in root for exclude in EXCLUDE_DIRS):
                continue

            for file in files:
                if re.search(PYTHON_FILES_PATTERN, file):
                    file_path = Path(root) / file
                    python_files.append(file_path)
        return python_files

    def check_await_missing(self, file_path: Path, content: str) -> None:
        """await ´©¶ô ¹®Á¦ Á¡°Ë"""
        lines = content.split("\n")
        in_async_function = False
        async_function_name = ""

        for line_num, line in enumerate(lines, 1):
            # async ÇÔ¼ö ½ÃÀÛ Ã¼Å©
            if re.search(r"async\s+def\s+\w+", line):
                in_async_function = True
                match = re.search(r"async\s+def\s+(\w+)", line)
                if match:
                    async_function_name = match.group(1)

            # ÇÔ¼ö/Å¬·¡½º ³¡ Ã¼Å© (°£´ÜÇÑ ÈÞ¸®½ºÆ½)
            if re.search(r"^\s*(def|class|async def)", line) and in_async_function:
                # ÀÌÀü ÇÔ¼ö°¡ ³¡³² (»õ ÇÔ¼ö ½ÃÀÛ)
                prev_match = re.search(r"async\s+def\s+(\w+)", line)
                if prev_match:
                    async_function_name = prev_match.group(1)
                else:
                    in_async_function = False

            # .train() È£Ãâ Ã£±â (await ¾øÀÌ)
            if in_async_function:
                # await ¾øÀÌ train() È£ÃâÇÏ´Â ÆÐÅÏ Ã£±â
                if re.search(r"\.train\s*\(", line) and "await" not in line:
                    # ÁÖ¼®ÀÌ ¾Æ´Ñ °æ¿ì¸¸
                    if not re.match(r"^\s*#", line):
                        self.issues["await_missing"].append(
                            (
                                line_num,
                                str(file_path.relative_to(self.project_root)),
                                line.strip(),
                            )
                        )

    def check_bare_except(self, file_path: Path, content: str) -> None:
        """bare except »ç¿ë Á¡°Ë"""
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            # bare except ÆÐÅÏ Ã£±â
            if re.search(r"except\s*:\s*", line) or re.search(r"except\s*:\s*pass", line):
                if not re.match(r"^\s*#", line):  # ÁÖ¼®ÀÌ ¾Æ´Ñ °æ¿ì¸¸
                    self.issues["bare_except"].append(
                        (
                            line_num,
                            str(file_path.relative_to(self.project_root)),
                            line.strip(),
                        )
                    )

    def check_magic_numbers(self, file_path: Path, content: str) -> None:
        """¸ÅÁ÷ ³Ñ¹ö ÇÏµåÄÚµù Á¡°Ë"""
        lines = content.split("\n")
        magic_number_pattern = r"\b(100|500|1000|2000|5000|8000)\b"

        for line_num, line in enumerate(lines, 1):
            # ÁÖ¼®ÀÌ³ª ¹®ÀÚ¿­ ¸®ÅÍ·²ÀÌ ¾Æ´Ñ °æ¿ì¸¸
            if re.match(r"^\s*#", line):
                continue
            if re.search(magic_number_pattern, line):
                # config.py³ª »ó¼ö Á¤ÀÇ´Â Á¦¿Ü
                if "config" not in str(file_path).lower() and "=" not in line.split("#")[0]:
                    self.issues["magic_numbers"].append(
                        (
                            line_num,
                            str(file_path.relative_to(self.project_root)),
                            line.strip(),
                        )
                    )

    def check_todo_comments(self, file_path: Path, content: str) -> None:
        """TODO/FIXME ÁÖ¼® Á¡°Ë"""
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if re.search(r"(TODO|FIXME|XXX|HACK|BUG)", line, re.IGNORECASE):
                self.issues["todo_comments"].append(
                    (
                        line_num,
                        str(file_path.relative_to(self.project_root)),
                        line.strip(),
                    )
                )

    def check_file(self, file_path: Path) -> None:
        """´ÜÀÏ ÆÄÀÏ Á¡°Ë"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.file_count += 1
            self.total_lines += len(content.split("\n"))

            # °¢ Á¡°Ë Ç×¸ñ ½ÇÇà
            self.check_await_missing(file_path, content)
            self.check_bare_except(file_path, content)
            self.check_magic_numbers(file_path, content)
            self.check_todo_comments(file_path, content)

        except Exception as e:
            print(f"[ERROR] Failed to check {file_path}: {e}", file=sys.stderr)

    def generate_report(self) -> str:
        """Á¡°Ë °á°ú ¸®Æ÷Æ® »ý¼º"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("ÄÚµå Ç°Áú Á¡°Ë °á°ú")
        report_lines.append("=" * 80)
        report_lines.append(f"Á¡°Ë ÀÏ½Ã: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Á¡°Ë ÆÄÀÏ ¼ö: {self.file_count}")
        report_lines.append(f"ÃÑ ÄÚµå ¶óÀÎ: {self.total_lines:,}")
        report_lines.append("")

        # await ´©¶ô ¹®Á¦
        report_lines.append("## 1. await ´©¶ô ¹®Á¦ (Async Trap)")
        report_lines.append("-" * 80)
        if self.issues["await_missing"]:
            report_lines.append(f"?? ¹ß°ß: {len(self.issues['await_missing'])}°÷")
            for line_num, file_path, line in self.issues["await_missing"][:10]:
                report_lines.append(f"  {file_path}:{line_num} - {line}")
            if len(self.issues["await_missing"]) > 10:
                report_lines.append(f"  ... ¿Ü {len(self.issues['await_missing']) - 10}°÷")
        else:
            report_lines.append("? ¹®Á¦ ¾øÀ½")
        report_lines.append("")

        # bare except ¹®Á¦
        report_lines.append("## 2. Bare Except »ç¿ë")
        report_lines.append("-" * 80)
        if self.issues["bare_except"]:
            report_lines.append(f"?? ¹ß°ß: {len(self.issues['bare_except'])}°÷")
            for line_num, file_path, line in self.issues["bare_except"][:10]:
                report_lines.append(f"  {file_path}:{line_num} - {line}")
            if len(self.issues["bare_except"]) > 10:
                report_lines.append(f"  ... ¿Ü {len(self.issues['bare_except']) - 10}°÷")
        else:
            report_lines.append("? ¹®Á¦ ¾øÀ½")
        report_lines.append("")

        # ¸ÅÁ÷ ³Ñ¹ö ¹®Á¦
        report_lines.append("## 3. ¸ÅÁ÷ ³Ñ¹ö ÇÏµåÄÚµù")
        report_lines.append("-" * 80)
        if self.issues["magic_numbers"]:
            report_lines.append(f"?? ¹ß°ß: {len(self.issues['magic_numbers'])}°÷ (Âü°í¿ë)")
            for line_num, file_path, line in self.issues["magic_numbers"][:10]:
                report_lines.append(f"  {file_path}:{line_num} - {line}")
            if len(self.issues["magic_numbers"]) > 10:
                report_lines.append(f"  ... ¿Ü {len(self.issues['magic_numbers']) - 10}°÷")
        else:
            report_lines.append("? ¹®Á¦ ¾øÀ½")
        report_lines.append("")

        # TODO/FIXME ÁÖ¼®
        report_lines.append("## 4. TODO/FIXME ÁÖ¼®")
        report_lines.append("-" * 80)
        if self.issues["todo_comments"]:
            report_lines.append(f"? ¹ß°ß: {len(self.issues['todo_comments'])}°÷")
            for line_num, file_path, line in self.issues["todo_comments"][:10]:
                report_lines.append(f"  {file_path}:{line_num} - {line}")
            if len(self.issues["todo_comments"]) > 10:
                report_lines.append(f"  ... ¿Ü {len(self.issues['todo_comments']) - 10}°÷")
        else:
            report_lines.append("? ¾øÀ½")
        report_lines.append("")

        # ¿ä¾à
        total_issues = sum(len(issues) for issues in self.issues.values())
        report_lines.append("=" * 80)
        report_lines.append("¿ä¾à")
        report_lines.append("=" * 80)
        report_lines.append(f"ÃÑ ¹ß°ßµÈ ¹®Á¦: {total_issues}°÷")
        report_lines.append(f"  - await ´©¶ô: {len(self.issues['await_missing'])}°÷")
        report_lines.append(f"  - bare except: {len(self.issues['bare_except'])}°÷")
        report_lines.append(f"  - ¸ÅÁ÷ ³Ñ¹ö: {len(self.issues['magic_numbers'])}°÷ (Âü°í)")
        report_lines.append(f"  - TODO/FIXME: {len(self.issues['todo_comments'])}°÷")
        report_lines.append("")

        if total_issues == 0:
            report_lines.append("? ¸ðµç Á¡°Ë Ç×¸ñ Åë°ú!")
        elif len(self.issues["await_missing"]) == 0:
            report_lines.append("? ÁÖ¿ä ¹®Á¦(await ´©¶ô) ¾øÀ½")
        else:
            report_lines.append("?? ÁÖÀÇ: await ´©¶ô ¹®Á¦ ¹ß°ß")

        return "\n".join(report_lines)

    def run(self) -> int:
        """Á¡°Ë ½ÇÇà"""
        print("ÄÚµå Ç°Áú Á¡°Ë ½ÃÀÛ...")
        print(f"ÇÁ·ÎÁ§Æ® ·çÆ®: {self.project_root}")
        print("")

        python_files = self.find_python_files()
        print(f"Á¡°Ë ´ë»ó ÆÄÀÏ: {len(python_files)}°³")
        print("")

        for file_path in python_files:
            self.check_file(file_path)

        # ¸®Æ÷Æ® »ý¼º
        report = self.generate_report()
        print(report)

        # ÁÖ¿ä ¹®Á¦°¡ ÀÖÀ¸¸é Á¾·á ÄÚµå 1 ¹ÝÈ¯
        if len(self.issues["await_missing"]) > 0:
            return 1
        return 0


def main():
    """¸ÞÀÎ ÇÔ¼ö"""
    checker = CodeQualityChecker()
    exit_code = checker.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
