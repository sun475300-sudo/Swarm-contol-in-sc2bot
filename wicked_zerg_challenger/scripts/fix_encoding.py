import os
import sys

if len(sys.argv) < 2:
    print("Usage: fix_encoding.py <file>")
    sys.exit(1)

p = sys.argv[1]
if not os.path.exists(p):
    print("File not found:", p)
    sys.exit(2)

try:
    with open(p, "rb") as f:
        b = f.read()

    try:
        b.decode("utf-8")
        print("OK: already UTF-8")
        sys.exit(0)
    except UnicodeDecodeError as e:
        print("Unicode issue at byte", e.start, "-> converting using latin1 fallback")
        s = b.decode("latin1")

        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(s)
            print("Rewrote", p, "as UTF-8 (latin1 fallback)")
            sys.exit(0)
        except (IOError, OSError) as write_error:
            print(f"Failed to write file: {write_error}")
            sys.exit(3)
except (IOError, OSError) as read_error:
    print(f"Failed to read file: {read_error}")
    sys.exit(4)
except Exception as ex:
    print(f"Unexpected error: {ex}")
    sys.exit(5)
