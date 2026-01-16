# -*- coding: utf-8 -*-
"""
코드 품질 개선 자동화 도구

1. 중복 코드 제거
2. 사용하지 않는 import 정리
3. 코드 스타일 통일
4. 타입 힌트 추가
"""

import ast
import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent


class CodeQualityImprover:
    """코드 품질 개선기"""

    def __init__(self):
        self.unused_imports: Dict[str, List[str]] = {}
        self.duplicate_code: List[Dict] = []
        self.style_issues: Dict[str, List[str]] = {}

    def remove_unused_imports(self, file_path: Path) -> Tuple[bool, List[str]]:
        """사용하지 않는 import 제거"""
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 lines = content.splitlines()
 
 tree = ast.parse(content, filename=str(file_path))
 
 # Import 찾기
 imports = []
 import_lines = {}
 for node in ast.walk(tree):
 if isinstance(node, ast.Import):
 for alias in node.names:
 imports.append(alias.name)
 import_lines[alias.name] = node.lineno
 elif isinstance(node, ast.ImportFrom):
 if node.module:
 for alias in node.names:
                            full_name = f"{node.module}.{alias.name}"
 imports.append(alias.name)
 imports.append(full_name)
 import_lines[alias.name] = node.lineno
 import_lines[full_name] = node.lineno
 
 # 사용된 이름 찾기
 used_names = set()
 for node in ast.walk(tree):
 if isinstance(node, ast.Name):
 used_names.add(node.id)
 elif isinstance(node, ast.Attribute):
 if isinstance(node.value, ast.Name):
 used_names.add(node.value.id)
 
 # 사용하지 않는 import 찾기
 unused = []
 for imp in imports:
                base_name = imp.split('.')[0]
 if base_name not in used_names and imp not in used_names:
 # 표준 라이브러리는 제외 (간접 사용 가능)
                    if base_name not in ['os', 'sys', 'json', 'pathlib', 'typing', 
                                        'collections', 'datetime', 'logging', 'time',
                                        'random', 'math', 're', 'subprocess']:
 unused.append(imp)
 
 if unused:
 # 실제로 import 라인 제거
 new_lines = []
 skip_lines = set()
 for imp in unused:
 if imp in import_lines:
 skip_lines.add(import_lines[imp] - 1) # 0-based index
 
 for i, line in enumerate(lines):
 if i not in skip_lines:
 new_lines.append(line)
 
 # 파일 저장
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
 
 return True, unused
 
 return False, []
 
 except Exception as e:
            return False, [f"Error: {str(e)}"]
 
 def check_code_style(self, file_path: Path) -> List[str]:
        """코드 스타일 검사"""
 issues = []
 
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()
 
 # PEP 8 기본 검사
 for i, line in enumerate(lines, 1):
 # 줄 길이 검사 (100자 초과)
 if len(line.rstrip()) > 100:
                    issues.append(f"Line {i}: Line too long ({len(line.rstrip())} characters)")
 
 # 들여쓰기 검사 (탭 사용)
                if line.startswith('\t'):
                    issues.append(f"Line {i}: Tab character used (use spaces)")
 
 # 공백 검사
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    if '  ' in line:  # 연속된 공백
                        issues.append(f"Line {i}: Multiple spaces found")
 
 return issues
 
 except Exception as e:
            return [f"Error reading file: {str(e)}"]
 
 def fix_code_style(self, file_path: Path) -> bool:
        """코드 스타일 자동 수정"""
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 lines = content.splitlines()
 
 fixed_lines = []
 for line in lines:
 # 탭을 공백으로 변환
                fixed_line = line.replace('\t', '    ')
 
 # 연속된 공백 정리 (단, 문자열 내부는 제외)
                if '  ' in fixed_line and '"' not in fixed_line and "'" not in fixed_line:
                    fixed_line = re.sub(r' {2,}', ' ', fixed_line)
 
 fixed_lines.append(fixed_line)
 
 # 파일 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
 
 return True
 
 except Exception as e:
            print(f"Error fixing style in {file_path}: {e}")
 return False
 
 def find_duplicate_functions(self, all_files: List[Path]) -> List[Dict]:
        """중복 함수 찾기 (간단한 버전)"""
 function_signatures: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
 
 for file_path in all_files:
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 
 for node in ast.walk(tree):
 if isinstance(node, ast.FunctionDef):
 # 함수 시그니처 생성
                            sig = f"{node.name}({len(node.args.args)} args)"
 function_signatures[sig].append((
 str(file_path.relative_to(PROJECT_ROOT)),
 node.lineno
 ))
 except Exception:
 continue
 
 duplicates = []
 for sig, occurrences in function_signatures.items():
 if len(occurrences) > 1:
 duplicates.append({
                    "signature": sig,
                    "occurrences": occurrences,
                    "count": len(occurrences)
 })
 
        return sorted(duplicates, key=lambda x: x["count"], reverse=True)


