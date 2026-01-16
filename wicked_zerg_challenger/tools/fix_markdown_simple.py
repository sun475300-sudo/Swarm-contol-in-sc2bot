# -*- coding: utf-8 -*-
"""
Simple Markdown Fixer - Fixes common markdown style issues
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def fix_file(file_path: Path) -> int:
    """Fix markdown file"""
 try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 except Exception:
 return 0
 
 original = content
 fixes = 0
 
 # Fix: 헤딩 뒤 빈 줄 추가
    content = re.sub(r'(^#{1,6}\s+[^\n]+)\n([^\n#\s])', r'\1\n\n\2', content, flags=re.MULTILINE)
 
 # Fix: 리스트 앞 빈 줄 추가 (헤딩이나 다른 리스트가 아닌 경우)
    content = re.sub(r'(^[^\n-*+\d])\n([\s]*[-*+]\s)', r'\1\n\n\2', content, flags=re.MULTILINE)
    content = re.sub(r'(^[^\n-*+\d])\n([\s]*\d+\.\s)', r'\1\n\n\2', content, flags=re.MULTILINE)
 
 # Fix: 리스트 뒤 빈 줄 추가 (다음 줄이 리스트나 헤딩이 아닌 경우)
    content = re.sub(r'([\s]*[-*+]\s[^\n]+)\n([^\n\s#-*+\d])', r'\1\n\n\2', content, flags=re.MULTILINE)
    content = re.sub(r'([\s]*\d+\.\s[^\n]+)\n([^\n\s#-*+\d])', r'\1\n\n\2', content, flags=re.MULTILINE)
 
 # Fix: 코드 블록 앞 빈 줄 추가
    content = re.sub(r'([^\n])\n(```)', r'\1\n\n\2', content)
 
 # Fix: 코드 블록 뒤 빈 줄 추가
    content = re.sub(r'(```)\n([^\n])', r'\1\n\n\2', content)
 
 # Fix: 빈 코드 블록에 언어 추가 (간단한 추론)
    lines = content.split('\n')
 new_lines = []
 i = 0
 while i < len(lines):
 line = lines[i]
        if line.strip() == '```' and i + 1 < len(lines):
 # 다음 몇 줄 확인
 for j in range(i + 1, min(i + 5, len(lines))):
                if '```' in lines[j]:
 break
                if 'python' in lines[j].lower() or 'import ' in lines[j] or 'def ' in lines[j]:
                    line = '```python'
 fixes += 1
 break
                elif 'bash' in lines[j].lower() or lines[j].strip().startswith('$') or 'cd ' in lines[j]:
                    line = '```bash'
 fixes += 1
 break
 new_lines.append(line)
 i += 1
    content = '\n'.join(new_lines)
 
 if content != original:
 try:
            with open(file_path, 'w', encoding='utf-8') as f:
 f.write(content)
 return fixes + 1
 except Exception:
 return 0
 
 return 0


def main():
 files = [
        "PRE_COMMIT_CHECKLIST.md",
        "FINAL_PRE_COMMIT_SUMMARY.md",
        "PROJECT_STRUCTURE_IMPROVEMENT_PLAN.md",
        "TRAINING_OPTIMIZATION_GUIDE.md",
        "GITHUB_UPLOAD_READY.md",
        "FINAL_STATUS.md",
        "README_GITHUB_UPLOAD.md",
 ]
 
 total = 0
 for fname in files:
 path = PROJECT_ROOT / fname
 if path.exists():
 count = fix_file(path)
 if count > 0:
                print(f"Fixed: {fname} ({count} changes)")
 total += count
 
    print(f"\nTotal: {total} files fixed")


if __name__ == "__main__":
 main()