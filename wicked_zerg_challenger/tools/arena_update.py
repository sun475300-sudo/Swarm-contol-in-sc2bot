"""
Arena Update Packager

Creates a timestamped AI Arena update package using existing packager,
then moves the generated ZIP into a dedicated AI_Arena_Updates folder.

Usage:
  python tools/arena_update.py [--keep-submission] [--notes PATH]

Options:
  --keep-submission   Keep the temporary aiarena_submission folder
  --notes PATH        Optional path to a markdown/text file to copy into
                      the update folder with a timestamped filename
"""

import argparse
from pathlib import Path
import shutil
from datetime import datetime
import sys


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def find_latest_zip(root: Path, bot_prefix: str) -> Path | None:
    zips = sorted(root.glob(f"{bot_prefix}_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return zips[0] if zips else None


def copy_notes(src: Path, dst_dir: Path):
    if not src.exists():
        print(f"[WARN] Notes file not found: {src}")
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"update_notes_{timestamp()}{src.suffix}"
    content = src.read_text(encoding="utf-8", errors="ignore")
    header = f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    if src.suffix.lower() in {".md", ".txt"}:
        content = header + content
    dst.write_text(content, encoding="utf-8")
    print(f"[OK] Notes copied to {dst}")


def main():
    parser = argparse.ArgumentParser(description="Arena Update Packager")
    parser.add_argument("--keep-submission", action="store_true", help="Keep aiarena_submission folder after packaging")
    parser.add_argument("--notes", type=str, default=None, help="Optional notes file to include in update folder")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    # Ensure project root is on sys.path for imports
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    updates_dir = root / "AI_Arena_Updates"

    # Pre-clean submission path if a stray file exists (avoid NotADirectoryError)
    submission = root / "aiarena_submission"
    try:
        if submission.exists() and not submission.is_dir():
            submission.unlink(missing_ok=True)
            print(f"[CLEANUP] Pre-removed stray file: {submission}")
    except Exception as e:
        print(f"[WARN] Failed pre-clean on {submission}: {e}")

    # Import and run existing packager
    from package_for_aiarena import AIArenaPackager
    packager = AIArenaPackager()
    ok = packager.package()
    if not ok:
        print("[ERROR] Packaging failed; aborting update")
        return

    # Locate the latest zip created by packager
    latest_zip = find_latest_zip(root, packager.bot_name)
    if not latest_zip:
        print("[ERROR] No ZIP found after packaging")
        return

    # Create update folder and move zip into a timestamped subfolder
    release_dir = updates_dir / f"{packager.bot_name}_{timestamp()}"
    release_dir.mkdir(parents=True, exist_ok=True)
    target_zip = release_dir / latest_zip.name
    shutil.move(str(latest_zip), str(target_zip))
    print(f"[OK] Moved package to {target_zip}")

    # Optionally copy notes
    if args.notes:
        copy_notes(Path(args.notes), release_dir)

    # Optionally remove aiarena_submission to avoid duplication
    if not args.keep_submission:
        submission = root / "aiarena_submission"
        if submission.exists():
            shutil.rmtree(submission, ignore_errors=True)
            print(f"[CLEANUP] Removed {submission}")

    print(f"[DONE] Arena update prepared at {release_dir}")


if __name__ == "__main__":
    main()
