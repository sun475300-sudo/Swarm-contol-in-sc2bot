#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

ÀüÃ¼ ÇÁ·ÎÁ§Æ®ÀÇ ÇÑ±Û ÀÎÄÚµù ¹®Á¦ ¼öÁ¤ ½ºÅ©¸³Æ®

"""



import os

import sys

from pathlib import Path

from typing import List, Tuple



def check_file_encoding(filepath: Path) -> Tuple[bool, str]:

    """ÆÄÀÏÀÇ ÀÎÄÚµù ¹®Á¦ È®ÀÎ"""

    try:

        with open(filepath, 'rb') as f:

            raw_data = f.read()

        

        # UTF-8·Î µðÄÚµù ½Ãµµ

        try:

            text = raw_data.decode('utf-8')

            # Syntax °Ë»ç

            try:

                compile(text, str(filepath), 'exec')

                return True, "OK"

            except SyntaxError as e:

                return False, f"Syntax error at line {e.lineno}: {e.msg}"

        except UnicodeDecodeError as e:

            return False, f"UTF-8 decode error at byte {e.start}"

    except Exception as e:

        return False, f"Error: {str(e)}"



def fix_file_encoding(filepath: Path) -> bool:

    """ÆÄÀÏ ÀÎÄÚµù ¼öÁ¤"""

    try:

        # ¹é¾÷ »ý¼º

        backup_path = filepath.with_suffix(filepath.suffix + '.encoding_backup')

        if not backup_path.exists():

            with open(filepath, 'rb') as f:

                backup_data = f.read()

            with open(backup_path, 'wb') as f:

                f.write(backup_data)

        

        # ¹ÙÀÌ³Ê¸®·Î ÀÐ±â

        with open(filepath, 'rb') as f:

            raw_data = f.read()

        

        # ¿©·¯ ÀÎÄÚµù ½Ãµµ

        encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']

        decoded_text = None

        used_encoding = None

        

        for enc in encodings:

            try:

                decoded_text = raw_data.decode(enc)

                used_encoding = enc

                if enc == 'utf-8':

                    return True  # ÀÌ¹Ì UTF-8

                break

            except (UnicodeDecodeError, LookupError):

                continue

        

        if decoded_text is None:

            # errors='replace'·Î °­Á¦ µðÄÚµù

            decoded_text = raw_data.decode('latin1', errors='replace')

            used_encoding = 'latin1 (with replacement)'

        

        # UTF-8·Î ÀúÀå

        with open(filepath, 'w', encoding='utf-8', errors='replace') as f:

            f.write(decoded_text)

        

        return True

    except Exception as e:

        print(f"  ERROR: Failed to fix {filepath}: {e}")

        return False



def find_python_files(root: Path) -> List[Path]:

    """¸ðµç Python ÆÄÀÏ Ã£±â"""

    python_files = []

    exclude_dirs = {'__pycache__', '.git', 'venv', '.venv', 'node_modules', 

                    'models', 'logs', 'data', 'replays', 'backups', 'stats',

                    'static', 'build', 'dist', '.pytest_cache'}

    

    for py_file in root.rglob('*.py'):

        # Á¦¿ÜÇÒ µð·ºÅä¸® Ã¼Å©

        if any(exclude_dir in py_file.parts for exclude_dir in exclude_dirs):

            continue

        python_files.append(py_file)

    

    return sorted(python_files)



def main():

    project_root = Path(__file__).parent.parent

    print(f"ÇÁ·ÎÁ§Æ® ·çÆ®: {project_root}")

    print("=" * 80)

    print("ÀüÃ¼ Python ÆÄÀÏ ÀÎÄÚµù Á¡°Ë ¹× ¼öÁ¤")

    print("=" * 80)

    print()

    

    python_files = find_python_files(project_root)

    print(f"ÃÑ {len(python_files)}°³ ÆÄÀÏ ¹ß°ß\n")

    

    problematic_files = []

    fixed_files = []

    

    for i, py_file in enumerate(python_files, 1):

        relative_path = py_file.relative_to(project_root)

        

        if i % 10 == 0:

            print(f"[ÁøÇà Áß] {i}/{len(python_files)} ÆÄÀÏ °Ë»ç Áß...")

        

        is_ok, msg = check_file_encoding(py_file)

        

        if not is_ok:

            problematic_files.append((py_file, msg))

            print(f"[¹®Á¦ ¹ß°ß] {relative_path}")

            print(f"           ¿À·ù: {msg}")

            

            # ¼öÁ¤ ½Ãµµ

            if fix_file_encoding(py_file):

                # Àç°Ë»ç

                is_ok_after, msg_after = check_file_encoding(py_file)

                if is_ok_after:

                    fixed_files.append(py_file)

                    print(f"           ? ¼öÁ¤ ¿Ï·á")

                else:

                    print(f"           ?? ¼öÁ¤ ÈÄ¿¡µµ ¹®Á¦ ÀÖÀ½: {msg_after}")

            print()

    

    print("=" * 80)

    print("Á¡°Ë ¿Ï·á")

    print("=" * 80)

    print(f"ÃÑ ÆÄÀÏ ¼ö: {len(python_files)}")

    print(f"¹®Á¦ ¹ß°ß: {len(problematic_files)}°³")

    print(f"¼öÁ¤ ¿Ï·á: {len(fixed_files)}°³")

    

    if fixed_files:

        print(f"\n? ¼öÁ¤µÈ ÆÄÀÏ:")

        for f in fixed_files:

            print(f"  - {f.relative_to(project_root)}")

    

    if len(problematic_files) > len(fixed_files):

        print(f"\n?? ¼öÁ¤µÇÁö ¾ÊÀº ÆÄÀÏ:")

        for f, msg in problematic_files:

            if f not in fixed_files:

                print(f"  - {f.relative_to(project_root)}: {msg}")

    

    return 0 if len(problematic_files) == len(fixed_files) else 1



if __name__ == '__main__':

    sys.exit(main())

