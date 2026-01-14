#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

°­·ÂÇÑ ÀÎÄÚµù ¼öÁ¤ ½ºÅ©¸³Æ®

¿©·¯ ÀÎÄÚµùÀ» ½ÃµµÇÏ¿© UTF-8·Î º¯È¯

"""



import sys

import os

from pathlib import Path



def fix_encoding(filepath):

    """ÆÄÀÏ ÀÎÄÚµùÀ» UTF-8·Î °­Á¦ º¯È¯"""

    filepath = Path(filepath)

    

    if not filepath.exists():

        print(f"File not found: {filepath}")

        return False

    

    # ¹ÙÀÌ³Ê¸®·Î ÀÐ±â

    with open(filepath, 'rb') as f:

        raw_data = f.read()

    

    # ¿©·¯ ÀÎÄÚµù ½Ãµµ

    encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1', 'iso-8859-1']

    decoded_text = None

    used_encoding = None

    

    for enc in encodings:

        try:

            decoded_text = raw_data.decode(enc)

            used_encoding = enc

            if enc == 'utf-8':

                print(f"OK: File is already UTF-8")

                return True

            break

        except (UnicodeDecodeError, LookupError):

            continue

    

    if decoded_text is None:

        print(f"ERROR: Could not decode file with any encoding")

        return False

    

    print(f"Detected encoding: {used_encoding}")

    print(f"Converting to UTF-8...")

    

    # UTF-8·Î ÀúÀå

    try:

        # ¹é¾÷ »ý¼º

        backup_path = filepath.with_suffix(filepath.suffix + '.backup')

        with open(backup_path, 'wb') as f:

            f.write(raw_data)

        print(f"Backup created: {backup_path}")

        

        # UTF-8·Î ÀúÀå

        with open(filepath, 'w', encoding='utf-8', errors='replace') as f:

            f.write(decoded_text)

        print(f"File converted to UTF-8: {filepath}")

        return True

    except Exception as e:

        print(f"ERROR: Failed to write file: {e}")

        return False



if __name__ == '__main__':

    if len(sys.argv) < 2:

        print("Usage: fix_encoding_strong.py <file>")

        sys.exit(1)

    

    success = fix_encoding(sys.argv[1])

    sys.exit(0 if success else 1)

