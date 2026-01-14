#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

¸®ÇÃ·¹ÀÌ °æ·Î È®ÀÎ ½ºÅ©¸³Æ®

"""



import os

from pathlib import Path



def main():

    print("=" * 70)

    print("REPLAY PATH CHECK")

    print("=" * 70)

    print()

    

    # È¯°æ º¯¼ö È®ÀÎ

    env_path = os.environ.get("REPLAY_ARCHIVE_DIR")

    if env_path:

        print(f"[ENV] REPLAY_ARCHIVE_DIR: {env_path}")

        if Path(env_path).exists():

            count = len(list(Path(env_path).glob("*.SC2Replay")))

            print(f"     -> {count} replay files found")

        else:

            print(f"     -> Path does not exist")

    else:

        print("[INFO] REPLAY_ARCHIVE_DIR environment variable not set")

    print()

    

    # °æ·Î ¿ì¼±¼øÀ§ È®ÀÎ

    print("=== Path Priority Check ===")

    paths = [

        ("D:/replays/replays", "Default training source directory"),

        ("replays_archive", "Project replays_archive"),

        ("local_training/scripts/replays", "Scripts replays"),

        ("replays", "Project replays"),

        (str(Path.home() / "replays" / "replays"), "Home replays/replays"),

        (str(Path.home() / "replays"), "Home replays"),

    ]

    

    for path_str, description in paths:

        path = Path(path_str)

        if path.exists():

            count = len(list(path.glob("*.SC2Replay")))

            print(f"[OK] {path_str}")

            print(f"     Description: {description}")

            print(f"     Replay files: {count}")

            print()

        else:

            print(f"[NOT FOUND] {path_str} ({description})")

    

    # ±âº» °æ·Î »ó¼¼ Á¤º¸

    print()

    print("=" * 70)

    print("DEFAULT PATH DETAILS: D:/replays/replays")

    print("=" * 70)

    default_path = Path("D:/replays/replays")

    if default_path.exists():

        replays = list(default_path.glob("*.SC2Replay"))

        print(f"Total replay files: {len(replays)}")

        print()

        print("Sample files (first 10):")

        for r in replays[:10]:

            size_kb = r.stat().st_size // 1024

            print(f"  - {r.name} ({size_kb} KB)")

        

        # ¿Ï·á µð·ºÅä¸® È®ÀÎ

        completed_dir = default_path / "completed"

        if completed_dir.exists():

            completed_count = len(list(completed_dir.glob("*.SC2Replay")))

            print()

            print(f"Completed replays: {completed_count} (in {completed_dir})")

    else:

        print("[ERROR] Default path does not exist!")

        print("[INFO] Creating directory...")

        default_path.mkdir(parents=True, exist_ok=True)

        print("[OK] Directory created")

    

    print()

    print("=" * 70)

    print("CHECK COMPLETE")

    print("=" * 70)



if __name__ == "__main__":

    main()

