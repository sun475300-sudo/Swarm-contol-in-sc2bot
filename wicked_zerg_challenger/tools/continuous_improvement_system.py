# -*- coding: utf-8 -*-
"""
지속적인 개선 시스템 (Continuous Improvement System)

에러 수정, 최적화, 코드 품질 개선을 자동으로 모니터링하고 개선하는 시스템
"""

import os
import ast
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent


class ContinuousImprovementSystem:
    """지속적인 개선 시스템"""

 def __init__(self):
 self.improvement_log: List[Dict] = []
 self.error_tracker: Dict[str, int] = defaultdict(int)
 self.performance_metrics: Dict[str, float] = {}
 self.quality_metrics: Dict[str, float] = {}
 
 def monitor_errors(self, log_file: Optional[Path] = None) -> Dict:
        """에러 모니터링"""
 if log_file is None:
            log_file = PROJECT_ROOT / "logs" / "error_log.txt"
 
 errors = {
            "total_errors": 0,
            "error_types": defaultdict(int),
            "error_files": defaultdict(int),
            "recent_errors": []
 }
 
 if not log_file.exists():
 return errors
 
 try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()
 
 # 최근 100줄만 분석
 recent_lines = lines[-100:] if len(lines) > 100 else lines
 
 for line in recent_lines:
                if 'ERROR' in line or 'Exception' in line or 'Traceback' in line:
                    errors["total_errors"] += 1
 
 # 에러 타입 추출
                    if 'TypeError' in line:
                        errors["error_types"]["TypeError"] += 1
                    elif 'AttributeError' in line:
                        errors["error_types"]["AttributeError"] += 1
                    elif 'NameError' in line:
                        errors["error_types"]["NameError"] += 1
                    elif 'ValueError' in line:
                        errors["error_types"]["ValueError"] += 1
 else:
                        errors["error_types"]["Other"] += 1
 
 # 파일 추출
                    if '.py:' in line:
                        file_match = line.split('.py:')[0].split()[-1]
 if file_match:
                            errors["error_files"][file_match + '.py'] += 1
 
                    errors["recent_errors"].append(line.strip())
                    if len(errors["recent_errors"]) > 20:
                        errors["recent_errors"].pop(0)
 
 except Exception as e:
            print(f"[WARNING] Error monitoring failed: {e}")
 
 return errors
 
 def analyze_performance(self) -> Dict:
        """성능 분석"""
 performance = {
            "file_count": 0,
            "total_lines": 0,
            "average_file_size": 0,
            "large_files": [],
            "complex_functions": []
 }
 
 python_files = []
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]
 for file in files:
                if file.endswith('.py'):
 python_files.append(Path(root) / file)
 
        performance["file_count"] = len(python_files)
 
 total_lines = 0
 for file_path in python_files:
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = len(f.readlines())
 total_lines += lines
 
 if lines > 1000:
                        performance["large_files"].append({
                            "file": str(file_path.relative_to(PROJECT_ROOT)),
                            "lines": lines
 })
 
 # 복잡한 함수 찾기
 try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 for node in ast.walk(tree):
 if isinstance(node, ast.FunctionDef):
 complexity = 1
 for child in ast.walk(node):
 if isinstance(child, (ast.If, ast.While, ast.For, ast.Try)):
 complexity += 1
 if complexity > 15:
                                performance["complex_functions"].append({
                                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                                    "function": node.name,
                                    "complexity": complexity,
                                    "line": node.lineno
 })
 except Exception:
 pass
 except Exception:
 continue
 
        performance["total_lines"] = total_lines
 if python_files:
            performance["average_file_size"] = total_lines / len(python_files)
 
 return performance
 
 def check_code_quality(self) -> Dict:
        """코드 품질 체크"""
 quality = {
            "unused_imports": 0,
            "long_functions": 0,
            "duplicate_code": 0,
            "style_issues": 0
 }
 
 # 간단한 품질 체크
 python_files = []
 for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]
 for file in files:
                if file.endswith('.py'):
 python_files.append(Path(root) / file)
 
 for file_path in python_files[:50]: # 샘플링 (처음 50개만)
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 lines = content.splitlines()
 
 # 긴 함수 찾기
 try:
 tree = ast.parse(content, filename=str(file_path))
 for node in ast.walk(tree):
 if isinstance(node, ast.FunctionDef):
                            if hasattr(node, 'end_lineno') and node.end_lineno:
 func_length = node.end_lineno - node.lineno
 if func_length > 100:
                                    quality["long_functions"] += 1
 except Exception:
 pass
 
 # 스타일 이슈 찾기
 for i, line in enumerate(lines, 1):
 if len(line) > 100:
                        quality["style_issues"] += 1
                    if '\t' in line:
                        quality["style_issues"] += 1
 
 except Exception:
 continue
 
 return quality
 
 def generate_improvement_report(self) -> str:
        """개선 리포트 생성"""
 report = []
        report.append("# 지속적인 개선 리포트\n\n")
        report.append(f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        report.append("---\n\n")
 
 # 에러 모니터링
 errors = self.monitor_errors()
        report.append("## 1. 에러 모니터링\n\n")
        report.append(f"- **총 에러 수**: {errors['total_errors']}개\n\n")
 
        if errors["error_types"]:
            report.append("### 에러 타입별 분포\n\n")
            for error_type, count in sorted(errors["error_types"].items(), key=lambda x: x[1], reverse=True):
                report.append(f"- `{error_type}`: {count}개\n")
            report.append("\n")
 
        if errors["error_files"]:
            report.append("### 에러가 발생한 파일\n\n")
            for file, count in sorted(errors["error_files"].items(), key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"- `{file}`: {count}회\n")
            report.append("\n")
 
 # 성능 분석
 performance = self.analyze_performance()
        report.append("## 2. 성능 분석\n\n")
        report.append(f"- **Python 파일 수**: {performance['file_count']}개\n")
        report.append(f"- **총 코드 라인**: {performance['total_lines']:,}줄\n")
        report.append(f"- **평균 파일 크기**: {performance['average_file_size']:.1f}줄\n\n")
 
        if performance["large_files"]:
            report.append("### 큰 파일 (1000줄 이상)\n\n")
            for file_info in sorted(performance["large_files"], key=lambda x: x["lines"], reverse=True)[:10]:
                report.append(f"- `{file_info['file']}`: {file_info['lines']}줄\n")
            report.append("\n")
 
        if performance["complex_functions"]:
            report.append("### 복잡한 함수 (순환 복잡도 15 이상)\n\n")
            for func_info in sorted(performance["complex_functions"], key=lambda x: x["complexity"], reverse=True)[:10]:
                report.append(f"- `{func_info['file']}:{func_info['line']}` - `{func_info['function']}` (복잡도: {func_info['complexity']})\n")
            report.append("\n")
 
 # 코드 품질
 quality = self.check_code_quality()
        report.append("## 3. 코드 품질 체크\n\n")
        report.append(f"- **긴 함수**: {quality['long_functions']}개\n")
        report.append(f"- **스타일 이슈**: {quality['style_issues']}개\n\n")
 
 # 개선 제안
        report.append("---\n\n")
        report.append("## 개선 제안\n\n")
 
        if errors["total_errors"] > 0:
            report.append("### 1. 에러 수정\n\n")
            report.append(f"- 총 {errors['total_errors']}개의 에러가 발견되었습니다.\n")
            report.append("- 가장 빈번한 에러 타입을 우선적으로 수정하세요.\n\n")
 
        if performance["large_files"]:
            report.append("### 2. 큰 파일 분리\n\n")
            report.append(f"- {len(performance['large_files'])}개의 큰 파일이 발견되었습니다.\n")
            report.append("- 큰 파일을 작은 모듈로 분리하세요.\n\n")
 
        if performance["complex_functions"]:
            report.append("### 3. 복잡한 함수 단순화\n\n")
            report.append(f"- {len(performance['complex_functions'])}개의 복잡한 함수가 발견되었습니다.\n")
            report.append("- 복잡한 함수를 작은 함수로 분리하세요.\n\n")
 
        if quality["style_issues"] > 0:
            report.append("### 4. 코드 스타일 개선\n\n")
            report.append(f"- {quality['style_issues']}개의 스타일 이슈가 발견되었습니다.\n")
            report.append("- `bat\\improve_code_quality.bat`를 실행하여 자동 수정하세요.\n\n")
 
        return ''.join(report)
 
 def save_improvement_log(self):
        """개선 로그 저장"""
        log_file = PROJECT_ROOT / "logs" / "improvement_log.json"
 log_file.parent.mkdir(exist_ok=True)
 
 log_data = {
            "timestamp": datetime.now().isoformat(),
            "improvements": self.improvement_log,
            "error_tracker": dict(self.error_tracker),
            "performance_metrics": self.performance_metrics,
            "quality_metrics": self.quality_metrics
 }
 
 try:
            with open(log_file, 'w', encoding='utf-8') as f:
 json.dump(log_data, f, indent=2, ensure_ascii=False)
 except Exception as e:
            print(f"[WARNING] Failed to save improvement log: {e}")


def main():
    """메인 함수"""
    print("=" * 70)
    print("지속적인 개선 시스템")
    print("=" * 70)
 print()
 
 system = ContinuousImprovementSystem()
 
    print("에러 모니터링 중...")
 errors = system.monitor_errors()
    print(f"  - 총 에러 수: {errors['total_errors']}개")
    if errors["error_types"]:
        print(f"  - 에러 타입: {len(errors['error_types'])}개")
 print()
 
    print("성능 분석 중...")
 performance = system.analyze_performance()
    print(f"  - Python 파일: {performance['file_count']}개")
    print(f"  - 총 코드 라인: {performance['total_lines']:,}줄")
    print(f"  - 큰 파일: {len(performance['large_files'])}개")
    print(f"  - 복잡한 함수: {len(performance['complex_functions'])}개")
 print()
 
    print("코드 품질 체크 중...")
 quality = system.check_code_quality()
    print(f"  - 긴 함수: {quality['long_functions']}개")
    print(f"  - 스타일 이슈: {quality['style_issues']}개")
 print()
 
    print("개선 리포트 생성 중...")
 report = system.generate_improvement_report()
 
    report_path = PROJECT_ROOT / "CONTINUOUS_IMPROVEMENT_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
 f.write(report)
 
    print(f"리포트가 생성되었습니다: {report_path}")
 
 # 개선 로그 저장
 system.save_improvement_log()
    print("개선 로그가 저장되었습니다.")
 print()
    print("=" * 70)
    print("완료!")
    print("=" * 70)


if __name__ == "__main__":
 main()