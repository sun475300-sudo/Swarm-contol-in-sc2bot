#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple UTF-8 validation for main_integrated.py."""

from pathlib import Path


def main() -> None:
    filepath = Path(__file__).parent / "main_integrated.py"
    print(f"Checking file: {filepath}")
    print(f"File exists: {filepath.exists()}")

    if not filepath.exists():
        return

    raw_data = filepath.read_bytes()
    print(f"File size: {len(raw_data)} bytes")

    try:
        text = raw_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        print(f"[ERROR] UTF-8 decode error at byte {exc.start}: {exc}")
        print(f"Problem bytes: {raw_data[exc.start:exc.start + 20]}")
        return

    print("[OK] File is valid UTF-8")

    try:
        compile(text, str(filepath), "exec")
        print("[OK] Syntax is valid")
    except SyntaxError as exc:
        print(f"[ERROR] Syntax error: {exc}")
        if exc.text:
            print(f"Line {exc.lineno}: {exc.text.strip()}")


if __name__ == "__main__":
    main()
