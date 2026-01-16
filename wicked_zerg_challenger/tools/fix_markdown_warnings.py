# -*- coding: utf-8 -*-
"""
Markdown 파일 경고 자동 수정 도구

마크다운 스타일 경고를 자동으로 수정합니다.
"""

import re
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent


def fix_markdown_file(file_path: Path) -> List[str]:
    """마크다운 파일의 경고를 수정"""
 fixes = []
 
 try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()
 except Exception as e:
        return [f"Error reading file: {e}"]
 
 new_lines = []
 i = 0
 
 while i < len(lines):
 line = lines[i]
 original_line = line
 
 # MD009: Trailing spaces 제거
 if line.rstrip() != line and line.strip():
            line = line.rstrip() + '\n'
 if line != original_line:
                fixes.append(f"Line {i+1}: Removed trailing spaces")
 
 # MD022: 헤딩 앞뒤 빈 줄 추가
        if re.match(r'^#{1,6}\s+', line):
 # 헤딩 앞에 빈 줄 추가 (이전 줄이 비어있지 않으면)
            if new_lines and new_lines[-1].strip() and new_lines[-1] != '\n':
                new_lines.append('\n')
                fixes.append(f"Line {i+1}: Added blank line before heading")
 
 new_lines.append(line)
 
 # 헤딩 뒤에 빈 줄 추가 (다음 줄이 비어있지 않으면)
            if i + 1 < len(lines) and lines[i + 1].strip() and lines[i + 1] != '\n':
                new_lines.append('\n')
                fixes.append(f"Line {i+1}: Added blank line after heading")
 # MD032: 리스트 앞뒤 빈 줄 추가
        elif re.match(r'^[\s]*[-*+]\s+', line) or re.match(r'^[\s]*\d+\.\s+', line):
 # 리스트 앞에 빈 줄 추가
            if new_lines and new_lines[-1].strip() and not re.match(r'^[\s]*[-*+]\s+', new_lines[-1]) and not re.match(r'^[\s]*\d+\.\s+', new_lines[-1]):
                if new_lines[-1] != '\n':
                    new_lines.append('\n')
                    fixes.append(f"Line {i+1}: Added blank line before list")
 
 new_lines.append(line)
 
 # 리스트 뒤에 빈 줄 추가 (다음 줄이 리스트가 아니고 비어있지 않으면)
 if i + 1 < len(lines):
 next_line = lines[i + 1]
                if next_line.strip() and not re.match(r'^[\s]*[-*+]\s+', next_line) and not re.match(r'^[\s]*\d+\.\s+', next_line) and not re.match(r'^#{1,6}\s+', next_line):
                    if i + 2 >= len(lines) or lines[i + 2] != '\n':
 # 다음 줄이 코드 블록이면 빈 줄 추가 안 함
                        if not next_line.strip().startswith('```'):
                            new_lines.append('\n')
                            fixes.append(f"Line {i+1}: Added blank line after list")
 # MD031: 코드 블록 앞뒤 빈 줄 추가
        elif line.strip().startswith('```'):
 # 코드 블록 앞에 빈 줄 추가
            if new_lines and new_lines[-1].strip() and new_lines[-1] != '\n':
                new_lines.append('\n')
                fixes.append(f"Line {i+1}: Added blank line before code block")
 
 new_lines.append(line)
 
 # 코드 블록 뒤에 빈 줄 추가
            if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('```'):
 # 코드 블록이 끝나는 경우
                if line.strip() == '```' or (line.strip().startswith('```') and len(line.strip()) > 3):
 # 다음 줄이 코드 블록이 아니면 빈 줄 추가
                    if i + 1 < len(lines) and not lines[i + 1].strip().startswith('```'):
                        new_lines.append('\n')
                        fixes.append(f"Line {i+1}: Added blank line after code block")
 # MD040: 코드 블록 언어 지정
        elif line.strip().startswith('```') and len(line.strip()) == 3:
 # 언어가 지정되지 않은 코드 블록
 # 다음 몇 줄을 확인하여 언어 추론 시도
 language = None
 for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip().startswith('```'):
 break
 content = lines[j].strip()
 if content:
 # 간단한 언어 추론
                    if 'python' in content.lower() or 'import ' in content or 'def ' in content:
                        language = 'python'
                    elif 'bash' in content.lower() or content.startswith('$') or 'cd ' in content:
                        language = 'bash'
                    elif 'git' in content.lower():
                        language = 'bash'
                    elif 'yaml' in content.lower() or content.startswith('-') or content.startswith('key:'):
                        language = 'yaml'
                    elif 'json' in content.lower() or content.startswith('{') or content.startswith('['):
                        language = 'json'
                    elif 'markdown' in content.lower() or content.startswith('#'):
                        language = 'markdown'
 break
 
 if language:
                new_lines.append(f'```{language}\n')
                fixes.append(f"Line {i+1}: Added language '{language}' to code block")
 else:
 new_lines.append(line)
 else:
 new_lines.append(line)
 
 i += 1
 
 # 파일 저장
 try:
        with open(file_path, 'w', encoding='utf-8') as f:
 f.writelines(new_lines)
 return fixes
 except Exception as e:
        return [f"Error writing file: {e}"]


def main():
    """메인 함수"""
    print("=" * 70)
    print("Markdown 경고 자동 수정 도구")
    print("=" * 70)
 print()
 
 # 주요 MD 파일 목록
 md_files = [
        "PRE_COMMIT_CHECKLIST.md",
        "FINAL_PRE_COMMIT_SUMMARY.md",
        "PROJECT_STRUCTURE_IMPROVEMENT_PLAN.md",
        "TRAINING_OPTIMIZATION_GUIDE.md",
        "GITHUB_UPLOAD_READY.md",
        "FINAL_STATUS.md",
        "README_GITHUB_UPLOAD.md",
        "COMPLETE_RUN_SCRIPT_ERRORS_EXPLANATION.md",
        "MARKDOWN_WARNINGS_EXPLANATION.md",
 ]
 
 total_fixes = 0
 
 for md_file in md_files:
 file_path = PROJECT_ROOT / md_file
 if not file_path.exists():
            print(f"[SKIP] {md_file} - 파일이 없습니다.")
 continue
 
        print(f"\n[FIXING] {md_file}...")
 fixes = fix_markdown_file(file_path)
 
 if fixes:
            print(f"  수정 사항: {len(fixes)}개")
 for fix in fixes[:5]: # 처음 5개만 표시
                print(f"    - {fix}")
 if len(fixes) > 5:
                print(f"    ... 외 {len(fixes) - 5}개")
 total_fixes += len(fixes)
 else:
            print("  수정 사항 없음")
 
    print("\n" + "=" * 70)
    print(f"총 {total_fixes}개 수정 완료!")
    print("=" * 70)


if __name__ == "__main__":
 main()