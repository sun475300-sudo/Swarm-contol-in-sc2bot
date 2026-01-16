# -*- coding: utf-8 -*-
"""
Fix all markdown warnings in MD files
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def fix_markdown_content(content: str) -> tuple[str, int]:
    """Fix markdown content and return fixed content and number of fixes"""
 original = content
 fixes = 0
    lines = content.split('\n')
 new_lines = []
 
 i = 0
 while i < len(lines):
 line = lines[i]
        prev_line = new_lines[-1] if new_lines else ""
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
 
 # MD022: 헤딩 앞뒤 빈 줄
        if re.match(r'^#{1,6}\s+', line):
 # 헤딩 앞에 빈 줄
            if new_lines and prev_line.strip() and prev_line != '':
                new_lines.append('')
 fixes += 1
 new_lines.append(line)
 # 헤딩 뒤에 빈 줄
            if next_line.strip() and not re.match(r'^#{1,6}\s+', next_line) and next_line != '':
                new_lines.append('')
 fixes += 1
 # MD032: 리스트 앞뒤 빈 줄
        elif re.match(r'^[\s]*[-*+]\s+', line) or re.match(r'^[\s]*\d+\.\s+', line):
 # 리스트 앞에 빈 줄 (이전이 헤딩이나 리스트가 아니면)
 if new_lines and prev_line.strip():
                if not re.match(r'^#{1,6}\s+', prev_line) and not re.match(r'^[\s]*[-*+]\s+', prev_line) and not re.match(r'^[\s]*\d+\.\s+', prev_line):
                    if prev_line != '':
                        new_lines.append('')
 fixes += 1
 new_lines.append(line)
 # 리스트 뒤에 빈 줄 (다음이 리스트나 헤딩이 아니면)
            if next_line.strip() and not re.match(r'^[\s]*[-*+]\s+', next_line) and not re.match(r'^[\s]*\d+\.\s+', next_line) and not re.match(r'^#{1,6}\s+', next_line):
                if not next_line.strip().startswith('```'):
 # 다음 줄이 코드 블록이 아니면
                    if i + 2 < len(lines) and lines[i + 2].strip() and not lines[i + 2].strip().startswith('```'):
                        new_lines.append('')
 fixes += 1
 # MD031: 코드 블록 앞뒤 빈 줄
        elif line.strip().startswith('```'):
 # 코드 블록 앞에 빈 줄
            if new_lines and prev_line.strip() and prev_line != '':
                new_lines.append('')
 fixes += 1
 # MD040: 코드 블록 언어 지정
            if line.strip() == '```':
 # 다음 몇 줄 확인하여 언어 추론
 lang = None
 for j in range(i + 1, min(i + 10, len(lines))):
                    if '```' in lines[j]:
 break
 check_line = lines[j].strip().lower()
                    if 'python' in check_line or 'import ' in lines[j] or 'def ' in lines[j] or 'class ' in lines[j]:
                        lang = 'python'
 break
                    elif 'bash' in check_line or check_line.startswith('$') or 'cd ' in check_line or 'git ' in check_line:
                        lang = 'bash'
 break
                    elif 'yaml' in check_line or lines[j].strip().startswith('-') or ':' in lines[j] and not 'http' in lines[j]:
                        lang = 'yaml'
 break
                    elif 'json' in check_line or lines[j].strip().startswith('{') or lines[j].strip().startswith('['):
                        lang = 'json'
 break
                    elif 'markdown' in check_line or lines[j].strip().startswith('#'):
                        lang = 'markdown'
 break
 if lang:
                    new_lines.append(f'```{lang}')
 fixes += 1
 else:
 new_lines.append(line)
 else:
 new_lines.append(line)
 # 코드 블록 뒤에 빈 줄
            if next_line.strip() and not next_line.strip().startswith('```'):
                new_lines.append('')
 fixes += 1
 else:
 new_lines.append(line)
 
 i += 1
 
 # 연속된 빈 줄 제거 (최대 2개)
 result_lines = []
 prev_empty = False
 for line in new_lines:
        if line == '':
 if not prev_empty:
                result_lines.append('')
 prev_empty = True
 else:
 result_lines.append(line)
 prev_empty = False
 
    result = '\n'.join(result_lines)
 
 # 파일 끝에 빈 줄 추가
    if result and not result.endswith('\n'):
        result += '\n'
 
 return result, fixes


def fix_file(file_path: Path) -> int:
    """Fix a single markdown file"""
 try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 except Exception as e:
        print(f"  Error reading {file_path.name}: {e}")
 return 0
 
 fixed_content, fixes = fix_markdown_content(content)
 
 if fixes > 0:
 try:
            with open(file_path, 'w', encoding='utf-8') as f:
 f.write(fixed_content)
 return fixes
 except Exception as e:
            print(f"  Error writing {file_path.name}: {e}")
 return 0
 
 return 0


def main():
    """Main function"""
    print("=" * 70)
    print("Markdown 경고 자동 수정 도구")
    print("=" * 70)
 print()
 
 # 모든 MD 파일 찾기
    md_files = list(PROJECT_ROOT.rglob("*.md"))
 
 # 제외할 디렉토리
    exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'backup_before_refactoring'}
 
 md_files = [f for f in md_files if not any(exclude in str(f) for exclude in exclude_dirs)]
 
    print(f"총 {len(md_files)}개 MD 파일 발견")
 print()
 
 total_fixes = 0
 fixed_files = []
 
 for md_file in md_files:
 rel_path = md_file.relative_to(PROJECT_ROOT)
 fixes = fix_file(md_file)
 if fixes > 0:
            print(f"[FIXED] {rel_path} - {fixes}개 수정")
 fixed_files.append((rel_path, fixes))
 total_fixes += fixes
 
 print()
    print("=" * 70)
 if total_fixes > 0:
        print(f"총 {len(fixed_files)}개 파일, {total_fixes}개 수정 완료!")
 else:
        print("수정할 내용이 없습니다.")
    print("=" * 70)


if __name__ == "__main__":
 main()