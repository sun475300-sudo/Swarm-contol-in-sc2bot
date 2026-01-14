#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""°­Á¦·Î main_integrated.py¸¦ UTF-8·Î º¯È¯"""



import sys

from pathlib import Path



def main():

    filepath = Path(__file__).parent.parent / 'local_training' / 'main_integrated.py'

    

    print(f"Reading file: {filepath}")

    with open(filepath, 'rb') as f:

        raw_data = f.read()

    

    print(f"File size: {len(raw_data)} bytes")

    

    # ¿©·¯ ÀÎÄÚµù ½Ãµµ

    for encoding in ['cp949', 'euc-kr', 'latin1', 'iso-8859-1']:

        try:

            text = raw_data.decode(encoding)

            print(f"Successfully decoded as {encoding}")

            

            # UTF-8·Î ÀúÀå

            backup = filepath.with_suffix('.backup')

            if not backup.exists():

                with open(backup, 'wb') as f:

                    f.write(raw_data)

                print(f"Backup created: {backup}")

            

            with open(filepath, 'w', encoding='utf-8', errors='replace') as f:

                f.write(text)

            print(f"File saved as UTF-8: {filepath}")

            

            # °ËÁõ

            with open(filepath, 'r', encoding='utf-8') as f:

                content = f.read()

            print("Verification: File can be read as UTF-8")

            return True

        except (UnicodeDecodeError, LookupError):

            continue

    

    print("ERROR: Could not decode file")

    return False



if __name__ == '__main__':

    success = main()

    sys.exit(0 if success else 1)

