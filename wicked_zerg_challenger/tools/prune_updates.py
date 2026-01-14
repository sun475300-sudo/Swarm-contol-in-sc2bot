import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPDATES = ROOT / "AI_Arena_Updates"


def list_update_dirs():
    if not UPDATES.exists():
        return []
    dirs = [p for p in UPDATES.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs


def prune(keep: int, dry_run: bool = False) -> int:
    dirs = list_update_dirs()
    to_delete = dirs[keep:]
    for p in to_delete:
        if dry_run:
            print(f"[DRY] Remove update folder {p}")
        else:
            try:
                shutil.rmtree(p)
            except Exception as e:
                print(f"[WARN] Failed to remove {p}: {e}")
    return len(to_delete)


def main():
    ap = argparse.ArgumentParser(description="Prune old AI_Arena_Updates folders, keeping the latest N")
    ap.add_argument("--keep", type=int, default=3, help="Number of latest update folders to keep")
    ap.add_argument("--dry-run", action="store_true", help="Show actions without deleting")
    args = ap.parse_args()

    removed = prune(keep=args.keep, dry_run=args.dry_run)
    print(f"Removed {removed} update folders; kept {args.keep}")


if __name__ == "__main__":
    main()
