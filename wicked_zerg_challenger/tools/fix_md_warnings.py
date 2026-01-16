# -*- coding: utf-8 -*-
"""
Fix markdown warnings - Simple version
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def fix_content(content: str) -> str:
    """Fix markdown content"""
    lines = content.split('\n')
 result = []
 i = 0
 
 while i < len(lines):
 line = lines[i]
        prev = result[-1] if result else ""
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
 
 # Heading
        if re.match(r'^#{1,6}\s+', line):
 if result and prev.strip():
                result.append('')
 result.append(line)
            if next_line.strip() and not re.match(r'^#{1,6}\s+', next_line):
                result.append('')
 # List
        elif re.match(r'^[\s]*[-*+]\s+', line) or re.match(r'^[\s]*\d+\.\s+', line):
            if result and prev.strip() and not re.match(r'^[\s]*[-*+]\s+', prev) and not re.match(r'^[\s]*\d+\.\s+', prev) and not re.match(r'^#{1,6}\s+', prev):
                result.append('')
 result.append(line)
            if next_line.strip() and not re.match(r'^[\s]*[-*+]\s+', next_line) and not re.match(r'^[\s]*\d+\.\s+', next_line) and not re.match(r'^#{1,6}\s+', next_line) and not next_line.strip().startswith('```'):
 if i + 2 < len(lines) and lines[i + 2].strip():
                    result.append('')
 # Code block
        elif line.strip().startswith('```'):
 if result and prev.strip():
                result.append('')
            if line.strip() == '```':
 # Try to detect language
 lang = None
 for j in range(i + 1, min(i + 10, len(lines))):
                    if '```' in lines[j]:
 break
 check = lines[j].strip().lower()
                    if 'python' in check or 'import ' in lines[j] or 'def ' in lines[j]:
                        lang = 'python'
 break
                    elif 'bash' in check or check.startswith('$') or 'cd ' in check or 'git ' in check:
                        lang = 'bash'
 break
                result.append(f'```{lang}' if lang else line)
 else:
 result.append(line)
            if next_line.strip() and not next_line.strip().startswith('```'):
                result.append('')
 else:
 result.append(line)
 i += 1
 
 # Remove excessive blank lines
 final = []
 prev_empty = False
 for line in result:
        if line == '':
 if not prev_empty:
                final.append('')
 prev_empty = True
 else:
 final.append(line)
 prev_empty = False
 
    return '\n'.join(final) + '\n'


def main():
 files = [
        "FINAL_PRE_COMMIT_SUMMARY.md",
        "TRAINING_OPTIMIZATION_GUIDE.md",
        "PROJECT_STRUCTURE_IMPROVEMENT_PLAN.md",
        "GITHUB_UPLOAD_READY.md",
        "FINAL_STATUS.md",
        "README_GITHUB_UPLOAD.md",
 ]
 
 for fname in files:
 path = PROJECT_ROOT / fname
 if path.exists():
 try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 fixed = fix_content(content)
                with open(path, 'w', encoding='utf-8') as f:
 f.write(fixed)
                print(f"Fixed: {fname}")
 except Exception as e:
                print(f"Error fixing {fname}: {e}")


if __name__ == "__main__":
 main()