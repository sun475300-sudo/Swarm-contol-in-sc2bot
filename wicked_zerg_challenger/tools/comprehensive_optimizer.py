# -*- coding: utf-8 -*-
"""
종합 최적화 도구

1. 불필요한 파일 식별 및 삭제
2. 코드 스타일 통일화
3. 실행 로직 정밀검토
4. 전체 로직 최적화
"""

import os
import ast
import re
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent


class ComprehensiveOptimizer:
    """종합 최적화기"""
 
 def __init__(self, dry_run: bool = True):
 self.dry_run = dry_run
 self.files_to_remove: List[Path] = []
 self.dirs_to_remove: List[Path] = []
 self.style_issues: Dict[str, List[str]] = {}
 self.optimization_suggestions: List[str] = []
 
 def identify_unnecessary_files(self) -> Dict:
        """불필요한 파일 식별"""
 unnecessary_patterns = [
 # 백업 파일
            '**/*.bak',
            '**/*.backup',
            '**/*~',
            '**/*.tmp',
            '**/*.temp',
 
 # 캐시 파일
            '**/__pycache__/**',
            '**/*.pyc',
            '**/*.pyo',
            '**/.pytest_cache/**',
            '**/.mypy_cache/**',
 
 # IDE 파일
            '**/.idea/**',
            '**/.vscode/**',
            '**/.vs/**',
            '**/*.swp',
            '**/*.swo',
            '**/.DS_Store',
 
 # 로그 파일 (오래된 것)
            '**/logs/*.log',
            '**/logs/*.txt',
 
 # 임시 문서
            '**/TEMP_*.md',
            '**/temp_*.md',
            '**/*_temp.md',
 ]
 
 # 제외할 디렉토리
 exclude_dirs = {
            '__pycache__', '.git', '.venv', 'venv', 'node_modules',
            'models', 'checkpoints', 'data', 'replays'
 }
 
 files_found = []
 dirs_found = []
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
 # 제외할 디렉토리 필터링
 dirs[:] = [d for d in dirs if d not in exclude_dirs]
 
 for file in files:
 file_path = Path(root) / file
 rel_path = file_path.relative_to(PROJECT_ROOT)
 
 # 패턴 매칭
 for pattern in unnecessary_patterns:
                    if file_path.match(pattern) or file_path.name.endswith(('.bak', '.backup', '~', '.tmp', '.temp')):
 files_found.append(file_path)
 break
 
 # 빈 디렉토리 찾기
 for dir_name in dirs:
 dir_path = Path(root) / dir_name
 try:
 if not any(dir_path.iterdir()):
 dirs_found.append(dir_path)
 except Exception:
 pass
 
 return {
            "files": files_found,
            "dirs": dirs_found
 }
 
 def check_code_style_consistency(self) -> Dict:
        """코드 스타일 일관성 검사"""
 issues = defaultdict(list)
 
 python_files = []
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]
 for file in files:
                if file.endswith('.py'):
 python_files.append(Path(root) / file)
 
 for file_path in python_files[:100]: # 샘플링
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 lines = content.splitlines()
 
 # 들여쓰기 검사 (탭 vs 공백)
 for i, line in enumerate(lines, 1):
                    if line.startswith('\t'):
                        issues[str(file_path)].append(f"Line {i}: Tab character used (use spaces)")
 
 # 줄 길이 검사
 if len(line.rstrip()) > 120:
                        issues[str(file_path)].append(f"Line {i}: Line too long ({len(line.rstrip())} characters)")
 
 # 연속된 공백 검사
                    if re.search(r' {3,}', line):
                        issues[str(file_path)].append(f"Line {i}: Multiple consecutive spaces")
 
 # Import 순서 검사
 imports = []
 for i, line in enumerate(lines, 1):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
 imports.append((i, line))
 
 if imports:
 # 표준 라이브러리, 서드파티, 로컬 순서 확인
 pass # 간단한 버전이므로 생략
 
 except Exception as e:
                issues[str(file_path)].append(f"Error reading file: {e}")
 
 return dict(issues)
 
 def analyze_execution_logic(self) -> Dict:
        """실행 로직 분석"""
 analysis = {
            "main_scripts": [],
            "import_errors": [],
            "circular_imports": [],
            "missing_dependencies": []
 }
 
 # 메인 스크립트 찾기
 main_scripts = [
            'main.py',
            'COMPLETE_RUN_SCRIPT.py',
            'run_*.py'
 ]
 
 for root, dirs, files in os.walk(PROJECT_ROOT):
 for file in files:
                if file in ['main.py', 'COMPLETE_RUN_SCRIPT.py'] or file.startswith('run_'):
 file_path = Path(root) / file
                    analysis["main_scripts"].append(str(file_path.relative_to(PROJECT_ROOT)))
 
 return analysis
 
 def optimize_code(self) -> List[str]:
        """코드 최적화 제안"""
 suggestions = []
 
 python_files = []
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]
 for file in files:
                if file.endswith('.py'):
 python_files.append(Path(root) / file)
 
 # 큰 파일 찾기
 large_files = []
 for file_path in python_files:
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = len(f.readlines())
 if lines > 1000:
 large_files.append((str(file_path.relative_to(PROJECT_ROOT)), lines))
 except Exception:
 pass
 
 if large_files:
            suggestions.append(f"큰 파일 발견 ({len(large_files)}개): 분리 고려")
 for file, lines in sorted(large_files, key=lambda x: x[1], reverse=True)[:5]:
                suggestions.append(f"  - {file}: {lines}줄")
 
 # 복잡한 함수 찾기
 complex_functions = []
 for file_path in python_files[:50]: # 샘플링
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 
 for node in ast.walk(tree):
 if isinstance(node, ast.FunctionDef):
 complexity = 1
 for child in ast.walk(node):
 if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
 complexity += 1
 if complexity > 20:
 complex_functions.append((
 str(file_path.relative_to(PROJECT_ROOT)),
 node.name,
 node.lineno,
 complexity
 ))
 except Exception:
 pass
 
 if complex_functions:
            suggestions.append(f"복잡한 함수 발견 ({len(complex_functions)}개): 단순화 고려")
 for file, func, line, comp in sorted(complex_functions, key=lambda x: x[3], reverse=True)[:5]:
                suggestions.append(f"  - {file}:{line} {func}() (복잡도: {comp})")
 
 return suggestions
 
 def generate_report(self) -> str:
        """최적화 리포트 생성"""
 report = []
        report.append("# 종합 최적화 리포트\n\n")
 
 # 불필요한 파일
 unnecessary = self.identify_unnecessary_files()
        report.append("## 1. 불필요한 파일\n\n")
        report.append(f"- 발견된 파일: {len(unnecessary['files'])}개\n")
        report.append(f"- 발견된 디렉토리: {len(unnecessary['dirs'])}개\n\n")
 
        if unnecessary['files']:
            report.append("### 삭제 대상 파일 (상위 20개)\n\n")
            for file_path in unnecessary['files'][:20]:
                report.append(f"- `{file_path.relative_to(PROJECT_ROOT)}`\n")
            report.append("\n")
 
 # 코드 스타일
 style_issues = self.check_code_style_consistency()
        report.append("## 2. 코드 스타일 일관성\n\n")
 total_issues = sum(len(issues) for issues in style_issues.values())
        report.append(f"- 총 스타일 이슈: {total_issues}개\n")
        report.append(f"- 영향받는 파일: {len(style_issues)}개\n\n")
 
 # 실행 로직
 execution = self.analyze_execution_logic()
        report.append("## 3. 실행 로직 분석\n\n")
        report.append(f"- 메인 스크립트: {len(execution['main_scripts'])}개\n")
        for script in execution['main_scripts']:
            report.append(f"  - `{script}`\n")
        report.append("\n")
 
 # 최적화 제안
 suggestions = self.optimize_code()
        report.append("## 4. 최적화 제안\n\n")
 for suggestion in suggestions:
            report.append(f"- {suggestion}\n")
        report.append("\n")
 
        return ''.join(report)
 
 def execute_optimization(self):
        """최적화 실행"""
        print("=" * 70)
        print("종합 최적화 실행")
        print("=" * 70)
 print()
 
 # 불필요한 파일 삭제
 if not self.dry_run:
 unnecessary = self.identify_unnecessary_files()
            print(f"불필요한 파일 삭제 중... ({len(unnecessary['files'])}개)")
            for file_path in unnecessary['files']:
 try:
 file_path.unlink()
                    print(f"  [DELETED] {file_path.relative_to(PROJECT_ROOT)}")
 except Exception as e:
                    print(f"  [ERROR] {file_path.relative_to(PROJECT_ROOT)}: {e}")
 
            print(f"빈 디렉토리 삭제 중... ({len(unnecessary['dirs'])}개)")
            for dir_path in unnecessary['dirs']:
 try:
 dir_path.rmdir()
                    print(f"  [DELETED] {dir_path.relative_to(PROJECT_ROOT)}")
 except Exception as e:
                    print(f"  [ERROR] {dir_path.relative_to(PROJECT_ROOT)}: {e}")
 else:
            print("[DRY RUN] 실제 삭제는 수행하지 않습니다.")
 
 # 리포트 생성
        print("\n최적화 리포트 생성 중...")
 report = self.generate_report()
        report_path = PROJECT_ROOT / "COMPREHENSIVE_OPTIMIZATION_REPORT.md"
        with open(report_path, 'w', encoding='utf-8') as f:
 f.write(report)
        print(f"리포트가 생성되었습니다: {report_path}")


def main():
    """메인 함수"""
 import argparse
 
    parser = argparse.ArgumentParser(description="종합 최적화 도구")
    parser.add_argument("--execute", action="store_true", help="실제로 최적화 실행 (기본값: dry-run)")
 
 args = parser.parse_args()
 
 optimizer = ComprehensiveOptimizer(dry_run=not args.execute)
 optimizer.execute_optimization()


if __name__ == "__main__":
 main()