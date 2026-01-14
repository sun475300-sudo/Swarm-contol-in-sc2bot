import argparse
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
REPLAYS_DIR = ROOT / "replays"
DEPLOY_DIR = ROOT / "AI_Arena_Deploy"

TELEMETRY_PATTERNS = ["telemetry_*.json", "telemetry_*.csv"]
REPORT_PATTERNS = [
    "overlord_optimization_report_*.json",
    "evolution_report.json",
    "performance_summary.json",
]


def _iter_matches(patterns, base: Path):
    for pat in patterns:
        for p in base.glob(pat):
            yield p


def move_telemetry_to_data(dry_run: bool = False) -> int:
    moved = 0
    DATA_DIR.mkdir(exist_ok=True)
    for p in _iter_matches(TELEMETRY_PATTERNS, ROOT):
        target = DATA_DIR / p.name
        if dry_run:
            print(f"[DRY] Move {p} -> {target}")
        else:
            shutil.move(str(p), str(target))
        moved += 1
    return moved


def move_training_stats_to_data(dry_run: bool = False) -> int:
    src = ROOT / "training_stats.json"
    if not src.exists():
        return 0
    DATA_DIR.mkdir(exist_ok=True)
    dest = DATA_DIR / src.name
    if dry_run:
        print(f"[DRY] Move {src} -> {dest}")
    else:
        try:
            shutil.move(str(src), str(dest))
        except Exception as e:
            print(f"[WARN] Failed to move {src}: {e}")
            return 0
    return 1


def prune_logs(keep: int = 5, dry_run: bool = False) -> int:
    if not LOGS_DIR.exists():
        return 0
    files = sorted(
        [p for p in LOGS_DIR.glob("*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    to_delete = files[keep:]
    for p in to_delete:
        if dry_run:
            print(f"[DRY] Delete log {p}")
        else:
            try:
                p.unlink()
            except Exception as e:
                print(f"[WARN] Failed to delete {p}: {e}")
    return len(to_delete)


def prune_reports(keep: int = 1, dry_run: bool = False) -> int:
    removed = 0
    # Collect matching report files in ROOT and logs/
    candidates = []
    for pat in REPORT_PATTERNS:
        candidates.extend(list(ROOT.glob(pat)))
        if LOGS_DIR.exists():
            candidates.extend(list(LOGS_DIR.glob(pat)))
    # Group by stem prefix to keep latest per pattern
    by_name = {}
    for p in candidates:
        key = p.name.split("_")[0] if "_" in p.name else p.name
        by_name.setdefault(key, []).append(p)
    for key, files in by_name.items():
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        to_del = files[keep:]
        for p in to_del:
            if dry_run:
                print(f"[DRY] Delete report {p}")
            else:
                try:
                    p.unlink()
                    removed += 1
                except Exception as e:
                    print(f"[WARN] Failed to delete {p}: {e}")
    return removed


def cleanup_aiarena_submission_path(dry_run: bool = False) -> int:
    path = ROOT / "aiarena_submission"
    if not path.exists():
        return 0
    # Handle stray file vs directory
    try:
        if path.is_file():
            if dry_run:
                print(f"[DRY] Unlink stray file {path}")
            else:
                path.unlink()
            return 1
        if path.is_dir():
            if dry_run:
                print(f"[DRY] Remove directory {path}")
            else:
                shutil.rmtree(path)
            return 1
    except Exception as e:
        print(f"[WARN] Failed to remove {path}: {e}")
    return 0


def remove_ai_arena_deploy(dry_run: bool = False) -> int:
    if not DEPLOY_DIR.exists():
        return 0
    try:
        if DEPLOY_DIR.is_dir():
            if dry_run:
                print(f"[DRY] Remove directory {DEPLOY_DIR}")
            else:
                shutil.rmtree(DEPLOY_DIR)
            return 1
        else:
            if dry_run:
                print(f"[DRY] Unlink stray file {DEPLOY_DIR}")
            else:
                DEPLOY_DIR.unlink()
            return 1
    except Exception as e:
        print(f"[WARN] Failed to remove {DEPLOY_DIR}: {e}")
    return 0


def prune_pycache_and_cursor(dry_run: bool = False) -> int:
    removed = 0
    targets = []
    # Collect all __pycache__ directories
    for root, dirs, files in os.walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                targets.append(Path(root) / d)
    # Top-level .cursor
    cursor_dir = ROOT / ".cursor"
    if cursor_dir.exists():
        targets.append(cursor_dir)

    for t in targets:
        try:
            if dry_run:
                print(f"[DRY] Remove cache dir {t}")
            else:
                shutil.rmtree(t)
            removed += 1
        except Exception as e:
            print(f"[WARN] Failed to remove {t}: {e}")
    return removed


def remove_model_backups(dry_run: bool = False) -> int:
    removed = 0
    patterns = ["*.pt.backup", "*.pth.backup"]
    for base in [ROOT, MODELS_DIR]:
        for p in _iter_matches(patterns, base):
            if dry_run:
                print(f"[DRY] Delete backup {p}")
            else:
                try:
                    p.unlink()
                    removed += 1
                except Exception as e:
                    print(f"[WARN] Failed to delete {p}: {e}")
    return removed


def main():
    ap = argparse.ArgumentParser(description="Cleanup routine for logs, telemetry, and backups")
    ap.add_argument("--dry-run", action="store_true", help="Show actions without changing files")
    ap.add_argument("--keep-logs", type=int, default=5, help="Number of newest logs to keep in logs/")
    ap.add_argument("--keep-reports", type=int, default=1, help="Number of latest optimization/performance reports to keep")
    args = ap.parse_args()

    total_moved = move_telemetry_to_data(dry_run=args.dry_run)
    total_stats_moved = move_training_stats_to_data(dry_run=args.dry_run)
    total_pruned_logs = prune_logs(keep=args.keep_logs, dry_run=args.dry_run)
    total_submission_clean = cleanup_aiarena_submission_path(dry_run=args.dry_run)
    total_deploy_removed = remove_ai_arena_deploy(dry_run=args.dry_run)
    total_caches_removed = prune_pycache_and_cursor(dry_run=args.dry_run)
    total_reports_pruned = prune_reports(keep=args.keep_reports, dry_run=args.dry_run)
    total_backups_removed = remove_model_backups(dry_run=args.dry_run)

    print(
        f"Telemetry moved: {total_moved}, training_stats moved: {total_stats_moved}, logs pruned: {total_pruned_logs}, "
        f"submission cleaned: {total_submission_clean}, deploy removed: {total_deploy_removed}, "
        f"caches removed: {total_caches_removed}, reports pruned: {total_reports_pruned}, backups removed: {total_backups_removed}"
    )


if __name__ == "__main__":
    main()
