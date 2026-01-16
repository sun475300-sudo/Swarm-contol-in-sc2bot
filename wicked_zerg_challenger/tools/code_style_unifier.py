# -*- coding: utf-8 -*-
"""
코드 스타일 통일 도구

PEP 8 스타일 가이드에 따라 모든 코드 스타일을 통일
"""

import re

PROJECT_ROOT = Path(__file__).parent.parent


class CodeStyleUnifier:
    """코드 스타일 통일기"""

    def __init__(self):
        self.fixes_applied: List[Dict] = []
 
 def unify_indentation(self, content: str, file_path: Path) -> Tuple[str, int]:
        """들여쓰기 통일 (4 spaces)"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0
 
 for i, line in enumerate(lines):
 if not line.strip(): # 빈 줄
                modified_lines.append('')
 continue
 
 # 탭을 4 spaces로 변환
            if '\t' in line:
 # 탭의 개수만큼 4 spaces로 변환
                leading_tabs = len(line) - len(line.lstrip('\t'))
                leading_spaces = len(line) - len(line.lstrip(' '))
 if leading_tabs > 0:
                    new_line = ' ' * (leading_tabs * 4) + line.lstrip('\t')
 modified_lines.append(new_line)
 fix_count += 1
 continue
 
 modified_lines.append(line)
 
        return '\n'.join(modified_lines), fix_count
 
 def unify_import_order(self, content: str, file_path: Path) -> Tuple[str, int]:
        """Import 순서 통일 (PEP 8)"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0
 
 # Import 섹션 찾기
 import_section = []
 import_start = -1
 import_end = -1
 in_import_section = False
 
 for i, line in enumerate(lines):
 stripped = line.strip()
 
 # Import 시작
            if stripped.startswith('import ') or stripped.startswith('from '):
 if not in_import_section:
 in_import_section = True
 import_start = i
 import_section.append((i, line))
            elif in_import_section and stripped and not stripped.startswith('#'):
 # Import 섹션 종료
 import_end = i
 break
 
 if import_section:
 # Import 정렬
 stdlib_imports = []
 third_party_imports = []
 local_imports = []
 other_lines = []
 
 for idx, line in import_section:
 stripped = line.strip()
                if stripped.startswith('from __future__'):
 other_lines.append((idx, line))
                elif any(stdlib in stripped for stdlib in ['import sys', 'import os', 'import json', 'import time', 'import random', 'import logging', 'import traceback', 'import asyncio', 'import gc', 'import re', 'import ast']):
 stdlib_imports.append((idx, line))
                elif any(third in stripped for third in ['import torch', 'import numpy', 'import sc2', 'from sc2', 'from loguru']):
 third_party_imports.append((idx, line))
 else:
 local_imports.append((idx, line))
 
 # 정렬된 import로 교체
 if stdlib_imports or third_party_imports or local_imports:
 # 기존 import 라인 제거하고 정렬된 것으로 교체
 new_imports = []
 if other_lines:
 new_imports.extend([line for _, line in other_lines])
                    new_imports.append('')
 if stdlib_imports:
 new_imports.extend([line for _, line in sorted(stdlib_imports)])
                    new_imports.append('')
 if third_party_imports:
 new_imports.extend([line for _, line in sorted(third_party_imports)])
                    new_imports.append('')
 if local_imports:
 new_imports.extend([line for _, line in sorted(local_imports)])
 
 # 기존 import 라인을 정렬된 것으로 교체
 for i in range(import_start, import_end if import_end > 0 else len(lines)):
 if i < import_start + len(import_section):
 if i == import_start:
 modified_lines.extend(new_imports)
 # 기존 라인은 스킵
 else:
 modified_lines.append(lines[i])
 
 fix_count += 1
                return '\n'.join(modified_lines), fix_count
 
 return content, 0
 
 def unify_function_naming(self, content: str, file_path: Path) -> Tuple[str, int]:
        """함수 네이밍 통일 (snake_case)"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0
 
 for i, line in enumerate(lines):
 # 함수 정의 찾기
            match = re.match(r'^(\s*)def\s+([A-Z][a-zA-Z0-9_]*)\s*\(', line)
 if match:
 indent = match.group(1)
 func_name = match.group(2)
 # 대문자로 시작하는 함수명을 snake_case로 변경 제안 (주석)
                if func_name[0].isupper() and not func_name.startswith('__'):
                    snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', func_name).lower()
                    comment = f"{indent}# STYLE: Consider renaming {func_name} to {snake_case} (PEP 8: snake_case)"
 modified_lines.append(line)
 modified_lines.append(comment)
 fix_count += 1
 continue
 
 modified_lines.append(line)
 
        return '\n'.join(modified_lines), fix_count
 
 def unify_line_length(self, content: str, file_path: Path) -> Tuple[str, int]:
        """줄 길이 통일 (최대 120자)"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0
 
 for i, line in enumerate(lines):
 if len(line) > 120:
 # 긴 줄 분리 제안 (주석)
 indent = len(line) - len(line.lstrip())
                comment = f"{' ' * indent}# STYLE: Line too long ({len(line)} chars). Consider splitting."
 modified_lines.append(line)
 modified_lines.append(comment)
 fix_count += 1
 else:
 modified_lines.append(line)
 
        return '\n'.join(modified_lines), fix_count
 
 def unify_spacing(self, content: str, file_path: Path) -> Tuple[str, int]:
        """공백 통일"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0
 
 for i, line in enumerate(lines):
 # 연산자 주변 공백
 # =, ==, !=, <, >, <=, >= 주변 공백 통일
 original_line = line
            new_line = re.sub(r'(\w+)([=!<>]+)(\w+)', r'\1 \2 \3', line)
            new_line = re.sub(r'(\w+)\s+([=!<>]+)\s+(\w+)', r'\1 \2 \3', new_line)
 
 # 함수 호출: func( ) -> func()
            new_line = re.sub(r'(\w+)\s*\(\s+\)', r'\1()', new_line)
 
 if new_line != original_line:
 modified_lines.append(new_line)
 fix_count += 1
 else:
 modified_lines.append(line)
 
        return '\n'.join(modified_lines), fix_count


def unify_code_style(file_path: Path) -> Dict:
    """코드 스타일 통일"""
 unifier = CodeStyleUnifier()
 
 try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 original_content = content
 
 # 들여쓰기 통일
 content, indent_fixes = unifier.unify_indentation(content, file_path)
 
 # Import 순서 통일
 content, import_fixes = unifier.unify_import_order(content, file_path)
 
 # 함수 네이밍 통일
 content, naming_fixes = unifier.unify_function_naming(content, file_path)
 
 # 줄 길이 통일
 content, length_fixes = unifier.unify_line_length(content, file_path)
 
 # 공백 통일
 content, spacing_fixes = unifier.unify_spacing(content, file_path)
 
 total_fixes = indent_fixes + import_fixes + naming_fixes + length_fixes + spacing_fixes
 
 if total_fixes > 0:
 # 백업 생성
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(original_content)
 
 # 수정된 내용 저장
            with open(file_path, 'w', encoding='utf-8') as f:
 f.write(content)
 
 return {
                "success": True,
                "indent_fixes": indent_fixes,
                "import_fixes": import_fixes,
                "naming_fixes": naming_fixes,
                "length_fixes": length_fixes,
                "spacing_fixes": spacing_fixes,
                "total_fixes": total_fixes
 }
 else:
 return {
                "success": False,
                "total_fixes": 0
 }
 
 except Exception as e:
 return {
            "success": False,
            "error": str(e)
 }


def main():
    """메인 함수"""
    print("=" * 70)
    print("코드 스타일 통일 도구")
    print("=" * 70)
 print()
 
 # 주요 파일 목록
 main_files = [
        "wicked_zerg_bot_pro.py",
        "production_manager.py",
        "combat_manager.py",
        "economy_manager.py",
        "intel_manager.py",
        "scouting_system.py",
        "queen_manager.py",
        "zerg_net.py"
 ]
 
 total_indent_fixes = 0
 total_import_fixes = 0
 total_naming_fixes = 0
 total_length_fixes = 0
 total_spacing_fixes = 0
 
    print("코드 스타일 통일 적용 중...")
 for main_file in main_files:
 file_path = PROJECT_ROOT / main_file
 if file_path.exists():
            print(f"  - {main_file}")
 result = unify_code_style(file_path)
 
            if result.get("success"):
                print(f"    들여쓰기: {result['indent_fixes']}개")
                print(f"    Import: {result['import_fixes']}개")
                print(f"    네이밍: {result['naming_fixes']}개")
                print(f"    줄 길이: {result['length_fixes']}개")
                print(f"    공백: {result['spacing_fixes']}개")
                total_indent_fixes += result['indent_fixes']
                total_import_fixes += result['import_fixes']
                total_naming_fixes += result['naming_fixes']
                total_length_fixes += result['length_fixes']
                total_spacing_fixes += result['spacing_fixes']
            elif result.get("error"):
                print(f"    오류: {result['error']}")
 else:
                print(f"    변경 사항 없음")
 
 print()
    print("=" * 70)
    print("코드 스타일 통일 완료!")
    print(f"  들여쓰기: {total_indent_fixes}개")
    print(f"  Import: {total_import_fixes}개")
    print(f"  네이밍: {total_naming_fixes}개")
    print(f"  줄 길이: {total_length_fixes}개")
    print(f"  공백: {total_spacing_fixes}개")
    print("=" * 70)


if __name__ == "__main__":
 main()