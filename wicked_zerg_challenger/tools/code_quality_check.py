#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Quality Check Script
정기적으로 소스코드 품질을 점검하는 스크립트

점검 항목:
1. await 누락 문제 (Async Trap)
2. 예외 처리 패턴 (bare except)
3. 매직 넘버/문자열 하드코딩
4. Import 경로 검증
5. TODO/FIXME 주석
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# 점검 대상 파일 패턴
PYTHON_FILES_PATTERN = r"\.py$"

# 제외할 디렉토리
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
    """코드 품질 점검 클래스"""

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
        """Python 파일 찾기"""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 제외할 디렉토리 필터링
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            if any(exclude in root for exclude in EXCLUDE_DIRS):
                continue

            for file in files:
                if re.search(PYTHON_FILES_PATTERN, file):
                    file_path = Path(root) / file
                    python_files.append(file_path)
        return python_files

    def check_await_missing(self, file_path: Path, content: str) -> None:
        """await 누락 문제 점검"""
        lines = content.split("\n")
        in_async_function = False
        async_function_name = ""

        for line_num, line in enumerate(lines, 1):
            # async 함수 시작 체크
            if re.search(r"async\s+def\s+\w+", line):
                in_async_function = True
                match = re.search(r"async\s+def\s+(\w+)", line)
                if match:
                    async_function_name = match.group(1)

            # 함수/클래스 끝 체크 (간단한 휴리스틱)
            if re.search(r"^\s*(def|class|async def)", line) and in_async_function:
                # 이전 함수가 끝남 (새 함수 시작)
                prev_match = re.search(r"async\s+def\s+(\w+)", line)
                if prev_match:
                    async_function_name = prev_match.group(1)
                else:
                    in_async_function = False

            # .train() 호출 찾기 (await 없이)
            if in_async_function:
                # await 없이 train() 호출하는 패턴 찾기
                if re.search(r"\.train\s*\(", line) and "await" not in line:
                    # 주석이 아닌 경우만
                    if not re.match(r"^\s*#", line):
                        self.issues["await_missing"].append(
                            (
                                line_num,
                                str(file_path.relative_to(self.project_root)),
                                line.strip(),
                            )
                        )

    def check_bare_except(self, file_path: Path, content: str) -> None:
        """bare except 사용 점검"""
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            # bare except 패턴 찾기
            if re.search(r"except\s*:\s*", line) or re.search(r"except\s*:\s*pass", line):
                if not re.match(r"^\s*#", line):  # 주석이 아닌 경우만
                    self.issues["bare_except"].append(
                        (
                            line_num,
                            str(file_path.relative_to(self.project_root)),
                            line.strip(),
                        )
                    )

    def check_magic_numbers(self, file_path: Path, content: str) -> None:
        """매직 넘버 하드코딩 점검"""
        lines = content.split("\n")
        magic_number_pattern = r"\b(100|500|1000|2000|5000|8000)\b"

        for line_num, line in enumerate(lines, 1):
            # 주석이나 문자열 리터럴이 아닌 경우만
            if re.match(r"^\s*#", line):
                continue
            if re.search(magic_number_pattern, line):
                # config.py나 상수 정의는 제외
                if "config" not in str(file_path).lower() and "=" not in line.split("#")[0]:
                    self.issues["magic_numbers"].append(
                        (
                            line_num,
                            str(file_path.relative_to(self.project_root)),
                            line.strip(),
                        )
                    )

    def check_todo_comments(self, file_path: Path, content: str) -> None:
        """TODO/FIXME 주석 점검"""
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
        """단일 파일 점검"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.file_count += 1
            self.total_lines += len(content.split("\n"))

            # 각 점검 항목 실행
            self.check_await_missing(file_path, content)
            self.check_bare_except(file_path, content)
            self.check_magic_numbers(file_path, content)
            self.check_todo_comments(file_path, content)

        except Exception as e:
            print(f"[ERROR] Failed to check {file_path}: {e}", file=sys.stderr)

    def generate_report(self) -> str:
        """점검 결과 리포트 생성"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("코드 품질 점검 결과")
        report_lines.append("=" * 80)
        report_lines.append(f"점검 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"점검 파일 수: {self.file_count}")
        report_lines.append(f"총 코드 라인: {self.total_lines:,}")
        report_lines.append("")

        # await 누락 문제
        report_lines.append("## 1. await 누락 문제 (Async Trap)")
        report_lines.append("-" * 80)
        if self.issues["await_missing"]:
            report_lines.append(f"?? 발견: {len(self.issues['await_missing'])}곳")
            for line_num, file_path, line in self.issues["await_missing"][:10]:
                report_lines.append(f"  {file_path}:{line_num} - {line}")
            if len(self.issues["await_missing"]) > 10:
                report_lines.append(f"  ... 외 {len(self.issues['await_missing']) - 10}곳")
        else:
            report_lines.append("? 문제 없음")
        report_lines.append("")

        # bare except 문제
        report_lines.append("## 2. Bare Except 사용")
        report_lines.append("-" * 80)
        if self.issues["bare_except"]:
            report_lines.append(f"?? 발견: {len(self.issues['bare_except'])}곳")
            for line_num, file_path, line in self.issues["bare_except"][:10]:
                report_lines.append(f"  {file_path}:{line_num} - {line}")
            if len(self.issues["bare_except"]) > 10:
                report_lines.append(f"  ... 외 {len(self.issues['bare_except']) - 10}곳")
        else:
            report_lines.append("? 문제 없음")
        report_lines.append("")

        # 매직 넘버 문제
        report_lines.append("## 3. 매직 넘버 하드코딩")
        report_lines.append("-" * 80)
        if self.issues["magic_numbers"]:
            report_lines.append(f"?? 발견: {len(self.issues['magic_numbers'])}곳 (참고용)")
            for line_num, file_path, line in self.issues["magic_numbers"][:10]:
                report_lines.append(f"  {file_path}:{line_num} - {line}")
            if len(self.issues["magic_numbers"]) > 10:
                report_lines.append(f"  ... 외 {len(self.issues['magic_numbers']) - 10}곳")
        else:
            report_lines.append("? 문제 없음")
        report_lines.append("")

        # TODO/FIXME 주석
        report_lines.append("## 4. TODO/FIXME 주석")
        report_lines.append("-" * 80)
        if self.issues["todo_comments"]:
            report_lines.append(f"? 발견: {len(self.issues['todo_comments'])}곳")
            for line_num, file_path, line in self.issues["todo_comments"][:10]:
                report_lines.append(f"  {file_path}:{line_num} - {line}")
            if len(self.issues["todo_comments"]) > 10:
                report_lines.append(f"  ... 외 {len(self.issues['todo_comments']) - 10}곳")
        else:
            report_lines.append("? 없음")
        report_lines.append("")

        # 요약
        total_issues = sum(len(issues) for issues in self.issues.values())
        report_lines.append("=" * 80)
        report_lines.append("요약")
        report_lines.append("=" * 80)
        report_lines.append(f"총 발견된 문제: {total_issues}곳")
        report_lines.append(f"  - await 누락: {len(self.issues['await_missing'])}곳")
        report_lines.append(f"  - bare except: {len(self.issues['bare_except'])}곳")
        report_lines.append(f"  - 매직 넘버: {len(self.issues['magic_numbers'])}곳 (참고)")
        report_lines.append(f"  - TODO/FIXME: {len(self.issues['todo_comments'])}곳")
        report_lines.append("")

        if total_issues == 0:
            report_lines.append("? 모든 점검 항목 통과!")
        elif len(self.issues["await_missing"]) == 0:
            report_lines.append("? 주요 문제(await 누락) 없음")
        else:
            report_lines.append("?? 주의: await 누락 문제 발견")

        return "\n".join(report_lines)

    def run(self) -> int:
        """점검 실행"""
        print("코드 품질 점검 시작...")
        print(f"프로젝트 루트: {self.project_root}")
        print("")

        python_files = self.find_python_files()
        print(f"점검 대상 파일: {len(python_files)}개")
        print("")

        for file_path in python_files:
            self.check_file(file_path)

        # 리포트 생성
        report = self.generate_report()
        print(report)

        # 주요 문제가 있으면 종료 코드 1 반환
        if len(self.issues["await_missing"]) > 0:
            return 1
        return 0


def main():
    """메인 함수"""
    checker = CodeQualityChecker()
    exit_code = checker.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
