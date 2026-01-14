#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""ÀÎÄÚµù È®ÀÎ ½ºÅ©¸³Æ®"""



import sys

from pathlib import Path



filepath = Path(__file__).parent / 'main_integrated.py'



print(f"Checking file: {filepath}")

print(f"File exists: {filepath.exists()}")



if filepath.exists():

    # ¹ÙÀÌ³Ê¸®·Î ÀÐ±â

    with open(filepath, 'rb') as f:

        raw_data = f.read()

    

    print(f"File size: {len(raw_data)} bytes")

    

    # UTF-8·Î µðÄÚµù ½Ãµµ

    try:

        text = raw_data.decode('utf-8')

        print("? File is valid UTF-8")

        

        # Syntax °Ë»ç

        try:

            compile(text, str(filepath), 'exec')

            print("? Syntax is valid")

        except SyntaxError as e:

            print(f"? Syntax error: {e}")

            print(f"  Line {e.lineno}: {e.text}")

    except UnicodeDecodeError as e:

        print(f"? UTF-8 decode error at byte {e.start}: {e}")

        print(f"  Problem bytes: {raw_data[e.start:e.start+20]}")