def find_all_python_files() -> List[Path]:
    """모든 Python 파일 찾기"""
 python_files = []
    exclude_dirs = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
 dirs[:] = [d for d in dirs if d not in exclude_dirs]
 
 for file in files:
            if file.endswith('.py'):
 python_files.append(Path(root) / file)
 
 return python_files


def main():
    """메인 함수"""
 import argparse
 
    parser = argparse.ArgumentParser(description="코드 품질 개선 도구")
    parser.add_argument("--remove-unused", action="store_true", help="사용하지 않는 import 제거")
    parser.add_argument("--fix-style", action="store_true", help="코드 스타일 자동 수정")
    parser.add_argument("--check-style", action="store_true", help="코드 스타일 검사")
    parser.add_argument("--all", action="store_true", help="모든 개선 작업 수행")
 
 args = parser.parse_args()
 
 if not any([args.remove_unused, args.fix_style, args.check_style, args.all]):
 parser.print_help()
 return
 
    print("=" * 70)
    print("코드 품질 개선 도구")
    print("=" * 70)
 print()
 
 improver = CodeQualityImprover()
 python_files = find_all_python_files()
 
    print(f"총 {len(python_files)}개의 Python 파일을 찾았습니다.")
 print()
 
 if args.all or args.remove_unused:
        print("사용하지 않는 import 제거 중...")
 removed_count = 0
 for i, file_path in enumerate(python_files, 1):
 if i % 20 == 0:
                print(f"  진행 중: {i}/{len(python_files)}")
 success, unused = improver.remove_unused_imports(file_path)
 if success and unused:
 removed_count += len(unused)
 rel_path = file_path.relative_to(PROJECT_ROOT)
                print(f"  [FIXED] {rel_path}: {len(unused)}개 import 제거")
        print(f"총 {removed_count}개의 사용하지 않는 import를 제거했습니다.")
 print()
 
 if args.all or args.check_style:
        print("코드 스타일 검사 중...")
 total_issues = 0
 for i, file_path in enumerate(python_files, 1):
 if i % 20 == 0:
                print(f"  진행 중: {i}/{len(python_files)}")
 issues = improver.check_code_style(file_path)
 if issues:
 total_issues += len(issues)
 rel_path = file_path.relative_to(PROJECT_ROOT)
                print(f"  [ISSUES] {rel_path}: {len(issues)}개 문제 발견")
        print(f"총 {total_issues}개의 스타일 문제를 발견했습니다.")
 print()
 
 if args.all or args.fix_style:
        print("코드 스타일 자동 수정 중...")
 fixed_count = 0
 for i, file_path in enumerate(python_files, 1):
 if i % 20 == 0:
                print(f"  진행 중: {i}/{len(python_files)}")
 if improver.fix_code_style(file_path):
 fixed_count += 1
        print(f"총 {fixed_count}개 파일의 스타일을 수정했습니다.")
 print()
 
    print("=" * 70)
    print("작업 완료!")
    print("=" * 70)


if __name__ == "__main__":
 main()